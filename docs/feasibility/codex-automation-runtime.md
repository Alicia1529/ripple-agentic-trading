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

The second trigger occurred because the schedule was moved to a later minute while the first run had not yet appeared in the task list. It was paused as soon as those results were observed; no further runs are scheduled.

## What this demonstrates

- A local Codex cron Automation can autonomously create a standalone task against the actual Ripple checkout and start the constrained, read-only command.
- No human interaction was required for either trigger.
- The observed local `python3` runtime lacks the standard-library `zoneinfo` module, so this run did not establish a usable scheduling runtime for the timezone probe.

## What remains unproven

- This is not evidence about cloud Automation, cloud checkout selection, secrets, usage, or any cloud runtime.
- The probe did not reach its JSON output or Git lookup, so the observed commit and a successful read-only runtime report remain unverified.
- Two failed starts do not establish scheduler reliability, timing precision, or daylight-saving behavior.
- No broker operation, network operation, credential access, or production scheduling behavior was tested.
