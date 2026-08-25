# Ripple agent entrypoint

Ripple is an existing two-account, fixture-backed dry-run MVP moving toward hosted acceptance. Preserve the two isolated account lanes, current trading behavior, deterministic safety rules, schemas, timing, and state semantics. Optimize for the shortest safe path to a testable trading loop; build only for a current concrete requirement.

Read before all work:

1. `PROPOSAL.md` — outcome and scope
2. `docs/ARCHITECTURE.md` — current system and accepted boundaries
3. `docs/INVARIANTS.md` — non-negotiable safety rules
4. `docs/TODO.md` — genuinely unfinished work
5. `docs/AGENT_HANDOFF.md` — protocol and latest three entries only

Read `docs/RUNBOOK.md` for deployment, debugging, or recovery. Read `CONTEXT.md` when changing domain language. Routine prompts and schedules live in `routines/`; Account A strategy behavior lives in `strategies/growth_momentum_v1.md`.

## Delivery contract

- Define the stage, next observable outcome, exact scope, accepted risks, non-goals, and verification before planning.
- Preserve existing architecture and reuse current configuration and data models. Adjacent refactoring needs separate approval.
- A new subsystem or changes to more than four production files require explicit approval and a smaller alternative. Documentation-only breadth is proportional to the task.
- Durable architecture changes require an explicit decision in `docs/DECISIONS.md` and a matching update to `docs/ARCHITECTURE.md`.
- Every implementation and review must identify affected invariants and run relevant tests before handoff.

## Workflow

1. **Bounded design:** inspect without editing; propose the smallest viable diff and list explicit non-goals.
2. **Approval:** wait for explicit scope approval.
3. **Bounded implementation:** use a new task and implement exactly the approved diff; leave optional improvements out.
4. **Handoff:** commit focused work with the assigned role prefix, verify it, and append one compact rolling handoff entry.

Use Low reasoning for small, clearly scoped implementation. Use Medium or High only for architecture decisions or difficult debugging where broader exploration is worth the scope risk.
