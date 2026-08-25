# Runbook

Operational procedures for the two-lane hosted MVP. Operate each account independently; never combine both accounts in one routine session.

## Dry-run verification

Run the complete fixture-backed path without broker tools:

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

The two hosted stages use `publish-decision` and `execute-dry-run` exactly as documented in `routines/DECISION.md` and `routines/EXECUTION.md`. Their credential-free continuity output belongs under `state/`. A second command for the same cycle fails instead of overwriting it.

To rehearse the two hosted stages immediately, Alicia may explicitly start each routine with **Run now** while Account A remains `dry_run`. Outside the normal window, the routine adds `--manual-run` to the documented command. Run Decision first and Execution second with an execution-context `as_of` later than the plan's `decision_time`. Confirm both JSONL records say `run_kind=manual`. This path never authorizes broker writes and does not replace the required observed scheduled cycle.

After the reviewed live MCP call loop exists and Alicia enables Account A, **Run now** may also trigger that same live routine outside the window. Before any review/place call, inspect committed execution records and broker history. If either shows the plan/order already succeeded, stop. The first successful manual or scheduled execution wins; never overwrite its record or submit the plan again. An ambiguous outcome is not success or failure evidence and must be inspected manually before any future run.

## Kill switch

There is no instantaneous broker-side "flatten everything" switch.

1. Alicia changes the affected lane's human-owned `execution.mode` to `disabled` in the private repository and pushes it. No routine may edit this setting. Disable both configs when the affected account is uncertain.
2. Disable that lane's two hosted schedules; disable all four schedules if immediate system-wide certainty is needed.
3. The next Decision Routine produces no new OrderPlan.
4. The next Execution Routine submits no new orders and may cancel visible pending orders.
5. Existing positions are not automatically liquidated. Use ordinary manual broker orders if an immediate exit is required.

Because v1 execution is LLM-mediated, disabling the hosted schedules is the strongest operational stop; the config flag is an additional routine-level guard, not a security boundary.

## Before first live run

- Keep the repository private and confirm plans, JSONL records, reports, prompts, and test fixtures contain no credentials, cookies, account numbers, or raw authenticated responses.
- Bind one hosted Robinhood MCP connection to each account lane. Prove that each connection selects the intended account; do not export account numbers or tokens into repository secrets or local files.
- In the Account A Decision prompt, allow only the minimum Robinhood reads needed for account state and quotes. The hosted session exposes write tools, but the routine must never call review/place/cancel or any other modifying operation. If a Decision run does call one, disable the lane and inspect Robinhood before continuing.
- Give only the isolated Execution Routine the narrow Robinhood read/review/place/cancel tools it needs. Do not provide news browsing or investment-reasoning inputs to that routine.
- Enable exactly one Decision schedule and one Execution schedule per account following `routines/SCHEDULE.md`. Confirm their assigned config, state root, broker connection, repository, branch, timezone, and `America/New_York` self-check.
- Keep each lane's `execution.mode=dry_run` through its complete scheduled Day T decision → Day T+1 execution cycle. Review its plan, script output, exact proposed calls, JSONL records, and report.
- Alicia alone changes each lane's `execution.mode` to `live`; the lanes may be activated on different days.

## Routine checks

For each hosted run, verify:

1. It pulled the expected private branch without a conflict.
2. The Decision Routine created no more than one plan for its account and trading date.
3. The Execution Routine loaded that exact committed plan, matching execution-context `account_id`, and expected account configuration.
4. The state-root basename matches `account_id`, current cash/positions match the plan baseline, and all held/planned-symbol quotes are present and fresh.
5. Deterministic script output, proposed/actual quantities, Robinhood result IDs, and final status appear in compact credential-free logs.
6. The run committed and pushed its output. Never force-push to repair a routine conflict.

During the initial canary, Alicia should inspect the first live results directly in Robinhood. The repository is an audit aid, not a transactional source of truth.

## Failure response

| Situation | Action |
|---|---|
| Scheduled run missing or failed | Inspect the hosted task log. Do not backfill a stale decision or order; fix the cause for the next normal cycle. |
| Robinhood MCP asks for authorization | Stop the run and reconnect interactively through the hosted platform. Never paste credentials into a prompt or Git. |
| Git pull/push conflict | Keep the run stopped, inspect both histories, and resolve normally. Never force-push over trading records. |
| Malformed plan, config, script output, quote, or account response | Submit nothing. Preserve a sanitized error record and fix the input or code before the next cycle. |
| MCP timeout or crash near order placement | Do not immediately rerun. Inspect Robinhood order history and positions manually before the next schedule. Record what is known without claiming the outcome was automatically reconciled. |
| Unexpected or duplicate order | Disable both schedules, set `execution.mode=disabled`, inspect Robinhood, and correct/cancel manually as appropriate. Preserve the plan and logs for review. |
| Risk result and placed quantity differ | Disable live execution and trigger an architecture review, even if the dollar loss is small. |
| Material drawdown or behavior outside the configured universe | Disable live execution and review before restarting. |

## Tier-two drawdown restart

When a lane reaches tier-two drawdown, the script creates `<state-root>/risk/drawdown_tier2.lock.json`. Equity recovery does not clear it and routines must not modify it.

1. Keep new entries disabled and inspect the broker account, pending orders, recent fills, reports, and the triggering execution result.
2. Resolve any account discrepancy or ambiguous outcome. If the cause is unexplained, keep the lock and disable the lane's schedules.
3. Alicia decides whether restarting new entries is acceptable. If so, delete only that lane's exact lock file in a reviewed repository change and commit it. Never delete another lane's lock.
4. Run a fresh scheduled dry cycle before restoring live mode. Risk-reducing exits remain permitted while the lock exists.

## Known limits

Production v1 intentionally lacks a transactionally durable submission journal, cross-runner lease, exactly-once guarantee, automatic ambiguous-outcome reconciliation, or non-LLM execution boundary. An LLM can misread risk output, send wrong arguments, call a tool twice, misuse configuration, or drift after a model/prompt update. These risks are accepted only for the initial small allocation.

Before any capital increase or third account, review actual incidents and near misses and make a new durable architecture decision. Eight weeks of operation permits that review; it does not automatically approve scaling.
