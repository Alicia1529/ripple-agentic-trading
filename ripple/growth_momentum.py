"""Deterministically compile raw Decision facts for Growth Momentum."""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Mapping, Sequence

from .account_config import load_account_config


_SYMBOL_FIELDS = {
    "bars",
    "financials",
    "next_earnings_date",
    "sector",
    "prices_source_url",
    "financials_source_url",
    "earnings_source_url",
}
_BAR_FIELDS = {"date", "open", "high", "low", "close", "interpolated"}
_FINANCIAL_FIELDS = {
    "period_end_date",
    "revenue",
    "gross_profit",
    "operating_cash_flow",
    "capital_expenditures",
}
_BENCHMARKS = {"SPY", "QQQ"}


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


def _validate_source(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ValueError(f"{field} must be an https URL")
    return value


def _bars(raw: Any, symbol: str, as_of: date) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) < 66:
        raise ValueError(f"{symbol}.bars requires at least 66 completed sessions")
    result = []
    previous_date = None
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) != _BAR_FIELDS:
            raise ValueError(f"{symbol}.bars[{index}] fields do not match the schema")
        bar_date = _date(item["date"], f"{symbol}.bars[{index}].date")
        if bar_date.weekday() >= 5:
            raise ValueError(f"{symbol}.bars cannot contain weekend dates")
        if bar_date > as_of or (previous_date is not None and bar_date <= previous_date):
            raise ValueError(f"{symbol}.bars dates must be ordered completed sessions")
        if item["interpolated"] is not False:
            raise ValueError(f"{symbol}.bars cannot contain interpolated sessions")
        prices = {
            field: _decimal(item[field], f"{symbol}.bars[{index}].{field}")
            for field in ("open", "high", "low", "close")
        }
        if min(prices.values()) <= 0 or prices["high"] < max(
            prices["open"], prices["low"], prices["close"]
        ) or prices["low"] > min(prices["open"], prices["high"], prices["close"]):
            raise ValueError(f"{symbol}.bars[{index}] has invalid OHLC values")
        result.append({"date": bar_date, **prices})
        previous_date = bar_date
    return result


def _financials(raw: Any, symbol: str, as_of: date) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) < 8:
        raise ValueError(f"{symbol}.financials requires at least 8 quarters")
    result = []
    previous_date = None
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) != _FINANCIAL_FIELDS:
            raise ValueError(f"{symbol}.financials[{index}] fields do not match the schema")
        period_date = _date(
            item["period_end_date"], f"{symbol}.financials[{index}].period_end_date"
        )
        if period_date > as_of or (previous_date is not None and period_date >= previous_date):
            raise ValueError(f"{symbol}.financials must be newest-first completed quarters")
        values = {
            field: _decimal(item[field], f"{symbol}.financials[{index}].{field}")
            for field in (
                "revenue", "gross_profit", "operating_cash_flow",
                "capital_expenditures",
            )
        }
        if values["revenue"] <= 0:
            raise ValueError(f"{symbol}.financials[{index}].revenue must be positive")
        if values["capital_expenditures"] < 0:
            raise ValueError(
                f"{symbol}.financials[{index}].capital_expenditures must be a positive outflow"
            )
        result.append({"period_end_date": period_date, **values})
        previous_date = period_date
    return result


def _mom_60_10(bars: Sequence[Mapping[str, Any]], end: int) -> Decimal:
    return bars[end - 10]["close"] / bars[end - 60]["close"] - Decimal(1)


def _technical_facts(
    bars: Sequence[Mapping[str, Any]],
    qqq_by_date: Mapping[date, tuple[Sequence[Mapping[str, Any]], int]],
) -> dict[str, Any]:
    end = len(bars) - 1
    closes = [bar["close"] for bar in bars]
    returns = [closes[index] / closes[index - 1] - Decimal(1) for index in range(end - 59, end + 1)]
    mean_return = sum(returns, Decimal(0)) / Decimal(len(returns))
    variance = sum((value - mean_return) ** 2 for value in returns) / Decimal(len(returns) - 1)
    vol_60 = variance.sqrt() * Decimal(252).sqrt()
    momentum = _mom_60_10(bars, end)
    if vol_60 == 0:
        raise ValueError("vol_60 is zero")

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
    if latest_date not in qqq_by_date:
        raise ValueError("QQQ is missing the latest aligned session")
    qqq_bars, qqq_end = qqq_by_date[latest_date]
    qqq_momentum = _mom_60_10(qqq_bars, qqq_end)
    relative_momentum = momentum - qqq_momentum

    streak = 0
    for index in range(end, 59, -1):
        session = bars[index]["date"]
        aligned = qqq_by_date.get(session)
        if aligned is None:
            raise ValueError("symbol and QQQ sessions are not aligned")
        aligned_bars, aligned_end = aligned
        if _mom_60_10(bars, index) - _mom_60_10(aligned_bars, aligned_end) > 0:
            break
        streak += 1
        if streak == 5:
            break

    return {
        "close": _format(closes[-1]),
        "sma50": _format(sum(closes[-50:], Decimal(0)) / Decimal(50)),
        "mom_60_10": _format(momentum),
        "vol_60": _format(vol_60),
        "risk_adj_mom": _format(momentum / vol_60),
        "atr20_pct": _format(atr20_pct),
        "rel_mom_qqq": _format(relative_momentum),
        "rel_mom_streak": streak,
    }


