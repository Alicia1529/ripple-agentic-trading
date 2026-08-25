# Current effective decisions

Git history retains superseded reasoning. This file summarizes only decisions that govern the current MVP.

## Product and release

- Ripple exists to learn from a small, inspectable real-money agent loop. The repository keeps two independent fixture lanes; Account A alone owns the current hosted path.
- Initial exposure is $500–1000 for Account A. Alicia alone enables live mode, funds the account, restarts a tier-two lock, or approves more capital.
- One complete Account A scheduled dry cycle and verified account binding gate its live activation. Eight continuous live weeks permit a capital review, not automatic scaling.
- An Account B hosted path, a third account, or increased capital triggers architecture review of execution isolation, durability, idempotency, reconciliation, and operational ownership.

## Decision and execution

- Decision runs Sunday–Thursday around 9:00 PM `America/New_York`; Sunday uses Friday's completed close plus weekend facts. Execution runs the next weekday around 9:35 AM. Missed cycles are not backfilled.
- The Decision Routine publishes one immutable `DecisionSnapshot` and `OrderPlan`. It never uses broker write tools, even when the hosted connection exposes them.
- The Execution Routine may execute, scale down, reject, or abort the published plan after deterministic revalidation. It performs no new investment reasoning. Script-emitted full-position stop-loss/take-profit Risk Exits are the sole unplanned-order exception.
- Stable plan/order IDs and first-success ownership reduce duplicates. Manual runs are labeled; ambiguous broker outcomes stop without blind retry.

## State and isolation

- Account A and B use concrete separate configurations, state roots, and risk state over the same CLI and risk code. Account A alone has hosted schedules and an MCP connection; Account B remains fixture-backed. There is no coordinator, shared ledger, or `accounts[]` framework.
- `DecisionSnapshot` and `OrderPlan` remain strict immutable value objects. Persisted financial values are base-10 decimal strings. OrderPlans accept positive share-quantity `LIMIT`, `regular_hours`, `gfd` orders and carry a credential-free account baseline.
- Private Git stores code, configuration, per-cycle plans, compact JSONL records, and sanitized reports between fresh hosted sessions. Hosted MCP stores OAuth state. Tokens, cookies, account numbers, and raw authenticated responses never enter Git artifacts.
- Git is not a transactional submission journal or cross-runner lease. The small-account MVP explicitly accepts crash-before-log, duplicate-call, ambiguous-timeout, prompt/tool-use, configuration, and model-drift risks.

## Deterministic safety

- Risk is computed per account: 20% maximum symbol position, three new positions per day, 5% daily-loss breaker, 10% tier-one drawdown, 15% tier-two drawdown, 15-minute quote freshness, 30-day taxpayer-wide wash-sale lookback, 8% stop-loss, and 20% take-profit.
- BUY cash is reserved cumulatively at worst-case limit fills. Missing/stale quotes, baseline mismatch, cross-account mismatch, malformed inputs, or uncertain required state fail closed.
- Tier two persists an account-scoped lock blocking new BUYs until Alicia reviews and removes it. Risk-reducing exits remain possible when safely computable.
- `execution.mode` is a human-owned gate. Disabling hosted schedules is the strongest operational stop; neither action automatically liquidates positions.

## Current strategy and non-goals

- Account A uses `strategies/growth_momentum_v1.md`: full configured-universe screening and current-position review may yield no trade, one 10% BUY, one full discretionary SELL, or both. The generic publisher and deterministic execution checks remain authoritative.
- The MVP does not include a strategy engine/plugin system, analyst ensemble, shadow/comparison infrastructure, additional brokers, intraday trading, tax-lot optimization, custom OAuth, a non-LLM executor, transactional persistence, exactly-once submission, or automatic ambiguous-outcome reconciliation.
