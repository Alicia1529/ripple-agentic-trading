# Current status

Living status doc — this reflects the *current* state of in-flight work, not a growing history. When a section is done, either delete it or fold it into a one-line note under "Recently completed"; don't leave finished work cluttering this file. If there's something a future session genuinely needs to pick up mid-task, that unfinished-work state belongs here, in enough detail that the next agent doesn't have to re-derive it from git log or chat history.

## Phase 0 — build

Status: **NOT STARTED.** Design is complete (`PROPOSAL.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`); no code exists yet.

Remaining, roughly in dependency order:

- [ ] `OrderPlan` data model + persistence (see `docs/ARCHITECTURE.md` "OrderPlan data model")
- [ ] Risk engine (position sizing, daily loss breaker, drawdown tiers, wash-sale guard, stop-loss/take-profit) as unit-testable, stdlib-first code — see `docs/ARCHITECTURE.md` "Risk layer"
- [ ] Adversarial test cases proving an LLM-authored instruction cannot bypass the risk engine (D6 in `docs/DECISIONS.md`)
- [ ] Decision Run: Account A (Claude Code cloud routine) and Account B (Codex cloud Automation) against Alpaca paper first, single account for initial wiring
- [ ] Execution Run: plain code, no LLM in the loop, per the "Execution must not be an LLM session" constraint
- [ ] Idempotency (D3c): per-order persisted state checked before submission, `order_id` generated once and reused, single-flight guard against overlapping triggers
- [ ] Timezone-safe scheduling (D10a): poll-and-self-check against `America/New_York`, not a fixed UTC cron
- [ ] Mean-reversion baseline + SPY/QQQ bookkeeping, both marked at T+1 open (not signal-day close) per the look-ahead rule
- [ ] Shadow pool scaffolding: register/list candidates, virtual fill simulator
- [ ] Verify the three open questions in `docs/ARCHITECTURE.md` (two independent Agentic-account credentials, Pro/Plus usage caps, cloud-scheduler timezone support) before funding a live account

## Recently completed

- Design phase: `PROPOSAL.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` written and internally consistent.
- Repo reorganized: `docs/archive/` holds the two original independent draft proposals (Claude's and Codex's) plus the comparison research that synthesized them — superseded, kept for history only.
- Agent collaboration entry points consolidated: `AGENTS.md` and `CLAUDE.md` are thin indexes into shared docs; `docs/INVARIANTS.md` is the common correctness checklist.
