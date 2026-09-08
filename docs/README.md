# Documentation map

Start with the question you want to answer. The README presents the project; these documents
provide the runnable example, code references and operational detail behind it.

## Choose a reading path

| Reader | Suggested path | What you can learn or verify |
|---|---|---|
| First-time visitor | [README](../README.md) → [one cycle](ANATOMY_OF_A_CYCLE.md) | What Ripple does and how to reproduce its offline output |
| Technical interviewer | [Design choices](../README.md#design-choices-you-can-inspect) → [architecture](ARCHITECTURE.md) → [invariants](INVARIANTS.md) | Why responsibilities are separated, what Python enforces and which risks remain |
| Reviewing AI-assisted development | [Repair case](../learning/frozen-trade-date-case-study.md) → [scope workflow](../learning/compile-scope-before-codex-execution.md) | What the owner requested, what the agent changed and how the regression proves the repair |
| Contributor | [Contributing](../CONTRIBUTING.md) → [AGENTS.md](../AGENTS.md) → [writing a strategy](WRITING_A_STRATEGY.md) | How to make a bounded, testable change without weakening constraints |
| Operator | [Running](RUNNING.md) → [runbook](RUNBOOK.md) → [unfinished gates](TODO.md) | Runner requirements, failure handling and release status |

The offline walkthrough uses a **fixed fixture**, not a live market run. Its numbers are
reproducible; they do not measure LLM quality or investment performance. For a term such as
Account Lane, Strategy Spec or Cycle Profile, use the [glossary](../CONTEXT.md).

## Every document, and what it is authoritative for

| Document | Authoritative for | Changes |
|---|---|---|
| [`../config/*.json`](../config/) | Current lane identity, mode, strategy, universe, risk. **No document may restate this** | Often |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | How the system works today and where its boundaries sit | With the system |
| [`INVARIANTS.md`](INVARIANTS.md) | The non-negotiable safety and correctness rules | Rarely, and never casually |
| [`DECISIONS.md`](DECISIONS.md) | Durable choices that govern the current release, and why | On approved decisions |
| [`ANATOMY_OF_A_CYCLE.md`](ANATOMY_OF_A_CYCLE.md) | One reproducible fixture cycle, field by field | With the artifact schemas |
| [`WRITING_A_STRATEGY.md`](WRITING_A_STRATEGY.md) | The Strategy Spec contract | With the strategy seam |
| [`RUNNING.md`](RUNNING.md) | The Agent Runner contract and the prompt library | With the routines |
| [`RUNBOOK.md`](RUNBOOK.md) | Operations, verification, incidents, restart | With operational experience |
| [`TODO.md`](TODO.md) | Genuinely unfinished work and the next release gates | Continuously |
| [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) | The latest three handoff entries only | Every session |
| [`../CONTEXT.md`](../CONTEXT.md) | Domain vocabulary — the terms to use and the ones to avoid | With the domain model |
| [`../PROPOSAL.md`](../PROPOSAL.md) | Why Ripple exists, product scope, and release gates | With the product |
| [`../SECURITY.md`](../SECURITY.md) | What counts as a security issue, and the boundary before running it live | Rarely |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Setup, scope rules, welcome contributions, and settled non-goals | Rarely |
| [`../routines/`](../routines/) | What each Decision and Execution run must do | With the routines |
| [`../strategies/`](../strategies/) | Investment policy, one version-named file each | Never in place — add a new version |

## Keeping references current

**Deployment facts live in exactly one place.** Which lane is live, which strategy it uses, what its
universe and risk values are — that is `config/*.json` and nothing else. Stable documentation
describes interfaces and constraints; it does not mirror a mutable inventory. When you need current
deployment facts, inspect the catalog:

```bash
uv run --no-cache python -m ripple.mvp list-accounts --mode live
```

**A decision and its documentation land together.** Changing durable architecture means recording
the decision in [`DECISIONS.md`](DECISIONS.md) and updating
[`ARCHITECTURE.md`](ARCHITECTURE.md) in the same change. A change that invalidates something in
[`INVARIANTS.md`](INVARIANTS.md) is an architecture decision, not a local exception.
