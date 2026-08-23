# Hosted Schedule

Configure exactly two routines per enabled account lane. Never combine accounts in one session:

| Routine | Trigger | Prompt |
|---|---|---|
| Account A Decision | Weekdays at 9:00 PM `America/New_York` | Account A + `routines/DECISION.md` |
| Account B Decision | Weekdays at 9:10 PM `America/New_York` | Account B + `routines/DECISION.md` |
| Account A Execution | Weekdays at 9:35 AM `America/New_York` | Account A + `routines/EXECUTION.md` |
| Account B Execution | Weekdays at 9:45 AM `America/New_York` | Account B + `routines/EXECUTION.md` |

If the hosted scheduler cannot express an IANA timezone, trigger in a wider UTC window and retain the prompt's `America/New_York` self-check. Do not configure overlapping copies. Missed cycles are not backfilled.

The ten-minute lane offset avoids normal Git pull/push collisions without adding a lock or coordinator. It is not a correctness lease; a delayed run still stops on a dirty tree, pull conflict, existing output, or stale plan.

Each lane passes hosted dry-run acceptance after one observed scheduled Day T Decision Routine and Day T+1 Execution Routine. Switching that lane to live requires separate implementation of the reviewed MCP call loop plus Alicia's explicit change of its `execution.mode`; these prompts do not authorize it.
