import json
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import unittest

from ripple import OrderPlan


ROOT = Path(__file__).resolve().parents[1]


class MvpDryCycleTests(unittest.TestCase):
    def test_two_account_lanes_produce_isolated_state(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            base = ["python3.12", "-m", "ripple.mvp", "run-dry-cycle"]
            lanes = {
                "account_A": (
                    ROOT / "config" / "mvp.json",
                    ROOT / "fixtures" / "mvp" / "dry_cycle.json",
                ),
                "account_B": (
                    ROOT / "config" / "mvp-account-b.json",
                    ROOT / "fixtures" / "mvp" / "dry_cycle_account_b.json",
                ),
            }

            plans = {}
            for account_id, (config, fixture) in lanes.items():
                output = root / account_id
                completed = subprocess.run(
                    base + [
                        "--config", str(config),
                        "--fixture", str(fixture),
                        "--output", str(output),
                    ],
                    cwd=ROOT, text=True, capture_output=True, check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                plan_path = output / "plans" / "2026-08-24" / "order_plan.json"
                plans[account_id] = json.loads(plan_path.read_text())
                self.assertEqual(plans[account_id]["account_id"], account_id)
                decision_log = json.loads(
                    (output / "logs" / "decisions.jsonl").read_text()
                )
                execution_log = json.loads(
                    (output / "logs" / "executions.jsonl").read_text()
                )
                self.assertEqual(decision_log["account_id"], account_id)
                self.assertEqual(execution_log["account_id"], account_id)

            self.assertNotEqual(
                plans["account_A"]["order_plan_id"],
                plans["account_B"]["order_plan_id"],
            )
            account_a_fixture = json.loads(lanes["account_A"][1].read_text())
            account_b_fixture = json.loads(lanes["account_B"][1].read_text())
            self.assertEqual(account_a_fixture["snapshot"], account_b_fixture["snapshot"])
            from ripple.mvp import _execute_dry_run, _read_json
            with self.assertRaisesRegex(ValueError, "account_id does not match"):
                _execute_dry_run(
                    _read_json(lanes["account_B"][0]),
                    OrderPlan.from_dict(plans["account_A"]),
                    account_b_fixture["execution_context"],
                    root / "crossed" / "account_B",
                )
            self.assertFalse((root / "crossed").exists())

    def test_cli_produces_one_reviewable_credential_free_cycle(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "account_A"
            command = [
                "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                "--config", str(ROOT / "config" / "mvp.json"),
                "--fixture", str(ROOT / "fixtures" / "mvp" / "dry_cycle.json"),
                "--output", str(output),
            ]

            completed = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("dry-run cycle complete", completed.stdout)

            plan_path = output / "plans" / "2026-08-24" / "order_plan.json"
            snapshot_path = output / "snapshots" / "2026-08-24" / "decision_snapshot.json"
            execution_path = output / "executions" / "2026-08-25" / "dry_run.json"
            report_path = output / "reports" / "2026-08-25.md"
            decision_log = output / "logs" / "decisions.jsonl"
            execution_log = output / "logs" / "executions.jsonl"
            for path in (
                snapshot_path, plan_path, execution_path, report_path,
                decision_log, execution_log,
            ):
                self.assertTrue(path.is_file(), path)

            plan = json.loads(plan_path.read_text())
            OrderPlan.from_dict(plan)
            execution = json.loads(execution_path.read_text())
            self.assertEqual(execution["mode"], "dry_run")
            self.assertEqual(execution["status"], "allowed")
            self.assertEqual(execution["actions"][0]["broker_order"]["symbol"], "AAPL")
            self.assertEqual(len(decision_log.read_text().splitlines()), 1)
            self.assertEqual(len(execution_log.read_text().splitlines()), 1)
            self.assertEqual(
                json.loads(decision_log.read_text())["kind"], "decision_published",
            )
            self.assertEqual(
                json.loads(execution_log.read_text())["kind"], "dry_run_completed",
            )
            self.assertIn("DRY RUN", report_path.read_text())

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
            self.assertEqual(len(decision_log.read_text().splitlines()), 1)
            self.assertEqual(len(execution_log.read_text().splitlines()), 1)

    def test_hosted_routine_commands_handoff_through_published_plan(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "account_A"
            decision_input = root / "decision.json"
            context_input = root / "execution_context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            from ripple.mvp import execute_dry_run, publish_decision
            config = ROOT / "config" / "mvp.json"

            publish_decision(
                config, decision_input, output,
                now=datetime.fromisoformat(fixture["decision"]["decision_time"]),
            )

            plan_path = output / "plans" / "2026-08-24" / "order_plan.json"
            execute_dry_run(
                config, plan_path, context_input, output,
                now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
            )
            self.assertTrue((output / "executions" / "2026-08-25" / "dry_run.json").is_file())

    def test_new_york_trading_date_is_used_for_utc_documents(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        fixture["snapshot"]["as_of"] = "2026-08-25T00:55:00Z"
        fixture["decision"]["decision_time"] = "2026-08-25T01:05:00Z"
        fixture["execution_context"]["as_of"] = "2026-08-25T13:35:00Z"
        fixture["execution_context"]["quotes"]["AAPL"]["as_of"] = (
            "2026-08-25T13:34:00Z"
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "account_A"
            fixture_path = Path(temporary_directory) / "fixture.json"
            fixture_path.write_text(json.dumps(fixture))
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                    "--config", str(ROOT / "config" / "mvp.json"),
                    "--fixture", str(fixture_path),
                    "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(
                (output / "plans" / "2026-08-24" / "order_plan.json").is_file()
            )
            self.assertTrue(
                (output / "executions" / "2026-08-25" / "dry_run.json").is_file()
            )

    def test_disabled_mode_and_same_day_execution_fail_closed(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = json.loads((ROOT / "config" / "mvp.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "account_A"
            decision_input = root / "decision.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "account_baseline": fixture["account_baseline"],
                "decision": fixture["decision"],
            }))
            disabled_config = root / "disabled.json"
            config["execution"]["mode"] = "disabled"
            disabled_config.write_text(json.dumps(config))
            base = ["python3.12", "-m", "ripple.mvp"]

            disabled = subprocess.run(
                base + [
                    "run-dry-cycle", "--config", str(disabled_config),
                    "--fixture", str(ROOT / "fixtures" / "mvp" / "dry_cycle.json"),
                    "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(disabled.returncode, 0)
            self.assertIn("disabled", disabled.stderr)
            self.assertFalse(output.exists())

            config["execution"]["mode"] = "dry_run"
            enabled_config = root / "enabled.json"
            enabled_config.write_text(json.dumps(config))
            from ripple.mvp import _publish_decision, _read_json
            plan = _publish_decision(
                _read_json(enabled_config), _read_json(decision_input), output,
            )
            context = fixture["execution_context"]
            context["as_of"] = "2026-08-24T22:00:00-04:00"
            context["quotes"]["AAPL"]["as_of"] = "2026-08-24T21:59:00-04:00"
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context))
            from ripple.mvp import _execute_dry_run
            with self.assertRaisesRegex(ValueError, "next weekday"):
                _execute_dry_run(
                    _read_json(enabled_config), plan, _read_json(context_path), output,
                )

    def test_state_root_must_match_configured_account(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            wrong_root = Path(temporary_directory) / "account_B"
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "run-dry-cycle",
                    "--config", str(ROOT / "config" / "mvp.json"),
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
        config = json.loads((ROOT / "config" / "mvp.json").read_text())
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
                            Path(temporary_directory) / "account_A",
                        )

    def test_tier_two_drawdown_latch_persists_until_human_reset(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = json.loads((ROOT / "config" / "mvp.json").read_text())
        from ripple.mvp import _build_plan, _execute_dry_run

        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "account_A"
            first_plan = _build_plan(
                {
                    "snapshot": fixture["snapshot"],
                    "account_baseline": fixture["account_baseline"],
                    "decision": fixture["decision"],
                },
                config,
            )
            first_context = json.loads(json.dumps(fixture["execution_context"]))
            first_context["account"]["equity"] = "850"
            first_result = _execute_dry_run(config, first_plan, first_context, output)
            self.assertTrue(first_result["manual_restart_required"])
            self.assertTrue((output / "risk" / "drawdown_tier2.lock.json").is_file())

            second_input = {
                "snapshot": json.loads(json.dumps(fixture["snapshot"])),
                "account_baseline": json.loads(json.dumps(fixture["account_baseline"])),
                "decision": json.loads(json.dumps(fixture["decision"])),
            }
            second_input["snapshot"]["as_of"] = "2026-08-25T20:55:00-04:00"
            second_input["decision"]["decision_time"] = "2026-08-25T21:00:00-04:00"
            second_plan = _build_plan(second_input, config)
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
