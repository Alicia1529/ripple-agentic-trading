import json
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ripple.growth_momentum import compile_growth_momentum_facts


ROOT = Path(__file__).resolve().parents[1]


class GrowthMomentumFactsTests(unittest.TestCase):
    def symbol(self, symbol, start, *, step="1"):
        bars = []
        start_date = date(2026, 4, 1)
        price = Decimal(start)
        increment = Decimal(step)
        session_date = start_date
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
        revenues = ["180", "160", "140", "120", "100", "100", "100", "100"]
        operating_cash_flow = ["50", "40", "30", "20", "15", "14", "13", "12"]
        period_dates = [
            "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30",
            "2025-06-30", "2025-03-31", "2024-12-31", "2024-09-30",
        ]
        financials = []
        for index in range(8):
            financials.append({
                "period_end_date": period_dates[index],
                "revenue": revenues[index],
                "gross_profit": str(Decimal(revenues[index]) / 2),
                "operating_cash_flow": operating_cash_flow[index],
                "capital_expenditures": "5",
            })
        return {
            "bars": bars,
            "financials": financials,
            "next_earnings_date": "2026-08-20",
            "sector": "Technology",
            "prices_source_url": f"https://example.com/{symbol}/prices",
            "financials_source_url": f"https://example.com/{symbol}/financials",
            "earnings_source_url": f"https://example.com/{symbol}/earnings",
        }

    def document(self):
        document = {
            "as_of": "2026-07-07",
            "symbols": {
                "AAPL": self.symbol("AAPL", "100", step="2"),
                "QQQ": self.symbol("QQQ", "200"),
                "SPY": self.symbol("SPY", "300"),
            },
        }
        for benchmark in ("SPY", "QQQ"):
            document["symbols"][benchmark]["financials"] = []
            document["symbols"][benchmark]["next_earnings_date"] = None
        return document

    def test_compiles_complete_deterministic_facts(self):
        result = compile_growth_momentum_facts(self.document())
        facts = result["facts"]["AAPL"]

        self.assertEqual(facts["close"], "238")
        self.assertEqual(facts["sma50"], "189")
        self.assertEqual(facts["mom_60_10"], "0.847457627118644067796610169")
        self.assertEqual(facts["atr20_pct"], "0.01680672268907563025210084034")
        self.assertEqual(facts["rel_mom_streak"], 0)
        self.assertEqual(facts["days_to_earnings"], 44)
        self.assertEqual(facts["rev_growth_yoy"], ["0.8", "0.6", "0.4", "0.2"])
        self.assertEqual(facts["gross_margin"], ["0.5"] * 4)
        self.assertEqual(facts["fcf_ttm"], "120")
        self.assertEqual(
            facts["fcf_trend"],
            {"quarterly": ["45", "35", "25", "15"], "improved_all_four_quarters": True},
        )
        self.assertGreater(Decimal(facts["risk_adj_mom"]), 0)
        self.assertEqual(
            result["provenance"]["AAPL"]["financials"],
            "https://example.com/AAPL/financials",
        )
        self.assertEqual(result["facts"]["SPY"]["asset_role"], "benchmark")
        self.assertNotIn("fcf_ttm", result["facts"]["SPY"])

    def test_missing_or_unsafe_raw_data_fails_closed(self):
        cases = []
        short = self.document()
        short["symbols"]["AAPL"]["bars"] = short["symbols"]["AAPL"]["bars"][:65]
        cases.append((short, "at least 66"))

        interpolated = self.document()
        interpolated["symbols"]["AAPL"]["bars"][20]["interpolated"] = True
        cases.append((interpolated, "interpolated"))

        missing_cash_flow = self.document()
        missing_cash_flow["symbols"]["AAPL"]["financials"][0]["operating_cash_flow"] = None
        cases.append((missing_cash_flow, "decimal string"))

        stale_earnings = self.document()
        stale_earnings["symbols"]["AAPL"]["next_earnings_date"] = "2026-07-07"
        cases.append((stale_earnings, "must be after"))

        negative_capex = self.document()
        negative_capex["symbols"]["AAPL"]["financials"][0]["capital_expenditures"] = "-5"
        cases.append((negative_capex, "positive outflow"))

        for document, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    compile_growth_momentum_facts(document)

    def test_relative_momentum_streak_is_capped_at_policy_threshold(self):
        document = self.document()
        document["symbols"]["AAPL"] = self.symbol("AAPL", "100", step="0.1")

        result = compile_growth_momentum_facts(document)

        self.assertEqual(result["facts"]["AAPL"]["rel_mom_streak"], 5)

    def test_cli_writes_new_credential_free_artifact(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "raw.json"
            output_path = root / "facts.json"
            input_path.write_text(json.dumps(self.document()))
            completed = subprocess.run(
                [
                    "python3.12", "-m", "ripple.growth_momentum",
                    "--input", str(input_path), "--output", str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(output_path.read_text())["as_of"], "2026-07-07")
            second = subprocess.run(
                [
                    "python3.12", "-m", "ripple.growth_momentum",
                    "--input", str(input_path), "--output", str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
