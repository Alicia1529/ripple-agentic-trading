# Current unfinished work

Repository acceptance is complete for the two-account fixture-backed dry-run MVP. Only the work below is unfinished.

## Hosted acceptance

- [ ] Observe Account A's complete scheduled prior-evening Decision → next-weekday dry Execution cycle; review its plan, deterministic output, JSONL records, and report.
- [ ] Keep Account A's hosted artifacts credential-free; manual rehearsals do not count as scheduled acceptance.

## Live loop and gates

- [ ] Implement and review the narrow live MCP read/review/place/cancel call loop without changing decision, risk, timing, schema, or state semantics.
- [ ] Verify Account A's hosted connection selects the intended account and confirm live order shapes with non-writing or smallest-safe probes.
- [ ] Preserve one scheduler per phase, stable IDs, pre-submit repository/broker-history checks, and no blind retry after an ambiguous outcome.
- [ ] Alicia reviews Account A's full dry cycle and explicitly changes its human-owned `execution.mode` from `dry_run` to `live`.
- [ ] Start Account A with its approved $500–1000 validation allocation and inspect its first live cycle.

## Eight-week capital review

- [ ] Operate Account A for eight continuous weeks and record after-cost performance, drawdown, missed runs, reconnects, Git conflicts, ambiguous outcomes, and any divergence from deterministic output.
- [ ] Before increasing capital, review observed incidents and decide whether LLM execution remains acceptable or requires a non-LLM executor, transactional journal, broker idempotency proof, or stronger reconciliation.
- [ ] Record any approved architecture change and exact owner-approved funding change. Capital never increases automatically.

## Third-account trigger

- [ ] Before adding a third account, review credential isolation, transactional state, duplicate/ambiguous submissions, per-account risk state, scheduling, and operational ownership.
- [ ] Add coordination or account-collection abstractions only after a third concrete lane or shared operation proves the need.
