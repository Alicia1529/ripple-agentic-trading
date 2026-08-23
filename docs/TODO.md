# Current status

Living status doc. Keep only genuinely unfinished work here.

Status: **LOCAL DRY-RUN MVP IMPLEMENTED; FIRST HOSTED SCHEDULED CYCLE PENDING.** The repository now has strict decision publication, deterministic risk revalidation, separate Decision/Execution CLI commands, fixture-backed end-to-end acceptance, credential-free JSON/JSONL/report output, and exact hosted routine contracts. Production v1 remains one Robinhood account. SQLite, a plain executor, self-managed OAuth, exactly-once execution, multi-account support, and shadow strategies are not v1 launch work.

## Development day 1 — deterministic core

- [x] Freeze the first strategy's universe, schedule, and minimum input set; do not add a plugin system or generic strategy interface
- [x] Implement only the sizing, position-cap, order-count, loss/drawdown, prohibited-product, price-tolerance, available-cash, wash-sale, and position-threshold calculations used by the first run
- [x] Make the scripts accept and return strict credential-free JSON with base-10 decimal strings
- [x] Add focused fixture tests for allowed, clipped, rejected, stale-price, malformed-input, and non-live mode cases
- [x] Finish only the `OrderPlan` semantic checks needed by those scripts and the hosted routines

## Development day 2 — Decision Routine

- [x] Write the narrow Decision Routine contract: fresh session, approved read-only inputs, no Robinhood write tools, no credential handling
- [x] Produce exactly one strict per-cycle DecisionSnapshot and OrderPlan with stable plan/order IDs and `account_id`
- [x] Append one compact credential-free JSONL decision record
- [x] Document pull-before-run, commit/push-after-run, and fail-on-conflict behavior in the routine contract
- [x] Test the command and scripts against fixed fixtures; reject unknown fields, malformed output, and any proposed instrument outside the configured universe

## Development day 3 — dry-run MVP

- [x] Write the isolated Execution Routine contract: load only the published plan/config/account facts, never investment news or thesis material
- [x] Re-run deterministic checks and permit only execute-as-is, downward scaling, rejection, or whole-plan abort
- [x] In `dry_run`, emit credential-free proposed Robinhood arguments without invoking write tools; append compact JSONL results and a report
- [ ] Configure exactly one hosted Decision schedule and one hosted Execution schedule with an `America/New_York` time/date self-check; verify the Decision environment excludes broker write capability
- [ ] Observe one complete scheduled Day T decision → Day T+1 dry execution; resolve any schedule, repository, schema, or risk-script defect

MVP is complete when that scheduled dry cycle is understandable from the OrderPlan, script outputs, JSONL records, and report without using broker write tools.

## Development days 4–7 — one-account live canary

- [ ] Connect the platform-managed Robinhood MCP only to the Execution Routine; keep credentials and raw authenticated responses out of Git and logs
- [ ] Verify one explicit account is selected and confirm the current read/review/place/cancel tool schemas with non-writing or smallest-safe probes
- [ ] Verify the Decision Routine cannot access broker write tools; if the hosted platform cannot provide that capability separation, do not launch on it
- [ ] Keep one scheduler per phase, stable IDs, a pre-submit history/log check, and no immediate blind retry after timeout as best-effort guards
- [ ] Finish the operator report, kill-switch instructions, MCP reconnection steps, Git-conflict response, and manual Robinhood inspection after an ambiguous outcome
- [ ] Alicia reviews one full dry cycle and explicitly changes the human-owned `execution.mode` from `dry_run` to `live`
- [ ] Start with the manually approved small validation allocation and monitor the first live cycle

The accepted D26 risks—wrong tool arguments, duplicate calls, crash-after-submit/before-log, ambiguous timeout, config misuse, prompt injection, and model/prompt drift—do not block this small-account launch. Do not silently claim that v1 prevents them.

## Eight-week capital review

- [ ] Operate the single account for eight continuous weeks and record after-cost performance, drawdown, missed/failed runs, MCP reconnects, Git conflicts, ambiguous outcomes, and any divergence from risk-script output
- [ ] Before any capital increase, explicitly revisit D26 and decide whether evidence justifies retaining LLM execution or requires a non-LLM executor, transactional submission journal, broker idempotency proof, stronger reconciliation, or other controls
- [ ] Record any approved architecture change in `docs/DECISIONS.md`, update `docs/ARCHITECTURE.md`, and let Alicia approve the exact funding change; never increase capital automatically

## Later — multi-account expansion

- [ ] Do not add a second account by copying the routine
- [ ] First complete a durable architecture review covering credential isolation, transactional state, duplicate/ambiguous submissions, per-account risk state, and operational ownership
- [ ] Then add the smallest second-account seam without changing the proven single-account domain behavior

## Existing evidence, not launch blockers

- Immutable `DecisionSnapshot`, `OrderPlan`, and `ExecutionEvent` value objects exist with focused tests. Transactional append-only persistence and a complete execution state machine are deferred.
- Local Python MCP bootstrap, fresh-process reuse/refresh, one-account selection, sanitized order-history reads, and a local Codex Automation runtime probe succeeded. This remains a fallback/hardening path, not the production-v1 credential/runtime design.
- Robinhood review/place/cancel/history schemas are recorded in `docs/feasibility/`; live idempotency and comprehensive outcome reconciliation are unproven and accepted only at the D26 initial-allocation boundary.
