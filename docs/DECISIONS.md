# Decisions

Append-only decision log (ADR-style). Each entry records what was decided and why, at the time it was decided. Don't edit past entries to "fix" wording — if a decision changes, add a new entry that supersedes the old one and say so explicitly. `docs/ARCHITECTURE.md` reflects the *current* state that results from these decisions; this file explains *how we got here*.

## D1 — Real objective

**Decision:** Learn agent-system design + build a genuinely comparable baseline, not chase returns.

**Why:** The capital involved ($500–1000 per live account) is too small for returns to matter financially. The actual goal is hands-on experience building "untrusted LLM decision layer + deterministic code-enforced risk layer," which is structurally the same problem as production LLM-safety system design.

## D2 — Number of live accounts

**Decision:** Two Robinhood Agentic live accounts, both under the same Robinhood login, each running a full independent 3-analyst + PM pipeline. Alpaca is used only for paper validation, not as a third parallel account.

**Why:** We need a real, live A/B comparison of two model configurations. Each account's own broker statement is authoritative — this avoids the "shared-account multi-strategy" conflict-resolution machinery (which symbol belongs to which strategy, no silent netting, ledger-vs-broker reconciliation invariants) that a single shared account would require. Two accounts under one login add negligible operational overhead compared to spreading across multiple brokers (which was the actual concern behind "don't want too many accounts").

## D2a — Model assignment per account

**Decision:** Both accounts run the *same* analyst/PM architecture, risk layer, universe, and cadence — the only difference is which model powers them. Concretely: **Account A = Claude** (Decision Run as a Claude Code cloud scheduled routine, initially using an existing Claude Pro subscription), **Account B = OpenAI** (Decision Run as a Codex cloud Automation, initially using an existing ChatGPT Plus subscription). Consumer subscription capacity is suitable for a monitored feasibility trial but is not a production reliability boundary: limits are shared, variable, and workload-dependent. A production lane whose missed run is unacceptable uses an explicitly enabled, budget-capped metered API path; exhaustion never causes an unaudited provider/model switch.

**Why:** Holding everything else constant makes the comparison a clean model-capability comparison, not a confound of different strategy designs. Official vendor documentation confirms that scheduled/cloud work consumes the same variable allowances as interactive use and offers no fixed per-run capacity guarantee. Existing subscriptions may keep feasibility cost near $0, but the actual four-call workload must be measured; API credentials are the documented automation boundary when capacity and reliability matter. See `docs/feasibility/model-subscription-usage.md`.

## D2b — Capital per account

**Decision:** Each account gets its own $500–1000 (total exposure $1000–2000 across both), not a shared pool.

## D2c — Zero-ops constraint confirmed compatible with the two-account + shadow-pool scope

**Decision:** The zero-routine-operational-load constraint (see `docs/ARCHITECTURE.md` "Positioning") does not force this design down to a single-account/single-strategy system. Explicitly checked and confirmed: the two-live-account (D2) plus open shadow-pool (D5) design is compatible with near-zero maintenance, because every human touchpoint in it is a rare, high-stakes event (monthly allowlist review, a risk breaker firing, a shadow-candidate graduation approval), not routine toil.

**Why:** A separate, externally-generated document in this repo's history (now `docs/archive/PROPOSAL_COMPARISON.v0.md`) argued for collapsing to a single active strategy specifically *because of* this constraint, reasoning that low maintenance time implies minimal architecture. That conclusion was checked directly and rejected — the constraint is real, but doesn't require that architectural collapse, since reconciliation, cost logging, and missed-run detection are all automated code, not manual work regardless of how many accounts exist. `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` are authoritative over that archived document.

*(Logged after the fact — this was decided in the same working session as D2/D2a/D2b, not chronologically after D11 below; placed here to keep it near the account-scope decisions it protects.)*

## D3 — Decision/execution split (supersedes an earlier same-evening-submission design)

**Decision:** Signals are generated once daily after market close and persisted as an immutable `OrderPlan`. No order is ever submitted the same evening. A separate Execution Run, ~9:35am ET the next trading day, revalidates and executes.

