# Why Ripple uses prior-evening Decision and T+1 morning Execution

> **Status:** This note explains the existing schedule. It is not an architecture decision, schedule-change proposal, Strategy Spec, or authorization to trade. The implemented contract remains a prior-evening Decision followed by next-weekday Execution at about 9:35 AM ET.

## Existing schedule and conclusion

Ripple already uses the first of these four timing patterns for the two checked-in policies, [Growth Momentum v3](../strategies/growth_momentum_v3.md) and [Earnings Drift v1](../strategies/earnings_drift_v1.md):

1. T evening after close: completed-session reevaluation, research, and plan; T+1 at 9:35 AM: deterministic market confirmation and Execution. The comparison used 6:00 PM, while the checked-in trigger is around 9:00 PM.
2. The same T Decision; T+1 Execution at noon.
3. The same T Decision; T+1 Execution at 3:00 PM.
4. T at 3:00 PM: research, plan, and same-day Execution.

The checked-in schedule expresses scheme 1 as a Decision around **9:00 PM ET** and deterministic confirmation and Execution around **9:35 AM ET on T+1**. This note explains why that existing separation fits both strategies better than the later or same-session alternatives. It does not establish that 9:35 produces better investment returns; that empirical question requires shadow observations.

| Scheme | Growth Momentum v3 | Earnings Drift v1 | Fit with current Ripple contract |
|---|---|---|---|
| 1 — T evening → T+1 9:35 AM | Best fit | Best fit; prefer later evening Decision | Implemented timing contract |
| 2 — T evening → T+1 noon | Signal may survive, but price anchor is older | Loses part of the early event window | Not implemented |
| 3 — T evening → T+1 3:00 PM | Weak fit; strongest names may already have escaped the limit | Weak fit; almost a full session of event response precedes entry | Not implemented |
| 4 — T 3:00 PM research/plan/execution | Incompatible with completed-session inputs | Incompatible with completed-session event accounting | Violates current Decision/Execution separation |

## Why the existing schedule fits the strategies

Growth Momentum v3 is a medium-horizon trend and quality policy. It ranks securities from completed daily bars, a 50-session average, 60-to-10-session momentum, relative momentum, volatility, and quarterly fundamentals. The original momentum study documents continuation over **3- to 12-month holding periods**, which supports treating the signal as slower than an intraday signal, although Ripple's exact formulas are its own policy rather than a reproduction of that study ([Jegadeesh and Titman, 1993](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x)).

The Strategy Spec nevertheless makes the execution time consequential. Every order is anchored to T's completed-session close. A BUY limit is only 0.5%–2% above that close, and Execution must reject a BUY when the actual T+1 regular-session open is more than 3% above it. Executing at 9:35 uses the specified opening fact shortly after the 9:30 auction while the prior close remains a relatively recent anchor. NYSE identifies 9:30 AM–4:00 PM ET as its Core Trading Session and 9:30 as the Core Open Auction ([NYSE trading information](https://www.nyse.com/trade/trading-information)).

Earnings Drift v1 is an event-driven post-earnings-announcement-drift policy. It admits candidates only one through three completed sessions after the report, requires positive EPS and revenue surprises plus a 2%–15% initial reaction, and plans exits over as many as 30 sessions. The original PEAD paper examines continued price response after an earnings announcement; this supports the post-announcement premise, but it does not by itself establish that 9:35 is optimal for Ripple's implementation ([Bernard and Thomas, 1989](https://www.jstor.org/stable/2491062)). Within Ripple's narrow one-to-three-session entry window, earlier T+1 execution preserves more of the intended post-event interval than noon or 3:00 PM.

The checked-in 9:00 PM Decision is particularly useful for Earnings Drift. Its research must evaluate guidance, the repeatability of management's stated driver, and operating indicators. At an earlier cutoff such as 6:00 PM, the complete release, filing, prepared remarks, or call evidence needed for those questions may not yet be available. This is an operational inference from the policy's evidence requirements, not a claim that every issuer reports late. The existing later-evening schedule gives the routine more opportunity to collect complete primary-source evidence. Missing evidence must still fail closed; a later clock time cannot justify guessing.

