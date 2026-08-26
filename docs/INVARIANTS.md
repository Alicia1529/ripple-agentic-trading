# System invariants

This is the non-negotiable review checklist. Implementation status belongs in `docs/TODO.md`.

1. **Decision sessions never use execution capability.** A Decision-stage LLM never reviews, places, cancels, or alters a broker order. A Decision-stage write is an incident that stops the affected lane and live schedules.
2. **Risk calculations are deterministic and shared.** Every mode uses the checked-in risk code, and an Execution Routine must use its output verbatim. V1 does not claim a code-level barrier prevents a live LLM from bypassing it.
3. **Published decisions are immutable and strategy-attributed.** Decision-bearing OrderPlan content, including `account_id` and `strategy_id`, never changes after publication. Later results never rewrite it.
4. **Execution is separate and narrow.** It may execute, simulate, scale down, reject, or abort a published plan without a new investment thesis. A deterministic full-position Risk Exit is the sole unplanned-order exception.
5. **Uncertainty fails closed.** Missing or stale market data, unavailable or baseline-mismatched account state, malformed configuration, a missing Strategy Spec, or a failed risk check authorizes no planned order or Shadow Fill.
6. **Decision and fill times stay honest.** A Day T signal never receives a Day T close fill. Live evaluation, Shadow Fills, and later replay use the documented prior-evening Decision and next-weekday Execution semantics.
7. **Account Lanes remain isolated.** Config filename, plan, execution context, state-root basename, risk state, fill evidence, broker call, and live mode agree on one lowercase `account_id`. Taxpayer-wide loss-sale history is the sole documented cross-lane input.
8. **Credentials remain outside artifacts.** Secrets, tokens, cookies, account numbers, and raw authenticated responses remain outside Git, prompts, plans, fixtures, logs, and reports.
9. **Funding and activation remain human decisions.** The system cannot enable live mode, select a replacement live strategy, open or fund an account, reconcile a shadow portfolio into a real account, increase capital, or clear a restart lock.
10. **Mode selection is deterministic.** The catalog permits at most one live configuration, selects all shadow configurations in account-ID order, and excludes dry-run configurations from every scheduled cohort.
11. **Routine errors do not broaden authority.** An MCP error, malformed result, ambiguous outcome, or one shadow lane's failure authorizes no retry, cross-lane state change, or additional order. Independent shadow lanes may continue their own cycles.
12. **Git is continuity, not transactional state.** Trade-date cycle artifacts and configurations pass between fresh sessions. V1 has no transactional append-only store, cross-runner lease, or exactly-once guarantee.
13. **Shadow evidence stays explicit.** A Shadow Fill requires deterministic risk permission and a marketable T+1 quote, records zero-fee/zero-slippage assumptions, and is never represented as a broker fill.
14. **Tier-two drawdown requires human restart.** A lane-scoped tier-two lock blocks new BUYs until the designated owner reviews and removes that exact lock. Equity recovery cannot clear it; safely computable exits remain allowed.

Every implementation and review identifies affected invariants and verifies them in proportion to risk. A proposed change that invalidates one requires an approved durable decision and matching architecture update.
