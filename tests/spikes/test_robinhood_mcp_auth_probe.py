import io
import json
import unittest
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout

from spikes import robinhood_mcp_auth_probe as probe


VALID_ENV = {
    probe.URL_ENV: "https://agent.robinhood.com/mcp/trading",
    probe.TOKEN_ENV: "test-secret-that-must-not-leak",
}


class FakeSession:
    def __init__(self, *, initialize_result=None, tools_result=None, error=None):
        self.operations = []
        self.initialize_result = initialize_result or {"protocolVersion": "2025-06-18"}
        self.tools_result = tools_result or {"tools": [{"name": "get_accounts"}]}
        self.error = error

    async def initialize(self):
        self.operations.append("initialize")
        if self.error:
            raise self.error
        return self.initialize_result

    async def list_tools(self):
        self.operations.append("tools/list")
        return self.tools_result

    def __getattr__(self, name):
        self.operations.append(name)
        raise AssertionError("unexpected broker operation")


class FakeHttpFailure(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.response = type("Response", (), {"status_code": status_code})()


def factory_for(session):
    @asynccontextmanager
    async def factory(_config):
        yield session

    return factory


def invoke_main(environ, factory, argv=()):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = probe.main(environ=environ, session_factory=factory, argv=argv)
    return status, stdout.getvalue(), stderr.getvalue()


class RobinhoodMcpAuthProbeTests(unittest.TestCase):
    def test_success_emits_sanitized_json_and_only_discovers_tools(self):
        session = FakeSession(
            tools_result={
                "tools": [
                    {"name": "get_accounts"},
                    {"name": "place_equity_order"},
                ]
            }
        )

        status, stdout, stderr = invoke_main(VALID_ENV, factory_for(session))

        self.assertEqual(status, 0)
        self.assertEqual(
            json.loads(stdout),
            {
                "ok": True,
                "operation": "initialize+tools/list",
                "protocol_version": "2025-06-18",
                "server": "robinhood_trading",
                "tool_count": 2,
            },
        )
        self.assertEqual(stderr, "")
        self.assertEqual(session.operations, ["initialize", "tools/list"])

    def test_missing_config_fails_closed_without_opening_a_session(self):
        opened = False

        @asynccontextmanager
        async def factory(_config):
            nonlocal opened
            opened = True
            yield FakeSession()

        status, stdout, stderr = invoke_main({}, factory)

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["error"], "missing_or_invalid_config")
        self.assertEqual(stderr, "")
        self.assertFalse(opened)

    def test_plaintext_command_line_arguments_are_rejected_and_redacted(self):
        secret = VALID_ENV[probe.TOKEN_ENV]
        session = FakeSession()

        status, stdout, stderr = invoke_main(VALID_ENV, factory_for(session), argv=(secret,))

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["error"], "arguments_not_allowed")
        self.assertNotIn(secret, stdout)
        self.assertNotIn(secret, stderr)
        self.assertEqual(session.operations, [])

    def test_auth_failure_redacts_secret_from_stdout_and_stderr(self):
        secret = VALID_ENV[probe.TOKEN_ENV]
        session = FakeSession(error=RuntimeError("authentication failed for " + secret))

        status, stdout, stderr = invoke_main(VALID_ENV, factory_for(session))

        self.assertEqual(status, 1)
        self.assertNotIn(secret, stdout)
        self.assertNotIn(secret, stderr)
        self.assertEqual(json.loads(stdout)["error"], "connection_or_authentication_failure")
        self.assertEqual(session.operations, ["initialize"])

    def test_http_auth_and_interaction_failures_are_distinguished_and_redacted(self):
        secret = VALID_ENV[probe.TOKEN_ENV]
        for status_code, expected_error in (
            (302, "interaction_required"),
            (401, "authentication_failure"),
        ):
            with self.subTest(status_code=status_code):
                session = FakeSession(error=FakeHttpFailure(status_code, secret))

                status, stdout, stderr = invoke_main(VALID_ENV, factory_for(session))

                self.assertEqual(status, 1)
                self.assertEqual(json.loads(stdout)["error"], expected_error)
                self.assertNotIn(secret, stdout)
                self.assertNotIn(secret, stderr)
                self.assertEqual(session.operations, ["initialize"])

    def test_malformed_tools_response_fails_closed(self):
        session = FakeSession(tools_result={"tools": "not-a-list"})

        status, stdout, _stderr = invoke_main(VALID_ENV, factory_for(session))

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["error"], "malformed_protocol_response")
        self.assertEqual(session.operations, ["initialize", "tools/list"])

    def test_unexpected_endpoint_fails_closed(self):
        invalid_env = dict(VALID_ENV)
        invalid_env[probe.URL_ENV] = "https://example.com/mcp"
        session = FakeSession()

        status, stdout, _stderr = invoke_main(invalid_env, factory_for(session))

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout)["error"], "missing_or_invalid_config")
        self.assertEqual(session.operations, [])


if __name__ == "__main__":
    unittest.main()
