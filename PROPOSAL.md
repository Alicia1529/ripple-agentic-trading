# Ripple Trading — Proposal

**Current stage:** the repository implements a two-account, fixture-backed dry-run MVP. Account A is moving toward hosted scheduled acceptance; the reviewed live broker-write loop remains unfinished. Account B has no hosted Decision or Execution path.

This document explains what Ripple is, why it exists, and what the current release is meant to prove. `docs/ARCHITECTURE.md` is the current technical design, `docs/DECISIONS.md` records why durable choices were made, and `docs/TODO.md` tracks unfinished work.

## What this is

Ripple is a deliberately small system for learning how an LLM-authored trading decision can move through deterministic, inspectable safety checks before execution.

The repository models exactly two isolated Robinhood Agentic account lanes. Both reuse the same CLI, schemas, and deterministic risk code while keeping configuration and state separate. Account A is the current hosted lane, with its own Decision Routine, Execution Routine, broker connection, and human-owned live gate. Account B remains fixture-backed repository evidence only.

## Why it exists

Ripple has two connected learning goals:

1. **AI-native development:** learn how to turn broad ideas into bounded, reviewable slices that produce working evidence rather than speculative infrastructure.
2. **Agentic trading:** learn which responsibilities fit an LLM, which must remain deterministic, and where prompt-mediated execution still leaves real operational risk.

The project is not trying to prove that an AI can reliably beat the market from a small sample. It is trying to make the full decision-to-execution loop understandable: what the model saw, what it decided, what code allowed or rejected, what would be sent to the broker, and where human authority remains required.

## Current release

The current repository proves this vertical slice without broker writes:

```text
credential-free fixture
        ↓
DecisionSnapshot + OrderPlan
        ↓
deterministic execution revalidation
        ↓
proposed broker arguments + JSONL evidence + readable report
```

The two fixture lanes run this path independently and reject cross-account use. Hosted acceptance proves Account A's same prior-evening Decision → next-weekday dry Execution path in scheduled fresh sessions with its intended broker connection.

Live activation is a later gate. It requires the narrow MCP read/review/place/cancel loop to be implemented and reviewed, the intended account binding to be proven, a complete scheduled dry cycle to be inspected, and the owner to explicitly change that lane's mode.

## Scope at a glance

- **Exactly two concrete repository lanes:** Account A owns the current hosted path; Account B remains fixture-backed. There is no shared account collection, batch coordinator, or third-account framework.
- **Separate Decision and Execution sessions:** investment reasoning happens before the plan is frozen; next-morning execution does not create a new thesis.
- **Deterministic risk authority:** checked-in code validates plan shape, account state, data freshness, sizing, cash, position, loss, drawdown, wash-sale, and exit rules.
- **Small, inspectable state:** credential-free plans, logs, results, locks, and reports pass between fresh sessions through private Git.
- **Platform-owned credentials:** Robinhood authorization remains in the hosted MCP connection, outside repository artifacts.
- **Human-owned exposure:** the system cannot fund an account, enable live mode, clear a restart lock, increase capital, or add another lane.

## Evidence and release gates

| Stage | Evidence required | What it permits |
|---|---|---|
| Repository dry-run | Both fixtures complete in isolated state roots and the core tests pass | Continue to hosted setup |
| Hosted dry acceptance | One Account A scheduled Decision and next-weekday dry Execution cycle is reviewable | Review Account A for live readiness |
| Small live canary | Account A live loop reviewed, account binding proven, owner approval recorded | Begin with an approved $500–1000 allocation |
| Capital or account expansion | Eight continuous weeks of operational evidence plus a new architecture review | Human consideration of a specific change; never automatic expansion |

The Account A small allocation limits exposure while gathering real evidence. It does not make duplicate calls, ambiguous outcomes, incorrect tool use, prompt drift, or crash-before-log gaps technically impossible. Those are accepted limitations of the initial canary and must be reconsidered before expanding capital or adding another hosted lane.

## Boundaries

The current release is the two-account, long-only, prior-evening decision and next-morning execution loop. It does not include additional brokers or accounts, intraday trading, a generic strategy framework, comparison/shadow infrastructure, custom OAuth, a non-LLM executor, transactional submission state, exactly-once execution, automatic reconciliation, dashboards, or automated capital changes.

Live trading and its consequences remain the account owner's responsibility. Read `docs/ARCHITECTURE.md` for the system walkthrough, `docs/INVARIANTS.md` for the safety contract, `docs/TODO.md` for the remaining gates, and `docs/RUNBOOK.md` for operation and recovery.
