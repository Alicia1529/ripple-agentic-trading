# Architecture

This is the current state of the system design. It's a living document — when the design changes, this file is edited in place to describe the new current state; the *history* of why it changed belongs in `docs/DECISIONS.md`, not here.

## Positioning

The initial $500–1000 per live account is a deliberately small real-money validation allocation, not a fixed lifetime ceiling or merely an amount to play with. The goals are:

1. Learn agent-system design by building a complete "untrusted LLM decision layer + deterministic code-enforced risk layer" system.
2. Find out whether a multi-agent architecture (3 analysts + PM) and a specific model choice actually add value over a simple deterministic strategy and over doing nothing (passive holding) — which requires a genuinely comparable baseline running alongside the live accounts, not just the agent on its own.
3. Preserve the option to increase an account's funding if live evidence later shows stable, attributable profitability after costs and within the risk rules. Any increase is an explicit human decision, not an automated response to recent performance; its amount and evidence threshold must be reviewed before the increase.

**Hard constraint: low routine operational load after a stable pilot.** Reconciliation, health checks, credential-expiry checks, missed-run detection, and reporting are automated. Ambiguous broker outcomes, a broken invariant, or a material risk event fail closed and notify a human. The design does not promise zero oversight before the broker integration and recovery behavior have been observed in paper and live-canary phases. See `docs/DECISIONS.md` D1, D2, D2c, D14, and D17 for how this constraint shaped the scope.

**Target scope:** two live Robinhood Agentic accounts running the same 3-analyst + PM architecture with different model configurations, plus a controlled shadow incubation pool. This is the target state, not the starting state; rollout gates are defined below. The live comparison provides useful evidence under controlled inputs, but one realized equity curve per model is not treated as causal proof of model superiority.

## System architecture: decision and execution are separate stages

**Core principle:** when to decide (a target portfolio) and when to execute (place real orders) are different problems. Decision timing is governed by information availability — the day's closing data isn't final until after close. Execution timing is governed by market liquidity and execution quality — the first few minutes after open have the thinnest liquidity and widest spreads. A signal being generated after close does not imply the resulting order should be submitted after close.

### Daily timeline (US Eastern Time)

Account A, Account B, and the shadow pool share the same market-data snapshot moment (a controlled variable, for a fair comparison) but each produces its own decision independently (Account A via Claude, Account B via OpenAI/Codex, each shadow candidate via its own config).

**Timezone handling:** none of the triggers below are a fixed UTC cron time. The scheduler polls every 5–10 minutes inside a loose window around the target time; the script itself computes the real current time in `America/New_York` and no-ops if it isn't inside the window yet. See D10a in `docs/DECISIONS.md` for why.

```
4:00 PM ET   Market close
4:00–9:00    Wait — earnings and other market-moving news often come out after the close
             (sometimes hours after), so the gap gives that information time to land before
             the day's decision is made, rather than analyzing a still-incomplete picture
9:00 PM ET   Decision Run (three parallel schedules, all reading the same market snapshot):
             - Account A: Claude Code cloud scheduled routine
             - Account B: Codex cloud Automation
             - Shadow pool: GitHub Actions
             Each does:
             1. Freeze one DecisionSnapshot shared by all comparison lanes
             2. Analyst agent(s) produce signals/expected returns (own model config)
             3. Portfolio manager produces a target portfolio
             4. Risk engine validates constraints (see Risk layer, below)
             5. Order planner turns the target portfolio into concrete orders
             6. Persist the immutable OrderPlan transactionally
             7. Archive the DecisionSnapshot, prompts/tool traces, and raw model outputs as an immutable audit bundle

Overnight    No trading. The persisted OrderPlan is not touched.

~9:35 AM ET  Execution Run (GitHub Actions, ~5 minutes after open — not pinned to 9:30:00;
next day     live accounts only, the shadow pool uses a virtual fill simulator instead):
             1. Load yesterday's persisted OrderPlan
             2. Revalidate account state (see Execution revalidation, below)
             3. Check current positions and available cash
             4. Check whether price has moved outside the pre-set tolerance band
             5. Execute the orders that pass validation
             6. Monitor fills
             7. Reconcile positions
             8. Append execution events and broker reconciliation transactionally
             9. Archive detailed logs and fill evidence as an immutable audit bundle
```

