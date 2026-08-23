# Architecture

This is the current state of the system design. It's a living document — when the design changes, this file is edited in place to describe the new current state; the *history* of why it changed belongs in `docs/DECISIONS.md`, not here.

## Positioning

The initial $500–1000 per live account is a deliberately small real-money validation allocation, not a fixed lifetime ceiling or merely an amount to play with. The goals are:

1. Learn agent-system design by shipping one small-account system with isolated Decision and Execution Routines plus deterministic, inspectable risk calculations.
2. Find out whether a multi-agent architecture (3 analysts + PM) and a specific model choice actually add value over a simple deterministic strategy and over doing nothing (passive holding) — which requires a genuinely comparable baseline running alongside the live accounts, not just the agent on its own.
3. Preserve the option to increase an account's funding if live evidence later shows stable, attributable profitability after costs and within the risk rules. Any increase is an explicit human decision, not an automated response to recent performance; its amount and evidence threshold must be reviewed before the increase.

**Hard constraint: ship quickly with low routine operational load.** The first release deliberately uses the hosted LLM platform's scheduler, repository access, and Robinhood MCP credential lifecycle instead of building a separate runtime. The owner monitors the small-account canaries. D27 accepts extending D26 to exactly two small accounts without adding hardening infrastructure. Before funding is increased or a third account is added, those execution risks must be reviewed again.

**Production v1 scope:** exactly two Robinhood Agentic account lanes. Each lane has its own configuration, state root, Decision Routine, Execution Routine, platform-managed broker connection, and human-controlled live gate. Both reuse the same CLI and deterministic risk scripts. A dedicated non-LLM executor, transactional storage, self-managed OAuth, analyst ensemble, statistical comparison harness, and shadow strategies are later work.

The account seam remains intentionally small: one command invocation resolves exactly one account configuration and writes below that account's state root. `config/mvp.json` remains Account A for backward compatibility; `config/mvp-account-b.json` adds Account B. There is no `accounts[]` schema, batch coordinator, credential abstraction, strategy-plugin framework, or shared ledger. The operator or hosted scheduler invokes the same command once per lane. A third account requires another architecture review.

## System architecture: decision and execution are separate stages

**Core principle:** when to decide (a target portfolio) and when to execute (place real orders) are different problems. Decision timing is governed by information availability — the day's closing data isn't final until after close. Execution timing is governed by market liquidity and execution quality — the first few minutes after open have the thinnest liquidity and widest spreads. A signal being generated after close does not imply the resulting order should be submitted after close.

### Daily timeline (US Eastern Time)

Production v1 runs this timeline independently for each configured account lane. The two lanes may share the same frozen market-data facts, but there is no cross-account runtime coordinator: one lane's command, files, broker calls, and failure state do not authorize work in the other lane.

**Timezone handling:** none of the triggers below are a fixed UTC cron time. The scheduler polls every 5–10 minutes inside a loose window around the target time; the script itself computes the real current time in `America/New_York` and no-ops if it isn't inside the window yet. See D10a in `docs/DECISIONS.md` for why.

```
4:00 PM ET   Market close
4:00–9:00    Wait — earnings and other market-moving news often come out after the close
             (sometimes hours after), so the gap gives that information time to land before
             the day's decision is made, rather than analyzing a still-incomplete picture
9:00–9:10 PM ET   Decision Runs (Account A, then Account B):
             It does:
             1. Start a fresh Decision Routine without broker write tools
             2. Gather the allowed inputs and produce a target portfolio
             3. Run deterministic risk and sizing scripts
             4. Write one immutable-per-cycle OrderPlan file
             5. Append a compact JSONL decision record and push both to the private repository

Overnight    No trading. The persisted OrderPlan is not touched.

~9:35–9:45 AM ET  Execution Runs (Account A, then Account B):
next day     1. Pull and load yesterday's published OrderPlan
             2. Read current positions, cash, price, mode, and risk configuration
             3. Run deterministic revalidation scripts
             4. In dry_run, record the proposed actions without broker writes
             5. In live mode, review/place only the allowed orders through Robinhood MCP
             6. Append compact JSONL results and push them to the private repository
```

