# Running Ripple

Ripple separates **what a run must do** from **who runs it**. The prompts in
[`routines/`](../routines/) are the durable contract; the Agent Runner that executes them is a
replaceable host for the agent. This document covers the offline demo and the requirements for
moving from a supplied fixture to separate hosted Decision and Execution runs.

Operational procedures — incident response, the kill switch, tier-two restart — stay in
[`RUNBOOK.md`](RUNBOOK.md).

## Run one cycle offline

This needs no model, no API key, no broker connection, and no network. It replays a checked-in
fixture through the real publisher, the real deterministic risk module, and the real shadow
adapter:

```bash
uv run --no-cache python -m ripple.mvp run-shadow-cycle \
  --config config/examples/demo_lane.json \
  --fixture fixtures/mvp/demo_lane_cycle.json \
  --output /tmp/ripple-demo/demo_lane
```

It writes one complete Decision Cycle to `/tmp/ripple-demo/demo_lane/trading_days/2026-08-25/`:

| File | What it shows |
|---|---|
| `decision_snapshot.json` | The immutable allowed inputs and universe for the cycle |
| `order_plan.json` | The immutable, strategy-attributed decision intent |
| `execution.json` | The deterministic risk verdict, the fill attempt, and the ending virtual account |
| `report.md` | The same cycle in human-readable form |

`report.md` ends with `No broker write tool was called.` and records the Shadow Fill as
`assumed_t_plus_one_quote_fill` — an assumption, never a broker confirmation.

`config/examples/demo_lane.json` sits outside the `config/*.json` glob, so the demo lane is
excluded from scheduled selection while it remains there. For another offline experiment, keep
the configuration under `config/examples/` and pass its path explicitly. Adding a configuration to
`config/` is a reviewed deployment change: it joins the catalog and, depending on its mode and
profile, may join a scheduled cohort. See [Writing a Strategy Spec](WRITING_A_STRATEGY.md).

Use a fresh output directory for another replay. Existing cycle artifacts are never overwritten
by the publisher.

## The Agent Runner contract

An **Agent Runner** starts a fresh agent session with a routine, repository access and the tools
that phase requires. The Python core has no runner-specific integration. Merely launching an agent
does not prove that its permissions, state continuity or scheduling satisfy the contract. A runner must:

1. **start fresh** — one session per run, with no memory of another phase or lane;
2. **read one routine completely** — [`AGENTS.md`](../AGENTS.md) plus exactly one of
   [`routines/DECISION_LIVE.md`](../routines/DECISION_LIVE.md),
   [`DECISION_SHADOW.md`](../routines/DECISION_SHADOW.md),
   [`EXECUTION_LIVE.md`](../routines/EXECUTION_LIVE.md),
   [`EXECUTION_SHADOW.md`](../routines/EXECUTION_SHADOW.md),
   [`DECISION_SHADOW_CLOSE.md`](../routines/DECISION_SHADOW_CLOSE.md), or
   [`EXECUTION_SHADOW_CLOSE.md`](../routines/EXECUTION_SHADOW_CLOSE.md);
3. **own exactly one cohort phase** — never perform the other phase or another cohort in the same
   run;
4. **fire at the right time** — the six triggers in
   [`routines/SCHEDULE.md`](../routines/SCHEDULE.md), in `America/New_York`; each routine
   re-checks its own window, so a runner that cannot express an IANA timezone may trigger inside a
   wider UTC window;
5. **reach the repository and the facts it needs** — repository read/write, unattended
   `git pull`/`git push` for continuity, and network access for market sources. A live Execution
   runner additionally needs the reviewed broker connection; **a shadow or dry-run runner must not
   have one**;
6. **stop instead of widening authority** — a failed precondition, malformed result, or ambiguous
   outcome ends the run and is reported, never retried blindly; and
7. **never backfill on its own** — a missed cycle stays missed until a designated owner runs an
   explicitly labeled historical Decision.

Python enforces schemas, account binding, timing, risk and fill semantics. Fresh sessions, tool
permissions, trigger configuration and prompt adherence are runner responsibilities. Passing the
Python checks alone does not prove those operational boundaries were respected.

## Runner: any agent, driven by hand

Use a separate session for Decision and Execution so the two phases remain isolated. The examples
below use `next_session_open`; the close-profile instructions are in
[Close Decision](../routines/DECISION_SHADOW_CLOSE.md) and
[Close Execution](../routines/EXECUTION_SHADOW_CLOSE.md). Replace the bracketed values before sending a prompt.

