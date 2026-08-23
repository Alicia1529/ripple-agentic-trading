# Multi-Agent Development Workflow

Ripple supports development by independent Codex threads, Claude Code sessions, and future coding agents. The collaboration substrate is Git plus the shared project documentation—not a particular tool's conversation history.

```text
Thread/session = temporary engineer
Repo           = shared organizational memory
Branch         = version isolation
Worktree       = filesystem/work-in-progress isolation
```

Give each thread or session one coherent task. Use one agent by default for one small vertical slice. Add agents only when work separates cleanly or an independent review is worth its coordination cost. For example:

```text
Thread A — implement OrderPlan persistence
Thread B — review execution idempotency
Thread C — reason about architecture
```

These are independent agent instances governed by the same repository instructions and shared documents.

## Sources of truth

```text
PROPOSAL.md
    project goals, scope, and major design

docs/ARCHITECTURE.md
    current system architecture

docs/INVARIANTS.md
    correctness and safety rules that must never be violated

docs/DECISIONS.md
    durable architectural decisions and rejected alternatives

docs/TODO.md
    genuinely unfinished work and current implementation status

AGENTS.md
    canonical agent entrypoint into the shared docs

CLAUDE.md
    thin Claude Code pointer to AGENTS.md

thread/session prompt
    current task and temporary role
```

Stable project knowledge belongs in these shared sources, not in vendor-specific instructions or agent-role files. Assign temporary roles through prompts; do not create files such as `AGENT_BUILDER.md`, `AGENT_REVIEWER.md`, or `AGENT_ARCHITECT.md`.

## Commit identity

Every agent-authored commit subject starts with the temporary role assigned to that task:

```text
Builder: add Robinhood MCP auth probe
Architect: record broker authentication boundary
Reviewer: add an approved review-only regression test
Coordinator: document review routing
```

Use `Builder`, `Architect`, `Reviewer`, or `Coordinator`, followed by a concise imperative summary. A Reviewer normally creates no commit during the initial read-only review. Existing commits are historical evidence and are not renamed to adopt this convention retroactively.

## Starter prompts

### Builder

```text
Act as the Builder for one scoped Ripple change: <task>.

Read AGENTS.md or CLAUDE.md first, then read every document it requires, including docs/AGENT_WORKFLOW.md. Identify the affected invariants. Implement the scoped change and add or update relevant tests. Run those tests and report the results. Preserve current architecture; if the task requires an architectural change, stop and make that change explicit rather than silently introducing it. Leave the branch in a reviewable state with a focused diff and a commit whose subject starts with `Builder:`.
```

### Reviewer

```text
Act as an independent Reviewer for Ripple branch/commit/diff: <reference>.

Read AGENTS.md or CLAUDE.md first, then read every document it requires, including docs/AGENT_WORKFLOW.md. Initially review without modifying code. Separate correctness defects from optional improvements, and cite concrete files and lines. Inspect failure modes, missing tests, concurrency, idempotency, and violations of docs/INVARIANTS.md in particular. Report findings by severity; if there are no material findings, say so and name any residual testing risk.
```

### Architect

```text
Act as the Architect for this Ripple question: <question>.

Read AGENTS.md or CLAUDE.md first, then read every document it requires, including docs/AGENT_WORKFLOW.md. Reason before implementation. Identify affected invariants, interfaces, trade-offs, and failure modes; compare viable alternatives and state a recommendation. If a durable architectural decision is approved, append it to docs/DECISIONS.md and update the current design in docs/ARCHITECTURE.md. Do not claim implementation work is complete unless the repository proves it.
```

## Learning-first incremental loop

Use this sequential loop when Alicia wants to understand and inspect every code change:

```text
Architect defines the smallest useful slice
        ↓
Builder implements and tests one focused commit
        ↓
Alicia inspects the diff and asks questions
        ↓
Reviewer reviews that exact commit without editing
        ↓
Builder addresses approved findings in another focused commit
        ↓
Alicia inspects the result before the next slice begins
```

1. **Architect:** Select the first or next smallest useful slice. Explain why it comes next, what is in and out of scope, affected interfaces and invariants, acceptance criteria, and the tests that will prove completion. Finish with a concrete Builder-ready task. Architecture work is also required when a slice exposes a durable design choice; routine implementation details do not need a separate architecture pass.
2. **Builder:** Before editing, state the intended files, behavior, and verification. Implement only the approved slice, run the relevant tests, and create one focused `Builder:` commit. Stop after reporting the commit and test results so Alicia can inspect the diff.
3. **Alicia checkpoint:** Inspect the exact commit and ask questions until the behavior and implementation are clear. The next slice waits for this checkpoint.
4. **Reviewer:** Review the exact commit or diff read-only. Report correctness defects separately from optional improvements, with concrete file and line references. Do not modify the implementation during the initial review.
5. **Fix and close:** The Builder implements only the approved review findings in a new focused commit and reruns the relevant tests. Alicia inspects that follow-up diff before accepting the slice or returning to the Architect for the next one.

