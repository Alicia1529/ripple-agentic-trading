# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 23:12 PDT — Dry-run tests isolated from deployment mode

- Outcome: legacy MVP dry-run tests now create a test-owned temporary `dry_run` configuration instead of reading the live mode from `config/account_a.json`.
- Scope: changed only [`tests/test_mvp_cycle.py`](../tests/test_mvp_cycle.py); production configuration, Decision, Execution, risk, and state behavior are unchanged.
- Evidence: all 19 MVP cycle tests and the complete 53-test suite pass; compileall and `git diff --check` pass.
- Risk: one previously false-positive timing test now reaches the intended dry-run timing guard rather than passing on an unrelated live-mode error.

## 2026-08-26 00:01 PDT — Shadow branch corrected in the system diagrams

- Outcome: the Mermaid diagrams in [`ARCHITECTURE.md`](ARCHITECTURE.md), [`README.md`](../README.md), and [`PROPOSAL.md`](../PROPOSAL.md) now show shadow skipping only the Robinhood call, not the risk verdict or the T+1 marketability check.
- Correction: the previous "assumed T+1 quote fill" label understated [`shadow.py`](../ripple/shadow.py), which records `not_filled`/`limit_not_marketable` when the 9:35 quote misses the planned limit.
- Scope: diagram labels and evidence edges only; prose, code, configurations, and state are unchanged.
- Evidence: all three diagrams render through mermaid-cli; `git diff --check` passes.

## 2026-08-26 00:03 PDT — V2 Lite unleveraged buying-power basis

- Outcome: [`growth_momentum_v2_lite.md`](../strategies/growth_momentum_v2_lite.md) may use broker-authorized pending-deposit early access only through `unleveraged_buying_power`; margin and additive pending deposits remain forbidden.
- Execution: [`EXECUTION_LIVE.md`](../routines/EXECUTION_LIVE.md) maps the same fresh broker value to `execution_context.account.cash`; deterministic baseline mismatch still aborts.
- Scope: policy and routine text only; no schema, risk, config, Decision, Execution, or broker write changed.
- Evidence: all 53 tests and `git diff --check` pass.
- Next/risk: a future live Decision may use this basis; if Robinhood reduces early access before Execution, baseline matching safely aborts the plan.
