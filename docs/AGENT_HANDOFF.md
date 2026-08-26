# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 22:19 PDT — README manual and backfill commands

- Outcome: expanded [`README.md`](../README.md#manual-runs) with copyable manual Decision/Shadow Execution and historical Decision/Execution examples.
- Contract: documented input shapes, canonical plan paths, run provenance, backfill timing/mode/overwrite limits, and unchanged safety checks.
- Evidence: every shown flag matches current CLI help and `git diff --check` passes.
- Scope/risk: documentation only; no runtime, configuration, routine, or state artifact changed.

## 2026-08-25 22:23 PDT — Decision rationale published

- Outcome: every new Decision now requires a concise `decision_rationale`; the OrderPlan persists it and `publish-decision` prints it after the plan ID.
- Semantics: rationale explains the final portfolio/orders; warnings remain input-quality or uncertainty evidence. Legacy OrderPlans without rationale remain readable.
- Scope: updated the shared publisher/schema, active Strategy Specs, fixtures, domain/architecture records, and focused tests; Execution and deterministic risk are unchanged.
- Evidence: 7 focused tests, compileall, JSON parsing, and `git diff --check` pass. Full 53-test run retains the known 7 failures/2 errors from legacy dry-run tests using current live/shadow configs.

## 2026-08-25 22:24 PDT — README inputs made runnable

- Outcome: corrected [`README.md`](../README.md#manual-runs) so manual and backfill examples create their Decision and Execution input files before invoking the CLI.
- Clarity: distinguished fixture-only wiring demos from real point-in-time research inputs and explained that `/tmp` paths are caller-created, not repository fixtures.
- Evidence: both documented command sequences ran end to end and produced an allowed one-action Shadow cycle; `git diff --check` passes.
- Scope/risk: documentation only; examples write under fresh `/tmp` directories and do not modify canonical state.
