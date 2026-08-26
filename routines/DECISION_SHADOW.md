# Shadow Decision Routine — 9:00 PM America/New_York

You are Ripple's Decision Routine for every shadow Account Lane. One schedule trigger owns the cohort, but each lane produces an independent Decision Cycle and state root. You have no broker-write authority.

Scheduled invocations never automatically fill missed dates. A designated-owner historical backfill is separate: use `--historical-backfill` with complete point-in-time inputs and a historical `decision_time` inside the normal Decision window, identify the result as `backfill`, and use a separately authorized manual Shadow Execution when fill evidence is required.

## Cohort selection

1. Read `AGENTS.md` and its required sources. Pull with `git pull --ff-only` and require a clean worktree.
2. Run `uv run --no-cache python -m ripple.mvp validate-configs`, then `uv run --no-cache python -m ripple.mvp list-accounts --mode shadow`.
3. Process every returned account ID in that exact order. Dry-run and live accounts are out of scope.

## Per-lane isolation

For each lane, read only its `config/<account_id>.json`, selected Strategy Spec, and `state/accounts/<account_id>`. Do not reuse another lane's plan, holdings, target portfolio, lock, or failure as input.

Use `ending_account` from the latest prior `trading_days/*/execution.json` as the virtual cash/position source. On the first cycle, use the configured `shadow.initial_cash`, empty positions, and a reviewed matching equity/high-water baseline. Mark current equity from fresh quotes, update high-water mark only upward, calculate the new day's P&L, and reset `new_positions_today` for the next trading date; never carry stale valuation or a prior day's entry count forward.

Gather the selected strategy's required facts for the complete configured universe and current virtual positions. Where two lanes require the same market facts, use the same completed-session `as_of` for fair comparison, while producing independent decisions.

Build one credential-free temporary input per lane with exactly `snapshot`, `account_baseline`, and `decision`, then publish:

```bash
uv run --no-cache python -m ripple.mvp publish-decision \
  --config config/<account_id>.json \
  --input /tmp/ripple-shadow-decision-<account_id>.json \
  --output state/accounts/<account_id>
```

A lane with missing facts, an existing plan, or malformed state stops only that lane and is reported as failed; it does not authorize or mutate another lane. After all lanes, run the core tests, inspect new files for secrets, commit new credential-free state in one `Decision: shadow YYYY-MM-DD` commit, and push normally. Report every account ID, strategy ID, plan ID or failure, order count, tests, and commit. Do not perform Execution work.

The publisher writes both Decision artifacts under `state/accounts/<account_id>/trading_days/<trade-date>`, where the trade date is the next New York weekday after the Decision.
