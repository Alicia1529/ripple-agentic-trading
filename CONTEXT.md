# Ripple trading domain

Ripple describes a two-stage, strategy-attributed trading loop whose lane boundaries, decision artifacts, execution evidence, and risk authority remain explicit.

## Language

**Account Lane**:
One isolated strategy portfolio, identified by the filename of its account configuration. A Live Account Lane is bound to a real broker account; a Shadow Account Lane owns virtual evidence only.
_Avoid_: Broker account, account worker, strategy instance

**Strategy Spec**:
A checked-in, version-named investment policy selected by an Account Lane and applied only by its Decision Routine.
_Avoid_: Plugin, strategy engine, trading bot

**Trading Day**:
A date with a regular `America/New_York` session, decided by the checked-in trading calendar rather than by weekday arithmetic. A Decision Cycle's trade date is always one.
_Avoid_: Weekday, business day, market day

**Execution Mode**:
The human-owned classification of an Account Lane as `live`, `shadow`, or `dry_run`.
_Avoid_: Environment, automatic promotion state

**Cycle Profile**:
The configured timing topology of a Decision Cycle: `next_session_open` or `same_session_close`.
_Avoid_: Strategy cadence, execution mode

**Scheduled Cohort**:
The Account Lanes selected for one scheduled run by Execution Mode and Cycle Profile. A live cohort contains at most one lane; a shadow cohort contains every matching shadow lane; dry-run lanes belong to neither.
_Avoid_: Shared account pool, batch account

**Decision Cycle**:
One profile-attributed Decision and its corresponding Execution attempt for a single Account Lane. Its Trading Day is the frozen Execution-session date; `next_session_open` decides on the prior evening, while `same_session_close` decides earlier on that same regular session.
_Avoid_: Trading session, daily batch

**Decision Routine**:
The isolated LLM role that gathers allowed facts, applies the selected Strategy Spec, and publishes one decision without execution authority.
_Avoid_: Trading bot, execution agent

**DecisionSnapshot**:
The immutable allowed inputs, universe, and as-of facts used for one Decision Cycle.
_Avoid_: Prompt context, market snapshot

**OrderPlan**:
The immutable, strategy-attributed decision-stage instruction for one Account Lane and Decision Cycle.
_Avoid_: Trade result, execution plan

**Decision Rationale**:
The concise, human-readable explanation for an OrderPlan's final target portfolio and orders, including a no-trade result. It is investment judgment, not a data-quality warning or deterministic risk result.
_Avoid_: Warning, rejection reason, execution reason code

**Execution Routine**:
The isolated role that applies deterministic risk output to a published OrderPlan without forming a new investment view.
_Avoid_: Portfolio manager, independent trading agent

**Shadow Fill**:
A credential-free, profile-attributed assumption that a deterministic-risk-allowed order filled at its actual Execution quote when its limit was marketable. It is evidence, never a broker fill.
_Avoid_: Paper broker confirmation, backdated fill

**Risk Exit**:
A deterministic full-position sell produced by a configured stop-loss or take-profit rule.
_Avoid_: Execution trade idea, replacement plan

**Lane State**:
The credential-free continuity record owned by one Account Lane, including plans, facts, results, reports, and restart locks.
_Avoid_: Shared ledger, transactional journal

**Live Gate**:
The human-owned approval boundary that permits one Account Lane to use real broker-write capability after required acceptance checks.
_Avoid_: Automatic promotion, model approval

**Hosted Acceptance**:
Evidence from the intended scheduled environment without unauthorized broker writes. Manual rehearsal is not Hosted Acceptance.
_Avoid_: Local acceptance, manual dry run
