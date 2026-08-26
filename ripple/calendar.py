"""The NYSE trading calendar shared by Decision timing, Execution timing, and replay.

Ripple is a T+1 system: a prior-evening Decision targets the next `America/New_York`
regular session. "Next weekday" is not that session, so the calendar is checked-in
data rather than a weekday arithmetic rule.

The tables below are transcribed from the NYSE published holiday and early-closings
calendar and cover `COVERAGE_START`..`COVERAGE_END` only. A query outside that range
raises instead of extrapolating, so an uncovered date fails closed (invariant 5)
rather than silently resolving to a weekday that may not be a session.

Extending coverage is a data review, not a code change: add the published closures
for the new years and move `COVERAGE_END`. Any backward extension must also include
unscheduled closures, which follow no observance rule -- for example the 2025-01-09
national day of mourning and the 2012-10-29/30 storm closures. An unscheduled
closure announced inside the covered range is added the same way, by a designated-
owner commit; `--manual-run` remains the timing escape hatch until it lands.
"""

from datetime import date, timedelta


_ONE_DAY = timedelta(days=1)

COVERAGE_START = date(2026, 1, 1)
COVERAGE_END = date(2027, 12, 31)

# Full closures. No regular session exists on these dates.
_FULL_CLOSURES = frozenset({
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King, Jr. Day
    date(2026, 2, 16),   # Washington's Birthday
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth National Independence Day
    date(2026, 7, 3),    # Independence Day observed
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving Day
    date(2026, 12, 25),  # Christmas Day
    date(2027, 1, 1),    # New Year's Day
    date(2027, 1, 18),   # Martin Luther King, Jr. Day
    date(2027, 2, 15),   # Washington's Birthday
    date(2027, 3, 26),   # Good Friday
    date(2027, 5, 31),   # Memorial Day
    date(2027, 6, 18),   # Juneteenth observed
    date(2027, 7, 5),    # Independence Day observed
    date(2027, 9, 6),    # Labor Day
    date(2027, 11, 25),  # Thanksgiving Day
    date(2027, 12, 24),  # Christmas Day observed
})

# Sessions that close at 1:00 PM instead of 4:00 PM. These are trading days and the
# 9:30-9:50 AM Execution window is unaffected, so no timing check consumes them.
# They are recorded because they come from the same published calendar and the same
# human review, and a reader asking whether a half day changes the schedule needs
# the answer here rather than in a second data review.
EARLY_CLOSE_DAYS = frozenset({
    date(2026, 11, 27),  # day after Thanksgiving
    date(2026, 12, 24),  # Christmas Eve
    date(2027, 11, 26),  # day after Thanksgiving
})


class NoTradingSession(ValueError):
    """A required `America/New_York` regular session does not exist.

    Distinct from a malformed or out-of-window timestamp: the input is well
    formed and the market is simply closed. A scheduled Routine reports this as
    a successful no-op; every other caller still fails closed.
    """


def _covered(day: date) -> date:
    if not COVERAGE_START <= day <= COVERAGE_END:
        raise ValueError(
            f"{day.isoformat()} is outside the checked-in NYSE calendar coverage "
            f"{COVERAGE_START.isoformat()}..{COVERAGE_END.isoformat()}"
        )
    return day


def is_trading_day(day: date) -> bool:
    """Return whether `day` has a regular `America/New_York` session."""
    return _covered(day).weekday() < 5 and day not in _FULL_CLOSURES


def next_trading_day(day: date) -> date:
    """Return the first trading day strictly after `day`."""
    candidate = day + _ONE_DAY
    while not is_trading_day(candidate):
        candidate += _ONE_DAY
    return candidate