## Why noon and 3:00 PM are weaker

Schemes 2 and 3 retain the slow signal, but they do not retain the same execution experiment. The published limits and gap thresholds remain frozen against T's close while the market has traded for roughly 2.5 or 5.5 hours. A later quote is therefore evaluated against an increasingly stale anchor.

This can create adverse fill selection. A strong momentum or earnings-drift candidate may move above the BUY limit early and never fill; a candidate that weakens intraday may fall back inside the limit and fill later. The resulting portfolio may systematically omit the strongest continuations while accepting more intraday reversals. This is an inference from the Specs' frozen LIMIT construction, not a universal property of limit orders. The SEC explains the mechanical tradeoff: a limit order constrains price but does not guarantee execution, and it executes only if the market reaches the specified limit ([SEC, *Trading Basics*](https://www.sec.gov/tm/investor-alerts-bulletins/trading101basics.pdf)).

The issue is sharper for Earnings Drift because the policy intentionally enters near the event. Noon discards the first half of T+1; 3:00 PM discards almost the whole regular session. Growth Momentum is less time-sensitive at the signal level, but its narrow prior-close BUY band and opening-gap cancellation still make 9:35 the cleanest match to the authored order semantics.

## Why Scheme 4 is incompatible

At 3:00 PM on T, the regular session has not completed. NYSE's regular close is 4:00 PM ET, so daily close, completed OHLC bar, session return, and session count are not final. Growth Momentum explicitly requires completed, non-interpolated regular-session bars and uses the latest completed close as its reference price. Earnings Drift uses the latest completed-session close and counts completed sessions since the report. Substituting a 3:00 PM snapshot would silently create new intraday definitions and should require new versioned Strategy Specs rather than reinterpretation of the existing ones.

Scheme 4 also collapses Decision and Execution. [Invariant 1](INVARIANTS.md) forbids Decision sessions from using execution capability; [Invariant 4](INVARIANTS.md) keeps Execution narrow and prohibits a new thesis; and [Invariant 6](INVARIANTS.md) requires honest prior-evening Decision and next-weekday fill semantics. The [architecture](ARCHITECTURE.md#overnight-boundary) freezes the published plan across the overnight boundary. Same-session research, planning, and trading would invalidate those controls, not merely adjust a schedule.

## What “market confirmation” may do

T+1 confirmation must remain deterministic and execution-only. It may:

- read the current quote and test planned LIMIT marketability;
- read the actual regular-session open and apply the frozen gap rule;
- revalidate account identity, baseline, cash, holdings, quote freshness, and deterministic risk limits; and
- stop on stale, missing, malformed, mismatched, halted, or otherwise unsafe input.

It may **not** perform new issuer research, change the thesis, replace a candidate, alter target weights, widen a limit, chase price, or publish a revised plan. Those actions belong to a new Decision Cycle. This boundary follows [Invariants 2, 4, and 5](INVARIANTS.md) and the [next-weekday Execution contract](ARCHITECTURE.md#next-weekday-execution).

## Implication and validation

No schedule change follows from this analysis. The current prior-evening Decision and 9:35 AM T+1 Execution remain the canonical contract. Growth Momentum could tolerate an earlier research start, but Earnings Drift should not publish until its required evidence is complete. If that evidence is unavailable by the cutoff, publish no BUY rather than defer research into Execution.

Before considering a schedule change, run a shadow-only observation study. For each single frozen OrderPlan, retain 9:35 as the **only canonical Execution** and record credential-free, non-authoritative observation quotes at noon and 3:00 PM. Those observations must not invoke risk a second time, create fills, mutate cash or positions, generate additional execution records, or revise the plan. Compare planned-limit marketability, distance from T's close and frozen limit, opening-gap outcomes, and later 5-/20-session returns by strategy and event age. This would measure timing sensitivity without manufacturing three mutually inconsistent executions from one plan.

Implementing even observation-only artifacts requires a separately reviewed schema/state change. Changing canonical Execution away from 9:35, or permitting a 3:00 PM Decision, would additionally require an approved durable architecture decision and, for Scheme 4, new Strategy Spec versions because the completed-session meaning changes.
