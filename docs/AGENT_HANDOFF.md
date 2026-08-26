# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-26 12:40 PDT — T+1 timing resolved against a trading calendar

- Outcome: new [`ripple/calendar.py`](../ripple/calendar.py) holds the NYSE closures for 2026–2027, transcribed from nyse.com; `_next_weekday` is gone from [`mvp.py`](../ripple/mvp.py). Trade dates, decision eves, execution dates, and both runtime clocks now resolve against it.
- Before: a Sunday 2026-09-06 Decision published `trading_days/2026-09-07` (Labor Day) and refused execution on 09-08, orphaning the plan. All ten 2026 closures fall on a scheduled cycle.
- Contract change: a scheduled run outside a trading session prints `no trading session` and exits 0; manual and backfill still fail loudly. Dates outside coverage raise.
- Evidence: 72 tests pass; `validate-configs` reports two accounts. No config or state change.
- Risk: coverage ends 2027-12-31 and holds no unscheduled closures.

## 2026-08-26 01:22 PDT — README introduces the documentation set

- Outcome: [`README.md`](../README.md) now groups every document by the question it answers — understand it, run it, change it — so the three new pages and the existing set are reachable from the front page.
- Correction: the stale "Current gates" paragraph, which still required a live loop the intro already described as in place, is replaced by what actually gates expansion.
- Deferred: `EXECUTION_LIVE.md` and [`ARCHITECTURE.md`](ARCHITECTURE.md) still say the live broker-write loop is unimplemented while TODO, README, and `config/account_a.json` say otherwise; README now points at both authorities instead of taking a side. Owner decision required.
- Evidence: 72 tests pass, no broken links, every `docs/*.md` reachable from README or the map.

## 2026-08-26 01:33 PDT — Live Execution stop contract removed

- Outcome: [`EXECUTION_LIVE.md`](../routines/EXECUTION_LIVE.md) now operates the reviewed live loop for a catalog-selected lane and requires deterministic output fidelity, account binding, duplicate/history checks, ambiguity stops, and credential-free evidence.
- Alignment: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`RUNNING.md`](RUNNING.md), and [`SCHEDULE.md`](../routines/SCHEDULE.md) no longer describe the completed loop or live tasks as unfinished.
- Scope: prompt and documentation only; no code, strategy, configuration, state, schedule trigger, broker connection, or allocation changed.
- Evidence: full tests pass; stale stop-contract search and `git diff --check` are clean.
- Risk: live v1 retains the reliability limits documented in [`RUNBOOK.md`](RUNBOOK.md); ambiguous outcomes still require human inspection and never authorize retry.
