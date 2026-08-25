# Current architecture

Ripple is an existing fixture-backed dry-run MVP moving toward hosted acceptance. It runs exactly two isolated Robinhood Agentic account lanes over the same concrete CLI, schemas, and deterministic risk code. This document describes only that current system.

## Two isolated lanes

| Lane | Configuration | State root | Hosted boundary |
|---|---|---|---|
| Account A | `config/mvp.json` | `state/accounts/account_A` | One Decision schedule, one Execution schedule, one bound MCP connection |
| Account B | `config/mvp-account-b.json` | `state/accounts/account_B` | Separate schedules and separately bound MCP connection |

Each command resolves one configuration and writes below one account-named state root. Configuration, plan, execution context, state-root basename, risk state, broker calls, and live gate must agree on `account_id`. One lane never authorizes work in the other. Taxpayer-wide loss-sale history is the sole documented cross-account input.

There is no `accounts[]` schema, coordinator, batch runner, shared ledger, credential abstraction, or third-account support. The ten-minute hosted schedule offset reduces ordinary Git conflicts but is not a lease.

## Decision and execution split

Decision and execution are separate fresh hosted sessions because information readiness and execution quality occur at different times:

```text
Sunday–Thursday ~9:00 PM ET
Decision: allowed facts → strategy → deterministic sizing → snapshot + plan → Git

Overnight
Published plan remains immutable

Next weekday ~9:35 AM ET
Execution: plan + current account facts → deterministic revalidation → dry record or live MCP calls → Git
```

Sunday's decision uses Friday's completed close plus facts available by Sunday evening. Other decisions use the latest completed session. Execution occurs after the next market open; no evaluation may pretend a signal using a completed close filled at that same close. Missed cycles are not backfilled.

The public commands check the real `America/New_York` date and phase window. Explicit owner-initiated manual runs may bypass the window where documented and are labeled `run_kind=manual`; manual dry evidence never counts as scheduled acceptance.

The Decision Routine may gather required broker reads but never review, place, cancel, or alter an order. Account A's hosted connection exposes write tools, so this is a prompt-enforced small-allocation boundary rather than platform tool isolation. Any Decision write call is an incident: stop, disable the lane, and inspect Robinhood.

The Execution Routine receives the published plan, current account/risk facts, and required quotes—not news or new thesis material. It may execute as-is, scale down, reject an order, or abort the plan. It must not change direction or invent a trade. A deterministic full-position stop-loss/take-profit Risk Exit is the sole permitted order absent from the plan.

## Documents and state flow

`DecisionSnapshot` is an immutable strict envelope of allowed inputs, unique universe, and timezone-aware `as_of`. It recursively detaches data and serializes to a fresh copy.

`OrderPlan` is the immutable decision output. It binds stable plan/order IDs, account and model metadata, snapshot ID and market time, target portfolio, credential-free decision-time cash/positions baseline, and zero or more orders. Persisted financial values are base-10 decimal strings. Orders are positive share-quantity `LIMIT`, `regular_hours`, `gfd`; BUYs include the decision-stage reason.

The current Account A strategy is `strategies/growth_momentum_v1.md`. It screens the full configured universe, reviews current positions, and may publish no trade, one fixed 10% BUY, one full discretionary SELL, or both. The generic publisher validates the result. There is no strategy-specific Python engine or plugin framework.

Execution never mutates the plan. It appends credential-free JSONL facts and writes an execution result plus human-readable report. A second publication/execution for an owned cycle fails rather than overwriting success. A tier-two breach creates `<state-root>/risk/drawdown_tier2.lock.json`; equity recovery does not clear it.

## Deterministic revalidation

All limits are evaluated against the assigned account's own equity and state:

| Rule | Current value | Result |
|---|---:|---|
| Maximum position | 20% per symbol | Clip to cap |
| New positions | 3 per account/day | Reject excess |
| Daily loss | 5% | Block new entries; exits remain |
| Drawdown tier 1 | 10% from high-water mark | Block new entries and notify |
| Drawdown tier 2 | 15% | Persist human-restart lock; exits remain |
| Quote freshness | 15 minutes | Missing/stale data fails closed |
| Wash sale | 30-day taxpayer-wide lookback | Block BUY; never block a safe exit |
| Position thresholds | 8% stop loss / 20% take profit | Emit deterministic full-position Risk Exit |
| Products | Long equities only | Reject shorts, leverage, and options |

BUY cash is reserved cumulatively at limit prices, the worst permitted fill. Execution aborts planned trading when cash/positions differ from the plan baseline, required held/planned-symbol quotes are missing or stale, account identity differs, input is malformed, or deterministic checks cannot safely size an action. Required-data uncertainty suppresses Risk Exits too; the routine never guesses.

Every clipped or rejected instruction records the original proposal, triggered rule, actual action, and `account_id`. Deterministic scripts are authoritative, but v1 does not technically prevent the LLM Execution session from misreading or bypassing their output.

## Hosted Git and MCP boundaries

The private Git repository carries code, configuration, per-cycle plans, compact decision/execution JSONL records, sanitized reports, and account-scoped locks between fresh sessions. Every routine pulls before work, commits and pushes credential-free output, stops on conflict, and never force-pushes trading state.

The hosted platform owns Robinhood OAuth storage, refresh, account authorization, and reconnection. Credentials, tokens, cookies, account numbers, and raw authenticated responses never enter Git, prompts, plans, fixtures, logs, or reports. Account numbers may exist only transiently in tool arguments/session memory.

Git is continuity and audit evidence, not a transactional trading journal. It does not close the broker-acceptance-before-log window or provide a cross-runner lease. One Decision and one Execution scheduler per lane, stable IDs, repository/broker-history checks, first-success ownership, and no blind retry reduce—but do not eliminate—duplicates.

## Accepted small-allocation risks

At the initial $500–1000 per lane, the owner accepts prompt/tool-use mistakes, incorrect arguments, duplicate calls, ambiguous timeouts, crash-before-log gaps, configuration misuse, prompt injection, and model/prompt drift. An ambiguous MCP outcome stops the run and requires manual Robinhood inspection before another attempt. The repository must not claim automatic reconciliation or exactly-once execution.

`execution.mode` is human-owned. `dry_run` forbids broker writes; `live` is enabled only after its gates; `disabled` stops new work. Disabling hosted schedules is the strongest operational stop. Neither setting automatically liquidates positions.

## Live gates

Each lane remains dry-run until all of the following are true:

1. Its hosted MCP connection is bound and proven to select the intended account.
2. One scheduled prior-evening Decision and next-weekday dry Execution cycle is complete and reviewable.
3. The live read/review/place/cancel call loop has been implemented and reviewed.
4. Alicia explicitly changes that lane's mode and approves its initial allocation.

The first live cycles are inspected directly in Robinhood. After eight continuous live weeks, observed performance and incidents permit a capital review; they do not authorize an increase. Capital expansion or a third account requires a new durable architecture decision.

## Explicit non-goals

- Refactoring the current MVP, risk, OrderPlan, DecisionSnapshot, or strategy behavior.
- A third account, shared scheduling/coordinator, account framework, or shadow/comparison infrastructure.
- A non-LLM executor, transactional journal, cross-runner lease, exactly-once guarantee, or automatic ambiguous-outcome reconciliation.
- Self-managed OAuth, additional brokers, intraday trading, tax-lot optimization, VWAP/TWAP, dashboards, or automatic capital changes.
- Execution-stage investment reasoning or any broker call from the Decision Routine.

`docs/INVARIANTS.md` is the review checklist; `docs/RUNBOOK.md` defines operation and recovery; `docs/TODO.md` contains the remaining gates.
