# Anatomy of one Decision Cycle

`docs/ARCHITECTURE.md` describes the system in general. This document follows one concrete cycle
from evening decision to next-trading-day evidence, using the offline demo so every value below is
reproducible on your machine.

```bash
uv run --no-cache python -m ripple.mvp run-shadow-cycle \
  --config config/examples/demo_lane.json \
  --fixture fixtures/mvp/demo_lane_cycle.json \
  --output /tmp/ripple-demo/demo_lane
```

Everything lands in one directory named for the **trade date** — the next `America/New_York`
regular session the orders are meant to reach, resolved through the checked-in trading calendar
rather than by weekday arithmetic, and not the evening the decision was made:

```text
/tmp/ripple-demo/demo_lane/trading_days/2026-08-25/
├── decision_snapshot.json   written the prior evening
├── order_plan.json          written the prior evening
├── execution.json           written the trading day, 9:35 AM
└── report.md                written the trading day, 9:35 AM
```

Keeping both halves of a cycle in one directory is what makes the Day T → Day T+1 boundary
inspectable: you can never accidentally review a decision next to another day's fills.

## 1. `decision_snapshot.json` — what the decision was allowed to know

```json
{
  "snapshot_id": "10de633f-be1f-4548-944a-76b94296ed5b",
  "as_of": "2026-08-24T20:55:00-04:00",
  "universe": ["AAPL", "MSFT", "NVDA", "…"],
  "inputs": { "market": { "AAPL": { "close": "100.00" } } }
}
```

The snapshot freezes the inputs, not the reasoning. `as_of` is when the facts were true; `universe`
is the lane's configured symbol set, so a later reader can tell that a symbol was *not considered*
rather than *considered and rejected*. In a real cycle `inputs` also carries compiled deterministic
facts, source URLs, warnings, and candidate-rejection evidence — often thousands of lines.

Money is always a **base-10 decimal string**, never a float. `"100.00"` survives a round trip; a
float does not.

This file is immutable. Publishing twice for the same lane and date fails rather than overwriting
it, so evidence cannot be quietly revised after an outcome is known.

## 2. `order_plan.json` — what the decision intends

```json
{
  "order_plan_id": "2cd39959-d5a3-5bb1-847e-e8604bdea1f1",
  "decision_snapshot_id": "10de633f-be1f-4548-944a-76b94296ed5b",
  "account_id": "demo_lane",
  "strategy_id": "growth_momentum_v1",
  "decision_run_kind": "fixture",
  "decision_time": "2026-08-24T21:00:00-04:00",
  "decision_rationale": "AAPL is the selected eligible strategy candidate; target a 10% position …",
  "account_baseline": { "cash": "720", "positions": {} },
  "target_portfolio": { "AAPL": "0.10", "cash": "0.90" },
  "orders": [ … ]
}
```

Four fields carry the audit trail:

| Field | Why it is frozen here |
|---|---|
| `account_id` | The lane that owns this plan. Execution refuses a plan whose account differs from its own. |
| `strategy_id` | Which Strategy Spec produced it. A later comparison does not have to trust today's config. |
| `decision_snapshot_id` | The exact inputs behind it. |
| `decision_run_kind` | `scheduled`, `manual`, `backfill`, or `fixture`. A backfilled plan can never be mistaken for a contemporaneous signal. |

`decision_rationale` is investment judgment in plain language — the *why* behind the final
portfolio, including a no-trade result. It is deliberately distinct from data-quality warnings
(which live in the snapshot) and from deterministic reason codes (which appear at execution).

`account_baseline` is the account the decision believed it was acting on. Execution re-checks it
against reality and aborts on a mismatch, which is what stops a plan built on a stale balance.

Each order is fully specified before the market opens:

```json
{
  "order_id": "f85c6b8b-e233-5415-8388-3a972ce376d1",
  "symbol": "AAPL", "side": "BUY", "quantity": "0.5",
  "order_type": "LIMIT", "limit_price": "101.00",
  "reference_price_at_decision": "100.00",
  "price_tolerance_pct": "0.01",
  "market_hours": "regular_hours", "time_in_force": "gfd",
  "buy_reason": "AAPL is the selected eligible strategy candidate."
}
```

`limit_price` is anchored to `reference_price_at_decision` — the prior session's completed close — and
`price_tolerance_pct` caps how far the two may drift apart before execution rejects the order. That
pair is what keeps an overnight gap from turning a stale limit into an unintended fill.

