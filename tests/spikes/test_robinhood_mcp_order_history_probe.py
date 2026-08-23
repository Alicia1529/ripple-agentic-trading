import asyncio
import importlib.util
import io
import json
import sys
import unittest
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace


PROBE_PATH = Path(__file__).resolve().parents[2] / "spikes" / "robinhood_mcp_order_history_probe.py"
sys.path.insert(0, str(PROBE_PATH.parent))
PROBE_SPEC = importlib.util.spec_from_file_location("ripple_robinhood_mcp_order_history_probe", PROBE_PATH)
order_history_probe = importlib.util.module_from_spec(PROBE_SPEC)
sys.modules[PROBE_SPEC.name] = order_history_probe
PROBE_SPEC.loader.exec_module(order_history_probe)


class FakeSession:
    def __init__(self):
        self.calls = []

    async def initialize(self):
        self.calls.append("initialize")

    async def call_tool(self, name, arguments):
        self.calls.append(("call_tool", name, arguments))
        if name == "get_accounts":
            return SimpleNamespace(
                structuredContent={
                    "data": {
                        "accounts": [
                            {
                                "account_number": "private-agentic-account",
                                "agentic_allowed": True,
                                "deactivated": False,
                                "permanently_deactivated": False,
                                "state": "active",
                            }
                        ]
                    }
                }
            )
        return SimpleNamespace(
            structuredContent={
                "data": {
                    "orders": [
                        {
                            "id": "private-order-id",
                            "symbol": "PRIVATE",
                            "quantity": "12.5",
                            "price": "99.99",
                            "state": "filled",
                        }
                    ]
                }
            }
        )


class OrderHistoryProbeTests(unittest.TestCase):
    def test_reads_history_for_the_only_accessible_account_without_disclosing_orders(self):
        session = FakeSession()

        @asynccontextmanager
        async def session_factory(_provider):
            yield session

        result = asyncio.run(order_history_probe.run_order_history_probe(object(), session_factory))

        self.assertEqual(
            session.calls,
            [
                "initialize",
                ("call_tool", "get_accounts", {}),
                ("call_tool", "get_equity_orders", {"account_number": "private-agentic-account"}),
            ],
        )
        self.assertEqual(
            result.evidence,
            {
                "history_response_well_formed": True,
                "order_history_access_demonstrated": True,
                "outcome": "equity_order_history_read",
                "server": "robinhood_trading",
            },
        )
        serialized = json.dumps(result.evidence)
        for private_value in ("private-order-id", "PRIVATE", "12.5", "99.99", "filled"):
            self.assertNotIn(private_value, serialized)

    def test_malformed_history_fails_closed(self):
        class MalformedHistorySession(FakeSession):
            async def call_tool(self, name, arguments):
                if name == "get_equity_orders":
                    return SimpleNamespace(structuredContent={"data": {"orders": "private-order"}})
                return await super().call_tool(name, arguments)

        session = MalformedHistorySession()

        @asynccontextmanager
        async def session_factory(_provider):
            yield session

        with self.assertRaises(order_history_probe.OrderHistoryProbeError):
            asyncio.run(order_history_probe.run_order_history_probe(object(), session_factory))

    def test_ambiguous_account_binding_fails_before_history_is_read(self):
        class AmbiguousAccountSession(FakeSession):
            async def call_tool(self, name, arguments):
                self.calls.append(("call_tool", name, arguments))
                return SimpleNamespace(
                    structuredContent={
                        "data": {
                            "accounts": [
                                {
                                    "account_number": number,
                                    "agentic_allowed": True,
                                    "deactivated": False,
                                    "permanently_deactivated": False,
                                    "state": "active",
                                }
                                for number in ("private-first", "private-second")
                            ]
                        }
                    }
                )

        session = AmbiguousAccountSession()

        @asynccontextmanager
        async def session_factory(_provider):
            yield session

        with self.assertRaises(order_history_probe.AccountBindingError):
            asyncio.run(order_history_probe.run_order_history_probe(object(), session_factory))
        self.assertFalse(any(call[1] == "get_equity_orders" for call in session.calls if isinstance(call, tuple)))

    def test_main_never_prints_order_or_exception_details(self):
        secret = "private-order-detail"

        async def failed():
            raise RuntimeError(secret)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = order_history_probe.main(argv=[], command_runner=failed)

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["outcome"], "order_history_probe_failed")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
