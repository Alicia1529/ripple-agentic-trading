# Current effective decisions

Git history retains superseded reasoning. This file summarizes only decisions that govern the current release.

## Product and release

- Ripple compares isolated, strategy-attributed Account Lanes while keeping deterministic risk authority and human-owned live activation.
- `account_a` is currently `dry_run`; `account_b` is currently `shadow`. There is no live configuration while the broker-write loop and acceptance gates remain unfinished.
- Initial live exposure remains $500–1000. Alicia alone enables live mode, binds or funds the broker account, restarts a tier-two lock, switches the live strategy, or approves more capital.
- Live and shadow evidence can support a human review. No metric or threshold automatically promotes a strategy or changes capital.

## Account Catalog and strategies

- Each `config/<account_id>.json` file defines one Account Lane; its lowercase snake-case filename is the sole account identifier.
- A configuration contains a human-readable description, exactly one Strategy Spec identifier, one execution mode, one universe, and one set of risk values. Shadow lanes also declare initial virtual cash.
- The catalog validates every selected `strategies/<strategy_id>.md` file and fails if more than one configuration is live. It returns account-ID-sorted cohorts instead of maintaining an `accounts[]` registry.
- Strategy Specs remain prompt-defined Markdown policies. Ripple does not add a Python plugin engine. New versioned specs are added as new files rather than changing historical attribution in place.
- `strategy_id` is frozen into new OrderPlans and execution evidence so later review does not depend on the current config alone.
- Account A selects `growth_momentum_v3`; its research evaluation, compiled fact provenance, and thesis records stay in immutable DecisionSnapshots while its orders use the shared schema. Account B is outside that switch.
- Growth Momentum numeric facts are derived by one checked-in deterministic compiler from normalized source-attributed raw inputs. The compiler owns Decimal formulas, date/session alignment, interpolation rejection, source and freshness checks, and completeness checks; the LLM gathers and normalizes sources but does not recompute compiler output. This is a facts seam, not a Python strategy engine: filtering, ranking, prose research, and portfolio judgment remain in the versioned Strategy Spec.

## Modes and scheduling

- `live` selects zero or one lane for the live Decision and Execution runs. `shadow` selects all shadow lanes for their two cohort runs. `dry_run` is excluded from scheduling and exists only for deliberate manual development.
- Exactly four schedule triggers represent the topology: live Decision, shadow Decision, live Execution, and shadow Execution. One failing shadow lane cannot authorize or mutate another lane.
- A shadow-to-live change requires explicit reconciliation against the real broker account. Virtual holdings and fills never become broker authority.
- Disabling both live schedules is the strongest operational stop. Changing the live lane to `dry_run` removes it from scheduled cohorts but does not cancel orders or liquidate positions.

## Decision and execution

- Decision runs Sunday–Thursday around 9:00 PM `America/New_York`; Execution runs the next weekday around 9:35 AM. Missed cycles are not backfilled.
- The Decision Routine publishes one immutable `DecisionSnapshot` and strategy-attributed `OrderPlan`. It never uses broker write tools.
- The Execution Routine performs no new investment reasoning. It may execute, scale down, reject, or abort after deterministic revalidation. Script-emitted full-position stop-loss/take-profit Risk Exits are the sole unplanned-order exception.
- Stable IDs and first-success ownership reduce duplicates. Manual runs are labeled; ambiguous live broker outcomes stop without blind retry.
- A BUY may freeze an optional `gap_cancel_above` price. That order requires the actual regular-session open at Execution and is rejected only when the open is strictly above the threshold; a missing required open fails closed. Existing plans without the field remain valid.

## Shadow execution

- Shadow uses the same deterministic risk result as live/dry evaluation and never calls a broker.
- An allowed BUY limit fills only when the T+1 execution quote is at or below its limit; an allowed SELL limit fills only when the quote is at or above its limit. Market Risk Exits fill at the quote.
- A Shadow Fill is recorded at the T+1 quote and execution timestamp with zero fees and zero slippage. Unmarketable limits are recorded as `not_filled`.
- Each result freezes fill attempts and the ending virtual cash, positions, average costs, new-position count, and loss-sale state for the next cycle. It is comparison evidence, not a claim about real broker fills.

## State and isolation

- Every lane owns its configuration, state root, plan, virtual or real account facts, risk state, execution evidence, and restart lock. Taxpayer-wide loss-sale history remains the only documented cross-lane input.
- Existing uppercase `state/accounts/account_A` artifacts are immutable legacy fixture evidence. Lowercase catalog identifiers start new canonical roots; historical plans are not rewritten.
- Private Git stores credential-free plans, compact JSONL facts, results, reports, and locks. Platform-managed Robinhood authorization remains outside the repository.
- Git is not a transactional submission journal or cross-runner lease. The live canary still accepts crash-before-log, duplicate-call, ambiguous-timeout, prompt/tool-use, configuration, and model-drift risks.

## Deterministic safety and non-goals

- Risk remains per lane: 20% maximum position, three new positions per day, 5% daily loss, 10%/15% drawdown tiers, 15-minute quote age, 30-day taxpayer-wide wash-sale lookback, 8% stop loss, and 20% take profit. Planned limits must remain inside a positive per-order price tolerance capped at 10%; Growth Momentum v3 retains v2's removal of v1's fixed 1% policy but does not remove this deterministic cap.
- Missing or stale facts, baseline mismatch, cross-account mismatch, malformed inputs, or unsafe sizing fail closed. Tier two requires human restart.
- Current non-goals include a dashboard, automatic strategy ranking/promotion, multiple simultaneous live lanes, additional brokers, intraday trading, a Python strategy engine, transactional persistence, exactly-once submission, automatic reconciliation, and calibrated fee/slippage simulation.
