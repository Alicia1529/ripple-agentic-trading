# Running Ripple

Ripple separates **what a run must do** from **who runs it**. The prompts in
[`routines/`](../routines/) are the durable contract; the Agent Runner that executes them is an
implementation detail you can replace. This document covers the offline demo, the contract every
runner must satisfy, and the runners known to satisfy it.

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
invisible to the catalog and can never be selected by a scheduled cohort. Copy it into `config/`
under a new snake_case filename to create a lane of your own; that filename becomes the account
identifier.

## The Agent Runner contract

An Agent Runner is anything that can start a session in this repository and follow one routine
prompt. Ripple does not care which product it is, and no runner is privileged in the code. A
runner must:

1. **start fresh** — one session per run, with no memory of another phase or lane;
2. **read one routine completely** — [`AGENTS.md`](../AGENTS.md) plus exactly one of
   [`routines/DECISION_LIVE.md`](../routines/DECISION_LIVE.md),
   [`DECISION_SHADOW.md`](../routines/DECISION_SHADOW.md),
   [`EXECUTION_LIVE.md`](../routines/EXECUTION_LIVE.md), or
   [`EXECUTION_SHADOW.md`](../routines/EXECUTION_SHADOW.md);
3. **own exactly one cohort phase** — never perform the other phase or another cohort in the same
   run;
4. **fire at the right time** — the four triggers in
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

Nothing in this contract is enforced by Python. Deterministic code enforces schemas, account
binding, timing, risk, and fill semantics; the runner contract is what keeps a correct run
*correctly scoped*.

## Runner: any agent, driven by hand

Use a separate session for Decision and Execution so the two phases remain isolated. Replace the bracketed values before sending a prompt.

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

## Runner: Codex scheduled tasks

OpenAI currently exposes Codex automations as **Scheduled tasks** in the ChatGPT desktop app. A scheduled task created from Codex can work in a local Git project, while a web-only task cannot directly access a folder on this computer. See the official [Scheduled tasks documentation](https://developers.openai.com/codex/app/automations).

The files in [`routines/`](../routines/) are the durable prompts that a scheduled task reads; they are not executable schedules and are not registered automatically. [`routines/SCHEDULE.md`](../routines/SCHEDULE.md) is the operator-owned target schedule manifest. It documents the eventual four-task live/shadow topology; hosted shadow acceptance uses the two shadow tasks below, while live tasks remain disabled until the broker-write loop and Live Gate are complete.

Before creating the tasks:

- open this repository as a local project in the ChatGPT desktop app and select Codex;
- use the intended private state branch, confirm the worktree is clean, and confirm unattended `git pull`/`git push` can use the repository remote;
- keep the computer on, the desktop app running, and the repository available at each trigger time; and
- grant only repository write and network access needed for Git and market facts. Shadow tasks need no Robinhood connection or broker-write permission.

Create two **standalone** scheduled tasks. Choose this local project, not an isolated worktree, so Decision and Execution use the same checked-out branch and credential-free state history. Leave model and reasoning settings at their defaults unless an observed run requires a reviewed change.

| Task name | Time zone and recurrence | Saved prompt |
|---|---|---|
| `Ripple Shadow Decision` | `America/New_York`; Sun–Thu at 9:00 PM. Advanced rule: `RRULE:FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH;BYHOUR=21;BYMINUTE=0` | `Work in the selected Ripple repository. Read routines/DECISION_SHADOW.md completely and follow it exactly. This task owns only the Shadow Decision cohort. Do not perform Execution or live work. If a precondition fails, stop and report it without broadening authority.` |
| `Ripple Shadow Execution` | `America/New_York`; Mon–Fri at 9:35 AM. Advanced rule: `RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=35` | `Work in the selected Ripple repository. Read routines/EXECUTION_SHADOW.md completely and follow it exactly. This task owns only the Shadow Execution cohort. Do not perform Decision or live work. If a precondition fails, stop and report it without broadening authority.` |

The desktop workflow is:

1. Open a Codex chat for this local repository and ask it to create the standalone scheduled task with the name, saved prompt, recurrence, and time zone above. You can also create and later manage it from **Scheduled** in the desktop sidebar.
2. Before enabling recurrence, run each saved prompt once in a normal Codex chat. Record the validated catalog output and verify that every selected lane is authorized for the task's cohort.
3. Enable Shadow Decision first. After its first successful scheduled run, inspect `state/accounts/<account_id>/trading_days/<trade-date>/order_plan.json` for each selected lane and its `Decision: shadow <date>` commit.
4. Enable Shadow Execution. After the next-trading-day run, inspect `execution.json` and `report.md` in that same trade-date directory, including the ending virtual account, and its `Execution: shadow <date>` commit. Confirm no broker call occurred.
5. Review the first few runs in **Scheduled**. Pause a task after a failed precondition, Git conflict, unexpected artifact, credential finding, or timing error; scheduled tasks never automatically backfill a missed cycle. A designated-owner historical Decision and any following Execution are separate, explicitly labeled manual operations.

Do not create or enable the two live tasks yet. They become eligible only after the live tasks in [`docs/TODO.md`](TODO.md) are complete and the designated owner explicitly approves the mode change and allocation. Editing a routine changes what the next scheduled run reads; changing a trigger or enabling live remains an operator action in the Scheduled interface and must stay aligned with [`routines/SCHEDULE.md`](../routines/SCHEDULE.md).

## Runner: Claude Code, or any other agent

Any agent that can be pointed at this repository with a prompt satisfies the contract as long as
it meets the seven requirements above. Start it in the repository root with one of the prompts
from *any agent, driven by hand*, and schedule it with whatever the host provides — `cron`,
`launchd`, a CI schedule, or the tool's own scheduler. For example, a headless invocation plus a
system scheduler:

```bash
# Sun-Thu 21:00 America/New_York, Shadow Decision
0 21 * * 0-4  cd /path/to/ripple && claude -p "Run Ripple's normal shadow Decision now. Read AGENTS.md and routines/DECISION_SHADOW.md completely and follow them exactly."
```

Check the requirements that are easy to get wrong with a new runner: an isolated worktree breaks
Decision-to-Execution continuity, a shared session breaks phase isolation, and a runner holding a
broker connection during a shadow run violates the mode contract regardless of what the prompt
says.
