# Runbook

Operational procedures for the D26 single-account hosted v1. Replace placeholders with exact platform controls and commands during implementation.

## Dry-run verification

Run the complete fixture-backed path without broker tools:

```bash
uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/mvp.json \
  --fixture fixtures/mvp/dry_cycle.json \
  --output /tmp/ripple-mvp
```

The two hosted stages use `publish-decision` and `execute-dry-run` exactly as documented in `routines/DECISION.md` and `routines/EXECUTION.md`. Their credential-free continuity output belongs under `state/`. A second command for the same cycle fails instead of overwriting it.

## Kill switch

There is no instantaneous broker-side "flatten everything" switch.

1. Alicia changes the human-owned `execution.mode` to `disabled` in the private repository and pushes it. Neither routine may edit this setting.
2. Disable both hosted schedules if immediate certainty is needed.
3. The next Decision Routine produces no new OrderPlan.
4. The next Execution Routine submits no new orders and may cancel visible pending orders.
5. Existing positions are not automatically liquidated. Use ordinary manual broker orders if an immediate exit is required.

Because v1 execution is LLM-mediated, disabling the hosted schedules is the strongest operational stop; the config flag is an additional routine-level guard, not a security boundary.

## Before first live run

- Keep the repository private and confirm plans, JSONL records, reports, prompts, and test fixtures contain no credentials, cookies, account numbers, or raw authenticated responses.
- Connect Robinhood through the hosted platform's MCP connection. Do not export its tokens into repository secrets or local files.
- Give the Decision Routine only approved read tools and repository access. It must have no Robinhood place/cancel capability. If the platform cannot enforce that separation, do not run the Decision Routine there.
- Give only the isolated Execution Routine the narrow Robinhood read/review/place/cancel tools it needs. Do not provide news browsing or investment-reasoning inputs to that routine.
- Enable exactly one Decision schedule and one Execution schedule following `routines/SCHEDULE.md`. Confirm their repository, branch, timezone, and `America/New_York` self-check.
- Keep `execution.mode=dry_run` through one complete scheduled Day T decision → Day T+1 execution cycle. Review its plan, script output, exact proposed calls, JSONL records, and report.
- Alicia alone changes `execution.mode` to `live` for the initial small allocation.

## Routine checks

For each hosted run, verify:

1. It pulled the expected private branch without a conflict.
2. The Decision Routine created no more than one plan for the trading date.
3. The Execution Routine loaded that exact committed plan and the expected account configuration.
4. Deterministic script output, proposed/actual quantities, Robinhood result IDs, and final status appear in compact credential-free logs.
5. The run committed and pushed its output. Never force-push to repair a routine conflict.

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
| Risk result and placed quantity differ | Disable live execution and treat it as a D26 architecture-review trigger, even if the dollar loss is small. |
| Material drawdown or behavior outside the configured universe | Disable live execution and review before restarting. |

## Known limits

Production v1 intentionally does not implement a transactionally durable submission journal, cross-runner lease, exactly-once guarantee, automatic ambiguous-outcome reconciliation, or non-LLM execution boundary. An LLM can still misread risk output, send the wrong arguments, call a tool twice, misuse configuration, or change behavior after a model/prompt update. D26 accepts those risks only for the initial small allocation and fast launch.

Before any capital increase or second account, review actual incidents and near misses and make a new durable architecture decision. Eight weeks of operation permits that review; it does not automatically approve scaling.
