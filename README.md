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
| `account_a` | `dry_run` | `growth_momentum_v3` | Manual fixture-backed development and future live candidate |
| `account_b` | `shadow` | `earnings_drift_v1` | Event-driven earnings evidence with virtual T+1 execution and no Robinhood writes |

The lanes now select different versioned policies. Account A uses Growth Momentum v3 with deterministically compiled numeric facts. Account B uses Earnings Drift v1 with a `$1000` initial virtual balance; later cycles continue from its latest shadow ending state. This enables attributed comparison evidence but does not automatically rank, promote, or fund either strategy.

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

## Create the scheduled Codex workflows

OpenAI currently exposes Codex automations as **Scheduled tasks** in the ChatGPT desktop app. A scheduled task created from Codex can work in a local Git project, while a web-only task cannot directly access a folder on this computer. See the official [Scheduled tasks documentation](https://developers.openai.com/codex/app/automations).

The files in [`routines/`](routines/) are the durable prompts that a scheduled task reads; they are not executable schedules and are not registered automatically. [`routines/SCHEDULE.md`](routines/SCHEDULE.md) is the operator-owned target schedule manifest. It documents the eventual four-task live/shadow topology, but the current rollout should activate only the two shadow tasks below because there is no live account or approved broker-write loop.

Before creating the tasks:

- open this repository as a local project in the ChatGPT desktop app and select Codex;
- use the intended private state branch, confirm the worktree is clean, and confirm unattended `git pull`/`git push` can use the repository remote;
- keep the computer on, the desktop app running, and the repository available at each trigger time; and
- grant only repository write and network access needed for Git and market facts. Shadow tasks need no Robinhood connection or broker-write permission.

Create two **standalone** scheduled tasks. Choose this local project, not an isolated worktree, so Decision and Execution use the same checked-out branch and credential-free state history. Leave model and reasoning settings at their defaults unless an observed run requires a reviewed change.

| Task name | Time zone and recurrence | Saved prompt |
|---|---|---|
| `Ripple Shadow Decision` | `America/New_York`; Sun–Thu at 9:00 PM. Advanced rule: `RRULE:FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH;BYHOUR=21;BYMINUTE=0` | `Work in the selected Ripple repository. Read routines/DECISION_SHADOW.md completely and follow it exactly. This task owns only the Shadow Decision cohort. Do not perform Execution or live work. If a precondition fails, stop and report it without broadening authority.` |
| `Ripple Shadow Execution` | `America/New_York`; Mon–Fri at 9:35 AM. Advanced rule: `RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=35` | `Work in the selected Ripple repository. Read routines/EXECUTION_SHADOW.md completely and follow it exactly. This task owns only the Shadow Execution cohort. Do not perform Decision or live work. If a precondition fails, stop and report it without broadening authority.` |

The desktop workflow is:

1. Open a Codex chat for this local repository and ask it to create the standalone scheduled task with the name, saved prompt, recurrence, and time zone above. You can also create and later manage it from **Scheduled** in the desktop sidebar.
2. Before enabling recurrence, run each saved prompt once in a normal Codex chat. Confirm catalog validation selects only `account_b` for shadow and no account for live.
3. Enable Shadow Decision first. After its first successful scheduled run, inspect `state/accounts/account_b/trading_days/<trade-date>/order_plan.json` and its `Decision: shadow <date>` commit.
4. Enable Shadow Execution. After the next-weekday run, inspect `execution.json` and `report.md` in that same trade-date directory, including the ending virtual account, and its `Execution: shadow <date>` commit. Confirm no broker call occurred.
5. Review the first few runs in **Scheduled**. Pause a task after a failed precondition, Git conflict, unexpected artifact, credential finding, or timing error; do not backfill a missed cycle.

Do not create or enable the two live tasks yet. They become eligible only after the live tasks in [`docs/TODO.md`](docs/TODO.md) are complete and Alicia explicitly approves the mode change and allocation. Editing a routine changes what the next scheduled run reads; changing a trigger or enabling live remains an operator action in the Scheduled interface and must stay aligned with [`routines/SCHEDULE.md`](routines/SCHEDULE.md).

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

Canonical state uses lowercase config identifiers and groups each prior-evening Decision and next-weekday Execution under `state/accounts/<account_id>/trading_days/<trade-date>`.

## Current gates

Before any lane becomes live, Ripple still needs the reviewed Robinhood read/review/place/cancel loop, intended-account binding proof, scheduled hosted acceptance, real cash/position reconciliation, and explicit owner approval. A strategy switch or capital increase remains a separate human decision.

Read [`PROPOSAL.md`](PROPOSAL.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/TODO.md`](docs/TODO.md), and [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the complete current model.

Ripple is educational software, not financial advice. Live trading and its consequences remain the account owner's responsibility.
