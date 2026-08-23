"""Immutable decision-stage order plans."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from typing import Any, Mapping

from ._immutable_json import freeze_json, thaw_json, validate_json
from ._validation import (
    require_aware_timestamp,
    require_canonical_uuid,
    require_decimal_string,
    require_nonempty_string,
)


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

_DECIMAL_ORDER_FIELDS = {
    "quantity",
    "dollar_amount",
    "limit_price",
    "stop_price",
    "price_tolerance_pct",
    "reference_price_at_decision",
}
_SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,9}")


def _validate_planned_order(order: Mapping[str, Any]) -> None:
    fields = set(order)
    if not _REQUIRED_ORDER_FIELDS <= fields or not fields <= _REQUIRED_ORDER_FIELDS | _OPTIONAL_ORDER_FIELDS:
        raise ValueError("planned order fields do not match the schema")
    if ("quantity" in order) == ("dollar_amount" in order):
        raise ValueError("planned order requires exactly one sizing field")

    require_canonical_uuid(order["order_id"], "order_id")
    scalar_fields = fields - {"order_id"}
    for field in scalar_fields:
        validator = require_decimal_string if field in _DECIMAL_ORDER_FIELDS else require_nonempty_string
        validator(order[field], field)
    if not _SYMBOL.fullmatch(order["symbol"]):
        raise ValueError("symbol must be an uppercase equity symbol")
    if order["side"] not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    if order["order_type"] not in {"LIMIT", "MARKET"}:
        raise ValueError("order_type must be LIMIT or MARKET")
    if order["order_type"] == "LIMIT" and "limit_price" not in order:
        raise ValueError("LIMIT orders require limit_price")
    if order["order_type"] == "MARKET" and "limit_price" in order:
        raise ValueError("MARKET orders must not have limit_price")
    if "dollar_amount" in order and order["order_type"] != "MARKET":
        raise ValueError("dollar_amount is valid only for MARKET orders")
    if "stop_price" in order:
        raise ValueError("stop orders are outside the MVP OrderPlan schema")
    if "market_hours" in order and order["market_hours"] != "regular_hours":
        raise ValueError("MVP orders require regular_hours")
    if "time_in_force" in order and order["time_in_force"] != "gfd":
        raise ValueError("MVP orders require gfd")
    for field in fields & _DECIMAL_ORDER_FIELDS:
        if Decimal(order[field]) <= 0:
            raise ValueError(f"{field} must be greater than zero")
    if Decimal(order["price_tolerance_pct"]) > Decimal("0.10"):
        raise ValueError("price_tolerance_pct must not exceed 0.10")
    if order["order_type"] == "LIMIT":
        reference_price = Decimal(order["reference_price_at_decision"])
        limit_move = abs(Decimal(order["limit_price"]) - reference_price) / reference_price
        if limit_move > Decimal(order["price_tolerance_pct"]):
            raise ValueError("limit_price must be inside price_tolerance_pct")


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
        decision_at = datetime.fromisoformat(values["decision_time"].replace("Z", "+00:00"))
        snapshot_at = datetime.fromisoformat(
            values["market_snapshot_as_of"].replace("Z", "+00:00")
        )
        if snapshot_at > decision_at:
            raise ValueError("market_snapshot_as_of must not be after decision_time")
        target_portfolio = document["target_portfolio"]
        orders = document["orders"]
        if not isinstance(target_portfolio, Mapping):
            raise ValueError("target_portfolio must be an object")
        if not isinstance(orders, list) or any(not isinstance(order, Mapping) for order in orders):
            raise ValueError("orders must be a list of objects")
        if not target_portfolio or any(
            not isinstance(symbol, str) or not symbol or not isinstance(weight, str) or not weight
            for symbol, weight in target_portfolio.items()
        ):
            raise ValueError("target_portfolio must map symbols to decimal strings")
        for weight in target_portfolio.values():
            require_decimal_string(weight, "target_portfolio weight")
        if "cash" not in target_portfolio:
            raise ValueError("target_portfolio must include cash")
        weights = [Decimal(weight) for weight in target_portfolio.values()]
        if any(weight < 0 or weight > 1 for weight in weights) or sum(weights) != Decimal("1"):
            raise ValueError("target_portfolio weights must be between zero and one and sum to one")
        for order in orders:
            _validate_planned_order(order)
            if order["symbol"] not in target_portfolio:
                raise ValueError("planned order symbol must appear in target_portfolio")
        order_ids = [order["order_id"] for order in orders]
        if len(order_ids) != len(set(order_ids)):
            raise ValueError("planned order ids must be unique")
        order_symbols = [order["symbol"] for order in orders]
        if len(order_symbols) != len(set(order_symbols)):
            raise ValueError("MVP permits at most one planned order per symbol")
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
