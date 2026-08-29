import contextlib
import io
import json
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import unittest

from ripple import OrderPlan
from ripple.account_config import load_account_config


ROOT = Path(__file__).resolve().parents[1]


def _write_dry_run_config(root: Path) -> Path:
    config = json.loads((ROOT / "config" / "account_a.json").read_text())
    config["execution"]["mode"] = "dry_run"
    config_path = root / "account_a.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config))
    return config_path


class MvpDryCycleTests(unittest.TestCase):
    def test_published_limits_use_broker_valid_directional_cent_prices(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = load_account_config(ROOT / "config" / "account_a.json")
        from ripple.mvp import _build_plan

        buy_input = {
            "snapshot": fixture["snapshot"],
            "account_baseline": fixture["account_baseline"],
            "decision": json.loads(json.dumps(fixture["decision"])),
        }
        buy_input["decision"]["orders"][0].update({
            "reference_price_at_decision": "356.5",
            "limit_price": "358.2825",
            "price_tolerance_pct": "0.005",
        })
        self.assertEqual(
            _build_plan(buy_input, config).orders[0]["limit_price"],
            "358.28",
        )

        sell_input = json.loads(json.dumps(buy_input))
        sell_order = sell_input["decision"]["orders"][0]
        sell_order["side"] = "SELL"
        sell_order["limit_price"] = "354.7175"
        sell_order.pop("buy_reason")
        self.assertEqual(
            _build_plan(sell_input, config).orders[0]["limit_price"],
            "354.72",
        )

    def test_manual_decision_can_freeze_an_explicit_same_day_trade_date(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        fixture["snapshot"]["as_of"] = "2026-08-27T01:15:00-04:00"
        fixture["decision"]["decision_time"] = "2026-08-27T01:16:00-04:00"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "decision.json"
            input_path.write_text(json.dumps({
                key: fixture[key] for key in ("snapshot", "account_baseline", "decision")
            }))
            from ripple.mvp import publish_decision

            plan = publish_decision(
                ROOT / "config" / "account_a.json",
                input_path,
                root / "account_a",
                manual=True,
                trade_date="2026-08-27",
            )

            self.assertEqual(plan.trade_date, "2026-08-27")
            self.assertTrue((
                root / "account_a" / "trading_days" / "2026-08-27" / "order_plan.json"
            ).is_file())

    def test_order_plan_id_is_unique_per_trade_date(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = load_account_config(ROOT / "config" / "account_a.json")
        from ripple.mvp import _build_plan

        manual_input = json.loads(json.dumps({
            key: fixture[key] for key in ("snapshot", "account_baseline", "decision")
        }))
        manual_input["snapshot"]["as_of"] = "2026-08-27T01:15:00-04:00"
        manual_input["decision"]["decision_time"] = "2026-08-27T01:16:00-04:00"
        manual_plan = _build_plan(
            manual_input,
            config,
            enforce_schedule=False,
            decision_run_kind="manual",
            trade_date_override="2026-08-27",
        )

        scheduled_input = json.loads(json.dumps({
            key: fixture[key] for key in ("snapshot", "account_baseline", "decision")
        }))
        scheduled_input["snapshot"]["as_of"] = "2026-08-27T21:00:00-04:00"
        scheduled_input["decision"]["decision_time"] = "2026-08-27T21:00:00-04:00"
        scheduled_plan = _build_plan(
            scheduled_input,
            config,
            decision_run_kind="scheduled",
        )

        self.assertEqual(manual_plan.trade_date, "2026-08-27")
        self.assertEqual(scheduled_plan.trade_date, "2026-08-28")
        self.assertNotEqual(manual_plan.order_plan_id, scheduled_plan.order_plan_id)

    def test_closing_momentum_v1_fixture_uses_shared_unbound_shadow_path(self):
        fixture_path = ROOT / "fixtures" / "mvp" / "closing_momentum_v1_cycle.json"
        config_path = ROOT / "fixtures" / "mvp" / "closing_momentum_v1_account.json"
        fixture = json.loads(fixture_path.read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "closing_momentum_v1_account"
            from ripple.mvp import run_shadow_cycle

            result = run_shadow_cycle(config_path, fixture_path, output)
            cycle = output / "trading_days" / "2026-08-26"
            plan = json.loads((cycle / "order_plan.json").read_text())
            self.assertEqual(plan["strategy_id"], "closing_momentum_v1")
            self.assertEqual(plan["cycle_profile"], "same_session_close")
            self.assertEqual(plan["target_portfolio"]["AAPL"], "0.08")
            self.assertEqual(plan["orders"][0]["reference_price_at_decision"], "100")
            self.assertEqual(result["strategy_id"], "closing_momentum_v1")
            self.assertEqual(result["shadow_fills"][0]["price"], "100.40")
            self.assertEqual(
                result["shadow_fills"][0]["reason_code"],
                "assumed_same_session_quote_fill",
            )
            bindings = [
                (path.stem, json.loads(path.read_text()))
                for path in (ROOT / "config").glob("*.json")
                if json.loads(path.read_text())["strategy"] == "closing_momentum_v1"
            ]
            self.assertEqual(len(bindings), 1)
            self.assertEqual(bindings[0][0], "account_c")
            self.assertEqual(bindings[0][1]["execution"], {
                "mode": "shadow", "cycle_profile": "same_session_close",
            })

    def test_same_session_shadow_cycle_uses_one_trade_date_and_execution_quote(self):
        fixture_path = ROOT / "fixtures" / "mvp" / "same_session_close_cycle.json"
        config_path = ROOT / "fixtures" / "mvp" / "same_session_close_account.json"
        fixture = json.loads(fixture_path.read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "same_session_close_account"
            from ripple.mvp import run_shadow_cycle

            result = run_shadow_cycle(config_path, fixture_path, output)
            cycle = output / "trading_days" / "2026-08-26"
            plan = json.loads((cycle / "order_plan.json").read_text())
            execution = json.loads((cycle / "execution.json").read_text())
            self.assertEqual(plan["cycle_profile"], "same_session_close")
            self.assertEqual(plan["trade_date"], "2026-08-26")
            self.assertEqual(execution["cycle_profile"], "same_session_close")
            self.assertEqual(execution["trade_date"], "2026-08-26")
            self.assertEqual(plan["strategy_id"], execution["strategy_id"])
            self.assertEqual(result["shadow_fills"][0]["price"], "100.50")
            self.assertEqual(
                result["shadow_fills"][0]["reason_code"],
                "assumed_same_session_quote_fill",
            )
            self.assertLess(fixture["snapshot"]["as_of"], plan["decision_time"])
            self.assertLess(plan["decision_time"], fixture["execution_context"]["as_of"])

    def test_same_session_timing_profile_mismatch_and_backfill_fail_closed(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "same_session_close_cycle.json").read_text()
        )
        config_path = ROOT / "fixtures" / "mvp" / "same_session_close_account.json"
        from ripple.mvp import _validate_execution_timing, publish_decision

        for execution_time in (
            "2026-08-26T14:50:00-04:00",
            "2026-08-27T15:25:00-04:00",
            "2026-08-26T15:41:00-04:00",
        ):
            with self.subTest(execution_time=execution_time), self.assertRaises(ValueError):
                _validate_execution_timing(
                    fixture["decision"]["decision_time"], execution_time,
                    "same_session_close",
                )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            decision_path = root / "decision.json"
            decision_path.write_text(json.dumps({
                key: fixture[key] for key in ("snapshot", "account_baseline", "decision")
            }))
            with self.assertRaisesRegex(ValueError, "backfill"):
                publish_decision(
                    config_path, decision_path, root / "same_session_close_account",
                    historical_backfill=True,
                )

    def test_same_session_scheduled_closed_and_early_close_days_are_no_ops(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "same_session_close_cycle.json").read_text()
        )
        config_path = ROOT / "fixtures" / "mvp" / "same_session_close_account.json"
        from ripple.calendar import NoTradingSession
        from ripple.mvp import publish_decision

        for day in ("2026-08-29", "2026-09-07", "2026-11-27"):
            with self.subTest(day=day), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                decision_input = json.loads(json.dumps({
                    key: fixture[key] for key in ("snapshot", "account_baseline", "decision")
                }))
                decision_input["snapshot"]["as_of"] = f"{day}T14:54:00-04:00"
                decision_input["decision"]["decision_time"] = f"{day}T14:55:00-04:00"
                input_path = root / "decision.json"
                input_path.write_text(json.dumps(decision_input))
                with self.assertRaises(NoTradingSession):
                    publish_decision(
                        config_path, input_path, root / "same_session_close_account",
                        now=datetime.fromisoformat(f"{day}T14:55:00-04:00"),
                    )
                self.assertFalse((root / "same_session_close_account").exists())

    def test_same_session_manual_bypasses_window_but_not_trade_date_or_profile(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "same_session_close_cycle.json").read_text()
        )
        fixture["snapshot"]["as_of"] = "2026-08-26T12:59:00-04:00"
        fixture["decision"]["decision_time"] = "2026-08-26T13:00:00-04:00"
        fixture["execution_context"]["as_of"] = "2026-08-26T13:05:00-04:00"
        fixture["execution_context"]["quotes"]["AAPL"]["as_of"] = "2026-08-26T13:04:00-04:00"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            decision_path = root / "decision.json"
            context_path = root / "context.json"
            decision_path.write_text(json.dumps({
                key: fixture[key] for key in ("snapshot", "account_baseline", "decision")
            }))
            context_path.write_text(json.dumps(fixture["execution_context"]))
            output = root / "same_session_close_account"
            from ripple.mvp import execute_shadow, publish_decision

            plan = publish_decision(
                ROOT / "fixtures" / "mvp" / "same_session_close_account.json",
                decision_path, output, manual=True,
            )
            plan_path = output / "trading_days" / "2026-08-26" / "order_plan.json"
            result = execute_shadow(
                ROOT / "fixtures" / "mvp" / "same_session_close_account.json",
                plan_path, context_path, output, manual=True,
            )
            self.assertEqual(result["trade_date"], "2026-08-26")
            self.assertEqual(plan.cycle_profile, "same_session_close")

            legacy_config = json.loads(
                (ROOT / "fixtures" / "mvp" / "same_session_close_account.json").read_text()
            )
            legacy_config["execution"].pop("cycle_profile")
            mismatch_path = root / "mismatch" / "same_session_close_account.json"
            mismatch_path.parent.mkdir()
            mismatch_path.write_text(json.dumps(legacy_config))
            with self.assertRaisesRegex(ValueError, "cycle_profile"):
                execute_shadow(mismatch_path, plan_path, context_path, root / "other" / "same_session_close_account", manual=True)

    def test_cycle_artifacts_share_the_target_trade_date_directory(self):
        fixture_path = ROOT / "fixtures" / "mvp" / "dry_cycle.json"
        fixture = json.loads(fixture_path.read_text())
        config = json.loads((ROOT / "config" / "account_a.json").read_text())
        config["execution"]["mode"] = "dry_run"
        config["universe"] = fixture["snapshot"]["universe"]

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_root = root / "config"
            config_root.mkdir()
            config_path = config_root / "account_a.json"
            config_path.write_text(json.dumps(config))
            output = root / "state" / "account_a"

            from ripple.mvp import run_dry_cycle

            run_dry_cycle(config_path, fixture_path, output)

            trade_date_root = output / "trading_days" / "2026-08-25"
            self.assertEqual(
                {path.name for path in trade_date_root.iterdir()},
                {
                    "decision_snapshot.json",
                    "execution.json",
                    "order_plan.json",
                    "report.md",
                },
            )
            self.assertFalse((output / "logs").exists())

    def test_two_account_lanes_produce_isolated_state(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dry_run_config = _write_dry_run_config(root / "config")
            lanes = {
                "account_a": (
                    "run-dry-cycle",
                    dry_run_config,
                    ROOT / "fixtures" / "mvp" / "dry_cycle.json",
                ),
                "account_b": (
                    "run-shadow-cycle",
                    ROOT / "config" / "account_b.json",
                    ROOT / "fixtures" / "mvp" / "dry_cycle_account_b.json",
                ),
            }

            plans = {}
            for account_id, (command, config, fixture) in lanes.items():
                output = root / account_id
                completed = subprocess.run(
                    ["python3.12", "-m", "ripple.mvp", command] + [
                        "--config", str(config),
                        "--fixture", str(fixture),
                        "--output", str(output),
                    ],
                    cwd=ROOT, text=True, capture_output=True, check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                plan_path = output / "trading_days" / "2026-08-25" / "order_plan.json"
                plans[account_id] = json.loads(plan_path.read_text())
                self.assertEqual(plans[account_id]["account_id"], account_id)
                execution = json.loads(
                    (output / "trading_days" / "2026-08-25" / "execution.json").read_text()
                )
                self.assertEqual(execution["account_id"], account_id)
                self.assertFalse((output / "logs").exists())

            self.assertNotEqual(
                plans["account_a"]["order_plan_id"],
                plans["account_b"]["order_plan_id"],
            )
            account_a_fixture = json.loads(lanes["account_a"][2].read_text())
            account_b_fixture = json.loads(lanes["account_b"][2].read_text())
            self.assertEqual(account_a_fixture["snapshot"], account_b_fixture["snapshot"])
            from ripple.mvp import _execute_shadow
            with self.assertRaisesRegex(ValueError, "account_id does not match"):
                _execute_shadow(
                    load_account_config(lanes["account_b"][1]),
                    OrderPlan.from_dict(plans["account_a"]),
                    account_b_fixture["execution_context"],
                    root / "crossed" / "account_b",
                )
            self.assertFalse((root / "crossed").exists())

    def test_cli_produces_one_reviewable_credential_free_cycle(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = _write_dry_run_config(root / "config")
            output = root / "account_a"
            command = [
                "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                "--config", str(config),
                "--fixture", str(ROOT / "fixtures" / "mvp" / "dry_cycle.json"),
                "--output", str(output),
            ]

            completed = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("dry_run cycle complete", completed.stdout)

            plan_path = output / "trading_days" / "2026-08-25" / "order_plan.json"
            snapshot_path = output / "trading_days" / "2026-08-25" / "decision_snapshot.json"
            execution_path = output / "trading_days" / "2026-08-25" / "execution.json"
            report_path = output / "trading_days" / "2026-08-25" / "report.md"
            for path in (snapshot_path, plan_path, execution_path, report_path):
                self.assertTrue(path.is_file(), path)

            plan = json.loads(plan_path.read_text())
            OrderPlan.from_dict(plan)
            self.assertEqual(
                plan["decision_rationale"],
                fixture["decision"]["decision_rationale"],
            )
            execution = json.loads(execution_path.read_text())
            self.assertEqual(execution["mode"], "dry_run")
            self.assertEqual(execution["status"], "allowed")
            self.assertEqual(execution["actions"][0]["broker_order"]["symbol"], "AAPL")
            self.assertEqual(execution["actions"][0]["symbol"], "AAPL")
            self.assertEqual(execution["actions"][0]["side"], "BUY")
            self.assertEqual(execution["actions"][0]["desired_buy_price"], "101.00")
            self.assertIn("Buy reason:", report_path.read_text())
            self.assertIn("DRY RUN", report_path.read_text())
            self.assertFalse((output / "logs").exists())

            all_output = "\n".join(
                path.read_text() for path in output.rglob("*") if path.is_file()
            ).lower()
            for forbidden in ("account_number", "access_token", "refresh_token", "password"):
                self.assertNotIn(forbidden, all_output)

            repeated = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("already exists", repeated.stderr)

    def test_new_decision_requires_a_rationale(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        rationale = fixture["decision"]["decision_rationale"]
        fixture["decision"].pop("decision_rationale")
        config = json.loads((ROOT / "config" / "account_a.json").read_text())
        config["execution"]["mode"] = "live"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = root / "account_a.json"
            input_path = root / "decision.json"
            config_path.write_text(json.dumps(config))
            input_path.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "publish-decision",
                    "--config", str(config_path),
                    "--input", str(input_path),
                    "--output", str(root / "account_a"),
                    "--manual-run",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("decision fields do not match", completed.stderr)

            fixture["decision"]["decision_rationale"] = rationale
            input_path.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "publish-decision",
                    "--config", str(config_path),
                    "--input", str(input_path),
                    "--output", str(root / "account_a"),
                    "--manual-run",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(f"decision rationale: {rationale}", completed.stdout)
            plan = json.loads((
                root / "account_a" / "trading_days" / "2026-08-25"
                / "order_plan.json"
            ).read_text())
            self.assertEqual(plan["decision_rationale"], rationale)

    def test_scheduled_shadow_commands_handoff_through_published_plan(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "dry_cycle_account_b.json").read_text()
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "account_b"
            decision_input = root / "decision.json"
            context_input = root / "execution_context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            from ripple.mvp import execute_shadow, publish_decision
            config = ROOT / "config" / "account_b.json"

            publish_decision(
                config, decision_input, output,
                now=datetime.fromisoformat(fixture["decision"]["decision_time"]),
            )

            plan_path = output / "trading_days" / "2026-08-25" / "order_plan.json"
            execute_shadow(
                config, plan_path, context_input, output,
                now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
            )
            self.assertTrue((output / "trading_days" / "2026-08-25" / "execution.json").is_file())

    def test_sunday_decision_executes_monday(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "dry_cycle_account_b.json").read_text()
        )
        fixture["snapshot"]["as_of"] = "2026-08-23T20:55:00-04:00"
        fixture["decision"]["decision_time"] = "2026-08-23T21:00:00-04:00"
        fixture["execution_context"]["as_of"] = "2026-08-24T09:35:00-04:00"
        for quote in fixture["execution_context"]["quotes"].values():
            quote["as_of"] = "2026-08-24T09:34:00-04:00"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "account_b"
            decision_input = root / "decision.json"
            context_input = root / "context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            from ripple.mvp import execute_shadow, publish_decision

            publish_decision(
                ROOT / "config" / "account_b.json",
                decision_input,
                output,
                now=datetime.fromisoformat(fixture["decision"]["decision_time"]),
            )
            plan_path = output / "trading_days" / "2026-08-24" / "order_plan.json"
            execute_shadow(
                ROOT / "config" / "account_b.json",
                plan_path,
                context_input,
                output,
                now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
            )
            self.assertTrue(
                (output / "trading_days" / "2026-08-24" / "execution.json").is_file()
            )

    def test_friday_and_saturday_decisions_are_rejected(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = load_account_config(ROOT / "config" / "account_a.json")
        from ripple.mvp import _build_plan

        for decision_time in (
            "2026-08-21T21:00:00-04:00",
            "2026-08-22T21:00:00-04:00",
        ):
            decision_input = {
                "snapshot": json.loads(json.dumps(fixture["snapshot"])),
                "account_baseline": fixture["account_baseline"],
                "decision": json.loads(json.dumps(fixture["decision"])),
            }
            decision_input["snapshot"]["as_of"] = decision_time
            decision_input["decision"]["decision_time"] = decision_time
            with self.subTest(decision_time=decision_time):
                with self.assertRaisesRegex(ValueError, "decision time"):
                    _build_plan(decision_input, config)

    def test_manual_dry_run_can_execute_immediately_outside_schedule(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        fixture["snapshot"]["as_of"] = "2026-08-23T23:59:00-04:00"
        fixture["decision"]["decision_time"] = "2026-08-24T00:00:00-04:00"
        fixture["execution_context"]["as_of"] = "2026-08-24T00:05:00-04:00"
        for quote in fixture["execution_context"]["quotes"].values():
            quote["as_of"] = "2026-08-24T00:04:00-04:00"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "account_a"
            decision_input = root / "decision.json"
            context_input = root / "context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            config = _write_dry_run_config(root / "config")
            publish = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "publish-decision",
                    "--config", str(config),
                    "--input", str(decision_input),
                    "--output", str(output),
                    "--manual-run",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(publish.returncode, 0, publish.stderr)
            plan_path = output / "trading_days" / "2026-08-25" / "order_plan.json"
            execute = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "execute-dry-run",
                    "--config", str(config),
                    "--plan", str(plan_path),
                    "--context", str(context_input),
                    "--output", str(output),
                    "--manual-run",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(execute.returncode, 0, execute.stderr)

            self.assertTrue(
                (output / "trading_days" / "2026-08-25" / "execution.json").is_file()
            )
            plan = json.loads(plan_path.read_text())
            execution = json.loads(
                (output / "trading_days" / "2026-08-25" / "execution.json").read_text()
            )
            self.assertEqual(plan["decision_run_kind"], "manual")
            self.assertEqual(execution["execution_run_kind"], "manual")
            report = (output / "trading_days" / "2026-08-25" / "report.md").read_text()
            self.assertIn("Decision run: `manual`", report)
            self.assertIn("Execution run: `manual`", report)

    def test_manual_decision_is_allowed_for_live_mode(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = json.loads((ROOT / "config" / "account_a.json").read_text())
        config["execution"]["mode"] = "live"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = root / "account_a.json"
            input_path = root / "decision.json"
            config_path.write_text(json.dumps(config))
            input_path.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            from ripple.mvp import publish_decision

            plan = publish_decision(
                config_path, input_path, root / "account_a", manual=True,
            )
            self.assertEqual(plan.account_id, "account_a")
            self.assertEqual(plan.decision_run_kind, "manual")
            self.assertTrue(
                (
                    root / "account_a" / "trading_days" / "2026-08-25"
                    / "order_plan.json"
                ).is_file()
            )

    def test_historical_decision_backfill_is_explicit_for_live_and_shadow(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        decision_input = {
            "snapshot": fixture["snapshot"],
            "account_baseline": fixture["account_baseline"],
            "decision": fixture["decision"],
        }

        for mode in ("live", "shadow"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                config = json.loads((ROOT / "config" / "account_a.json").read_text())
                config["execution"]["mode"] = mode
                if mode == "shadow":
                    config["shadow"] = {"initial_cash": "1000"}
                config_path = root / "account_a.json"
                input_path = root / "decision.json"
                config_path.write_text(json.dumps(config))
                input_path.write_text(json.dumps(decision_input))

                from ripple.mvp import publish_decision

                plan = publish_decision(
                    config_path,
                    input_path,
                    root / "account_a",
                    now=datetime.fromisoformat("2026-08-25T12:00:00-04:00"),
                    historical_backfill=True,
                )
                self.assertEqual(plan.decision_run_kind, "backfill")

                if mode == "shadow":
                    context_path = root / "context.json"
                    context_path.write_text(json.dumps(fixture["execution_context"]))
                    from ripple.mvp import execute_shadow

                    result = execute_shadow(
                        config_path,
                        root / "account_a" / "trading_days" / "2026-08-25"
                        / "order_plan.json",
                        context_path,
                        root / "account_a",
                        manual=True,
                    )
                    self.assertEqual(result["execution_run_kind"], "manual")
                    self.assertEqual(result["fill_status"], "filled")

                with self.assertRaises(FileExistsError):
                    publish_decision(
                        config_path,
                        input_path,
                        root / "account_a",
                        now=datetime.fromisoformat("2026-08-25T12:00:00-04:00"),
                        historical_backfill=True,
                    )

    def test_historical_decision_backfill_rejects_unsafe_scope_and_timing(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "decision.json"
            input_path.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            from ripple.mvp import publish_decision

            dry_config = json.loads((ROOT / "config" / "account_a.json").read_text())
            dry_config["execution"]["mode"] = "dry_run"
            dry_config_path = root / "dry" / "account_a.json"
            dry_config_path.parent.mkdir()
            dry_config_path.write_text(json.dumps(dry_config))
            with self.assertRaisesRegex(ValueError, "live or shadow"):
                publish_decision(
                    dry_config_path,
                    input_path,
                    root / "account_a",
                    historical_backfill=True,
                )

            config = json.loads((ROOT / "config" / "account_a.json").read_text())
            config["execution"]["mode"] = "live"
            config_path = root / "live" / "account_a.json"
            config_path.parent.mkdir()
            config_path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "past decision_time"):
                publish_decision(
                    config_path,
                    input_path,
                    root / "future" / "account_a",
                    now=datetime.fromisoformat("2026-08-24T20:00:00-04:00"),
                    historical_backfill=True,
                )
            off_schedule = json.loads(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            off_schedule["snapshot"]["as_of"] = "2026-08-24T19:59:00-04:00"
            off_schedule["decision"]["decision_time"] = "2026-08-24T20:00:00-04:00"
            off_schedule_path = root / "off-schedule.json"
            off_schedule_path.write_text(json.dumps(off_schedule))
            with self.assertRaisesRegex(ValueError, "decision time"):
                publish_decision(
                    config_path,
                    off_schedule_path,
                    root / "off-schedule" / "account_a",
                    now=datetime.fromisoformat("2026-08-25T12:00:00-04:00"),
                    historical_backfill=True,
                )
            with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                publish_decision(
                    config_path,
                    input_path,
                    root / "exclusive" / "account_a",
                    manual=True,
                    historical_backfill=True,
                )

    def test_first_execution_artifact_wins_between_manual_and_scheduled_runs(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_dry_run_config(root / "config")
            output = root / "account_a"
            decision_input = root / "decision.json"
            context_input = root / "context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            from ripple.mvp import execute_dry_run, publish_decision

            publish_decision(
                config_path,
                decision_input,
                output,
                manual=True,
            )
            plan_path = output / "trading_days" / "2026-08-25" / "order_plan.json"
            execute_dry_run(
                config_path, plan_path, context_input, output, manual=True,
            )

            with self.assertRaises(FileExistsError):
                execute_dry_run(
                    config_path,
                    plan_path,
                    context_input,
                    output,
                    now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
                )
            self.assertTrue(
                (output / "trading_days" / "2026-08-25" / "execution.json").is_file()
            )

    def test_execution_requires_the_matching_published_cycle(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_dry_run_config(root / "config")
            output = root / "account_a"
            decision_input = root / "decision.json"
            context_input = root / "context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            foreign_plan = root / "foreign-plan.json"

            from ripple.mvp import execute_dry_run, publish_decision

            publish_decision(
                config_path,
                decision_input,
                output,
                manual=True,
            )
            canonical_plan = output / "trading_days" / "2026-08-25" / "order_plan.json"
            document = json.loads(canonical_plan.read_text())
            document["target_portfolio"] = {"cash": "1"}
            document["orders"] = []
            foreign_plan.write_text(json.dumps(document))

            with self.assertRaisesRegex(ValueError, "published order plan"):
                execute_dry_run(
                    config_path,
                    foreign_plan,
                    context_input,
                    output,
                    manual=True,
                )

    def test_new_york_trading_date_is_used_for_utc_documents(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        fixture["snapshot"]["as_of"] = "2026-08-25T00:55:00Z"
        fixture["decision"]["decision_time"] = "2026-08-25T01:05:00Z"
        fixture["execution_context"]["as_of"] = "2026-08-25T13:35:00Z"
        fixture["execution_context"]["quotes"]["AAPL"]["as_of"] = (
            "2026-08-25T13:34:00Z"
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_dry_run_config(root / "config")
            output = root / "account_a"
            fixture_path = root / "fixture.json"
            fixture_path.write_text(json.dumps(fixture))
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                    "--config", str(config_path),
                    "--fixture", str(fixture_path),
                    "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(
                (output / "trading_days" / "2026-08-25" / "order_plan.json").is_file()
            )
            self.assertTrue(
                (output / "trading_days" / "2026-08-25" / "execution.json").is_file()
            )

    def test_trade_date_is_next_new_york_weekday(self):
        from ripple.mvp import _trade_date

        self.assertEqual(_trade_date("2026-08-24T21:00:00-04:00"), "2026-08-25")
        self.assertEqual(_trade_date("2026-08-23T21:00:00-04:00"), "2026-08-24")
        self.assertEqual(_trade_date("2026-08-25T01:00:00Z"), "2026-08-25")

    def test_scheduled_dry_run_and_same_day_execution_fail_closed(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_dry_run_config(root / "config")
            config = load_account_config(config_path)
            output = root / "account_a"
            decision_input = root / "decision.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            scheduled = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "publish-decision",
                    "--config", str(config_path),
                    "--input", str(decision_input),
                    "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(scheduled.returncode, 0)
            self.assertIn("excluded", scheduled.stderr)
            self.assertFalse(output.exists())

            from ripple.mvp import _publish_decision, _read_json
            plan = _publish_decision(
                config, _read_json(decision_input), output,
            )
            context = fixture["execution_context"]
            context["as_of"] = "2026-08-24T22:00:00-04:00"
            context["quotes"]["AAPL"]["as_of"] = "2026-08-24T21:59:00-04:00"
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context))
            from ripple.mvp import _execute_dry_run
            with self.assertRaisesRegex(ValueError, "next trading day"):
                _execute_dry_run(
                    config, plan, _read_json(context_path), output,
                )

    def test_state_root_must_match_configured_account(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_dry_run_config(root / "config")
            wrong_root = root / "account_b"
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                    "--config", str(config_path),
                    "--fixture", str(ROOT / "fixtures" / "mvp" / "dry_cycle.json"),
                    "--output", str(wrong_root),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("state root", completed.stderr)
            self.assertFalse(wrong_root.exists())

    def test_weekend_delayed_or_out_of_window_execution_is_rejected(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        from ripple.mvp import _build_plan, _execute_dry_run

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = load_account_config(_write_dry_run_config(root / "config"))
            plan = _build_plan(
                {
                    "snapshot": fixture["snapshot"],
                    "account_baseline": fixture["account_baseline"],
                    "decision": fixture["decision"],
                },
                config,
            )
            for execution_time in (
                "2026-08-29T09:35:00-04:00",
                "2026-08-26T09:35:00-04:00",
                "2026-08-25T12:00:00-04:00",
            ):
                context = json.loads(json.dumps(fixture["execution_context"]))
                context["as_of"] = execution_time
                for quote in context["quotes"].values():
                    quote["as_of"] = execution_time
                with self.subTest(execution_time=execution_time):
                    with self.assertRaises(ValueError):
                        _execute_dry_run(
                            config, plan, context,
                            root / "account_a",
                        )

    def test_tier_two_drawdown_latch_persists_until_human_reset(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        from ripple.mvp import _execute_dry_run, _publish_decision

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = load_account_config(_write_dry_run_config(root / "config"))
            output = root / "account_a"
            first_plan = _publish_decision(
                config,
                {
                    "snapshot": fixture["snapshot"],
                    "account_baseline": fixture["account_baseline"],
                    "decision": fixture["decision"],
                },
                output,
            )
            first_context = json.loads(json.dumps(fixture["execution_context"]))
            first_context["account"]["equity"] = "850"
            first_result = _execute_dry_run(config, first_plan, first_context, output)
            self.assertTrue(first_result["manual_restart_required"])
            self.assertTrue((output / "active_risk_lock.json").is_file())

            second_input = {
                "snapshot": json.loads(json.dumps(fixture["snapshot"])),
                "account_baseline": json.loads(json.dumps(fixture["account_baseline"])),
                "decision": json.loads(json.dumps(fixture["decision"])),
            }
            second_input["snapshot"]["as_of"] = "2026-08-25T20:55:00-04:00"
            second_input["decision"]["decision_time"] = "2026-08-25T21:00:00-04:00"
            second_plan = _publish_decision(config, second_input, output)
            second_context = json.loads(json.dumps(fixture["execution_context"]))
            second_context["as_of"] = "2026-08-26T09:35:00-04:00"
            second_context["account"]["equity"] = "1000"
            second_context["quotes"]["AAPL"]["as_of"] = "2026-08-26T09:34:00-04:00"
            second_result = _execute_dry_run(config, second_plan, second_context, output)

            self.assertEqual(
                second_result["actions"][0]["reason_code"],
                "drawdown_restart_required",
            )


if __name__ == "__main__":
    unittest.main()


def _write_shadow_config(root: Path) -> Path:
    config = json.loads((ROOT / "config" / "account_a.json").read_text())
    config["execution"]["mode"] = "shadow"
    config["shadow"] = {"initial_cash": "1000"}
    config_path = root / "account_a.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config))
    return config_path


class TradingCalendarTimingTests(unittest.TestCase):
    """Decision and Execution timing follow the NYSE calendar, not the weekday."""

    def _decision_input(self, decision_time: str) -> dict:
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        decision_input = {
            "snapshot": json.loads(json.dumps(fixture["snapshot"])),
            "account_baseline": fixture["account_baseline"],
            "decision": json.loads(json.dumps(fixture["decision"])),
        }
        decision_input["snapshot"]["as_of"] = decision_time
        decision_input["decision"]["decision_time"] = decision_time
        return decision_input

    def test_decision_the_evening_before_a_holiday_is_rejected(self):
        from ripple.mvp import _build_plan

        config = load_account_config(ROOT / "config" / "account_a.json")
        for decision_time in (
            "2026-11-25T21:00:00-05:00",  # Thanksgiving eve
            "2026-12-24T21:00:00-05:00",  # Christmas eve, holiday falls on Friday
            "2026-09-06T21:00:00-04:00",  # Sunday before Labor Day
        ):
            with self.subTest(decision_time=decision_time):
                with self.assertRaisesRegex(ValueError, "does not precede a New York trading day"):
                    _build_plan(self._decision_input(decision_time), config)

    def test_scheduled_decision_on_a_holiday_eve_publishes_nothing(self):
        from ripple.calendar import NoTradingSession
        from ripple.mvp import publish_decision

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_shadow_config(root / "config")
            input_path = root / "decision.json"
            input_path.write_text(json.dumps(self._decision_input("2026-11-25T21:00:00-05:00")))
            output = root / "state" / "account_a"

            with self.assertRaisesRegex(NoTradingSession, "2026-11-26"):
                publish_decision(
                    config_path, input_path, output,
                    now=datetime.fromisoformat("2026-11-25T21:00:00-05:00"),
                )
            self.assertFalse(output.exists())

    def test_scheduled_execution_on_a_holiday_stops_before_reading_the_plan(self):
        from ripple.calendar import NoTradingSession
        from ripple.mvp import execute_shadow

        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_shadow_config(root / "config")
            context = fixture["execution_context"]
            context["as_of"] = "2026-11-26T09:35:00-05:00"
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context))

            with self.assertRaisesRegex(NoTradingSession, "2026-11-26"):
                execute_shadow(
                    config_path,
                    root / "missing" / "order_plan.json",
                    context_path,
                    root / "state" / "account_a",
                    now=datetime.fromisoformat("2026-11-26T09:35:00-05:00"),
                )

    def test_no_trading_session_is_a_successful_command_no_op(self):
        from unittest import mock

        from ripple.calendar import NoTradingSession
        from ripple.mvp import main

        reported = io.StringIO()
        with mock.patch(
            "ripple.mvp.publish_decision",
            side_effect=NoTradingSession(
                "decision runtime has no New York trading session on 2026-11-26"
            ),
        ), contextlib.redirect_stdout(reported):
            exit_code = main([
                "publish-decision",
                "--config", str(ROOT / "config" / "account_a.json"),
                "--input", str(ROOT / "fixtures" / "mvp" / "dry_cycle.json"),
                "--output", "state/accounts/account_a",
            ])

        self.assertEqual(exit_code, 0)
        self.assertIn("no trading session", reported.getvalue())
        self.assertIn("nothing published or executed", reported.getvalue())

    def test_manual_decision_before_a_holiday_targets_the_next_session(self):
        from ripple.mvp import publish_decision

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = _write_dry_run_config(root / "config")
            input_path = root / "decision.json"
            input_path.write_text(json.dumps(self._decision_input("2026-11-25T21:00:00-05:00")))
            output = root / "state" / "account_a"

            plan = publish_decision(config_path, input_path, output, manual=True)

            self.assertTrue((output / "trading_days" / "2026-11-27" / "order_plan.json").is_file())
            self.assertFalse((output / "trading_days" / "2026-11-26").exists())
            self.assertEqual(plan.decision_run_kind, "manual")
