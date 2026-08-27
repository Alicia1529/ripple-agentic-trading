# Current unfinished work

Repository implementation now validates account/strategy configuration, enforces mode-and-profile scheduled cohorts, preserves strategy attribution, and produces isolated dry-run plus profile-attributed shadow evidence. The `same_session_close` shadow lane and repository routines are configured; hosted triggers and the first reviewable scheduled cycle remain acceptance gates.

## Hosted shadow acceptance

- [x] Configure the Shadow Decision and Shadow Execution schedules from `routines/SCHEDULE.md`.
- [x] Observe one complete scheduled Decision → next-weekday Shadow Execution cycle for every selected shadow lane.
- [x] Review the strategy-attributed plan, deterministic risk result, Shadow Fill assumptions, ending account, and report in one trade-date directory.
- [x] Confirm a failed shadow lane does not corrupt or authorize another lane when a second shadow configuration is eventually added.
- [ ] Configure the two `same_session_close` hosted shadow triggers from `routines/SCHEDULE.md`.
- [ ] Observe and review one complete scheduled same-date Decision → Shadow Execution cycle for the selected close-profile lane.

## Live acceptance and loop

- [x] Select the reviewed first live candidate.
- [x] Implement and review the narrow Agentic Robinhood read/review/place/cancel loop without changing Decision, risk, timing, schema, or state semantics.
- [x] Verify the hosted connection selects the intended broker account and reconcile its real cash/positions against the selected lane before mode change.
- [x] Preserve one live scheduler per phase, stable IDs, repository/broker-history duplicate checks, and no blind retry after an ambiguous outcome.
- [x] Observe the required scheduled no-write acceptance cycle in the intended hosted environment.
- [x] The designated owner explicitly changes exactly one reviewed configuration to `live` and approves the $500–1000 validation allocation.
- [x] Inspect the first live cycles directly in Robinhood and compare broker evidence with deterministic output.

## Strategy comparison and replay

- [x] Add reviewed, version-named Strategy Specs and the deterministic facts-compiler seam.
- [ ] Observe enough comparable cycles across enabled strategy-attributed lanes before making any claim about relative strategy behavior.
- [ ] Accumulate enough live/shadow records to define a review window, after-cost metrics, and acceptable incident criteria.
- [ ] Add replay/reporting only from recorded strategy IDs, profile-attributed plans and fill assumptions, and ending virtual states; do not retrofit fills from Decision reference prices or future closes.
- [ ] Treat any strategy switch or capital increase as a new human decision, never an automatic promotion.

## Reliability review before expansion

- [ ] Review observed missed runs, reconnects, Git conflicts, duplicate or ambiguous live outcomes, prompt drift, and divergence from deterministic output.
- [ ] Before adding a second simultaneous live lane or increasing capital, decide whether execution needs a non-LLM adapter, transactional journal, broker idempotency proof, or stronger reconciliation.
