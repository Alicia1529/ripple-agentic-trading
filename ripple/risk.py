"""Deterministic risk evaluation for one published OrderPlan."""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Any, Mapping

from ._immutable_json import validate_json
from ._validation import require_decimal_string, require_nonempty_string
from .order_plan import OrderPlan


_RULE_FIELDS = {"account_id", "execution", "universe", "risk"}
_RISK_FIELDS = {
    "max_position_pct",
    "max_new_positions_per_day",
    "daily_loss_pct",
    "drawdown_tier1_pct",
    "drawdown_tier2_pct",
    "max_quote_age_minutes",
    "wash_sale_lookback_days",
    "stop_loss_pct",
    "take_profit_pct",
}
_CONTEXT_FIELDS = {"as_of", "account", "quotes"}
_ACCOUNT_FIELDS = {
    "equity",
    "cash",
    "daily_pnl",
    "high_water_mark",
    "new_positions_today",
    "positions",
    "loss_sales",
}


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return parsed


def _rejected_action(order: Mapping[str, Any], reason_code: str) -> dict[str, Any]:
    sizing_field = "quantity" if "quantity" in order else "dollar_amount"
    return {
        "order_id": order["order_id"],
        "allowed": False,
        "reason_code": reason_code,
        "original_sizing": {"field": sizing_field, "value": order[sizing_field]},
        "actual_sizing": None,
        "broker_order": None,
    }


def _positive_decimal(value: Any, field: str, *, allow_zero: bool = False) -> Decimal:
    parsed = Decimal(require_decimal_string(value, field))
    if parsed < 0 or (parsed == 0 and not allow_zero):
        raise ValueError(f"{field} must be {'non-negative' if allow_zero else 'positive'}")
    return parsed


def _validate_inputs(execution_context: Mapping[str, Any], rules: Mapping[str, Any]) -> None:
    validate_json(execution_context)
    validate_json(rules)
    if set(rules) != _RULE_FIELDS:
        raise ValueError("risk rule fields do not match the schema")
    if not isinstance(rules["execution"], Mapping) or set(rules["execution"]) != {"mode"}:
        raise ValueError("execution fields do not match the schema")
    if rules["execution"]["mode"] not in {"dry_run", "live", "disabled"}:
        raise ValueError("execution.mode is not supported")
    require_nonempty_string(rules["account_id"], "account_id")
    universe = rules["universe"]
    if (
        not isinstance(universe, list)
        or not universe
        or any(not isinstance(symbol, str) or not symbol for symbol in universe)
        or len(universe) != len(set(universe))
    ):
        raise ValueError("universe must contain unique symbols")
    risk = rules["risk"]
    if not isinstance(risk, Mapping) or set(risk) != _RISK_FIELDS:
        raise ValueError("risk fields do not match the schema")
    for field in (
        "max_position_pct", "daily_loss_pct", "drawdown_tier1_pct",
        "drawdown_tier2_pct", "stop_loss_pct", "take_profit_pct",
    ):
        value = _positive_decimal(risk[field], field)
        if value > 1:
            raise ValueError(f"{field} must not exceed one")
    for field in (
        "max_new_positions_per_day", "max_quote_age_minutes", "wash_sale_lookback_days",
    ):
        if not isinstance(risk[field], int) or isinstance(risk[field], bool) or risk[field] <= 0:
            raise ValueError(f"{field} must be a positive integer")

    if not isinstance(execution_context, Mapping) or set(execution_context) != _CONTEXT_FIELDS:
        raise ValueError("execution context fields do not match the schema")
    _timestamp(execution_context["as_of"])
    account = execution_context["account"]
    if not isinstance(account, Mapping) or set(account) != _ACCOUNT_FIELDS:
        raise ValueError("account fields do not match the schema")
    equity = _positive_decimal(account["equity"], "equity")
    _positive_decimal(account["cash"], "cash", allow_zero=True)
    require_decimal_string(account["daily_pnl"], "daily_pnl")
    high_water = _positive_decimal(account["high_water_mark"], "high_water_mark")
    if high_water < equity:
        raise ValueError("high_water_mark must not be below equity")
    if (
        not isinstance(account["new_positions_today"], int)
        or isinstance(account["new_positions_today"], bool)
        or account["new_positions_today"] < 0
    ):
        raise ValueError("new_positions_today must be a non-negative integer")
    positions = account["positions"]
    if not isinstance(positions, Mapping):
        raise ValueError("positions must be an object")
    for symbol, position in positions.items():
        if not isinstance(symbol, str) or not isinstance(position, Mapping) or set(position) != {
            "quantity", "average_cost"
        }:
            raise ValueError("position fields do not match the schema")
        _positive_decimal(position["quantity"], "position quantity")
        _positive_decimal(position["average_cost"], "position average_cost")
    loss_sales = account["loss_sales"]
    if not isinstance(loss_sales, list):
        raise ValueError("loss_sales must be a list")
    for sale in loss_sales:
        if not isinstance(sale, Mapping) or set(sale) != {"symbol", "sold_at"}:
            raise ValueError("loss sale fields do not match the schema")
        require_nonempty_string(sale["symbol"], "loss sale symbol")
        _timestamp(sale["sold_at"])
    quotes = execution_context["quotes"]
    if not isinstance(quotes, Mapping):
        raise ValueError("quotes must be an object")
    for symbol, quote in quotes.items():
        if not isinstance(symbol, str) or not isinstance(quote, Mapping) or set(quote) != {
            "price", "as_of"
        }:
            raise ValueError("quote fields do not match the schema")
        _positive_decimal(quote["price"], "quote price")
        _timestamp(quote["as_of"])


