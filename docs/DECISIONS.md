# Current effective decisions

Git history retains superseded reasoning. This file summarizes only decisions that govern the current release.

## Product and release

- Ripple compares isolated, strategy-attributed Account Lanes while keeping deterministic risk authority and human-owned live activation.
- Current Account Lane identity, mode, strategy, universe, and risk bindings are defined only by `config/*.json`; stable documentation does not duplicate that mutable deployment inventory.
- Initial live exposure remains $500–1000. The designated owner alone enables live mode, binds or funds the broker account, restarts a tier-two lock, switches the live strategy, or approves more capital.
- Live and shadow evidence can support a human review. No metric or threshold automatically promotes a strategy or changes capital.

## Account Catalog and strategies

- Each `config/<account_id>.json` file defines one Account Lane; its lowercase snake-case filename is the sole account identifier.
- A configuration contains a human-readable description, exactly one Strategy Spec identifier, one execution mode, one universe, and one set of risk values. Shadow lanes also declare initial virtual cash.
- The catalog validates every selected `strategies/<strategy_id>.md` file and fails if more than one configuration is live. It returns account-ID-sorted cohorts instead of maintaining an `accounts[]` registry.
- Strategy Specs remain prompt-defined Markdown policies. Ripple does not add a Python plugin engine. New versioned specs are added as new files rather than changing historical attribution in place.
- `strategy_id` is frozen into new OrderPlans and execution evidence so later review does not depend on the current config alone.
- Strategy research, compiled fact provenance, and thesis records stay in immutable DecisionSnapshots while orders use the shared schema.
- A Strategy Spec may require a checked-in deterministic compiler for normalized source-attributed raw inputs. The compiler reads the selected account configuration and requires the input symbol set to match its universe exactly. It owns Decimal formulas, date/session alignment, interpolation rejection, source and freshness checks, and completeness checks; the LLM gathers and normalizes sources but does not recompute compiler output. This is a facts seam, not a Python strategy engine: filtering, ranking, prose research, and portfolio judgment remain in the versioned Strategy Spec.

## Modes and scheduling

- Each Account Lane resolves an optional Cycle Profile: omitted configuration preserves `next_session_open`; `same_session_close` uses a Decision and later Execution on one regular Trading Day. Every new OrderPlan freezes the resolved profile and trade date. Historical plans without both fields remain legacy `next_session_open` evidence.
- Scheduled cohorts are selected by both Execution Mode and Cycle Profile, with mode-only catalog inspection retained for operators. V1 `same_session_close` allows Decision from 2:25–3:05 PM and Execution from 3:15–3:40 PM New York, treats early-close sessions as scheduled no-ops, permits manual window bypass without date/order bypass, and prohibits historical backfill.

- `live` selects zero or one lane for the current `next_session_open` live runs. `shadow` lanes are partitioned into profile-specific cohorts. `dry_run` is excluded from scheduling and exists only for deliberate manual development.
- Six schedule triggers represent the current topology: four `next_session_open` live/shadow triggers and two `same_session_close` shadow triggers. One failing shadow lane cannot authorize or mutate another lane.
- A shadow-to-live change requires explicit reconciliation against the real broker account. Virtual holdings and fills never become broker authority.
- Disabling both live schedules is the strongest operational stop. Changing the live lane to `dry_run` removes it from scheduled cohorts but does not cancel orders or liquidate positions.

## Decision and execution

- Decision runs on the evening before a Trading Day around 9:00 PM `America/New_York`; Execution runs that Trading Day around 9:35 AM. Trading days come from the checked-in NYSE calendar in `ripple/calendar.py`, not from weekday arithmetic: a decision evening is valid only when the following calendar day has a regular session, which yields the Sunday–Thursday pattern outside holiday weeks and suppresses the eve of a market holiday. A scheduled trigger that lands outside a trading session publishes and executes nothing, reports the closed session, and exits successfully; manual and backfill runs still fail loudly. A date outside the calendar's checked-in coverage is an error rather than an extrapolation, so extending coverage is a reviewed data commit. Unscheduled closures are added the same way, with `--manual-run` as the interim timing escape hatch. Schedules never automatically backfill missed cycles. The designated owner may publish a live/shadow historical Decision from complete point-in-time inputs; it retains the normal Decision window and is labeled `backfill`. Execution may consume that immutable plan through the normal manual path without relaxing risk, account binding, Live Gate, or broker safeguards.
- The Decision Routine publishes one immutable `DecisionSnapshot` and strategy-attributed `OrderPlan`. It never uses broker write tools.
- A completed regular-session close is the dated session's official consolidated closing price (the market-center official close), defined by the tape rather than by the 4:00 PM auction mechanism, so an in-hours correction disseminated after 4:00 PM still belongs to it. A last-trade snapshot, intraday index level, real-time "last", or "previous close" label is not that value. When acceptable date-indexed sources still disagree, resolution is ordered: prefer the value each source labels the official close, then defer to an exchange or SIP official closing price, then fail closed for that symbol. Values are never averaged or synthesized between sources, and a later minor revision does not retroactively invalidate a published plan. `routines/DECISION_SHADOW.md` carries the operational form.
- Every newly published OrderPlan includes a concise, human-readable `decision_rationale` for its final target portfolio and orders. It remains distinct from DecisionSnapshot warnings, candidate-rejection evidence, and deterministic Execution reason codes; legacy plans without it remain readable.
- The Execution Routine performs no new investment reasoning. It may execute, scale down, reject, or abort after deterministic revalidation. Script-emitted full-position stop-loss/take-profit Risk Exits are the sole unplanned-order exception.
- Stable IDs and first-success ownership reduce duplicates. Each new OrderPlan freezes its Decision run kind (`scheduled`, `manual`, or `backfill`), each execution result independently freezes its Execution run kind, and explicitly authorized manual runs remain accepted without relaxing safety checks. Historical plans without this field remain readable. Ambiguous live broker outcomes stop without blind retry.
- A BUY may freeze an optional `gap_cancel_above` price. That order requires the actual regular-session open at Execution and is rejected only when the open is strictly above the threshold; a missing required open fails closed. Existing plans without the field remain valid.

