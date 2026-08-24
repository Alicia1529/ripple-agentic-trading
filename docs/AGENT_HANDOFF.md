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

## 2026-08-23 21:47 PDT — Account A manual trigger correction

- Outcome: limited D29 cadence work to Account A and renamed its explicit override to `--manual-run`.
- Live policy: manual live is approved once the existing MCP call-loop TODO is implemented; it reuses the scheduled routine and risk checks.
- Duplicate rule: first successful manual/scheduled execution wins; later triggers stop and never overwrite or resubmit.
- Evidence: manual live Decision and manual-versus-scheduled execution ownership have focused tests.
- Next: implement and verify the reviewed Account A live MCP call loop before any live Run now.

## 2026-08-23 22:12 PDT — Account A prompt-only Decision isolation

- Evidence: the first real Decision Automation exposed Robinhood write tools and stopped before repository or broker changes.
- Decision: D31 accepts prompt-only non-use for Account A's initial small allocation; visible write tools no longer stop Decision.
- Contract: Decision may call only required reads; any review/place/cancel call is an incident requiring lane disable and Robinhood inspection.
- Automation: current prompt explicitly supersedes the old failure conclusion retained in automation memory.
- Verification: core suite passes 39 tests; `compileall` and `git diff --check` pass.

## 2026-08-24 00:12 PDT — Minimal Account A growth/momentum Decision

- Outcome: added fixed `growth_momentum_v1` input → Decision publication for empty Account A: one 10% BUY or `NO_TRADE`.
- Strategy: code enforces SPY/QQQ, momentum, earnings-distance, ranking, and sizing; the LLM provides sourced business-quality pass/fail evidence.
- Boundary: any existing position stops publication; HOLD/SELL/ROTATE and data-provider infrastructure remain deferred under D32.
- Evidence: the existing Execution dry-run consumed the generated plan; all 44 core tests, `compileall`, and `git diff --check` pass.
- Next: run the updated Account A Decision Automation, inspect its plan, then run Monday Execution dry-run.

## 2026-08-24 — Bounded MVP execution policy

- Outcome: added repository-level guardrails against over-execution to `AGENTS.md`.
- Contract: design, explicit approval, and implementation are separate stages; implementation starts in a new thread and follows only the approved scope.
- Scope guard: new subsystems or changes spanning more than four production files require approval and a smaller alternative.
- Reasoning: Low for small scoped implementation; Medium or High for architecture and difficult debugging.
- Evidence: documentation diff checked with `git diff --check`.

## 2026-08-24 01:46 PDT — Prompt-defined recurring strategy

- Outcome: removed the dedicated growth strategy engine, policy input fixture, and tests; Account A now uses one plain-language strategy with the existing generic Decision publisher.
- Behavior: full-universe screening and current-position review may produce no trade, one 10% BUY, one full SELL, or both; D33 records the accepted prompt-mediated trade-off.
- Automation: the active Account A Decision prompt now follows the strategy document and `publish-decision`; its schedule is unchanged.
- Evidence: 39 core tests, `compileall`, and `git diff --check` pass.
- Next: observe the next Decision and dry Execution; add strategy code only if live evidence shows the prompt path is insufficient.
