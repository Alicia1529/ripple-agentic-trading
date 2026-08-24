"""Minimal Account A growth/momentum Decision policy."""

from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from ._validation import require_aware_timestamp, require_decimal_string


POLICY_ID = "growth_momentum_v1"
POLICY_VERSION = "mvp1"
_INPUT_FIELDS = {
    "decision_time", "account_baseline", "market_gate", "benchmark", "candidates",
}
_MARKET_FIELDS = {"symbol", "close", "sma50", "source_uri", "as_of"}
_BENCHMARK_FIELDS = {"symbol", "return_60d", "source_uri", "as_of"}
_CANDIDATE_FIELDS = {
    "symbol", "close", "sma50", "return_60d", "next_earnings_date",
    "earnings_status", "business_quality_pass", "business_quality_reason",
    "source_uri", "as_of",
}


def _decimal(value: Any, field: str, *, positive: bool = False) -> Decimal:
    parsed = Decimal(require_decimal_string(value, field))
    if positive and parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return parsed


def _source_uri(value: Any) -> str:
    if not isinstance(value, str) or urlparse(value).scheme not in {"http", "https"}:
        raise ValueError("source_uri must be an http(s) URI")
    return value


def _as_of(value: Any, decision_at: datetime) -> str:
    parsed = datetime.fromisoformat(
        require_aware_timestamp(value, "as_of").replace("Z", "+00:00")
    )
    age = decision_at - parsed.astimezone(decision_at.tzinfo)
    if age.total_seconds() < 0 or age.days > 3:
        raise ValueError("market evidence must be no more than three calendar days old")
    return value


def _weekdays_between(start: date, end: date) -> int:
    count = 0
    candidate = start
    while candidate < end:
        candidate = candidate.fromordinal(candidate.toordinal() + 1)
        if candidate.weekday() < 5:
            count += 1
    return count


def _validate_baseline(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"cash", "positions"}:
        raise ValueError("account_baseline fields do not match the schema")
    cash = _decimal(value["cash"], "account_baseline cash")
    if cash < 0 or not isinstance(value["positions"], Mapping):
        raise ValueError("account_baseline is malformed")
    positions = {}
    for symbol, quantity in value["positions"].items():
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("position symbol is malformed")
        if _decimal(quantity, "position quantity", positive=True) <= 0:
            raise ValueError("position quantity must be positive")
        positions[symbol] = quantity
    return {"cash": value["cash"], "positions": positions}


