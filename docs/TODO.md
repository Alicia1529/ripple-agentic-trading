# Current status

Living status doc. Keep only genuinely unfinished work here.

Status: **TWO-ACCOUNT LOCAL DRY-RUN MVP IMPLEMENTED; HOSTED SCHEDULED CYCLES PENDING.** Account A and Account B run the same strict decision/risk CLI independently with separate configurations and account-named state roots. Execution reconciles its decision-time account baseline, fails the cycle on required-data uncertainty, reserves aggregate BUY cash at worst-case limit prices, produces deterministic position Risk Exits, and persists the tier-two restart lock. SQLite, a plain executor, self-managed OAuth, exactly-once execution, a batch account coordinator, third-account support, and shadow strategies are not v1 launch work.

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
- [x] Configure Account A's one hosted Decision schedule and one hosted Execution schedule with an `America/New_York` time/date self-check
- [x] Add Account B's concrete config, fixture, account-scoped state contract, and cross-account rejection test without adding a coordinator
- [x] Observe Account A's hosted Decision capability: its session exposes broker writes; D31 accepts prompt-only non-use for the initial allocation
- [x] Add the simple recurring `growth_momentum_v1` Decision prompt: full-universe screening, current-position review, and at most one BUY plus one full SELL
- [ ] Observe Account A's complete scheduled Day T decision → Day T+1 dry execution
- [ ] Bind Account B's hosted MCP connection to the intended broker account, configure its two schedules, and observe its complete scheduled dry cycle

Account A's Sunday–Thursday Decision and Monday–Friday Execution dry-run Codex schedules are active and the completed temporary scheduler probe is paused. The first manual Decision attempt proved that the hosted session exposes Robinhood write tools and stopped without repository or broker changes. D31 now accepts prompt-only non-use for the initial Account A allocation, so the next manual or scheduled Decision may continue while calling only required read operations. An explicit manual run can publish a Decision in either configured mode; the current execution command remains dry-run only. Manual live Execution is an approved trigger for the still-unimplemented reviewed MCP call loop, not evidence that the call loop exists. Account B schedule work remains separate.

Repository MVP acceptance is complete. Hosted acceptance is complete per lane when its scheduled dry cycle is understandable from the account-scoped OrderPlan, script outputs, JSONL records, and report without using broker write tools.

## Development days 4–7 — two independent small-account canaries

- [ ] Connect a separately bound platform-managed Robinhood MCP to each account's Execution Routine; keep credentials, account numbers, and raw authenticated responses out of Git and logs
- [ ] Verify each connection selects its intended account and confirm the current read/review/place/cancel tool schemas with non-writing or smallest-safe probes
- [x] Record Account A's lack of per-tool hosted isolation and Alicia's D31 acceptance of prompt-only write prohibition for the initial small allocation
- [ ] Keep one scheduler per phase, stable IDs, a pre-submit history/log check, and no immediate blind retry after timeout as best-effort guards
- [x] Finish the operator report, kill-switch instructions, MCP reconnection steps, Git-conflict response, tier-two restart procedure, and manual Robinhood inspection after an ambiguous outcome
- [ ] Alicia reviews each lane's full dry cycle and explicitly changes that lane's human-owned `execution.mode` from `dry_run` to `live`
- [ ] Start each account with its manually approved small validation allocation and monitor its first live cycle; activation may be staggered

The accepted D26 risks—wrong tool arguments, duplicate calls, crash-after-submit/before-log, ambiguous timeout, config misuse, prompt injection, and model/prompt drift—do not block this small-account launch. Do not silently claim that v1 prevents them.

## Eight-week capital review

- [ ] Operate each enabled account for eight continuous weeks and record after-cost performance, drawdown, missed/failed runs, MCP reconnects, Git conflicts, ambiguous outcomes, and any divergence from risk-script output
- [ ] Before any capital increase, explicitly revisit D26 and decide whether evidence justifies retaining LLM execution or requires a non-LLM executor, transactional submission journal, broker idempotency proof, stronger reconciliation, or other controls
- [ ] Record any approved architecture change in `docs/DECISIONS.md`, update `docs/ARCHITECTURE.md`, and let Alicia approve the exact funding change; never increase capital automatically

## Later — expansion beyond two accounts

- [ ] Do not add a third account by copying a config and schedule without review
- [ ] First complete a durable architecture review covering credential isolation, transactional state, duplicate/ambiguous submissions, per-account risk state, and operational ownership
- [ ] Add coordination or account-collection abstractions only when a third concrete lane or shared operation demonstrates the need

## Existing evidence, not launch blockers

- Immutable `DecisionSnapshot`, `OrderPlan`, and `ExecutionEvent` value objects exist with focused tests. Transactional append-only persistence and a complete execution state machine are deferred.
- Local Python MCP bootstrap, fresh-process reuse/refresh, one-account selection, sanitized order-history reads, and a local Codex Automation runtime probe succeeded. Account B binding remains unproven. The local path remains fallback evidence, not the production-v1 credential/runtime design.
- Robinhood review/place/cancel/history schemas are recorded in `docs/feasibility/`; live idempotency and comprehensive outcome reconciliation are unproven and accepted only at the D26 initial-allocation boundary.
