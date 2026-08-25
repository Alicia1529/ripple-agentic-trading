# Hosted Schedule

The current hosted path is Account A only. Configure exactly one Decision Routine and one Execution Routine:

| Routine | Trigger | Prompt |
|---|---|---|
| Account A Decision | Sunday–Thursday at 9:00 PM `America/New_York` | Account A + `routines/DECISION.md` |
| Account A Execution | Weekdays at 9:35 AM `America/New_York` | Account A + `routines/EXECUTION.md` |

If the hosted scheduler cannot express an IANA timezone, trigger in a wider UTC window and retain the prompt's `America/New_York` self-check. Do not configure overlapping copies. Missed cycles are not backfilled.

Account A passes hosted dry-run acceptance after one observed scheduled Day T Decision Routine and Day T+1 Execution Routine. Switching it to live requires separate implementation of the reviewed MCP call loop plus Alicia's explicit change of its `execution.mode`; these prompts do not authorize it.

Account B remains a fixture-backed repository lane. It has no hosted Decision schedule, Execution schedule, or bound MCP path.

For Account A, an explicit Alicia-initiated **Run now** may use `publish-decision --manual-run` outside the Decision window in either `dry_run` or `live`. `execute-dry-run --manual-run` remains the immediate no-write rehearsal. After the reviewed live MCP call loop is implemented and Alicia enables it, Run now may trigger that same live Execution Routine outside its window. Manual and scheduled triggers are not last-write-wins: the first successful execution wins, and a later trigger must stop.
