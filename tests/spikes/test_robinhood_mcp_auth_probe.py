import io
import importlib.util
import json
import sys
import unittest
import asyncio
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import httpx2


PROBE_PATH = Path(__file__).resolve().parents[2] / "spikes" / "robinhood_mcp_auth_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("ripple_robinhood_mcp_auth_probe", PROBE_PATH)
probe = importlib.util.module_from_spec(PROBE_SPEC)
sys.modules[PROBE_SPEC.name] = probe
PROBE_SPEC.loader.exec_module(probe)


VALID_ENV = {probe.URL_ENV: probe.EXPECTED_URL}


class FakeMcpTransport:
    def __init__(self, failure_status=None, malformed=False, exception=None):
        self.calls = []
        self.failure_status = failure_status
        self.malformed = malformed
        self.exception = exception

    async def handle(self, request):
        self.calls.append(request)
        if self.exception:
            raise self.exception
        if self.failure_status:
            headers = {"content-type": "application/json"}
            if 300 <= self.failure_status < 400:
                headers["location"] = "https://interaction.example/authorize"
            return httpx2.Response(self.failure_status, headers=headers)

        message = json.loads(request.content.decode())
        method = message["method"]
        if method == "initialize":
            result = {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "serverInfo": {"name": "fake", "version": "1.0"},
            }
        elif method == "notifications/initialized":
            return httpx2.Response(202)
        elif method == "tools/list":
            result = "malformed" if self.malformed else {
                "tools": [{"name": "get_accounts", "inputSchema": {"type": "object"}}]
            }
        else:
            raise AssertionError("unexpected MCP method: " + method)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": message.get("id"), "result": result},
        )

    def transport(self):
        return httpx2.MockTransport(self.handle)


def session_factory(transport):
    @asynccontextmanager
    async def factory(config):
        async with probe.mcp_session(config, http_transport=transport.transport()) as session:
            yield session

    return factory


def invoke_main(environ, factory, argv=(), metadata_discoverer=probe.discover_oauth_metadata):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = probe.main(environ=environ, session_factory=factory, argv=argv, metadata_discoverer=metadata_discoverer)
    return status, stdout.getvalue(), stderr.getvalue()


class RobinhoodMcpAuthProbeTests(unittest.TestCase):
    def test_oauth_metadata_discovery_is_read_only_and_sanitized(self):
        secret = "metadata-secret-must-not-leak"
        calls = []

        async def handler(request):
            calls.append(request)
            if request.url.path == "/resource":
                return httpx2.Response(200, json={"resource": probe.EXPECTED_URL, "authorization_servers": ["https://auth.example"]})
            if request.url.path == "/.well-known/oauth-authorization-server":
                return httpx2.Response(200, json={"issuer": "https://auth.example", "authorization_endpoint": "https://auth.example/authorize?" + secret, "token_endpoint": "https://auth.example/token", "client_id_metadata_document_supported": True})
            raise AssertionError(request.url.path)

        result = asyncio.run(probe.discover_oauth_metadata(
            probe.ProbeConfig(probe.EXPECTED_URL),
            ['Bearer resource_metadata="https://metadata.example/resource"'],
            httpx2.MockTransport(handler),
        ))

        self.assertEqual(result["outcome"], "oauth_metadata_discovered")
        self.assertTrue(result["authorization_endpoint_advertised"])
        self.assertTrue(result["token_endpoint_advertised"])
        self.assertEqual(result["client_registration"], "client_id_metadata")
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual([call.method for call in calls], ["GET", "GET"])
        self.assertTrue(all("authorization" not in call.headers for call in calls))

    def test_oauth_metadata_discovery_fails_closed(self):
        for challenge in ([], ['Bearer resource_metadata="http://metadata.example/resource"'], ['Basic abc']):
            with self.subTest(challenge=challenge):
                with self.assertRaises(probe.MalformedProtocolResponse):
                    asyncio.run(probe.discover_oauth_metadata(probe.ProbeConfig(probe.EXPECTED_URL), challenge, httpx2.MockTransport(lambda request: None)))

    def test_transport_only_initializes_and_lists_tools_without_delete_or_tool_call(self):
        transport = FakeMcpTransport()

        status, stdout, stderr = invoke_main(VALID_ENV, session_factory(transport))

        self.assertEqual(status, 1)
        self.assertEqual(
            json.loads(stdout),
            {
                "authentication": "not_demonstrated",
                "headless_authentication_proven": False,
                "outcome": "protocol_reachable_tool_discovery",
                "protocol_version": "2025-11-25",
                "server": "robinhood_trading",
                "tool_count": 1,
            },
        )
        self.assertEqual(stderr, "")
        self.assertEqual([request.method for request in transport.calls], ["POST", "POST", "POST"])
        self.assertEqual(
            [json.loads(request.content.decode())["method"] for request in transport.calls],
            ["initialize", "notifications/initialized", "tools/list"],
        )
        self.assertNotIn("authorization", transport.calls[0].headers)
        self.assertNotIn("DELETE", [request.method for request in transport.calls])
        self.assertNotIn(
            "tools/call",
            [json.loads(request.content.decode())["method"] for request in transport.calls],
        )

    def test_authentication_and_interaction_requirements_fail_closed_without_redirects(self):
        for status_code, outcome in (
            (401, "oauth_metadata_discovery_failed"),
            (302, "interactive_authentication_required"),
        ):
            with self.subTest(status_code=status_code):
                transport = FakeMcpTransport(failure_status=status_code)

                async def discovery_failure(_config, _challenges):
                    raise probe.MalformedProtocolResponse

                status, stdout, stderr = invoke_main(VALID_ENV, session_factory(transport), metadata_discoverer=discovery_failure)

                self.assertEqual(status, 1)
                self.assertEqual(json.loads(stdout)["outcome"], outcome)
                self.assertEqual(stderr, "")
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(transport.calls[0].url.host, "agent.robinhood.com")
                self.assertEqual(transport.calls[0].method, "POST")

    def test_malformed_response_fails_closed(self):
        transport = FakeMcpTransport(malformed=True)

        status, stdout, _stderr = invoke_main(VALID_ENV, session_factory(transport))

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["outcome"], "malformed_or_invalid_protocol_response")

    def test_exception_messages_cannot_reach_stdout_or_stderr(self):
        secret = "secret-that-must-not-leak"
        transport = FakeMcpTransport(exception=RuntimeError("failure " + secret))

        status, stdout, stderr = invoke_main(VALID_ENV, session_factory(transport))

        self.assertEqual(status, 1)
        self.assertNotIn(secret, stdout)
        self.assertNotIn(secret, stderr)
        self.assertEqual(json.loads(stdout)["outcome"], "connection_or_protocol_failure")

    def test_connection_failure_fails_closed(self):
        transport = FakeMcpTransport(exception=OSError("network unavailable"))

        status, stdout, _stderr = invoke_main(VALID_ENV, session_factory(transport))

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["outcome"], "connection_failure")

    def test_invalid_config_and_command_line_arguments_fail_closed(self):
        transport = FakeMcpTransport()

        status, stdout, _stderr = invoke_main({}, session_factory(transport))
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["outcome"], "missing_or_invalid_config")
        self.assertEqual(transport.calls, [])

        status, stdout, _stderr = invoke_main(VALID_ENV, session_factory(transport), argv=("secret",))
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["outcome"], "arguments_not_allowed")
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