**Why:** Decision timing is governed by information availability (when the day's closing data is final); execution timing is governed by market liquidity/execution quality (the first few minutes after open have the thinnest liquidity and widest spreads). These are different problems and conflating them was a real design mistake in the first draft, corrected here. As a side effect, this removes any dependency on how Robinhood Agentic's order tools behave when the market is closed, since orders are now only ever submitted after the market has opened.

## D3a — Default order type

**Decision:** Limit / marketable-limit orders by default, with the limit set within a configurable tolerance band (e.g. ±0.5%, `price_tolerance_pct`) of the price at decision time. Market orders require an explicit justification from the strategy. No VWAP/TWAP or other sophisticated execution algorithms in Phase 0.

**Why:** There's real overnight gap risk between decision time and next-day execution; a limit order bounds the worst acceptable fill price. Phase 0 optimizes for deterministic, debuggable behavior over execution sophistication.

## D3b — Decision Run moved from ~4:15pm to 9:00pm ET (supersedes the original post-close timing in D3)

**Decision:** The Decision Run happens at 9:00pm ET, not 15 minutes after close. The wait between close and decision widens from ~15 minutes to ~5 hours.

**Why:** Earnings and other market-moving news are often released after the close — sometimes hours after, not right at 4:00. A 15-minute buffer risks running the day's analysis on an incomplete picture; 9pm gives that information time to actually land first. This doesn't change anything else about D3 (still no same-evening order submission, still a separate next-morning Execution Run) — only how long the system waits before deciding.

## D3c — Idempotency design

**Decision:** The window-polling scheduler (D10a) can in principle trigger a Decision or Execution Run more than once inside the same target window (crash-and-restart, overlapping poll, scheduler retry) — "at most once" is not automatic just because the design intends it, so it's made explicit: order `order_id`s are generated once at Decision Run time and never regenerated; a Decision Run no-ops if that account already has today's plan; an Execution Run checks its own persisted per-order state before submitting anything and persists "submitted" immediately after each individual order (not batched at the end); `order_id` is passed to the broker as a client order id / idempotency key if supported; a single-flight guard prevents two overlapping triggers from both acting.

**Why:** Without this, a duplicate trigger could submit the same live order twice — a real financial risk, not a hypothetical one — or (for Decision Run) generate two different plans for the same day and leave it ambiguous which one is authoritative. This closes a gap `docs/RUNBOOK.md`'s Recovery section had flagged as open Phase 0 work without a concrete answer.

## D4 — Agent composition per account

**Decision:** Within each account: 3 independent analysts scoring candidates + a PM agent aggregating their output (stronger model).

**Why:** This is the core learning object of the project — analyst-level accuracy and confidence calibration need to be individually measurable, which requires the analysts to be separately identifiable, not folded into a single monolithic call.

## D5 — Baseline = open shadow incubation pool

**Decision:** Alongside the two live accounts, the system maintains an open pool of shadow candidates that never place real orders. It starts with two fixed benchmarks — a deterministic mean-reversion strategy, and SPY/QQQ buy-and-hold — and new candidates (new model configs, new strategy designs) can be added at any time with no cap on count.

**Why:** Without a baseline, there's no way to tell whether the multi-agent architecture — or the specific choice of model — is actually adding value versus market beta or luck. Keeping the pool open means testing a new idea later is just registering a new candidate, not an architecture change.

## D5a — Shadow → live graduation gate

**Decision:** A candidate graduates only if it (1) has run in the shadow pool for at least 8 weeks continuously, (2) has simultaneously beaten *both* the mean-reversion baseline and SPY/QQQ over that same window, and (3) has no material execution bugs and a clean risk-layer record. Meeting the gate only produces a notification — the system never opens an account or deposits capital on its own; that decision is Alicia's alone.

**Why:** The 8-week window matches the Phase 1 paper gate so there's one consistent bar, not two. Requiring it to beat *both* benchmarks (not just one) guards against a candidate that only looks good relative to a weak comparison. Opening a new funded account is a real financial decision and deliberately stays a rare, human-approved event rather than something automated — consistent with "Alicia carries zero routine operational load," since this is an occasional decision, not routine toil.

## D5b — TradingAgents added as a shadow-pool candidate

**Decision:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) is added to the shadow pool (D5) as a candidate — not adopted as Account A/B's core architecture, and not a replacement for the 3-analyst + PM design (D4).

