# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 00:31 PDT — Routine Python entrypoints

- Outcome: replaced every bare Ripple CLI `python` call in the four scheduled routines with the repository-standard `uv run --no-cache python` entrypoint.
- Scope: routine prompts and this rolling handoff only; no config, state, broker, Decision, or Execution changes.
- Evidence: catalog validation and all three cohort listings pass; no bare routine entrypoint remains; `git diff --check` passes.
- Test risk: 41 core tests currently fail (9 failures, 8 errors) because committed `account_a` is live with an expanded universe while tests still expect dry-run/old fixtures.
- Next: reconcile that pre-existing config/test mismatch separately before relying on the full suite.

## 2026-08-25 00:37 PDT — Account B manual Shadow Decision

- Outcome: published the Alicia-authorized manual 2026-08-24 Decision for `account_b`; `earnings_drift_v1` produced plan `a664f9e2-4cec-5a6f-a399-0836dc4ddefa` with zero orders and 100% cash.
- Evidence: catalog/cohort validation, sourced three-session universe screen, artifact/schema inspection, credential scan, and `git diff --check` pass.
- Tests: 41 core tests ran; the documented `account_a` mode/universe fixture mismatch remains at 9 failures and 8 errors.
- Next/risk: 2026-08-25 Shadow Execution may consume this plan; the manual provenance is explicit and no broker or Execution work occurred.

## 2026-08-25 01:00 PDT — Manual live routine timing override

- Outcome: Live Decision and Execution routines now permit Alicia-authorized manual invocation outside scheduled windows while retaining manual provenance.
- Scope: routine instructions and this rolling handoff only; no broker adapter, risk, schema, configuration, state, or Live Gate change.
- Safety: manual mode changes timing only and cannot bypass account binding, deterministic risk, duplicate/ambiguity checks, immutability, or the unfinished broker-write gate.
- Evidence: routine inspection and `git diff --check` pass; 41 core tests retain the pre-existing config/fixture mismatch at 9 failures and 8 errors, including all three targeted manual-run tests.
- Next/risk: implement and review the live adapter before any manual or scheduled broker write.
