import unittest

from ripple import ExecutionEvent


class ExecutionEventTests(unittest.TestCase):
    event_id = "d44c4279-6d02-4773-a888-f906fb738aae"
    plan_id = "10de633f-be1f-4548-944a-76b94296ed5b"
    order_id = "04bbf1c7-416b-4ca2-b5a6-0e27be980965"
    attempt_id = "6b0d8396-9978-4e7c-9c08-d0ceca7ba903"

    def valid_document(self, kind="planned"):
        document = {
            "execution_event_id": self.event_id,
            "order_plan_id": self.plan_id,
            "account_id": "account_A",
            "occurred_at": "2026-08-23T09:35:00-04:00",
            "kind": kind,
            "order_id": None,
            "payload": {},
        }
        if kind == "aborted":
            document["payload"] = {"reason_code": "account_state_mismatch"}
        if kind in {"scaled", "clipped"}:
            document["order_id"] = self.order_id
            document["payload"] = {
                "sizing_field": "quantity",
                "original_value": "12",
                "actual_value": "10",
                "rule_code": "available_cash",
            }
        if kind == "submission_started":
            document["order_id"] = self.order_id
            document["payload"] = {"submission_attempt_id": self.attempt_id}
        if kind == "broker_acknowledged":
            document["order_id"] = self.order_id
            document["payload"] = {
                "submission_attempt_id": self.attempt_id,
                "broker_order_id": "opaque-broker-id",
                "evidence": self.evidence(),
            }
        if kind in {"partially_filled", "filled"}:
            document["order_id"] = self.order_id
            document["payload"] = {
                "submission_attempt_id": self.attempt_id,
                "broker_order_id": "opaque-broker-id",
                "cumulative_quantity": "3",
                "average_price": "227.50",
                "cumulative_fees": "0",
                "evidence": self.evidence(),
            }
        if kind == "rejected":
            document["order_id"] = self.order_id
            document["payload"] = {"source": "execution_guard", "reason_code": "stale_quote"}
        if kind == "unknown":
            document["order_id"] = self.order_id
            document["payload"] = {
                "submission_attempt_id": self.attempt_id,
                "reason_code": "acknowledgement_missing",
            }
        return document

    @staticmethod
    def evidence():
        return {
            "uri": "s3://ripple-audit/events/acknowledgement.json",
            "sha256": "a" * 64,
        }

    def test_events_are_deeply_immutable_and_detached_from_input(self):
        document = self.valid_document("broker_acknowledged")
        event = ExecutionEvent.from_dict(document)
        document["payload"]["evidence"]["uri"] = "s3://changed"

        self.assertEqual(
            event.payload["evidence"]["uri"],
            "s3://ripple-audit/events/acknowledgement.json",
        )
        with self.assertRaises(TypeError):
            event.payload["new_order"] = "forbidden"
        serialized = event.to_dict()
        serialized["payload"]["evidence"]["uri"] = "s3://changed"
        self.assertEqual(
            event.payload["evidence"]["uri"],
            "s3://ripple-audit/events/acknowledgement.json",
        )

    def test_valid_kind_specific_payloads_are_accepted(self):
        for kind in (
            "planned", "aborted", "scaled", "clipped", "submission_started",
            "broker_acknowledged", "partially_filled", "filled", "rejected", "unknown",
        ):
            with self.subTest(kind=kind):
                self.assertEqual(ExecutionEvent.from_dict(self.valid_document(kind)).kind, kind)
        broker_rejection = self.valid_document("rejected")
        broker_rejection["payload"] = {
            "source": "broker",
            "reason_code": "broker_rejected",
            "submission_attempt_id": self.attempt_id,
            "evidence": self.evidence(),
        }
        self.assertEqual(ExecutionEvent.from_dict(broker_rejection).kind, "rejected")

    def test_envelope_kind_and_order_level_rules_fail_closed(self):
        documents = []

        extra = self.valid_document()
        extra["metadata"] = {}
        documents.append(extra)

        unknown_kind = self.valid_document()
        unknown_kind["kind"] = "cancelled"
        documents.append(unknown_kind)

        planned_with_order = self.valid_document()
        planned_with_order["order_id"] = self.order_id
        documents.append(planned_with_order)

        missing_order = self.valid_document("unknown")
        missing_order["order_id"] = None
        documents.append(missing_order)

        for document in documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    ExecutionEvent.from_dict(document)

    def test_payload_allowlists_and_adjustment_comparisons_fail_closed(self):
        documents = []

        nonempty_planned = self.valid_document()
        nonempty_planned["payload"] = {"symbol": "AAPL"}
        documents.append(nonempty_planned)

        for field in ("symbol", "side", "order_type", "new_order"):
            forbidden_order_instruction = self.valid_document("unknown")
            forbidden_order_instruction["payload"][field] = "forbidden"
            documents.append(forbidden_order_instruction)

        for actual_value in ("12", "13", "0", "-1"):
            invalid_adjustment = self.valid_document("scaled")
            invalid_adjustment["payload"]["actual_value"] = actual_value
            documents.append(invalid_adjustment)

        for document in documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    ExecutionEvent.from_dict(document)

    def test_financial_values_must_be_decimal_strings(self):
        documents = []
        for value in (12.0, 12, "12%", "not-a-decimal", "1e3"):
            invalid_adjustment = self.valid_document("clipped")
            invalid_adjustment["payload"]["actual_value"] = value
            documents.append(invalid_adjustment)

        for document in documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    ExecutionEvent.from_dict(document)

    def test_submission_acknowledgement_rejection_and_fill_rules_fail_closed(self):
        documents = []

        started_with_broker_id = self.valid_document("submission_started")
        started_with_broker_id["payload"]["broker_order_id"] = "opaque-broker-id"
        documents.append(started_with_broker_id)

        for field in ("submission_attempt_id", "broker_order_id", "evidence"):
            acknowledgement = self.valid_document("broker_acknowledged")
            del acknowledgement["payload"][field]
            documents.append(acknowledgement)

        for field in ("submission_attempt_id", "evidence"):
            broker_rejection = self.valid_document("rejected")
            broker_rejection["payload"] = {
                "source": "broker",
                "reason_code": "broker_rejected",
                "submission_attempt_id": self.attempt_id,
                "evidence": self.evidence(),
            }
            del broker_rejection["payload"][field]
            documents.append(broker_rejection)

        local_rejection = self.valid_document("rejected")
        local_rejection["payload"]["broker_order_id"] = "opaque-broker-id"
        documents.append(local_rejection)

        for field in ("cumulative_quantity", "average_price", "cumulative_fees", "evidence"):
            fill = self.valid_document("filled")
            del fill["payload"][field]
            documents.append(fill)

        for field, value in (
            ("cumulative_quantity", "0"),
            ("average_price", "0"),
            ("cumulative_fees", "-1"),
        ):
            fill = self.valid_document("filled")
            fill["payload"][field] = value
            documents.append(fill)

        for document in documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    ExecutionEvent.from_dict(document)

    def test_unknown_cannot_authorize_retry_or_identify_a_broker_order(self):
        for field, value in (
            ("broker_order_id", "opaque-broker-id"),
            ("retry_allowed", True),
            ("new_order", "BUY AAPL"),
        ):
            document = self.valid_document("unknown")
            document["payload"][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    ExecutionEvent.from_dict(document)

    def test_evidence_must_be_a_credential_free_uri_and_hash_pointer(self):
        documents = []
        for uri in (
            "https://audit.example/event.json?token=secret",
            "https://audit.example/event.json#fragment",
            "https://user:secret@audit.example/event.json",
        ):
            document = self.valid_document("filled")
            document["payload"]["evidence"]["uri"] = uri
            documents.append(document)
        for digest in ("A" * 64, "a" * 63, "raw broker response"):
            document = self.valid_document("filled")
            document["payload"]["evidence"]["sha256"] = digest
            documents.append(document)
        raw_response = self.valid_document("filled")
        raw_response["payload"]["evidence"]["broker_response"] = {"order": "raw"}
        documents.append(raw_response)

        for document in documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    ExecutionEvent.from_dict(document)

    def test_direct_construction_cannot_bypass_validation(self):
        with self.assertRaises(TypeError):
            ExecutionEvent()


if __name__ == "__main__":
    unittest.main()
