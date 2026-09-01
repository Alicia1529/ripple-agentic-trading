# Ripple Trading

Ripple is a small, inspectable experiment in AI-native development and agentic trading. Multiple isolated Account Lanes can select different checked-in investment strategies while sharing deterministic validation and risk rules. The goal is to monitor live and shadow records, understand failures, and build evidence for later human review—not to promise returns.

The repository implements a validated account catalog, a manual dry-run path, and a T+1 quote-based shadow execution path. Hosted schedules and the reviewed live Agentic Robinhood broker-write loop are in place; [`docs/TODO.md`](docs/TODO.md) is the authority on what is still unfinished.

## Requirements and verification

Ripple needs CPython 3.12 or later and nothing else: the deterministic core, the CLI, and the whole test suite use only the standard library. Operators drive it with [`uv`](https://docs.astral.sh/uv/), which reads `.python-version` and selects that interpreter for you.

```bash
uv run --no-cache python -m unittest discover -s tests -t .
uv run --no-cache python -m ripple.mvp validate-configs
```

The first command runs the whole test suite; the second validates every account configuration and its selected Strategy Spec. Without `uv`, run the same commands with any Python 3.12 interpreter from the repository root. A system Python older than 3.12 fails on import, which is a version problem rather than a missing package.

## Run one cycle offline

No model, no API key, no broker connection, no network. This replays a checked-in fixture through the real publisher, the real deterministic risk module, and the real shadow adapter:

```bash
uv run --no-cache python -m ripple.mvp run-shadow-cycle \
  --config config/examples/demo_lane.json \
  --fixture fixtures/mvp/demo_lane_cycle.json \
  --output /tmp/ripple-demo/demo_lane
```

It writes a complete Decision Cycle — `decision_snapshot.json`, `order_plan.json`, `execution.json`, and a readable `report.md` — to `/tmp/ripple-demo/demo_lane/trading_days/2026-08-25/`. The report ends with `No broker write tool was called.` The demo lane lives outside the `config/*.json` glob, so it is invisible to the catalog and can never be selected by a scheduled run. See [`docs/RUNNING.md`](docs/RUNNING.md) to turn it into a lane of your own.

## Actual structure

```mermaid
flowchart TD
    CFG["config/&lt;account_id&gt;.json<br/>filename is the Account Lane identity"]
    SPEC["strategies/&lt;strategy_id&gt;.md"]
    CAT["Account Catalog<br/>rejects a missing Strategy Spec, malformed config,<br/>invalid filename identifier, or a second live lane"]

    CFG -->|"selects one strategy"| SPEC
    CFG --> CAT

    CAT --> LIVE["live: zero or one lane"]
    CAT --> SHDW["shadow: every shadow lane"]
    CAT --> DRY["dry_run: manual development, never scheduled"]

    LIVE --> DEC
    SHDW --> DEC
    DRY -.->|"manual only"| DEC

    DEC["prior-evening Decision<br/>immutable DecisionSnapshot and strategy-attributed OrderPlan"]
    DEC --> EXE["next-trading-day Execution, 9:35 AM ET<br/>deterministic risk: allow, clip, reject, abort, Risk Exit"]

    EXE --> L["live: Agentic Robinhood after the Live Gate"]
    EXE --> S["shadow: no broker call, but the same risk verdict<br/>and the real 9:35 quote still decide<br/>marketable: assumed fill at that quote, else not_filled"]

    L --> ST
    S --> ST
    ST["Lane State: execution.json, report.md, ending virtual account<br/>credential-free evidence written back for every mode"]

    classDef gated stroke-dasharray: 5 4;
    class L,DRY gated;
```

Daily hosting uses four schedule triggers: one live Decision run, one all-shadow Decision run, one live Execution run, and one all-shadow Execution run. A live run may have no selected account; dry-run configurations are never scheduled.

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

Robinhood accepts fractional shares only as regular-hours market orders. Ripple therefore keeps the immutable OrderPlan's LIMIT price as the Decision intent and sizing basis, but converts a risk-allowed Live order whose final quantity is fractional to `MARKET + regular_hours` before direct broker placement. The current quote must first satisfy the planned limit (`BUY quote <= limit`, `SELL quote >= limit`), otherwise deterministic risk rejects it. Integer-share Live orders remain LIMIT orders, and Shadow behavior is unchanged. Because a market order has no hard execution-price cap, the eventual Live fill can slip beyond the planned limit; this is an accepted small-canary risk, not a guaranteed maximum purchase price or minimum sale price.

The designated owner's standing approval authorizes Scheduled Live Execution to place each exact deterministic `broker_order` once without Robinhood review or per-order confirmation. An explicit `--manual-run` invocation supplies the equivalent authority for that manual cycle. Account binding, immutable-plan matching, fresh facts, deterministic risk, stable-ID duplicate checks, the reviewed allocation, and fail-closed ambiguity handling remain mandatory; placement errors and uncertain outcomes stop without retry.

Execution requires positions to match the immutable account baseline exactly. Current broker cash below the frozen baseline aborts the plan; current cash above it is recorded but does not abort and cannot enlarge the plan, because deterministic BUY reservation remains capped at the lower frozen cash value.

For shadow execution, a risk-allowed BUY limit is marketable when the next-trading-day quote is at or below the limit; a SELL limit is marketable when the quote is at or above it. A marketable action is assumed filled at that quote with zero fees and zero slippage. The result records fill attempts and ending virtual account state. These are explicit assumptions, not broker fills.

### Why Decision is prior-evening and Execution is at 9:35 AM

The evening Decision uses completed daily bars and leaves time to gather source evidence before freezing the plan. Execution at 9:35 AM observes the actual regular-session open and a fresh quote while limits anchored to the prior close are still relevant. This fits both the slower [Growth Momentum](strategies/growth_momentum_v3.md) signal and the more time-sensitive [Earnings Drift](strategies/earnings_drift_v1.md) event window. Waiting until noon or 3:00 PM makes the frozen price anchor progressively stale and can favor intraday reversals over the strongest continuations; planning at 3:00 PM would instead use an incomplete session and collapse the Decision/Execution boundary. This is structural rationale, not proof that 9:35 produces better returns.

## Safety model

Deterministic Python controls schemas, account binding, timing, quote freshness, baseline matching, sizing, cash reservation, position caps, loss and drawdown breakers, wash-sale checks, and Risk Exits. Routine prompts control LLM research and tool use. The human owner controls schedules, Robinhood binding, funding, live activation, capital, and restart.

Core limits are 20% per symbol, three new positions per day, 5% daily loss, 10%/15% drawdown tiers, 15-minute quote age, 30-day taxpayer-wide wash-sale lookback, 8% stop loss, and 20% take profit. Missing or inconsistent required data fails closed.

The catalog permits at most one live configuration, but this is not a broker-side security boundary. Live v1 still lacks exactly-once execution and automatic ambiguous-outcome reconciliation. See [`docs/INVARIANTS.md`](docs/INVARIANTS.md) for the full contract.

## Running Ripple

Ripple separates **what a run must do** from **who runs it**. The four prompts in
[`routines/`](routines/) are the durable contract — one per cohort phase — and the Agent Runner
that executes them is replaceable: Codex scheduled tasks drive the current deployment, but nothing
in the Python privileges one product over another.

[`docs/RUNNING.md`](docs/RUNNING.md) states the seven requirements any runner must satisfy, then
gives the prompt library and the setup for each runner known to satisfy them.
[`routines/SCHEDULE.md`](routines/SCHEDULE.md) is the operator-owned schedule manifest.

## Documentation

Each document owns one kind of truth, because what the system *is*, what it must *never* do, what was *decided*, and how to *operate* it all change at different rates. [`docs/README.md`](docs/README.md) is the complete map; this is the short version.

**Understand what it does**

| Document | Answers |
|---|---|
| [`docs/ANATOMY_OF_A_CYCLE.md`](docs/ANATOMY_OF_A_CYCLE.md) | What one cycle actually produces, field by field, from a demo you can rerun. The fastest way in |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the system works today, and where its boundaries sit |
| [`docs/INVARIANTS.md`](docs/INVARIANTS.md) | The 13 rules that may never be broken — the checklist every review runs against |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Which durable choices govern this release, and why they were made that way |
| [`CONTEXT.md`](CONTEXT.md) | What each domain term means, and which tempting synonyms to avoid |
| [`PROPOSAL.md`](PROPOSAL.md) | Why Ripple exists, what it deliberately is not, and the gates between releases |

**Run it**

| Document | Answers |
|---|---|
| [`docs/RUNNING.md`](docs/RUNNING.md) | What any Agent Runner must guarantee, and how to drive Ripple with Codex, Claude Code, or by hand |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | How to verify a working copy, respond to failures, restart after a tier-two lock, and stop everything |
| [`routines/`](routines/) | What each of the four scheduled runs must do — the durable prompt contracts themselves |
| [`docs/TODO.md`](docs/TODO.md) | What is genuinely unfinished, and which gate comes next |

**Change it**

| Document | Answers |
|---|---|
| [`docs/WRITING_A_STRATEGY.md`](docs/WRITING_A_STRATEGY.md) | How to add an investment policy in Markdown, what it may decide, and what it can never loosen |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, scope discipline, the contributions most wanted, and the non-goals already settled |
| [`AGENTS.md`](AGENTS.md) | The working contract for humans and agents alike; read it before changing anything |
| [`SECURITY.md`](SECURITY.md) | What counts as a security issue here, and what to understand before pointing this at a broker |

## Repository map

| Path | Purpose |
|---|---|
| [`config/`](config/) | One filename-identified configuration per Account Lane; [`config/examples/`](config/examples/) holds unscheduled samples |
| [`strategies/`](strategies/) | Version-named Strategy Specs selected by config |
| [`ripple/`](ripple/) | Catalog, artifacts, CLI, trading calendar, deterministic risk, and shadow simulation |
| [`routines/`](routines/) | Live/shadow Decision and Execution contracts plus schedules |
| [`fixtures/`](fixtures/) | Credential-free dry and shadow evidence inputs |
| [`tests/`](tests/) | Catalog, isolation, artifact, risk, timing, calendar, and fill coverage |
| [`docs/`](docs/) | Architecture, invariants, decisions, operations, and unfinished work — see [`docs/README.md`](docs/README.md) |

Canonical state uses lowercase config identifiers and groups each prior-evening Decision and next-trading-day Execution under `state/accounts/<account_id>/trading_days/<trade-date>`.

## What still gates expansion

[`docs/TODO.md`](docs/TODO.md) is the authority on release state, and every live Execution run re-checks its own gate in [`routines/EXECUTION_LIVE.md`](routines/EXECUTION_LIVE.md) before any broker write. Past those, what remains gated is expansion: enough comparable cycles before any claim about relative strategy behavior, a defined review window and after-cost metrics before that comparison means anything, and a reliability review of missed runs, ambiguous outcomes, and prompt drift before a second simultaneous live lane or more capital.

No metric in this repository promotes a strategy or moves capital. A strategy switch, a capital increase, and clearing a tier-two restart lock are human decisions, every time.

Ripple is educational software, not financial advice. Trading involves risk of loss, and live trading and its consequences remain the account owner's responsibility.
