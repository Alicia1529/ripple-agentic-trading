# Ripple Trading — Proposal

**Status:** Design complete, implementation not started. This file is the *what and why*; the living technical spec is `docs/ARCHITECTURE.md`, and the record of how each decision was reached is `docs/DECISIONS.md`.

## What this is

A small, real-money trading system built to learn agent-system design, not to make money. Two live Robinhood Agentic accounts each run an independent 3-analyst + PM pipeline — one powered by Claude, one by OpenAI — as a genuine, live A/B comparison of model capability under identical architecture, risk rules, and trading universe. Alongside them, an open "shadow" pool of paper candidates (starting with a deterministic mean-reversion strategy and SPY/QQQ buy-and-hold) provides the baseline needed to tell whether the multi-agent approach — or the choice of model — is actually adding value, versus market beta or luck.

## Why

The capital at stake ($500–1000 per live account) is financially irrelevant. The actual goals:

1. Hands-on practice building an "untrusted LLM decision layer + deterministic, code-enforced risk layer" system — the same structural problem as production LLM-safety system design.
2. A genuinely comparable answer to "does any of this beat doing nothing" — which requires running a real baseline alongside the live accounts, not just trusting the agent's own numbers.

The person running this expects near-zero ongoing maintenance time going forward, so the entire design is built around **zero routine operational load**: it runs unattended, and only ever interrupts for rare, high-stakes events (a risk breaker firing, a shadow candidate clearing its graduation gate) — never for daily or weekly manual chores.

## Scope at a glance

- **Two live accounts**, same architecture, different model per account (Account A = Claude, Account B = OpenAI/Codex) — see `docs/DECISIONS.md` D2/D2a.
- **Decision and execution are separate stages**: signals are generated once daily after market close and persisted as an immutable plan; execution happens the next morning after the market opens, never the same evening — see `docs/ARCHITECTURE.md`.
- **Risk rules live only in code, never in a prompt** — the LLM proposes, code disposes, and the model that reasons about a trade never holds the tool that executes it.
- **An open shadow pool** for testing new model configs or strategy ideas on paper, with an explicit, human-approved gate before any of them get real money.
- Explicitly **not** attempting: multi-broker integration, intraday trading, tax-lot optimization, or anything that would reintroduce recurring manual maintenance. See `docs/ARCHITECTURE.md` "Explicitly out of scope for v1" for the full list and reasoning.

## Where to go next

- Building or reviewing code: read `docs/ARCHITECTURE.md` (current system design) and `docs/DECISIONS.md` (why it's built this way) before touching anything.
- Safety and correctness constraints: read `docs/INVARIANTS.md`.
- Current implementation status: `docs/TODO.md`.
- Operational procedures (kill switch, what to do when notified, deploy/debug/recovery): `docs/RUNBOOK.md`.
- Historical drafts that led here (two independent proposals plus the research that reconciled them, all superseded): `docs/archive/`.

## Boundaries

Claude (in any interface) is responsible for design, code, backtesting tools, and the reporting pipeline; it does not execute trades, hold credentials, or give buy/sell advice on specific securities. Live trading decisions and their consequences belong to the account owner alone.