### Normal run

Send the Decision prompt during the normal Decision window:

```text
Run Ripple's normal [live|shadow] Decision now. Read AGENTS.md and routines/DECISION_[LIVE|SHADOW].md completely and follow them exactly. Use the current validated cohort and selected Strategy Spec. This is a normal scheduled-style run, not manual and not a backfill. Stop after publishing and verifying the Decision artifacts; do not perform Execution.
```

On the next trading day, send the matching Execution prompt:

```text
Run Ripple's normal [live|shadow] Execution now. Read AGENTS.md and routines/EXECUTION_[LIVE|SHADOW].md completely and follow them exactly. Execute only the matching published plans through deterministic risk. This is a normal scheduled-style run, not manual and not a backfill. Do not perform new Decision work.
```

### Manual run

Manual mode is for an owner-authorized run outside the schedule window. It changes timing only; every other safety rule remains active. Send Decision and Execution as separate prompts:

```text
I am the designated owner and explicitly authorize a manual [live|shadow] Decision for account [account_id] now. Read AGENTS.md and routines/DECISION_[LIVE|SHADOW].md completely, gather all required current facts, and follow the routine using --manual-run. Preserve lane isolation and all stop conditions. Stop after publishing and verifying the Decision artifacts; do not perform Execution.
```

```text
I am the designated owner and explicitly authorize manual [live|shadow] Execution for account [account_id] and trade date [YYYY-MM-DD] now. Read AGENTS.md and routines/EXECUTION_[LIVE|SHADOW].md completely and follow the routine using --manual-run. Use only that cycle's immutable plan, run deterministic risk, preserve all Live Gate/account/duplicate/ambiguity checks, and do not perform new Decision work.
```

### Historical backfill

Backfill recreates a missed live or shadow cycle from point-in-time facts. First send the historical Decision prompt:

```text
I am the designated owner and explicitly authorize a historical [live|shadow] Decision backfill for account [account_id], with Decision date [YYYY-MM-DD] and intended trade date [YYYY-MM-DD]. Read AGENTS.md, routines/DECISION_[LIVE|SHADOW].md, and the account's selected Strategy Spec completely. Gather complete point-in-time facts for that historical Decision, use --historical-backfill, label the plan as backfill, and preserve all validation and immutability rules. Stop after publishing and verifying the Decision artifacts; do not perform Execution.
```

After reviewing that plan, start a separate session with the Execution prompt:

```text
I am the designated owner and explicitly authorize [live|shadow] Execution of the backfill plan for account [account_id] and trade date [YYYY-MM-DD]. Read AGENTS.md and routines/EXECUTION_[LIVE|SHADOW].md completely. Gather the matching historical T+1 execution facts, use --manual-run, execute only the immutable backfill plan through the normal deterministic and mode-specific safeguards, and do not perform new Decision work. Keep backfill provenance explicit in every artifact and report.
```

Backfill is unavailable for `dry_run`, never overwrites an existing cycle, and is never started automatically by a scheduled task.

## Hosted runs

The current deployment uses Codex scheduled tasks. The checked-in [schedule manifest](../routines/SCHEDULE.md)
owns the six trigger definitions and their routine paths. A Markdown routine describes the work;
it does not register or enable a schedule. Product setup is covered in the
[Codex automation documentation](https://developers.openai.com/codex/app/automations).

For each hosted phase, verify the repository-level requirements:

1. The run starts a fresh session and reads the complete routine for its mode and profile.
2. It uses the intended state branch, can pull and push without conflict, and sees the artifacts
   published by the preceding phase. A separate checkout must synchronize that same history before
   continuing; an isolated copy with missing state cannot execute the plan.
3. Its trigger follows the manifest's New York time and its routine checks the trading calendar.
4. Its permissions match its role. Shadow work has no broker connection; live Execution requires
   the reviewed connection and the Live Gate.
5. After an authorized scheduled cycle, the plan, execution and report are reviewable in the same
   trade-date directory. Check mode, profile, strategy, run provenance and any fill assumptions.

A missed trigger, credential finding, conflict or ambiguous result requires the stop behavior in
[the runbook](RUNBOOK.md). The presence of saved prompts or test results is not hosted acceptance;
[TODO](TODO.md) records the remaining acceptance reviews.

Another agent host can be evaluated against the same contract. Verify its session isolation,
permissions, scheduling and Git continuity with the required no-write evidence before relying on
it. Changing the runner does not grant new trading authority.
