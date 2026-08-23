# Ripple trading

Ripple separates model-authored investment decisions from a narrow hosted execution routine and deterministic risk calculations. Production v1 grants broker write tools only to the isolated Execution Routine and explicitly accepts that this is not a code-level enforcement boundary.

## Language

**DecisionSnapshot**:
The immutable set of market, news, fundamental, universe, and as-of inputs for one decision cycle. Production v1 has one lane; later comparison lanes may share the same snapshot.
_Avoid_: Prompt context, market snapshot

**OrderPlan**:
An immutable decision-stage instruction for one account and decision cycle. It contains intended portfolio and orders, but never execution outcomes.
_Avoid_: Trade result, execution plan

**ExecutionEvent**:
An immutable operational-fact document recorded after an OrderPlan is published, such as submission starting, broker acknowledgement, fill, rejection, abort, or unknown outcome. The value object does not itself guarantee append-only persistence; that requires a future transactional repository.
_Avoid_: OrderPlan status, mutable plan state

**Execution Routine**:
The isolated scheduled LLM session that applies the deterministic risk scripts to a published OrderPlan and may call broker write tools in production v1.
_Avoid_: Plain executor, execution agent
