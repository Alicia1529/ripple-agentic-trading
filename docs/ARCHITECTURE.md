# Architecture

This is the current state of the system design. It's a living document — when the design changes, this file is edited in place to describe the new current state; the *history* of why it changed belongs in `docs/DECISIONS.md`, not here.

## Positioning

The initial $500–1000 per live account is a deliberately small real-money validation allocation, not a fixed lifetime ceiling or merely an amount to play with. The goals are:

1. Learn agent-system design by building a complete "untrusted LLM decision layer + deterministic code-enforced risk layer" system.
2. Find out whether a multi-agent architecture (3 analysts + PM) and a specific model choice actually add value over a simple deterministic strategy and over doing nothing (passive holding) — which requires a genuinely comparable baseline running alongside the live accounts, not just the agent on its own.
3. Preserve the option to increase an account's funding if live evidence later shows stable, attributable profitability after costs and within the risk rules. Any increase is an explicit human decision, not an automated response to recent performance; its amount and evidence threshold must be reviewed before the increase.

**Hard constraint: zero routine operational load.** The person running this expects near-zero ongoing maintenance time going forward. The system must run unattended after deployment and only ever interrupt for rare, high-stakes events (a risk breaker firing, a shadow candidate clearing the graduation gate, or a live account becoming eligible for a capital review) — never for routine chores like manual reconciliation, manual CSV exports, manually confirming each trade, or manual credential renewal. This constraint has been explicitly checked against the two-live-account + open shadow-pool design below and confirmed compatible: every human touchpoint in this document is rare and high-stakes, not routine. See `docs/DECISIONS.md` D1, D2, D2c, and D14 for how this constraint shaped the scope.

**Scope:** two live Robinhood Agentic accounts running the same 3-analyst + PM architecture with different model configurations (a live A/B comparison of model capability), plus an open shadow incubation pool (starting with a mean-reversion baseline and SPY/QQQ buy-and-hold, extensible with new candidates) that can graduate into a new live account under an explicit, human-approved gate.

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
             1. Market data snapshot
             2. Analyst agent(s) produce signals/expected returns (own model config)
             3. Portfolio manager produces a target portfolio
             4. Risk engine validates constraints (see Risk layer, below)
             5. Order planner turns the target portfolio into concrete orders
             6. Persist the OrderPlan (see below), commit/push it to the repo, status = pending

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
             8. Persist execution results/logs, commit/push to the repo
```

Why two separate runs: execution always happens after the market has opened, so there is no dependency on how Robinhood Agentic's order tools behave while the market is closed. ~9:35 rather than exactly 9:30:00 avoids the thinnest-liquidity, widest-spread minutes right at open. Phase 0 favors deterministic, debuggable behavior over sophisticated execution — no VWAP/TWAP. Separating decision from execution also makes post-mortems clean: a bad outcome is either "the call was wrong" or "the price moved before execution," never both tangled together — and it's what makes backtests able to share the same timing semantics as production (see Look-ahead bias, below).

### OrderPlan data model

The output of the decision stage is a persisted, **immutable once written** `OrderPlan`:

```yaml
order_plan_id: uuid
decision_time: 2026-08-21T21:05:00-04:00     # ET
account_id: account_A                          # account_B / shadow:mean_reversion / shadow:spy_qqq / shadow:candidate_C ...
model_config_version: config_A_v3              # for reproducibility
market_snapshot_as_of: 2026-08-21T21:00:00-04:00   # close-price data as of 4pm, snapshotted at 9pm to give post-close news/earnings time to land
status: pending                                 # pending -> executed | aborted | partially_executed

target_portfolio:
  AAPL: 15%
  MSFT: 10%
  ...
  cash: 20%

orders:
  - order_id: uuid
    symbol: AAPL
    side: BUY
    qty: 12
    order_type: LIMIT
    limit_price: 227.50              # decision-time price + D3a tolerance band
    price_tolerance_pct: 0.5%        # used at execution time to detect an excessive gap
    reference_price_at_decision: 226.40
