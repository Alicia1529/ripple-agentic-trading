# Agent handoff

Every agent working in this repository reads these rules and the latest three entries before starting. Entries are chronological, newest at the bottom.

Before handing off, append one entry with local timestamp, outcome, evidence, next action, and only material risk. Limit each entry to 100 words and five bullets. Link to code, decisions, or TODO instead of repeating durable context. Never rewrite older entries except to correct a factual error.

## 2026-08-23 11:28 PDT — Whole-repository review fixes

- Outcome: fixed the approved MVP and two-account review findings in commit `67578cb`.
- Contracts: account reconciliation, fail-closed quotes, aggregate limit-price cash reservation, deterministic Risk Exits, New York time/state-root guards, and the tier-two restart lock are recorded in D28.
- Evidence: full discovery passed 97 tests; `compileall` and `git diff --check` passed.
- Next: complete the hosted Account A dry cycle and Account B MCP binding/scheduled dry cycle tracked in `docs/TODO.md`.
- Risk: D26/D27 execution ambiguity and exactly-once limitations remain intentionally deferred.

## 2026-08-23 11:28 PDT — Compact handoff protocol

- Outcome: replaced the one-time review handoff with this append-only `docs/AGENT_HANDOFF.md` recency index.
- Contract: every agent reads only the rules and latest three entries, then appends one entry before handoff.
- Context bound: each entry is at most 100 words and five bullets; authoritative detail stays in code, decisions, and TODO.
- Next: future agents append at the bottom using local time.

## 2026-08-23 21:23 PDT — Sunday cadence and manual rehearsal

- Outcome: changed Decision cadence to Sunday–Thursday so Sunday plans target Monday; Execution remains Monday–Friday.
- Manual path: explicit `--manual-dry-run` permits immediate staged rehearsal only in `dry_run` and records `run_kind=manual`.
- Automation: Account A Decision schedule and both Run now prompts were updated in Codex; live timing guards remain closed.
- Evidence: core suite passes 38 tests; `compileall` and `git diff --check` pass.
- Next: Alicia may Run now Decision then Execution, or wait for the next scheduled dry cycle.
