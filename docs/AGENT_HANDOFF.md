# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-28 18:22 PDT — OrderPlan Trading Day ID collision fixed

- Outcome: future stable OrderPlan IDs now derive from Account Lane plus frozen Trading Day, preventing a same-date manual cycle from colliding with that evening's next-session cycle.
- Evidence: [`mvp.py`](../ripple/mvp.py) uses validated `trade_date`; [`test_mvp_cycle.py`](../tests/test_mvp_cycle.py) reproduces distinct August 27/28 cycles.
- Verification: the regression failed with identical IDs before the fix and passed afterward; 91/91 core tests passed.
- Next/risk: historical IDs remain immutable; future normal next-session IDs change once because their seed now matches cycle identity.

## 2026-08-28 20:51 PDT — Scheduled Live direct placement approved

- Outcome: the designated owner granted standing Scheduled Live authority to place each exact deterministic broker action once without Robinhood review or per-order confirmation; explicit manual runs receive equivalent one-cycle authority.
- Safety: immutable-plan and account binding, fresh facts, deterministic risk, stable-ID duplicate checks, the small-canary allocation, exact arguments, and stop-without-retry ambiguity handling remain mandatory.
- Evidence: [`EXECUTION_LIVE.md`](../routines/EXECUTION_LIVE.md), [`DECISIONS.md`](DECISIONS.md), and [`RUNBOOK.md`](RUNBOOK.md) define the boundary.
- Verification/next: 91/91 tests and catalog/live-cohort checks passed; the next eligible Scheduled Live action may place automatically, while any failed precondition still stops the run.

## 2026-08-30 18:06 PDT — Account A scheduled Live Decision published

- Outcome: scheduled Live Decision published [`OrderPlan`](../state/accounts/account_a/trading_days/2026-08-31/order_plan.json) `b207a602-0de2-5111-a413-5322dbb7ccb3`; no Execution or broker write occurred.
- Decision: retain JPM at 10%, target V at 10%, and cash at 80%; proposed BUY is `0.261` V LIMIT `$383.50`, with `$393.048` opening-gap cancellation.
- Evidence: the co-located [`DecisionSnapshot`](../state/accounts/account_a/trading_days/2026-08-31/decision_snapshot.json) freezes complete 2026-08-28 compiled facts, holding review, top-three research, and account baseline.
- Verification/risk: 91/91 tests, catalog, compact-artifact, diff, and credential checks passed; any broker action remains separate Live Execution work.
