import importlib.util
import io
import json
import os
import socket
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


PROBE_PATH = Path(__file__).resolve().parents[2] / "spikes" / "codex_scheduler_runtime_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("ripple_codex_scheduler_runtime_probe", PROBE_PATH)
probe = importlib.util.module_from_spec(PROBE_SPEC)
sys.modules[PROBE_SPEC.name] = probe
PROBE_SPEC.loader.exec_module(probe)


REPO = Path(__file__).resolve().parents[2]
HEAD = "a" * 40


def metadata_reader(cwd):
    return {"top_level": str(cwd), "head": HEAD}


def invoke(now, metadata=metadata_reader, cwd=REPO, argv=(), timezone_loader=probe._new_york_timezone):
    output = io.StringIO()
    with redirect_stdout(output):
        status = probe.main(
            argv=argv,
            clock=lambda: now,
            metadata_reader=metadata,
            cwd=cwd,
            timezone_loader=timezone_loader,
        )
    return status, output.getvalue()


class CodexSchedulerRuntimeProbeTests(unittest.TestCase):
    def test_winter_conversion_uses_utc_minus_five(self):
        status, output = invoke(datetime(2026, 1, 15, 15, 30, tzinfo=timezone.utc))

        self.assertEqual(status, 0)
        result = json.loads(output)
        self.assertEqual(result["observed_america_new_york"], "2026-01-15T10:30:00-05:00")
        self.assertEqual(result["utc_offset"], "-0500")
        self.assertEqual(result["timezone_name"], "EST")

    def test_summer_conversion_uses_utc_minus_four(self):
        status, output = invoke(datetime(2026, 7, 15, 15, 30, tzinfo=timezone.utc))

        self.assertEqual(status, 0)
        result = json.loads(output)
        self.assertEqual(result["observed_america_new_york"], "2026-07-15T11:30:00-04:00")
        self.assertEqual(result["utc_offset"], "-0400")
        self.assertEqual(result["timezone_name"], "EDT")

    def test_fold_adjacent_timestamp_has_unambiguous_utc_offset(self):
        status, output = invoke(datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc))

        self.assertEqual(status, 0)
        result = json.loads(output)
        self.assertEqual(result["observed_america_new_york"], "2026-11-01T01:30:00-05:00")
        self.assertEqual(result["utc_offset"], "-0500")

    def test_output_is_one_sanitized_json_line(self):
        secret = "environment-value-must-not-leak"
        with patch.dict(os.environ, {"RIPPLE_TEST_SECRET": secret}):
            status, output = invoke(datetime(2026, 1, 1, tzinfo=timezone.utc))

        self.assertEqual(status, 0)
        self.assertEqual(output.count("\n"), 1)
        result = json.loads(output)
        self.assertEqual(result["git_head"], HEAD)
        self.assertEqual(result["broker_calls_attempted"], 0)
        self.assertNotIn(secret, output)
        self.assertNotIn("environ", output.lower())

    def test_failure_paths_fail_closed_without_environment_leakage(self):
        secret = "scheduler-secret-must-not-leak"

        status, output = invoke(datetime(2026, 1, 1), argv=())
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output), {"broker_calls_attempted": 0, "error": "runtime_probe_failed"})

        def bad_metadata(_cwd):
            raise probe.ProbeFailure(secret)

        status, output = invoke(datetime(2026, 1, 1, tzinfo=timezone.utc), metadata=bad_metadata)
        self.assertEqual(status, 1)
        self.assertNotIn(secret, output)
        self.assertEqual(json.loads(output), {"broker_calls_attempted": 0, "error": "runtime_probe_failed"})

        status, output = invoke(datetime(2026, 1, 1, tzinfo=timezone.utc), cwd=REPO.parent)
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output), {"broker_calls_attempted": 0, "error": "runtime_probe_failed"})

        status, output = invoke(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            metadata=lambda cwd: {"top_level": str(cwd)},
        )
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output), {"broker_calls_attempted": 0, "error": "runtime_probe_failed"})

        status, output = invoke(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            timezone_loader=lambda: (_ for _ in ()).throw(probe.ProbeFailure(secret)),
        )
        self.assertEqual(status, 1)
        self.assertNotIn(secret, output)
        self.assertEqual(json.loads(output), {"broker_calls_attempted": 0, "error": "runtime_probe_failed"})

    def test_no_network_or_broker_calls_are_available_to_the_probe(self):
        original_socket = socket.socket

        def forbidden_socket(*args, **kwargs):
            raise AssertionError("network call attempted")

        socket.socket = forbidden_socket
        try:
            status, output = invoke(datetime(2026, 1, 1, tzinfo=timezone.utc))
        finally:
            socket.socket = original_socket

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)["broker_calls_attempted"], 0)


if __name__ == "__main__":
    unittest.main()
