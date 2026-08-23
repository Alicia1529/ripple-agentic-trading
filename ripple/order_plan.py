"""Immutable decision-stage order plans."""

from dataclasses import dataclass
from typing import Any, Mapping

from ._immutable_json import freeze_json, thaw_json, validate_json
from ._validation import require_aware_timestamp, require_canonical_uuid, require_nonempty_string


_REQUIRED_FIELDS = {
    "order_plan_id",
    "decision_time",
    "account_id",
    "model_config_version",
    "decision_snapshot_id",
    "market_snapshot_as_of",
    "target_portfolio",
    "orders",
}

_REQUIRED_ORDER_FIELDS = {
    "order_id",
    "order_type",
    "price_tolerance_pct",
    "reference_price_at_decision",
    "side",
    "symbol",
}

_OPTIONAL_ORDER_FIELDS = {
    "dollar_amount",
    "limit_price",
    "market_hours",
    "quantity",
    "stop_price",
    "time_in_force",
}


def _validate_planned_order(order: Mapping[str, Any]) -> None:
    fields = set(order)
    if not _REQUIRED_ORDER_FIELDS <= fields or not fields <= _REQUIRED_ORDER_FIELDS | _OPTIONAL_ORDER_FIELDS:
        raise ValueError("planned order fields do not match the schema")
    if ("quantity" in order) == ("dollar_amount" in order):
        raise ValueError("planned order requires exactly one sizing field")

    require_canonical_uuid(order["order_id"], "order_id")
    scalar_fields = fields - {"order_id"}
    for field in scalar_fields:
        require_nonempty_string(order[field], field)


@dataclass(frozen=True, init=False)
class OrderPlan:
    order_plan_id: str
    decision_time: str
    account_id: str
    model_config_version: str
    decision_snapshot_id: str
    market_snapshot_as_of: str
    target_portfolio: Mapping[str, Any]
    orders: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "OrderPlan":
        if not isinstance(document, Mapping) or set(document) != _REQUIRED_FIELDS:
            raise ValueError("OrderPlan fields do not match the schema")
        values = {
            "order_plan_id": require_canonical_uuid(document["order_plan_id"], "order_plan_id"),
            "decision_time": require_aware_timestamp(document["decision_time"], "decision_time"),
            "account_id": require_nonempty_string(document["account_id"], "account_id"),
            "model_config_version": require_nonempty_string(
                document["model_config_version"], "model_config_version"
            ),
            "decision_snapshot_id": require_canonical_uuid(
                document["decision_snapshot_id"], "decision_snapshot_id"
            ),
            "market_snapshot_as_of": require_aware_timestamp(
                document["market_snapshot_as_of"], "market_snapshot_as_of"
            ),
        }
        target_portfolio = document["target_portfolio"]
        orders = document["orders"]
        if not isinstance(target_portfolio, Mapping):
            raise ValueError("target_portfolio must be an object")
        if not isinstance(orders, list) or any(not isinstance(order, Mapping) for order in orders):
            raise ValueError("orders must be a list of objects")
        if not target_portfolio or any(
            not isinstance(symbol, str)
            or not symbol
            or not isinstance(weight, str)
            or not weight
            for symbol, weight in target_portfolio.items()
        ):
            raise ValueError("target_portfolio must map symbols to decimal strings")
        for order in orders:
            _validate_planned_order(order)
        validate_json(target_portfolio)
        validate_json(orders)

        plan = object.__new__(cls)
        for field, value in values.items():
            object.__setattr__(plan, field, value)
        object.__setattr__(plan, "target_portfolio", freeze_json(target_portfolio))
        object.__setattr__(plan, "orders", freeze_json(orders))
        return plan

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_plan_id": self.order_plan_id,
            "decision_time": self.decision_time,
            "account_id": self.account_id,
            "model_config_version": self.model_config_version,
            "decision_snapshot_id": self.decision_snapshot_id,
            "market_snapshot_as_of": self.market_snapshot_as_of,
            "target_portfolio": thaw_json(self.target_portfolio),
            "orders": thaw_json(self.orders),
        }
