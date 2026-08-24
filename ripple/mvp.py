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

from .decision_snapshot import DecisionSnapshot
from .order_plan import OrderPlan
from .risk import evaluate_plan


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


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as output:
        output.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


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


def _validate_state_root(output: Path, config: Mapping[str, Any]) -> None:
    account_id = config.get("account_id")
    if not isinstance(account_id, str) or output.name != account_id:
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
    config: Mapping[str, Any],
    *,
    enforce_schedule: bool = True,
) -> OrderPlan:
    if set(config) != {"account_id", "execution", "universe", "risk"}:
        raise ValueError("configuration fields do not match the schema")
    mode = config["execution"].get("mode") if isinstance(config["execution"], Mapping) else None
    if mode == "disabled":
        raise ValueError("decision publishing is disabled")
    if mode not in {"dry_run", "live"}:
        raise ValueError("execution.mode is not supported")
    if set(decision_input) != _DECISION_INPUT_FIELDS:
        raise ValueError("decision input fields do not match the schema")
    snapshot = DecisionSnapshot.from_dict(decision_input["snapshot"])
    decision = decision_input["decision"]
    if not isinstance(decision, Mapping) or set(decision) != _DECISION_FIELDS:
        raise ValueError("decision fields do not match the schema")
    if snapshot.universe != tuple(config["universe"]):
        raise ValueError("snapshot universe does not match configuration")
    account_baseline = decision_input["account_baseline"]
    if not isinstance(account_baseline, Mapping):
        raise ValueError("decision input must include account_baseline")
    if not isinstance(decision["target_portfolio"], Mapping):
        raise ValueError("target_portfolio must be an object")
    target_symbols = set(decision["target_portfolio"]) - {"cash"}
    if not target_symbols <= set(snapshot.universe):
        raise ValueError("target portfolio contains a symbol outside the snapshot universe")
    max_position = Decimal(config["risk"]["max_position_pct"])
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
    plan_id = str(uuid5(NAMESPACE_URL, f"ripple:{config['account_id']}:{_date(decision_time)}"))
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
        "account_id": config["account_id"],
        "model_config_version": decision["model_config_version"],
        "decision_snapshot_id": snapshot.snapshot_id,
        "market_snapshot_as_of": snapshot.as_of,
        "account_baseline": account_baseline,
        "target_portfolio": decision["target_portfolio"],
        "orders": orders,
    })


def _publish_decision(
    config: Mapping[str, Any],
    decision_input: Mapping[str, Any],
    output: Path,
    *,
    run_kind: str = "fixture",
) -> OrderPlan:
    _validate_state_root(output, config)
    plan = _build_plan(
        decision_input, config, enforce_schedule=run_kind != "manual",
    )
    decision_date = _date(plan.decision_time)
    _write_new_json(
        output / "snapshots" / decision_date / "decision_snapshot.json",
        decision_input["snapshot"],
    )
    _write_new_json(
        output / "plans" / decision_date / "order_plan.json",
        plan.to_dict(),
    )
    _append_jsonl(output / "logs" / "decisions.jsonl", {
        "kind": "decision_published",
        "account_id": plan.account_id,
        "order_plan_id": plan.order_plan_id,
        "decision_snapshot_id": plan.decision_snapshot_id,
        "decision_time": plan.decision_time,
        "order_count": len(plan.orders),
        "plan_uri": f"plans/{decision_date}/order_plan.json",
        "run_kind": run_kind,
    })
    return plan


