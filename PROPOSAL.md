# Ripple Trading — Proposal

**Status:** Building a three-day single-account paper MVP, followed by a one-week target for the first live release. Production v1 follows the intentionally lean hosted-routine pattern in D26; the accepted reliability trade-offs are documented rather than silently overclaimed. This file is the *what and why*; the living technical spec is `docs/ARCHITECTURE.md`, and the record of how each decision was reached is `docs/DECISIONS.md`.

## What this is

A deliberately small trading system whose first production release runs one Robinhood Agentic account through two isolated hosted LLM routines: one decides and one executes. The delivery target is a working paper MVP in three development days and live operation within one week. Multi-account model comparison remains a later expansion goal, not a prerequisite for launching the first account.

## Why

The initial $500–1000 per live account is a deliberately small validation allocation, not a fixed lifetime ceiling or play money. The goals are:

1. Hands-on practice building an LLM decision pipeline with deterministic, inspectable risk calculations and explicit operational trade-offs.
2. A controlled, auditable comparison against simple baselines, without overstating what a small live sample can prove.
3. If live results eventually demonstrate stable, attributable profitability after costs and within the risk rules, selectively increase account funding by a manually approved amount. The system never increases funding on its own.

The person running this expects low ongoing maintenance time. Production v1 therefore delegates Robinhood credential lifecycle to the hosted MCP connection and uses Git-backed JSON/JSONL state. This is simpler but deliberately accepts low-probability duplicate, ambiguous-outcome, prompt/tool-use, and pre-log-crash risks while the account remains at its small validation allocation. Those risks must be reconsidered before adding capital or accounts.

## Scope at a glance

- **Three-day MVP target**: two hosted routines run one account through frozen input → decision → deterministic risk scripts → dry-run order record → sanitized report.
- **One-week production target**: connect the isolated Execution Routine to the platform-managed Robinhood MCP, keep `execution.mode` human-owned, and enable live after one reviewed dry-run cycle.
- **Eight-week capital gate**: after eight continuous live weeks with no unresolved execution or risk defect, the owner may review whether to increase the account allocation. No increase is automatic.
- **One-account production v1**, with account-scoped records and narrow broker/repository boundaries that preserve a straightforward path to the later two-account target — see `docs/DECISIONS.md` D24.
- **Decision and execution are separate sessions**: the Decision Routine has no broker write tools; the next-morning Execution Routine may call them but must not redo investment reasoning.
- **Risk calculations are deterministic scripts**: production v1 relies on the Execution Routine to pass correct inputs and follow their output. It does not claim that the LLM is structurally unable to bypass them.
- **Minimal hosted state**: a private Git repository carries configuration, per-cycle plans, JSONL logs, and sanitized reports between fresh routine sessions. Broker credentials remain only in the platform-managed MCP connection.
- **Deferred comparison infrastructure**: additional accounts, model A/B lanes, and a controlled shadow pool are added only after the single-account production path is stable.
- Explicitly **not** attempting: multi-broker integration, intraday trading, tax-lot optimization, or anything that would reintroduce recurring manual maintenance. See `docs/ARCHITECTURE.md` "Explicitly out of scope for v1" for the full list and reasoning.

## MVP definition

The three-day MVP is deliberately dry-run only. It has one fixed allowlist, one Decision Routine, one Execution Routine, deterministic risk scripts, one per-cycle OrderPlan file, append-only JSONL decision/order logs, and one sanitized report. Its acceptance test is one complete scheduled decision-to-dry-run cycle with no live order placed.

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
