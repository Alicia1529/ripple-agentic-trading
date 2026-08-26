import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AccountCatalogTests(unittest.TestCase):
    def test_repository_catalog_loads_all_config_files(self):
        from ripple.account_config import load_account_catalog

        catalog = load_account_catalog(ROOT / "config", ROOT / "strategies")
        config_paths = sorted((ROOT / "config").glob("*.json"))

        self.assertEqual(
            [config.account_id for config in catalog],
            [path.stem for path in config_paths],
        )
        for config in catalog:
            self.assertTrue(config.description)
            self.assertTrue(config.strategy_path.is_file())
            self.assertIn(config.mode, {"live", "shadow", "dry_run"})
            self.assertTrue(config.universe)

    def test_missing_strategy_and_second_live_config_fail_catalog_validation(self):
        from ripple.account_config import load_account_catalog

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_dir = root / "config"
            strategy_dir = root / "strategies"
            config_dir.mkdir()
            strategy_dir.mkdir()
            (strategy_dir / "exists.md").write_text("# Existing strategy\n")
            base = {
                "description": "Test account lane.",
                "strategy": "exists",
                "execution": {"mode": "live"},
                "universe": ["AAPL"],
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
            (config_dir / "account_a.json").write_text(json.dumps(base))
            second = json.loads(json.dumps(base))
            (config_dir / "account_b.json").write_text(json.dumps(second))

            with self.assertRaisesRegex(ValueError, "at most one live"):
                load_account_catalog(config_dir, strategy_dir)

            (config_dir / "account_b.json").unlink()
            missing = json.loads(json.dumps(base))
            missing["strategy"] = "missing"
            (config_dir / "account_a.json").write_text(json.dumps(missing))

            with self.assertRaisesRegex(ValueError, "strategy does not exist"):
                load_account_catalog(config_dir, strategy_dir)

    def test_shadow_config_requires_initial_cash_and_snake_case_identifier(self):
        from ripple.account_config import load_account_catalog

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_dir = root / "config"
            strategy_dir = root / "strategies"
            config_dir.mkdir()
            strategy_dir.mkdir()
            (strategy_dir / "exists.md").write_text("# Existing strategy\n")
            config = {
                "description": "Test shadow lane.",
                "strategy": "exists",
                "execution": {"mode": "shadow"},
                "universe": ["AAPL"],
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
            (config_dir / "Account-B.json").write_text(json.dumps(config))

            with self.assertRaisesRegex(ValueError, "snake_case"):
                load_account_catalog(config_dir, strategy_dir)

            (config_dir / "Account-B.json").rename(config_dir / "account_b.json")
            with self.assertRaisesRegex(ValueError, "initial_cash"):
                load_account_catalog(config_dir, strategy_dir)


if __name__ == "__main__":
    unittest.main()
