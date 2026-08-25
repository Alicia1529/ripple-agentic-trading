# Current architecture

This document explains how Ripple works today. It is the current technical design, not a roadmap or decision history. Durable reasons and superseded alternatives belong in `docs/DECISIONS.md`; unfinished work belongs in `docs/TODO.md`.

Ripple is a fixture-backed dry-run MVP moving Account A toward hosted acceptance. The repository runs exactly two isolated Robinhood Agentic fixture lanes over one concrete CLI, strict artifacts, and deterministic risk code. Account B has no hosted schedules or bound MCP path.

## System at a glance

Both fixture lanes run the same repository sequence with separate configuration and state. The hosted sequence is currently configured only for Account A:

```text
latest completed market facts + current account facts
                         │
                         ▼
                Decision Routine (LLM)
                 applies lane strategy
                         │
                  publishes once
                         ▼
          DecisionSnapshot + immutable OrderPlan
                         │
                  private Git state
                         │
                 remains unchanged
                         ▼
               Execution Routine (LLM)
          gathers current account facts and quotes
                         │
                         ▼
            deterministic revalidation code
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           execute     scale      reject/abort
              │
              ▼
      dry-run record today; reviewed MCP calls after the live gate
```

The LLM supplies bounded judgment and tool use. Python supplies strict artifact validation and authoritative risk calculations. The owner supplies broker binding, funding, live activation, restart, and expansion decisions.

## Components and responsibilities

| Component | Responsibility | Boundary |
|---|---|---|
| Lane configuration | Names one `account_id`, execution mode, symbol universe, and risk values | One command resolves one configuration; there is no `accounts[]` collection |
| Decision Routine | Gathers allowed facts, applies the assigned strategy, and prepares one decision input | May use required broker reads; never reviews, places, changes, or cancels an order |
| Decision publisher | Validates timing, account, universe, target weights, order shape, and position cap; assigns stable IDs and writes new artifacts | Does not perform research or broker work |
| `DecisionSnapshot` | Freezes the allowed inputs, universe, and timezone-aware `as_of` used by the decision | Contains no credentials or execution outcomes |
| `OrderPlan` | Freezes the target portfolio, proposed orders, decision metadata, and credential-free account baseline | Execution records never mutate it |
| Execution Routine | Loads the published plan, gathers current account facts, runs deterministic checks, and follows their result | Receives no news or new thesis material; cannot invent a trade |
| Risk engine | Produces allowed, clipped, rejected, or aborted actions from the plan, current facts, and configured rules | Does not choose investments or call the broker |
| Lane State | Carries immutable-per-cycle plans plus append-only-style JSONL facts, results, reports, and account-scoped locks between fresh sessions | Git continuity is not a transactional journal |
| Hosted MCP connection | Holds Robinhood authorization and exposes account/broker tools | Credentials and raw authenticated responses stay outside Git and artifacts |

Account A's current strategy is `strategies/growth_momentum_v1.md`. It screens the full configured universe, reviews current holdings, and may publish no trade, one fixed 10% BUY, one full discretionary SELL, or both. The strategy is prompt-defined; there is no strategy-specific Python engine or plugin framework.

## Why Decision and Execution are separate

Decision timing and execution timing solve different problems:

- A decision should use a completed market session and allow after-close facts, such as earnings, time to arrive.
- Execution should use current account state and current prices after the next market opens.
- Keeping investment reasoning out of the session that owns execution capability narrows the role and makes deviations easier to identify.
- Freezing the plan overnight makes the original intent reviewable and prevents next-morning narrative drift.

This split also keeps time semantics honest. A signal that uses Day T's completed close cannot claim a fill at that same close. It may only be evaluated against a Day T+1 execution opportunity.

## One Decision Cycle

### 1. Prior-evening Decision

Account A runs around 9:00 PM `America/New_York` Sunday–Thursday. Sunday uses Friday's completed close plus facts available by Sunday evening; other decisions use the latest completed session.

The fresh Decision Routine:

1. selects one assigned lane and reads only its configuration;
2. gathers the required credential-free market and account facts;
3. applies the lane's checked-in strategy;
4. prepares one strict snapshot, account baseline, target portfolio, and zero or more proposed orders; and
5. calls `publish-decision`, which writes a new `DecisionSnapshot`, `OrderPlan`, and compact decision record.

