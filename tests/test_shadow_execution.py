import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ShadowExecutionTests(unittest.TestCase):
    def test_shadow_sell_updates_cash_position_and_loss_sale_state(self):
        from ripple.shadow import simulate_shadow_fills

        result = simulate_shadow_fills(
            {
                "actions": [{
                    "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
                    "symbol": "AAPL",
                    "side": "SELL",
                    "allowed": True,
                    "actual_sizing": {"field": "quantity", "value": "0.5"},
                    "broker_order": {
                        "side": "sell",
                        "symbol": "AAPL",
                        "type": "limit",
                        "quantity": "0.5",
                        "limit_price": "99",
                    },
                }],
            },
            {
                "as_of": "2026-08-25T09:35:00-04:00",
                "account": {
                    "equity": "200",
                    "cash": "100",
                    "daily_pnl": "-10",
                    "high_water_mark": "220",
                    "new_positions_today": 0,
                    "positions": {
                        "AAPL": {"quantity": "1", "average_cost": "110"},
                    },
                    "loss_sales": [],
                },
                "quotes": {
                    "AAPL": {
                        "price": "100",
                        "as_of": "2026-08-25T09:34:00-04:00",
                    },
                },
            },
        )

        self.assertEqual(result["ending_account"]["cash"], "150")
        self.assertEqual(result["ending_account"]["positions"], {
            "AAPL": {"quantity": "0.5", "average_cost": "110"},
        })
        self.assertEqual(result["ending_account"]["loss_sales"], [{
            "symbol": "AAPL", "sold_at": "2026-08-25T09:35:00-04:00",
        }])

    def test_shadow_execution_records_t_plus_one_fill_and_ending_account(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "dry_cycle_account_b.json").read_text()
        )
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
            plan_path = output / "plans" / "2026-08-24" / "order_plan.json"
            result = execute_shadow(
                ROOT / "config" / "account_b.json",
                plan_path,
                context_input,
                output,
                now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
            )

            self.assertEqual(result["mode"], "shadow")
            self.assertEqual(result["strategy_id"], "growth_momentum_v1")
            self.assertEqual(result["fill_status"], "filled")
            self.assertEqual(result["shadow_fills"], [{
                "order_id": result["actions"][0]["order_id"],
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": "0.5",
                "price": "100.50",
                "filled_at": "2026-08-25T09:35:00-04:00",
                "status": "filled",
                "reason_code": "assumed_t_plus_one_quote_fill",
            }])
            self.assertEqual(result["ending_account"]["cash"], "669.75")
            self.assertEqual(result["ending_account"]["positions"], {
                "AAPL": {"quantity": "0.5", "average_cost": "100.5"},
            })
            self.assertTrue(
                (output / "executions" / "2026-08-25" / "shadow.json").is_file()
            )
            execution_log = json.loads(
                (output / "logs" / "executions.jsonl").read_text()
            )
            self.assertEqual(execution_log["kind"], "shadow_execution_completed")
            self.assertEqual(execution_log["strategy_id"], "growth_momentum_v1")
            self.assertEqual(execution_log["fill_count"], 1)
            self.assertIn(
                "No broker write tool was called",
                (output / "reports" / "2026-08-25.md").read_text(),
            )

            with self.assertRaises(FileExistsError):
                execute_shadow(
                    ROOT / "config" / "account_b.json",
                    plan_path,
                    context_input,
                    output,
                    now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
                )

    def test_allowed_limit_that_is_not_marketable_is_not_assumed_filled(self):
        fixture = json.loads(
            (ROOT / "fixtures" / "mvp" / "dry_cycle_account_b.json").read_text()
        )
        fixture["decision"]["orders"][0]["limit_price"] = "100.50"
        fixture["execution_context"]["quotes"]["AAPL"]["price"] = "100.75"
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
            result = execute_shadow(
                ROOT / "config" / "account_b.json",
                output / "plans" / "2026-08-24" / "order_plan.json",
                context_input,
                output,
                now=datetime.fromisoformat(fixture["execution_context"]["as_of"]),
            )

            self.assertEqual(result["status"], "allowed")
            self.assertEqual(result["fill_status"], "not_filled")
            self.assertEqual(result["shadow_fills"][0]["status"], "not_filled")
            self.assertEqual(
                result["shadow_fills"][0]["reason_code"], "limit_not_marketable",
            )
            self.assertEqual(result["ending_account"]["cash"], "720")
            self.assertEqual(result["ending_account"]["positions"], {})


if __name__ == "__main__":
    unittest.main()
