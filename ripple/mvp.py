"""Commands for the fixture-backed Decision and Execution Routines."""

import argparse
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from .account_config import AccountConfig, load_account_catalog, load_account_config
from .decision_snapshot import DecisionSnapshot
from .order_plan import OrderPlan
from .risk import evaluate_plan
from .shadow import simulate_shadow_fills


_CYCLE_FIELDS = {"snapshot", "account_baseline", "decision", "execution_context"}
_DECISION_INPUT_FIELDS = {"snapshot", "account_baseline", "decision"}
_DECISION_FIELDS = {
    "decision_time", "model_config_version", "target_portfolio", "orders",
}
_NEW_YORK = ZoneInfo("America/New_York")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


def _date(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return parsed.astimezone(_NEW_YORK).date().isoformat()


def _new_york_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return parsed.astimezone(_NEW_YORK)


def _next_weekday(value: date) -> date:
    candidate = value
    while True:
        candidate = candidate.fromordinal(candidate.toordinal() + 1)
        if candidate.weekday() < 5:
            return candidate


def _trade_date(decision_time: str) -> str:
    return _next_weekday(_new_york_time(decision_time).date()).isoformat()


def _published_cycle_root(output: Path, plan: OrderPlan) -> Path:
    if plan.decision_run_kind == "backfill":
        raise ValueError("Execution does not accept historical Decision backfills")
    cycle_root = output / "trading_days" / _trade_date(plan.decision_time)
    snapshot_path = cycle_root / "decision_snapshot.json"
    plan_path = cycle_root / "order_plan.json"
    if not snapshot_path.is_file() or not plan_path.is_file():
        raise ValueError("execution requires the published decision cycle")
    snapshot = DecisionSnapshot.from_dict(_read_json(snapshot_path))
    if snapshot.snapshot_id != plan.decision_snapshot_id:
        raise ValueError("published decision snapshot does not match the order plan")
    if _read_json(plan_path) != plan.to_dict():
        raise ValueError("published order plan does not match the execution input")
    return cycle_root


def _validate_state_root(output: Path, config: AccountConfig) -> None:
    if output.name != config.account_id:
        raise ValueError("state root must end with the configured account_id")


def _validate_decision_timing(
    decision_time: str,
    snapshot_time: str,
    *,
    enforce_schedule: bool = True,
) -> None:
    decision_at = _new_york_time(decision_time)
    snapshot_at = _new_york_time(snapshot_time)
    if enforce_schedule and (
        decision_at.weekday() not in {0, 1, 2, 3, 6}
        or not time(20, 55) <= decision_at.time() <= time(21, 15)
    ):
        raise ValueError("decision time is outside the allowed America/New_York window")
    if enforce_schedule and snapshot_at.date() != decision_at.date():
        raise ValueError("snapshot and decision must use the same New York date")


def _validate_execution_timing(
    decision_time: str,
    execution_time: str,
    *,
    enforce_schedule: bool = True,
) -> None:
    decision_at = _new_york_time(decision_time)
    execution_at = _new_york_time(execution_time)
    if not enforce_schedule:
        if execution_at <= decision_at:
            raise ValueError("manual execution must occur after the decision")
        return
    if execution_at.date() != _next_weekday(decision_at.date()):
        raise ValueError("execution must occur on the next weekday after the decision")
    if not time(9, 30) <= execution_at.time() <= time(9, 50):
        raise ValueError("execution time is outside the allowed America/New_York window")


def _validate_runtime_clock(now: datetime, expected_time: str, phase: str) -> None:
    if now.utcoffset() is None:
        raise ValueError("runtime clock must include a timezone offset")
    actual = now.astimezone(_NEW_YORK)
    expected = _new_york_time(expected_time)
    window = (time(20, 55), time(21, 15)) if phase == "decision" else (
        time(9, 30), time(9, 50)
    )
    allowed_days = {0, 1, 2, 3, 6} if phase == "decision" else {0, 1, 2, 3, 4}
    if actual.weekday() not in allowed_days or actual.date() != expected.date():
        raise ValueError(f"{phase} runtime date does not match America/New_York now")
    if not window[0] <= actual.time() <= window[1]:
        raise ValueError(f"{phase} runtime is outside the America/New_York window")


def _build_plan(
    decision_input: Mapping[str, Any],
    config: AccountConfig,
    *,
    enforce_schedule: bool = True,
    decision_run_kind: str = "fixture",
) -> OrderPlan:
    if set(decision_input) != _DECISION_INPUT_FIELDS:
        raise ValueError("decision input fields do not match the schema")
    snapshot = DecisionSnapshot.from_dict(decision_input["snapshot"])
    decision = decision_input["decision"]
    if not isinstance(decision, Mapping) or set(decision) != _DECISION_FIELDS:
        raise ValueError("decision fields do not match the schema")
    if snapshot.universe != config.universe:
        raise ValueError("snapshot universe does not match configuration")
    account_baseline = decision_input["account_baseline"]
    if not isinstance(account_baseline, Mapping):
        raise ValueError("decision input must include account_baseline")
    if not isinstance(decision["target_portfolio"], Mapping):
        raise ValueError("target_portfolio must be an object")
    target_symbols = set(decision["target_portfolio"]) - {"cash"}
    if not target_symbols <= set(snapshot.universe):
        raise ValueError("target portfolio contains a symbol outside the snapshot universe")
    max_position = Decimal(config.risk["max_position_pct"])
    if any(
        Decimal(value) > max_position
        for symbol, value in decision["target_portfolio"].items()
        if symbol != "cash"
    ):
        raise ValueError("target portfolio exceeds max_position_pct")
    if not isinstance(decision["orders"], list):
        raise ValueError("decision orders must be a list")

    decision_time = decision["decision_time"]
    _validate_decision_timing(
        decision_time, snapshot.as_of, enforce_schedule=enforce_schedule,
    )
    plan_id = str(uuid5(NAMESPACE_URL, f"ripple:{config.account_id}:{_date(decision_time)}"))
    orders = []
    for index, proposed_order in enumerate(decision["orders"]):
        if not isinstance(proposed_order, Mapping) or "order_id" in proposed_order:
            raise ValueError("decision orders must be objects without order_id")
        order = dict(proposed_order)
        order["order_id"] = str(uuid5(
            NAMESPACE_URL,
            f"{plan_id}:{index}:{order.get('symbol')}:{order.get('side')}",
        ))
        orders.append(order)
    return OrderPlan.from_dict({
        "order_plan_id": plan_id,
        "decision_time": decision_time,
        "account_id": config.account_id,
        "strategy_id": config.strategy_id,
        "model_config_version": decision["model_config_version"],
        "decision_snapshot_id": snapshot.snapshot_id,
        "market_snapshot_as_of": snapshot.as_of,
        "decision_run_kind": decision_run_kind,
        "account_baseline": account_baseline,
        "target_portfolio": decision["target_portfolio"],
        "orders": orders,
    })


def _publish_decision(
    config: AccountConfig,
    decision_input: Mapping[str, Any],
    output: Path,
    *,
    run_kind: str = "fixture",
) -> OrderPlan:
    _validate_state_root(output, config)
    plan = _build_plan(
        decision_input,
        config,
        enforce_schedule=run_kind != "manual",
        decision_run_kind=run_kind,
    )
    trade_date = _trade_date(plan.decision_time)
    cycle_root = output / "trading_days" / trade_date
    _write_new_json(
        cycle_root / "decision_snapshot.json",
        decision_input["snapshot"],
    )
    _write_new_json(
        cycle_root / "order_plan.json",
        plan.to_dict(),
    )
    return plan


def _write_report(
    path: Path,
    plan: OrderPlan,
    execution_context: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    title: str,
) -> None:
    action_lines = []
    for action in result["actions"]:
        desired_price = action.get("desired_buy_price")
        buy_reason = action.get("buy_reason")
        if action["allowed"]:
            line = (
                f"- {action['side']} {action['symbol']} "
                f"{action['actual_sizing']['value']} ({action['reason_code']})"
            )
        else:
            abort = action.get("abort_reason") or {}
            line = (
                f"- REJECT {action['side']} {action['symbol']}: "
                f"{abort.get('message', action['reason_code'])} "
                f"(`{action['reason_code']}`)"
            )
        if desired_price is not None:
            line += f"\n  - Desired buy price: `${desired_price}`"
        if buy_reason is not None:
            line += f"\n  - Buy reason: {buy_reason}"
        action_lines.append(line)
    fill_lines = []
    for fill in result.get("shadow_fills", []):
        fill_lines.append(
            f"- {fill['status'].upper()} {fill['side']} {fill['symbol']} "
            f"{fill['quantity']} at `${fill['price']}` (`{fill['reason_code']}`)"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as report:
        report.write(
            f"# Ripple — {title}\n\n"
            f"- Account: `{plan.account_id}`\n"
            f"- Strategy: `{plan.strategy_id}`\n"
            f"- Order plan: `{plan.order_plan_id}`\n"
            f"- Decision: `{plan.decision_time}`\n"
            f"- Decision run: `{plan.decision_run_kind or 'legacy'}`\n"
            f"- Execution run: `{result['execution_run_kind']}`\n"
            f"- Execution check: `{execution_context['as_of']}`\n"
            f"- Result: **{result['status']}**\n\n"
            "## Proposed actions\n\n"
            + ("\n".join(action_lines) if action_lines else "- No orders")
            + (
                "\n\n## Shadow fill attempts\n\n" + "\n".join(fill_lines)
                if fill_lines else ""
            )
            + "\n\nNo broker write tool was called.\n"
        )


def _execute_dry_run(
    config: AccountConfig,
    plan: OrderPlan,
    execution_context: Mapping[str, Any],
    output: Path,
    *,
    run_kind: str = "fixture",
) -> dict[str, Any]:
    _validate_state_root(output, config)
    if config.mode != "dry_run":
        raise ValueError("execute-dry-run requires execution.mode=dry_run")
    _validate_execution_timing(
        plan.decision_time,
        execution_context["as_of"],
        enforce_schedule=run_kind != "manual",
    )
    if plan.account_id != config.account_id:
        raise ValueError("plan account_id does not match configured account_id")
    cycle_root = _published_cycle_root(output, plan)
    execution_path = cycle_root / "execution.json"
    if execution_path.exists():
        raise FileExistsError(17, "File exists", execution_path)
    latch_path = output / "active_risk_lock.json"
    result = {
        **evaluate_plan(
            plan.to_dict(), execution_context, config.risk_rules(),
            new_entries_locked=latch_path.is_file(),
        ),
        "execution_run_kind": run_kind,
    }
    if result["manual_restart_required"] and not latch_path.exists():
        _write_new_json(latch_path, {
            "account_id": plan.account_id,
            "triggered_at": execution_context["as_of"],
            "reason_code": "drawdown_tier2",
        })
    _write_new_json(execution_path, result)
    _write_report(
        cycle_root / "report.md",
        plan,
        execution_context,
        result,
        title="DRY RUN",
    )
    return result


def _execute_shadow(
    config: AccountConfig,
    plan: OrderPlan,
    execution_context: Mapping[str, Any],
    output: Path,
    *,
    run_kind: str = "fixture",
) -> dict[str, Any]:
    _validate_state_root(output, config)
    if config.mode != "shadow":
        raise ValueError("execute-shadow requires execution.mode=shadow")
    _validate_execution_timing(
        plan.decision_time,
        execution_context["as_of"],
        enforce_schedule=run_kind != "manual",
    )
    if plan.account_id != config.account_id:
        raise ValueError("plan account_id does not match configured account_id")
    cycle_root = _published_cycle_root(output, plan)
    execution_path = cycle_root / "execution.json"
    if execution_path.exists():
        raise FileExistsError(17, "File exists", execution_path)
    latch_path = output / "active_risk_lock.json"
    risk_result = evaluate_plan(
        plan.to_dict(), execution_context, config.risk_rules(),
        new_entries_locked=latch_path.is_file(),
    )
    result = {
        **risk_result,
        **simulate_shadow_fills(risk_result, execution_context),
        "execution_run_kind": run_kind,
    }
    if result["manual_restart_required"] and not latch_path.exists():
        _write_new_json(latch_path, {
            "account_id": plan.account_id,
            "triggered_at": execution_context["as_of"],
            "reason_code": "drawdown_tier2",
        })
    _write_new_json(execution_path, result)
    _write_report(
        cycle_root / "report.md",
        plan,
        execution_context,
        result,
        title="SHADOW EXECUTION",
    )
    return result


def publish_decision(
    config_path: Path,
    input_path: Path,
    output: Path,
    *,
    now: datetime | None = None,
    manual: bool = False,
    historical_backfill: bool = False,
) -> OrderPlan:
    config = load_account_config(config_path)
    decision_input = _read_json(input_path)
    decision = decision_input.get("decision")
    if not isinstance(decision, Mapping) or not isinstance(decision.get("decision_time"), str):
        raise ValueError("decision input is missing decision_time")
    if manual and historical_backfill:
        raise ValueError("manual and historical backfill modes are mutually exclusive")
    if historical_backfill and config.mode not in {"live", "shadow"}:
        raise ValueError("historical Decision backfill requires live or shadow mode")
    if not manual and not historical_backfill and config.mode == "dry_run":
        raise ValueError("dry_run accounts are excluded from scheduled Decision runs")
    runtime_now = now or datetime.now(timezone.utc)
    if historical_backfill:
        if runtime_now.utcoffset() is None:
            raise ValueError("runtime clock must include a timezone offset")
        if _new_york_time(decision["decision_time"]) >= runtime_now.astimezone(_NEW_YORK):
            raise ValueError("historical Decision backfill must use a past decision_time")
    elif not manual:
        _validate_runtime_clock(
            runtime_now, decision["decision_time"], "decision",
        )
    return _publish_decision(
        config, decision_input, output,
        run_kind=(
            "manual" if manual else "backfill" if historical_backfill else "scheduled"
        ),
    )


def execute_dry_run(
    config_path: Path,
    plan_path: Path,
    context_path: Path,
    output: Path,
    *,
    now: datetime | None = None,
    manual: bool = False,
) -> dict[str, Any]:
    config = load_account_config(config_path)
    execution_context = _read_json(context_path)
    execution_time = execution_context.get("as_of")
    if not isinstance(execution_time, str):
        raise ValueError("execution context is missing as_of")
    if not manual:
        _validate_runtime_clock(
            now or datetime.now(timezone.utc), execution_time, "execution",
        )
    return _execute_dry_run(
        config,
        OrderPlan.from_dict(_read_json(plan_path)),
        execution_context,
        output,
        run_kind="manual" if manual else "scheduled",
    )


def execute_shadow(
    config_path: Path,
    plan_path: Path,
    context_path: Path,
    output: Path,
    *,
    now: datetime | None = None,
    manual: bool = False,
) -> dict[str, Any]:
    config = load_account_config(config_path)
    execution_context = _read_json(context_path)
    execution_time = execution_context.get("as_of")
    if not isinstance(execution_time, str):
        raise ValueError("execution context is missing as_of")
    if not manual:
        _validate_runtime_clock(
            now or datetime.now(timezone.utc), execution_time, "execution",
        )
    return _execute_shadow(
        config,
        OrderPlan.from_dict(_read_json(plan_path)),
        execution_context,
        output,
        run_kind="manual" if manual else "scheduled",
    )


def run_dry_cycle(config_path: Path, fixture_path: Path, output: Path) -> dict[str, Any]:
    config = load_account_config(config_path)
    if config.mode != "dry_run":
        raise ValueError("run-dry-cycle requires execution.mode=dry_run")
    fixture = _read_json(fixture_path)
    if set(fixture) != _CYCLE_FIELDS:
        raise ValueError("MVP fixture fields do not match the schema")
    decision_input = {field: fixture[field] for field in _DECISION_INPUT_FIELDS}
    plan = _publish_decision(config, decision_input, output)
    return _execute_dry_run(config, plan, fixture["execution_context"], output)


def run_shadow_cycle(config_path: Path, fixture_path: Path, output: Path) -> dict[str, Any]:
    config = load_account_config(config_path)
    if config.mode != "shadow":
        raise ValueError("run-shadow-cycle requires execution.mode=shadow")
    fixture = _read_json(fixture_path)
    if set(fixture) != _CYCLE_FIELDS:
        raise ValueError("MVP fixture fields do not match the schema")
    decision_input = {field: fixture[field] for field in _DECISION_INPUT_FIELDS}
    plan = _publish_decision(config, decision_input, output)
    return _execute_shadow(config, plan, fixture["execution_context"], output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ripple fixture-backed MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish = subparsers.add_parser("publish-decision")
    publish.add_argument("--config", type=Path, required=True)
    publish.add_argument("--input", type=Path, required=True)
    publish.add_argument("--output", type=Path, required=True)
    publish_mode = publish.add_mutually_exclusive_group()
    publish_mode.add_argument("--manual-run", action="store_true")
    publish_mode.add_argument("--historical-backfill", action="store_true")

    execute = subparsers.add_parser("execute-dry-run")
    execute.add_argument("--config", type=Path, required=True)
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--context", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--manual-run", action="store_true")

    shadow = subparsers.add_parser("execute-shadow")
    shadow.add_argument("--config", type=Path, required=True)
    shadow.add_argument("--plan", type=Path, required=True)
    shadow.add_argument("--context", type=Path, required=True)
    shadow.add_argument("--output", type=Path, required=True)
    shadow.add_argument("--manual-run", action="store_true")

    cycle = subparsers.add_parser("run-dry-cycle")
    cycle.add_argument("--config", type=Path, required=True)
    cycle.add_argument("--fixture", type=Path, required=True)
    cycle.add_argument("--output", type=Path, required=True)

    shadow_cycle = subparsers.add_parser("run-shadow-cycle")
    shadow_cycle.add_argument("--config", type=Path, required=True)
    shadow_cycle.add_argument("--fixture", type=Path, required=True)
    shadow_cycle.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate-configs")
    validate.add_argument("--config-dir", type=Path, default=Path("config"))
    validate.add_argument("--strategies-dir", type=Path, default=Path("strategies"))

    listing = subparsers.add_parser("list-accounts")
    listing.add_argument("--config-dir", type=Path, default=Path("config"))
    listing.add_argument("--strategies-dir", type=Path, default=Path("strategies"))
    listing.add_argument("--mode", choices=("live", "shadow", "dry_run"), required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command in {"validate-configs", "list-accounts"}:
            catalog = load_account_catalog(args.config_dir, args.strategies_dir)
            if args.command == "validate-configs":
                print(f"account catalog valid: {len(catalog.accounts)} account(s)")
            else:
                for config in catalog.for_mode(args.mode):
                    print(config.account_id)
            return 0
        if args.command == "publish-decision":
            plan = publish_decision(
                args.config, args.input, args.output,
                manual=args.manual_run,
                historical_backfill=args.historical_backfill,
            )
            print(f"decision published: {plan.order_plan_id}")
            return 0
        if args.command == "execute-dry-run":
            result = execute_dry_run(
                args.config, args.plan, args.context, args.output,
                manual=args.manual_run,
            )
        elif args.command == "execute-shadow":
            result = execute_shadow(
                args.config, args.plan, args.context, args.output,
                manual=args.manual_run,
            )
        elif args.command == "run-shadow-cycle":
            result = run_shadow_cycle(args.config, args.fixture, args.output)
        else:
            result = run_dry_cycle(args.config, args.fixture, args.output)
    except FileExistsError as error:
        print(f"command failed: output already exists: {error.filename}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError) as error:
        print(f"command failed: {error}", file=sys.stderr)
        return 2
    print(
        f"{result['mode']} cycle complete: "
        f"{result['status']} ({len(result['actions'])} action(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
