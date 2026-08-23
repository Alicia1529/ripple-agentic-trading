# Current status

Living status doc — this reflects the *current* state of in-flight work, not a growing history. When a section is done, either delete it or fold it into a one-line note under "Recently completed"; don't leave finished work cluttering this file. If there's something a future session genuinely needs to pick up mid-task, that unfinished-work state belongs here, in enough detail that the next agent doesn't have to re-derive it from git log or chat history.

Status: **PHASE −1 IN PROGRESS.** The architecture draft exists, and local runner-owned Robinhood MCP bootstrap, headless reuse, cross-process refresh, one account binding, and the sanitized order-history read path are verified. The second account binding, idempotency, lifecycle reconciliation, and deployment-runtime feasibility remain unverified.

## Phase −1 — feasibility

- Partial: one controlled local Codex Automation run successfully executed the read-only probe with `uv run --no-cache`. The same safe temporary Automation was activated at 2026-08-22 21:43 PDT for its next unchanged daily trigger at 2026-08-23 19:28 PDT, configured about 21 hours 44 minutes in advance; after observing that run, pause it or leave it active for one additional unchanged trigger to test repetition. Cloud Automation, secrets, usage limits, repeated-run reliability, and live DST-boundary behavior remain unverified.
- Partial: the local runner's sanitized probes found two brokerage accounts, selected exactly one active caller-accessible account, and successfully read a well-formed `get_equity_orders` envelope without disclosing account or order data. A second independent credential/account binding remains unverified. The history schema does not expose placement `ref_id`; live broker deduplication and lifecycle/ambiguous-outcome reconciliation remain unverified.
- Partial: official deployment-storage research rejects GitHub Actions secrets for rotating OAuth state and identifies AWS Secrets Manager plus Aurora PostgreSQL/S3 as leading synthetic-proof candidates, not selected vendors. Phase 0 must prove exact-version credential pointers, `refresh_started`/`refresh_unknown`, OIDC isolation, eventual-consistency failure behavior, Aurora cost/compatibility, and a secure logical-export path (`docs/feasibility/github-actions-oauth-secret-store.md`, `docs/feasibility/runtime-storage-options.md`).
- [x] Prove a plain, non-agentic runner can authenticate to Robinhood Trading MCP headlessly and refresh credentials without routine human action (`docs/feasibility/mcp-python-oauth-client.md`)
- [ ] Prove explicit account selection and two independent Agentic-account bindings
- [x] Capture the exact review/place/cancel/history schemas, including fractional/dollar-order behavior (`docs/feasibility/robinhood-equity-tool-schemas.md`)
- [ ] Test whether Robinhood accepts a stable client order id / idempotency key
- [ ] Prove broker-history reconciliation for accepted, rejected, partial, canceled, and ambiguous outcomes
- [ ] Verify Claude/Codex scheduling, secret lifecycle, usage assumptions, and timezone behavior
- [ ] Record every result; revise the architecture before implementation if a correctness-critical assumption fails

## Phase 0 — deterministic core

- Partial: the initial `DecisionSnapshot` and `OrderPlan` modules now enforce strict, deeply immutable JSON envelopes with canonical UUIDs and timezone-aware timestamps; `OrderPlan` uses a scalar planned-order field allowlist so execution outcomes cannot be nested into it, while tax lots remain out of scope. Feed-specific inputs, semantic portfolio/order validation, Decimal parsing/ranges, canonical hashing/persistence, and `ExecutionEvent` remain unfinished.
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

- On 2026-08-22 Alicia completed the local OAuth wizard: runner-owned interactive bootstrap, sanitized stored-state validation, two fresh-process forced-expiry refreshes, and final browser-free `initialize`/`tools/list` reuse all succeeded. No broker tool was called.
- The local OAuth failure gate is covered end to end with mock transport: rejected refresh credentials fail closed before MCP session creation, require bootstrap, and emit no credential or response detail.
- Official model-usage research established that Claude Pro and ChatGPT Plus are suitable only for monitored feasibility, not a fixed production capacity boundary; actual Ripple prompt usage and any explicit API fallback budget remain to be measured (`docs/feasibility/model-subscription-usage.md`).
- X is excluded from v1 after official API/terms research found no measured incremental value and unresolved retention/external-LLM policy conflicts; D19 records explicit reconsideration gates (`docs/feasibility/x-api-news-source.md`).
- Architecture draft: `PROPOSAL.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md` written and internally consistent; feasibility remains open.
- Repo reorganized: `docs/archive/` holds the two original independent draft proposals (Claude's and Codex's) plus the comparison research that synthesized them — superseded, kept for history only.
- Agent collaboration entry points consolidated: `AGENTS.md` and `CLAUDE.md` are thin indexes into shared docs; `docs/INVARIANTS.md` is the common correctness checklist.
- Multi-agent development workflow documented in `docs/AGENT_WORKFLOW.md`; roles live in prompts, concurrent writers use isolated branches/worktrees, and handoffs flow through Git and shared docs.