def _validate_market(
    value: Any, expected_symbol: str, decision_at: datetime, fields: set[str],
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{expected_symbol} evidence fields do not match the schema")
    if value["symbol"] != expected_symbol:
        raise ValueError(f"market role must use {expected_symbol}")
    result = dict(value)
    _source_uri(result["source_uri"])
    _as_of(result["as_of"], decision_at)
    return result


def _eligible_candidate(
    candidate: Mapping[str, Any], benchmark_return: Decimal, decision_at: datetime,
) -> bool:
    close = _decimal(candidate["close"], "candidate close", positive=True)
    sma50 = _decimal(candidate["sma50"], "candidate sma50", positive=True)
    return_60d = _decimal(candidate["return_60d"], "candidate return_60d")
    if candidate["earnings_status"] == "unknown":
        return False
    if not isinstance(candidate["next_earnings_date"], str):
        raise ValueError("known next_earnings_date must be an ISO date")
    earnings_date = date.fromisoformat(candidate["next_earnings_date"])
    return (
        close > sma50
        and return_60d > 0
        and return_60d > benchmark_return
        and candidate["earnings_status"] in {"confirmed", "estimated"}
        and earnings_date > decision_at.date()
        and _weekdays_between(decision_at.date(), earnings_date) > 2
        and candidate["business_quality_pass"] is True
        and bool(candidate["business_quality_reason"].strip())
    )


def build_decision_input(facts: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    """Build the strict existing Decision input from minimal sourced strategy facts."""
    if not isinstance(facts, Mapping) or set(facts) != _INPUT_FIELDS:
        raise ValueError("growth momentum input fields do not match the schema")
    if config.get("account_id") != "account_A":
        raise ValueError("growth_momentum_v1 MVP is limited to account_A")
    universe = config.get("universe")
    if not isinstance(universe, list):
        raise ValueError("configuration universe is malformed")
    risk = config.get("risk")
    if not isinstance(risk, Mapping) or _decimal(
        risk.get("max_position_pct"), "max_position_pct",
    ) < Decimal("0.10"):
        raise ValueError("Account A risk limit does not permit a 10% initial position")

    decision_time = require_aware_timestamp(facts["decision_time"], "decision_time")
    decision_at = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
    baseline = _validate_baseline(facts["account_baseline"])
    if baseline["positions"]:
        raise ValueError("growth_momentum_v1 MVP requires an empty Account A portfolio")
    market_gate = _validate_market(
        facts["market_gate"], "SPY", decision_at, _MARKET_FIELDS,
    )
    benchmark = _validate_market(
        facts["benchmark"], "QQQ", decision_at, _BENCHMARK_FIELDS,
    )
    spy_close = _decimal(market_gate["close"], "SPY close", positive=True)
    spy_sma50 = _decimal(market_gate["sma50"], "SPY sma50", positive=True)
    benchmark_return = _decimal(benchmark["return_60d"], "QQQ return_60d")

    candidates = facts["candidates"]
    if not isinstance(candidates, list) or len(candidates) > 3:
        raise ValueError("candidates must be a list of at most three objects")
    seen: set[str] = set()
    eligible: list[tuple[Decimal, str, dict[str, Any]]] = []
    for candidate_value in candidates:
        if not isinstance(candidate_value, Mapping) or set(candidate_value) != _CANDIDATE_FIELDS:
            raise ValueError("candidate fields do not match the schema")
        candidate = dict(candidate_value)
        symbol = candidate["symbol"]
        if symbol not in universe or symbol in {"SPY", "QQQ"} or symbol in seen:
            raise ValueError("candidate symbol is invalid or duplicated")
        seen.add(symbol)
        if candidate["earnings_status"] not in {"confirmed", "estimated", "unknown"}:
            raise ValueError("earnings_status is unsupported")
        if not isinstance(candidate["business_quality_pass"], bool):
            raise ValueError("business_quality_pass must be boolean")
        if not isinstance(candidate["business_quality_reason"], str):
            raise ValueError("business_quality_reason must be a string")
        _source_uri(candidate["source_uri"])
        _as_of(candidate["as_of"], decision_at)
        return_60d = _decimal(candidate["return_60d"], "candidate return_60d")
        if _eligible_candidate(candidate, benchmark_return, decision_at):
            eligible.append((return_60d - benchmark_return, symbol, candidate))

    selected = None
    outcome_reason = "NO_ELIGIBLE_CANDIDATE"
    if spy_close <= spy_sma50:
        outcome_reason = "MARKET_RISK_OFF"
    elif eligible:
        eligible.sort(key=lambda item: (-item[0], item[1]))
        selected = eligible[0][2]
        outcome_reason = "BUY_TOP_RELATIVE_STRENGTH"

    canonical_facts = json.dumps(facts, sort_keys=True, separators=(",", ":"))
    facts_sha256 = hashlib.sha256(canonical_facts.encode()).hexdigest()
    snapshot_id = str(uuid5(
        NAMESPACE_URL, f"ripple:{config['account_id']}:{decision_time}:{facts_sha256}",
    ))
    inputs = {
        "strategy": {"id": POLICY_ID, "version": POLICY_VERSION},
        "facts_sha256": facts_sha256,
        "market_gate": market_gate,
        "benchmark": benchmark,
        "candidates": candidates,
        "outcome": {
            "result": "BUY_ONLY" if selected else "NO_TRADE",
            "reason": outcome_reason,
            "selected_symbol": selected["symbol"] if selected else None,
        },
    }

    target_portfolio = {"cash": "1"}
    orders: list[dict[str, str]] = []
    if selected:
        close = Decimal(selected["close"])
        limit_price = (close * Decimal("1.01")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN,
        )
        quantity = (Decimal(baseline["cash"]) * Decimal("0.10") / limit_price).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        if quantity <= 0:
            raise ValueError("baseline cash is too small for a positive order")
        target_portfolio = {selected["symbol"]: "0.10", "cash": "0.90"}
        orders = [{
            "symbol": selected["symbol"],
            "side": "BUY",
            "quantity": format(quantity, "f"),
            "order_type": "LIMIT",
            "limit_price": format(limit_price, "f"),
            "price_tolerance_pct": "0.01",
            "reference_price_at_decision": selected["close"],
            "market_hours": "regular_hours",
            "time_in_force": "gfd",
        }]

    return {
        "snapshot": {
            "snapshot_id": snapshot_id,
            "as_of": decision_time,
            "universe": list(universe),
            "inputs": inputs,
        },
        "account_baseline": baseline,
        "decision": {
            "decision_time": decision_time,
            "model_config_version": f"{POLICY_ID}_{POLICY_VERSION}",
            "target_portfolio": target_portfolio,
            "orders": orders,
        },
    }
