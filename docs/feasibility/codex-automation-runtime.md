# Codex Automation runtime probe

## Observation

On 2026-08-22, a temporary standalone Codex Automation named `Ripple scheduler runtime probe (temporary)` targeted the local Ripple project checkout at `/Users/Alicia/Desktop/all/GitHub/ripple`. Its backing kind was `codex`; its configured execution environment was `local`, not cloud. The task was paused immediately after the runs became observable and was retained for Alicia's inspection.

The prompt allowed exactly one command:

```text
python3 spikes/codex_scheduler_runtime_probe.py
```

It prohibited edits, environment or secret access, network activity, broker tools, and all other commands. The expected Git commit was `b57912d4c17fae5d8f74d80da4aaf01f15991c63`, the checked-out HEAD when the Automation was created.

| Scheduled local time | Actual start (UTC) | Drift | Result | Observed Git HEAD |
| --- | --- | --- | --- | --- |
| 2026-08-22 16:22:00 −07:00 | 2026-08-22T23:22:42Z | +42 s | exit 1; `ModuleNotFoundError: zoneinfo` before probe output | Not determined |
| 2026-08-22 16:24:00 −07:00 | 2026-08-22T23:24:42Z | +42 s | exit 1; `ModuleNotFoundError: zoneinfo` before probe output | Not determined |
| 2026-08-22 16:44:00 −07:00 | 2026-08-22T23:44:13Z | +13 s | exit 2; uv could not write `/Users/Alicia/.cache/uv` before Python startup | Not determined |
| 2026-08-22 16:50:00 −07:00 | 2026-08-22T23:50:13Z | +13 s | exit 0; `uv run --no-cache` ran the probe with Python 3.12.13, EDT / -0400, and `broker_calls_attempted: 0` | `238b98b28b01e5499b87ee84f29f152b0d263460` |

The second trigger occurred because the schedule was moved to a later minute while the first run had not yet appeared in the task list. It was paused as soon as those results were observed; the later third and fourth controlled reruns are recorded below.

## Environment follow-up

The repository declares Python 3.12 in its root `.python-version` file. A third local Automation run at the configured 16:44 PDT trigger used:

```text
uv run python spikes/codex_scheduler_runtime_probe.py
```

It started at 2026-08-22T23:44:13Z, +13 seconds after the 23:44:00Z configured trigger, then exited 2 before Python started because uv attempted to initialize `/Users/Alicia/.cache/uv`, which the Automation sandbox cannot write. The Automation was immediately paused.

The next controlled command is:

```text
uv run --no-cache python spikes/codex_scheduler_runtime_probe.py
```

[`uv --no-cache`](https://docs.astral.sh/uv/concepts/cache/) uses a temporary cache for a single invocation. The fourth controlled local Automation run used that exact command at the configured 16:50 PDT trigger. It started at 2026-08-22T23:50:13Z (+13 seconds), exited 0, ran Python 3.12.13, observed EDT / `-0400`, reported `broker_calls_attempted: 0`, and observed Git HEAD `238b98b28b01e5499b87ee84f29f152b0d263460`. The Automation was immediately paused after the result.

## What this demonstrates

- A local Codex cron Automation can autonomously create a standalone task against the actual Ripple checkout and start the constrained, read-only command.
- No human interaction was required for any of the four scheduled runs.
- The observed local unqualified `python3` runtime lacks the standard-library `zoneinfo` module, so the first two runs did not establish a usable scheduling runtime for the timezone probe.
- The third Automation run demonstrated that its default uv cache is not writable; it did not start Python or the probe.
- The fourth controlled local run proves that this local Automation can execute the read-only probe through `uv run --no-cache` without human interaction.

## What remains unproven

- This is not evidence about cloud Automation, cloud checkout selection, secrets, usage limits, or any cloud runtime.
- One successful controlled run does not establish repeated-run reliability, timing precision, or daylight-saving behavior.
- No broker operation, network operation, credential access, or production scheduling behavior was tested.

## Near-term reschedule observation

Later on 2026-08-22, the same paused Automation was reactivated twice with the unchanged safe prompt and command, first for 19:25 PDT and then for 19:28 PDT. No new standalone task appeared in the project task list by 19:26:36 (96 seconds after the first trigger) or by 19:29:07 (67 seconds after the second trigger). The Automation memory also remained unchanged from the successful 16:50 run. It was paused again at 19:29 PDT to prevent a late or next-day execution.

These are bounded missed-trigger observations, not probe-command failures: the Python command never became observable as started. Because both schedules were edited only shortly before their target minute, this does not prove that a stable schedule configured well in advance is unreliable. It does show that near-term RRULE edits are not a dependable way to request an immediate verification run and must not be used as the production scheduling model.

## Stable-schedule follow-up in progress

At 2026-08-22 21:43 PDT, the same temporary Automation was reactivated without changing its safe prompt, command, project, or 19:28 PDT daily schedule. Its next trigger is 2026-08-23 19:28 PDT, about 21 hours 44 minutes after activation. This deliberately avoids the near-term-edit condition above. The run is pending and is not evidence until its standalone task and output are observed; after observation, pause the Automation or retain exactly one further unchanged trigger to test repetition.
