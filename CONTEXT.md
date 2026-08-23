# Ripple trading

Ripple separates model-authored investment decisions from deterministic execution so that reasoning can be compared without granting it trading authority.

## Language

**DecisionSnapshot**:
The immutable set of market, news, fundamental, universe, and as-of inputs shared by every comparison lane for one decision cycle.
_Avoid_: Prompt context, market snapshot

**OrderPlan**:
An immutable decision-stage instruction for one account and decision cycle. It contains intended portfolio and orders, but never execution outcomes.
_Avoid_: Trade result, execution plan

**ExecutionEvent**:
An append-only operational fact recorded after an OrderPlan is published, such as submission starting, broker acknowledgement, fill, rejection, abort, or unknown outcome.
_Avoid_: OrderPlan status, mutable plan state
