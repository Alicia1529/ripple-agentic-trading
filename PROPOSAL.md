# Ripple Trading — Proposal

**Status:** The paper MVP now supports two isolated account lanes; hosted-cycle and live-account acceptance remain operational work. Production v1 follows the intentionally lean hosted-routine pattern in D26 and the minimal two-account extension in D27; the accepted reliability trade-offs are documented rather than silently overclaimed. This file is the *what and why*; the living technical spec is `docs/ARCHITECTURE.md`, and the record of how each decision was reached is `docs/DECISIONS.md`.

## What this is

A deliberately small trading system whose first production release can run two Robinhood Agentic accounts through isolated hosted LLM routines: each account has one decision lane and one execution lane. The same concrete commands and risk code are reused for both accounts; configuration, state, broker connection, and live activation remain separate. Rich model-comparison infrastructure remains later work.

## Why

The initial $500–1000 per live account is a deliberately small validation allocation, not a fixed lifetime ceiling or play money. The goals are:

1. Hands-on practice building an LLM decision pipeline with deterministic, inspectable risk calculations and explicit operational trade-offs.
2. A controlled, auditable comparison against simple baselines, without overstating what a small live sample can prove.
3. If live results eventually demonstrate stable, attributable profitability after costs and within the risk rules, selectively increase account funding by a manually approved amount. The system never increases funding on its own.

The person running this expects low ongoing maintenance time. Production v1 therefore delegates Robinhood credential lifecycle to the hosted MCP connection and uses Git-backed JSON/JSONL state. This is simpler but deliberately accepts low-probability duplicate, ambiguous-outcome, prompt/tool-use, and pre-log-crash risks while the account remains at its small validation allocation. Those risks must be reconsidered before adding capital or accounts.

## Scope at a glance

- **Paper MVP**: each of two account configurations can independently run frozen input → decision → deterministic risk scripts → dry-run order record → sanitized report.
- **Production target**: connect each isolated Execution Routine to its own platform-managed Robinhood account connection, keep each `execution.mode` human-owned, and enable a lane only after its reviewed dry-run cycle.
- **Eight-week capital gate**: after eight continuous live weeks with no unresolved execution or risk defect, the owner may review whether to increase the account allocation. No increase is automatic.
- **Exactly two account lanes**, implemented as two concrete configurations over the same commands—not an account framework, batch coordinator, or shared ledger. See D27.
- **Decision and execution are separate sessions**: the Decision Routine has no broker write tools; the next-morning Execution Routine may call them but must not redo investment reasoning.
- **Risk calculations are deterministic scripts**: production v1 relies on the Execution Routine to pass correct inputs and follow their output. It does not claim that the LLM is structurally unable to bypass them.
- **Minimal hosted state**: a private Git repository carries configuration, per-cycle plans, JSONL logs, and sanitized reports between fresh routine sessions. Broker credentials remain only in the platform-managed MCP connection.
- **Deferred comparison infrastructure**: analyst ensembles, statistical A/B evaluation, additional accounts, and a controlled shadow pool remain outside the launch path.
- Explicitly **not** attempting: multi-broker integration, intraday trading, tax-lot optimization, or anything that would reintroduce recurring manual maintenance. See `docs/ARCHITECTURE.md` "Explicitly out of scope for v1" for the full list and reasoning.

## MVP definition

The MVP is deliberately dry-run only. Each account lane has one fixed allowlist, one Decision Routine, one Execution Routine, deterministic risk scripts, one per-cycle OrderPlan file, account-scoped JSONL decision/order logs, and one sanitized report. Its repository acceptance test runs both lanes into separate state roots and proves that a plan cannot execute against the other account's configuration. Hosted acceptance still requires complete scheduled decision-to-dry-run cycles with no live order placed.

The MVP does not include a dashboard, backtesting framework, cloud deployment, multiple models, multiple accounts, analyst debate, shadow strategies, generic plugins, or production broker writes. Those omissions are scope decisions, not unfinished MVP defects.

The one-week live release adds only the platform-managed Robinhood MCP connection, the human-owned live gate, and exact routine prompts. It does not add a plain executor, custom OAuth lifecycle, transactional database, exactly-once submission, or crash-safe reconciliation.

## Where to go next

- Building or reviewing code: read `docs/ARCHITECTURE.md` (current system design) and `docs/DECISIONS.md` (why it's built this way) before touching anything.
- Safety and correctness constraints: read `docs/INVARIANTS.md`.
- Current implementation status: `docs/TODO.md`.
- Operational procedures (kill switch, what to do when notified, deploy/debug/recovery): `docs/RUNBOOK.md`.
- Historical drafts that led here (two independent proposals plus the research that reconciled them, all superseded): `docs/archive/`.

## Boundaries

The Decision Routine cannot execute trades. The separately configured Execution Routine may place trades through the platform-managed Robinhood MCP after the human enables live mode. The platform, not repository code or the model-visible artifacts, stores the credential. Live trading decisions and their consequences belong to the account owner alone.
