# Same-session close shadow slice — execution plan

**Status:** Tasks 1 and 2 are fixture-accepted. Task 3 repository rollout and hosted triggers were
configured after owner approval on 2026-08-27; the first scheduled acceptance cycle remains
pending. This plan does not authorize a live lane, strategy switch, or capital change.

Use this plan when implementing the first `same_session_close` shadow capability. Read
`AGENTS.md` and its current sources of truth before acting; current repository state overrides
this planning artifact.

## Outcome

Add a second Decision Cycle timing profile without duplicating Decision, deterministic risk,
Shadow Fill, or Lane State implementations:

- `next_session_open`: preserve the existing prior-evening Decision and next-Trading-Day morning
  Execution behavior;
- `same_session_close`: publish a Decision and attempt Execution on the same regular Trading Day,
  before the close.

The first strategy using the new profile is a long-only, quantitative closing-momentum shadow
strategy. Live use is outside this plan.

## Trade-date contract

`trade_date` is the New York date of the Execution session and the directory key for one Decision
Cycle. It is always a checked-in-calendar Trading Day.

| Cycle profile | Decision | Execution | `trade_date` |
|---|---|---|---|
| `next_session_open` | Prior calendar evening | Next Trading Day, morning | Execution session date |
| `same_session_close` | Current Trading Day, before close | Same Trading Day, later | Decision and Execution New York date |

Example: a `same_session_close` Decision at `2026-08-26T14:55:00-04:00` and Execution at
`2026-08-26T15:25:00-04:00` both live under
`state/accounts/<account_id>/trading_days/2026-08-26/`.

For both profiles:

1. `DecisionSnapshot.as_of <= OrderPlan.decision_time < execution_context.as_of`;
2. an OrderPlan freezes its cycle profile and trade date before Execution;
3. Execution uses the co-located immutable snapshot and plan;
4. a Shadow Fill uses the actual Execution quote and timestamp, never a later official close; and
5. scheduled runs outside the profile's valid session or window write no artifact.

V1 treats every NYSE early-close session as a successful `same_session_close` no-op. Supporting a
window relative to an early close is a later calendar-and-scheduler decision.

## Release boundary

The repository has completed hosted shadow and live acceptance for the existing T+1 profile. It is
still accumulating comparable cycles, after-cost metrics, incident criteria, and reliability
evidence. This slice therefore ends at shadow evidence.

Accepted risks:

- Git remains continuity rather than a transactional handoff between the close Decision and
  Execution runs;
- a slow or missed Decision may leave no plan for Execution, which is a failed/no-op lane rather
  than authority to retry;
- Shadow Fill evidence retains the explicit zero-fee and zero-slippage assumption; and
- the strategy carries overnight gap risk after a same-session BUY.

Non-goals:

- same-day entry and exit of one symbol;
- shorting, margin leverage, intraday buying-power expansion, or sale-funded same-cycle BUYs;
- market-on-close orders, closing-auction participation, early-close support, or extended hours;
- a Python strategy engine, a generic scheduler subsystem, historical backtesting, or replay;
- live routines, broker writes, a live configuration, or hosted live triggers; and
- changing existing lane modes, strategy bindings, universes, risk values, or capital.

## Invariants and durable decision

The implementation must preserve invariants 1–4, 6–8, 10–11, and 13. It changes the wording and
scope of three invariants:

- **Invariant 5 — honest timing:** replace the T+1-only rule with profile-attributed timing. No
  signal receives a fill before Decision or a future official-close price.
- **Invariant 9 — deterministic selection:** scheduled cohorts are selected by Execution Mode and
  cycle profile, then remain account-ID sorted.
- **Invariant 12 — explicit Shadow Fill:** require the marketable quote from the plan's documented
  Execution profile rather than always a T+1 quote.

Before production code lands, record the approved decision in `docs/DECISIONS.md` and update
`docs/ARCHITECTURE.md` in the same change. Update `CONTEXT.md` so these terms have one meaning:

- **Cycle Profile:** the configured timing topology of a Decision Cycle;
- **Decision Cycle:** one profile-attributed Decision and its corresponding Execution attempt;
- **Scheduled Cohort:** lanes selected by Execution Mode and Cycle Profile; and
- **Shadow Fill:** a profile-attributed quote-fill assumption, not necessarily T+1.

