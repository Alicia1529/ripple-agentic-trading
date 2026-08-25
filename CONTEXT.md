# Ripple domain language

**DecisionSnapshot** — Immutable allowed market inputs, universe, and as-of facts for one decision cycle. Avoid “prompt context” and “market snapshot.”

**Account Lane** — One account's isolated configuration, state, risk, broker connection, and decision-to-execution path. It is not an account collection or coordinator.

**OrderPlan** — Immutable decision-stage instructions for one account and cycle, including intended portfolio, orders, and credential-free decision-time account baseline. Execution outcomes never belong in it.

**Risk Exit** — Deterministic full-position sell emitted by configured stop-loss or take-profit logic. It is risk authority over an existing holding, not new investment reasoning or a replacement plan.

**Execution Routine** — Isolated hosted session that applies deterministic risk output to a published plan and may use broker write tools only after the lane's live gate opens. Avoid “execution agent” when it implies independent judgment.

**Lane state** — Credential-free plan, decision/execution JSONL records, reports, and the account-scoped drawdown lock stored below one account-named state root. Git provides continuity, not transactional or exactly-once semantics.
