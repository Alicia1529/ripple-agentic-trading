# Ripple agent entrypoint

Ripple is an existing two-account, fixture-backed dry-run MVP moving toward hosted acceptance. Preserve the isolated account lanes, trading behavior, deterministic safety rules, schemas, timing, and state semantics. Build the shortest safe slice that produces evidence for a current requirement.

## Sources of truth

Read these before every task:

| Document | Authority |
|---|---|
| `PROPOSAL.md` | Why Ripple exists, the current release, and product scope |
| `docs/ARCHITECTURE.md` | How the current system works and where its boundaries sit |
| `docs/INVARIANTS.md` | Non-negotiable safety and correctness rules |
| `docs/TODO.md` | Genuinely unfinished work and the next operational gates |
| `docs/AGENT_HANDOFF.md` | Handoff protocol and the latest three entries only |

Use task-specific context only when its branch applies:

- Read `CONTEXT.md` when defining, renaming, or reviewing domain language.
- Read `docs/DECISIONS.md` before changing durable architecture; record an approved decision there and update `docs/ARCHITECTURE.md` in the same change.
- Read `docs/RUNBOOK.md` for deployment, scheduling, debugging, incident response, or recovery.
- Read `routines/` for hosted prompt or schedule work.
- Read `strategies/growth_momentum_v1.md` for Account A investment behavior.

## Delivery contract

Before planning, state:

1. the current release stage;
2. the next observable outcome;
3. the exact in-scope behavior and files;
4. accepted risks and explicit non-goals; and
5. the commands or artifacts that will prove completion.

Preserve the current architecture and reuse existing configuration and data models. Adjacent refactoring requires separate approval. A new subsystem or changes to more than four production files require explicit approval and a smaller alternative; documentation-only breadth should remain proportional to the task.

Every implementation and review identifies affected invariants. A proposed change that invalidates an invariant is an architecture decision, not a local exception.

## Workflow

1. **Bounded design:** inspect without editing, propose the smallest viable diff, and name non-goals.
2. **Approval:** wait for explicit scope approval.
3. **Bounded implementation:** use a new task, implement exactly the approved diff, and leave optional improvements out.
4. **Verification:** run tests proportional to the affected behavior and inspect generated artifacts where relevant.
5. **Handoff:** create one focused commit with the assigned role prefix and append one compact rolling handoff entry.

Use Low reasoning for small, clearly scoped implementation. Use Medium or High only when an architecture decision or difficult diagnosis justifies broader exploration.
