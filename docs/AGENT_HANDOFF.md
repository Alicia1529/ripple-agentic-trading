# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 22:58 PDT — Growth Momentum v2 Lite prompt tightened

- Outcome: added an explicit Decision order, valid no-trade outcomes, centralized failure scope, and a checkable publication self-check to [`growth_momentum_v2_lite.md`](../strategies/growth_momentum_v2_lite.md).
- Evidence rule: growth durability now requires affirmative primary-source support; absence of a discovered problem cannot qualify a BUY.
- Scope: formulas, filters, ranking, sizing, strategy identity, configurations, state, routines, and Execution behavior are unchanged.
- Evidence: catalog/diff/credential checks pass; the full test baseline remains 44/53 with the known legacy dry-run config mismatch.

## 2026-08-25 23:04 PDT — Account B historical Shadow Decision

- Outcome: owner-authorized backfill published `account_b`/`earnings_drift_v1` plan `7a0dae3e-23a8-5251-ac17-e141277fe1b9` for trade date 2026-08-26, with zero orders and 100% cash.
- Rationale: no configured-universe company reported earnings in the prior three completed sessions and no position required an exit; warnings remain separate evidence.
- Evidence: the complete snapshot exactly matches commit `1b9d2de`; JSON/schema, provenance, credential, and diff checks pass.
- Tests/risk: 44/53 tests pass; the known 7 failures/2 errors remain legacy dry-run/config mismatches. No Execution, fill, broker, or live work occurred.

## 2026-08-25 23:12 PDT — Dry-run tests isolated from deployment mode

- Outcome: legacy MVP dry-run tests now create a test-owned temporary `dry_run` configuration instead of reading the live mode from `config/account_a.json`.
- Scope: changed only [`tests/test_mvp_cycle.py`](../tests/test_mvp_cycle.py); production configuration, Decision, Execution, risk, and state behavior are unchanged.
- Evidence: all 19 MVP cycle tests and the complete 53-test suite pass; compileall and `git diff --check` pass.
- Risk: one previously false-positive timing test now reaches the intended dry-run timing guard rather than passing on an unrelated live-mode error.