This is a risk-scaled menu, not mandatory ceremony for every change. Low-risk slices may go directly to one Builder and Alicia's checkpoint. Before any role starts, define the stage, outcome, timebox, scope, risk budget, acceptance evidence, and expansion trigger from `docs/AI_NATIVE_DELIVERY.md`. Stop research or architecture work at its timebox unless the remaining uncertainty directly blocks the approved outcome.

Run these roles sequentially when they share one working directory. Parallel modifying agents require separate branches and worktrees as described below.

## Coordination and review routing

The Coordinator may be Alicia or a dedicated coordination thread. It owns the development stage and evidence, not the implementation. For each slice it tracks the Architect's scope, the exact Builder commit, test results, Alicia's checkpoint, Reviewer status, approved findings, and the follow-up commit. Git and the shared documents remain authoritative when a thread summary disagrees with repository state.

Reviewer feedback reaches the Builder through a self-contained handoff:

1. The Reviewer names the exact reviewed commit or diff range and reports findings by severity, with file and line references, optional improvements, and residual testing risk.
2. The Coordinator reads the completed review and presents it to Alicia. Alicia decides which optional improvements are approved; correctness findings remain release blockers until resolved or explicitly rejected with a recorded reason.
3. The Coordinator sends the Builder the exact reviewed reference plus the full approved findings. The message contains everything needed to work; the Builder never depends on the Reviewer's conversation history.
4. The Builder fixes only those findings, reruns the relevant tests, and creates a new focused `Builder:` commit.
5. The Coordinator asks the Reviewer to inspect the exact follow-up diff, then records the slice as accepted only after the review is clear and Alicia completes the checkpoint.

Use this handoff shape:

```text
Address the approved findings from review of <commit>:

<full findings with severity and file/line references>

Preserve the original slice scope. Run the relevant tests and create one
focused commit whose subject starts with `Builder:`. Stop after reporting
the new commit and test results.
```

## Branches and worktrees

Separate worktrees are not required merely because multiple threads exist. Sequential review or architecture work can use ordinary branches, and read-only agents can inspect an existing branch without their own worktree.

When multiple agents modify files concurrently, give each one its own branch and worktree so their working directories and uncommitted changes cannot collide:

```bash
git worktree add ../ripple-order-plan -b feature/order-plan
git worktree add ../ripple-review -b review/order-plan
```

The result is:

```text
ripple/                 main
ripple-order-plan/      feature/order-plan
ripple-review/          review/order-plan
```

Choose branch names that describe ownership. Before merging, review each diff, run the relevant tests, and resolve integration conflicts against the current sources of truth.

## Handoff through durable artifacts

Agents must not depend on another agent's conversation history. Completed work is communicated through:

1. Code and tests.
2. Commits and diffs.
3. `docs/DECISIONS.md` for durable architectural decisions.
4. `docs/TODO.md` only for genuinely unfinished work.

Do not maintain append-only conversational `HANDOFF.md` logs. If work is complete, the code, tests, docs, and Git history are the handoff. If work is incomplete, record only the minimum current state needed for another agent to continue in `docs/TODO.md`.

```text
Agent
  ↓
code / tests / docs
  ↓
Git
  ↓
next independent Agent
```

This makes the engineering organization reproducible across tools:

```text
Role       → thread/session prompt
Knowledge  → repo
Ownership  → branch/worktree
Handoff    → Git + shared docs
Review     → independent thread/session
```

## Match process to risk

Use multiple agents when independence improves the result, not as process overhead.

| Risk | Examples | Recommended flow |
|---|---|---|
| Low | Reporting, formatting, simple utilities | One agent implements directly |
| Medium | Schemas, experiment harness, data pipeline | One agent implements; another independently reviews |
| High | Risk engine, broker execution, idempotency, scheduling, backtest timing semantics | Architecture pass → implementation → adversarial independent review → regression tests |

Regardless of risk level, one agent owns one coherent task, respects `docs/INVARIANTS.md`, and leaves a verifiable repository state for the next independent agent.
