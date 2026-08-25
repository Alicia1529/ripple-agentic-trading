# Ripple trading domain

Ripple describes a two-stage, agent-mediated trading loop whose account boundaries, decision artifacts, and risk authority must remain explicit. Use these terms consistently in code and documentation.

## Language

**Account Lane**:
One account's isolated decision-to-execution path, identified by `account_id`. A lane never owns another lane's plan, state, risk, or broker authority.
_Avoid_: Account worker, account collection

**Decision Cycle**:
One prior-evening decision and its corresponding next-weekday execution attempt for a single Account Lane.
_Avoid_: Trading session, daily run

**Decision Routine**:
The isolated LLM role that gathers allowed facts, applies the assigned strategy, and publishes one decision without execution authority.
_Avoid_: Trading bot, execution agent

**DecisionSnapshot**:
The immutable allowed inputs, universe, and as-of facts used for one Decision Cycle.
_Avoid_: Prompt context, market snapshot

**OrderPlan**:
The immutable decision-stage instruction for one Account Lane and Decision Cycle. It contains the intended portfolio, proposed orders, and credential-free account baseline, but never execution outcomes.
_Avoid_: Trade result, execution plan

**Execution Routine**:
The isolated LLM role that applies deterministic risk output to a published OrderPlan. It may execute, scale down, reject, or abort, but does not form a new investment view.
_Avoid_: Portfolio manager, independent trading agent

**Risk Exit**:
A deterministic full-position sell produced by a configured stop-loss or take-profit rule. It is risk authority over an existing holding, not a new investment decision or a replacement OrderPlan.
_Avoid_: Execution trade idea, replacement plan

**Lane State**:
The credential-free continuity record owned by one Account Lane, including its plans, decision and execution facts, reports, and restart lock.
_Avoid_: Shared ledger, transactional journal

**Live Gate**:
The human-owned approval boundary that permits one Account Lane to move from dry-run evidence to real broker writes after its required acceptance checks.
_Avoid_: Automatic promotion, model approval

**Hosted Acceptance**:
Evidence from a complete scheduled Decision Cycle in the intended hosted environment, with no broker write. Manual rehearsal is not Hosted Acceptance.
_Avoid_: Local acceptance, manual dry run
