# Ripple Trading

A small, real-money trading system built to learn agent-system design: two live Robinhood Agentic accounts running the same multi-agent architecture on different models (Claude vs. OpenAI), plus an open shadow pool of paper candidates that provides the baseline needed to tell whether any of it actually beats doing nothing.

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

On macOS, run [`scripts/verify-robinhood-mcp-oauth.sh`](scripts/verify-robinhood-mcp-oauth.sh). The five-stage wizard checks Python 3.12, walks through one browser authorization, runs two forced-expiry refresh proofs in separate headless processes, and finishes with ordinary headless reuse. Every MCP session performs only `initialize` and `tools/list`. Credentials are stored in macOS Keychain; Docker and `.env` secrets are not used. This runner-owned local proof has completed against Robinhood; it remains distinct from the earlier unauthenticated/access-token probes, and the production secret store remains undecided.

## Status

Architecture draft complete; broker/scheduler feasibility is in progress. See `docs/TODO.md`.

## License

[MIT](LICENSE) — same spirit as the other reference projects this borrows ideas from (see `docs/DECISIONS.md`): read it, adapt it, don't blindly run it against real money.