def evaluate_plan(
    plan_document: Mapping[str, Any],
    execution_context: Mapping[str, Any],
    rules: Mapping[str, Any],
) -> dict[str, Any]:
    """Return credential-free execution actions for one plan."""
    _validate_inputs(execution_context, rules)
    plan = OrderPlan.from_dict(plan_document)
    if plan.account_id != rules.get("account_id"):
        raise ValueError("plan account_id does not match rules")

    mode = rules["execution"]["mode"]
    universe = rules["universe"]

    account = execution_context.get("account")
    if not isinstance(account, Mapping):
        raise ValueError("account must be an object")
    quotes = execution_context["quotes"]

    execution_time = _timestamp(execution_context["as_of"])
    equity = Decimal(account["equity"])
    high_water_mark = Decimal(account["high_water_mark"])
    daily_pnl = Decimal(account["daily_pnl"])
    risk_rules = rules["risk"]
    drawdown = (high_water_mark - equity) / high_water_mark

    position_alerts = []
    for symbol, position in account["positions"].items():
        quote = quotes.get(symbol)
        if not isinstance(quote, Mapping):
            raise ValueError(f"missing quote for held position {symbol}")
        current_price = Decimal(quote["price"])
        average_cost = Decimal(position["average_cost"])
        return_pct = (current_price - average_cost) / average_cost
        kind = None
        if return_pct <= -Decimal(risk_rules["stop_loss_pct"]):
            kind = "stop_loss"
        elif return_pct >= Decimal(risk_rules["take_profit_pct"]):
            kind = "take_profit"
        if kind:
            position_alerts.append({
                "symbol": symbol,
                "kind": kind,
                "current_price": quote["price"],
                "average_cost": position["average_cost"],
            })

    actions = []
    new_positions_reserved = account["new_positions_today"]
    for order in plan.orders:
        symbol = order["symbol"]
        if symbol not in universe:
            raise ValueError("planned order symbol is outside the universe")
        if mode == "disabled":
            actions.append(_rejected_action(order, "execution_disabled"))
            continue
        quote = quotes.get(symbol)
        if not isinstance(quote, Mapping):
            actions.append(_rejected_action(order, "missing_quote"))
            continue
        current_price = Decimal(quote["price"])
        quote_time = _timestamp(quote["as_of"])
        quote_age = execution_time - quote_time
        if quote_age < timedelta(0) or quote_age > timedelta(
            minutes=risk_rules["max_quote_age_minutes"]
        ):
            actions.append(_rejected_action(order, "stale_quote"))
            continue
        reference_price = Decimal(order["reference_price_at_decision"])
        price_move = abs(current_price - reference_price) / reference_price
        if price_move > Decimal(order["price_tolerance_pct"]):
            actions.append(_rejected_action(order, "price_outside_tolerance"))
            continue
        if order["side"] == "BUY" and daily_pnl <= -(equity * Decimal(risk_rules["daily_loss_pct"])):
            actions.append(_rejected_action(order, "daily_loss"))
            continue
        if order["side"] == "BUY" and drawdown >= Decimal(risk_rules["drawdown_tier2_pct"]):
            actions.append(_rejected_action(order, "drawdown_tier2"))
            continue
        if order["side"] == "BUY" and drawdown >= Decimal(risk_rules["drawdown_tier1_pct"]):
            actions.append(_rejected_action(order, "drawdown_tier1"))
            continue

        positions = account.get("positions", {})
        if not isinstance(positions, Mapping):
            raise ValueError("positions must be an object")
        is_new_position = symbol not in positions or Decimal(positions[symbol]["quantity"]) == 0
        if (
            order["side"] == "BUY"
            and is_new_position
            and new_positions_reserved >= risk_rules["max_new_positions_per_day"]
        ):
            actions.append(_rejected_action(order, "max_new_positions"))
            continue
        if order["side"] == "BUY":
            lookback = timedelta(days=risk_rules["wash_sale_lookback_days"])
            recent_loss_sale = any(
                sale.get("symbol") == symbol
                and timedelta(0) <= execution_time - _timestamp(sale["sold_at"]) <= lookback
                for sale in account.get("loss_sales", [])
            )
            if recent_loss_sale:
                actions.append(_rejected_action(order, "wash_sale"))
                continue

        sizing_field = "quantity" if "quantity" in order else "dollar_amount"
        sizing_value = order[sizing_field]
        actual_value = sizing_value
        reason_code = "allowed"

        if order["side"] == "BUY":
            position = positions.get(symbol, {}) if isinstance(positions, Mapping) else {}
            current_quantity = Decimal(position.get("quantity", "0"))
            current_value = current_quantity * current_price
            max_position_value = Decimal(account["equity"]) * Decimal(
                rules["risk"]["max_position_pct"]
            )
            position_room = max(Decimal("0"), max_position_value - current_value)
            cash_room = Decimal(account["cash"])
            allowed_notional = min(position_room, cash_room)
            requested_notional = (
                Decimal(sizing_value) * current_price
                if sizing_field == "quantity"
                else Decimal(sizing_value)
            )
            if requested_notional > allowed_notional:
                reason_code = "max_position" if position_room <= cash_room else "available_cash"
                if sizing_field == "quantity":
                    clipped = (allowed_notional / current_price).quantize(
                        Decimal("0.000001"), rounding=ROUND_DOWN
                    )
                else:
                    clipped = allowed_notional.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
                if clipped <= 0:
                    actions.append(_rejected_action(order, reason_code))
                    continue
                actual_value = _format_decimal(clipped)
        else:
            position_quantity = Decimal(positions.get(symbol, {}).get("quantity", "0"))
            requested_quantity = (
                Decimal(sizing_value)
                if sizing_field == "quantity"
                else Decimal(sizing_value) / current_price
            )
            if position_quantity <= 0:
                actions.append(_rejected_action(order, "insufficient_position"))
                continue
            if requested_quantity > position_quantity:
                reason_code = "position_quantity"
                if sizing_field == "quantity":
                    actual_value = _format_decimal(position_quantity)
                else:
                    actual_value = _format_decimal(
                        (position_quantity * current_price).quantize(
                            Decimal("0.01"), rounding=ROUND_DOWN
                        )
                    )
        broker_order = {
            "side": order["side"].lower(),
            "symbol": symbol,
            "type": order["order_type"].lower(),
            sizing_field: actual_value,
        }
        for field in ("limit_price", "stop_price", "market_hours", "time_in_force"):
            if field in order:
                broker_order[field] = order[field]
        broker_order["ref_id"] = order["order_id"]
        actions.append({
            "order_id": order["order_id"],
            "allowed": True,
            "reason_code": reason_code,
            "original_sizing": {"field": sizing_field, "value": sizing_value},
            "actual_sizing": {"field": sizing_field, "value": actual_value},
            "broker_order": broker_order,
        })
        if order["side"] == "BUY" and is_new_position:
            new_positions_reserved += 1

    allowed_count = sum(action["allowed"] for action in actions)
    if not actions or allowed_count == len(actions):
        status = "partial" if any(
            action["reason_code"] != "allowed" for action in actions
        ) else "allowed"
    elif allowed_count == 0:
        status = "rejected"
    else:
        status = "partial"
    return {
        "order_plan_id": plan.order_plan_id,
        "account_id": plan.account_id,
        "mode": mode,
        "status": status,
        "actions": actions,
        "position_alerts": position_alerts,
    }
