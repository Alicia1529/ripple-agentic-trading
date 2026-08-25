# Current unfinished work

Repository implementation now validates account/strategy configuration, enforces scheduled cohorts, preserves strategy attribution, and produces isolated dry-run and T+1 quote-based shadow evidence.

## Hosted shadow acceptance

- [ ] Configure the Shadow Decision and Shadow Execution schedules from `routines/SCHEDULE.md`.
- [ ] Observe one complete `account_b` scheduled Decision → next-weekday Shadow Execution cycle.
- [ ] Review the strategy-attributed plan, deterministic risk result, Shadow Fill assumptions, ending account, JSONL record, and report.
- [ ] Confirm a failed shadow lane does not corrupt or authorize another lane when a second shadow configuration is eventually added.

## Live acceptance and loop

- [ ] Decide which reviewed configuration will become the first live lane; no configuration is live today.
- [ ] Implement and review the narrow Agentic Robinhood read/review/place/cancel loop without changing Decision, risk, timing, schema, or state semantics.
- [ ] Verify the hosted connection selects the intended broker account and reconcile its real cash/positions against the selected lane before mode change.
- [ ] Preserve one live scheduler per phase, stable IDs, repository/broker-history duplicate checks, and no blind retry after an ambiguous outcome.
- [ ] Observe the required scheduled no-write acceptance cycle in the intended hosted environment.
- [ ] Alicia explicitly changes exactly one configuration from `dry_run` or `shadow` to `live` and approves the $500–1000 validation allocation.
- [ ] Inspect the first live cycles directly in Robinhood and compare broker evidence with deterministic output.

## Strategy comparison and replay

- [x] Add reviewed, version-named Strategy Specs; `account_a` now selects `growth_momentum_v2` and `account_b` selects `earnings_drift_v1`.
- [ ] Observe enough comparable Account A and Account B cycles before making any claim about relative strategy behavior.
- [ ] Accumulate enough live/shadow records to define a review window, after-cost metrics, and acceptable incident criteria.
- [ ] Add replay/reporting only from recorded strategy IDs, plans, T+1 fill assumptions, and ending virtual states; do not retrofit Day T fills.
- [ ] Treat any strategy switch or capital increase as a new human decision, never an automatic promotion.

## Reliability review before expansion

- [ ] Review observed missed runs, reconnects, Git conflicts, duplicate or ambiguous live outcomes, prompt drift, and divergence from deterministic output.
- [ ] Before adding a second simultaneous live lane or increasing capital, decide whether execution needs a non-LLM adapter, transactional journal, broker idempotency proof, or stronger reconciliation.
