# Ripple Trading

Ripple is a small, inspectable experiment in AI-native development and agentic trading. Multiple isolated Account Lanes can select different checked-in investment strategies while sharing deterministic validation and risk rules. The goal is to monitor live and shadow records, understand failures, and build evidence for later human review—not to promise returns.

The repository now implements a validated account catalog, a manual dry-run lane, and a T+1 quote-based shadow execution path. Hosted schedules and the reviewed live Agentic Robinhood broker-write loop remain unfinished, so no configuration is live today.

## Actual structure

```text
strategies/*.md
       ↑ config selects one strategy
config/<account_id>.json
       │ filename is the identifier
       ▼
 Account Catalog
 ├─ live:    zero or one lane
 ├─ shadow:  every shadow lane
 └─ dry_run: manual development only
       │
       ├─ prior-evening Decision
       │    → immutable strategy-attributed OrderPlan
       └─ next-weekday Execution
            → deterministic risk
               ├─ live: Agentic Robinhood after Live Gate
               └─ shadow: assumed T+1 quote fill, no broker call
```

Daily hosting uses four schedule triggers: one live Decision run, one all-shadow Decision run, one live Execution run, and one all-shadow Execution run. A live run may have no selected account; dry-run configurations are never scheduled.

## Current lanes

| Account | Mode | Strategy | Purpose |
|---|---|---|---|
| `account_a` | `dry_run` | `growth_momentum_v1` | Manual fixture-backed development and future live candidate |
| `account_b` | `shadow` | `growth_momentum_v1` | Virtual T+1 execution evidence without Robinhood writes |

Both currently use the same strategy because this change does not invent a second investment policy. Add a new version-named file under `strategies/` and select it from another account configuration to begin a meaningful strategy comparison.

Each account configuration contains:

- a narrative `description` of its purpose, strategy, universe, and risk constraints;
- a `strategy` identifier that must resolve to `strategies/<strategy>.md`;
- `execution.mode` in `live`, `shadow`, or `dry_run`;
- its allowed symbol universe and deterministic risk values; and
- `shadow.initial_cash` when it owns a virtual portfolio.

Catalog validation rejects a missing Strategy Spec, malformed config, invalid filename identifier, or more than one live lane.

## Decision and execution

The Decision Routine gathers allowed facts, follows only the selected Strategy Spec, and publishes an immutable `DecisionSnapshot` and `OrderPlan`. The plan freezes both `account_id` and `strategy_id`. Decision has no order-review, place, cancel, or modification authority.

The separate Execution Routine gathers current account facts and quotes and runs deterministic risk code. It can allow, scale down, reject, or abort planned actions; it cannot form a new thesis. A deterministic full-position stop-loss/take-profit Risk Exit is the only unplanned-order exception.

For shadow execution, a risk-allowed BUY limit is marketable when the next-weekday quote is at or below the limit; a SELL limit is marketable when the quote is at or above it. A marketable action is assumed filled at that quote with zero fees and zero slippage. The result records fill attempts and ending virtual account state. These are explicit assumptions, not broker fills.

## Safety model

Deterministic Python controls schemas, account binding, timing, quote freshness, baseline matching, sizing, cash reservation, position caps, loss and drawdown breakers, wash-sale checks, and Risk Exits. Routine prompts control LLM research and tool use. The human owner controls schedules, Robinhood binding, funding, live activation, capital, and restart.

Core limits are 20% per symbol, three new positions per day, 5% daily loss, 10%/15% drawdown tiers, 15-minute quote age, 30-day taxpayer-wide wash-sale lookback, 8% stop loss, and 20% take profit. Missing or inconsistent required data fails closed.

The catalog permits at most one live configuration, but this is not a broker-side security boundary. Live v1 still lacks exactly-once execution and automatic ambiguous-outcome reconciliation. See [`docs/INVARIANTS.md`](docs/INVARIANTS.md) for the full contract.

## Run locally

Requirements: Python 3.12 and [`uv`](https://docs.astral.sh/uv/). These commands use checked-in fixtures and no broker credentials.

Validate the catalog and cohorts:

```bash
uv run --no-cache python -m ripple.mvp validate-configs
uv run --no-cache python -m ripple.mvp list-accounts --mode live
uv run --no-cache python -m ripple.mvp list-accounts --mode shadow
uv run --no-cache python -m ripple.mvp list-accounts --mode dry_run
```

Run the dry and shadow fixture lanes:

```bash
uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/account_a.json \
  --fixture fixtures/mvp/dry_cycle.json \
  --output /tmp/ripple-mvp/account_a

uv run --no-cache python -m ripple.mvp run-shadow-cycle \
  --config config/account_b.json \
  --fixture fixtures/mvp/dry_cycle_account_b.json \
  --output /tmp/ripple-mvp/account_b
```

Run the tests:

```bash
env PYTHONDONTWRITEBYTECODE=1 uv run --no-cache python -m unittest \
  tests.test_account_config \
  tests.test_decision_snapshot \
  tests.test_order_plan \
  tests.test_risk \
  tests.test_shadow_execution \
  tests.test_mvp_cycle
```

## Repository map

| Path | Purpose |
|---|---|
| [`config/`](config/) | One filename-identified configuration per Account Lane |
| [`strategies/`](strategies/) | Version-named Strategy Specs selected by config |
| [`ripple/`](ripple/) | Catalog, artifacts, CLI, deterministic risk, and shadow simulation |
| [`routines/`](routines/) | Live/shadow Decision and Execution contracts plus schedules |
| [`fixtures/`](fixtures/) | Credential-free dry and shadow evidence inputs |
| [`tests/`](tests/) | Catalog, isolation, artifact, risk, timing, and fill coverage |
| [`docs/`](docs/) | Architecture, decisions, invariants, operations, and unfinished work |

Existing `state/accounts/account_A` files are read-only legacy fixture evidence. New canonical state uses lowercase config identifiers and does not rewrite those historical artifacts.

## Current gates

Before any lane becomes live, Ripple still needs the reviewed Robinhood read/review/place/cancel loop, intended-account binding proof, scheduled hosted acceptance, real cash/position reconciliation, and explicit owner approval. A strategy switch or capital increase remains a separate human decision.

Read [`PROPOSAL.md`](PROPOSAL.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/TODO.md`](docs/TODO.md), and [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the complete current model.

Ripple is educational software, not financial advice. Live trading and its consequences remain the account owner's responsibility.
