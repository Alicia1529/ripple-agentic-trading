"""Compile compact, deterministic facts for Growth Momentum v2 Lite."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Mapping, Sequence

from .account_config import load_account_config


_BENCHMARKS = {"SPY", "QQQ"}
_DOCUMENT_FIELDS = {"as_of", "expected_latest_session", "retrieved_at", "symbols"}
_SYMBOL_FIELDS = {
    "bars",
    "next_earnings_date",
    "sector",
    "prices_source_url",
    "sector_source_url",
    "earnings_source_url",
}
_BAR_FIELDS = {"date", "open", "high", "low", "close", "interpolated"}


def _decimal(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{field} must be a decimal string") from error
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    return parsed


def _format(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered if rendered not in {"", "-0"} else "0"


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _source(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ValueError(f"{field} must be an https URL")
    return value


def _aware_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be a timezone-aware timestamp") from error
    if parsed.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    return value


def _bars(
    raw: Any, symbol: str, as_of: date,
) -> tuple[list[dict[str, Any]], int, int, bool]:
    if not isinstance(raw, list):
        raise ValueError(f"{symbol}.bars must be a list")
    accepted = []
    interpolated_count = 0
    previous_date = None
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) != _BAR_FIELDS:
            raise ValueError(f"{symbol}.bars[{index}] fields do not match the schema")
        bar_date = _date(item["date"], f"{symbol}.bars[{index}].date")
        if bar_date.weekday() >= 5:
            raise ValueError(f"{symbol}.bars cannot contain weekend dates")
        if bar_date > as_of or (previous_date is not None and bar_date <= previous_date):
            raise ValueError(f"{symbol}.bars dates must be ordered sessions")
        if not isinstance(item["interpolated"], bool):
            raise ValueError(f"{symbol}.bars[{index}].interpolated must be boolean")
        prices = {
            field: _decimal(item[field], f"{symbol}.bars[{index}].{field}")
            for field in ("open", "high", "low", "close")
        }
        if min(prices.values()) <= 0 or prices["high"] < max(
            prices["open"], prices["low"], prices["close"]
        ) or prices["low"] > min(
            prices["open"], prices["high"], prices["close"]
        ):
            raise ValueError(f"{symbol}.bars[{index}] has invalid OHLC values")
        if item["interpolated"]:
            interpolated_count += 1
        else:
            accepted.append({"date": bar_date, **prices})
        previous_date = bar_date
    required_window_interpolated = any(
        item["interpolated"] for item in raw[-66:]
    )
    return accepted, len(raw), interpolated_count, required_window_interpolated


def _mom_60_10(bars: Sequence[Mapping[str, Any]], end: int) -> Decimal:
    return bars[end - 10]["close"] / bars[end - 60]["close"] - Decimal(1)


def _technical_facts(
    bars: Sequence[Mapping[str, Any]],
    qqq_by_date: Mapping[date, tuple[Sequence[Mapping[str, Any]], int]],
) -> dict[str, Any]:
    end = len(bars) - 1
    closes = [bar["close"] for bar in bars]
    momentum = _mom_60_10(bars, end)
    true_ranges = []
    for index in range(end - 19, end + 1):
        bar = bars[index]
        previous_close = bars[index - 1]["close"]
        true_ranges.append(max(
            bar["high"] - bar["low"],
            abs(bar["high"] - previous_close),
            abs(bar["low"] - previous_close),
        ))
    atr20_pct = (sum(true_ranges, Decimal(0)) / Decimal(20)) / closes[-1]

    latest_date = bars[end]["date"]
    qqq_bars, qqq_end = qqq_by_date[latest_date]
    relative_momentum = momentum - _mom_60_10(qqq_bars, qqq_end)
    streak = 0
    for index in range(end, 59, -1):
        qqq_bars, qqq_end = qqq_by_date[bars[index]["date"]]
        if _mom_60_10(bars, index) - _mom_60_10(qqq_bars, qqq_end) > 0:
            break
        streak += 1
        if streak == 5:
            break

    return {
        "close": _format(closes[-1]),
        "sma50": _format(sum(closes[-50:], Decimal(0)) / Decimal(50)),
        "mom_60_10": _format(momentum),
        "atr20_pct": _format(atr20_pct),
        "rel_mom_qqq": _format(relative_momentum),
        "rel_mom_streak": streak,
    }


def _unavailable(values: Mapping[str, Any], reason_code: str) -> dict[str, Any]:
    return {
        "asset_role": values["asset_role"],
        "days_to_earnings": values["days_to_earnings"],
        "reason_code": reason_code,
        "sector": values["sector"],
        "status": "unavailable",
    }


def compile_growth_momentum_lite_facts(
    document: Mapping[str, Any],
    expected_symbols: Sequence[str],
) -> dict[str, Any]:
    """Return compact facts and provenance without retaining raw daily bars."""
    if not isinstance(document, Mapping) or set(document) != _DOCUMENT_FIELDS:
        raise ValueError("facts input fields do not match the schema")
    as_of = _date(document["as_of"], "as_of")
    latest_session = _date(document["expected_latest_session"], "expected_latest_session")
    retrieved_at = _aware_timestamp(document["retrieved_at"], "retrieved_at")
    if latest_session.weekday() >= 5 or latest_session > as_of:
        raise ValueError("expected_latest_session must be a completed weekday")
    if (
        isinstance(expected_symbols, (str, bytes))
        or not isinstance(expected_symbols, Sequence)
        or not expected_symbols
        or any(not isinstance(symbol, str) or not symbol for symbol in expected_symbols)
        or len(expected_symbols) != len(set(expected_symbols))
    ):
        raise ValueError("configured universe must contain unique symbols")
    symbols = document["symbols"]
    if not isinstance(symbols, Mapping) or set(symbols) != set(expected_symbols):
        raise ValueError("symbols must exactly match the configured universe")
    if not _BENCHMARKS <= set(symbols):
        raise ValueError("symbols must include SPY and QQQ")

    normalized = {}
    provenance = {}
    for symbol, raw in symbols.items():
        if not isinstance(raw, Mapping) or set(raw) != _SYMBOL_FIELDS:
            raise ValueError(f"{symbol} fields do not match the schema")
        bars, requested_count, interpolated_count, required_window_interpolated = _bars(
            raw["bars"], symbol, as_of,
        )
        is_benchmark = symbol in _BENCHMARKS
        earnings_date = (
            None if raw["next_earnings_date"] is None
            else _date(raw["next_earnings_date"], f"{symbol}.next_earnings_date")
        )
        if is_benchmark and earnings_date is not None:
            raise ValueError(f"{symbol}.next_earnings_date must be null")
        if earnings_date is not None and earnings_date <= as_of:
            raise ValueError(f"{symbol}.next_earnings_date must be after as_of")
        sector = raw["sector"]
        if sector is not None and (not isinstance(sector, str) or not sector):
            raise ValueError(f"{symbol}.sector must be null or non-empty")
        days_to_earnings = None if earnings_date is None else (earnings_date - as_of).days
        normalized[symbol] = {
            "asset_role": "benchmark" if is_benchmark else "security",
            "bars": bars,
            "days_to_earnings": days_to_earnings,
            "required_window_interpolated": required_window_interpolated,
            "sector": sector,
        }
        provenance[symbol] = {
            "accepted_bar_count": len(bars),
            "earnings": _source(raw["earnings_source_url"], f"{symbol}.earnings_source_url"),
            "expected_latest_session": latest_session.isoformat(),
            "interpolated_bar_count": interpolated_count,
            "next_earnings_date": earnings_date.isoformat() if earnings_date else None,
            "prices": _source(raw["prices_source_url"], f"{symbol}.prices_source_url"),
            "prices_as_of": bars[-1]["date"].isoformat() if bars else None,
            "requested_bar_count": requested_count,
            "sector": _source(raw["sector_source_url"], f"{symbol}.sector_source_url"),
        }

    preliminary = {}
    for symbol, values in normalized.items():
        if len(values["bars"]) < 66:
            preliminary[symbol] = "insufficient_completed_sessions"
        elif values["bars"][-1]["date"] != latest_session:
            preliminary[symbol] = "missing_latest_completed_session"
        elif values["required_window_interpolated"]:
            preliminary[symbol] = "interpolated_session_in_required_window"
        else:
            preliminary[symbol] = None

    facts = {}
    qqq_available = preliminary["QQQ"] is None
    qqq_by_date = {}
    if qqq_available:
        qqq_bars = normalized["QQQ"]["bars"]
        qqq_by_date = {
            bar["date"]: (qqq_bars, index)
            for index, bar in enumerate(qqq_bars)
            if index >= 60
        }
    with localcontext() as context:
        context.prec = 28
        for symbol in sorted(normalized):
            values = normalized[symbol]
            reason = preliminary[symbol]
            if reason is None and symbol != "QQQ" and not qqq_available:
                reason = "qqq_facts_unavailable"
            if reason is None and any(
                bar["date"] not in qqq_by_date
                for bar in values["bars"][-5:]
            ):
                reason = "qqq_sessions_not_aligned"
            if reason is not None:
                facts[symbol] = _unavailable(values, reason)
                continue
            facts[symbol] = {
                "asset_role": values["asset_role"],
                "days_to_earnings": values["days_to_earnings"],
                "sector": values["sector"],
                "status": "available",
                **_technical_facts(values["bars"], qqq_by_date),
            }
    return {
        "as_of": as_of.isoformat(),
        "expected_latest_session": latest_session.isoformat(),
        "facts": facts,
        "provenance": provenance,
        "retrieved_at": retrieved_at,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile compact Growth Momentum Lite facts")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = load_account_config(args.config)
        document = json.loads(args.input.read_text())
        result = compile_growth_momentum_lite_facts(document, config.universe)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    except (FileExistsError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
