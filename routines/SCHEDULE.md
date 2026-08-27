# Hosted schedule

Configure six non-overlapping cohort triggers:

| Routine | Selection | Trigger | Prompt |
|---|---|---|---|
| Live Decision | zero or one `live` account | Sunday–Thursday 9:00 PM `America/New_York` | `routines/DECISION_LIVE.md` |
| Shadow Decision | `shadow` + `next_session_open` | Sunday–Thursday 9:00 PM `America/New_York` | `routines/DECISION_SHADOW.md` |
| Live Execution | zero or one `live` account | Weekdays 9:35 AM `America/New_York` | `routines/EXECUTION_LIVE.md` |
| Shadow Execution | `shadow` + `next_session_open` | Weekdays 9:35 AM `America/New_York` | `routines/EXECUTION_SHADOW.md` |
| Close Shadow Decision | `shadow` + `same_session_close` | Weekdays 2:30 PM `America/New_York` | `routines/DECISION_SHADOW_CLOSE.md` |
| Close Shadow Execution | `shadow` + `same_session_close` | Weekdays 3:20 PM `America/New_York` | `routines/EXECUTION_SHADOW_CLOSE.md` |

Cron cannot express the NYSE calendar, so the Sunday–Thursday and weekday triggers stay as configured and each routine self-checks. A Decision evening that does not precede a trading day, an Execution morning without a regular session, and any close trigger on a closed or early-close session are successful no-ops: they publish and execute nothing and report the closed session.

Every trigger validates the full catalog before selecting its cohort. A live run with no account is a successful no-op. Dry-run accounts are never scheduled. Triggers never automatically backfill missed cycles; a designated-owner historical Decision and any following Execution are separate manual operations.

If the scheduler cannot express an IANA timezone, trigger within a wider UTC window and retain each routine's `America/New_York` self-check. Do not configure overlapping copies of the same cohort phase.

Hosted acceptance is profile-specific: `next_session_open` requires reviewable Day T → T+1 evidence, while `same_session_close` requires a same-date Decision → later Execution cycle using the actual Execution quote. A live trigger with an empty cohort remains a successful no-op; a selected live lane follows `EXECUTION_LIVE.md` under its deterministic, account-binding, duplicate, ambiguity, and owner-controlled allocation safeguards.