A missing required fact produces no trade or stops publication rather than authorizing a guess. A second publication for the same owned cycle fails instead of overwriting the existing decision.

### 2. Overnight boundary

The published `OrderPlan` remains unchanged. Git carries the credential-free artifacts into the next fresh session. No trading occurs merely because a plan exists.

### 3. Next-weekday Execution

Account A runs around 9:35 AM `America/New_York`. Waiting past 9:30 avoids treating the most volatile opening minutes as the intended execution point.

The fresh Execution Routine:

1. loads the lane's prior-trading-day plan and configuration;
2. gathers current cash, positions, loss-sale history, order history, and required quotes;
3. builds a strict execution context;
4. runs deterministic revalidation; and
5. records the exact allowed, clipped, rejected, or aborted actions.

Today, `execute-dry-run` writes proposed broker arguments without a broker write. The reviewed live MCP read/review/place/cancel loop is not implemented yet. When it exists and the lane's Live Gate is open, the routine may submit only script-allowed actions exactly as emitted. A script-produced full-position Risk Exit is the sole order permitted without a matching planned order.

Missed cycles are not backfilled. An aborted plan waits for the next normal Decision Cycle.

## Two isolated lanes

| Lane | Configuration | State root | Hosted boundary |
|---|---|---|---|
| Account A | `config/mvp.json` | `state/accounts/account_A` | One Decision schedule, one Execution schedule, one bound MCP connection |
| Account B | `config/mvp-account-b.json` | `state/accounts/account_B` | Fixture-backed only; no hosted schedules or bound MCP path |

For every command, the configuration, plan, execution context, state-root basename, risk state, broker call, and live mode must agree on `account_id`. One lane's plan, failure, lock, or approval cannot authorize work in the other.

Taxpayer-wide loss-sale history is the only documented cross-account input. It may inform the wash-sale check, but it does not merge lane state or execution authority.

There is no coordinator, batch runner, shared ledger, credential abstraction, or third-account support. Adding an Account B hosted path is new scope rather than an implied consequence of its fixture lane.

## Artifacts and state flow

| Artifact | Created by | Used by | Mutability |
|---|---|---|---|
| `DecisionSnapshot` | Decision publisher | Review and reproducibility | Immutable once published |
| `OrderPlan` | Decision publisher | Execution Routine and review | Immutable once published |
| Decision JSONL record | Decision publisher | Continuity and audit review | A new compact fact is appended |
| Execution result | Execution command | Report, review, and duplicate checks | New per cycle; never rewrites the plan |
| Execution JSONL record | Execution command | Continuity and audit review | A new compact fact is appended |
| Human-readable report | Execution command | Operator review | Derived from the execution result |
| Tier-two lock | Execution command after a tier-two breach | Later Execution cycles | Persists until the owner removes that lane's exact lock after review |

Persisted financial values are base-10 decimal strings. Planned orders use positive share quantities and are `LIMIT`, `regular_hours`, and `gfd`; BUY orders carry the decision-stage reason. Artifacts contain stable plan/order IDs and no credentials or account numbers.

## Safety and authority layers

Ripple has three different safety layers. They must not be described as interchangeable:

| Layer | What it controls | What it does not guarantee |
|---|---|---|
| Deterministic code | Schemas, IDs, account binding, plan shape, timing, risk calculations, sizing, clipping, rejection, and abort results | It does not gather facts, choose investments, or directly prevent an LLM from ignoring its result |
| LLM routine contract | Allowed research, role separation, tool selection, exact use of deterministic output, stop conditions, and sanitized artifacts | It is prompt- and process-enforced, not a code-level capability boundary |
| Human/platform control | Broker authorization, live mode, funding, schedule disablement, drawdown restart, and capital/account expansion | It does not make Git transactional or remove broker-call ambiguity |

Account A's hosted Decision session exposes broker write tools because the connection cannot be restricted per tool. The routine may use required reads but must never call review, place, cancel, or any modifying operation. A Decision-stage write is an incident: stop the lane, disable its schedules, and inspect Robinhood.

The Execution Routine must use risk output verbatim, but v1 does not technically prevent it from misreading that output, passing an incorrect argument, or calling a tool twice. Initial live exposure is intentionally small because these are accepted operational risks, not prevented failure modes.

`docs/INVARIANTS.md` is the authoritative review checklist for these boundaries.

## Deterministic revalidation

All limits are evaluated against the assigned lane's account state:

| Rule | Current value | Deterministic result |
|---|---:|---|
| Maximum position | 20% per symbol | Clip to the available room or reject |
| New positions | 3 per account/day | Reject excess new BUYs |
| Daily loss | 5% of account equity | Block new BUYs; exits remain |
| Drawdown tier 1 | 10% from high-water mark | Block new BUYs |
| Drawdown tier 2 | 15% from high-water mark | Persist a human-restart lock; exits remain |
| Quote freshness | 15 minutes | Missing or stale required data aborts planned trading |
| Wash sale | 30-day taxpayer-wide lookback | Block the BUY; never block a safely computable exit |
| Position thresholds | 8% stop loss / 20% take profit | Emit a deterministic full-position Risk Exit |
| Products | Long equities only | Reject unsupported direction or product shapes |

Execution also verifies that current cash and positions match the decision baseline, the symbol remains in the lane universe, price movement stays within the plan tolerance, BUY cost fits cumulatively reserved cash, and SELL quantity does not exceed the holding.

Required-data uncertainty fails closed. Missing quotes, stale quotes, malformed input, account mismatch, or an unsafe sizing calculation authorizes no planned order. Required-data uncertainty suppresses Risk Exits too rather than guessing a quantity or price.

Every action retains the original proposal, triggered rule, actual sizing, readable reason, and `account_id`.

## Git, MCP, and reliability boundaries

### Continuity state

| Store | Holds | Required behavior |
|---|---|---|
| Private Git repository | Code, configuration, plans, compact JSONL facts, results, reports, and locks | Pull before work, write only new credential-free artifacts, commit and push normally, and stop on conflict |
| Hosted MCP connection | Robinhood OAuth state and account authorization | Keep credentials in the platform; reconnect interactively when required |

Git is organizational memory and audit evidence, not transactional submission state. It does not close the interval between broker acceptance and a later log commit, and it provides no cross-runner lease.

### Duplicate and ambiguous outcomes

V1 reduces duplicates with stable IDs, one scheduler per phase and lane, existing-output refusal, repository and visible broker-history checks, first-success ownership, and no blind retry after an ambiguous response.

These guards do not provide exactly-once execution. An MCP timeout, malformed response, or crash near submission stops the run. The owner must inspect Robinhood before any later attempt; the system must not infer success or failure from missing Git evidence.

### Credential boundary

Credentials, tokens, cookies, account numbers, and raw authenticated responses never enter Git, prompts, plans, fixtures, logs, or reports. Account numbers may exist only transiently in tool arguments and session memory.

## Live gates

Account A remains `dry_run` until all four conditions are satisfied:

1. its hosted MCP connection is bound and proven to select the intended Account A broker account;
2. one scheduled prior-evening Decision and next-weekday dry Execution cycle is complete and reviewable;
3. the narrow live MCP read/review/place/cancel loop is implemented and reviewed; and
4. Alicia explicitly changes Account A's mode and approves its initial allocation.

The first Account A live cycles are inspected directly in Robinhood. After eight continuous live weeks, observed performance and incidents permit a capital review; they do not authorize an increase. Capital expansion, an Account B hosted path, or a third account requires explicit new scope and architecture review.

`execution.mode` is human-owned. `dry_run` forbids broker writes, `live` permits only the reviewed loop, and `disabled` stops new work. Disabling hosted schedules is the strongest operational stop. Neither action automatically liquidates existing positions.

## Accepted risks and non-goals

At Account A's initial $500–1000 allocation, the owner accepts prompt/tool-use mistakes, incorrect broker arguments, duplicate calls, ambiguous timeouts, crash-before-log gaps, configuration misuse, prompt injection, and model or prompt drift. These limits must remain explicit in reports and reviews.

The current architecture does not include:

- a third account, shared coordinator, account framework, shared ledger, or comparison/shadow topology;
- a non-LLM executor, transactional journal, cross-runner lease, exactly-once guarantee, or automatic ambiguous-outcome reconciliation;
- self-managed OAuth, additional brokers, intraday trading, tax-lot optimization, or sophisticated execution algorithms;
- a generic strategy/data-provider/plugin framework, analyst ensemble, dashboard, or automatic capital changes; or
- execution-stage investment reasoning or any broker write from the Decision Routine.

Operational procedures and recovery steps belong in `docs/RUNBOOK.md`. Remaining acceptance work belongs in `docs/TODO.md`.