Why separate decision and execution runs: execution happens after the market opens, while the decision uses completed Day T information. Starting ~9:35 rather than exactly 9:30 avoids the most volatile opening minutes. Account B runs ten minutes after Account A to avoid ordinary Git push collisions without introducing a coordinator. Fresh isolated sessions also keep news and thesis material out of sessions that own broker write tools. This is a capability and prompt boundary, not a code-enforced security boundary.

### DecisionSnapshot, OrderPlan, and execution state

The production-v1 lane reads one immutable `DecisionSnapshot`. It contains the allowed market inputs, universe, and as-of timestamps used for that decision. The exact prompt/config hash, resolved model identifier, runtime version, and tool versions are recorded alongside it. News/fundamental enrichment and shared snapshots for comparison lanes are later additions; neither blocks the three-day MVP.

The initial deterministic-core module accepts a strict snapshot envelope containing `snapshot_id`, timezone-aware `as_of`, a non-empty unique `universe`, and JSON-only `inputs`. It recursively detaches and freezes the document at creation, rejects unknown envelope fields, and only exports a fresh mutable copy for serialization. Feed-specific schemas inside `inputs`, canonical content hashing, and object-store persistence remain later Phase 0 work; the minimal envelope is not treated as proof that those contracts are complete.

The output of the decision stage is a persisted, **immutable once written** `OrderPlan`:

```yaml
order_plan_id: uuid
decision_time: 2026-08-21T21:05:00-04:00     # ET
account_id: account_A                          # account_B / shadow:mean_reversion / shadow:spy_qqq / shadow:candidate_C ...
model_config_version: config_A_v3              # for reproducibility
decision_snapshot_id: uuid
market_snapshot_as_of: 2026-08-21T21:00:00-04:00

account_baseline:                              # credential-free reconciliation fact
  cash: "850.00"
  positions:
    AAPL: "1.5"

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
    market_hours: regular_hours
    time_in_force: gfd
```

The deterministic-core `OrderPlan` module enforces the strict top-level fields illustrated above, recursively freezes `account_baseline`, `target_portfolio`, and `orders`, and accepts only positive share-quantity `LIMIT`, `regular_hours`, `gfd` orders. The baseline is captured separately from the shareable market `DecisionSnapshot`. Because arbitrary nested objects are not accepted, execution outcomes cannot be smuggled into the decision document. Tax lots remain out of scope for v1. D23 fixes persisted numbers as base-10 decimal strings.

Once generated, the Execution Routine is instructed to do only four things: **execute as-is / abort the whole plan / scale down against deterministic limits / reject specific orders because risk or account state changed**. A configured stop-loss/take-profit may additionally emit a deterministic full-position market SELL Risk Exit for an existing holding; this is risk authority, not investment reasoning. The routine must not otherwise change direction or invent a trade. In v1 this is enforced by session isolation, tool scoping, strict files, and deterministic scripts—not by a non-LLM process boundary. D26 records that limitation.

Execution results do not mutate the plan. V1 appends compact JSONL records that preserve the original and actual quantities and any applied rule. The existing `ExecutionEvent` value object remains a useful schema for later hardening, but production v1 does not claim transactional append-only persistence, complete transition validation, or crash-safe submission state.

The initial `ExecutionEvent` value object has a strict seven-field envelope, finite kind-specific payloads, detached immutable serialization, downward-only adjustment values, and credential-free URI plus SHA-256 evidence pointers. It is repository evidence and a future hardening seam; wiring it to a transactional repository is explicitly deferred.

- Allowed: a symbol gaps overnight beyond the tolerance threshold → the execution guard rejects that order.
- Not allowed: the Decision Routine planned a buy yesterday, and the Execution Routine decides today it dislikes the symbol and sells it instead.

If a plan is aborted, the system waits for the next normal decision run — it never catches up or re-submits a stale plan.

**Production-v1 trade-off:** execution is an LLM session. The Decision Routine must not have broker write tools; the separately scheduled Execution Routine may have the narrow Robinhood review/place/cancel tools. Deterministic scripts calculate constraints, but the routine still interprets their output and constructs the tool call. Wrong arguments, duplicate calls, ambiguous timeouts, crash-before-log windows, config misuse, prompt injection, and model/prompt drift are accepted for the two initial small allocations. They are not acceptable by default for increased capital or an additional account.

### Production-v1 storage responsibilities