def _write_report(
    path: Path,
    plan: OrderPlan,
    execution_context: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    action_lines = [
        f"- {action['broker_order']['side'].upper()} {action['broker_order']['symbol']} "
        f"{action['actual_sizing']['value']} ({action['reason_code']})"
        if action["allowed"] else
        f"- REJECT {action['order_id']} ({action['reason_code']})"
        for action in result["actions"]
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as report:
        report.write(
            "# Ripple MVP — DRY RUN\n\n"
            f"- Account: `{plan.account_id}`\n"
            f"- Order plan: `{plan.order_plan_id}`\n"
            f"- Decision: `{plan.decision_time}`\n"
            f"- Execution check: `{execution_context['as_of']}`\n"
            f"- Result: **{result['status']}**\n\n"
            "## Proposed actions\n\n"
            + ("\n".join(action_lines) if action_lines else "- No orders")
            + "\n\nNo broker write tool was called.\n"
        )


def _execute_dry_run(
    config: Mapping[str, Any],
    plan: OrderPlan,
    execution_context: Mapping[str, Any],
    output: Path,
    *,
    run_kind: str = "fixture",
) -> dict[str, Any]:
    _validate_state_root(output, config)
    _validate_execution_timing(
        plan.decision_time,
        execution_context["as_of"],
        enforce_schedule=run_kind != "manual",
    )
    execution_date = _date(execution_context["as_of"])
    execution_path = output / "executions" / execution_date / "dry_run.json"
    if execution_path.exists():
        raise FileExistsError(17, "File exists", execution_path)
    latch_path = output / "risk" / "drawdown_tier2.lock.json"
    result = evaluate_plan(
        plan.to_dict(), execution_context, config,
        new_entries_locked=latch_path.is_file(),
    )
    if result["mode"] != "dry_run":
        raise ValueError("execute-dry-run requires execution.mode=dry_run")
    if result["manual_restart_required"] and not latch_path.exists():
        _write_new_json(latch_path, {
            "account_id": plan.account_id,
            "triggered_at": execution_context["as_of"],
            "reason_code": "drawdown_tier2",
        })
    _write_new_json(execution_path, result)
    _append_jsonl(output / "logs" / "executions.jsonl", {
        "kind": "dry_run_completed",
        "account_id": plan.account_id,
        "order_plan_id": plan.order_plan_id,
        "occurred_at": execution_context["as_of"],
        "status": result["status"],
        "action_count": len(result["actions"]),
        "result_uri": f"executions/{execution_date}/dry_run.json",
        "run_kind": run_kind,
    })
    _write_report(
        output / "reports" / f"{execution_date}.md",
        plan,
        execution_context,
        result,
    )
    return result


def publish_decision(
    config_path: Path,
    input_path: Path,
    output: Path,
    *,
    now: datetime | None = None,
    manual: bool = False,
) -> OrderPlan:
    config = _read_json(config_path)
    decision_input = _read_json(input_path)
    decision = decision_input.get("decision")
    if not isinstance(decision, Mapping) or not isinstance(decision.get("decision_time"), str):
        raise ValueError("decision input is missing decision_time")
    if not manual:
        _validate_runtime_clock(
            now or datetime.now(timezone.utc), decision["decision_time"], "decision",
        )
    return _publish_decision(
        config, decision_input, output,
        run_kind="manual" if manual else "scheduled",
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
    config = _read_json(config_path)
    if manual and config.get("execution", {}).get("mode") != "dry_run":
        raise ValueError("manual runs require execution.mode=dry_run")
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


def run_dry_cycle(config_path: Path, fixture_path: Path, output: Path) -> dict[str, Any]:
    config = _read_json(config_path)
    fixture = _read_json(fixture_path)
    if set(fixture) != _CYCLE_FIELDS:
        raise ValueError("MVP fixture fields do not match the schema")
    decision_input = {field: fixture[field] for field in _DECISION_INPUT_FIELDS}
    plan = _publish_decision(config, decision_input, output)
    return _execute_dry_run(config, plan, fixture["execution_context"], output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ripple fixture-backed MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish = subparsers.add_parser("publish-decision")
    publish.add_argument("--config", type=Path, required=True)
    publish.add_argument("--input", type=Path, required=True)
    publish.add_argument("--output", type=Path, required=True)
    publish.add_argument("--manual-run", action="store_true")

    execute = subparsers.add_parser("execute-dry-run")
    execute.add_argument("--config", type=Path, required=True)
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--context", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--manual-run", action="store_true")

    cycle = subparsers.add_parser("run-dry-cycle")
    cycle.add_argument("--config", type=Path, required=True)
    cycle.add_argument("--fixture", type=Path, required=True)
    cycle.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "publish-decision":
            plan = publish_decision(
                args.config, args.input, args.output,
                manual=args.manual_run,
            )
            print(f"decision published: {plan.order_plan_id}")
            return 0
        if args.command == "execute-dry-run":
            result = execute_dry_run(
                args.config, args.plan, args.context, args.output,
                manual=args.manual_run,
            )
        else:
            result = run_dry_cycle(args.config, args.fixture, args.output)
    except FileExistsError as error:
        print(f"command failed: output already exists: {error.filename}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError) as error:
        print(f"command failed: {error}", file=sys.stderr)
        return 2
    print(f"dry-run cycle complete: {result['status']} ({len(result['actions'])} action(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
