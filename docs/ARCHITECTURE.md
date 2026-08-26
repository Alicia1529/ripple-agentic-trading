# Current architecture

This document describes Ripple as implemented today. Durable reasons belong in `docs/DECISIONS.md`; unfinished work belongs in `docs/TODO.md`.

Ripple is an account-catalog MVP for comparing isolated strategy lanes. `account_a` is a manual `dry_run` development lane and `account_b` is a fixture-backed `shadow` lane. The catalog and shadow execution path are implemented. Hosted schedules, Account A acceptance, and the reviewed live Robinhood broker-write loop remain unfinished.

Account A selects `growth_momentum_v3`. Its prose research, candidate rejections,
warnings, and thesis records remain immutable DecisionSnapshot evidence; its
actual intent still uses the shared OrderPlan schema.

## System at a glance

```text
strategies/<strategy_id>.md
             ▲
             │ selected by
config/<account_id>.json
             │
             ▼
       Account Catalog
  validates every config and strategy
  enforces at most one live lane
        ┌────┴─────┐
        ▼          ▼
   live cohort   shadow cohort       dry_run
     0..1          0..N              manual only
        │          │
        ├── Decision Routine(s), prior evening
        │      produce strategy-attributed immutable plans
        └── Execution Routine(s), next weekday
                     │
              deterministic risk
                ┌────┴────┐
                ▼         ▼
          live adapter  shadow adapter
          Robinhood     T+1 quote assumption
          after gate    no broker calls
```

The LLM supplies bounded fact gathering and investment judgment. Python validates configurations and artifacts, compiles source-attributed Growth Momentum facts, assigns stable IDs, performs deterministic risk calculations, and simulates Shadow Fills. The owner supplies broker binding, funding, live activation, restart, and strategy-switch decisions.

## Account Catalog interface

Every file matching `config/*.json` is one Account Lane. The filename stem is its canonical identifier and must be lowercase `snake_case`; there is no duplicated `account_id` field and no central `accounts[]` document.

```json
{
  "description": "Human-readable purpose, strategy, universe, and risk summary.",
  "strategy": "earnings_drift_v1",
  "execution": {"mode": "shadow"},
  "shadow": {"initial_cash": "1000"},
  "universe": ["AAPL", "SPY", "QQQ"],
  "risk": {}
}
```

`shadow.initial_cash` is required only for a shadow lane. Financial values remain base-10 decimal strings.

The catalog validates, as one operation:

- strict configuration fields and risk value shapes;
- canonical account and strategy identifiers;
- a real `strategies/<strategy_id>.md` file for every selected strategy;
- unique universe symbols;
- `execution.mode` in `live`, `shadow`, or `dry_run`; and
- no more than one live configuration.

The catalog returns deterministic, account-ID-sorted cohorts. A missing strategy or second live configuration invalidates the catalog instead of silently skipping a lane.

## Strategy seam

`strategies/` may contain multiple version-named Strategy Specs. A configuration selects exactly one by identifier. The Decision Routine reads that file completely and applies it to only its assigned lane.

The seam is deliberately small: Strategy Specs are prompt-defined Markdown policies, not Python plugins. The generic publisher and deterministic risk module remain authoritative for shape, sizing, and safety. Adding a new strategy does not require changing Python, but selecting a missing strategy fails catalog validation.

Account A selects `growth_momentum_v3`. Its Decision Routine normalizes source-attributed completed-session OHLC, eight quarterly financial/cash-flow rows, earnings dates, and sectors, then passes that credential-free input and the selected account configuration through the deterministic Growth Momentum facts compiler. The compiler requires its symbol set to match the configured universe exactly. SPY and QQQ are benchmark-only and receive technical facts without impossible corporate-financial requirements. Every security receives complete technical, relative-momentum, earnings-distance, revenue-growth, margin, and free-cash-flow facts or the whole compilation fails. Ranking and prose research begin only after success; raw authenticated responses are never persisted.

Account B currently selects `earnings_drift_v1`, an event-driven policy adapted to the generic publication seam. Its earnings facts, research answers, rejected candidates, warnings, and thesis metadata belong in immutable `DecisionSnapshot.inputs`; its plan still uses the shared `OrderPlan` schema. The first shadow cycle starts from its configured `$1000` virtual balance. Later cycles continue from the latest `ending_account` rather than resetting capital.