**Why:** Its actual pipeline (5 analysts + bull/bear researcher debate + trader + a 3-way risk debate + portfolio manager) is exactly the "debate-style multi-agent architecture" already deferred to a future ablation rather than v1 (see `docs/ARCHITECTURE.md` "Explicitly out of scope for v1"). Adopting it wholesale into the live accounts would silently reopen that decision and would also add enough LLM call volume to put real pressure on the Claude Pro / ChatGPT Plus usage caps the ~$0-marginal-cost assumption in D2a depends on. The shadow pool is exactly where "does a heavier architecture actually do better" belongs — it costs nothing to the live accounts either way, and this is precisely the debate-style-architecture question the pool exists to eventually answer.

**Compatibility check:** its repo (Apache 2.0 licensed) has no broker/execution code anywhere — the `Trader` role's output is a structured `TraderProposal` (action/reasoning/optional entry price, stop-loss, sizing), and its own system prompt explicitly withholds external tools. This is consistent with D6 without needing to strip anything out. It's invoked per-symbol (`propagate(ticker, date)`), which fits inside our Decision Run's per-symbol loop rather than competing with our own scheduling.

**Remaining work before this candidate actually runs:** an adapter from `TraderProposal`'s shape (categorical action, no calibrated confidence score) to our analyst/OrderPlan schema (`score∈[-1,1]`, `confidence∈[0,1]`); its LLM cost is metered API like other shadow candidates, not covered by either live account's subscription.

## D6 — Risk layer authority