Completion criterion: every changed invariant has one generalized replacement, and stable docs no
longer claim that all Decision Cycles are necessarily T+1.

## Task 1 — implement the cycle-profile seam

**Approval gate:** this task changes durable architecture. Obtain explicit owner approval for the
four production-code files below. If safe implementation requires `ripple/risk.py`,
`ripple/calendar.py`, a new production module, or another production file, stop and propose a
smaller alternative or request expanded scope.

### 1. Account Catalog

Modify `ripple/account_config.py`:

- accept optional `execution.cycle_profile` with exactly `next_session_open` or
  `same_session_close`;
- interpret an absent field as legacy `next_session_open`, so current configurations retain their
  behavior without edits;
- expose the resolved value on immutable `AccountConfig`;
- keep `risk_rules()` limited to the existing execution mode so deterministic risk input does not
  change; and
- add deterministic selection by `(mode, cycle_profile)` while retaining mode-only inspection for
  operators.

Extend `list-accounts` with optional `--cycle-profile`. Scheduled routines will eventually use
both filters; an operator may still list every lane of one mode.

Completion criterion: malformed profiles fail catalog validation, omitted profiles resolve to
`next_session_open`, and selection is account-ID sorted and lane-isolated.

### 2. OrderPlan attribution

Modify `ripple/order_plan.py`:

- add paired `cycle_profile` and `trade_date` fields to every newly published plan;
- require both or neither when reading an artifact;
- validate the supported profile and ISO date shape;
- keep historical plans without either field readable as legacy `next_session_open` evidence; and
- emit neither field when round-tripping a legacy plan.

Do not change planned-order shape, stable-ID formulas, limits, GFD semantics, or the one-order-per-
symbol rule.

Completion criterion: new plans freeze profile/date, legacy plan round trips are byte-semantic
equivalents, and a half-attributed plan fails validation.

### 3. Profile-aware cycle timing

Modify `ripple/mvp.py`. Keep the seam internal to this module for this slice; do not create a new
scheduler or timing module.

Preserve existing scheduled behavior for `next_session_open`. Add these scheduled semantics for
`same_session_close`:

- Decision and snapshot use the same New York Trading Day;
- allowed Decision window: 2:25–3:05 PM `America/New_York`;
- Execution uses the same date, occurs after Decision, and is allowed from 3:15–3:40 PM;
- weekend, full-closure, out-of-calendar, and `EARLY_CLOSE_DAYS` behavior fails closed; scheduled
  closed/early-close sessions are successful no-ops;
- `--manual-run` may bypass the clock window but still requires the frozen same-session trade date
  and Execution after Decision; and
- `--historical-backfill` rejects `same_session_close` in V1.

Publishing writes to the plan's frozen `trade_date`; Execution resolves the co-located cycle from
that field and requires current configuration profile to match. Legacy plans retain the existing
next-Trading-Day derivation.

Add `cycle_profile` and `trade_date` to new execution results and reports. Do not change the
`DecisionSnapshot` schema.

Completion criterion: the same New York date is used for Decision, Execution, and state directory;
Execution before Decision, profile mismatch, early-close scheduling, and a non-Trading-Day date
authorize no action or artifact.

### 4. Profile-attributed Shadow Fill

Modify `ripple/shadow.py`:

- accept the resolved cycle profile from the caller;
- preserve `assumed_t_plus_one_quote_fill` for `next_session_open` evidence;
- use `assumed_same_session_quote_fill` for a marketable `same_session_close` limit; and
- retain `limit_not_marketable`, execution-quote pricing, execution timestamps, ending-account
  transitions, and zero-cost assumptions.

Completion criterion: no same-session result is labeled T+1, no next-open regression is renamed,
and neither profile can fill from the Decision reference price alone.

### 5. Tests and fixture evidence

Add or extend tests in the existing matching files. Cover at least:

1. absent, valid, and invalid configuration profiles;
2. deterministic mode-plus-profile cohort selection;
3. legacy and new OrderPlan parsing/round trips;
4. a normal-day `next_session_open` regression cycle;
5. a normal-day `same_session_close` Decision and later Execution under one trade-date directory;
6. same-session Execution before Decision, on another date, and after its window;
7. weekend, holiday, and early-close scheduled no-ops;
8. manual-window bypass without trade-date bypass;
9. profile mismatch between config and plan;
10. fresh, stale, missing, marketable, and unmarketable Execution quotes; and
11. distinct Shadow Fill reason codes with unchanged ending-account arithmetic.