Production v1 deliberately has only two continuity mechanisms:

| Storage | Holds | Required behavior |
|---|---|---|
| Private Git repository | Code, config, one per-cycle OrderPlan file, compact JSONL decision/execution records, and sanitized reports | Pull before a run; commit and push after a run; never force-push over a conflict. A push failure is reported and the next run stops until repository state is understood. |
| Hosted platform MCP connection | Robinhood OAuth state and account authorization | The platform owns storage and refresh. Credentials, tokens, cookies, and raw authenticated responses never enter Git, prompts, plans, or logs. Reconnect is a human platform operation if the connection expires. |

This is intentionally not a transactional trading journal. Git does not close the interval between a successful broker call and a later log commit, and it does not provide a lease across multiple schedulers. Production v1 therefore permits exactly one Decision scheduler and one Execution scheduler per account lane and accepts the remaining crash, duplicate, and ambiguity risks under D26/D27. Every lane writes beneath a distinct account-scoped state root.

### Execution-time revalidation and abort conditions

The Execution Routine's job before placing an order is checking "does last night's decision still hold today," not making a new decision:

| Check | Trigger | Action |
|---|---|---|
| Account state reconciliation | Current positions/cash don't match what the OrderPlan assumed | Abort the plan, log the discrepancy, notify (rare event) |
| Price tolerance | Open price vs. `reference_price_at_decision` exceeds `price_tolerance_pct` | Abort that order — no chasing the price, no re-reasoning, wait for the next decision run |
| Available cash / buying power | Aggregate BUY cost at worst-case limit fills exceeds cash | Reserve cash in plan order and scale down or reject the excess, then log it |
| Risk layer re-check | Re-run today's account equity through the risk rules (e.g. overnight equity change pushes an order past the 20% position cap) | Clip or reject, same logic as the risk layer itself |
| Data freshness | Current quotes/account state unavailable (API failure etc.) | No trade, log and notify, wait for the next cycle |

**Existing-position stop-loss/take-profit recheck, independent of the day's OrderPlan:** every Execution Run also re-evaluates stop-loss/take-profit conditions on *all currently held positions* in that account, regardless of whether there's a new decision today or how compelling a new thesis sounds. Any triggered stop-loss/take-profit fires immediately per the risk layer rules. (See `docs/DECISIONS.md` D13 — this closes a gap found while reviewing FriesTrader.)

Tier-two drawdown writes an account-scoped `risk/drawdown_tier2.lock.json`. New BUYs stay blocked across later cycles until a human reviews the account and removes the lock; recovery in equity does not silently restart entries. Risk-reducing exits remain available.

### Idempotency

Production v1 uses best-effort duplicate reduction, not exactly-once or crash-safe at-most-once execution:

- each OrderPlan and planned order gets a stable ID;
- the Execution Routine checks the committed JSONL records and visible broker history before placing an order;
- only one scheduler is configured for each routine;
- an MCP timeout or malformed response ends the current run rather than causing an immediate blind retry;
- after a timeout or crash, the owner checks Robinhood before the next scheduled run.

These guards do not close a crash-after-acceptance/before-log window and cannot guarantee that an LLM will never issue the same tool call twice. D26/D27 accept that risk for the two initial small allocations. A capital increase or third account requires another architecture review of transactional submission state, broker idempotency, and non-LLM execution.

### Look-ahead bias: backtest/live timing must match

**Rule:** if a signal was generated using Day T's closing price or other end-of-day data, neither a historical backtest nor a paper/live performance calculation may assume the fill happened at Day T's close. It must be modeled as filling near Day T+1's open.

- Wrong: signal generated from a $220 close on Day T → backtest assumes a fill at $220.
- Correct: signal generated at Day T close → fill modeled at T+1 open (or shortly after).

This applies equally to the shadow pool's bookkeeping (see Baseline & benchmark, below): the mean-reversion baseline, SPY/QQQ, and any future candidate must mark their virtual fills at the **T+1 open price**, never at the signal day's own close — otherwise the baseline would have an information advantage the live accounts don't get, and the comparison would be unfair. Any historical backtest built later (e.g. to tune the mean-reversion strategy) must follow the same timing semantics so backtest and production behave consistently.

### Eventual comparison topology

