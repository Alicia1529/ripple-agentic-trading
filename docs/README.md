# Documentation map

Ripple keeps different kinds of truth in different files on purpose: what the system *is*, what it
must *never* do, what was *decided* and why, and how to *operate* it change at very different
rates. Start here to find the one that answers your question.

## Start by who you are

**Just looking around.** [`README.md`](../README.md) for the pitch and the offline demo, then
[`ANATOMY_OF_A_CYCLE.md`](ANATOMY_OF_A_CYCLE.md) to watch one real cycle move through the system
artifact by artifact. That pair explains more in ten minutes than the architecture document does.

**Want to add a strategy.** [`WRITING_A_STRATEGY.md`](WRITING_A_STRATEGY.md). Strategies are
Markdown policies, so this is the lowest-friction way to contribute something real.

**Going to run it.** [`RUNNING.md`](RUNNING.md) for the Agent Runner contract and the prompt
library, then [`RUNBOOK.md`](RUNBOOK.md) for verification, schedules, incidents, and the kill
switch.

**Changing the code.** [`../AGENTS.md`](../AGENTS.md) first — it is the working contract for humans
and agents alike — then [`INVARIANTS.md`](INVARIANTS.md) and
[`ARCHITECTURE.md`](ARCHITECTURE.md). [`../CONTRIBUTING.md`](../CONTRIBUTING.md) has the mechanics.

## Every document, and what it is authoritative for

| Document | Authoritative for | Changes |
|---|---|---|
| [`../config/*.json`](../config/) | Current lane identity, mode, strategy, universe, risk. **No document may restate this** | Often |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | How the system works today and where its boundaries sit | With the system |
| [`INVARIANTS.md`](INVARIANTS.md) | The non-negotiable safety and correctness rules | Rarely, and never casually |
| [`DECISIONS.md`](DECISIONS.md) | Durable choices that govern the current release, and why | On approved decisions |
| [`ANATOMY_OF_A_CYCLE.md`](ANATOMY_OF_A_CYCLE.md) | One worked cycle, field by field | With the artifact schemas |
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

## Two rules that keep this from rotting

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
