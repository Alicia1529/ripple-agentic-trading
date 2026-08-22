# Ripple Trading — Proposal

**Status:** Architecture draft complete; broker and scheduler feasibility not yet verified; implementation not started. This file is the *what and why*; the living technical spec is `docs/ARCHITECTURE.md`, and the record of how each decision was reached is `docs/DECISIONS.md`.

## What this is

A paper-first trading-system experiment built primarily to learn agent-system design and to test whether the system can produce durable, risk-adjusted returns. The target end state is two small Robinhood Agentic accounts running the same 3-analyst + PM pipeline — one powered by Claude, one by OpenAI — after the broker integration and deterministic execution core pass explicit feasibility, paper, and single-account live-canary gates. Alongside them, a controlled shadow pool (starting with a deterministic mean-reversion strategy and SPY/QQQ buy-and-hold) provides evidence about whether the multi-agent approach or model choice adds value over simpler alternatives. A two-account equity-curve difference is evidence, not by itself causal proof of model superiority.

## Why

The initial $500–1000 per live account is a deliberately small validation allocation, not a fixed lifetime ceiling or play money. The goals are:

1. Hands-on practice building an "untrusted LLM decision layer + deterministic, code-enforced risk layer" system — the same structural problem as production LLM-safety system design.
2. A controlled, auditable comparison against simple baselines, without overstating what a small live sample can prove.
3. If live results eventually demonstrate stable, attributable profitability after costs and within the risk rules, selectively increase account funding by a manually approved amount. The system never increases funding on its own.

The person running this expects low ongoing maintenance time. The target is therefore **low routine operational load after a stable pilot**, not an unverified promise of zero oversight: reconciliation, health checks, credential-expiry checks, and missed-run detection are automated, while ambiguous broker outcomes and material risk events fail closed and notify a human.

## Scope at a glance

- **Staged rollout**: broker/scheduler feasibility spike → deterministic core → full paper/shadow run → one-account live canary → two-account live comparison. No live funding happens before the preceding gate passes.
- **Two-account target state**, same architecture and frozen inputs, different model per account (Account A = Claude, Account B = OpenAI/Codex) — see `docs/DECISIONS.md` D2/D2a and D17.
- **Decision and execution are separate stages**: signals are generated once daily after market close and persisted as an immutable `OrderPlan`; execution happens the next morning, with outcomes recorded as separate append-only events.
- **Risk rules live only in code, never in a prompt** — the LLM proposes, code disposes, and the model that reasons about a trade never holds the tool that executes it.
- **Purpose-built storage boundaries**: a transactional store holds correctness-critical operational state; object storage holds large immutable audit artifacts; Git holds code, configuration, schemas, docs, and sanitized reports — not live execution state.
- **A controlled shadow pool** for testing new model configs or strategy ideas on paper. Evaluation rules are registered before a candidate starts, and promotion always requires a human decision.
- Explicitly **not** attempting: multi-broker integration, intraday trading, tax-lot optimization, or anything that would reintroduce recurring manual maintenance. See `docs/ARCHITECTURE.md` "Explicitly out of scope for v1" for the full list and reasoning.

## Where to go next

- Building or reviewing code: read `docs/ARCHITECTURE.md` (current system design) and `docs/DECISIONS.md` (why it's built this way) before touching anything.
- Safety and correctness constraints: read `docs/INVARIANTS.md`.
- Current implementation status: `docs/TODO.md`.
- Operational procedures (kill switch, what to do when notified, deploy/debug/recovery): `docs/RUNBOOK.md`.
- Historical drafts that led here (two independent proposals plus the research that reconciled them, all superseded): `docs/archive/`.

## Boundaries

Claude (in any interface) is responsible for design, code, backtesting tools, and the reporting pipeline; it does not execute trades, hold credentials, or give buy/sell advice on specific securities. Live trading decisions and their consequences belong to the account owner alone.
