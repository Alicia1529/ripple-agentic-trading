# Decisions

Append-only decision log (ADR-style). Each entry records what was decided and why, at the time it was decided. Don't edit past entries to "fix" wording — if a decision changes, add a new entry that supersedes the old one and say so explicitly. `docs/ARCHITECTURE.md` reflects the *current* state that results from these decisions; this file explains *how we got here*.

## D1 — Real objective

**Decision:** Learn agent-system design + build a genuinely comparable baseline, not chase returns.

**Why:** The capital involved ($500–1000 per live account) is too small for returns to matter financially. The actual goal is hands-on experience building "untrusted LLM decision layer + deterministic code-enforced risk layer," which is structurally the same problem as production LLM-safety system design.

## D2 — Number of live accounts

**Decision:** Two Robinhood Agentic live accounts, both under the same Robinhood login, each running a full independent 3-analyst + PM pipeline. Alpaca is used only for paper validation, not as a third parallel account.

**Why:** We need a real, live A/B comparison of two model configurations. Each account's own broker statement is authoritative — this avoids the "shared-account multi-strategy" conflict-resolution machinery (which symbol belongs to which strategy, no silent netting, ledger-vs-broker reconciliation invariants) that a single shared account would require. Two accounts under one login add negligible operational overhead compared to spreading across multiple brokers (which was the actual concern behind "don't want too many accounts").

## D2a — Model assignment per account

**Decision:** Both accounts run the *same* analyst/PM architecture, risk layer, universe, and cadence — the only difference is which model powers them. Concretely: **Account A = Claude** (Decision Run as a Claude Code cloud scheduled routine, using an existing Claude Pro subscription), **Account B = OpenAI** (Decision Run as a Codex cloud Automation, using an existing ChatGPT Plus subscription).

**Why:** Holding everything else constant makes the comparison a clean model-capability comparison, not a confound of different strategy designs. Both accounts piggyback on subscriptions already being paid for, so marginal LLM cost is close to $0 — pending confirmation that usage caps are sufficient (see Open Questions in `docs/ARCHITECTURE.md`), with metered API billing as the documented fallback if not.

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

## D4 — Agent composition per account

**Decision:** Within each account: 3 independent analysts scoring candidates + a PM agent aggregating their output (stronger model).

**Why:** This is the core learning object of the project — analyst-level accuracy and confidence calibration need to be individually measurable, which requires the analysts to be separately identifiable, not folded into a single monolithic call.

## D5 — Baseline = open shadow incubation pool

**Decision:** Alongside the two live accounts, the system maintains an open pool of shadow candidates that never place real orders. It starts with two fixed benchmarks — a deterministic mean-reversion strategy, and SPY/QQQ buy-and-hold — and new candidates (new model configs, new strategy designs) can be added at any time with no cap on count.

**Why:** Without a baseline, there's no way to tell whether the multi-agent architecture — or the specific choice of model — is actually adding value versus market beta or luck. Keeping the pool open means testing a new idea later is just registering a new candidate, not an architecture change.

## D5a — Shadow → live graduation gate

**Decision:** A candidate graduates only if it (1) has run in the shadow pool for at least 8 weeks continuously, (2) has simultaneously beaten *both* the mean-reversion baseline and SPY/QQQ over that same window, and (3) has no material execution bugs and a clean risk-layer record. Meeting the gate only produces a notification — the system never opens an account or deposits capital on its own; that decision is Alicia's alone.

**Why:** The 8-week window matches the Phase 1 paper gate so there's one consistent bar, not two. Requiring it to beat *both* benchmarks (not just one) guards against a candidate that only looks good relative to a weak comparison. Opening a new funded account is a real financial decision and deliberately stays a rare, human-approved event rather than something automated — consistent with "Alicia carries zero routine operational load," since this is an occasional decision, not routine toil.

## D6 — Risk layer authority

**Decision:** Risk rules live only in code, never in a prompt. Each live account runs its own independent risk-layer instance (parameters are identical, but state — today's order count, current drawdown — is per-account). Every intercepted/clipped instruction is logged as `{original instruction, rule triggered, actual action, account_id}`.

**Why:** Non-negotiable design principle for the whole project — an LLM's output is a proposal, never an instruction the risk layer has to honor. This is also why the Decision-stage LLM session must never hold a tool capable of placing a live order (see `docs/ARCHITECTURE.md` "Execution must not be an LLM session"): if the model that reasons about the trade also holds the tool that executes it, the "code enforces it, not the prompt" guarantee degrades into "the prompt tells the model to behave," regardless of how deterministic the risk math itself is.

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

## Open-source references consulted

- [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) and [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) — multi-agent analyst/PM architecture references.
- [YizhiSong/FriesTrader](https://github.com/YizhiSong/FriesTrader) — a real, deployed Robinhood Agentic trading agent with a similar decision/execution split and mechanical risk-rule scripts. Read, not forked. Its per-cycle stop-loss/take-profit recheck and cross-account wash-sale guard directly informed the two entries above. One meaningful difference worth being deliberate about: its "mechanical rules the model cannot override" claim covers the risk *arithmetic* (deterministic scripts), but the actual gate on whether an order gets placed is enforced by prompt instructions to the same LLM session that holds the order-placing tool — not a code-level barrier the LLM has no path around. This project's D6 is intentionally stricter: the Decision-stage LLM is never given an order-placing tool at all.