## Shadow execution

- Shadow uses the same deterministic risk result as live/dry evaluation and never calls a broker.
- An allowed BUY limit fills only when the profile's Execution quote is at or below its limit; an allowed SELL limit fills only when that quote is at or above its limit. Market Risk Exits fill at the quote.
- A Shadow Fill is recorded at the profile's Execution quote and timestamp with zero fees and zero slippage. Unmarketable limits are recorded as `not_filled`.
- For `same_session_close`, the equivalent marketable fill is recorded at the later same-session Execution quote and timestamp with reason `assumed_same_session_quote_fill`; it never uses the Decision reference price or a future official close. Existing `next_session_open` evidence retains `assumed_t_plus_one_quote_fill`.
- Each result freezes fill attempts and the ending virtual cash, positions, average costs, new-position count, and loss-sale state for the next cycle. It is comparison evidence, not a claim about real broker fills.

## State and isolation

- Every lane owns its configuration, state root, plan, virtual or real account facts, risk state, execution evidence, and restart lock. Taxpayer-wide loss-sale history remains the only documented cross-lane input.
- Each lowercase lane stores one complete cycle under `state/accounts/<account_id>/trading_days/<trade_date>`. The trade date is the frozen Execution-session date and is always a real session; it is the day after a `next_session_open` Decision and the same New York date as a `same_session_close` Decision.
- A cycle publishes `decision_snapshot.json` and `order_plan.json` before Execution; `execution.json` and `report.md` are added to that same directory afterward. Execution requires the co-located snapshot and plan to exist and match its input. Repeated publication or execution fails instead of overwriting evidence.
- JSONL indexes are not stored; the trade-date directories are the sole cycle index. A lane-wide tier-two block is the optional account-root `active_risk_lock.json` because it persists across trade dates.
- The state layout reset removed prior checked-in state artifacts before hosted acceptance. Private Git stores only new credential-free cycles and locks. Platform-managed Robinhood authorization remains outside the repository.
- Git is not a transactional submission journal or cross-runner lease. The live canary still accepts crash-before-log, duplicate-call, ambiguous-timeout, prompt/tool-use, configuration, and model-drift risks.

## Published evidence

- Ripple does not claim published Decision or Execution evidence is permanently immutable at the Git-history level. The code still refuses to overwrite an existing `decision_snapshot.json`/`order_plan.json` in the same trade-date directory (publish-once-per-cycle), but the designated owner may remove a mistaken or superseded artifact from the repository as a manual override. This reflects actual practice rather than authorizing routine cleanup: a manual override is a human, out-of-band correction, never something a Decision or Execution Routine does to its own or another cycle's output.

## Deterministic safety and non-goals

- Risk remains per lane: 20% maximum position, three new positions per day, 5% daily loss, 10%/15% drawdown tiers, 15-minute quote age, 30-day taxpayer-wide wash-sale lookback, 8% stop loss, and 20% take profit. Planned limits must remain inside a positive per-order price tolerance capped at 10%; Growth Momentum v3 retains v2's removal of v1's fixed 1% policy but does not remove this deterministic cap.
- Missing or stale facts, baseline mismatch, cross-account mismatch, malformed inputs, or unsafe sizing fail closed. Tier two requires human restart.
- Historical backtesting is a current non-goal. Each Decision is a single non-replayable model call over point-in-time facts, and there is no MarketData port or historical bar source; a multi-year replay would require both. Forward shadow lanes are Ripple's simulation of live trading: same schedule, same Strategy Spec, and same deterministic risk authority as live, differing only in the documented Shadow Fill assumption. Evidence about a strategy therefore comes from accumulated forward cycles rather than reconstructed history. Revisiting this needs a new decision, not a local exception.
- Current non-goals include a dashboard, automatic strategy ranking/promotion, multiple simultaneous live lanes, additional brokers, same-day entry and exit, a Python strategy engine, transactional persistence, exactly-once submission, automatic reconciliation, calibrated fee/slippage simulation, and historical backtesting or a market-data replay layer.
