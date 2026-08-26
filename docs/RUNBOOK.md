# Runbook

Operational procedures for the account catalog, manual development lane, shadow cohort, and future single live lane.

## Repository verification

Validate the complete catalog and inspect scheduled membership:

```bash
uv run --no-cache python -m ripple.mvp validate-configs
uv run --no-cache python -m ripple.mvp list-accounts --mode live
uv run --no-cache python -m ripple.mvp list-accounts --mode shadow
uv run --no-cache python -m ripple.mvp list-accounts --mode dry_run
```

Treat the command output and reviewed `config/*.json` files as the current deployment inventory. A missing strategy or second live configuration must fail validation.

Choose account IDs from the catalog output and run each matching credential-free fixture path:

```bash
uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/<dry_run_account_id>.json \
  --fixture fixtures/mvp/<dry_run_fixture>.json \
  --output /tmp/ripple-mvp/<dry_run_account_id>

uv run --no-cache python -m ripple.mvp run-shadow-cycle \
  --config config/<shadow_account_id>.json \
  --fixture fixtures/mvp/<shadow_fixture>.json \
  --output /tmp/ripple-mvp/<shadow_account_id>
```

The first command writes Decision artifacts under `trading_days/<trade-date>/`. The second adds `execution.json` and `report.md` to that same directory, including deterministic risk, Shadow Fill attempts, and `ending_account`. Neither command calls a broker. Re-running the same cycle fails instead of overwriting evidence.

For an explicitly authorized manual Decision or Execution, use the corresponding `publish-decision`, `execute-dry-run`, or `execute-shadow` command with `--manual-run`. Manual mode changes timing validation only: it still requires the canonical state root and, for Execution, the matching co-located snapshot and plan. The OrderPlan records the Decision run kind and `execution.json` records the Execution run kind independently, so a manual phase may safely hand off to a scheduled phase or vice versa.

## Hosted schedules

Configure exactly the four cohort triggers in `routines/SCHEDULE.md`: live Decision, shadow Decision, live Execution, and shadow Execution. Never schedule dry-run lanes.

Each run starts by validating the complete catalog. A live run with no selected lane is a successful no-op. A shadow run processes every selected lane independently and reports a per-lane summary.

## Shadow operation

For each shadow lane:

1. Use the latest prior result's `ending_account` as the next virtual portfolio; for the first cycle, use the configured `shadow.initial_cash` with no positions.
2. Mark equity and daily P&L from current quotes, update high-water mark only upward, and reset `new_positions_today` at the new trading date before publishing the new account baseline. Do not treat stale ending valuation or a prior day's count as current.
3. Publish one plan using the lane's selected Strategy Spec.
4. At T+1 Execution, provide fresh quotes for every held and planned symbol and call `execute-shadow`.
5. Inspect `fill_status`, every `shadow_fills` entry, and `ending_account`. A `not_filled` limit remains unfilled; do not manually force it into the virtual portfolio.
6. Commit only new credential-free state artifacts. Never rewrite an earlier plan or shadow result.

Zero fees and zero slippage are explicit MVP assumptions. Do not describe shadow performance as live, executable, or after-cost performance.

## Live Gate and kill switch

Before enabling any live lane:

- implement and review the Agentic Robinhood loop;
- prove the connection selects the intended broker account;
- reconcile real cash and positions with the selected lane rather than carrying over virtual state;
- complete the required scheduled no-write acceptance;
- confirm there is exactly one live configuration; and
- obtain the designated owner's explicit mode and allocation approval.

There is no instantaneous repository-side “flatten everything” switch. To stop live work:

1. Disable both live schedules on the hosting platform.
2. Change the affected configuration from `live` to `dry_run` and push it. No routine may make this change.
3. Inspect the broker account and manually cancel or close anything that requires immediate action.

Changing mode does not cancel pending orders or liquidate positions. Disabling schedules is the strongest operational stop.

## Routine checks

For every hosted run, verify:

1. the expected private branch was pulled without conflict;
2. catalog validation passed and cohort membership was recorded;
3. configuration filename, plan, context, and state-root basename use the same account ID;
4. the plan's strategy ID matches the selected configuration;
5. all held/planned-symbol quotes are present and fresh;
6. deterministic output and actual live or assumed shadow outcomes are recorded separately; and
7. no credential, token, cookie, account number, or raw authenticated response entered Git.

## Failure response

| Situation | Action |
|---|---|
| Missing Strategy Spec or malformed catalog | Stop all cohorts; fix and review configuration before the next normal cycle |
| Second live configuration | Stop live schedules; restore at most one live lane before any Decision or Execution work |
| One shadow lane fails | Record and stop that lane; continue only independently validated shadow lanes |
| Scheduled run is missed | Do not backfill a stale Decision or order; fix the cause for the next normal cycle |
| Git conflict | Stop the affected run and resolve normally; never force-push trading evidence |
| Missing/stale quote or baseline mismatch | Execute and simulate nothing for the affected planned work |
| Robinhood authorization request | Stop live work and reconnect interactively; never paste credentials into a prompt or Git |
| Ambiguous live broker outcome | Do not retry; inspect Robinhood history and positions before a later schedule |
| Risk output differs from submitted live order | Disable live schedules and trigger architecture review |
| Unexpected Shadow Fill | Preserve the result, disable shadow schedules if systemic, and correct code rather than editing evidence |

## Tier-two restart

`<state-root>/active_risk_lock.json` blocks new BUYs until the designated owner reviews and removes that exact lane's lock. Equity recovery cannot clear it. Inspect the relevant real or virtual account evidence, resolve discrepancies, and run a fresh reviewed cycle before restoring entries.

## Known limits

Live v1 lacks a transactional submission journal, cross-runner lease, exactly-once guarantee, automatic ambiguous-outcome reconciliation, and non-LLM execution barrier. Shadow v1 assumes quote-price fills with no costs and is not a broker emulator. These limitations must remain visible in every performance review.