Create a credential-free `same_session_close` fixture using a demo configuration outside the
scheduled `config/*.json` glob. No current Account Lane binding changes in Task 1.

Completion criterion: the fixture produces reviewable same-day artifacts in a temporary state
root, every negative case fails closed, and all existing tests remain green.

### 6. Task 1 verification

Run:

```bash
uv run --no-cache python -m unittest discover -s tests -t .
uv run --no-cache python -m ripple.mvp validate-configs
uv run --no-cache python -m ripple.mvp list-accounts --mode live
uv run --no-cache python -m ripple.mvp list-accounts --mode shadow
git diff --check
```

Inspect the fixture artifacts and prove:

- `cycle_profile == "same_session_close"` and `trade_date` is the shared New York date;
- snapshot, Decision, Execution, and quote timestamps are ordered honestly;
- the OrderPlan and execution evidence carry the selected strategy ID;
- a fill, if present, uses the Execution quote and same-session reason code;
- no existing T+1 fixture changes semantics; and
- no credential, token, cookie, account number, or raw authenticated response is present.

Commit one focused Task 1 change with the assigned role prefix and append one compact rolling
handoff entry. Do not begin Task 2 in the same implementation task.

## Task 2 — author an unbound closing-momentum strategy

Start a new task after Task 1 is reviewed. Add a version-named Strategy Spec and a demo fixture;
do not select it from `config/*.json` yet.

The draft policy should:

- be long-only and quantitative so the close Decision does not depend on open-ended primary-source
  research during a narrow window;
- use completed-session compiler facts for SMA, 60–10 momentum, relative QQQ momentum, ATR, sector,
  and earnings distance;
- add fresh regular-session price and session-open facts with source and timezone-aware as-of time;
- evaluate every holding before entries;
- require a positive SPY/QQQ regime, positive completed-session momentum, current price above the
  completed SMA and both prior close and current-session open, adequate earnings distance, and
  available cash without a SELL fill;
- rank from compiler-produced values, select at most one new position, target no more than 8%, and
  hold no more than eight positions;
- keep deterministic stop loss, take profit, drawdown, wash-sale, quote-age, and 20% position rules
  authoritative;
- use the current Decision quote as `reference_price_at_decision`, a bounded LIMIT inside the 10%
  system tolerance, `regular_hours`, and `gfd`; and
- publish a valid no-trade plan when regime, data, eligibility, or cash is insufficient.

The Strategy Spec must explicitly reject future official-close data, margin, same-day round trips,
sale-funded BUYs, market-on-close orders, and early-close sessions while stating the positive
replacement behavior.

Completion criterion: the new spec passes the strategy self-check, its fixture publishes through
the shared schema, deterministic risk remains unchanged, and no scheduled or live binding exists.

## Task 3 — owner-approved shadow rollout

This task requires a separate owner decision naming the new shadow Account Lane, initial virtual
cash, universe, risk values, and strategy binding. Do not infer these deployment facts from this
plan.

After approval:

1. add the new `shadow` configuration with explicit
   `"execution": {"mode": "shadow", "cycle_profile": "same_session_close"}`;
2. update the existing overnight routines to select `next_session_open` explicitly;
3. add close-shadow Decision and Execution routines that select only `same_session_close`;
4. update `routines/SCHEDULE.md` with shadow-close triggers around 2:30 PM and 3:20 PM New York;
5. configure the two hosted shadow triggers only after repository acceptance; and
6. observe one complete scheduled Decision → same-session Shadow Execution cycle before calling
   the new profile hosted-accepted.

A missing plan at the Execution trigger, a Git conflict, a stale quote, an account-baseline
mismatch, or a missed window stops that lane without retry or backfill. Existing overnight and live
schedules continue independently.

Completion criterion: scheduled evidence shows correct cohort selection, same-date state,
deterministic risk output, profile-attributed Shadow Fill assumptions, ending virtual state, no
cross-lane mutation, and no broker call.

## Final stop condition

The plan is complete when Task 3 has one reviewable hosted shadow cycle and the repository records
remaining comparison, cost-model, and reliability work in `docs/TODO.md`. Live consideration is a
new architecture and owner-approval task after a review window and acceptance criteria have been
defined from observed evidence.
