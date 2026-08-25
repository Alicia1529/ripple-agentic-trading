# System invariants

This is the non-negotiable review checklist. Implementation status belongs in `docs/TODO.md`.

1. **Decision sessions never use execution capability.** A Decision-stage LLM must never review, place, cancel, or alter a broker order. The hosted Account A session exposes those tools, so non-use is prompt-enforced. Any Decision-stage write call is an incident that stops and disables the lane for review.
2. **Risk calculations are deterministic.** The Execution Routine calls the checked-in risk scripts and must use their output verbatim. V1 does not claim a code-level barrier prevents that LLM session from misapplying or bypassing the result.
3. **Published decisions are immutable.** The decision-bearing contents of an `OrderPlan` do not change after publication. Execution results and abort reasons are recorded as later operational facts, not rewritten reasoning.
4. **Execution is a separate, narrow routine.** It may execute, abort, scale down, or reject a published plan within the documented rules; it must not perform new investment reasoning or intentionally invent a trade. A deterministic full-position stop-loss/take-profit Risk Exit is the only unplanned-order exception. This is a prompt/tool-use constraint in production v1, not a structural impossibility.
5. **Uncertainty fails closed.** Missing or stale market data, unavailable or decision-baseline-mismatched account state, or a failed risk check aborts planned trading for that cycle. Required-data uncertainty also suppresses Risk Exits rather than guessing a quantity or price.
6. **Decision and fill times stay honest.** A signal using a completed market session is never treated as filled at that same close. Scheduled backtests, shadow fills, and live evaluation use the documented prior-evening decision / next-weekday execution semantics. Manual runs are labeled as manual; a manual dry run is never represented as a live fill.
7. **Account lanes remain isolated.** Each configured lane has separate configuration, state root, and risk state; a hosted lane additionally owns its execution calls and broker connection. Plan, rules, execution context, and state-root basename must name the same `account_id`. Taxpayer-wide loss-sale history is the sole documented cross-account input.
8. **Credentials remain outside artifacts.** Secrets and account numbers remain in the hosted connection or transient tool arguments, never in Git, prompts, plans, fixtures, logs, or reports.
9. **Funding and activation remain human decisions.** The system cannot enable live mode, open or fund an account, increase capital, or add a third lane on its own.
10. **Routine errors stop the cycle.** An MCP error, missing input, malformed result, or ambiguous outcome authorizes no retry or further order in that run. V1 accepts the residual pre-log ambiguity at the small allocation.
11. **Git is continuity, not transactional state.** Per-cycle plans, configuration, JSONL logs, and reports pass between fresh hosted sessions. V1 has no transactional append-only, lease, or exactly-once guarantee.
12. **Tier-two drawdown requires human restart.** A tier-two lock blocks new BUYs until Alicia reviews the lane and explicitly removes its exact lock. Equity recovery cannot clear it; safely computable risk-reducing exits remain allowed.

For implementation or review work, identify the affected invariants and add verification proportional to the risk. If a proposed change invalidates an invariant, record a new decision and update the shared source-of-truth documents instead of weakening an entry file or prompt.
