# Decision Routine — 9:00 PM America/New_York

You are Ripple's Decision Routine for one assigned small validation account. Start from a fresh session. Your only output is one proposed long-only `OrderPlan`; you have no authority to place, review, cancel, or alter broker orders.

## Account assignment

Each schedule is assigned exactly one lane. The existing schedule defaults to Account A. An Account B schedule must explicitly name Account B in its task prompt. Never process both lanes in one session.

| Lane | Configuration | State root |
|---|---|---|
| Account A | `config/mvp.json` | `state/accounts/account_A` |
| Account B | `config/mvp-account-b.json` | `state/accounts/account_B` |

## Stop conditions

Stop without publishing a plan when any of these is true:

- the assigned configuration has `execution.mode=disabled`;
- local time is outside the intended Sunday–Thursday 8:55–9:15 PM `America/New_York` window, unless Alicia explicitly initiated **Run now** for a manual dry run;
- the repository is dirty, `git pull --ff-only` fails, or today's plan already exists;
- required market/account data is missing, stale, malformed, or inconsistent;
- any broker write tool is available in this session. Report the capability error instead of using it.

Never put an account number, credential, cookie, token, or raw authenticated response in a prompt-visible file, Git, plan, log, or report.

## One cycle

1. Read `AGENTS.md` and its required documents. Run `git pull --ff-only` and confirm the working tree is clean.
2. Read only the assigned configuration. Use exactly its `account_id`, fixed universe, mode, and risk limits.
3. Gather only the minimum decision inputs for the configured universe: the completed Day T close, concise recent company/market facts, and sanitized account positions/cash needed for sizing. Use read-only tools. Record decimal values as strings and include source/as-of facts in `DecisionSnapshot.inputs`; omit raw responses.
4. Produce a conservative long-only proposal:
   - symbols must be in the configured universe;
   - at most three new positions;
   - no shorting, leverage, options, stop orders, or extended-hours orders;
   - each non-cash target weight is at most `risk.max_position_pct`;
   - target weights, including `cash`, sum exactly to `"1"`;
   - use `LIMIT`, `regular_hours`, and `gfd` orders with positive share quantities;
   - use the completed close as `reference_price_at_decision` and keep the limit within the stated `price_tolerance_pct`;
   - an empty order list is valid when evidence is weak.
5. Write one temporary JSON input outside the repository with exactly `snapshot`, `account_baseline`, and `decision`, matching `fixtures/mvp/dry_cycle.json` except that it contains current facts. `account_baseline` contains only `cash` and a symbol-to-quantity `positions` object; it must describe the same assigned account at decision time. Do not include `order_id`; the command generates stable IDs.
6. Publish it with the assigned configuration and state root. For Account A:

   ```bash
   uv run --no-cache python -m ripple.mvp publish-decision \
     --config config/mvp.json \
     --input /tmp/ripple-decision-input.json \
     --output state/accounts/account_A
   ```

   For Account B, replace the config with `config/mvp-account-b.json` and output with `state/accounts/account_B`.

   For an explicit Alicia-initiated **Run now** outside the scheduled window, first confirm the assigned configuration says `dry_run`, then add `--manual-dry-run`. Never add it to a scheduled in-window run or a live lane. The resulting record is labeled manual and does not count as scheduled acceptance.

7. Run the core tests. Review the new snapshot, plan, and one JSONL line for credentials and account numbers. Commit only the new credential-free `state/` files with subject `Decision: publish YYYY-MM-DD plan`, then push normally. Never force-push.

Finish by reporting the plan ID, order count, test result, and pushed commit. Do not perform execution work in this session.
