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

The second trigger occurred because the schedule was moved to a later minute while the first run had not yet appeared in the task list. It was paused as soon as those results were observed; the later third controlled rerun is recorded below.

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

[`uv --no-cache`](https://docs.astral.sh/uv/concepts/cache/) uses a temporary cache for a single invocation. Locally, `/opt/homebrew/bin/uv run --no-cache python --version` selected Python 3.12.13 successfully. This leaves the host's system Python unchanged. That local command check and the earlier failed Automation runs do not prove a successful Automation run; the paused Automation has not yet run the no-cache command.

## What this demonstrates

- A local Codex cron Automation can autonomously create a standalone task against the actual Ripple checkout and start the constrained, read-only command.
- No human interaction was required for either trigger.
- The observed local unqualified `python3` runtime lacks the standard-library `zoneinfo` module, so the first two runs did not establish a usable scheduling runtime for the timezone probe.
- The third Automation run demonstrated that its default uv cache is not writable; it did not start Python or the probe.

## What remains unproven

- This is not evidence about cloud Automation, cloud checkout selection, secrets, usage, or any cloud runtime.
- The probe has not reached its JSON output or Git lookup in an Automation run, so the observed commit and a successful read-only Automation runtime report remain unverified.
- Three failed starts do not establish scheduler reliability, timing precision, or daylight-saving behavior.
- No broker operation, network operation, credential access, or production scheduling behavior was tested.
