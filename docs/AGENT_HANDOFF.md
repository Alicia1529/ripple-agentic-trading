# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

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

## 2026-08-26 01:05 PDT — Stage lines realigned with TODO

- Outcome: the stage sentences in [`PROPOSAL.md`](../PROPOSAL.md) and [`README.md`](../README.md) no longer claim hosted acceptance and the broker-write loop are unfinished; both now defer to [`TODO.md`](TODO.md) instead of restating status.
- Neither line names an account, mode, or strategy binding, so `config/*.json` stays the sole deployment authority.
- Open discrepancy: TODO marks live acceptance complete, but the repository holds no live execution evidence — the only live plan (2026-08-27) was removed by `ffadebd`. Worth an owner check before any live claim is made elsewhere.
- Evidence: 61 tests pass; documentation only. No `ripple/*.py`, config, or state change.
