import unittest

from ripple.order_plan import OrderPlan


class OrderPlanTests(unittest.TestCase):
    def test_cycle_profile_and_trade_date_are_paired_with_legacy_round_trip(self):
        legacy_document = self.valid_document()
        legacy = OrderPlan.from_dict(legacy_document)
        self.assertIsNone(legacy.cycle_profile)
        self.assertEqual(legacy.to_dict(), legacy_document)

        attributed = self.valid_document()
        attributed.update({
            "cycle_profile": "same_session_close",
            "trade_date": "2026-08-22",
        })
        self.assertEqual(OrderPlan.from_dict(attributed).to_dict(), attributed)

        for mutation in (
            {"cycle_profile": "same_session_close"},
            {"trade_date": "2026-08-22"},
            {"cycle_profile": "later", "trade_date": "2026-08-22"},
            {"cycle_profile": "same_session_close", "trade_date": "08/22/2026"},
        ):
            document = self.valid_document()
            document.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                OrderPlan.from_dict(document)

    def valid_document(self):
        return {
            "order_plan_id": "d44c4279-6d02-4773-a888-f906fb738aae",
            "decision_time": "2026-08-22T21:05:00-04:00",
            "account_id": "account_a",
            "strategy_id": "growth_momentum_v1",
            "model_config_version": "config_A_v3",
            "decision_snapshot_id": "10de633f-be1f-4548-944a-76b94296ed5b",
            "market_snapshot_as_of": "2026-08-22T21:00:00-04:00",
            "account_baseline": {"cash": "850", "positions": {}},
            "target_portfolio": {"AAPL": "0.15", "cash": "0.85"},
            "orders": [],
        }

    def valid_buy_order(self):
        return {
            "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": "12",
            "order_type": "LIMIT",
            "limit_price": "227.50",
            "price_tolerance_pct": "0.005",
            "reference_price_at_decision": "226.40",
            "market_hours": "regular_hours",
            "time_in_force": "gfd",
            "buy_reason": "Strongest eligible momentum candidate.",
        }

    def test_plan_is_deeply_immutable_and_contains_no_execution_state(self):
        document = {
            "order_plan_id": "d44c4279-6d02-4773-a888-f906fb738aae",
            "decision_time": "2026-08-22T21:05:00-04:00",
            "account_id": "account_a",
            "strategy_id": "growth_momentum_v1",
            "model_config_version": "config_A_v3",
            "decision_snapshot_id": "10de633f-be1f-4548-944a-76b94296ed5b",
            "market_snapshot_as_of": "2026-08-22T21:00:00-04:00",
            "account_baseline": {"cash": "850", "positions": {}},
            "target_portfolio": {"AAPL": "0.15", "cash": "0.85"},
            "orders": [
                {
                    "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "quantity": "12",
                    "order_type": "LIMIT",
                    "limit_price": "227.50",
                    "price_tolerance_pct": "0.005",
                    "reference_price_at_decision": "226.40",
                    "market_hours": "regular_hours",
                    "time_in_force": "gfd",
                    "buy_reason": "Strongest eligible momentum candidate.",
                }
            ],
        }

        plan = OrderPlan.from_dict(document)
        document["target_portfolio"]["AAPL"] = "1.00"
        document["orders"][0]["quantity"] = "999"

        self.assertEqual(plan.target_portfolio["AAPL"], "0.15")
        self.assertEqual(plan.orders[0]["quantity"], "12")
        self.assertEqual(
            plan.orders[0]["buy_reason"],
            "Strongest eligible momentum candidate.",
        )
        with self.assertRaises(TypeError):
            plan.orders[0]["state"] = "filled"
        self.assertEqual(plan.to_dict()["orders"][0]["quantity"], "12")
        self.assertNotIn("execution_status", plan.to_dict())

    def test_decision_run_kind_is_optional_for_history_and_strict_when_present(self):
        legacy = OrderPlan.from_dict(self.valid_document())
        self.assertIsNone(legacy.decision_run_kind)
        self.assertNotIn("decision_run_kind", legacy.to_dict())
        self.assertIsNone(legacy.decision_rationale)
        self.assertNotIn("decision_rationale", legacy.to_dict())

        manual_document = self.valid_document()
        manual_document["decision_run_kind"] = "manual"
        manual = OrderPlan.from_dict(manual_document)
        self.assertEqual(manual.decision_run_kind, "manual")
        self.assertEqual(manual.to_dict()["decision_run_kind"], "manual")

        backfill_document = self.valid_document()
        backfill_document["decision_run_kind"] = "backfill"
        backfill = OrderPlan.from_dict(backfill_document)
        self.assertEqual(backfill.decision_run_kind, "backfill")
        self.assertEqual(backfill.to_dict()["decision_run_kind"], "backfill")

        invalid = self.valid_document()
        invalid["decision_run_kind"] = "bypass"
        with self.assertRaisesRegex(ValueError, "decision_run_kind"):
            OrderPlan.from_dict(invalid)

        explained_document = self.valid_document()
        explained_document["decision_rationale"] = "No eligible candidate; retain cash."
        explained = OrderPlan.from_dict(explained_document)
        self.assertEqual(
            explained.decision_rationale,
            "No eligible candidate; retain cash.",
        )
        self.assertEqual(
            explained.to_dict()["decision_rationale"],
            "No eligible candidate; retain cash.",
        )

        invalid_rationale = self.valid_document()
        invalid_rationale["decision_rationale"] = ""
        with self.assertRaisesRegex(ValueError, "decision_rationale"):
            OrderPlan.from_dict(invalid_rationale)

    def test_malformed_or_execution_bearing_plans_fail_closed(self):
        invalid_documents = []

        execution_bearing = self.valid_document()
        execution_bearing["execution_status"] = "filled"
        invalid_documents.append(execution_bearing)

        nested_execution_outcome = self.valid_document()
        nested_execution_outcome["orders"] = [
            {
                "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
                "symbol": "AAPL",
                "state": "filled",
                "broker_order_id": "private-broker-order",
            }
        ]
        invalid_documents.append(nested_execution_outcome)

        deeply_nested_execution_outcome = self.valid_document()
        deeply_nested_execution_outcome["orders"] = [
            {
                "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
                "symbol": "AAPL",
                "result": {"state": "filled"},
            }
        ]
        invalid_documents.append(deeply_nested_execution_outcome)

        out_of_scope_tax_lots = self.valid_document()
        out_of_scope_tax_lots["orders"] = [
            {
                "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
                "symbol": "AAPL",
                "side": "SELL",
                "quantity": "12",
                "order_type": "LIMIT",
                "limit_price": "227.50",
                "price_tolerance_pct": "0.005",
                "reference_price_at_decision": "226.40",
                "market_hours": "regular_hours",
                "time_in_force": "gfd",
                "tax_lots": [{"open_lot_id": "out-of-scope", "quantity": "12"}],
            }
        ]
        invalid_documents.append(out_of_scope_tax_lots)

        bad_id = self.valid_document()
        bad_id["order_plan_id"] = "not-a-uuid"
        invalid_documents.append(bad_id)

        naive_time = self.valid_document()
        naive_time["decision_time"] = "2026-08-22T21:05:00"
        invalid_documents.append(naive_time)

        future_snapshot = self.valid_document()
        future_snapshot["market_snapshot_as_of"] = "2026-08-22T21:06:00-04:00"
        invalid_documents.append(future_snapshot)

        empty_account = self.valid_document()
        empty_account["account_id"] = ""
        invalid_documents.append(empty_account)

        bad_portfolio = self.valid_document()
        bad_portfolio["target_portfolio"] = []
        invalid_documents.append(bad_portfolio)

        bad_orders = self.valid_document()
        bad_orders["orders"] = {"order_id": "not-a-list"}
        invalid_documents.append(bad_orders)

        non_json_order = self.valid_document()
        non_json_order["orders"] = [{"symbols": {"AAPL"}}]
        invalid_documents.append(non_json_order)

        for value in ("15%", "not-a-decimal"):
            invalid_decimal = self.valid_document()
            invalid_decimal["target_portfolio"] = {"AAPL": value}
            invalid_documents.append(invalid_decimal)

        invalid_order_decimal = self.valid_document()
        invalid_order_decimal["orders"] = [{
            "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965", "symbol": "AAPL", "side": "BUY",
            "quantity": "12", "order_type": "LIMIT", "limit_price": "15%",
            "price_tolerance_pct": "0.005", "reference_price_at_decision": "226.40",
        }]
        invalid_documents.append(invalid_order_decimal)

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    OrderPlan.from_dict(document)

    def test_mvp_portfolio_and_order_semantics_fail_closed(self):
        valid_order = {
            "order_id": "04bbf1c7-416b-4ca2-b5a6-0e27be980965",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": "1",
            "order_type": "LIMIT",
            "limit_price": "101.00",
            "price_tolerance_pct": "0.01",
            "reference_price_at_decision": "100.00",
            "market_hours": "regular_hours",
            "time_in_force": "gfd",
        }
        invalid_documents = []

        bad_weight_sum = self.valid_document()
        bad_weight_sum["target_portfolio"] = {"AAPL": "0.15", "cash": "0.80"}
        invalid_documents.append(bad_weight_sum)

        negative_weight = self.valid_document()
        negative_weight["target_portfolio"] = {"AAPL": "-0.15", "cash": "1.15"}
        invalid_documents.append(negative_weight)

        for field, value in (
            ("side", "SHORT"),
            ("order_type", "STOP_LIMIT"),
            ("quantity", "0"),
            ("limit_price", "0"),
            ("limit_price", "103"),
            ("price_tolerance_pct", "0"),
            ("reference_price_at_decision", "-1"),
        ):
            document = self.valid_document()
            document["orders"] = [{**valid_order, field: value}]
            invalid_documents.append(document)

        missing_target = self.valid_document()
        missing_target["orders"] = [valid_order]
        missing_target["target_portfolio"] = {"MSFT": "0.15", "cash": "0.85"}
        invalid_documents.append(missing_target)

        duplicate_order = self.valid_document()
        duplicate_order["orders"] = [valid_order, dict(valid_order)]
        invalid_documents.append(duplicate_order)

        for mutation in (
            {"order_type": "MARKET", "limit_price": None},
            {"market_hours": None},
            {"time_in_force": None},
            {"quantity": None, "dollar_amount": "100"},
        ):
            document = self.valid_document()
            order = dict(valid_order)
            for field, value in mutation.items():
                if value is None:
                    order.pop(field, None)
                else:
                    order[field] = value
            document["orders"] = [order]
            invalid_documents.append(document)

        for baseline in (
            {"cash": "850"},
            {"cash": "not-decimal", "positions": {}},
            {"cash": "850", "positions": {"AAPL": "0"}},
        ):
            document = self.valid_document()
            document["account_baseline"] = baseline
            invalid_documents.append(document)

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    OrderPlan.from_dict(document)

    def test_buy_may_record_an_opening_gap_cancel_price(self):
        document = self.valid_document()
        document["orders"] = [self.valid_buy_order()]
        document["orders"][0]["gap_cancel_above"] = "233.192"

        plan = OrderPlan.from_dict(document)

        self.assertEqual(plan.orders[0]["gap_cancel_above"], "233.192")

    def test_opening_gap_cancel_price_is_buy_only_and_above_reference(self):
        invalid_documents = []

        sell = self.valid_document()
        sell["orders"] = [self.valid_buy_order()]
        sell["orders"][0]["side"] = "SELL"
        sell["orders"][0].pop("buy_reason")
        sell["orders"][0]["gap_cancel_above"] = "233.192"
        invalid_documents.append(sell)

        not_above_reference = self.valid_document()
        not_above_reference["orders"] = [self.valid_buy_order()]
        not_above_reference["orders"][0]["gap_cancel_above"] = "226.40"
        invalid_documents.append(not_above_reference)

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    OrderPlan.from_dict(document)


if __name__ == "__main__":
    unittest.main()
