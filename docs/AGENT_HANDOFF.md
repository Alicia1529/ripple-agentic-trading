# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-26 01:05 PDT — Stage lines realigned with TODO

- Outcome: the stage sentences in [`PROPOSAL.md`](../PROPOSAL.md) and [`README.md`](../README.md) no longer claim hosted acceptance and the broker-write loop are unfinished; both now defer to [`TODO.md`](TODO.md) instead of restating status.
- Neither line names an account, mode, or strategy binding, so `config/*.json` stays the sole deployment authority.
- Open discrepancy: TODO marks live acceptance complete, but the repository holds no live execution evidence — the only live plan (2026-08-27) was removed by `ffadebd`. Worth an owner check before any live claim is made elsewhere.
- Evidence: 61 tests pass; documentation only. No `ripple/*.py`, config, or state change.

## 2026-08-26 12:40 PDT — T+1 timing resolved against a trading calendar

- Outcome: new [`ripple/calendar.py`](../ripple/calendar.py) holds the NYSE closures for 2026–2027, transcribed from nyse.com; `_next_weekday` is gone from [`mvp.py`](../ripple/mvp.py). Trade dates, decision eves, execution dates, and both runtime clocks now resolve against it.
- Before: a Sunday 2026-09-06 Decision published `trading_days/2026-09-07` (Labor Day) and refused execution on 09-08, orphaning the plan. All ten 2026 closures fall on a scheduled cycle.
- Contract change: a scheduled run outside a trading session prints `no trading session` and exits 0; manual and backfill still fail loudly. Dates outside coverage raise.
- Evidence: 72 tests pass; `validate-configs` reports two accounts. No config or state change.
- Risk: coverage ends 2027-12-31 and holds no unscheduled closures.

## 2026-08-26 01:13 PDT — Reader-facing documentation added

- Outcome: added [`docs/README.md`](README.md) as the documentation map, [`ANATOMY_OF_A_CYCLE.md`](ANATOMY_OF_A_CYCLE.md) walking one reproducible cycle field by field, [`WRITING_A_STRATEGY.md`](WRITING_A_STRATEGY.md) for the Strategy Spec contract, plus root `CONTRIBUTING.md` and `SECURITY.md`.
- Scope: five new files only. No existing document, routine, configuration, code, or state was touched, because a concurrent session held README, PROPOSAL, ARCHITECTURE, INVARIANTS, RUNBOOK, RUNNING, DECISIONS, the routines, and `ripple/mvp.py`.
- Alignment: trade-date wording follows the new trading calendar rather than weekday arithmetic.
- Evidence: 72 tests pass, the documented demo command runs verbatim, and the new documents have no broken relative links. Open follow-up: README does not yet link the three new `docs/` pages.
