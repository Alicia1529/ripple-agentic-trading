# AGENTS.md

Read in this order:
1. `PROPOSAL.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DECISIONS.md`
4. `docs/TODO.md`

Before changing architecture, update `docs/DECISIONS.md`.
Run tests before committing.
Do not modify production trading behavior without tests.
Never give a Decision-stage LLM session a tool that can place a live order — see "Execution must not be an LLM session" in `docs/ARCHITECTURE.md`. This is the one invariant not to relax for convenience.
