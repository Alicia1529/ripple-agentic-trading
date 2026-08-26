# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 22:29 PDT — README prompt-only run guide

- Outcome: replaced local CLI, fixture, `jq`, and `/tmp` walkthroughs with copyable Codex prompts for normal, manual, and historical backfill runs.
- Contract: Decision and Execution remain separate tasks; prompts carry explicit mode, account/date authority, provenance, routine selection, and safety boundaries.
- Evidence: prompt paths and flags match the current routines and implementation; `git diff --check` passes.
- Scope/risk: documentation only; no runtime, configuration, routine, or state changed.

## 2026-08-25 22:37 PDT — Growth Momentum v2 Lite added

- Outcome: added [`growth_momentum_v2_lite.md`](../strategies/growth_momentum_v2_lite.md), a prompt-defined strategy without the v3 compiler or FCF inputs.
- Safety: source-attributed inputs remain mandatory; uncertainty fails closed, while deterministic risk, timing, and Decision/Execution separation are unchanged.
- Scope: the Strategy Spec is not selected by any Account Lane; configuration, state, broker access, and Execution remain untouched.
- Evidence: catalog and diff/credential checks pass; 44/53 tests pass, with the known 7 failures/2 errors from legacy dry-run tests reading current live/shadow configs.

## 2026-08-25 22:58 PDT — Growth Momentum v2 Lite prompt tightened

- Outcome: added an explicit Decision order, valid no-trade outcomes, centralized failure scope, and a checkable publication self-check to [`growth_momentum_v2_lite.md`](../strategies/growth_momentum_v2_lite.md).
- Evidence rule: growth durability now requires affirmative primary-source support; absence of a discovered problem cannot qualify a BUY.
- Scope: formulas, filters, ranking, sizing, strategy identity, configurations, state, routines, and Execution behavior are unchanged.
- Evidence: catalog/diff/credential checks pass; the full test baseline remains 44/53 with the known legacy dry-run config mismatch.
