import json
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import unittest

from ripple import OrderPlan
from ripple.account_config import load_account_config


ROOT = Path(__file__).resolve().parents[1]


class MvpDryCycleTests(unittest.TestCase):
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
            lanes = {
                "account_a": (
                    "run-dry-cycle",
                    ROOT / "config" / "account_a.json",
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
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "account_a"
            command = [
                "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                "--config", str(ROOT / "config" / "account_a.json"),
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
            config = ROOT / "config" / "account_a.json"
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
        config_path = ROOT / "config" / "account_a.json"

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
                ROOT / "config" / "account_a.json",
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
                    ROOT / "config" / "account_a.json",
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
            output = Path(temporary_directory) / "account_a"
            fixture_path = Path(temporary_directory) / "fixture.json"
            fixture_path.write_text(json.dumps(fixture))
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                    "--config", str(ROOT / "config" / "account_a.json"),
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
        config = load_account_config(ROOT / "config" / "account_a.json")
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
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
                    "--config", str(ROOT / "config" / "account_a.json"),
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
            with self.assertRaisesRegex(ValueError, "next weekday"):
                _execute_dry_run(
                    config, plan, _read_json(context_path), output,
                )

    def test_state_root_must_match_configured_account(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            wrong_root = Path(temporary_directory) / "account_b"
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                    "--config", str(ROOT / "config" / "account_a.json"),
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
        config = load_account_config(ROOT / "config" / "account_a.json")
        from ripple.mvp import _build_plan, _execute_dry_run

        plan = _build_plan(
            {
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            },
            config,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
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
                            Path(temporary_directory) / "account_a",
                        )

    def test_tier_two_drawdown_latch_persists_until_human_reset(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = load_account_config(ROOT / "config" / "account_a.json")
        from ripple.mvp import _execute_dry_run, _publish_decision

        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "account_a"
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
