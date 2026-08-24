# AGENTS.md

Start here:

1. `PROPOSAL.md`
2. `docs/ARCHITECTURE.md`
3. `docs/INVARIANTS.md`
4. `docs/TODO.md`
5. `docs/AI_NATIVE_DELIVERY.md`
6. `docs/AGENT_WORKFLOW.md`
7. `docs/AGENT_HANDOFF.md` — read its rules and latest three entries only

Respect `docs/INVARIANTS.md` for every implementation and review. When changing durable architecture, add a decision to `docs/DECISIONS.md` and update `docs/ARCHITECTURE.md`; never introduce such a change silently.
Before planning or implementation, use `docs/AI_NATIVE_DELIVERY.md` to define the current delivery contract and keep scope, process, and risk proportional to the release stage.
For deployment, debugging, or recovery work, read `docs/RUNBOOK.md`.
Run the relevant tests before handing off a change. Use `docs/TODO.md` only for current status and genuinely unfinished work.

## MVP implementation policy

- Optimize for the shortest safe path to a testable trading loop.
- Preserve the existing architecture unless redesign is explicitly requested.
- Reuse existing configuration and data models.
- Build abstractions only for current, concrete requirements.
- Treat feature scope as authoritative: adjacent refactoring requires separate approval.
- Separate required changes from optional improvements, and implement only the required changes.
- If a change requires a new subsystem or affects more than four production files, stop and request approval; include a smaller alternative.

## Task workflow

Separate design from implementation:

1. **Bounded design:** Inspect the code and propose the smallest viable diff without editing files. Explicitly list what will not be built.
2. **Approval:** Wait for the proposed scope to be reviewed and explicitly approved.
3. **Bounded implementation:** Start a new thread and implement exactly the approved plan. Preserve the architecture and leave adjacent improvements out of the diff.

Use Low reasoning for small, clearly scoped implementation tasks. Reserve Medium or High reasoning for architecture decisions and difficult debugging, where exploring more alternatives is worth the additional scope-expansion risk.
