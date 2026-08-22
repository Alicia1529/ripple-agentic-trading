#!/usr/bin/env python3
"""Read-only runtime probe for a Codex Automation invocation."""

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Tuple


NEW_YORK = "America/New_York"


class ProbeFailure(Exception):
    """A runtime property required for this feasibility probe was unavailable."""


def _repository_metadata(cwd: Path) -> Mapping[str, str]:
    """Return the current checkout metadata without changing it."""
    try:
        top_level = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProbeFailure("git_metadata_unavailable") from exc

    if not head:
        raise ProbeFailure("git_head_unavailable")
    return {"head": head, "top_level": top_level}


def _new_york_timezone() -> Any:
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError as exc:
        raise ProbeFailure("america_new_york_unavailable") from exc
    try:
        return ZoneInfo(NEW_YORK)
    except ZoneInfoNotFoundError as exc:
        raise ProbeFailure("america_new_york_unavailable") from exc


def _result(
    now: datetime,
    cwd: Path,
    metadata: Mapping[str, str],
    new_york_timezone: Any,
) -> Mapping[str, Any]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ProbeFailure("naive_timestamp")
    utc_now = now.astimezone(timezone.utc)
    eastern_now = utc_now.astimezone(new_york_timezone)
    offset = eastern_now.utcoffset()
    if offset is None:
        raise ProbeFailure("timezone_offset_unavailable")

    top_level = Path(metadata.get("top_level", "")).resolve()
    if top_level != cwd or not (cwd / "AGENTS.md").is_file() or not (cwd / "docs").is_dir():
        raise ProbeFailure("not_ripple_repository")

    return {
        "broker_calls_attempted": 0,
        "current_working_directory": str(cwd),
        "git_head": metadata["head"],
        "observed_america_new_york": eastern_now.isoformat(),
        "observed_utc": utc_now.isoformat(),
        "python_runtime": platform.python_version(),
        "timezone_name": eastern_now.tzname(),
        "utc_offset": eastern_now.strftime("%z"),
    }


def run_probe(
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    metadata_reader: Callable[[Path], Mapping[str, str]] = _repository_metadata,
    cwd: Optional[Path] = None,
    timezone_loader: Callable[[], Any] = _new_york_timezone,
) -> Mapping[str, Any]:
    """Collect the narrow, read-only facts used by the scheduler feasibility check."""
    working_directory = (cwd or Path.cwd()).resolve()
    new_york_timezone = timezone_loader()
    return _result(clock(), working_directory, metadata_reader(working_directory), new_york_timezone)


def main(
    argv: Optional[Tuple[str, ...]] = None,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    metadata_reader: Callable[[Path], Mapping[str, str]] = _repository_metadata,
    cwd: Optional[Path] = None,
    timezone_loader: Callable[[], Any] = _new_york_timezone,
) -> int:
    """Print exactly one sanitized JSON result and return a shell status."""
    if (tuple(sys.argv[1:]) if argv is None else argv):
        outcome: Mapping[str, Any] = {"broker_calls_attempted": 0, "error": "arguments_not_allowed"}
        status = 1
    else:
        try:
            outcome = run_probe(
                clock=clock,
                metadata_reader=metadata_reader,
                cwd=cwd,
                timezone_loader=timezone_loader,
            )
            status = 0
        except (KeyError, ProbeFailure):
            outcome = {"broker_calls_attempted": 0, "error": "runtime_probe_failed"}
            status = 1

    print(json.dumps(outcome, separators=(",", ":"), sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
