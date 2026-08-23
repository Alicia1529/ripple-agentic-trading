# AI-Native Delivery: Align the Next Release, Not Just the Vision

This playbook prevents AI-assisted projects from turning a small, reversible MVP into an imagined final production system. Use it before planning, research, implementation, or review.

## The core lesson

Agreement on the long-term vision is not delivery alignment.

Delivery is aligned only when the human and agent share the same understanding of:

- the current release stage;
- the next observable outcome;
- the time budget;
- the accepted risk budget;
- explicit non-goals;
- the completion test;
- the conditions that justify more complexity.

An agent naturally optimizes for completeness and risk coverage. The project owner defines what is **sufficient for this stage**. Quality is multidimensional: for an MVP, simplicity, inspectability, reversibility, and learning speed can matter more than infrastructure completeness.

## Start every slice with a delivery contract

Before changing code, write a compact contract containing:

1. **Stage** — prototype, dry-run MVP, small live canary, production hardening, capital expansion, or multi-tenant expansion.
2. **Outcome** — one behavior that will run, be tested, or produce new evidence.
3. **Timebox** — the maximum time for design/research and the target time for implementation.
4. **In scope** — only the behavior required to produce that outcome.
5. **Out of scope** — attractive adjacent work that will wait.
6. **Risk budget** — risks to eliminate now, reduce cheaply, limit by exposure, or explicitly accept.
7. **Acceptance** — commands, observations, or artifacts that prove completion.
8. **Expansion trigger** — concrete evidence that would justify another abstraction or control.

If one of these is ambiguous enough to change the implementation materially, surface it before expanding the design.

## Match engineering depth to the stage

### Prototype

Answer one feasibility or design question. Optimize for fast evidence. Throw the result away if keeping it would create accidental commitments.

### Dry-run MVP

Build the shortest complete vertical slice without irreversible external effects. Prefer fixed inputs, one concrete path, small scripts, and inspectable artifacts.

### Small live canary

Limit exposure and make accepted risks explicit. Add only the controls required by the owner's stated loss tolerance and operating model. Monitor the first real cycles.

### Production hardening

Use observed failures and operational evidence to select durability, idempotency, recovery, security, and monitoring work. Avoid hardening imagined paths before the canary reveals which ones matter.

### Expansion

Add abstractions when a second concrete account, strategy, broker, tenant, or runtime creates a demonstrated need. Revisit risks before increasing capital or blast radius.

## Treat risk instead of automatically eliminating it

For each meaningful failure mode, choose one response deliberately:

| Response | Use when |
|---|---|
| Eliminate | The failure is intolerable at the current exposure or violates a hard invariant. |
| Reduce | A small, reviewable guard materially lowers likelihood or impact. |
| Limit exposure | A small account, canary, rate limit, fixed universe, or manual gate caps loss. |
| Accept | Probability and impact fit the owner's current risk budget, and the trade-off is recorded honestly. |

Do not describe an accepted risk as technically prevented. Do not promote every identified failure mode into a release blocker.

## Prefer reversible decisions

Classify a decision before designing around it:

- **Reversible:** choose the smallest working option and preserve a narrow seam.
- **Costly to reverse:** compare viable alternatives and record the reason.
- **Irreversible or high-blast-radius:** slow down, gather evidence, and require explicit approval.

Future extensibility usually means avoiding lock-in, not implementing future consumers. For a first use case, keep identifiers and boundaries that would permit migration, then wait for the second concrete use before extracting a general framework.

## Make evidence the unit of progress

Count progress as a new observable capability, not as document volume, schema count, or the number of failure modes discussed.

A useful slice should produce at least one of:

- a test that proves a behavior;
- a runnable end-to-end path;
- a scheduled cycle observed in its real environment;
- a real integration fact that changes the next decision;
- a user-reviewable artifact tied to runtime behavior.

For every proposed task, ask: **What new evidence exists after this that does not exist now?** If the answer is only “the architecture is more complete,” remove it from the MVP critical path unless it resolves an approved durable decision.

## Timebox research and architecture

Define a research spike before starting it:

- one question;
- a fixed time limit;
- success evidence;
- failure evidence;
- known questions it will not answer;
- the fallback decision when time expires.

At the timebox, stop. Use the evidence already gathered, record the remaining uncertainty as deferred or accepted risk, and continue with the smallest viable slice. Extend research only when the unresolved fact directly blocks the approved outcome.

Architecture work has the same bound. A durable decision earns documentation; routine implementation details do not require an architecture phase.

## Keep implementation slices small

One slice should have:

- one primary behavior change;
- one owner;
- a small, named file set;
- explicit interfaces and affected invariants;
- focused tests;
- one reviewable commit.

Use concrete code for the first caller. Add configuration and abstractions only when required by the current contract. Preserve unrelated code and defer optional cleanup.

## Scale process with risk

Use one agent by default for one coherent, low-risk vertical slice. Add an independent reviewer when the consequence of a defect justifies the coordination cost. Use multiple agents in parallel only when their tasks are genuinely independent and do not require repeated full-context reconstruction.

Agent roles, documents, and handoffs are overhead unless they reduce a specific risk. If process produces more coordination artifacts than executable evidence, simplify the process.

The human should not need to repeatedly say “stop researching” or “start implementing.” During longer work, the agent should report:

- evidence produced;
- timebox remaining;
- distance to the current release outcome;
- any emerging scope expansion;
- work that can now be deleted or deferred.

## Checkpoints

At the end of every slice, answer:

1. What new evidence did this produce?
2. Did it move the current release closer to running?
3. Did it add complexity not required by the delivery contract?
4. What is the smallest next observable outcome?
5. If the deadline is unchanged, what should be removed?

Before beginning the next slice, obtain the human checkpoint required by the project's workflow.

## Warning signs

Pause and re-scope when any of these appears:

- infrastructure is being built for a consumer that does not exist;
- a reversible choice is treated as a permanent architecture commitment;
- research expands beyond its original question;
- accepted risks silently become mandatory pre-release projects;
- documents grow while no new path runs;
- the same context is repeatedly reconstructed across agents;
- “production quality” is used without a shared release definition;
- the owner must repeatedly pull the work back toward the MVP.

## Default decision rule

When two approaches both satisfy the current delivery contract, choose the one with:

1. fewer moving parts;
2. less new code;
3. a shorter path to real evidence;
4. easier human inspection;
5. a reversible migration path.

The purpose of an MVP is not to prove that the system is ready to scale. It is to obtain the real evidence needed to decide what deserves to be built next.
