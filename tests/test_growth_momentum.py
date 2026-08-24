import copy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from ripple.growth_momentum import build_decision_input
from ripple import OrderPlan
from ripple.mvp import execute_dry_run


ROOT = Path(__file__).resolve().parents[1]


class GrowthMomentumTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config" / "mvp.json").read_text())
        self.facts = json.loads(
            (ROOT / "fixtures" / "mvp" / "growth_momentum_input.json").read_text()
        )

    def test_selects_highest_relative_strength_and_fixes_new_position_at_ten_percent(self):
        second = copy.deepcopy(self.facts["candidates"][0])
        second.update({"symbol": "MSFT", "return_60d": "0.20"})
        self.facts["candidates"].append(second)

        decision_input = build_decision_input(self.facts, self.config)

        self.assertEqual(
            decision_input["snapshot"]["inputs"]["outcome"],
            {
                "result": "BUY_ONLY",
                "reason": "BUY_TOP_RELATIVE_STRENGTH",
                "selected_symbol": "MSFT",
            },
        )
        self.assertEqual(
            decision_input["decision"]["target_portfolio"],
            {"MSFT": "0.10", "cash": "0.90"},
        )
        self.assertEqual(len(decision_input["decision"]["orders"]), 1)
        self.assertEqual(decision_input["decision"]["orders"][0]["quantity"], "0.990099")

    def test_risk_off_and_missing_quality_produce_no_trade(self):
        cases = []
        risk_off = copy.deepcopy(self.facts)
        risk_off["market_gate"]["close"] = risk_off["market_gate"]["sma50"]
        cases.append((risk_off, "MARKET_RISK_OFF"))
        weak_quality = copy.deepcopy(self.facts)
        weak_quality["candidates"][0]["business_quality_pass"] = False
        cases.append((weak_quality, "NO_ELIGIBLE_CANDIDATE"))
        for facts, reason in cases:
            with self.subTest(reason=reason):
                decision_input = build_decision_input(facts, self.config)
                self.assertEqual(decision_input["decision"]["orders"], [])
                self.assertEqual(
                    decision_input["decision"]["target_portfolio"], {"cash": "1"},
                )
                self.assertEqual(
                    decision_input["snapshot"]["inputs"]["outcome"]["reason"], reason,
                )

    def test_existing_position_fails_closed_until_sell_hold_policy_exists(self):
        self.facts["account_baseline"] = {
            "cash": "900", "positions": {"AAPL": "1"},
        }
        with self.assertRaisesRegex(ValueError, "empty Account A"):
            build_decision_input(self.facts, self.config)

    def test_strict_input_and_account_a_scope_fail_closed(self):
        self.facts["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "input fields"):
            build_decision_input(self.facts, self.config)

        facts = json.loads(
            (ROOT / "fixtures" / "mvp" / "growth_momentum_input.json").read_text()
        )
        config = copy.deepcopy(self.config)
        config["account_id"] = "account_B"
        with self.assertRaisesRegex(ValueError, "account_A"):
            build_decision_input(facts, config)

    def test_published_growth_plan_is_consumed_by_existing_execution(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "account_A"
            input_path = root / "growth.json"
            context_path = root / "context.json"
            input_path.write_text(json.dumps(self.facts))

            published = subprocess.run(
                [
                    "python3.12", "-m", "ripple.mvp", "publish-growth-decision",
                    "--config", str(ROOT / "config" / "mvp.json"),
                    "--input", str(input_path),
                    "--output", str(output),
                    "--manual-run",
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(published.returncode, 0, published.stderr)
            plan_path = output / "plans" / "2026-08-23" / "order_plan.json"
            plan = OrderPlan.from_dict(json.loads(plan_path.read_text()))
            context = {
                "account_id": "account_A",
                "as_of": "2026-08-24T09:35:00-04:00",
                "account": {
                    "equity": "1000",
                    "cash": "1000",
                    "daily_pnl": "0",
                    "high_water_mark": "1000",
                    "new_positions_today": 0,
                    "positions": {},
                    "loss_sales": []
                },
                "quotes": {
                    "AAPL": {
                        "price": "100.50",
                        "as_of": "2026-08-24T09:34:00-04:00"
                    }
                }
            }
            context_path.write_text(json.dumps(context))

            result = execute_dry_run(
                ROOT / "config" / "mvp.json",
                plan_path,
                context_path,
                output,
                now=datetime.fromisoformat(context["as_of"]),
            )

            self.assertEqual(plan.orders[0]["symbol"], "AAPL")
            self.assertEqual(result["status"], "allowed")
            self.assertTrue(result["actions"][0]["allowed"])


if __name__ == "__main__":
    unittest.main()
