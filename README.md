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
| [`docs/archive/`](docs/archive/) | Superseded early drafts, kept for history only |

## Status

Design complete, implementation not started. See `docs/TODO.md`.

## License

No license has been chosen yet. Until one is added, standard copyright applies — the code is not licensed for reuse.