## 3. The overnight boundary

Nothing happens. The plan is not revisited, re-scored, or refreshed. Git carries the two files into
a completely fresh session, and Execution receives no new investment thesis. The separation is the
point: the thing that decided *what to want* is gone by the time anything can trade.

## 4. `execution.json` — what deterministic code allowed, and what it assumed

At 9:35 AM on the trade date, Execution loads the plan, current account state, loss-sale history, and fresh
quotes, then runs the shared risk module. The file has three layers.

**The verdict**, per action:

```json
{
  "order_id": "f85c6b8b-…", "symbol": "AAPL", "side": "BUY",
  "allowed": true, "reason_code": "allowed",
  "original_sizing": { "field": "quantity", "value": "0.5" },
  "actual_sizing":   { "field": "quantity", "value": "0.5" },
  "broker_order": { "type": "limit", "side": "buy", "quantity": "0.5", "limit_price": "101.00", … }
}
```

`original_sizing` and `actual_sizing` are separate on purpose. When a position cap or cash
reservation shrinks an order, both numbers survive, so a later reader sees that risk *clipped* the
order rather than that the strategy asked for less. `broker_order` is the exact argument set a live
adapter would submit — identical in shadow mode, simply never sent.

**The fill attempt**, which is where shadow mode differs from live mode and nowhere else:

```json
{
  "order_id": "f85c6b8b-…", "symbol": "AAPL", "side": "BUY", "quantity": "0.5",
  "status": "filled", "price": "100.50",
  "filled_at": "2026-08-25T09:35:00-04:00",
  "reason_code": "assumed_t_plus_one_quote_fill"
}
```

The trade-date quote of `100.50` is at or below the `101.00` limit, so the order is marketable and is
assumed filled **at the quote**, with zero fees and zero slippage. Had the quote opened above the
limit, this entry would read `not_filled` with `reason_code: limit_not_marketable`, and the
position would simply not exist. Shadow mode skips the broker call — it does not skip the check.

**The ending account**, which becomes the next cycle's starting point:

```json
{
  "cash": "669.75",
  "positions": { "AAPL": { "quantity": "0.5", "average_cost": "100.5" } },
  "new_positions_today": 1,
  "loss_sales": [],
  "equity": "800", "daily_pnl": "0", "high_water_mark": "800"
}
```

`720 − 0.5 × 100.50 = 669.75`. The fill derives `cash`, `positions`, `average_cost`,
`new_positions_today`, and `loss_sales`. It **carries through** `equity`, `daily_pnl`, and
`high_water_mark` unchanged — those are re-marked from current quotes before the next Decision, not
guessed at fill time. That is why equity can look stale in a file written seconds after a fill.

## 5. `report.md` — the same cycle for a human

```text
# Ripple — SHADOW EXECUTION
- Account: `demo_lane`     - Strategy: `growth_momentum_v1`
- Decision run: `fixture`  - Execution run: `fixture`
- Result: **allowed**

## Shadow fill attempts
- FILLED BUY AAPL 0.5 at `$100.50` (`assumed_t_plus_one_quote_fill`)

No broker write tool was called.
```

Decision run kind and Execution run kind are recorded independently, because a manual Decision may
legitimately hand off to a scheduled Execution or the reverse. The closing line is a claim about
this specific run, not a general reassurance.

## What deterministic code guaranteed in this cycle

Not the investment idea — the guardrails around it. Before that fill was allowed, checked-in Python
verified that the plan's account matched the executing lane, that the co-located snapshot and plan
existed and matched the execution input, that every symbol was inside the configured universe, that
quotes were fresh, that the baseline still matched reality, that the limit stayed within its price
tolerance, that the position stayed under the per-symbol cap, that cash covered the cumulative
BUYs, that the new-position count and drawdown breakers were clear, and that no wash-sale rule was
violated. Any one of those failing produces no order and no fill, never a smaller guess.

## What this cycle does not prove

A Shadow Fill is an assumption that a real limit order would have filled at that quote with zero
cost. It is comparison evidence between lanes, not a claim about broker behavior. Zero fees and
zero slippage are stated MVP simplifications, not a model. And a single cycle says nothing about a
strategy — see [`INVARIANTS.md`](INVARIANTS.md) for the full safety contract and
[`TODO.md`](TODO.md) for what still has to accumulate before any comparison is meaningful.
