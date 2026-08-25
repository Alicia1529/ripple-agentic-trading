# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-24 23:55 PDT — Account B Earnings Drift strategy

- Outcome: added [`earnings_drift_v1`](../strategies/earnings_drift_v1.md), selected it for `account_b`, and changed first-cycle virtual cash to `$1000`.
- Design: adapted event research and thesis metadata to `DecisionSnapshot.inputs`; shared OrderPlan, deterministic risk, T+1 timing, and lane isolation are unchanged.
- Evidence: catalog/cohort validation, 36 focused-snapshot and 41 combined-worktree tests, Account B fixture cycle, artifact inspection, credential scan, and `git diff --check` pass.
- Next/risk: observe a sourced scheduled cycle; the fixture proves plumbing, not the strategy's research quality or comparative performance.

## 2026-08-24 23:58 PDT — Account A Growth Momentum v2

- Outcome: added [`growth_momentum_v2`](../strategies/growth_momentum_v2.md) and selected it for dry-run `account_a`; Account B files and state were not changed by this task.
- Design: added optional BUY `gap_cancel_above` with required `session_open`; above-threshold opens reject and missing opens fail closed, while legacy plans remain valid.
- Evidence: catalog/cohorts, 41 core tests, Account A fixture attribution, policy scan, and `git diff --check` pass.
- Next/risk: exercise a sourced v2 Decision; the deterministic 10% tolerance cap and unfinished Live Gate remain in force.

## 2026-08-25 00:31 PDT — Routine Python entrypoints

- Outcome: replaced every bare Ripple CLI `python` call in the four scheduled routines with the repository-standard `uv run --no-cache python` entrypoint.
- Scope: routine prompts and this rolling handoff only; no config, state, broker, Decision, or Execution changes.
- Evidence: catalog validation and all three cohort listings pass; no bare routine entrypoint remains; `git diff --check` passes.
- Test risk: 41 core tests currently fail (9 failures, 8 errors) because committed `account_a` is live with an expanded universe while tests still expect dry-run/old fixtures.
- Next: reconcile that pre-existing config/test mismatch separately before relying on the full suite.
