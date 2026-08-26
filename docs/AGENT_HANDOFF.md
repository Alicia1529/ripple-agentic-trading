# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-26 00:48 PDT — Compact V2 Lite facts

- Outcome: [`growth_momentum_v2_lite_compact.md`](../strategies/growth_momentum_v2_lite_compact.md) and its [compiler](../ripple/growth_momentum_lite.py) keep bars transient and publish compact facts; `account_a` selects the new version.
- Safety: structural errors fail closed; unavailable symbols remain explicit, and unavailable held-position facts stop publication. Historical V2 Lite is unchanged.
- Evidence: 61 tests, catalog validation, bytecode compilation, and `git diff --check` pass; 18-symbol output is 13,545 bytes versus the prior 586,769-byte snapshot.
- Next/risk: the next live Decision should verify the compact artifact. No Decision, Execution, shadow, state, broker operation, or mutable cache was added.

## 2026-08-26 01:01 PDT — Runner seam documented and offline demo added

- Outcome: [`RUNNING.md`](RUNNING.md) states the seven-requirement Agent Runner contract and lists Codex scheduled tasks as one implementation rather than the entry point; [`README.md`](../README.md) drops from 179 to 117 lines.
- Demo: `run-shadow-cycle` over [`demo_lane.json`](../config/examples/demo_lane.json) and its fixture produces a full cycle with no model, key, broker, or network.
- Isolation: `config/examples/` sits outside the `config/*.json` glob, so the demo lane cannot join a scheduled cohort; `validate-configs` still reports two accounts.
- Evidence: 61 tests pass, both documented demo commands run verbatim, no broken relative links, and no `ripple/*.py`, config, or state change.

## 2026-08-26 01:03 PDT — Backtesting recorded as a current non-goal

- Outcome: [`DECISIONS.md`](DECISIONS.md) now records historical backtesting as a current non-goal, because a Decision is a single non-replayable model call and no MarketData port or historical bar source exists.
- Positioning: forward shadow lanes are stated as the simulation path in [`PROPOSAL.md`](../PROPOSAL.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md) — same schedule, spec, and deterministic risk as live, differing only in the Shadow Fill assumption.
- Reversal path: revisiting it requires a new decision, not a local exception.
- Evidence: 61 tests pass; documentation only, across three files. No `ripple/*.py`, config, state, or `docs/TODO.md` change.
