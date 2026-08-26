# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 20:17 PDT — Trade-date Lane State reset

- Outcome: reset all checked-in A/B state and replaced type/date trees with `trading_days/<trade-date>` cycles; prior-evening Decision artifacts and next-weekday Execution/report now share one directory.
- State: removed JSONL indexes; the optional lane-wide tier-two block is now `active_risk_lock.json`; empty A/B `trading_days` roots remain tracked.
- Architecture: recorded the approved reset in [`DECISIONS.md`](DECISIONS.md) and updated architecture, routines, runbook, README, proposal, invariants, and TODO references.
- Evidence: focused trade-date/layout tests and `git diff --check` pass; the core suite retains the pre-existing config/fixture mismatch at 8 failures and 8 errors.
- Risk/next: prior state remains recoverable only from Git history; the next Decision creates the first canonical new trade-date cycle.

## 2026-08-25 20:42 PDT — Fail-closed cycles and manual provenance

- Outcome: restored `account_a` to `dry_run`; the catalog now has no live lane, `account_b` shadow, and `account_a` dry-run.
- Facts: Growth Momentum compilation requires the input symbols to match the selected configuration's universe exactly.
- State: Execution requires its co-located snapshot and plan; new plans/results freeze Decision/Execution run kinds independently while manual runs remain accepted and legacy plans readable.
- Evidence: 50 core tests, catalog/cohort checks, syntax compilation, and `git diff --check` pass.
- Risk/next: deleted pre-reset state remains only in Git history; filing-availability timestamps remain a separate input-contract change.

## 2026-08-25 20:57 PDT — Config-owned deployment inventory

- Outcome: made [`config/*.json`](../config/) the sole authority for current lane identity, mode, strategy, universe, and risk bindings.
- Docs: architecture, proposal, README, runbook, TODO, and routines now describe stable contracts and discover cohorts through the catalog instead of caching concrete bindings.
- Strategy: moved compiler invocation into the selecting Strategy Spec; historical state and handoff facts remain intact.
- Evidence: catalog validation, deployment-detail scans, `git diff --check`, and all 50 core tests pass.
- Risk/next: generic fixture examples require substituting IDs and paths returned by catalog inspection; runtime behavior and configuration are unchanged.
