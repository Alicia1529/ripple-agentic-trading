"""Strict account-lane configuration and scheduled cohort selection."""

from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Any, Iterator, Mapping

from ._immutable_json import validate_json
from ._validation import require_decimal_string, require_nonempty_string


_CONFIG_FIELDS = {"description", "strategy", "execution", "universe", "risk"}
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
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
_MODES = {"dry_run", "live", "shadow"}


@dataclass(frozen=True)
class AccountConfig:
    account_id: str
    description: str
    strategy_id: str
    strategy_path: Path
    mode: str
    universe: tuple[str, ...]
    risk: Mapping[str, Any]
    shadow_initial_cash: str | None = None

    def risk_rules(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "execution": {"mode": self.mode},
            "universe": list(self.universe),
            "risk": dict(self.risk),
        }


@dataclass(frozen=True)
class AccountCatalog:
    accounts: tuple[AccountConfig, ...]

    def __iter__(self) -> Iterator[AccountConfig]:
        return iter(self.accounts)

    def for_mode(self, mode: str) -> tuple[AccountConfig, ...]:
        if mode not in _MODES:
            raise ValueError("execution.mode is not supported")
        return tuple(config for config in self.accounts if config.mode == mode)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    validate_json(value)
    return value


def _validate_risk(risk: Any) -> dict[str, Any]:
    if not isinstance(risk, Mapping) or set(risk) != _RISK_FIELDS:
        raise ValueError("risk fields do not match the schema")
    for field in (
        "max_position_pct", "daily_loss_pct", "drawdown_tier1_pct",
        "drawdown_tier2_pct", "stop_loss_pct", "take_profit_pct",
    ):
        value = Decimal(require_decimal_string(risk[field], field))
        if value <= 0 or value > 1:
            raise ValueError(f"{field} must be greater than zero and not exceed one")
    for field in (
        "max_new_positions_per_day", "max_quote_age_minutes", "wash_sale_lookback_days",
    ):
        if not isinstance(risk[field], int) or isinstance(risk[field], bool) or risk[field] <= 0:
            raise ValueError(f"{field} must be a positive integer")
    return dict(risk)


def load_account_config(
    path: Path,
    strategies_dir: Path | None = None,
) -> AccountConfig:
    account_id = path.stem
    if not _IDENTIFIER.fullmatch(account_id):
        raise ValueError("account config filename must be a snake_case identifier")
    document = _read_json(path)
    execution = document.get("execution")
    mode = execution.get("mode") if isinstance(execution, Mapping) else None
    if mode == "shadow" and "shadow" not in document:
        raise ValueError("shadow initial_cash is required")
    expected_fields = _CONFIG_FIELDS | ({"shadow"} if mode == "shadow" else set())
    if set(document) != expected_fields:
        raise ValueError("account configuration fields do not match the schema")
    if not isinstance(execution, Mapping) or set(execution) != {"mode"} or mode not in _MODES:
        raise ValueError("execution.mode is not supported")

    description = require_nonempty_string(document["description"], "description")
    strategy_id = require_nonempty_string(document["strategy"], "strategy")
    if not _IDENTIFIER.fullmatch(strategy_id):
        raise ValueError("strategy must be a snake_case identifier")
    strategies_dir = strategies_dir or Path(__file__).resolve().parents[1] / "strategies"
    strategy_path = strategies_dir / f"{strategy_id}.md"
    if not strategy_path.is_file():
        raise ValueError(f"configured strategy does not exist: {strategy_id}")

    universe = document["universe"]
    if (
        not isinstance(universe, list)
        or not universe
        or any(not isinstance(symbol, str) or not symbol for symbol in universe)
        or len(universe) != len(set(universe))
    ):
        raise ValueError("universe must contain unique symbols")

    shadow_initial_cash = None
    if mode == "shadow":
        shadow = document["shadow"]
        if not isinstance(shadow, Mapping) or set(shadow) != {"initial_cash"}:
            raise ValueError("shadow fields must contain only initial_cash")
        shadow_initial_cash = require_decimal_string(
            shadow["initial_cash"], "shadow initial_cash",
        )
        if Decimal(shadow_initial_cash) <= 0:
            raise ValueError("shadow initial_cash must be positive")

    return AccountConfig(
        account_id=account_id,
        description=description,
        strategy_id=strategy_id,
        strategy_path=strategy_path,
        mode=mode,
        universe=tuple(universe),
        risk=_validate_risk(document["risk"]),
        shadow_initial_cash=shadow_initial_cash,
    )


def load_account_catalog(config_dir: Path, strategies_dir: Path) -> AccountCatalog:
    accounts = tuple(
        load_account_config(path, strategies_dir)
        for path in sorted(config_dir.glob("*.json"))
    )
    if not accounts:
        raise ValueError("account catalog must contain at least one configuration")
    if sum(config.mode == "live" for config in accounts) > 1:
        raise ValueError("account catalog permits at most one live configuration")
    return AccountCatalog(accounts)
