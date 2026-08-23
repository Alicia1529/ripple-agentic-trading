import unittest
from copy import deepcopy

from ripple.risk import evaluate_plan


class RiskEvaluationTests(unittest.TestCase):
    def plan(self):
        return {
            "order_plan_id": "d44c4279-6d02-4773-a888-f906fb738aae",
            "decision_time": "2026-08-24T21:00:00-04:00",
            "account_id": "account_A",
            "model_config_version": "mvp_v1",
            "decision_snapshot_id": "10de633f-be1f-4548-944a-76b94296ed5b",
            "market_snapshot_as_of": "2026-08-24T20:55:00-04:00",
            "target_portfolio": {"AAPL": "0.15", "cash": "0.85"},
            "orders": [{
                "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": "1.5",
                "order_type": "LIMIT",
                "limit_price": "101.00",
                "price_tolerance_pct": "0.01",
                "reference_price_at_decision": "100.00",
                "market_hours": "regular_hours",
                "time_in_force": "gfd",
            }],
        }

    def context(self):
        return {
            "as_of": "2026-08-25T09:35:00-04:00",
            "account": {
                "equity": "1000",
                "cash": "500",
                "daily_pnl": "0",
                "high_water_mark": "1000",
                "new_positions_today": 0,
                "positions": {},
                "loss_sales": [],
            },
            "quotes": {
                "AAPL": {"price": "100.25", "as_of": "2026-08-25T09:34:00-04:00"},
            },
        }

    def rules(self):
        return {
            "account_id": "account_A",
            "execution": {"mode": "dry_run"},
            "universe": ["AAPL", "MSFT", "SPY", "QQQ"],
            "risk": {
                "max_position_pct": "0.20",
                "max_new_positions_per_day": 3,
                "daily_loss_pct": "0.05",
                "drawdown_tier1_pct": "0.10",
                "drawdown_tier2_pct": "0.15",
                "max_quote_age_minutes": 15,
                "wash_sale_lookback_days": 30,
                "stop_loss_pct": "0.08",
                "take_profit_pct": "0.20",
            },
        }

    def test_allowed_order_returns_exact_dry_run_broker_arguments(self):
        result = evaluate_plan(self.plan(), self.context(), self.rules())

        self.assertEqual(result["status"], "allowed")
        self.assertEqual(result["mode"], "dry_run")
        self.assertEqual(result["actions"], [{
            "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
            "allowed": True,
            "reason_code": "allowed",
            "original_sizing": {"field": "quantity", "value": "1.5"},
            "actual_sizing": {"field": "quantity", "value": "1.5"},
            "broker_order": {
                "side": "buy",
                "symbol": "AAPL",
                "type": "limit",
                "quantity": "1.5",
                "limit_price": "101.00",
                "market_hours": "regular_hours",
                "time_in_force": "gfd",
                "ref_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
            },
        }])

    def test_position_cap_clips_quantity_downward(self):
        plan = self.plan()
        plan["orders"][0]["quantity"] = "3"

        result = evaluate_plan(plan, self.context(), self.rules())

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["actions"][0]["reason_code"], "max_position")
        self.assertEqual(
            result["actions"][0]["actual_sizing"],
            {"field": "quantity", "value": "1.995012"},
        )
        self.assertEqual(result["actions"][0]["broker_order"]["quantity"], "1.995012")

    def test_execution_guards_reject_without_broker_arguments(self):
        cases = []

        disabled_rules = self.rules()
        disabled_rules["execution"]["mode"] = "disabled"
        cases.append((self.context(), disabled_rules, "execution_disabled"))

        stale = self.context()
        stale["quotes"]["AAPL"]["as_of"] = "2026-08-25T09:00:00-04:00"
        cases.append((stale, self.rules(), "stale_quote"))

        gap = self.context()
        gap["quotes"]["AAPL"]["price"] = "102"
        cases.append((gap, self.rules(), "price_outside_tolerance"))

        daily_loss = self.context()
        daily_loss["account"]["daily_pnl"] = "-50"
        cases.append((daily_loss, self.rules(), "daily_loss"))

        drawdown = self.context()
        drawdown["account"]["equity"] = "900"
        cases.append((drawdown, self.rules(), "drawdown_tier1"))

        order_limit = self.context()
        order_limit["account"]["new_positions_today"] = 3
        cases.append((order_limit, self.rules(), "max_new_positions"))

        wash_sale = self.context()
        wash_sale["account"]["loss_sales"] = [{
            "symbol": "AAPL", "sold_at": "2026-08-01T10:00:00-04:00",
        }]
        cases.append((wash_sale, self.rules(), "wash_sale"))

        missing_quote = self.context()
        del missing_quote["quotes"]["AAPL"]
        cases.append((missing_quote, self.rules(), "missing_quote"))

        no_cash = self.context()
        no_cash["account"]["cash"] = "0"
        cases.append((no_cash, self.rules(), "available_cash"))

        for context, rules, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result = evaluate_plan(deepcopy(self.plan()), context, rules)
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["actions"][0]["allowed"], False)
                self.assertEqual(result["actions"][0]["reason_code"], reason_code)
                self.assertIsNone(result["actions"][0]["actual_sizing"])
                self.assertIsNone(result["actions"][0]["broker_order"])

    def test_sell_is_clipped_to_owned_quantity(self):
        plan = self.plan()
        plan["target_portfolio"] = {"AAPL": "0", "cash": "1"}
        plan["orders"][0]["side"] = "SELL"
        plan["orders"][0]["quantity"] = "2"
        context = self.context()
        context["account"]["positions"] = {
            "AAPL": {"quantity": "1", "average_cost": "90"},
        }

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["actions"][0]["reason_code"], "position_quantity")
        self.assertEqual(result["actions"][0]["actual_sizing"]["value"], "1")
        self.assertEqual(result["actions"][0]["broker_order"]["quantity"], "1")

    def test_existing_position_thresholds_are_reported_without_inventing_orders(self):
        context = self.context()
        context["account"]["positions"] = {
            "AAPL": {"quantity": "1", "average_cost": "120"},
        }

        result = evaluate_plan(self.plan(), context, self.rules())

        self.assertEqual(result["position_alerts"], [{
            "symbol": "AAPL",
            "kind": "stop_loss",
            "current_price": "100.25",
            "average_cost": "120",
        }])
        self.assertEqual(len(result["actions"]), 1)

    def test_unknown_or_non_json_risk_inputs_fail_closed(self):
        cases = []

        rules_with_secret = self.rules()
        rules_with_secret["credential"] = "must-not-be-accepted"
        cases.append((self.plan(), self.context(), rules_with_secret))

        context_with_secret = self.context()
        context_with_secret["account"]["token"] = "must-not-be-accepted"
        cases.append((self.plan(), context_with_secret, self.rules()))

        floating_cash = self.context()
        floating_cash["account"]["cash"] = 500.0
        cases.append((self.plan(), floating_cash, self.rules()))

        bad_mode = self.rules()
        bad_mode["execution"]["mode"] = "production"
        cases.append((self.plan(), self.context(), bad_mode))

        for plan, context, rules in cases:
            with self.subTest(context=context, rules=rules):
                with self.assertRaises(ValueError):
                    evaluate_plan(plan, context, rules)


if __name__ == "__main__":
    unittest.main()
