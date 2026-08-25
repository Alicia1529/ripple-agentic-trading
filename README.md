# Ripple Trading

Ripple is a small, inspectable experiment in **AI-native development** and **agentic trading**. It explores how an LLM can make bounded portfolio decisions while ordinary Python code remains responsible for deterministic validation, position sizing, and risk controls.

The repository currently contains a fixture-backed **dry-run MVP for exactly two isolated Robinhood account lanes**. It can produce plans and simulated execution records, but the live broker call loop and hosted acceptance gates are not complete. It is a learning project—not a production trading bot or a promise of returns.

## What this project explores

Ripple has two connected learning goals:

- **AI-native development:** use agents to explore a problem, compile it into a small approved scope, implement one testable slice, and preserve the reasoning and operating boundaries in the repository.
- **Agentic trading:** give an LLM a narrow Decision role, then pass its immutable plan to a separate Execution role constrained by deterministic code and explicit human-owned live gates.

The central question is not “can an AI pick stocks?” It is: **what boundaries, artifacts, checks, and operating practices make an agent-driven trading loop understandable and reviewable?**

## How the loop works

```text
Latest completed market session
              │
              ▼
     Decision Routine (LLM)
     facts → thesis → OrderPlan
              │
              │ immutable, credential-free plan
              ▼
   Next-morning Execution Routine
   current facts → deterministic checks
              │
       ┌──────┼────────┐
       ▼      ▼        ▼
    execute  scale    abort
    dry run   down    safely
```

Each account lane has its own configuration, state directory, schedules, broker connection, risk state, and human-controlled live switch. The lanes share schemas and risk code, but one account can never authorize work in the other.

## Where safety lives

Ripple deliberately separates deterministic checks from agent behavior. **Code calculates what is allowed; prompts tell the LLM how to operate; humans decide whether live trading is enabled.** These layers are useful, but they are not equivalent guarantees.

### Deterministic checks in code

The checked-in Python code validates every plan and execution context and returns explicit `allowed`, `partial`, `rejected`, or `aborted` results with reason codes.

| Check | Current behavior |
|---|---|
| Account and input integrity | Require exact schemas, timezone-aware timestamps, matching `account_id` values, valid decimal strings, and a configured symbol universe. Malformed or mismatched input fails closed. |
| Order shape | Accept only positive-share `BUY` or `SELL` orders. Planned orders must be `LIMIT`, `regular_hours`, and `gfd`; shorts, leverage, and options are outside the model. |
| Quote coverage and freshness | Require a quote for every held or planned symbol. A missing quote or one older than 15 minutes aborts planned trading. |
| Decision baseline | Abort planned trading when current cash or positions differ from the immutable plan baseline. |
| Price movement | Reject an order when its current price moves beyond the tolerance recorded in the plan; the plan schema caps that tolerance at 10%. |
| Available cash | Reserve BUY cash cumulatively at the limit price and clip or reject quantities that do not fit. |
| Position size | Clip or reject a BUY that would take one symbol above 20% of account equity. |
| New positions | Permit at most 3 new positions per account per day. |
| Daily loss | Block new BUYs when daily loss reaches 5% of account equity; safely computable exits remain available. |
| Drawdown | At 10% drawdown, block new BUYs. At 15%, persist a lane-specific lock that requires human review and restart. |
| Wash sale | Block a BUY when the same symbol has a visible loss sale within the taxpayer-wide 30-day lookback. |
| Position exits | At an 8% loss or 20% gain from average cost, emit a deterministic full-position Risk Exit. |
| Sell quantity | Reject a SELL with no position and clip a quantity that exceeds the shares currently held. |

The risk engine is authoritative for sizing and permission. It does not choose investments, move money, or call the broker.

### LLM and workflow constraints

The agents handle work that cannot be reduced to the current deterministic rules:

- the **Decision LLM** gathers allowed facts, follows the checked-in strategy, forms the investment view, and publishes an immutable plan;
- the **Execution LLM** gathers current account facts, runs the risk code, and must use its output verbatim without adding a new thesis or inventing a trade;
- both routines must respect their assigned account, time window, Git state, existing plan/order history, credential boundary, and stop conditions;
- an ambiguous broker outcome stops the run and must not be blindly retried.

These are prompt- and process-enforced constraints. The current MVP does **not** provide a code-level barrier that prevents an LLM from calling the wrong tool, misreading deterministic output, passing incorrect broker arguments, or making a duplicate call. Dry-run mode makes no broker write, and the reviewed live MCP call loop is still unfinished.

### Human controls

Only the owner can bind broker accounts, fund them, change a lane from `dry_run` to `live`, clear a tier-two drawdown lock, increase capital, or add another account. Disabling the hosted schedules is the strongest operational stop.

See [`docs/INVARIANTS.md`](docs/INVARIANTS.md) for the complete non-negotiable safety checklist.

## Try the dry-run MVP

Requirements: Python 3.12 and [`uv`](https://docs.astral.sh/uv/). The MVP uses checked-in fixtures and does not require broker credentials.

Run both isolated account lanes:

```bash
uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/mvp.json \
  --fixture fixtures/mvp/dry_cycle.json \
  --output /tmp/ripple-mvp/account_A

uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/mvp-account-b.json \
  --fixture fixtures/mvp/dry_cycle_account_b.json \
  --output /tmp/ripple-mvp/account_B
```

Each command creates an account-scoped snapshot, immutable order plan, execution result, JSONL records, and readable report. Re-running the same cycle against the same output fails instead of overwriting prior evidence. No broker tool is called.

Run the core test suite:

```bash
env PYTHONDONTWRITEBYTECODE=1 uv run --no-cache python -m unittest \
  tests.test_decision_snapshot \
  tests.test_order_plan \
  tests.test_risk \
  tests.test_mvp_cycle
```

## Repository map

| Path | Purpose |
|---|---|
| [`ripple/`](ripple/) | CLI, schemas, validation, and deterministic risk code |
| [`routines/`](routines/) | Hosted Decision and Execution prompts plus schedule |
| [`strategies/`](strategies/) | Account A's current strategy specification |
| [`config/`](config/) | Separate configuration for the two account lanes |
| [`fixtures/`](fixtures/) | Credential-free inputs for reproducible dry cycles |
| [`tests/`](tests/) | Core behavior and invariant coverage |
| [`learning/`](learning/) | Notes and visual references from the AI-native development process |
| [`docs/`](docs/) | Architecture, safety rules, operations, decisions, and current work |

## Learning notes

Ripple also records reusable lessons from building the system with coding agents:

- [`Compile Scope Before Codex Execution`](learning/compile-scope-before-codex-execution.md) — explore broadly, then choose the smallest runnable milestone, define its autonomy boundary, verify it, and stop.

These notes describe the development process; they are not runtime instructions or trading rules.

## Current status

The two-account fixture-backed dry-run path is implemented and covered by tests. Work still required before either lane can trade live includes:

1. observing complete hosted scheduled dry cycles for both accounts;
2. implementing and reviewing the narrow live MCP read/review/place/cancel loop;
3. proving each broker connection selects the intended account;
4. receiving explicit human approval to change each lane from `dry_run` to `live`.

The initial live allocation, if those gates are completed, is intentionally limited to $500–1000 per account. Funding, activation, capital increases, and additional accounts always remain human decisions. Follow progress in [`docs/TODO.md`](docs/TODO.md).

## Read next

- [`PROPOSAL.md`](PROPOSAL.md) — intended outcome and scope
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — current system boundaries and data flow
- [`docs/INVARIANTS.md`](docs/INVARIANTS.md) — non-negotiable safety rules
- [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — operation, recovery, and kill-switch procedures
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — durable architecture decisions

## Disclaimer

Ripple is an educational software project. It is not financial advice, and its dry-run results do not represent real fills or future performance. Live trading and its consequences remain the account owner's responsibility.

Licensed under the [MIT License](LICENSE).
