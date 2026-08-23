import json
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
            account_b_fixture = json.loads(lanes["account_B"][1].read_text())
            account_b_context = root / "account_b_context.json"
            account_b_context.write_text(json.dumps(
                account_b_fixture["execution_context"]
            ))
            crossed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "execute-dry-run",
                    "--config", str(lanes["account_B"][0]),
                    "--plan", str(
                        root / "account_A" / "plans" / "2026-08-24" /
                        "order_plan.json"
                    ),
                    "--context", str(account_b_context),
                    "--output", str(root / "crossed"),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(crossed.returncode, 0)
            self.assertIn("account_id does not match", crossed.stderr)
            self.assertFalse((root / "crossed").exists())

    def test_cli_produces_one_reviewable_credential_free_cycle(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
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
            output = root / "state"
            decision_input = root / "decision.json"
            context_input = root / "execution_context.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"],
                "decision": fixture["decision"],
            }))
            context_input.write_text(json.dumps(fixture["execution_context"]))
            base = ["python3.12", "-m", "ripple.mvp"]
            config = str(ROOT / "config" / "mvp.json")

            published = subprocess.run(
                base + [
                    "publish-decision", "--config", config,
                    "--input", str(decision_input), "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(published.returncode, 0, published.stderr)

            plan_path = output / "plans" / "2026-08-24" / "order_plan.json"
            executed = subprocess.run(
                base + [
                    "execute-dry-run", "--config", config,
                    "--plan", str(plan_path), "--context", str(context_input),
                    "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertTrue((output / "executions" / "2026-08-25" / "dry_run.json").is_file())

    def test_disabled_mode_and_same_day_execution_fail_closed(self):
        fixture = json.loads((ROOT / "fixtures" / "mvp" / "dry_cycle.json").read_text())
        config = json.loads((ROOT / "config" / "mvp.json").read_text())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "state"
            decision_input = root / "decision.json"
            decision_input.write_text(json.dumps({
                "snapshot": fixture["snapshot"], "decision": fixture["decision"],
            }))
            disabled_config = root / "disabled.json"
            config["execution"]["mode"] = "disabled"
            disabled_config.write_text(json.dumps(config))
            base = ["python3.12", "-m", "ripple.mvp"]

            disabled = subprocess.run(
                base + [
                    "publish-decision", "--config", str(disabled_config),
                    "--input", str(decision_input), "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(disabled.returncode, 0)
            self.assertIn("disabled", disabled.stderr)
            self.assertFalse(output.exists())

            config["execution"]["mode"] = "dry_run"
            enabled_config = root / "enabled.json"
            enabled_config.write_text(json.dumps(config))
            published = subprocess.run(
                base + [
                    "publish-decision", "--config", str(enabled_config),
                    "--input", str(decision_input), "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(published.returncode, 0, published.stderr)
            context = fixture["execution_context"]
            context["as_of"] = "2026-08-24T22:00:00-04:00"
            context["quotes"]["AAPL"]["as_of"] = "2026-08-24T21:59:00-04:00"
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context))
            same_day = subprocess.run(
                base + [
                    "execute-dry-run", "--config", str(enabled_config),
                    "--plan", str(output / "plans" / "2026-08-24" / "order_plan.json"),
                    "--context", str(context_path), "--output", str(output),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(same_day.returncode, 0)
            self.assertIn("later trading date", same_day.stderr)


if __name__ == "__main__":
    unittest.main()
