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
    "account_baseline",
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
    "quantity",
    "limit_price",
    "market_hours",
    "time_in_force",
}

_OPTIONAL_ORDER_FIELDS: set[str] = set()

_DECIMAL_ORDER_FIELDS = {
    "quantity",
    "limit_price",
    "price_tolerance_pct",
    "reference_price_at_decision",
}
_SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,9}")


def _validate_planned_order(order: Mapping[str, Any]) -> None:
    fields = set(order)
    if not _REQUIRED_ORDER_FIELDS <= fields or not fields <= _REQUIRED_ORDER_FIELDS | _OPTIONAL_ORDER_FIELDS:
        raise ValueError("planned order fields do not match the schema")
    require_canonical_uuid(order["order_id"], "order_id")
    scalar_fields = fields - {"order_id"}
    for field in scalar_fields:
        validator = require_decimal_string if field in _DECIMAL_ORDER_FIELDS else require_nonempty_string
        validator(order[field], field)
    if not _SYMBOL.fullmatch(order["symbol"]):
        raise ValueError("symbol must be an uppercase equity symbol")
    if order["side"] not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    if order["order_type"] != "LIMIT":
        raise ValueError("MVP OrderPlan orders must be LIMIT")
    if order["market_hours"] != "regular_hours":
        raise ValueError("MVP orders require regular_hours")
    if order["time_in_force"] != "gfd":
        raise ValueError("MVP orders require gfd")
    for field in fields & _DECIMAL_ORDER_FIELDS:
        if Decimal(order[field]) <= 0:
            raise ValueError(f"{field} must be greater than zero")
    if Decimal(order["price_tolerance_pct"]) > Decimal("0.10"):
        raise ValueError("price_tolerance_pct must not exceed 0.10")
    reference_price = Decimal(order["reference_price_at_decision"])
    limit_move = abs(Decimal(order["limit_price"]) - reference_price) / reference_price
    if limit_move > Decimal(order["price_tolerance_pct"]):
        raise ValueError("limit_price must be inside price_tolerance_pct")


def _validate_account_baseline(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"cash", "positions"}:
        raise ValueError("account_baseline fields do not match the schema")
    cash = require_decimal_string(value["cash"], "account_baseline cash")
    if Decimal(cash) < 0:
        raise ValueError("account_baseline cash must be non-negative")
    positions = value["positions"]
    if not isinstance(positions, Mapping):
        raise ValueError("account_baseline positions must be an object")
    for symbol, quantity in positions.items():
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
            raise ValueError("account_baseline position symbols must be uppercase equities")
        quantity = require_decimal_string(quantity, "account_baseline position quantity")
        if Decimal(quantity) <= 0:
            raise ValueError("account_baseline position quantities must be positive")
    validate_json(value)
    return value


@dataclass(frozen=True, init=False)
class OrderPlan:
    order_plan_id: str
    decision_time: str
    account_id: str
    model_config_version: str
    decision_snapshot_id: str
    market_snapshot_as_of: str
    account_baseline: Mapping[str, Any]
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
        account_baseline = _validate_account_baseline(document["account_baseline"])
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
        object.__setattr__(plan, "account_baseline", freeze_json(account_baseline))
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
            "account_baseline": thaw_json(self.account_baseline),
            "target_portfolio": thaw_json(self.target_portfolio),
            "orders": thaw_json(self.orders),
        }