**Decision:** Risk rules live only in code, never in a prompt. Each live account runs its own independent risk-layer instance (parameters are identical, but state — today's order count, current drawdown — is per-account). Every intercepted/clipped instruction is logged as `{original instruction, rule triggered, actual action, account_id}`.

**Why:** Non-negotiable design principle for the whole project — an LLM's output is a proposal, never an instruction the risk layer has to honor. This is also why the Decision-stage LLM session must never hold a tool capable of placing a live order (see `docs/ARCHITECTURE.md` "Execution must not be an LLM session"): if the model that reasons about the trade also holds the tool that executes it, the "code enforces it, not the prompt" guarantee degrades into "the prompt tells the model to behave," regardless of how deterministic the risk math itself is.

## D6a — Daily loss circuit breaker widened to 5% (revises an earlier −1%)

**Decision:** The daily loss circuit breaker is 5% of the account's own equity (unrealized + realized), not 1%.

**Why:** The trading universe is narrow (~15–18 symbols) and at most 3 new positions open per day, so realistic concentration — and day-to-day account variance — is higher than a broadly diversified portfolio. A single ordinary bad day in one 20%-weighted position could push a −1% breaker past its threshold on pure noise, and since there's only one trading cycle per day (D3b), tripping it effectively cancels that day's only opportunity to open new positions — eroding the sample size the model-comparison analysis (see `docs/ARCHITECTURE.md` "Baseline & benchmark") depends on. The daily breaker's actual job is catching an acute malfunction, not absorbing ordinary volatility — the 10%/15% cumulative-drawdown tiers already exist to catch sustained bad performance. This lands back on the original draft's 5% figure, but under a materially different context than that draft assumed: no manual confirmation gate in front of it (D7). Worth watching in practice — a single bad day can now use half the headroom before the 10% tier blocks new positions, so if 5% turns out to trip often once the system is live, that's a signal to revisit, not just live with.

## D7 — Capital deployment pace

**Decision:** Once the paper gate passes, both accounts are funded with their full $500–1000 at once — no $250 starter tranche, no requirement to manually approve the first 20 trades.

## D8 — Trading universe

**Decision:** Both accounts share one fixed allowlist (~15 liquid large-caps + 2–3 ETFs), reviewed manually once a month. This is the one recurring human touchpoint that's kept, deliberately low-frequency.

## D9 — Prohibited instruments (v1)

**Decision:** No shorting, no leverage, no options. Rejected at the adapter layer, both accounts.

## D10 — Deployment

**Decision:** Account A's Decision Run is a Claude Code cloud scheduled routine; Account B's Decision Run is a Codex cloud Automation; the shadow pool's Decision Run runs on GitHub Actions (no live-account subscription needed, metered API is fine given the low call volume). The Execution Run for both live accounts runs uniformly on GitHub Actions as plain, non-agentic code — never inside an LLM session — for the reason in D6.

## D10a — Timezone correctness

**Decision:** No cron job is scheduled at a fixed UTC time. Instead, the scheduler triggers every 5–10 minutes inside a loose window around the target time, and the script itself computes the real current time in `America/New_York` (e.g. via Python's `zoneinfo`) and no-ops if it isn't inside the target window yet.

**Why:** US market hours are anchored to ET, and DST transitions (March/November) would silently shift any fixed-UTC schedule by an hour twice a year. GitHub Actions cron has no timezone parameter, and whether Claude Code's/Codex's own cloud scheduling natively supports IANA timezones is unconfirmed (see Open Questions). Computing real ET time at runtime is correct regardless of what the underlying scheduler assumes, and needs no manual twice-a-year cron edits.

## D11 — No Fidelity/Schwab monitoring pipeline

**Decision:** Not built in v1.

**Why:** Schwab requires recurring OAuth token renewal; Fidelity requires a weekly manual CSV export. Both are exactly the kind of recurring operational toil the zero-ops constraint (D-zero-ops, see `docs/ARCHITECTURE.md` §Positioning) rules out. A multi-account weekly report is a separate project if wanted later.

## D12 — Wash-sale detection (added; supersedes the original "excluded from v1" call)

**Decision:** A wash-sale guard is part of the risk layer, not excluded. IRS wash-sale rules apply per taxpayer across *all* accounts, not per account — and both live accounts are under the same person. It blocks buys only (new entries/top-ups), never blocks a stop-loss/take-profit/exit sell (risk management doesn't defer to tax outcome), and covers a configurable linked-account list (both live accounts, plus any others Alicia adds).

**Why this changed:** The original draft excluded wash-sale detection as "out of scope for a learning project." That was correct reasoning for a single account; it stopped being correct once the design grew to two live accounts under one person's name, where a loss sale in one and a repurchase in the other is a real, not hypothetical, wash sale.

## D13 — Per-cycle stop-loss/take-profit recheck (added)

**Decision:** Every Execution Run rechecks stop-loss/take-profit conditions on *all currently held positions* in that account, independent of whatever the day's `OrderPlan` says. A triggered stop-loss or take-profit fires regardless of how compelling a new thesis sounds.

**Why this changed:** The original Execution Agent design only revalidated the day's new `OrderPlan`; it had no independent check on existing positions. A convincing new thesis should never be able to cancel a stop-loss.

## D14 — Initial funding is a validation allocation, not a permanent cap (supersedes the fixed-cap implication in D1, D2b, and D7)

**Decision:** Each live account still starts with $500–1000, but that range is an initial real-money validation allocation rather than play money or a permanent ceiling. If an account later shows stable, attributable profitability after trading costs and while respecting the risk rules, Alicia may manually approve an appropriate funding increase. The system never deposits funds, increases an allocation, or relaxes risk controls automatically. The evidence threshold and amount of any increase must be reviewed explicitly before that increase rather than being inferred from a short winning streak.

**Why this changed:** The original wording correctly emphasized that learning and valid comparison matter more than short-term returns, but it incorrectly implied that returns would never matter financially and that account size would remain fixed forever. The intended posture is staged capital deployment: validate with a small amount first, then retain the option to scale cautiously if durable live evidence justifies it.

## D15 — Runtime state, audit artifacts, and Git use separate storage responsibilities

**Decision:** Correctness-critical operational state lives in a transactional store: OrderPlans, append-only ExecutionEvents, leases, per-account risk state, broker acknowledgements, and reconciliation results. Large immutable evidence lives in object storage: frozen DecisionSnapshots, raw model outputs, prompt/tool traces, detailed logs, and broker-response artifacts. Each transactional record references its audit objects by URI and content hash. Git contains code, configuration, schemas, migrations, docs, and sanitized reports; scheduled runs do not commit/push live execution state.

**Why:** Order submission needs atomicity, unique constraints, conditional updates, and a cross-runner lease. Git commits provide none of those semantics and introduce push races between accounts and schedulers. Large audit blobs do not need to participate in every correctness decision and would make either Git or a transactional database unnecessarily heavy. The split keeps the immediate decision state small and strongly consistent while preserving complete evidence for later review.

## D16 — Unknown broker outcomes fail closed (supersedes D3c's strict at-most-once claim)

**Decision:** Execution records `submission_started` before a broker call and `broker_acknowledged` only after receiving a broker order identifier. If a process crashes in between, the order enters `unknown`; it is reconciled against broker history before any retry. A transactional cross-runner lease replaces the runner-local single-flight marker. A stable client idempotency key is used if Robinhood supports one. Without broker-side idempotency, an ambiguous order is never blindly resubmitted, and the design claims fail-closed reconciliation rather than strict at-most-once submission.

**Why:** A broker can accept an order just before the runner crashes and before local state records the acknowledgement. No local "check then submit" sequence can eliminate that window. Blind retry risks a duplicate live order; stopping and reconciling is the safe behavior when the external outcome cannot be proven.

## D17 — Feasibility-first staged rollout (supersedes D7's simultaneous two-account start)

**Decision:** Delivery proceeds through explicit gates: Phase −1 broker/scheduler feasibility; Phase 0 deterministic core and failure-injection tests; Phase 1 full paper/shadow operation; Phase 2 one-account live canary; Phase 3 two-account live comparison. D14's $500–1000 range remains the initial live validation allocation, but the accounts are not funded simultaneously. The second account starts only after the first proves credential lifecycle, fills, reconciliation, alerts, and recovery. Additional shadow architectures wait until the core comparison pipeline is stable.

**Why:** The headless Robinhood MCP path, two-account binding, exact order schemas, fractional-order support, reconciliation, client idempotency, and scheduler secret behavior are foundational assumptions, not implementation details. Proving them first prevents building the deterministic core around an unavailable broker boundary. A one-account canary limits operational unknowns before duplicating them.

## D18 — Controlled evaluation and promotion (supersedes D5a's profit-based 8-week gate)

**Decision:** Eight continuous weeks is an operational-stability gate: no unresolved reconciliation, duplicate cycle, missed-run blind spot, or material risk defect. Before a candidate starts, its evaluation record fixes the minimum sample size, untouched holdout period, after-cost benchmark comparisons, turnover/slippage treatment, and drawdown/risk limits. Promotion requires passing both the operational and pre-registered evidence gates plus human approval. A two-account live equity-curve difference is reported as evidence, not causal proof of model superiority.

**Why:** Forty or so trading days and an open-ended candidate pool make it easy to promote a lucky winner. Selecting thresholds after seeing results creates the same bias. Frozen inputs, pre-registered criteria, a holdout period, and risk-adjusted after-cost reporting make the comparison more informative while keeping the final funding decision human.

## D19 — News/fundamental input source: free/open financial data primary; X excluded from v1

**Decision:** The DecisionSnapshot's news/fundamental input is sourced from free/open financial data providers — e.g. Yahoo Finance, Google Finance, Fidelity's public quote/news pages — covering the trading universe, pulled ahead of the 9:00pm ET Decision Run and frozen into the snapshot like any other input. X is excluded from v1. Reconsider it only after the primary pipeline is stable and a pre-registered experiment demonstrates incremental value, current endpoint pricing is known and capped, X explicitly approves external LLM inference plus the retention design, and deletion/edit compliance is reconciled with immutable DecisionSnapshots.

**Why:** X now has feasible pay-per-use read/search access, but useful recall has not been demonstrated and variable spend is per returned resource. More importantly, X requires deleted or modified content to be removed or updated, conflicting with Ripple's immutable audit inputs, and its public terms do not expressly authorize sending licensed content to an external LLM inference provider. Those costs and policy seams add operational burden to an optional source with no measured incremental value. See `docs/feasibility/x-api-news-source.md`.

## D20 — Repository Python runtime is 3.12 via uv

**Decision:** Ripple's default repository Python is the latest available Python 3.12 patch release selected by the root `.python-version` file. Local and scheduled repository commands enter that environment through `uv run`; they do not rely on or replace the host's unqualified `python3`.

**Why:** The first two local Codex Automation probes invoked macOS's Python 3.8.1 and failed before producing evidence because that runtime does not include `zoneinfo`. Pinning the repository's minor version makes timezone behavior and test execution reproducible without mutating an operating-system-managed interpreter. The Automation path still needs a successful rerun before scheduler runtime compatibility is considered proven.

## D21 — Scheduled uv invocations use a temporary cache

**Decision:** Scheduled Ripple Python commands use `uv run --no-cache` rather than bare `uv run`.

**Why:** The third local Codex Automation probe selected Python 3.12 with `uv run` but exited 2 before Python startup because its sandbox could not write uv's default cache at `/Users/Alicia/.cache/uv`. `--no-cache` uses a temporary cache for one invocation, avoiding that proven cache-permission boundary. A successful Automation rerun remains required before scheduler compatibility is considered proven.

## D22 — Runner-owned OAuth state is versioned and restart-safe

**Decision:** Each live-account Execution Run uses its own OAuth client registration and one private credential record shared only by a one-time interactive bootstrap command and that account's plain headless runner. The record atomically stores the SDK token and client-registration models, absolute access-token expiry, and validated MCP resource/authorization-server metadata. A version-pinned adapter restores that state before the first request and replaces it with compare-and-swap semantics after refresh. The headless path never initiates authorization or client registration; missing, mismatched, expired-without-refresh, refresh-rejected, or concurrently superseded state fails closed and requires a human bootstrap.

Before contacting the authorization server for a rotating-token refresh, the runner transactionally records `refresh_started` with its lease fencing token and expected credential revision. Success is complete only when the new secret is stored and the transactional record points to that exact version. A crash, expired lease, or ambiguous response before completion produces `refresh_unknown`; it never authorizes automatic retry with the old refresh token. Secret-store aliases are discovery aids, not correctness pointers, when their visibility is eventually consistent.

**Why:** An authenticated Codex MCP session proves Robinhood account access but does not give the independent execution runner an appropriate credential lifecycle. The current Python MCP SDK v2 storage interface persists token/client information, but its fresh-process initialization does not restore the absolute expiry or discovered token endpoint. A short-lived scheduler can therefore send an age-unknown stale bearer token, then fall into interactive authorization, or refresh against the wrong endpoint. Persisting and validating the missing restart state behind one deep module keeps this SDK-specific workaround local and testable. Static environment injection remains useful for the disposable access-token probe, but cannot safely preserve rotated refresh tokens in production. A lease and secret-store CAS protect local state but cannot cancel a refresh request already accepted by an external server, so ambiguous rotation needs the same fail-closed treatment as D16's unknown order submission. See `docs/feasibility/mcp-python-oauth-client.md` and `docs/feasibility/github-actions-oauth-secret-store.md`.

## D23 — Persist decision-stage decimal values as strings

**Decision:** `DecisionSnapshot` and `OrderPlan` documents serialize weights, quantities, dollar amounts, prices, and tolerances as base-10 decimal strings, never JSON floating-point numbers or percent-suffixed text. Weights and tolerances use ratios (`"0.15"` means 15%; `"0.005"` means 0.5%). Planned orders use the broker-aligned field name `quantity` rather than the earlier illustrative `qty` abbreviation. Exact scale, range, sum, and order-type conditional validation remains part of the Phase 0 field-level schema work.

**Why:** Financial values must round-trip exactly across Python, JSON, transactional storage, and the broker adapter. Binary floating point can silently change decimal intent, while percent suffixes require context-dependent parsing. Decimal strings preserve the authored value and align with Robinhood's declared quantity and price inputs without coupling the domain document to a Python-only numeric type.

## Open-source references consulted

- [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) — started as an architecture reference, later added as an actual shadow-pool candidate (see D5b).
- [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) — multi-agent analyst/PM architecture reference.
- [YizhiSong/FriesTrader](https://github.com/YizhiSong/FriesTrader) — a real, deployed Robinhood Agentic trading agent with a similar decision/execution split and mechanical risk-rule scripts. Read, not forked. Its per-cycle stop-loss/take-profit recheck and cross-account wash-sale guard directly informed the two entries above. One meaningful difference worth being deliberate about: its "mechanical rules the model cannot override" claim covers the risk *arithmetic* (deterministic scripts), but the actual gate on whether an order gets placed is enforced by prompt instructions to the same LLM session that holds the order-placing tool — not a code-level barrier the LLM has no path around. This project's D6 is intentionally stricter: the Decision-stage LLM is never given an order-placing tool at all.
