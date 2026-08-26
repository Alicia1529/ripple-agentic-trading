# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 18:02 PDT — Account B scheduled Shadow Decision

- Outcome: published scheduled 2026-08-25 `account_b` Decision; `earnings_drift_v1` plan `7a0dae3e-23a8-5251-ac17-e141277fe1b9` holds 100% cash with zero orders.
- Evidence: latest ending account supplied the $1000 baseline; sourced August 21/24/25 universe screen had no eligible completed earnings event, and August 25 SPY facts were recorded.
- Verification: catalog/cohort checks, artifact/schema inspection, credential scan, and `git diff --check` pass.
- Tests/risk: 41 core tests retain the documented config/fixture mismatch at 9 failures and 8 errors; 2026-08-26 Shadow Execution may consume this no-action plan.

## 2026-08-25 20:06 PDT — Deterministic Growth Momentum v3 facts

- Outcome: added a source-attributed Decimal facts compiler and selected [`growth_momentum_v3`](../strategies/growth_momentum_v3.md) for Account A; existing v2 decisions remain immutable.
- Interface: one normalized document produces technical, relative-momentum, earnings, growth, margin, and FCF facts; SPY/QQQ are benchmark-only, while incomplete or unsafe security data fails closed.
- Architecture: Decision gathers/normalizes sources, checked-in code derives numbers, and qualitative filtering/research remains in the Strategy Spec; no broker-write authority changed.
- Evidence: 4 compiler and 3 catalog tests, catalog validation, CLI immutability, syntax check, and `git diff --check` pass.
- Tests/risk: 45 core tests retain the pre-existing config/fixture mismatch at 8 failures and 8 errors; reconcile those fixtures separately before relying on the full suite.

## 2026-08-25 20:17 PDT — Trade-date Lane State reset

- Outcome: reset all checked-in A/B state and replaced type/date trees with `trading_days/<trade-date>` cycles; prior-evening Decision artifacts and next-weekday Execution/report now share one directory.
- State: removed JSONL indexes; the optional lane-wide tier-two block is now `active_risk_lock.json`; empty A/B `trading_days` roots remain tracked.
- Architecture: recorded the approved reset in [`DECISIONS.md`](DECISIONS.md) and updated architecture, routines, runbook, README, proposal, invariants, and TODO references.
- Evidence: focused trade-date/layout tests and `git diff --check` pass; the core suite retains the pre-existing config/fixture mismatch at 8 failures and 8 errors.
- Risk/next: prior state remains recoverable only from Git history; the next Decision creates the first canonical new trade-date cycle.
