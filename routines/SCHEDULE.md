# Hosted Schedule

Configure exactly two enabled routines for production v1:

| Routine | Trigger | Prompt |
|---|---|---|
| Decision | Weekdays at 9:00 PM `America/New_York` | `routines/DECISION.md` |
| Execution | Weekdays at 9:35 AM `America/New_York` | `routines/EXECUTION.md` |

If the hosted scheduler cannot express an IANA timezone, trigger in a wider UTC window and retain the prompt's `America/New_York` self-check. Do not configure overlapping copies. Missed cycles are not backfilled.

The dry-run MVP is complete after one observed scheduled Day T Decision Routine and Day T+1 Execution Routine. Switching to live requires separate implementation of the reviewed MCP call loop plus Alicia's explicit change of `execution.mode`; these prompts do not authorize it.
