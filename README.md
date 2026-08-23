# Ripple Trading

A small, real-money trading system built to learn agent-system design. The current target is a three-day dry-run MVP and a one-week live release for one Robinhood Agentic account using separate hosted Decision and Execution routines. Risk arithmetic is deterministic; the small-account v1 deliberately accepts the prompt-mediated execution risks recorded in D26.

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
| [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md) | Multi-agent development workflow and starter role prompts |
| [`docs/archive/`](docs/archive/) | Superseded early drafts, kept for history only |

## Developing with AI agents

Ripple is designed for independent Codex threads, Claude Code sessions, or other coding agents. Git and the shared project docs carry knowledge and handoffs across temporary sessions; roles belong in task prompts, while concurrent code-writing agents use separate branches and worktrees. See [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md).

## Verify local Robinhood MCP OAuth

On macOS, run [`scripts/verify-robinhood-mcp-oauth.sh`](scripts/verify-robinhood-mcp-oauth.sh) only to reproduce the completed local feasibility proof. The five-stage wizard checks Python 3.12, walks through one browser authorization, runs two forced-expiry refresh proofs in separate headless processes, and finishes with ordinary headless reuse. Credentials are stored in macOS Keychain and every MCP session performs only `initialize` and `tools/list`. Production v1 does not use this runner-owned credential path; it uses the hosted platform's managed Robinhood MCP connection per D26.

## Status

The three-day dry-run MVP and one-week hosted-routine production path are in progress. See `docs/TODO.md`.

## License

[MIT](LICENSE) — same spirit as the other reference projects this borrows ideas from (see `docs/DECISIONS.md`): read it, adapt it, don't blindly run it against real money.
