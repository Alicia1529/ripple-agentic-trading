import unittest

from ripple.decision_snapshot import DecisionSnapshot


class DecisionSnapshotTests(unittest.TestCase):
    def valid_document(self):
        return {
            "snapshot_id": "d44c4279-6d02-4773-a888-f906fb738aae",
            "as_of": "2026-08-22T21:00:00-04:00",
            "universe": ["AAPL", "MSFT"],
            "inputs": {"market": {"AAPL": {"close": "226.40"}}},
        }

    def test_snapshot_is_deeply_immutable_and_detached_from_input(self):
        document = {
            "snapshot_id": "d44c4279-6d02-4773-a888-f906fb738aae",
            "as_of": "2026-08-22T21:00:00-04:00",
            "universe": ["AAPL", "MSFT"],
            "inputs": {
                "market": {"AAPL": {"close": "226.40"}},
                "news": [{"source": "example", "headline": "fixture"}],
            },
        }

        snapshot = DecisionSnapshot.from_dict(document)
        document["universe"].append("NVDA")
        document["inputs"]["market"]["AAPL"]["close"] = "999.99"

        self.assertEqual(snapshot.universe, ("AAPL", "MSFT"))
        self.assertEqual(snapshot.inputs["market"]["AAPL"]["close"], "226.40")
        with self.assertRaises(TypeError):
            snapshot.inputs["market"]["AAPL"]["close"] = "1.00"
        self.assertEqual(
            snapshot.to_dict(),
            {
                "snapshot_id": "d44c4279-6d02-4773-a888-f906fb738aae",
                "as_of": "2026-08-22T21:00:00-04:00",
                "universe": ["AAPL", "MSFT"],
                "inputs": {
                    "market": {"AAPL": {"close": "226.40"}},
                    "news": [{"source": "example", "headline": "fixture"}],
                },
            },
        )

    def test_malformed_snapshot_documents_fail_closed(self):
        invalid_documents = []

        extra = self.valid_document()
        extra["credential"] = "must-not-be-ignored"
        invalid_documents.append(extra)

        bad_id = self.valid_document()
        bad_id["snapshot_id"] = "not-a-uuid"
        invalid_documents.append(bad_id)

        naive_time = self.valid_document()
        naive_time["as_of"] = "2026-08-22T21:00:00"
        invalid_documents.append(naive_time)

        duplicate_universe = self.valid_document()
        duplicate_universe["universe"] = ["AAPL", "AAPL"]
        invalid_documents.append(duplicate_universe)

        non_json_input = self.valid_document()
        non_json_input["inputs"] = {"symbols": {"AAPL"}}
        invalid_documents.append(non_json_input)

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    DecisionSnapshot.from_dict(document)

    def test_direct_construction_cannot_bypass_validation(self):
        with self.assertRaises(TypeError):
            DecisionSnapshot(
                snapshot_id="not-a-uuid",
                as_of="not-a-time",
                universe=("AAPL",),
                inputs={},
            )


if __name__ == "__main__":
    unittest.main()
