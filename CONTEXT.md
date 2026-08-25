# Ripple trading

Ripple separates model-authored investment decisions from a narrow hosted execution routine and deterministic risk calculations. Production v1 grants broker write tools only to the isolated Execution Routine and explicitly accepts that this is not a code-level enforcement boundary.

## Language

**DecisionSnapshot**:
The immutable set of market, news, fundamental, universe, and as-of inputs for one decision cycle. Account lanes may share the same snapshot when they intentionally compare decisions from the same facts.
_Avoid_: Prompt context, market snapshot

**Account Lane**:
One account's isolated decision-to-execution path, identified by `account_id`. A lane is not a shared multi-account coordinator and never owns another lane's plan or broker actions.
_Avoid_: Account worker, account collection

**OrderPlan**:
An immutable decision-stage instruction for one account and decision cycle. It contains intended portfolio, orders, and a credential-free account baseline for later reconciliation, but never execution outcomes.
_Avoid_: Trade result, execution plan

**Risk Exit**:
A deterministic full-position sell produced by a configured stop-loss or take-profit rule. It is risk authority applied to an existing holding, not a new investment decision or a mutation of the OrderPlan.
_Avoid_: Execution Routine trade idea, replacement plan

**Execution Routine**:
The isolated scheduled LLM session that applies the deterministic risk scripts to a published OrderPlan and may call broker write tools in production v1.
_Avoid_: Plain executor, execution agent
