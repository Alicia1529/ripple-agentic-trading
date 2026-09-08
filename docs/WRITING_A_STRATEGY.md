# Writing a Strategy Spec

A Strategy Spec is a versioned **Markdown investment policy** that tells the Decision agent which
facts to gather, how to evaluate candidates and when to propose a trade. Each Account Lane selects
one policy by identifier. Start with [Growth Momentum v1](../strategies/growth_momentum_v1.md)
for a short example of the format; selection in current deployments is defined by config.

The agent applies the investment policy; Python validates the resulting artifacts, calculates risk
and enforces timing and sizing constraints.
Adding a strategy therefore requires no Python — but a strategy can never loosen a deterministic
rule either.

## Try a policy locally

1. Create `strategies/<strategy_id>.md` with a lowercase `snake_case` identifier and version,
   such as `my_policy_v1`.
2. Copy [the demo config](../config/examples/demo_lane.json) to `config/examples/my_policy/demo_lane.json`
   and set its `strategy` to your new identifier. Keep it under `config/examples/` so scheduled
   runs do not select it. Keep the filename `demo_lane.json` to match the supplied fixture's
   `execution_context.account_id`. A different lane name requires a matching fixture account ID.
3. Run the supplied fixture with that configuration and a fresh output directory:

   ```bash
   uv run --no-cache python -m ripple.mvp run-shadow-cycle \
     --config config/examples/my_policy/demo_lane.json \
     --fixture fixtures/mvp/demo_lane_cycle.json \
     --output /tmp/ripple-strategy-demo/demo_lane
   ```

This verifies configuration loading, strategy-file existence and the fixed fixture's publication
and execution. **The fixture supplies its own decision; this command does not ask an LLM to apply
your new policy.** Evaluating the policy requires a separate Decision routine run with its required
facts and the appropriate owner authorization.

Adding a configuration to `config/` is a separate reviewed deployment change: it joins the catalog
and may become eligible for scheduling. At that point, run
`uv run --no-cache python -m ripple.mvp validate-configs` to validate the complete catalog. A
missing Strategy Spec fails validation rather than silently running a lane without a policy.

## What you decide, and what you never override

You own the investment policy:

- which facts the decision requires, and what makes one missing or untrustworthy;
- the regime test, hard filters, ranking, and how much qualitative research is warranted;
- when a position is exited on judgment rather than mechanics;
- position sizing and the shape of the target portfolio; and
- what counts as a valid no-trade outcome.

Deterministic code applies the selected lane's configured risk limits in every mode: position
caps, new-position counts, loss and drawdown breakers, quote freshness, loss-sale lookback and
stop-loss/take-profit exits. Read [`config/*.json`](../config/) for current values and
[the risk module](../ripple/risk.py) for enforcement. Per-order price tolerance cannot exceed the
code's 10% cap. A policy may impose stricter constraints; it cannot override the checks or grant
Decision any order-placement authority.

If a spec requires changing the deterministic safety contract, that is an architecture decision recorded in
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
source and freshness checks, and completeness checks. Invalid compiler input stops the compiler.
The compact compiler can return `status: "unavailable"` for a symbol; the selected policy specifies
when this disqualifies a candidate or stops the lane. Missing values must not be invented. Raw authenticated responses are never persisted.

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

A self-check makes the policy easier to review: it lists the statements the agent must verify
before publishing. It remains a prompt instruction; it does not add a Python-enforced guarantee
that the model followed every investment rule.

## Versioning

**Never edit a spec in place after it has produced a decision.** Published plans freeze
`strategy_id`, so editing the file behind that identifier silently rewrites the meaning of evidence
that already exists. Create a new identifier instead — `growth_momentum_v2` →
`growth_momentum_v2_lite` → `growth_momentum_v2_lite_compact` are all separate files — and switch
the lane when you are ready. Git history keeps the exact text that produced every past decision,
and old lanes keep their attribution.

Switching a live lane's strategy is a human decision, never an automatic promotion. No metric in
this repository moves capital or changes a binding on its own.
