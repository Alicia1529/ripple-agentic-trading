# System invariants

These are the non-negotiable constraints already established by `PROPOSAL.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md`. This document is a review checklist, not evidence that the constraints have been implemented; implementation status belongs in `docs/TODO.md`.

1. **Decision sessions have no execution capability.** A Decision-stage LLM cannot access broker write credentials or any tool that can place, cancel, or alter a live order.
2. **Risk authority is deterministic.** LLM output is a proposal. Code-enforced risk rules decide whether it is accepted, clipped, or rejected, and every intervention is logged.
3. **Published decisions are immutable.** The decision-bearing contents of an `OrderPlan` do not change after publication. Execution results and abort reasons are recorded as later operational facts, not rewritten reasoning.
4. **Execution cannot invent a trade.** The Execution Run is plain code. It may execute, abort, scale down, or reject a published plan within the documented rules; it cannot reverse direction or generate a new investment thesis.
5. **Uncertainty fails closed.** Missing or stale market data, unavailable account state, or a failed risk check produces no new trade for that cycle.
6. **Decision and fill times stay honest.** A signal using Day T closing data is never treated as filled at that same close. Backtests, shadow fills, and live evaluation use the documented Day T decision / Day T+1 execution semantics.
7. **Comparisons share controlled inputs.** Live accounts and shadow candidates use the same market-snapshot timing and trading universe while producing independent decisions.
8. **Live accounts remain isolated.** Each live account has separate risk state, execution calls, and broker reconciliation; one account's failure or breaker does not silently change the other.
9. **Credentials remain outside artifacts.** Secrets live only in approved secret stores or environment variables and never in the repository, an `OrderPlan`, or logs.
10. **Funding and promotion remain human decisions.** A shadow candidate may trigger a graduation notification, but the system cannot open an account, deposit funds, or promote itself to live trading.

For implementation or review work, identify the affected invariants and add verification proportional to the risk. If a proposed change invalidates an invariant, record a new decision and update the shared source-of-truth documents instead of weakening an entry file or prompt.
