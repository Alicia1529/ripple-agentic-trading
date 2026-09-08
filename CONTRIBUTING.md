# Contributing

Ripple separates AI investment judgment from deterministic validation and risk checks. You can
contribute without a broker account: run the offline fixture, reproduce a bug, improve an
explanation or propose a versioned strategy policy.

## Setup

CPython 3.12 or later, and nothing else. There are no runtime or test dependencies. Most work is
driven through [`uv`](https://docs.astral.sh/uv/), which reads `.python-version` and picks the right
interpreter for you:

```bash
uv run --no-cache python -m unittest discover -s tests -t .
uv run --no-cache python -m ripple.mvp validate-configs
```

Both also run under Python 3.12+ from the repository root. If imports fail, check the interpreter
version and working directory first; no third-party package installation is expected. Adding a
dependency is an architecture decision, not a convenience; see [`docs/DECISIONS.md`](docs/DECISIONS.md).

Then run the offline demo in [`README.md`](README.md) to see a complete cycle, and read
[`docs/ANATOMY_OF_A_CYCLE.md`](docs/ANATOMY_OF_A_CYCLE.md) to understand what it produced.

## Read this before changing anything

[`AGENTS.md`](AGENTS.md) is the working contract for everyone, human or agent. It asks you to state,
before you plan: the release stage, the next observable outcome, the exact in-scope behavior and
files, your accepted risks and non-goals, and the commands that will prove completion. This makes
a change reviewable before implementation, including which live-system constraints it must preserve. The [trade-date repair](learning/frozen-trade-date-case-study.md) shows a concrete
example of a bounded fix and its regression evidence.

Two further rules follow from it:

- **Identify the invariants your change touches.** [`docs/INVARIANTS.md`](docs/INVARIANTS.md) is the
  review checklist. A change that invalidates one is an architecture decision requiring a recorded
  entry in [`docs/DECISIONS.md`](docs/DECISIONS.md) and a matching architecture update — never a
  local exception.
- **Keep the diff proportional.** Adjacent refactoring needs separate approval. A new subsystem, or
  changes to more than four production files, needs explicit approval and a smaller alternative
  offered first.

## What is most welcome

**A new Strategy Spec.** The lowest-friction real contribution: strategies are version-named
Markdown policies, no Python required. See
[`docs/WRITING_A_STRATEGY.md`](docs/WRITING_A_STRATEGY.md).

**Tests that pin down a safety rule.** Especially fail-closed behavior — missing facts, stale
quotes, baseline mismatch, cross-account mismatch, unsafe sizing.

**Documentation that removes a guess.** If something took you three files to figure out, that is a
documentation defect worth fixing.

**Bugs in the deterministic core.** Risk, sizing, timing, and fill semantics are where correctness
matters most, and where a reproducing test is worth more than a patch.

## Current non-goals

These are settled decisions, not gaps waiting for a PR. Proposing one means proposing to revisit a
recorded decision, which is fine — but argue the decision, do not open the implementation.

A Python strategy plugin engine. Automatic strategy scoring or promotion. A dashboard. Multiple
simultaneous live lanes. Same-day entry and exit. Additional brokers. Transactional persistence or
exactly-once broker execution. Automatic reconciliation. Calibrated fee and slippage models.

## Non-negotiables

- **Nothing that touches real money merges without a human decision.** No code in this repository
  may enable live mode, bind or fund an account, increase capital, or clear a restart lock.
- **Credentials never enter the repository** — no secrets, tokens, cookies, account numbers, or raw
  authenticated responses in code, fixtures, prompts, logs, artifacts, or tests.
- **Published evidence is immutable.** Never rewrite a past plan, execution result, or report to
  make a run look better. Correct the code and let the record stand.
- **Financial values are base-10 decimal strings**, never floats.

## Submitting

Run the tests and catalog validation, keep the change scoped to what you described, and write a
commit message that explains why the change is correct rather than what the diff shows. If your
change affects behavior an invariant covers, say which invariant and how you verified it.

Trading decisions and their consequences remain the account owner's. Ripple is educational software
and not financial advice; see [`SECURITY.md`](SECURITY.md) before running anything against a real
broker account.
