# Hosted schedule

Configure exactly four non-overlapping cohort triggers:

| Routine | Selection | Trigger | Prompt |
|---|---|---|---|
| Live Decision | zero or one `live` account | Sunday–Thursday 9:00 PM `America/New_York` | `routines/DECISION_LIVE.md` |
| Shadow Decision | all `shadow` accounts | Sunday–Thursday 9:00 PM `America/New_York` | `routines/DECISION_SHADOW.md` |
| Live Execution | zero or one `live` account | Weekdays 9:35 AM `America/New_York` | `routines/EXECUTION_LIVE.md` |
| Shadow Execution | all `shadow` accounts | Weekdays 9:35 AM `America/New_York` | `routines/EXECUTION_SHADOW.md` |

Cron cannot express the NYSE calendar, so the Sunday–Thursday and weekday triggers stay as configured and each routine self-checks. A Decision evening that does not precede a trading day, and an Execution morning without a regular session, are successful no-ops: they publish and execute nothing and report the closed session. Expect one such no-op around every market holiday.

Every trigger validates the full catalog before selecting its cohort. A live run with no account is a successful no-op. Dry-run accounts are never scheduled. Triggers never automatically backfill missed cycles; a designated-owner historical Decision and any following Execution are separate manual operations.

If the scheduler cannot express an IANA timezone, trigger within a wider UTC window and retain each routine's `America/New_York` self-check. Do not configure overlapping copies of the same cohort phase.

Hosted shadow acceptance requires one reviewed Day T → T+1 cycle for every selected shadow lane. A live trigger with an empty cohort remains a successful no-op, and the live Execution prompt remains a stop contract until the broker loop and Live Gate tasks in `docs/TODO.md` are complete.
