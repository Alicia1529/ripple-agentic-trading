import asyncio
import importlib.util
import io
import json
import sys
import unittest
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace


PROBE_PATH = Path(__file__).resolve().parents[2] / "spikes" / "robinhood_mcp_account_probe.py"
sys.path.insert(0, str(PROBE_PATH.parent))
PROBE_SPEC = importlib.util.spec_from_file_location("ripple_robinhood_mcp_account_probe", PROBE_PATH)
account_probe = importlib.util.module_from_spec(PROBE_SPEC)
sys.modules[PROBE_SPEC.name] = account_probe
PROBE_SPEC.loader.exec_module(account_probe)


class FakeSession:
    def __init__(self, accounts):
        self.accounts = accounts
        self.calls = []

    async def initialize(self):
        self.calls.append("initialize")

    async def call_tool(self, name, arguments):
        self.calls.append(("call_tool", name, arguments))
        return SimpleNamespace(structuredContent={"data": {"accounts": self.accounts}})


def account(number, *, accessible):
    return {
        "account_number": number,
        "agentic_allowed": accessible,
        "deactivated": False,
        "permanently_deactivated": False,
        "state": "active",
    }


class AccountProbeTests(unittest.TestCase):
    def run_probe(self, accounts):
        session = FakeSession(accounts)

        @asynccontextmanager
        async def session_factory(_provider):
            yield session

        result = asyncio.run(account_probe.run_account_probe(object(), session_factory))
        return result, session

    def test_selects_the_only_accessible_account_without_disclosing_it(self):
        result, session = self.run_probe(
            [account("private-read-only", accessible=False), account("private-agentic", accessible=True)]
        )

        self.assertEqual(session.calls, ["initialize", ("call_tool", "get_accounts", {})])
        self.assertEqual(result.binding.account_number, "private-agentic")
        self.assertEqual(
            result.evidence,
            {
                "account_binding_demonstrated": True,
                "accessible_account_active": True,
                "brokerage_account_count": 2,
                "outcome": "agentic_account_binding_selected",
                "server": "robinhood_trading",
            },
        )
        self.assertNotIn("private", json.dumps(result.evidence))

    def test_zero_or_multiple_accessible_accounts_fail_closed(self):
        cases = (
            [account("read-only", accessible=False)],
            [account("first", accessible=True), account("second", accessible=True)],
        )
        for accounts in cases:
            with self.subTest(count=len(accounts)):
                with self.assertRaises(account_probe.AccountBindingError):
                    self.run_probe(accounts)

    def test_malformed_account_response_fails_closed(self):
        cases = (None, [None], [{"account_number": "private"}], [account("", accessible=True)])
        for accounts in cases:
            with self.subTest(accounts=accounts):
                with self.assertRaises(account_probe.AccountBindingError):
                    self.run_probe(accounts)

    def test_main_never_prints_account_or_exception_details(self):
        secret = "private-agentic-account"

        async def successful():
            return account_probe.AccountProbeResult(
                binding=account_probe.AgenticAccountBinding(account_number=secret),
                evidence={
                    "account_binding_demonstrated": True,
                    "accessible_account_active": True,
                    "brokerage_account_count": 1,
                    "outcome": "agentic_account_binding_selected",
                    "server": "robinhood_trading",
                },
            )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = account_probe.main(argv=[], command_runner=successful)

        self.assertEqual(status, 0)
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

        async def failed():
            raise RuntimeError(secret)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = account_probe.main(argv=[], command_runner=failed)

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["outcome"], "account_binding_failed")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_account_bearing_dataclasses_do_not_reveal_identifier_in_repr(self):
        secret = "private-agentic-account"
        result = account_probe.AccountProbeResult(
            binding=account_probe.AgenticAccountBinding(account_number=secret), evidence={"outcome": "ok"}
        )
        self.assertNotIn(secret, repr(result))


if __name__ == "__main__":
    unittest.main()
