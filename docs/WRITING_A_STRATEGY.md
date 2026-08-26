# Writing a Strategy Spec

A Strategy Spec is a checked-in, version-named **Markdown investment policy**. It is not a plugin,
a class, or a config schema. An Account Lane selects exactly one by identifier, and its Decision
Routine reads that file completely and applies it to that lane alone.

This is deliberate. Ripple's interesting question is which responsibilities belong to a language
model and which belong to deterministic code, so the policy lives where a model reads it, and the
code owns everything a model should never be trusted to redo: shape, sizing, timing, and safety.
Adding a strategy therefore requires no Python — but a strategy can never loosen a deterministic
rule either.

## Add one in three steps

1. Create `strategies/<strategy_id>.md`. The identifier is lowercase `snake_case` and carries its
   version: `growth_momentum_v3`, `earnings_drift_v1`.
2. Point a lane at it with `"strategy": "<strategy_id>"` in that lane's configuration.
3. Validate:

   ```bash
   uv run --no-cache python -m ripple.mvp validate-configs
   ```

Catalog validation fails when the file does not exist, so a typo stops the whole catalog instead of
silently running a lane with no policy. To try it without touching the real catalog, copy
[`config/examples/demo_lane.json`](../config/examples/demo_lane.json) into `config/` under a new
snake_case filename — `config/examples/` sits outside the `config/*.json` glob and is never
scheduled.

Validation proves your spec **exists and is bound**. It cannot prove the policy is any good; only a
Decision Routine run applies it.

## What you decide, and what you never override

You own the investment policy:

- which facts the decision requires, and what makes one missing or untrustworthy;
- the regime test, hard filters, ranking, and how much qualitative research is warranted;
- when a position is exited on judgment rather than mechanics;
- position sizing and the shape of the target portfolio; and
- what counts as a valid no-trade outcome.

Deterministic code owns the floor, in every mode, regardless of what your spec says: 20% maximum
per symbol, three new positions per day, 5% daily-loss breaker, 10%/15% drawdown tiers, 15-minute
quote freshness, 30-day wash-sale lookback, 8% stop loss, 20% take profit, and a per-order price
tolerance that may never exceed 10%. A spec may be **stricter** than the floor — Growth Momentum v1
caps its own limits at 1% — and can never be looser. It also cannot grant Decision any order
authority: publishing a plan is the only thing a Decision Routine may do.

If a spec you want requires changing that floor, that is an architecture decision recorded in
[`DECISIONS.md`](DECISIONS.md), not a line in a Markdown policy.

## What every spec must produce

All strategies publish through the same `OrderPlan` schema, so evidence stays comparable across
lanes:

- a `decision_rationale`: concise, human-readable, and covering a no-trade result too. It is
  investment judgment, not a data-quality warning and not a deterministic reason code;
- a `target_portfolio` whose weights sum to exactly `"1"`, holding preserved positions, a full sale
  written as `"0"`, and the remainder in `cash`;
- zero or more orders, each a positive-share `LIMIT`, `regular_hours`, `gfd` order carrying
  `reference_price_at_decision`, `limit_price`, `price_tolerance_pct`, and — for a BUY — a concise
  `buy_reason` grounded in decision-stage evidence; and
- research, rejected candidates, warnings, and thesis metadata recorded in the immutable
  `DecisionSnapshot` rather than in the plan.

Financial values are base-10 decimal strings. Never a float.

## The optional facts compiler

When a policy depends on a number that must be exactly right — a moving average, a 60-session
return, a session-aligned date — it should not be computed by a model in prose. A spec may require
a checked-in deterministic compiler; [`ripple/growth_momentum.py`](../ripple/growth_momentum.py) is
the worked example.

A compiler reads the selected lane configuration, **requires its input symbol set to match that
lane's universe exactly**, and emits credential-free facts plus provenance into
`DecisionSnapshot.inputs`. It owns Decimal formulas, session alignment, interpolation rejection,
source and freshness checks, and completeness checks; incomplete compilation stops publication
rather than degrading. Raw authenticated responses are never persisted.

The division holds even here: the model gathers and normalizes sources, the compiler derives
numbers from them, and the spec decides what those numbers mean. This is a facts seam, not the
beginning of a Python strategy engine — filtering, ranking, prose research, and portfolio judgment
stay in the Markdown.

## The shape mature specs converge on

`growth_momentum_v1` is the minimal readable example. The specs that have survived contact with
real cycles all grew the same sections, in roughly this order:

| Section | What it pins down |
|---|---|
| Authority and fail-closed rules | What this spec may never do, and what stops the cycle |
| Required Decision inputs | Every fact the policy needs, and what a missing one means |
| Decision order | Exits before entries, so a sale never funds a same-cycle buy by accident |
| Exits | Mechanical exits separated from judgment exits |
| Entries | Hard filters → ranking → bounded research → thesis record |
| Order construction | Limits, tolerances, sizing, and the exact order fields |
| Ripple publication shape | The mapping from policy output to `OrderPlan` fields |
| Failure behavior | Which failures stop the lane and which produce a valid no-trade |
| Self-check | A checkable list the routine runs before publishing |

The self-check is worth copying. It converts "follow this policy" into "verify these statements are
true about the plan you are about to publish," which is the difference between a prompt and a
contract.

## Versioning

**Never edit a spec in place after it has produced a decision.** Published plans freeze
`strategy_id`, so editing the file behind that identifier silently rewrites the meaning of evidence
that already exists. Create a new identifier instead — `growth_momentum_v2` →
`growth_momentum_v2_lite` → `growth_momentum_v2_lite_compact` are all separate files — and switch
the lane when you are ready. Git history keeps the exact text that produced every past decision,
and old lanes keep their attribution.

Switching a live lane's strategy is a human decision, never an automatic promotion. No metric in
this repository moves capital or changes a binding on its own.