```

Once generated, the Execution Agent may only: **execute as-is / abort the whole plan / scale down proportionally against available cash / reject specific orders because risk or account state changed**. It may never re-run analyst/PM reasoning or change direction because "its view changed today" — that would be tampering with an already-made decision, which breaks reproducibility, auditability, and attribution.

- Allowed: a symbol gaps overnight beyond the tolerance threshold → the execution guard rejects that order.
- Not allowed: the PM decided to buy NVDA yesterday, and the Execution Agent decides today it doesn't like NVDA anymore → sells it.

If a plan is aborted, the system waits for the next normal decision run — it never catches up or re-submits a stale plan.

**Execution must not be an LLM session.** This is also why the Decision-stage LLM session must never hold a tool capable of placing a live order. If the model reasoning about the trade also holds the tool that executes it, "risk rules live only in code, never in a prompt" (see Risk layer) degrades into "the prompt tells the model to behave," no matter how deterministic the risk math itself is. The Execution Run is plain, non-agentic code — an MCP client or direct broker API call, not an LLM inference loop — precisely so this guarantee holds regardless of which model powered the decision.

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

The window-polling scheduler (see Timezone handling, above) means a Decision or Execution Run could in principle be triggered more than once inside the same target window — a crash-and-restart, an overlapping poll, or a scheduler retry. Nothing about "poll every 5–10 minutes and no-op outside the window" by itself prevents *two* in-window triggers from both doing real work, so idempotency has to be handled explicitly, not assumed:

- Every order's `order_id` (see OrderPlan data model, above) is generated exactly once, at Decision Run time, and persisted with the plan — it is never regenerated on a later attempt.
- Before running the full analyst/PM pipeline, a Decision Run checks whether that account already has a plan for today's decision date; if so, it no-ops rather than generating a second, possibly different plan.
- Before submitting any order, an Execution Run checks its own persisted execution state for that specific `order_id` and skips it if already marked submitted/filled. State is persisted immediately after each individual order is submitted — not batched at the end of the plan — so a mid-plan crash resumes from the right order instead of resubmitting ones that already went through.
- `order_id` is passed to the broker as the client order id / idempotency key if the order-placing tool accepts one (unconfirmed for Robinhood Agentic specifically — see Open Questions, below), as a second line of defense on top of the local state check.
- A simple single-flight guard (an "already running" marker checked at the start of each invocation) prevents two overlapping triggers within the same polling window from both acting at once.

This is what makes "at most once" actually true rather than just intended — see `docs/DECISIONS.md` D3c.

### Look-ahead bias: backtest/live timing must match

**Rule:** if a signal was generated using Day T's closing price or other end-of-day data, neither a historical backtest nor a paper/live performance calculation may assume the fill happened at Day T's close. It must be modeled as filling near Day T+1's open.

- Wrong: signal generated from a $220 close on Day T → backtest assumes a fill at $220.
- Correct: signal generated at Day T close → fill modeled at T+1 open (or shortly after).

This applies equally to the shadow pool's bookkeeping (see Baseline & benchmark, below): the mean-reversion baseline, SPY/QQQ, and any future candidate must mark their virtual fills at the **T+1 open price**, never at the signal day's own close — otherwise the baseline would have an information advantage the live accounts don't get, and the comparison would be unfair. Any historical backtest built later (e.g. to tune the mean-reversion strategy) must follow the same timing semantics so backtest and production behave consistently.

### System diagram

```
Shared market data snapshot (one as_of timestamp, shared by both accounts + the shadow pool — decisions stay independent)
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
   Fill Monitoring -> Position Reconciliation -> Audit/Metrics/Logs (independent per account, no cross-effects)
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
| Drawdown tier 2 | −15% from the account's high-water mark | That account shuts down entirely, requires manual restart; the other account is unaffected and keeps running independently |
| Prohibited (v1) | Shorting, leverage, options | Rejected at the adapter layer, both accounts |
| Wash-sale guard (cross-account) | 30-day lookback (configurable); the IRS rule applies per taxpayer, not per account | Blocks buys only (new entries/top-ups) — never blocks a stop-loss/take-profit/exit sell, since risk management never defers to a tax outcome. A blocked buy is logged and flagged for year-end tax reference. Checked across a configurable `linked_accounts` list covering both live accounts |

Every intercepted/clipped instruction is logged as `{original instruction, rule triggered, actual action, account_id}`.

**Wash-sale guard's known limitation:** this only covers accounts and trades this system can see. If a repurchase happens in an account outside the system's control, it can't be prevented — that risk is on the human to track, not this system's responsibility.

**Zero-ops relationship:** everything above runs unattended except the once-a-month allowlist review. A notification only fires on the rare events — a 10%/15% drawdown breaker, or a shadow candidate clearing its graduation gate — which are safety valves, not routine operations. If the system behaves as designed, expect to receive close to zero actionable notifications through Phase 1/2.

**Kill switch, honestly stated:** Robinhood's own documentation does not describe an instant "flatten everything" kill-switch capability — only the ability to cancel a pending order, and it explicitly notes an agent may be "difficult to monitor or stop in real time." This system's "kill switch" means: a code-level flag that immediately stops generating new orders and cancels all pending ones; existing positions still need to be unwound through normal sell orders, not instantly zeroed. This limitation is documented in code comments and the runbook rather than overclaimed.

## Baseline & benchmark

The periodic report (auto-generated, not manual work) compares, starting with four lines and growing as the shadow pool gains candidates:

1. **Account A curve** — Model Config A's live, real-money equity after risk layer A.
2. **Account B curve** — Model Config B's live, real-money equity after risk layer B.
3. **Mean-reversion baseline curve** — same universe, same market snapshot, a simple deterministic rule (e.g. reverse-enter when price deviates from its N-day mean beyond a threshold), fills marked at T+1 open by the virtual fill simulator, uninfluenced by any LLM.
4. **SPY/QQQ buy-and-hold curve** — an equal-dollar buy of SPY and QQQ starting the day the live accounts began trading, held since, also marked at T+1 open, pure bookkeeping, no orders placed.
5. **(open) Shadow candidate curves** — one per candidate added to the pool later, pure virtual bookkeeping, continuously checked against the 8-week graduation gate (D5a).

What this measures:

- **Model-choice gain:** Account A vs. Account B — identical analyst design, risk layer, and universe, differing only in model, so the gap is model capability. This is the central learning target of the current scope.
- **Agent-architecture gain:** Account A/B vs. the mean-reversion baseline — whether multi-agent decision-making beats a simple rule at all.
- **Active-management gain:** accounts and baseline vs. SPY/QQQ buy-and-hold — whether the whole system is worth doing relative to doing nothing.
- Per-analyst direction accuracy and confidence calibration (reliability diagrams), tracked per account.

Every comparison curve's computation is written once as code; none of it needs manual upkeep.

## Deployment scheduling reliability

GitHub Actions documents that scheduled jobs can be delayed under high load, and can even be dropped. This applies to the Execution Run and the shadow pool's Decision Run. Account A/B's Decision Runs sit on Claude Code's / Codex's own cloud scheduling, whose reliability is unverified (see Open Questions) — treated with the same conservative assumption (may be delayed, no assumption of exact-time triggering). These delays are tolerable for a low-frequency, once-daily cadence (a few minutes to an hour doesn't change the strategy logic); the system adds an automated check for "today's run didn't happen" that notifies rather than requiring a manual daily check.

If the Execution Run itself is delayed, the price-tolerance check (see above) provides natural protection: the longer the delay, the more likely the price has moved outside the tolerance band, so the system leans toward aborting rather than forcing a stale plan through. An abort just waits for the next normal decision run — no catch-up, no backfilled orders.

## Cost model

| Item | Estimate | Note |
|---|---|---|
| Account A's Decision Run (Claude) | ~$0/month marginal | Runs against an existing Claude Pro subscription; assumes the usage cap is sufficient (unverified, see Open Questions) |
| Account B's Decision Run (Codex/OpenAI) | ~$0/month marginal | Same, against an existing ChatGPT Plus subscription; Codex's exact pricing tier should be independently confirmed on openai.com |
| Deployment (GitHub Actions) | $0 | Free tier covers both live accounts' Execution Run and the shadow pool's Decision Run |
| Shadow pool LLM calls (metered API) | ~$0 for non-LLM strategies (e.g. mean reversion); roughly +$10–20/month per LLM-driven candidate added | The pool doesn't have a ready subscription the way the two live accounts do, so metered billing is used for whatever candidates need it — call volume in the validation stage is small |
| Market data | $0 | yfinance / Alpaca free tier |
| Alpaca paper | $0 | Free |
| **Monthly total** | **~$0–20/month marginal**, with a documented **ceiling of ~$60/month** if both subscriptions' usage caps turn out to be insufficient and Decision Runs fall back to metered API | The ceiling is a worst case, not the expected number |

One-time/capital items (not part of the monthly figure): both live accounts initially get $500–1000 in funding (total initial exposure $1000–2000), funded only in the live phase and fully at risk of loss. That range is the validation starting point, not a permanent cap. If an account later demonstrates stable, attributable profitability after trading costs and within the risk rules, Alicia may manually approve an appropriate funding increase after reviewing the evidence and risk impact; the system never scales capital automatically. Every shadow-to-live graduation likewise starts with its own $500–1000 allocation, individually approved by hand — there's no cap on the eventual number of accounts, only on how fast new accounts or larger allocations get approved.

Real trading costs (commission, spread, slippage, regulatory fees) are logged automatically per fill, kept separate from P&L — no manual reconciliation required.

## Open questions (need hands-on verification, not assumed from documentation)

| Question | Basis so far | Why it matters |
|---|---|---|
| Can two Robinhood Agentic accounts each bind an independent agent/API credential? | Robinhood allows up to 10 self-directed investing accounts, Agentic accounts included, but the account-to-agent relationship isn't documented | Needed for D2 (two accounts) to work as designed |
| Are Claude Pro's / ChatGPT Plus's usage caps enough for daily 3-analyst+PM traffic (4 calls/account/day)? | Only third-party pricing aggregators checked so far, not verified line-by-line against openai.com/anthropic.com | Needed for the "~$0 marginal cost" assumption; metered API is the documented fallback |
| Do Claude Code's / Codex's cloud scheduling features natively support IANA timezones, or only UTC/browser-local time? | No official documentation found either way | Doesn't block the design — the poll-and-self-check pattern (D10a) is correct regardless of the answer, this only affects how the scheduler itself gets configured |
| Does Robinhood Agentic's order-placing tool accept a client-supplied order id / idempotency key? | Not confirmed from official documentation | Affects how strong the idempotency guarantee is (D3c) — local execution-state tracking works regardless, but a broker-side idempotency key would be a second line of defense against duplicate live orders |

Resolve these with a small/paper-environment test before funding a live account.

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

Claude (in any interface) is responsible for design, code, backtesting tools, and the reporting pipeline; it does not execute trades, hold credentials, or give buy/sell advice on specific securities. Live trading decisions and their consequences are Alicia's alone. All API keys / broker credentials live only in environment variables, GitHub Actions secrets, or Claude Code's/Codex's own cloud-scheduling secret mechanisms — never in the repo, and never in plaintext in an `OrderPlan` or a log.
