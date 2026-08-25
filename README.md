# Ripple Trading

Ripple is a two-account, fixture-backed dry-run trading MVP. Each isolated lane separates an LLM Decision Routine from a narrow next-morning Execution Routine and applies deterministic risk calculations. Hosted acceptance and the live MCP call loop remain unfinished.

Start with [`PROPOSAL.md`](PROPOSAL.md). The current technical contract is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), safety rules in [`docs/INVARIANTS.md`](docs/INVARIANTS.md), unfinished work in [`docs/TODO.md`](docs/TODO.md), and operations in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Fixture dry cycles

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

Each command writes a frozen snapshot, immutable plan, execution result, JSONL records, and report below its account-specific output. It refuses to overwrite an existing cycle and never calls a broker tool. Hosted stages use the same implementation through `publish-decision` and `execute-dry-run`; see [`routines/`](routines/) for their exact prompts and schedule.

Run the core suite:

```bash
env PYTHONDONTWRITEBYTECODE=1 uv run --no-cache python -m unittest \
  tests.test_decision_snapshot tests.test_order_plan tests.test_risk tests.test_mvp_cycle
```

Not financial advice. [MIT](LICENSE).
