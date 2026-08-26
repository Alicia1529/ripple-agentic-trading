from datetime import date
import unittest

from ripple.calendar import (
    COVERAGE_END,
    COVERAGE_START,
    EARLY_CLOSE_DAYS,
    is_trading_day,
    next_trading_day,
)


class TradingCalendarTests(unittest.TestCase):
    def test_published_full_closures_are_not_trading_days(self):
        for closure in (
            date(2026, 1, 1),
            date(2026, 1, 19),
            date(2026, 2, 16),
            date(2026, 4, 3),
            date(2026, 5, 25),
            date(2026, 6, 19),
            date(2026, 7, 3),
            date(2026, 9, 7),
            date(2026, 11, 26),
            date(2026, 12, 25),
            date(2027, 1, 1),
            date(2027, 1, 18),
            date(2027, 2, 15),
            date(2027, 3, 26),
            date(2027, 5, 31),
            date(2027, 6, 18),
            date(2027, 7, 5),
            date(2027, 9, 6),
            date(2027, 11, 25),
            date(2027, 12, 24),
        ):
            with self.subTest(closure=closure):
                self.assertFalse(is_trading_day(closure))

    def test_weekends_and_ordinary_weekdays(self):
        self.assertFalse(is_trading_day(date(2026, 8, 22)))
        self.assertFalse(is_trading_day(date(2026, 8, 23)))
        self.assertTrue(is_trading_day(date(2026, 8, 24)))
        self.assertTrue(is_trading_day(date(2026, 8, 28)))

    def test_early_closes_remain_trading_days(self):
        for early_close in EARLY_CLOSE_DAYS:
            with self.subTest(early_close=early_close):
                self.assertTrue(is_trading_day(early_close))

    def test_next_trading_day_skips_holidays_and_weekends(self):
        # Labor Day 2026: Friday and the weekend hand off to Tuesday.
        self.assertEqual(next_trading_day(date(2026, 9, 4)), date(2026, 9, 8))
        self.assertEqual(next_trading_day(date(2026, 9, 6)), date(2026, 9, 8))
        # Thanksgiving 2026: Wednesday and the holiday hand off to Friday.
        self.assertEqual(next_trading_day(date(2026, 11, 25)), date(2026, 11, 27))
        self.assertEqual(next_trading_day(date(2026, 11, 26)), date(2026, 11, 27))
        # Christmas 2026 falls on Friday, so Thursday hands off to Monday.
        self.assertEqual(next_trading_day(date(2026, 12, 24)), date(2026, 12, 28))
        # An ordinary Friday hands off to Monday.
        self.assertEqual(next_trading_day(date(2026, 8, 21)), date(2026, 8, 24))

    def test_dates_outside_coverage_fail_closed(self):
        for uncovered in (
            date(COVERAGE_START.year - 1, 12, 31),
            date(COVERAGE_END.year + 1, 1, 1),
        ):
            with self.subTest(uncovered=uncovered):
                with self.assertRaisesRegex(ValueError, "outside the checked-in"):
                    is_trading_day(uncovered)

    def test_next_trading_day_fails_closed_at_the_coverage_edge(self):
        with self.assertRaisesRegex(ValueError, "outside the checked-in"):
            next_trading_day(COVERAGE_END)


if __name__ == "__main__":
    unittest.main()
