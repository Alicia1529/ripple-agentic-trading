"""Deterministic T+1 quote-fill simulation for one shadow account lane."""

from decimal import Decimal
from typing import Any, Mapping


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _is_marketable(order: Mapping[str, Any], quote_price: Decimal) -> bool:
    if order["type"] == "market":
        return True
    limit_price = Decimal(order["limit_price"])
    return quote_price <= limit_price if order["side"] == "buy" else quote_price >= limit_price


def simulate_shadow_fills(
    risk_result: Mapping[str, Any],
    execution_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Return fill attempts and post-fill account state without broker I/O."""
    account = execution_context["account"]
    cash = Decimal(account["cash"])
    positions = {
        symbol: {
            "quantity": Decimal(position["quantity"]),
            "average_cost": Decimal(position["average_cost"]),
        }
        for symbol, position in account["positions"].items()
    }
    loss_sales = [dict(sale) for sale in account["loss_sales"]]
    new_positions_today = account["new_positions_today"]
    fill_attempts = []

    for action in risk_result["actions"]:
        if not action["allowed"]:
            continue
        order = action["broker_order"]
        symbol = action["symbol"]
        quote_text = execution_context["quotes"][symbol]["price"]
        quote_price = Decimal(quote_text)
        quantity = Decimal(action["actual_sizing"]["value"])
        if not _is_marketable(order, quote_price):
            fill_attempts.append({
                "order_id": action["order_id"],
                "symbol": symbol,
                "side": action["side"],
                "quantity": action["actual_sizing"]["value"],
                "price": quote_text,
                "filled_at": execution_context["as_of"],
                "status": "not_filled",
                "reason_code": "limit_not_marketable",
            })
            continue

        previous = positions.get(symbol)
        if action["side"] == "BUY":
            previous_quantity = previous["quantity"] if previous else Decimal("0")
            previous_cost = previous["average_cost"] if previous else Decimal("0")
            total_quantity = previous_quantity + quantity
            average_cost = (
                previous_quantity * previous_cost + quantity * quote_price
            ) / total_quantity
            positions[symbol] = {
                "quantity": total_quantity,
                "average_cost": average_cost,
            }
            cash -= quantity * quote_price
            if previous_quantity == 0:
                new_positions_today += 1
        else:
            if previous is None or quantity > previous["quantity"]:
                raise ValueError("shadow fill exceeds the available position")
            cash += quantity * quote_price
            if quote_price < previous["average_cost"]:
                loss_sales.append({
                    "symbol": symbol,
                    "sold_at": execution_context["as_of"],
                })
            remaining = previous["quantity"] - quantity
            if remaining == 0:
                del positions[symbol]
            else:
                positions[symbol] = {
                    "quantity": remaining,
                    "average_cost": previous["average_cost"],
                }
        fill_attempts.append({
            "order_id": action["order_id"],
            "symbol": symbol,
            "side": action["side"],
            "quantity": action["actual_sizing"]["value"],
            "price": quote_text,
            "filled_at": execution_context["as_of"],
            "status": "filled",
            "reason_code": "assumed_t_plus_one_quote_fill",
        })

    filled_count = sum(fill["status"] == "filled" for fill in fill_attempts)
    if not fill_attempts:
        fill_status = "no_actions"
    elif filled_count == 0:
        fill_status = "not_filled"
    elif filled_count == len(fill_attempts):
        fill_status = "filled"
    else:
        fill_status = "partial"
    ending_positions = {
        symbol: {
            "quantity": _format_decimal(position["quantity"]),
            "average_cost": _format_decimal(position["average_cost"]),
        }
        for symbol, position in sorted(positions.items())
    }
    return {
        "fill_status": fill_status,
        "shadow_fills": fill_attempts,
        "ending_account": {
            "equity": account["equity"],
            "cash": _format_decimal(cash),
            "daily_pnl": account["daily_pnl"],
            "high_water_mark": account["high_water_mark"],
            "new_positions_today": new_positions_today,
            "positions": ending_positions,
            "loss_sales": loss_sales,
        },
    }
