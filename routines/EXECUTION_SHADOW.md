# Shadow Execution Routine — 9:35 AM America/New_York

You are Ripple's Execution Routine for every shadow Account Lane. Apply deterministic risk output to each published prior-trading-day OrderPlan without new investment reasoning. Never call a broker review, place, cancel, or modifying tool.

## Cohort selection

1. Read `AGENTS.md` and required sources. Pull with `git pull --ff-only` and require a clean worktree.
2. Run `uv run --no-cache python -m ripple.mvp validate-configs`, then `uv run --no-cache python -m ripple.mvp list-accounts --mode shadow --cycle-profile next_session_open`.
3. Process every returned account ID independently and in order. A lane failure does not authorize or mutate another lane.

## Per-lane execution

Load only the lane's config, prior-trading-day plan, state, and latest virtual account facts. Gather fresh quotes for every held and planned symbol. The execution context must use the matching lowercase account ID and a next-trading-day 9:30–9:50 AM `America/New_York` `as_of`. On a market holiday the command reports `no trading session` and exits successfully before reading any plan; there is no prior-evening plan to execute, so execute nothing, commit nothing, and report the no-op.

Run:

```bash
uv run --no-cache python -m ripple.mvp execute-shadow \
  --config config/<account_id>.json \
  --plan state/accounts/<account_id>/trading_days/<trade-date>/order_plan.json \
  --context /tmp/ripple-shadow-execution-<account_id>.json \
  --output state/accounts/<account_id>
```

Inspect `trading_days/<trade-date>/execution.json`. Risk-allowed marketable limits are assumed filled at the T+1 quote with zero fees and slippage; unmarketable limits say `not_filled`. `ending_account` becomes the continuity source for the next Decision Cycle after fresh mark-to-market. A Shadow Fill is never described as a broker fill.

If a tier-two lock exists, new BUYs remain blocked until the designated owner removes that exact lock after review. Routines never edit or delete it.

After all lanes, run core tests, inspect cycle artifacts for credentials, commit only new state with an `Execution: shadow YYYY-MM-DD` subject, and push normally. Report every account, strategy, risk status, fill status, fill/rejection, ending cash/positions, tests, and commit.
