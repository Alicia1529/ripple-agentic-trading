# Ripple Trading

A small, real-money trading system built to learn agent-system design. The dry-run MVP supports exactly two isolated Robinhood Agentic account lanes using the same simple commands and separate hosted Decision and Execution routines. Risk arithmetic is deterministic; the small-account v1 deliberately accepts the prompt-mediated execution risks recorded in D26/D27.

Not financial advice. Read [`PROPOSAL.md`](PROPOSAL.md) for what this is and why before anything else.

## Docs

| File | Purpose |
|---|---|
| [`PROPOSAL.md`](PROPOSAL.md) | What this is, why it exists, scope at a glance |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Current system design — read this before writing code |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Append-only log of why each design choice was made |
| [`docs/INVARIANTS.md`](docs/INVARIANTS.md) | Non-negotiable system constraints and review checklist |
| [`docs/TODO.md`](docs/TODO.md) | Current implementation status |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Kill switch, what to do when notified, deploy/debug/recovery |
| [`docs/AI_NATIVE_DELIVERY.md`](docs/AI_NATIVE_DELIVERY.md) | Reusable delivery rules for aligning scope, speed, quality, and risk |
| [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md) | Multi-agent development workflow and starter role prompts |
| [`docs/archive/`](docs/archive/) | Superseded early drafts, kept for history only |

## Developing with AI agents

Ripple is designed for independent Codex threads, Claude Code sessions, or other coding agents. Git and the shared project docs carry knowledge and handoffs across temporary sessions; roles belong in task prompts, while concurrent code-writing agents use separate branches and worktrees. See [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md).

## Verify local Robinhood MCP OAuth

On macOS, run [`scripts/verify-robinhood-mcp-oauth.sh`](scripts/verify-robinhood-mcp-oauth.sh) only to reproduce the completed local feasibility proof. The five-stage wizard checks Python 3.12, walks through one browser authorization, runs two forced-expiry refresh proofs in separate headless processes, and finishes with ordinary headless reuse. Credentials are stored in macOS Keychain and every MCP session performs only `initialize` and `tools/list`. Production v1 does not use this runner-owned credential path; it uses the hosted platform's managed Robinhood MCP connection per D26.

## Status

The fixture-backed dry-run MVP is implemented for Account A and Account B. Each lane validates a strict decision, publishes one immutable-per-cycle snapshot and OrderPlan, re-runs deterministic execution risk checks, and produces credential-free JSON/JSONL records plus a human report beneath its own state root. Real hosted scheduled cycles are still operational acceptance gates; see `docs/TODO.md`.

## Run the dry-run MVP

From the repository root:

```bash
uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/mvp.json \
  --fixture fixtures/mvp/dry_cycle.json \
  --output /tmp/ripple-mvp/account_A

uv run --no-cache python -m ripple.mvp run-dry-cycle \
  --config config/mvp-account-b.json \
  --fixture fixtures/mvp/dry_cycle_account_b.json \
  --output /tmp/ripple-mvp/account_B
```

Review both account directories for the frozen snapshot, published plan, execution result, JSONL records, and report. The command refuses to overwrite an existing cycle. It never calls a broker tool. Account A's original config and command remain valid; Account B is the same concrete path with a second config and output root.

The two hosted stages use the same implementation through `publish-decision` and `execute-dry-run`. Their exact contracts and schedule are in [`routines/`](routines/).

Run the core suite with:

```bash
uv run --no-cache python -m unittest \
  tests.test_decision_snapshot tests.test_order_plan tests.test_execution_event \
  tests.test_risk tests.test_mvp_cycle
```

## License

[MIT](LICENSE) — same spirit as the other reference projects this borrows ideas from (see `docs/DECISIONS.md`): read it, adapt it, don't blindly run it against real money.
