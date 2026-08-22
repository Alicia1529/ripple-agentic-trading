# Runbook

Operational procedures. This is written ahead of implementation, as part of the spec for what needs to be built — update it as the real system's behavior diverges from what's described here.

## Kill switch

There is no broker-provided instant "flatten everything" capability (see `docs/ARCHITECTURE.md` "Risk layer" for why). The kill switch here means:

1. Flip a config flag (e.g. `execution.mode` for the affected account, or a global flag) — this must be a value only a human ever changes; no code path in either the Decision or Execution stage may write to it.
2. Next Decision Run: no new OrderPlan is generated for that account.
3. Next Execution Run: all pending orders for that account are cancelled; no new orders are submitted.
4. Existing positions are **not** instantly liquidated — they still need normal sell orders to unwind. If an immediate exit is wanted, that's a manual trade placed by the human, not something the system does automatically on kill-switch flip.

## What to do when notified

The system should only ever notify for the events below. If something else is generating notifications, that's itself a bug worth investigating — see "Unexpected notification" at the bottom.

| Notification | What it means | What to do |
|---|---|---|
| Drawdown tier 1 (−10%) on an account | New positions blocked for that account | Review recent decisions/fills for that account at your own pace; no action required unless something looks wrong |
| Drawdown tier 2 (−15%) on an account | That account has shut down, needs manual restart | Review what happened before restarting; the other account and the shadow pool are unaffected and kept running |
| Shadow candidate cleared the graduation gate (D5a) | 8+ weeks, beat both benchmarks, no execution bugs | Decide by hand whether to fund a new live account for it — this is a real financial decision, take the time it needs |
| "Today's scheduled run didn't happen" | A Decision or Execution Run was skipped or failed | Check the relevant scheduler (Claude Code routine / Codex Automation / GitHub Actions) logs; the missed cycle is not backfilled — the system waits for the next normal cycle |
| Account state reconciliation mismatch | Positions/cash don't match what was expected | Investigate before the next Execution Run proceeds for that account — this should be rare and worth understanding, not just clearing |
| Wash-sale block | A buy was blocked because it would trigger a wash sale | No action needed unless you disagree with the block; it's logged for tax records either way |

**Unexpected notification** — anything not in the table above, or anything that recurs when it should be rare: treat it as a signal something in the design or implementation is wrong, not routine noise to dismiss.

## Deploy

Not yet implemented — this section will describe:

- First-time setup for each of the three schedulers (Claude Code cloud routine for Account A, Codex cloud Automation for Account B, GitHub Actions for the shadow pool + both accounts' Execution Run).
- Where credentials live for each (env vars / GitHub Actions secrets / each cloud scheduler's own secret store) — never in the repo.
- How to point a fresh deployment at a new Robinhood Agentic account without touching the shared pipeline code.

## Debug

Not yet implemented — this section will describe how to replay a specific day's chain from the frozen `DecisionSnapshot`, immutable `OrderPlan`, transactional `ExecutionEvents`, and referenced audit objects; and how to distinguish "the call was wrong" from "the price moved before execution" using the decision/execution timestamps.

## Recovery

Not yet implemented — this section will describe what to do after a crashed or partially-completed Execution Run and how to confirm recovery before the next cycle. Per D16, `submission_started` without `broker_acknowledged` is an unknown outcome: query broker history, append a reconciliation result, and resume only if the outcome is proven. Unresolved ambiguity keeps that account blocked and requires human review; it never triggers a blind resubmission.
