# Ripple Trading — Proposal

Ripple is a deliberately small trading system for learning how an LLM decision layer can operate behind deterministic, inspectable safety calculations. The current repository MVP runs fixture-backed dry cycles for exactly two isolated Robinhood Agentic account lanes. Hosted acceptance and live execution remain unfinished operational work.

Each lane has its own configuration, state root, Decision Routine, Execution Routine, broker connection, and human-owned live gate. Both lanes reuse the same CLI, schemas, risk code, and schedule pattern. There is no shared ledger, account coordinator, generic strategy framework, or third-account support.

The initial live allocation is $500–1000 per account. It limits exposure while the owner gathers real operational evidence; the system never deposits or increases capital. After eight continuous live weeks, the owner may review after-cost results and incidents. Increased capital or a third account requires a new architecture review and explicit approval.

## Current path

1. A fresh Decision Routine gathers allowed facts after the latest completed session, applies the configured strategy, and publishes one immutable `DecisionSnapshot` and `OrderPlan`.
2. A separate next-morning Execution Routine loads that plan and current account facts, runs deterministic revalidation, and in dry-run mode records proposed broker arguments without a write.
3. Credential-free plans, JSONL records, and reports pass between sessions through a private Git repository. Broker credentials remain in the hosted MCP connection.
4. Each lane must pass a complete scheduled dry cycle and account-binding review before Alicia can enable its human-owned live gate.

The hosted MVP deliberately accepts prompt/tool-use mistakes, duplicate calls, ambiguous timeouts, crash-before-log gaps, configuration misuse, and model or prompt drift at the small validation allocation. These are documented limits, not prevented failure modes.

## Scope boundaries

Current work is the two-account long-only loop, deterministic risk and revalidation, hosted prompts, account isolation, operational recovery, and evidence needed for safe activation. The MVP excludes a non-LLM executor, transactional journal, exactly-once submission, automatic reconciliation, custom OAuth, additional brokers or accounts, intraday trading, tax-lot optimization, comparison/shadow infrastructure, dashboards, and automated capital changes.

Read `docs/ARCHITECTURE.md` for the current technical contract, `docs/INVARIANTS.md` for safety rules, `docs/TODO.md` for unfinished acceptance work, and `docs/RUNBOOK.md` for operation and recovery. Live trading and its consequences remain the account owner's responsibility.