Every new `OrderPlan`, Decision record, deterministic result, execution record, and report carries `strategy_id`. New OrderPlans also freeze whether Decision was `fixture`, `manual`, or `scheduled`; execution evidence independently freezes its own run kind. Historical plans without Decision run provenance remain readable as legacy evidence. A versioned Strategy Spec should not be edited in place after it has produced decisions; create a new identifier so historical attribution stays meaningful. Git history retains its exact checked-in content.

## Execution modes and scheduled cohorts

| Mode | Scheduled selection | Execution behavior | Authority |
|---|---|---|---|
| `live` | The live cohort contains zero or one lane | Deterministic risk output may be sent to the reviewed Agentic Robinhood adapter after the Live Gate | Human-owned activation; real broker consequence |
| `shadow` | Every shadow lane is selected in account-ID order | Deterministic risk runs; marketable allowed orders receive assumed T+1 quote fills and virtual ending state | No broker connection or write |
| `dry_run` | Excluded from all scheduled cohorts | Manual fixture/development evaluation only; proposed broker arguments but no fill | Developer evidence only |

Changing an execution mode is a reviewed human operation. A shadow-to-live change also requires broker binding and real cash/position baseline reconciliation; virtual holdings never authorize a real trade.

## Four scheduled runs

Ripple uses four non-overlapping schedule triggers:

| Run | Selection | Intended time |
|---|---|---|
| Live Decision | 0..1 live lane | Sunday–Thursday around 9:00 PM `America/New_York` |
| Shadow Decision | all shadow lanes | Sunday–Thursday around 9:00 PM `America/New_York` |
| Live Execution | 0..1 live lane | next weekday around 9:35 AM `America/New_York` |
| Shadow Execution | all shadow lanes | next weekday around 9:35 AM `America/New_York` |

There may be zero live lane while the Live Gate is closed; the live runs then finish without account work. Dry-run lanes are never selected. Missed cycles are not backfilled.

The shadow runs are one scheduled cohort but each lane remains an independent Decision Cycle. One lane's malformed input or failure is reported for that lane and does not authorize, mutate, or suppress another lane's work.

## One Decision Cycle

### Prior-evening Decision

The Decision Routine:

1. validates the complete catalog and selects its live or shadow cohort;
2. isolates one lane's configuration, state root, and selected Strategy Spec;
3. gathers allowed market and account facts;
4. prepares one strict `DecisionSnapshot`, account baseline, target portfolio, and zero or more proposed orders; and
5. publishes one immutable, strategy-attributed `OrderPlan`.

Decision never reviews, places, cancels, or changes a broker order. Missing facts produce no trade or stop that lane rather than authorizing a guess. A second publication for the same lane and date fails instead of overwriting evidence.

For a shadow lane, the Decision baseline comes from its latest prior `ending_account`; the first cycle starts from the reviewed `shadow.initial_cash`. Before the next cycle, current quotes mark equity and daily P&L, high-water mark moves only upward, and the prior trading day's new-position count resets. A live lane reads its real account through the platform-managed connection. These sources never merge.

### Overnight boundary

The published plan remains unchanged. Git carries credential-free artifacts into the next fresh routine. Execution receives no new investment thesis and does not rewrite Decision content.

### Next-weekday Execution

Execution loads the plan from the current trade-date directory, current account state, loss-sale history, and fresh quotes. Before risk evaluation, it requires that directory's immutable `decision_snapshot.json` and `order_plan.json` to exist and match the execution input. This binding applies equally to scheduled and explicitly authorized manual runs. It then runs the shared deterministic risk module.

Live execution may eventually submit only script-allowed actions exactly as emitted through the reviewed Robinhood read/review/place/cancel loop. That loop is not implemented or approved today, so no configuration is live.

Shadow execution uses the same risk output but never calls Robinhood. For each allowed action:

- the current quote must still satisfy the planned limit (`BUY quote <= limit`, `SELL quote >= limit`); market Risk Exits are marketable;
- a marketable order is assumed filled at the execution quote and `as_of` time;
- fees and slippage are explicitly zero in this MVP;
- an unmarketable limit is recorded as `not_filled`; and
- cash, quantity, average cost, new-position count, and visible loss-sale state are carried into an immutable per-cycle `ending_account`.

The plan's signal time remains Day T and every fill attempt remains Day T+1. Shadow never backdates a fill to the decision close.

