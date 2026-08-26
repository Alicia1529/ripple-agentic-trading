# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 22:12 PDT — Backfill Execution enabled

- Outcome: removed the blanket Execution rejection for plans with `decision_run_kind=backfill`; matching manual live/shadow Execution may now consume those immutable plans.
- Safety: normal timing order, deterministic risk, lane/account binding, Live Gate, duplicate, ambiguity, and broker safeguards remain unchanged.
- Evidence: focused backfill tests pass, including a manual Shadow Execution that records a fill from the historical T+1 context; `git diff --check` passes.
- Scope/risk: schedules still never backfill automatically, and backfill evidence must not be represented as a contemporaneous signal.

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
