# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 22:05 PDT — Decision-only historical backfill

- Outcome: `publish-decision --historical-backfill` now permits explicitly attributed live/shadow historical Decisions while rejecting dry-run, future/off-window timestamps, overwrite, and Execution use.
- Scope: no historical Execution, broker order, Shadow Fill, risk rule, account binding, or state rewrite authority was added; schedules still never backfill automatically.
- Evidence: three focused tests pass; live/shadow CLI smoke runs each wrote only immutable snapshot/plan artifacts labeled `backfill`; compileall and `git diff --check` pass.
- Tests/risk: full 52-test core run retains the pre-existing 7 failures/2 errors because legacy dry-run tests reference the now-live `account_a` config; point-in-time input completeness remains owner-reviewed.

## 2026-08-25 22:11 PDT — Account B historical Shadow Decision

- Outcome: owner-authorized backfill published `account_b`/`earnings_drift_v1` plan `7a0dae3e-23a8-5251-ac17-e141277fe1b9` for trade date 2026-08-26; it holds 100% cash with zero orders.
- Evidence: the complete point-in-time snapshot was restored from commit `1b9d2de`; its SHA-256 matches exactly, and the plan is labeled `backfill`.
- Verification: catalog/cohort checks, JSON parsing, credential scan, and `git diff --check` pass; the backfill safety tests pass.
- Tests/risk: full 52-test run retains the known 7 failures/2 errors in legacy dry-run tests against current live/shadow configs; no Execution, fill, broker, or live work occurred.

## 2026-08-25 22:12 PDT — Backfill Execution enabled

- Outcome: removed the blanket Execution rejection for plans with `decision_run_kind=backfill`; matching manual live/shadow Execution may now consume those immutable plans.
- Safety: normal timing order, deterministic risk, lane/account binding, Live Gate, duplicate, ambiguity, and broker safeguards remain unchanged.
- Evidence: focused backfill tests pass, including a manual Shadow Execution that records a fill from the historical T+1 context; `git diff --check` passes.
- Scope/risk: schedules still never backfill automatically, and backfill evidence must not be represented as a contemporaneous signal.