## Modules and responsibilities

| Module | Interface responsibility | What stays behind it |
|---|---|---|
| Account catalog | Load all lane configs and select one mode cohort | Filename identity, strict schema, strategy existence, live-count validation, deterministic ordering |
| Growth Momentum facts compiler | Compile one normalized source-attributed document into complete v3 facts | Decimal formulas, session alignment, provenance, interpolation rejection, and fail-closed validation |
| Decision publisher | Publish one validated Decision Cycle | Timing, universe, target weights, stable IDs, strategy attribution, immutable writes |
| `DecisionSnapshot` | Represent allowed decision inputs | Strict JSON and immutable nested values |
| `OrderPlan` | Represent strategy-attributed decision intent | Strict order shape, account baseline, portfolio weights, immutable nested values |
| Risk module | Return allowed, clipped, rejected, or aborted actions | Account binding, freshness, sizing, cash reservation, loss/drawdown/wash-sale/exit rules |
| Shadow adapter | Return fill attempts and ending virtual state | T+1 marketability, quote-price fills, position/cash state transition, no broker I/O |
| Live adapter | Use deterministic output with Robinhood | Still unfinished and gated |
| Lane State | Carry credential-free evidence across fresh sessions | Per-lane trade-date cycles and an optional active risk lock |

## Artifacts and state

| Artifact | Mutability and use |
|---|---|
| `DecisionSnapshot` | Immutable allowed facts and universe for review/reproduction |
| `OrderPlan` | Immutable account-, strategy-, cycle-, and Decision-run-attributed decision |
| Dry-run result | Proposed actions plus Execution run provenance; explicitly not fills |
| Shadow result | Risk result, fill attempts, assumptions, ending virtual account state, and Execution run provenance |
| Report | Human-readable action and Shadow Fill summary |
| Tier-two lock | Lane-scoped persistent block on new BUYs until owner review |

Canonical state roots are `state/accounts/<account_id>`. Each cycle lives at `trading_days/<trade_date>`, where `trade_date` is the next New York weekday after the Decision. `decision_snapshot.json` and `order_plan.json` are published prior evening; `execution.json` and `report.md` join the same directory after Execution. The optional account-root `active_risk_lock.json` persists across dates. Cycle artifacts never cross roots or overwrite earlier evidence.

## Deterministic safety

All modes use the same rules: 20% maximum symbol position, three new positions per day, 5% daily-loss breaker, 10% tier-one drawdown, 15% tier-two drawdown and owner restart, 15-minute quote freshness, 30-day taxpayer-wide wash-sale lookback, 8% stop loss, and 20% take profit.

Execution also checks the decision baseline, universe, price tolerance, cumulative BUY cash, and SELL holdings. Every planned limit must remain within its positive per-order tolerance, which may not exceed 10%. A BUY may additionally freeze `gap_cancel_above`; such an order requires the actual regular-session open and is rejected when that open is strictly above the frozen threshold. A missing required session open aborts the plan. Missing or stale facts, malformed input, cross-account mismatch, or unsafe sizing fails closed. A deterministic full-position Risk Exit is the only action allowed without a matching planned order.

## Authority and reliability

Deterministic code controls schemas, Growth Momentum numeric fact derivation, IDs, account binding, timing, risk calculations, and Shadow Fill state transitions. Routine prompts control source gathering, normalization, qualitative research, and LLM tool use. The owner and platform control credentials, schedules, broker binding, live activation, capital, and restart.

Git is continuity and audit evidence, not a transactional submission journal or cross-runner lease. Live execution still accepts duplicate-call, ambiguous-timeout, crash-before-log, prompt/tool-use, and model-drift risk at the small canary allocation. Shadow results avoid broker risk but remain assumptions, not evidence that a real limit order would have filled at that price or with zero costs.

Credentials, tokens, cookies, account numbers, and raw authenticated responses never enter Git artifacts, fixtures, prompts, logs, or reports.

## Current non-goals

The implemented architecture does not include automatic strategy scoring/promotion, a dashboard, multiple simultaneous live lanes, a Python strategy engine, transactional persistence, exactly-once broker execution, automatic reconciliation, intraday trading, additional brokers, tax-lot optimization, or a calibrated slippage/fee model.

Operational procedures belong in `docs/RUNBOOK.md`. Remaining hosted and live work belongs in `docs/TODO.md`.
