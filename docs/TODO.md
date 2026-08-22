# Current status

Living status doc — this reflects the *current* state of in-flight work, not a growing history. When a section is done, either delete it or fold it into a one-line note under "Recently completed"; don't leave finished work cluttering this file. If there's something a future session genuinely needs to pick up mid-task, that unfinished-work state belongs here, in enough detail that the next agent doesn't have to re-derive it from git log or chat history.

Status: **PHASE −1 IN PROGRESS.** The architecture draft exists, and a safe, read-only Robinhood MCP probe scaffold now exists. Headless authentication, credential refresh, and broker feasibility remain unverified.

## Phase −1 — feasibility

- In progress: a disposable Robinhood MCP probe checks unauthenticated endpoint/protocol reachability and fails closed on authentication or interaction requirements. It does not hold credentials, invoke broker tools, or prove headless authentication/refresh.
- Partial: a local Codex Automation independently triggered the read-only scheduler probe, but its `python3` runtime lacked `zoneinfo`; successful runtime, cloud Automation, secrets, usage, and DST behavior remain unverified.
- [ ] Prove a plain, non-agentic runner can authenticate to Robinhood Trading MCP headlessly and refresh credentials without routine human action
- [ ] Prove explicit account selection and two independent Agentic-account bindings
- [ ] Capture the exact review/place/cancel/history schemas, including fractional/dollar-order behavior
- [ ] Test whether Robinhood accepts a stable client order id / idempotency key
- [ ] Prove broker-history reconciliation for accepted, rejected, partial, canceled, and ambiguous outcomes
- [ ] Verify Claude/Codex scheduling, secret lifecycle, usage assumptions, and timezone behavior
- [ ] Decide whether X (Twitter) is worth adding as a supplementary news source, based on its API access tier and pricing (D19) — the primary free/open financial-data feed does not depend on this decision
- [ ] Record every result; revise the architecture before implementation if a correctness-critical assumption fails

## Phase 0 — deterministic core

- [ ] Choose the smallest transactional and object stores that satisfy D15; document retention, backup/export, unique constraints, conditional writes, and cross-runner leases
- [ ] Implement immutable `DecisionSnapshot` and `OrderPlan` schemas plus append-only `ExecutionEvent` records
- [ ] Implement risk engine (position sizing, daily loss breaker, drawdown tiers, wash-sale guard, deterministic exits) as unit-testable code
- [ ] Implement fake broker, execution state machine, transactional lease, and broker reconciliation
- [ ] Add adversarial tests proving an LLM-authored instruction cannot bypass the risk engine
- [ ] Add failure-injection tests: duplicate trigger, crash before submit, crash after broker acceptance, stale data, partial fill, and unresolved broker outcome
- [ ] Implement timezone-safe scheduling as a trigger only; transactional state decides whether work may proceed

## Phase 1 — paper and shadow

- [ ] Run Claude, OpenAI, mean-reversion, and SPY/QQQ lanes from the same frozen DecisionSnapshot
- [ ] Register every candidate's sample-size, holdout, cost, benchmark, and risk criteria before its evaluation starts
- [ ] Complete eight continuous weeks without unresolved reconciliation, duplicate cycles, missed-run blind spots, or material risk defects

## Phase 2/3 — live rollout

- [ ] Start one-account live canary with a manually approved validation allocation
- [ ] Verify real credential lifecycle, fills, reconciliation, alerts, kill switch, and recovery before enabling the second account
- [ ] Start the two-account live comparison only after the canary gate passes

Before any increase beyond the initial $500–1000 per live account:

- [ ] Define and document the evidence window, profitability/risk criteria, and approved increase amount for the one-time human capital review required by D14; no automatic scaling

## Recently completed

- Architecture draft: `PROPOSAL.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md` written and internally consistent; feasibility remains open.
- Repo reorganized: `docs/archive/` holds the two original independent draft proposals (Claude's and Codex's) plus the comparison research that synthesized them — superseded, kept for history only.
- Agent collaboration entry points consolidated: `AGENTS.md` and `CLAUDE.md` are thin indexes into shared docs; `docs/INVARIANTS.md` is the common correctness checklist.
- Multi-agent development workflow documented in `docs/AGENT_WORKFLOW.md`; roles live in prompts, concurrent writers use isolated branches/worktrees, and handoffs flow through Git and shared docs.
