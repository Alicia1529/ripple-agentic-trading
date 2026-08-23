# Repository review fix handoff — 2026-08-23

This is a one-time handoff for the whole-repository MVP/two-account review and its approved fixes. Current behavior is authoritative in code, tests, `docs/ARCHITECTURE.md`, `docs/INVARIANTS.md`, and D28 in `docs/DECISIONS.md`. Genuinely unfinished operational work remains in `docs/TODO.md`.

## Completed scope

- Made BUY cash reservation cumulative and based on worst-case limit fills.
- Added deterministic full-position stop-loss/take-profit Risk Exits.
- Made missing/stale required quotes abort the cycle.
- Added credential-free decision-time cash/position baselines and execution reconciliation.
- Bound each configured `account_id` to its state-root basename.
- Added New York decision/execution date and time-window validation, including correct UTC-to-New-York date paths.
- Persisted an account-scoped tier-two drawdown lock requiring human restart.
- Restricted MVP plans to positive share-quantity `LIMIT`, `regular_hours`, `gfd` orders.
- Rejected non-finite OAuth expiry values and pinned `httpx2==2.5.0`.
- Updated the proposal, architecture, invariants, routine contracts, runbook, fixtures, README, TODO, and domain language to match the implementation.

## Verification evidence

Executed from the repository root:

```bash
uv run --no-cache --with-requirements \
  spikes/requirements-robinhood-mcp-auth-probe.txt \
  python -m unittest discover -s tests
```

Result: `Ran 97 tests ... OK`.

Additional checks:

```bash
python3.12 -m compileall -q ripple spikes tests
git diff --check
```

Both completed successfully. Dependency resolution confirmed `mcp 2.0.0`, `httpx2 2.5.0`, and `keyring 25.7.0`.

## Remaining work

No known repository review finding from this pass remains open. The remaining gates are operational and are tracked in `docs/TODO.md`: observe Account A's hosted scheduled dry cycle and capability separation, bind and verify Account B's hosted MCP account connection and schedules, then complete each lane's independently reviewed live gate. Transactional exactly-once execution and other D26/D27 accepted risks remain intentionally deferred until the required capital/third-account architecture review.
