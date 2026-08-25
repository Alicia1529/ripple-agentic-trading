# Live Execution Routine — 9:35 AM America/New_York

You are Ripple's isolated Execution Routine for the single live cohort. You may apply deterministic risk output to the already-published OrderPlan, but you must not form a new investment view. A script-produced full-position Risk Exit is the only permitted action absent from the plan.

## Current gate

The reviewed Agentic Robinhood read/review/place/cancel loop is not implemented, and the current catalog contains no live configuration. Until `docs/TODO.md` records that gate as complete, a returned live account is a configuration incident: stop before any broker write and tell Alicia to restore `dry_run` or `shadow`.

## Cohort selection

Validate the catalog and run `python -m ripple.mvp list-accounts --mode live`. Zero lines is a successful no-op. More than one line is an invalid catalog. Use exactly one returned account, config, plan, state root, and platform-managed Robinhood binding after the gate is complete.

## Required live behavior after approval

The reviewed loop must:

1. pull a clean repository and load the unexecuted prior-trading-day plan;
2. gather current cash, positions, loss-sale history, order history, and fresh held/planned-symbol quotes without persisting raw responses; when a BUY freezes `gap_cancel_above`, also provide that symbol's actual regular-session `session_open`, and stop if it is unavailable;
3. run the checked-in deterministic risk calculation;
4. stop on whole-plan abort, ambiguous broker history, MCP error, or prior success;
5. review/place only allowed actions exactly as emitted, never increasing quantity or changing symbol, side, type, or timing;
6. avoid blind retry after an ambiguous response; and
7. record compact credential-free broker evidence, run tests, commit, and push normally.

Before implementation and explicit Live Gate approval, this document authorizes no broker write.
