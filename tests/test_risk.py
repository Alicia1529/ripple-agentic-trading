import unittest
from copy import deepcopy

from ripple.risk import evaluate_plan


class RiskEvaluationTests(unittest.TestCase):
    def plan(self):
        return {
            "order_plan_id": "d44c4279-6d02-4773-a888-f906fb738aae",
            "decision_time": "2026-08-24T21:00:00-04:00",
            "account_id": "account_a",
            "strategy_id": "growth_momentum_v1",
            "model_config_version": "mvp_v1",
            "decision_snapshot_id": "10de633f-be1f-4548-944a-76b94296ed5b",
            "market_snapshot_as_of": "2026-08-24T20:55:00-04:00",
            "account_baseline": {"cash": "500", "positions": {}},
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
                "buy_reason": "Strongest eligible momentum candidate.",
            }],
        }

    def context(self):
        return {
            "account_id": "account_a",
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
            "account_id": "account_a",
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
            "symbol": "AAPL",
            "side": "BUY",
            "desired_buy_price": "101.00",
            "buy_reason": "Strongest eligible momentum candidate.",
            "allowed": True,
            "abort_reason": None,
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
            {"field": "quantity", "value": "1.980198"},
        )
        self.assertEqual(result["actions"][0]["broker_order"]["quantity"], "1.980198")

    def test_multiple_buys_reserve_cash_at_their_worst_case_fill_price(self):
        plan = self.plan()
        plan["target_portfolio"] = {"AAPL": "0.1", "MSFT": "0.1", "cash": "0.8"}
        second = dict(plan["orders"][0])
        second["order_id"] = "8e8e6f96-2948-4b91-9675-11a029968ae1"
        second["symbol"] = "MSFT"
        plan["orders"] = [plan["orders"][0], second]
        plan["orders"][0]["quantity"] = "1"
        second["quantity"] = "1"
        plan["account_baseline"]["cash"] = "150"
        context = self.context()
        context["account"]["cash"] = "150"
        context["quotes"]["MSFT"] = {
            "price": "100.25", "as_of": "2026-08-25T09:34:00-04:00",
        }

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["actions"][0]["actual_sizing"]["value"], "1")
        self.assertEqual(result["actions"][1]["reason_code"], "available_cash")
        self.assertEqual(result["actions"][1]["actual_sizing"]["value"], "0.485148")

    def test_execution_guards_reject_without_broker_arguments(self):
        cases = []

        stale = self.context()
        stale["quotes"]["AAPL"]["as_of"] = "2026-08-25T09:00:00-04:00"
        cases.append((self.plan(), stale, self.rules(), "stale_quote", "aborted"))

        gap = self.context()
        gap["quotes"]["AAPL"]["price"] = "102"
        cases.append((self.plan(), gap, self.rules(), "price_outside_tolerance", "rejected"))

        daily_loss = self.context()
        daily_loss["account"]["daily_pnl"] = "-50"
        cases.append((self.plan(), daily_loss, self.rules(), "daily_loss", "rejected"))

        drawdown = self.context()
        drawdown["account"]["equity"] = "900"
        cases.append((self.plan(), drawdown, self.rules(), "drawdown_tier1", "rejected"))

        order_limit = self.context()
        order_limit["account"]["new_positions_today"] = 3
        cases.append((self.plan(), order_limit, self.rules(), "max_new_positions", "rejected"))

        wash_sale = self.context()
        wash_sale["account"]["loss_sales"] = [{
            "symbol": "AAPL", "sold_at": "2026-08-01T10:00:00-04:00",
        }]
        cases.append((self.plan(), wash_sale, self.rules(), "wash_sale", "rejected"))

        missing_quote = self.context()
        del missing_quote["quotes"]["AAPL"]
        cases.append((self.plan(), missing_quote, self.rules(), "missing_quote", "aborted"))

        no_cash = self.context()
        no_cash["account"]["cash"] = "0"
        no_cash_plan = self.plan()
        no_cash_plan["account_baseline"]["cash"] = "0"
        cases.append((no_cash_plan, no_cash, self.rules(), "available_cash", "rejected"))

        for plan, context, rules, reason_code, status in cases:
            with self.subTest(reason_code=reason_code):
                result = evaluate_plan(deepcopy(plan), context, rules)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["actions"][0]["allowed"], False)
                self.assertEqual(result["actions"][0]["reason_code"], reason_code)
                self.assertEqual(result["actions"][0]["symbol"], "AAPL")
                self.assertEqual(result["actions"][0]["side"], "BUY")
                self.assertEqual(result["actions"][0]["desired_buy_price"], "101.00")
                self.assertEqual(
                    result["actions"][0]["buy_reason"],
                    "Strongest eligible momentum candidate.",
                )
                self.assertEqual(
                    result["actions"][0]["abort_reason"]["code"], reason_code,
                )
                self.assertIsNone(result["actions"][0]["actual_sizing"])
                self.assertIsNone(result["actions"][0]["broker_order"])

    def test_buy_above_opening_gap_threshold_is_rejected(self):
        plan = self.plan()
        plan["orders"][0]["gap_cancel_above"] = "103.00"
        context = self.context()
        context["quotes"]["AAPL"]["session_open"] = "103.01"

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["actions"][0]["reason_code"], "opening_gap")
        self.assertIsNone(result["actions"][0]["broker_order"])

    def test_buy_at_opening_gap_threshold_is_allowed(self):
        plan = self.plan()
        plan["orders"][0]["gap_cancel_above"] = "103.00"
        context = self.context()
        context["quotes"]["AAPL"]["session_open"] = "103.00"

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["status"], "allowed")
        self.assertTrue(result["actions"][0]["allowed"])

    def test_missing_required_session_open_aborts_the_plan(self):
        plan = self.plan()
        plan["orders"][0]["gap_cancel_above"] = "103.00"

        result = evaluate_plan(plan, self.context(), self.rules())

        self.assertEqual(result["status"], "aborted")
        self.assertEqual(result["abort_reason"], "missing_session_open")
        self.assertEqual(
            result["actions"][0]["reason_code"], "missing_session_open",
        )

    def test_sell_is_clipped_to_owned_quantity(self):
        plan = self.plan()
        plan["target_portfolio"] = {"AAPL": "0", "cash": "1"}
        plan["orders"][0]["side"] = "SELL"
        plan["orders"][0].pop("buy_reason")
        plan["orders"][0]["quantity"] = "2"
        context = self.context()
        context["account"]["positions"] = {
            "AAPL": {"quantity": "1", "average_cost": "90"},
        }
        plan["account_baseline"]["positions"] = {"AAPL": "1"}

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["actions"][0]["reason_code"], "position_quantity")
        self.assertEqual(result["actions"][0]["actual_sizing"]["value"], "1")
        self.assertEqual(result["actions"][0]["broker_order"]["quantity"], "1")

    def test_existing_position_thresholds_generate_deterministic_risk_exits(self):
        plan = self.plan()
        plan["orders"] = []
        plan["target_portfolio"] = {"cash": "1"}
        plan["account_baseline"]["positions"] = {"AAPL": "1"}
        context = self.context()
        context["account"]["positions"] = {
            "AAPL": {"quantity": "1", "average_cost": "120"},
        }

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["position_alerts"], [{
            "symbol": "AAPL",
            "kind": "stop_loss",
            "current_price": "100.25",
            "average_cost": "120",
        }])
        self.assertEqual(len(result["actions"]), 1)
        action = result["actions"][0]
        self.assertEqual(action["reason_code"], "stop_loss")
        self.assertEqual(action["symbol"], "AAPL")
        self.assertEqual(action["side"], "SELL")
        self.assertIsNone(action["desired_buy_price"])
        self.assertIsNone(action["buy_reason"])
        self.assertIsNone(action["abort_reason"])
        self.assertEqual(action["broker_order"]["side"], "sell")
        self.assertEqual(action["broker_order"]["type"], "market")
        self.assertEqual(action["broker_order"]["quantity"], "1")

    def test_stale_quote_aborts_all_planned_orders(self):
        plan = self.plan()
        plan["target_portfolio"] = {"AAPL": "0.1", "MSFT": "0.1", "cash": "0.8"}
        second = dict(plan["orders"][0])
        second["order_id"] = "8e8e6f96-2948-4b91-9675-11a029968ae1"
        second["symbol"] = "MSFT"
        plan["orders"].append(second)
        context = self.context()
        context["quotes"]["AAPL"]["as_of"] = "2026-08-25T09:00:00-04:00"
        context["quotes"]["MSFT"] = {
            "price": "100.25", "as_of": "2026-08-25T09:34:00-04:00",
        }

        result = evaluate_plan(plan, context, self.rules())

        self.assertEqual(result["status"], "aborted")
        self.assertTrue(all(not action["allowed"] for action in result["actions"]))
        self.assertTrue(all(action["broker_order"] is None for action in result["actions"]))

    def test_account_state_mismatch_aborts_plan(self):
        context = self.context()
        context["account"]["cash"] = "499"

        result = evaluate_plan(self.plan(), context, self.rules())

        self.assertEqual(result["status"], "aborted")
        self.assertEqual(result["actions"][0]["reason_code"], "account_state_mismatch")

    def test_account_baseline_compares_decimal_values_not_string_formatting(self):
        plan = self.plan()
        plan["account_baseline"] = {"cash": "500.00", "positions": {"AAPL": "1.0"}}
        plan["orders"] = []
        plan["target_portfolio"] = {"cash": "1"}
        context = self.context()
        context["account"]["cash"] = "500"
        context["account"]["positions"] = {
            "AAPL": {"quantity": "1.00", "average_cost": "100.25"},
        }

        result = evaluate_plan(plan, context, self.rules())

        self.assertIsNone(result["abort_reason"])

    def test_tier_two_drawdown_requires_manual_restart_after_recovery(self):
        result = evaluate_plan(
            self.plan(), self.context(), self.rules(), new_entries_locked=True,
        )

        self.assertEqual(result["actions"][0]["reason_code"], "drawdown_restart_required")
        self.assertTrue(result["manual_restart_required"])

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

        wrong_account = self.context()
        wrong_account["account_id"] = "account_b"
        cases.append((self.plan(), wrong_account, self.rules()))

        for plan, context, rules in cases:
            with self.subTest(context=context, rules=rules):
                with self.assertRaises(ValueError):
                    evaluate_plan(plan, context, rules)


if __name__ == "__main__":
    unittest.main()