def _fundamental_facts(financials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    revenue_growth = [
        financials[index]["revenue"] / financials[index + 4]["revenue"] - Decimal(1)
        for index in range(4)
    ]
    gross_margin = [
        financials[index]["gross_profit"] / financials[index]["revenue"]
        for index in range(4)
    ]
    free_cash_flow = [
        financials[index]["operating_cash_flow"] - financials[index]["capital_expenditures"]
        for index in range(4)
    ]
    return {
        "rev_growth_yoy": [_format(value) for value in revenue_growth],
        "gross_margin": [_format(value) for value in gross_margin],
        "fcf_ttm": _format(sum(free_cash_flow, Decimal(0))),
        "fcf_trend": {
            "quarterly": [_format(value) for value in free_cash_flow],
            "improved_all_four_quarters": all(
                free_cash_flow[index] > free_cash_flow[index + 1]
                for index in range(3)
            ),
        },
    }


def compile_growth_momentum_facts(
    document: Mapping[str, Any],
    expected_symbols: Sequence[str],
) -> dict[str, Any]:
    """Return complete strategy facts from normalized, source-attributed raw inputs."""
    if not isinstance(document, Mapping) or set(document) != {"as_of", "symbols"}:
        raise ValueError("facts input fields do not match the schema")
    as_of = _date(document["as_of"], "as_of")
    symbols = document["symbols"]
    if (
        isinstance(expected_symbols, (str, bytes))
        or not isinstance(expected_symbols, Sequence)
        or not expected_symbols
        or any(not isinstance(symbol, str) or not symbol for symbol in expected_symbols)
        or len(expected_symbols) != len(set(expected_symbols))
    ):
        raise ValueError("configured universe must contain unique symbols")
    if not isinstance(symbols, Mapping) or set(symbols) != set(expected_symbols):
        raise ValueError("symbols must exactly match the configured universe")
    if "QQQ" not in symbols or "SPY" not in symbols:
        raise ValueError("symbols must include SPY and QQQ")

    normalized = {}
    for symbol, raw in symbols.items():
        if not isinstance(symbol, str) or not symbol or not isinstance(raw, Mapping):
            raise ValueError("symbols must map identifiers to objects")
        if set(raw) != _SYMBOL_FIELDS:
            raise ValueError(f"{symbol} fields do not match the schema")
        is_benchmark = symbol in _BENCHMARKS
        financials = (
            [] if is_benchmark and raw["financials"] == []
            else _financials(raw["financials"], symbol, as_of)
        )
        next_earnings_date = (
            None if is_benchmark and raw["next_earnings_date"] is None
            else _date(raw["next_earnings_date"], f"{symbol}.next_earnings_date")
        )
        normalized[symbol] = {
            "bars": _bars(raw["bars"], symbol, as_of),
            "financials": financials,
            "next_earnings_date": next_earnings_date,
            "sector": raw["sector"],
            "asset_role": "benchmark" if is_benchmark else "security",
            "sources": {
                "prices": _validate_source(raw["prices_source_url"], f"{symbol}.prices_source_url"),
                "financials": _validate_source(
                    raw["financials_source_url"], f"{symbol}.financials_source_url"
                ),
                "earnings": _validate_source(
                    raw["earnings_source_url"], f"{symbol}.earnings_source_url"
                ),
            },
        }
        if not isinstance(raw["sector"], str) or not raw["sector"]:
            raise ValueError(f"{symbol}.sector must be non-empty")
        if (as_of - normalized[symbol]["bars"][-1]["date"]).days > 4:
            raise ValueError(f"{symbol}.bars latest completed session is stale")
        if (
            normalized[symbol]["next_earnings_date"] is not None
            and normalized[symbol]["next_earnings_date"] <= as_of
        ):
            raise ValueError(f"{symbol}.next_earnings_date must be after as_of")

    qqq_bars = normalized["QQQ"]["bars"]
    qqq_by_date = {
        bar["date"]: (qqq_bars, index)
        for index, bar in enumerate(qqq_bars)
        if index >= 60
    }
    facts = {}
    provenance = {}
    with localcontext() as context:
        context.prec = 28
        for symbol in sorted(normalized):
            values = normalized[symbol]
            technical = _technical_facts(values["bars"], qqq_by_date)
            facts[symbol] = {
                **technical,
                "asset_role": values["asset_role"],
                "sector": values["sector"],
            }
            if values["asset_role"] == "security":
                facts[symbol].update({
                    **_fundamental_facts(values["financials"]),
                    "days_to_earnings": (values["next_earnings_date"] - as_of).days,
                })
            provenance[symbol] = {
                **values["sources"],
                "prices_as_of": values["bars"][-1]["date"].isoformat(),
                "financials_as_of": (
                    values["financials"][0]["period_end_date"].isoformat()
                    if values["financials"] else None
                ),
                "earnings_date": (
                    values["next_earnings_date"].isoformat()
                    if values["next_earnings_date"] else None
                ),
            }
    return {"as_of": as_of.isoformat(), "facts": facts, "provenance": provenance}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Growth Momentum Decision facts")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = load_account_config(args.config)
        document = json.loads(args.input.read_text())
        result = compile_growth_momentum_facts(document, config.universe)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    except (FileExistsError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