The following diagram describes the later full comparison target. Production v1 implements only two independent vertical lanes over the same concrete modules; it does not yet implement analyst ensembles, a comparison coordinator, or the shadow pool.

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

**Future comparison constraints (Phase 3, not production-v1 work):**

- A future analyst output schema may use `{ticker, direction, score∈[-1,1], confidence∈[0,1], rationale}`, fully logged and tagged with `account_id` and `order_plan_id`. Production v1 does not implement the three-analyst composition.
- The two live accounts are fully independent: separate risk-layer instances, separate execution-adapter calls, separate broker statements. No shared account, so none of the "shared-account multi-strategy" conflict-resolution machinery is needed.
- The shadow pool is a lightweight `strategy_ledger`: each candidate runs a Decision Run and produces an OrderPlan, but there's no Execution Run/broker involved — a virtual fill simulator marks fills at the T+1 open price. It never calls the execution adapter or touches a real account, so it never has a capital-conflict problem, and stays far lighter than a full shared-account ledger. The pool being open just means adding a candidate is registering a new record, not an architecture change.
- Shadow-to-live graduation is the only path that grows the number of live accounts (see D5a). Existing live accounts may receive a manually approved funding increase after a separate profitability and risk review (see D14). The system never opens an account, deposits capital, or raises an account's allocation on its own.
- Risk-layer split: rules in a prompt are *advisory*; rules in code are *binding*. Each account context owns its risk state (today's order count, current drawdown).
- A future comparison release may introduce a virtual fill simulator. Production v1 dry-run simply records proposed calls, while live mode uses Robinhood MCP after ~9:35am. No generic broker-plugin framework is built.

## Risk calculations and execution guardrails

Production v1 computes every rule below in deterministic scripts against the configured account's own equity. The Execution Routine is required to use those results. The v1 architecture does not technically prevent the routine from misreading or bypassing them; that accepted limitation is explicit in D26.

| Rule | Value | Action when triggered |
|---|---|---|
| Max position per symbol | 20% of the account's own equity | Clip the order to the cap |
| Max new positions per day | 3 per account | Excess orders are dropped and logged |
| Daily loss circuit breaker | −5% (unrealized + realized, against the account's own equity) | No new positions for the rest of the day; closing positions still allowed |
| Drawdown tier 1 | −10% from the account's high-water mark | Block new positions, generate a notification (the one case worth glancing at) |
| Drawdown tier 2 | −15% from the account's high-water mark | Disable new entries and require manual restart; deterministic risk-reducing exits remain available. |
| Prohibited (v1) | Shorting, leverage, options | Rejected at the adapter layer |
| Wash-sale guard | 30-day lookback (configurable); the IRS rule applies per taxpayer, not per account | Blocks buys only (new entries/top-ups) — never blocks a stop-loss/take-profit/exit sell. Each lane's `loss_sales` input includes visible sales from both configured accounts; missing linked-account history fails closed for new buys. |

Every intercepted/clipped instruction is logged as `{original instruction, rule triggered, actual action, account_id}`.

**Wash-sale guard's known limitation:** this only covers accounts and trades this system can see. If a repurchase happens in an account outside the system's control, it can't be prevented — that risk is on the human to track, not this system's responsibility.

**Low-ops relationship:** hosted schedules and compact reports handle routine operation. The owner checks failed runs, repository conflicts, MCP reconnection requests, ambiguous broker outcomes, and material drawdown during the small-account canary.

**Kill switch, honestly stated:** `execution.mode` is a human-owned repository setting read by both routines. Setting it to `disabled` stops new plans and instructs the Execution Routine to cancel visible pending orders without submitting new ones. This is prompt- and process-mediated, not an instantaneous broker-side kill switch. Existing positions still require ordinary sell orders or manual action.

## Deferred baseline & benchmark (Phase 3)

The following comparison design remains the later target. It is not on the production-v1 implementation path.

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

For production v1, D26 supersedes the former eight-week pre-live gate and D25 runtime: one complete scheduled dry-run cycle is the minimum observation period. Eight continuous live weeks permit a capital review, but do not waive the required D26 architecture review before increasing funds. D18's comparison rules remain later work.

## Delivery plan and release gates

1. **Development day 1 — deterministic core:** implement only the fixed-universe sizing and risk scripts required by the first strategy, with small fixture tests.
2. **Development day 2 — Decision Routine:** define its narrow prompt/tool contract and produce one strict per-cycle OrderPlan plus JSONL decision record in the private repository.
3. **Development day 3 — dry-run MVP:** define the isolated Execution Routine, run risk revalidation in `dry_run`, append results, and prove one scheduled Day T → Day T+1 cycle without broker writes.
4. **Live connections:** bind one platform-managed Robinhood MCP connection to each account's Execution Routine, verify explicit account selection plus read/review/place/cancel behavior with the smallest safe probes, and configure exactly two schedules per lane.
5. **Production-path dry-run cycles:** observe each lane's Decision and Execution Routines and resolve any plan, account-binding, tool, schedule, or repository failure.
6. **Small-account live activation:** Alicia explicitly changes one lane's `execution.mode` to `live` after reviewing that lane's dry cycle. The second lane is enabled independently after its own account binding and dry cycle. Credentials stay in platform connections; the repository remains private and credential-free.
7. **After eight continuous live weeks:** review after-cost performance, drawdown, operational failures, and every D26 accepted risk. A capital increase requires a new architecture decision; it is never automatic.
8. **Later expansion:** before a third account, richer model-comparison orchestration, or larger capital, perform another architecture review based on observed operation.

## Deployment scheduling reliability

### Broker OAuth credential lifecycle

Production v1 delegates OAuth storage, refresh, and reconnection to the hosted platform's Robinhood MCP connection. Ripple neither reads nor persists token material. If the platform reports that authorization is missing or expired, the run stops and Alicia reconnects it interactively in the platform. The completed local Python/Keychain OAuth work remains feasibility evidence and a possible future non-LLM executor path, not launch-critical code.

The hosted scheduler starts a fresh session for each run. The command checks the real `America/New_York` time and intended document date before acting. Exactly one Decision schedule and one Execution schedule may be enabled per account lane. Git history and stable plan IDs reduce accidental repeats, but there is no cross-runner transactional lease in v1.

Repository Python commands target Python 3.12, selected by the root `.python-version` file. Hosted routines run scripts through the repository's declared environment; current Codex Automation probes use `uv run --no-cache` where required by that sandbox.

If the Execution Run is delayed, the price-tolerance script should reject stale orders. Failed or missed cycles are not backfilled.

## Cost model

| Item | Estimate | Note |
|---|---|---|
| Decision and Execution Routines | ~$0/month marginal while subscription/hosted allowance remains | Measure actual usage; any metered fallback is explicit and budget-capped |
| Private Git repository | Existing plan | Stores credential-free continuity records and reports |
| Platform-managed Robinhood MCP | Platform-dependent | OAuth lifecycle is delegated to the connected hosted platform |
| Market data | $0 | yfinance / Alpaca free tier |
| News/fundamental data, primary (D19) | $0 | Free/open sources — Yahoo Finance, Google Finance, Fidelity public pages |
| News/fundamental data, X supplement | $0 | Excluded from v1 by D19; no X integration or credential is provisioned |
| **Monthly total** | **Primarily hosted-model/API usage** | No dedicated Mac runtime, database, or custom OAuth service is required for v1 |

One-time/capital items (not part of the monthly figure): each production-v1 account may initially receive $500–1000 after its own dry-run gate, for total initial exposure of $1000–2000 when both are live. Each allocation is fully at risk of loss. If later evidence supports an increase, Alicia may approve it manually; the system never scales capital automatically.

When broker responses expose them, trading costs, fills, and result IDs are copied into credential-free records and kept separate from P&L. Production v1 does not claim complete automatic reconciliation.

## Open questions (need hands-on verification, not assumed from documentation)

| Question | Basis so far | Why it matters |
|---|---|---|
| Can the selected hosted routine expose the Robinhood MCP connection reliably in scheduled fresh sessions? | Interactive/local probes proved the MCP schemas and account reads; hosted scheduled write-path behavior has not yet been observed | Must be proven with a complete scheduled dry run and the smallest safe live connection probes |
| Can two Robinhood Agentic accounts each bind an independent hosted MCP connection? | Robinhood allows multiple self-directed investing accounts, but the account-to-agent relationship isn't documented | Must be verified before Account B live activation; it does not block two-account repository dry-run support or Account A operation |
| Does live Robinhood behavior honor explicit account selection and the declared fractional/dollar-order shapes? | The current review/place/cancel/history schemas require `account_number`; review/place declare share-or-dollar inputs and regular-hours market-only fractional support up to six decimals. No live eligibility or routing test has run. | Small validation accounts and account isolation depend on this |
| What is the real token/context footprint and rejection rate for the one production-v1 decision call? | Official vendor docs confirm variable shared subscription allowances and metered automation paths; no fixed capacity is promised. The checked-in routine contract exists, but its hosted usage has not been measured. | Determines the explicit API fallback budget and whether monitored subscription runs are operationally sufficient |
| Do Claude Code's / Codex's cloud scheduling features natively support IANA timezones, or only UTC/browser-local time? | No official documentation found either way | Doesn't block the design — the poll-and-self-check pattern (D10a) is correct regardless of the answer, this only affects how the scheduler itself gets configured |
| Does Robinhood Agentic honor its declared client idempotency key across retries and ambiguous outcomes? | The current `place_equity_order` schema advertises an optional UUID `ref_id`; no live deduplication test has run | Deferred under D26 for the small-account launch; must be revisited before capital or account expansion |

Resolve hosted MCP availability, explicit account selection, and declared order shape before enabling live mode. The accepted D26 ambiguity and LLM-execution risks are not launch blockers for the initial allocation; they become mandatory review items before scaling.

**Lower-priority, deferred:** the following are known open items, deliberately not resolved now—revisit once the two concrete account lanes are generating real data rather than speculating ahead of it.

- **Model version drift across cloud-scheduled routines.** The production-v1 Decision Run must record the resolved model identifier. Whether later comparison lanes can pin model aliases is deferred to Phase 3.
- **Analyst confidence-calibration sample size.** The Baseline & benchmark section calls for per-analyst reliability diagrams, but no minimum sample size has been set for when ~8 weeks × 3 analysts × ~15–18 symbols is actually enough data to draw a meaningful calibration curve versus noise. Low priority because it only affects how the calibration reporting is interpreted, not the trading/risk mechanics; worth pinning down as part of D18's pre-registered evidence criteria before Phase 1's results are read.

## Explicitly out of scope for v1

- Schwab/Fidelity integration and a multi-broker weekly report — the recurring operational load (OAuth renewal, manual CSV export) conflicts with the zero-ops constraint.
- The Codex-style "shared-account multi-strategy" virtual ledger (which strategy owns which symbol, no silent netting, ledger-vs-broker reconciliation invariants) — each live strategy has its own account, so this conflict-resolution machinery isn't needed. The only ledger that exists is the lightweight one for the two shadow lines, which never touches real money and needs no conflict handling.
- Tax-lot management (specific lot selection, long/short-term gain optimization) — out of scope for a learning project. (Wash-sale detection is *not* excluded — see the risk layer, above.)
- Intraday/higher-frequency trading — conflicts with the zero-ops constraint, revisit only as a deliberate Phase 3 decision.
- Debate-style multi-agent architecture — left for a future ablation, not in v1.
- A plain non-LLM execution service, SQLite or another transactional journal, leases, exactly-once submission, and automated ambiguous-outcome reconciliation — deliberately deferred for the initial small-account canary under D26.
- A self-managed Robinhood OAuth client or credential store — the hosted platform connection owns credential lifecycle in v1.
- VWAP/TWAP or other sophisticated execution algorithms — Phase 0 defaults to single limit/marketable-limit orders (D3a) unless portfolio size or measured slippage clearly requires more.
- The Execution Routine independently re-deriving an investment view — it may only execute/abort/scale/reject an already-persisted OrderPlan, never re-run investment reasoning or change direction because "its view changed."
- Shadow candidates graduating automatically — graduation always requires the D5a gate plus a human approval; the system can never open an account or deposit funds on its own.

## Boundaries

The hosted Decision Routine produces the proposed trade plan but has no broker write capability. The hosted Execution Routine may place trades through the platform-managed Robinhood MCP connection after deterministic scripts and mode checks. It must not receive news or thesis material or invent a trade outside the published OrderPlan. Alicia owns the live-mode decision, funding, and consequences. Credentials remain only in the platform connection—never in Git, prompts, plans, reports, or logs.
