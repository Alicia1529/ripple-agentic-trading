import json
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ripple.growth_momentum_lite import compile_growth_momentum_lite_facts


ROOT = Path(__file__).resolve().parents[1]


class GrowthMomentumLiteFactsTests(unittest.TestCase):
    EXPECTED_SYMBOLS = ("AAPL", "QQQ", "SPY")

    def symbol(self, symbol, start, *, step="1"):
        bars = []
        session_date = date(2026, 4, 1)
        price = Decimal(start)
        increment = Decimal(step)
        for index in range(70):
            while session_date.weekday() >= 5:
                session_date += timedelta(days=1)
            close = price + increment * index
            bars.append({
                "date": session_date.isoformat(),
                "open": str(close - 1),
                "high": str(close + 2),
                "low": str(close - 2),
                "close": str(close),
                "interpolated": False,
            })
            session_date += timedelta(days=1)
        return {
            "bars": bars,
            "next_earnings_date": "2026-08-20",
            "sector": "Technology",
            "prices_source_url": f"https://example.com/{symbol}/prices",
            "sector_source_url": f"https://example.com/{symbol}/sector",
            "earnings_source_url": f"https://example.com/{symbol}/earnings",
        }

    def document(self):
        symbols = {
            "AAPL": self.symbol("AAPL", "100", step="2"),
            "QQQ": self.symbol("QQQ", "200"),
            "SPY": self.symbol("SPY", "300"),
        }
        for benchmark in ("SPY", "QQQ"):
            symbols[benchmark]["next_earnings_date"] = None
        return {
            "as_of": "2026-07-07",
            "expected_latest_session": symbols["SPY"]["bars"][-1]["date"],
            "retrieved_at": "2026-07-07T21:00:00-04:00",
            "symbols": symbols,
        }

    def test_compiles_compact_deterministic_facts(self):
        result = compile_growth_momentum_lite_facts(
            self.document(), self.EXPECTED_SYMBOLS,
        )
        facts = result["facts"]["AAPL"]

        self.assertEqual(facts["status"], "available")
        self.assertEqual(facts["close"], "238")
        self.assertEqual(facts["sma50"], "189")
        self.assertEqual(facts["mom_60_10"], "0.847457627118644067796610169")
        self.assertEqual(facts["atr20_pct"], "0.01680672268907563025210084034")
        self.assertEqual(facts["rel_mom_streak"], 0)
        self.assertEqual(facts["days_to_earnings"], 44)
        self.assertEqual(result["provenance"]["AAPL"]["accepted_bar_count"], 70)
        self.assertEqual(result["provenance"]["AAPL"]["interpolated_bar_count"], 0)
        self.assertEqual(result["retrieved_at"], "2026-07-07T21:00:00-04:00")

        encoded = json.dumps(result)
        self.assertNotIn('"bars"', encoded)
        self.assertNotIn('"open"', encoded)
        self.assertLess(len(encoded), 4_000)

    def test_missing_latest_session_is_compact_unavailable_evidence(self):
        document = self.document()
        document["symbols"]["AAPL"]["bars"][-1]["interpolated"] = True

        result = compile_growth_momentum_lite_facts(
            document, self.EXPECTED_SYMBOLS,
        )

        self.assertEqual(result["facts"]["AAPL"], {
            "asset_role": "security",
            "days_to_earnings": 44,
            "reason_code": "missing_latest_completed_session",
            "sector": "Technology",
            "status": "unavailable",
        })
        self.assertEqual(result["provenance"]["AAPL"]["accepted_bar_count"], 69)
        self.assertEqual(result["provenance"]["AAPL"]["interpolated_bar_count"], 1)

    def test_unavailable_qqq_marks_relative_facts_unavailable(self):
        document = self.document()
        document["symbols"]["QQQ"]["bars"][-1]["interpolated"] = True

        result = compile_growth_momentum_lite_facts(
            document, self.EXPECTED_SYMBOLS,
        )

        self.assertEqual(
            result["facts"]["AAPL"]["reason_code"], "qqq_facts_unavailable",
        )
        self.assertEqual(
            result["facts"]["SPY"]["reason_code"], "qqq_facts_unavailable",
        )
        self.assertEqual(
            result["facts"]["QQQ"]["reason_code"],
            "missing_latest_completed_session",
        )

    def test_interpolated_required_window_is_unavailable(self):
        document = self.document()
        document["symbols"]["AAPL"]["bars"][-3]["interpolated"] = True

        result = compile_growth_momentum_lite_facts(
            document, self.EXPECTED_SYMBOLS,
        )

        self.assertEqual(
            result["facts"]["AAPL"]["reason_code"],
            "interpolated_session_in_required_window",
        )

    def test_malformed_or_unsafe_input_fails_closed(self):
        cases = []
        invalid_price = self.document()
        invalid_price["symbols"]["AAPL"]["bars"][0]["close"] = "not-a-number"
        cases.append((invalid_price, "decimal string"))

        unordered = self.document()
        unordered["symbols"]["AAPL"]["bars"][1]["date"] = (
            unordered["symbols"]["AAPL"]["bars"][0]["date"]
        )
        cases.append((unordered, "ordered sessions"))

        unsafe_source = self.document()
        unsafe_source["symbols"]["AAPL"]["prices_source_url"] = "http://example.com"
        cases.append((unsafe_source, "https URL"))

        naive_retrieval = self.document()
        naive_retrieval["retrieved_at"] = "2026-07-07T21:00:00"
        cases.append((naive_retrieval, "timezone-aware"))

        for document, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    compile_growth_momentum_lite_facts(
                        document, self.EXPECTED_SYMBOLS,
                    )

    def test_input_symbols_must_exactly_match_configured_universe(self):
        document = self.document()
        del document["symbols"]["AAPL"]

        with self.assertRaisesRegex(ValueError, "configured universe"):
            compile_growth_momentum_lite_facts(document, self.EXPECTED_SYMBOLS)

    def test_cli_writes_new_compact_artifact(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "raw.json"
            output_path = root / "facts.json"
            config_path = root / "account_a.json"
            input_path.write_text(json.dumps(self.document()))
            config = json.loads((ROOT / "config" / "account_a.json").read_text())
            config["universe"] = list(self.EXPECTED_SYMBOLS)
            config_path.write_text(json.dumps(config))

            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.growth_momentum_lite",
                    "--config", str(config_path),
                    "--input", str(input_path), "--output", str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = output_path.read_text()
            self.assertNotIn('"bars"', output)
            self.assertEqual(json.loads(output)["as_of"], "2026-07-07")
            second = subprocess.run(
                [
                    "python3.12", "-m", "ripple.growth_momentum_lite",
                    "--config", str(config_path),
                    "--input", str(input_path), "--output", str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("exists", second.stderr)

    def test_complete_configured_universe_output_stays_compact(self):
        configured = json.loads((ROOT / "config" / "account_a.json").read_text())[
            "universe"
        ]
        symbols = {
            symbol: self.symbol(symbol, "100", step="1")
            for symbol in configured
        }
        for benchmark in ("SPY", "QQQ"):
            symbols[benchmark]["next_earnings_date"] = None
        document = {
            "as_of": "2026-07-07",
            "expected_latest_session": symbols["SPY"]["bars"][-1]["date"],
            "retrieved_at": "2026-07-07T21:00:00-04:00",
            "symbols": symbols,
        }

        result = compile_growth_momentum_lite_facts(document, configured)

        self.assertEqual(set(result["facts"]), set(configured))
        self.assertLess(len(json.dumps(result, indent=2)), 50_000)


if __name__ == "__main__":
    unittest.main()
