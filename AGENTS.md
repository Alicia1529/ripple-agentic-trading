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