Why two separate runs: execution always happens after the market has opened, so there is no dependency on how Robinhood Agentic's order tools behave while the market is closed. ~9:35 rather than exactly 9:30:00 avoids the thinnest-liquidity, widest-spread minutes right at open. Phase 0 favors deterministic, debuggable behavior over sophisticated execution — no VWAP/TWAP. Separating decision from execution also makes post-mortems clean: a bad outcome is either "the call was wrong" or "the price moved before execution," never both tangled together — and it's what makes backtests able to share the same timing semantics as production (see Look-ahead bias, below).

### DecisionSnapshot, OrderPlan, and execution state

Every comparison lane reads the same immutable `DecisionSnapshot`. It contains the allowed market data, news/fundamental inputs from the v1 free/open primary feed (such as Yahoo Finance, Google Finance, and Fidelity's public pages; X is excluded by D19), universe, and as-of timestamps used for that decision. Each lane's exact prompt/config hash, model identifier, runtime version, and tool versions are recorded alongside the snapshot. This controls the evidence available to the models instead of allowing each runtime to fetch a different news corpus and calling the result a controlled A/B test.

The initial deterministic-core module accepts a strict snapshot envelope containing `snapshot_id`, timezone-aware `as_of`, a non-empty unique `universe`, and JSON-only `inputs`. It recursively detaches and freezes the document at creation, rejects unknown envelope fields, and only exports a fresh mutable copy for serialization. Feed-specific schemas inside `inputs`, canonical content hashing, and object-store persistence remain later Phase 0 work; the minimal envelope is not treated as proof that those contracts are complete.

The output of the decision stage is a persisted, **immutable once written** `OrderPlan`:

```yaml
order_plan_id: uuid
decision_time: 2026-08-21T21:05:00-04:00     # ET
account_id: account_A                          # account_B / shadow:mean_reversion / shadow:spy_qqq / shadow:candidate_C ...
model_config_version: config_A_v3              # for reproducibility
decision_snapshot_id: uuid
market_snapshot_as_of: 2026-08-21T21:00:00-04:00

target_portfolio:
  AAPL: "0.15"
  MSFT: "0.10"
  ...
  cash: "0.20"

orders:
  - order_id: uuid
    symbol: AAPL
    side: BUY
    quantity: "12"
    order_type: LIMIT
    limit_price: "227.50"              # decision-time price + D3a tolerance band
    price_tolerance_pct: "0.005"       # used at execution time to detect an excessive gap
    reference_price_at_decision: "226.40"
```

The initial deterministic-core `OrderPlan` module enforces the strict top-level fields illustrated above, recursively freezes `target_portfolio` and `orders`, and applies a scalar-value allowlist to every planned-order field. Because arbitrary nested objects are not accepted, execution outcomes cannot be smuggled into the decision document. Tax lots remain out of scope for v1. D23 fixes the persisted numeric representation as base-10 decimal strings; complete semantic validation for weights, prices, quantities, order-type conditionals, and persistence constraints remains later Phase 0 work.

Once generated, the Execution Agent may only: **execute as-is / abort the whole plan / scale down proportionally against available cash / reject specific orders because risk or account state changed**. It may never re-run analyst/PM reasoning or change direction because "its view changed today" — that would be tampering with an already-made decision, which breaks reproducibility, auditability, and attribution.

Execution status is not mutated inside the plan. `planned`, `submission_started`, `broker_acknowledged`, `partially_filled`, `filled`, `rejected`, `aborted`, and `unknown` are append-only `ExecutionEvent` facts. Scaling or clipping produces an event that records the original quantity, the applied rule, and the actual quantity; the original OrderPlan remains unchanged.

- Allowed: a symbol gaps overnight beyond the tolerance threshold → the execution guard rejects that order.
- Not allowed: the PM decided to buy NVDA yesterday, and the Execution Agent decides today it doesn't like NVDA anymore → sells it.

If a plan is aborted, the system waits for the next normal decision run — it never catches up or re-submits a stale plan.

**Execution must not be an LLM session.** This is also why the Decision-stage LLM session must never hold a tool capable of placing a live order. If the model reasoning about the trade also holds the tool that executes it, "risk rules live only in code, never in a prompt" (see Risk layer) degrades into "the prompt tells the model to behave," no matter how deterministic the risk math itself is. The Execution Run is plain, non-agentic code — an MCP client or direct broker API call, not an LLM inference loop — precisely so this guarantee holds regardless of which model powered the decision.

### Storage responsibilities

The three storage classes have deliberately different jobs:

| Storage | Holds | Required behavior |
|---|---|---|
| Transactional store | OrderPlans, ExecutionEvents, per-account risk state, leases, submission attempts, broker acknowledgements, and reconciliation results | Atomic writes, unique constraints, conditional updates, and cross-runner leases. This is the source of truth for what may execute next. |
| Object storage | Frozen DecisionSnapshots, raw model outputs, prompt/tool traces, detailed logs, broker-response evidence, and generated audit bundles | Immutable or versioned blobs, addressed by URI plus content hash. Losing one must not make the execution state ambiguous. |
| Git repository | Code, config, schemas, documentation, migrations, and sanitized reports | Human review and version history. Git is not the runtime database, and scheduled jobs do not commit/push live execution state. |

Concrete example: the transactional row says `order_id=123` is in `broker_acknowledged` and points to an object such as `audit/2026-08-21/account_A/order-123/broker-response.json` plus its SHA-256 hash. The small row participates in correctness decisions; the large response remains available for audit without bloating the transactional database.

No storage vendor is chosen here. Phase −1 verifies the required broker behavior; Phase 0 selects the smallest managed services that provide these semantics. Application code depends on the semantics, not a provider-specific API.

### Execution-time revalidation and abort conditions

The Execution Agent's job before placing an order is checking "does last night's decision still hold today," not making a new decision:

| Check | Trigger | Action |
|---|---|---|
| Account state reconciliation | Current positions/cash don't match what the OrderPlan assumed | Abort the plan, log the discrepancy, notify (rare event) |
| Price tolerance | Open price vs. `reference_price_at_decision` exceeds `price_tolerance_pct` | Abort that order — no chasing the price, no re-reasoning, wait for the next decision run |
| Available cash / buying power | Insufficient to execute the full order | Scale down proportionally or abort the excess, log it |
| Risk layer re-check | Re-run today's account equity through the risk rules (e.g. overnight equity change pushes an order past the 20% position cap) | Clip or reject, same logic as the risk layer itself |
| Data freshness | Current quotes/account state unavailable (API failure etc.) | No trade, log and notify, wait for the next cycle |

**Existing-position stop-loss/take-profit recheck, independent of the day's OrderPlan:** every Execution Run also re-evaluates stop-loss/take-profit conditions on *all currently held positions* in that account, regardless of whether there's a new decision today or how compelling a new thesis sounds. Any triggered stop-loss/take-profit fires immediately per the risk layer rules. (See `docs/DECISIONS.md` D13 — this closes a gap found while reviewing FriesTrader.)

### Idempotency

The window-polling scheduler can trigger more than once, and a process can crash after the broker accepts an order but before the local acknowledgement is recorded. Local "check, submit, then mark submitted" logic cannot close that ambiguity window by itself.

- A unique constraint on `(account_id, decision_date)` prevents two authoritative plans for one account/day.
- Every `order_id` is generated once in the OrderPlan. A unique constraint prevents two local execution records for it.
- A transactional cross-runner lease, not a runner-local marker file, admits only one active execution attempt for an account/plan.
- Execution appends `submission_started` before the broker call and `broker_acknowledged` only after a broker order identifier is returned.
- The plan's `order_id` is passed as the broker idempotency key if Robinhood supports it.
- A retry that sees `submission_started` without an acknowledgement treats the outcome as `unknown`. It queries broker order history and reconciles before doing anything else.
- If reconciliation cannot prove that the order was rejected or never accepted, the account fails closed and notifies a human; the order is not automatically resubmitted.

Strict at-most-once submission is claimed only if the broker supports a stable client idempotency key. Without it, the guarantee is fail-closed reconciliation with no blind retry. See `docs/DECISIONS.md` D16, which supersedes the stronger claim in D3c.

### Look-ahead bias: backtest/live timing must match

**Rule:** if a signal was generated using Day T's closing price or other end-of-day data, neither a historical backtest nor a paper/live performance calculation may assume the fill happened at Day T's close. It must be modeled as filling near Day T+1's open.

- Wrong: signal generated from a $220 close on Day T → backtest assumes a fill at $220.
- Correct: signal generated at Day T close → fill modeled at T+1 open (or shortly after).

This applies equally to the shadow pool's bookkeeping (see Baseline & benchmark, below): the mean-reversion baseline, SPY/QQQ, and any future candidate must mark their virtual fills at the **T+1 open price**, never at the signal day's own close — otherwise the baseline would have an information advantage the live accounts don't get, and the comparison would be unfair. Any historical backtest built later (e.g. to tune the mean-reversion strategy) must follow the same timing semantics so backtest and production behave consistently.

### System diagram

```
Frozen DecisionSnapshot (same allowed market/news inputs for both accounts + shadow lanes)
                    |
        +-----------+-----------------------+
        v                                    v                               v
   Account A pipeline                   Account B pipeline              Shadow pool (one lane per candidate)
   Analyst(Config A) -> PM(Config A)     Analyst(Config B) -> PM(Config B)  Analyst/rules -> PM or rule engine
        v                                    v                               v
   Risk Engine A                         Risk Engine B                   Virtual Risk Engine (same logic)
        v                                    v                               v
   Order Planner -> OrderPlan A          Order Planner -> OrderPlan B    Order Planner -> virtual OrderPlan
        | (persisted, unchanged overnight)   |                               |
==================================== next day, ~9:35 ET ============================================
        v                                    v                               v
   Execution Revalidation A              Execution Revalidation B        Virtual Fill Simulator
        v                                    v                          (marks fills at T+1 open)
   Robinhood Agentic Account A           Robinhood Agentic Account B          v
        v                                    v                          Virtual equity curve
   Fill Monitoring -> Transactional Events/Reconciliation -> Immutable Audit Bundles
```

**Multi-account note:** this is deliberately not the common "multiple accounts execute the same shared decision, scaled by each account's capital" pattern. Accounts A and B intentionally run independent decision pipelines (different model configs) — that's the point of D2a. What they genuinely share is only the market-snapshot timing and the trading universe (controlled variables), not the target portfolio. A "same decision, per-account sizing" mode would need separate design work and isn't in scope now.

**Key design constraints:**

- Analyst output schema: `{ticker, direction, score∈[-1,1], confidence∈[0,1], rationale}`, fully logged, tagged with `account_id` and `order_plan_id` so signal → OrderPlan → execution result can be traced for audit.
- The two live accounts are fully independent: separate risk-layer instances, separate execution-adapter calls, separate broker statements. No shared account, so none of the "shared-account multi-strategy" conflict-resolution machinery is needed.
- The shadow pool is a lightweight `strategy_ledger`: each candidate runs a Decision Run and produces an OrderPlan, but there's no Execution Run/broker involved — a virtual fill simulator marks fills at the T+1 open price. It never calls the execution adapter or touches a real account, so it never has a capital-conflict problem, and stays far lighter than a full shared-account ledger. The pool being open just means adding a candidate is registering a new record, not an architecture change.
- Shadow-to-live graduation is the only path that grows the number of live accounts (see D5a). Existing live accounts may receive a manually approved funding increase after a separate profitability and risk review (see D14). The system never opens an account, deposits capital, or raises an account's allocation on its own.
- Risk-layer split: rules in a prompt are *advisory*; rules in code are *binding*. Both live accounts run the same rule values, but state (today's order count, current drawdown) is tracked independently per account.
- The execution adapter is pluggable. v1 enables Alpaca paper (for validation) and Robinhood Agentic (both live accounts reuse the same adapter implementation, differing only in credentials/account). It is only ever called after ~9:35am, never right after close.

## Risk layer (code-enforced)

Both live accounts apply every rule below independently, computed against that account's own equity — a breaker firing on Account A does not pause Account B.

| Rule | Value | Action when triggered |
|---|---|---|
| Max position per symbol | 20% of the account's own equity | Clip the order to the cap |
| Max new positions per day | 3 per account | Excess orders are dropped and logged |
| Daily loss circuit breaker | −5% (unrealized + realized, against the account's own equity) | No new positions for the rest of the day; closing positions still allowed |
| Drawdown tier 1 | −10% from the account's high-water mark | Block new positions, generate a notification (the one case worth glancing at) |
| Drawdown tier 2 | −15% from the account's high-water mark | Disable new entries and require manual restart; deterministic risk-reducing exits remain available. The other account is unaffected. |
| Prohibited (v1) | Shorting, leverage, options | Rejected at the adapter layer, both accounts |
| Wash-sale guard (cross-account) | 30-day lookback (configurable); the IRS rule applies per taxpayer, not per account | Blocks buys only (new entries/top-ups) — never blocks a stop-loss/take-profit/exit sell, since risk management never defers to a tax outcome. A blocked buy is logged and flagged for year-end tax reference. Checked across a configurable `linked_accounts` list covering both live accounts |

Every intercepted/clipped instruction is logged as `{original instruction, rule triggered, actual action, account_id}`.

**Wash-sale guard's known limitation:** this only covers accounts and trades this system can see. If a repurchase happens in an account outside the system's control, it can't be prevented — that risk is on the human to track, not this system's responsibility.

**Low-ops relationship:** once the live canary has proved the operational path, routine reconciliation, health checks, and reports run unattended. Notifications are reserved for ambiguous broker outcomes, missed runs, broken invariants, credential expiry, material drawdown, or an evidence gate that needs a human decision.

**Kill switch, honestly stated:** Robinhood's own documentation does not describe an instant "flatten everything" kill-switch capability — only the ability to cancel a pending order, and it explicitly notes an agent may be "difficult to monitor or stop in real time." This system's "kill switch" means: a code-level flag that immediately stops generating new orders and cancels all pending ones; existing positions still need to be unwound through normal sell orders, not instantly zeroed. This limitation is documented in code comments and the runbook rather than overclaimed.

## Baseline & benchmark

The periodic report compares the following curves after trading costs. Candidate definitions, evaluation windows, and promotion criteria are registered before the candidate starts; adding many candidates and promoting whichever happens to win is not a valid evaluation method.

1. **Account A curve** — Model Config A's live, real-money equity after risk layer A.
2. **Account B curve** — Model Config B's live, real-money equity after risk layer B.
3. **Mean-reversion baseline curve** — same universe, same market snapshot, a simple deterministic rule (e.g. reverse-enter when price deviates from its N-day mean beyond a threshold), fills marked at T+1 open by the virtual fill simulator, uninfluenced by any LLM.
4. **SPY/QQQ buy-and-hold curve** — an equal-dollar buy of SPY and QQQ starting the day the live accounts began trading, held since, also marked at T+1 open, pure bookkeeping, no orders placed.
5. **Shadow candidate curves** — one per registered candidate, pure virtual bookkeeping. Additional architectures such as TradingAgents wait until the core comparison pipeline is stable.

What this provides evidence about:

- **Model-choice difference:** Account A vs. Account B under the same frozen DecisionSnapshot, prompt/tool contract, risk layer, and universe. One live path per model remains observational evidence, not causal proof.
- **Agent-architecture difference:** Account A/B vs. the mean-reversion baseline, interpreted with risk, turnover, and cost differences rather than raw ending value alone.
- **Active-management difference:** accounts and baseline vs. SPY/QQQ buy-and-hold, reported with volatility, drawdown, cash exposure, beta, turnover, and after-cost return.
- Per-analyst direction accuracy and confidence calibration (reliability diagrams), tracked per account.

Every comparison curve's computation is written once as code; none of it needs manual upkeep.

The original 8-week rule is an **operational-stability gate only**: no missed or duplicate cycles, no unresolved reconciliation, and no material risk-layer defect. Strategy promotion additionally requires a pre-registered minimum sample size, an untouched holdout period, after-cost performance against both benchmarks, and drawdown/risk limits. Those numerical thresholds must be decided before a candidate's evaluation begins; they are not chosen after seeing its curve. See D18, which supersedes D5a's profit-based 8-week graduation rule.

## Staged rollout

1. **Phase −1 — feasibility:** prove headless broker authentication/refresh, explicit account selection, two independent Agentic-account bindings, order/review/cancel schemas, fractional-order behavior, broker order-history reconciliation, client idempotency support, and scheduler secret/timezone behavior. Completion means every item has a captured test result; failure changes the architecture before production code is built.
2. **Phase 0 — deterministic core:** implement DecisionSnapshot, immutable OrderPlan, transactional ExecutionEvents, risk engine, leases, reconciliation, fake broker, and failure-injection tests. Completion means crash-before-submit, crash-after-acceptance, duplicate trigger, stale data, and partial-fill tests all fail closed.
3. **Phase 1 — paper/shadow:** run both model lanes and fixed baselines on the same frozen inputs. Completion means at least eight continuous weeks with no unresolved operational defect; this establishes reliability, not profitability.
4. **Phase 2 — one-account live canary:** fund one account with a manually approved validation allocation and verify real credential lifecycle, fills, reconciliation, alerts, and recovery. Risk-reducing exits remain available even when new entries are disabled.
5. **Phase 3 — two-account live comparison:** add the second account only after the canary gate passes. Additional shadow candidates and any later capital increase follow their separately pre-registered evidence and human-approval gates.

## Deployment scheduling reliability

### Broker OAuth credential lifecycle

Each live-account Execution Run owns a separate OAuth client registration and credential record; it never borrows the interactive Codex or Claude MCP session. A one-time interactive bootstrap command and the plain headless runner share one private, versioned credential store through a small `load` / compare-and-swap interface. The record atomically contains the SDK token and client-registration models, an absolute access-token expiry, and the validated MCP resource, authorization-server issuer, and authorization-server metadata needed to find the refresh endpoint after a fresh process starts.

The headless runner never opens a browser, registers a client, or begins an authorization-code flow. Before its first MCP request, a version-pinned adapter validates that the stored server/resource/issuer bindings match configuration and restores the Python MCP SDK's in-memory expiry and metadata. An age-unknown access token with a refresh token is treated as expired so the runner refreshes before sending it. Missing state, a missing refresh token, rejected refresh, binding mismatch, stale compare-and-swap write, or any request for interactive authorization fails closed and notifies the human to rerun bootstrap. Refreshed state is atomically replaced so overlapping processes cannot silently overwrite a rotated refresh token.

Refresh-token rotation has the same external-ambiguity class as order submission. Before a runner sends a refresh request, it transactionally records `refresh_started` with the current lease fencing token and expected credential revision. Only after the authorization server responds, the new complete secret version is stored, and the transactional record commits that exact secret-version pointer may the state return to `ready`. If the process or lease disappears anywhere in between, the state becomes `refresh_unknown`; lease expiry never authorizes automatic reuse of the old rotating refresh token. Recovery fails closed and requires a human bootstrap or a separately proven reconciliation procedure. A lease fences later local writes but cannot revoke an external refresh request already in flight.

The concrete secret-store vendor remains a Phase 0 deployment choice, but it must provide encryption at rest, access isolation per live account, atomic compare-and-swap updates, exact-version addressing, and auditability. A strongly consistent transactional record identifies the only approved exact secret version; an eventually consistent `current` alias cannot be the correctness pointer. A static environment variable or write-only GitHub Actions secret is sufficient for the short-lived access-token feasibility probe, not for production refresh-token rotation. See D22, `docs/feasibility/mcp-python-oauth-client.md`, and `docs/feasibility/github-actions-oauth-secret-store.md`.

GitHub Actions documents that scheduled jobs can be delayed under high load and can be dropped. This applies to the Execution Run and the shadow pool's Decision Run. Account A/B's Decision Runs sit on Claude Code's / Codex's own cloud scheduling, whose reliability is unverified (see Open Questions) and is treated with the same conservative assumption.

Repository Python commands target Python 3.12, selected by the root `.python-version` file. Scheduled commands must enter that environment with `uv run --no-cache`, rather than assuming the runner's unqualified `python3` is compatible or that its default uv cache is writable. `--no-cache` gives each invocation a temporary cache and avoids the default cache path that the observed Automation sandbox could not write. This is a repository/runtime requirement, not a request to replace the host operating system's Python.

The scheduler is only a trigger. The transactional store decides whether a cycle may run, leases prevent overlap, and price/data-freshness checks decide whether a delayed execution is still valid. A missed-run monitor must use an independent heartbeat path rather than relying only on the same scheduler it monitors.

If the Execution Run itself is delayed, the price-tolerance check (see above) provides natural protection: the longer the delay, the more likely the price has moved outside the tolerance band, so the system leans toward aborting rather than forcing a stale plan through. An abort just waits for the next normal decision run — no catch-up, no backfilled orders.

## Cost model

| Item | Estimate | Note |
|---|---|---|
| Account A's Decision Run (Claude) | ~$0/month marginal during monitored feasibility if allowance remains | Claude Pro limits are shared and variable; any production API fallback is explicit and budget-capped |
| Account B's Decision Run (Codex/OpenAI) | ~$0/month marginal during monitored feasibility if allowance remains | ChatGPT Plus limits are shared and variable; any production API fallback is explicit and budget-capped |
| Deployment (GitHub Actions) | $0 | Free tier covers both live accounts' Execution Run and the shadow pool's Decision Run |
| Transactional + object storage | Provisional; target free/low-cost managed tiers | Provider selection happens only after required transaction, lease, retention, and export semantics are verified |
| Shadow pool LLM calls (metered API) | ~$0 for non-LLM strategies (e.g. mean reversion); roughly +$10–20/month per LLM-driven candidate added | The pool doesn't have a ready subscription the way the two live accounts do, so metered billing is used for whatever candidates need it — call volume in the validation stage is small |
| Market data | $0 | yfinance / Alpaca free tier |
| News/fundamental data, primary (D19) | $0 | Free/open sources — Yahoo Finance, Google Finance, Fidelity public pages |
| News/fundamental data, X supplement | $0 | Excluded from v1 by D19; no X integration or credential is provisioned |
| Alpaca paper | $0 | Free |
| **Monthly total** | **~$0–20/month marginal during monitored feasibility** if subscription allowance is sufficient | Production API fallback cost remains provisional until real prompt/token measurements support an explicit daily and monthly cap; there is no silent overage |

One-time/capital items (not part of the monthly figure): both live accounts initially get $500–1000 in funding (total initial exposure $1000–2000), funded only in the live phase and fully at risk of loss. That range is the validation starting point, not a permanent cap. If an account later demonstrates stable, attributable profitability after trading costs and within the risk rules, Alicia may manually approve an appropriate funding increase after reviewing the evidence and risk impact; the system never scales capital automatically. Every shadow-to-live graduation likewise starts with its own $500–1000 allocation, individually approved by hand — there's no cap on the eventual number of accounts, only on how fast new accounts or larger allocations get approved.

Real trading costs (commission, spread, slippage, regulatory fees) are logged automatically per fill, kept separate from P&L — no manual reconciliation required.

## Open questions (need hands-on verification, not assumed from documentation)

| Question | Basis so far | Why it matters |
|---|---|---|
| Can a plain, non-agentic GitHub Actions client authenticate to Robinhood Trading MCP headlessly and refresh credentials without routine human action? | The local macOS runner now proves restart-safe bootstrap, cross-process refresh, rejection handling, and sanitized account binding; GitHub Actions secret storage/runtime behavior remains untested | The entire Execution Run depends on the deployment boundary; local proof does not establish the hosted runner |
| Can two Robinhood Agentic accounts each bind an independent agent/API credential? | Robinhood allows up to 10 self-directed investing accounts, Agentic accounts included, but the account-to-agent relationship isn't documented | Needed for D2 (two accounts) to work as designed |
| Does live Robinhood behavior honor explicit account selection and the declared fractional/dollar-order shapes? | The current review/place/cancel/history schemas require `account_number`; review/place declare share-or-dollar inputs and regular-hours market-only fractional support up to six decimals. No live eligibility or routing test has run. | Small validation accounts and account isolation depend on this |
| What is the real token/context footprint and rejection rate for daily 3-analyst+PM traffic? | Official vendor docs confirm variable shared subscription allowances and metered automation paths; no fixed capacity is promised. The actual Ripple prompts do not exist yet to measure | Determines the explicit API fallback budget and whether monitored subscription runs are operationally sufficient |
| Do Claude Code's / Codex's cloud scheduling features natively support IANA timezones, or only UTC/browser-local time? | No official documentation found either way | Doesn't block the design — the poll-and-self-check pattern (D10a) is correct regardless of the answer, this only affects how the scheduler itself gets configured |
| Does Robinhood Agentic honor its declared client idempotency key across retries and ambiguous outcomes? | The current `place_equity_order` schema advertises an optional UUID `ref_id` and directs clients to reuse it for the same logical order; no live deduplication test has been run | Determines whether strict at-most-once submission is possible; without proven behavior D16 still requires fail-closed reconciliation for ambiguous outcomes |

Resolve the broker and scheduler questions in Phase −1, before building an integration that assumes their answers. Cost-only questions may remain provisional, but no live funding happens while a correctness-critical answer is unknown.

**Lower-priority, deferred:** the following are known open items, deliberately not resolved now — revisit once Phase 1 (paper/shadow) is generating real data rather than speculating ahead of it.

- **Model version drift across cloud-scheduled routines.** Account A/B's Decision Runs go through Claude Code's / Codex's own cloud scheduling; if either resolves to a `latest`-style model alias rather than a pinned model ID, a provider-side model upgrade could silently change one side of the comparison mid-run without an explicit decision to do so. `model_config_version` records a version label but doesn't by itself guarantee the alias is pinned. Low priority because it doesn't block Phase −1/0, but should be checked before Phase 1 begins accumulating comparison data.
- **Analyst confidence-calibration sample size.** The Baseline & benchmark section calls for per-analyst reliability diagrams, but no minimum sample size has been set for when ~8 weeks × 3 analysts × ~15–18 symbols is actually enough data to draw a meaningful calibration curve versus noise. Low priority because it only affects how the calibration reporting is interpreted, not the trading/risk mechanics; worth pinning down as part of D18's pre-registered evidence criteria before Phase 1's results are read.

## Explicitly out of scope for v1

- Schwab/Fidelity integration and a multi-broker weekly report — the recurring operational load (OAuth renewal, manual CSV export) conflicts with the zero-ops constraint.
- The Codex-style "shared-account multi-strategy" virtual ledger (which strategy owns which symbol, no silent netting, ledger-vs-broker reconciliation invariants) — each live strategy has its own account, so this conflict-resolution machinery isn't needed. The only ledger that exists is the lightweight one for the two shadow lines, which never touches real money and needs no conflict handling.
- Tax-lot management (specific lot selection, long/short-term gain optimization) — out of scope for a learning project. (Wash-sale detection is *not* excluded — see the risk layer, above.)
- Intraday/higher-frequency trading — conflicts with the zero-ops constraint, revisit only as a deliberate Phase 3 decision.
- Debate-style multi-agent architecture — left for a future ablation, not in v1.
- VWAP/TWAP or other sophisticated execution algorithms — Phase 0 defaults to single limit/marketable-limit orders (D3a) unless portfolio size or measured slippage clearly requires more.
- The Execution Agent independently re-deriving an investment view — it may only execute/abort/scale/reject an already-persisted OrderPlan, never re-run analyst/PM reasoning or change direction because "its view changed."
- Shadow candidates graduating automatically — graduation always requires the D5a gate plus a human approval; the system can never open an account or deposit funds on its own.

## Boundaries

Claude (in any interface) is responsible for design, code, backtesting tools, and the reporting pipeline; it does not execute trades, hold credentials, or give buy/sell advice on specific securities. Live trading decisions and their consequences are Alicia's alone. All API keys / broker credentials live only in approved secret stores or a scheduler's secret mechanism appropriate to their lifecycle — never in the repo, and never in plaintext in an `OrderPlan` or a log. A credential that rotates must use a store that can atomically write the replacement; a static environment variable alone is not sufficient.
