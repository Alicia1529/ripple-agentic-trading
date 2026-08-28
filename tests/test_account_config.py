import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AccountCatalogTests(unittest.TestCase):
    def test_cycle_profile_defaults_validates_and_selects_deterministically(self):
        from ripple.account_config import load_account_catalog

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_dir = root / "config"
            strategy_dir = root / "strategies"
            config_dir.mkdir()
            strategy_dir.mkdir()
            (strategy_dir / "exists.md").write_text("# Existing strategy\n")
            base = json.loads((ROOT / "config" / "account_b.json").read_text())
            base["strategy"] = "exists"
            base["universe"] = ["AAPL"]
            (config_dir / "z_lane.json").write_text(json.dumps(base))
            same_close = json.loads(json.dumps(base))
            same_close["execution"]["cycle_profile"] = "same_session_close"
            (config_dir / "a_lane.json").write_text(json.dumps(same_close))

            catalog = load_account_catalog(config_dir, strategy_dir)
            self.assertEqual(catalog.for_mode("shadow")[1].cycle_profile, "next_session_open")
            self.assertEqual(
                [config.account_id for config in catalog.for_schedule(
                    "shadow", "same_session_close",
                )],
                ["a_lane"],
            )

            same_close["execution"]["cycle_profile"] = "closing_bell"
            (config_dir / "a_lane.json").write_text(json.dumps(same_close))
            with self.assertRaisesRegex(ValueError, "cycle_profile"):
                load_account_catalog(config_dir, strategy_dir)

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

    def test_repository_scheduled_cohorts_are_profile_isolated(self):
        from ripple.account_config import load_account_catalog

        catalog = load_account_catalog(ROOT / "config", ROOT / "strategies")

        self.assertEqual(
            [config.account_id for config in catalog.for_schedule(
                "shadow", "next_session_open",
            )],
            ["account_b"],
        )
        self.assertEqual(
            [config.account_id for config in catalog.for_schedule(
                "shadow", "same_session_close",
            )],
            ["account_c"],
        )
        account_b = next(config for config in catalog if config.account_id == "account_b")
        account_c = next(config for config in catalog if config.account_id == "account_c")
        self.assertEqual(account_b.strategy_id, "earnings_drift_v2")
        strategy_text = account_b.strategy_path.read_text()
        self.assertNotIn("`sue`", strategy_text)
        self.assertIn(
            "Rank passing candidates by `eps_surprise_pct` descending",
            strategy_text,
        )
        self.assertEqual(account_c.strategy_id, "closing_momentum_v1")
        self.assertEqual(account_c.shadow_initial_cash, account_b.shadow_initial_cash)
        self.assertEqual(account_c.universe, account_b.universe)
        self.assertEqual(account_c.risk, account_b.risk)

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
