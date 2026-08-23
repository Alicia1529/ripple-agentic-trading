import asyncio
import importlib.util
import io
import json
import sys
import time
import unittest
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx2
from mcp.shared.auth import OAuthClientInformationFull, OAuthMetadata, OAuthToken


CLI_PATH = Path(__file__).resolve().parents[2] / "spikes" / "robinhood_mcp_oauth_cli.py"
sys.path.insert(0, str(CLI_PATH.parent))
CLI_SPEC = importlib.util.spec_from_file_location("ripple_robinhood_mcp_oauth_cli", CLI_PATH)
oauth_cli = importlib.util.module_from_spec(CLI_SPEC)
sys.modules[CLI_SPEC.name] = oauth_cli
CLI_SPEC.loader.exec_module(oauth_cli)


async def send_callback(port, target):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET {target} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode())
    await writer.drain()
    response = await reader.read()
    writer.close()
    await writer.wait_closed()
    return response


async def async_value(value):
    return value


class FakeSession:
    def __init__(self):
        self.calls = []

    async def initialize(self):
        self.calls.append("initialize")
        return {"protocolVersion": "2025-11-25"}

    async def list_tools(self):
        self.calls.append("list_tools")
        return {"tools": [{"name": "read_only_tool"}, {"name": "write_tool_not_called"}]}


class MemoryStateStore:
    def __init__(self, versioned_state=None):
        self.versioned_state = versioned_state

    async def load(self):
        return self.versioned_state

    async def compare_and_swap(self, expected_revision, state):
        current_revision = self.versioned_state.revision if self.versioned_state else None
        if current_revision != expected_revision:
            raise oauth_cli.OAuthStateConflict("state changed")
        next_revision = "1" if current_revision is None else str(int(current_revision) + 1)
        self.versioned_state = oauth_cli.VersionedOAuthState(next_revision, state)
        return next_revision

    async def clear(self, expected_revision):
        if self.versioned_state is None or self.versioned_state.revision != expected_revision:
            raise oauth_cli.OAuthStateConflict("state changed")
        self.versioned_state = None


def versioned_state(*, expires_at=None, revision="1"):
    return oauth_cli.VersionedOAuthState(
        revision,
        oauth_cli.OAuthState(
            server_url=oauth_cli.SERVER_URL,
            resource_url=oauth_cli.SERVER_URL,
            issuer="https://auth.example",
            access_token_expires_at=time.time() + 3600 if expires_at is None else expires_at,
            tokens=OAuthToken(
                access_token="access-old",
                token_type="Bearer",
                expires_in=3600,
                refresh_token="refresh-old",
                scope="mcp:tools",
            ),
            client_info=OAuthClientInformationFull(
                client_id="client-id",
                grant_types=["authorization_code", "refresh_token"],
                issuer="https://auth.example",
            ),
            oauth_metadata=OAuthMetadata(
                issuer="https://auth.example",
                authorization_endpoint="https://auth.example/authorize",
                token_endpoint="https://auth.example/token",
                registration_endpoint="https://auth.example/register",
            ),
        ),
    )


class LoopbackOAuthCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_false_browser_return_does_not_close_an_open_callback_listener(self):
        callback = oauth_cli.LoopbackOAuthCallback(port=0, open_browser=lambda _url: False)
        authorization_url = "https://auth.example/authorize?state=expected-state"

        await callback.redirect_handler(authorization_url)
        response = await send_callback(
            callback.bound_port,
            "/callback?code=fresh-code&state=expected-state",
        )
        result = await callback.callback_handler()

        self.assertEqual(result.code, "fresh-code")
        self.assertIn(b"Authorization complete", response)

    async def test_browser_exception_after_launch_does_not_close_callback_listener(self):
        opened = []

        def launch_then_raise(url):
            opened.append(url)
            raise OSError("launcher reported failure after handing off URL")

        callback = oauth_cli.LoopbackOAuthCallback(port=0, open_browser=launch_then_raise)
        authorization_url = "https://auth.example/authorize?state=expected-state"

        await callback.redirect_handler(authorization_url)
        response = await send_callback(
            callback.bound_port,
            "/callback?code=fresh-code&state=expected-state",
        )
        result = await callback.callback_handler()

        self.assertEqual(opened, [authorization_url])
        self.assertEqual(result.code, "fresh-code")
        self.assertIn(b"Authorization complete", response)

    async def test_receives_one_valid_callback_without_exposing_code(self):
        opened = []
        callback = oauth_cli.LoopbackOAuthCallback(port=0, open_browser=lambda url: opened.append(url) or True)
        authorization_url = "https://auth.example/authorize?state=expected-state"

        await callback.redirect_handler(authorization_url)
        response = await send_callback(
            callback.bound_port,
            "/callback?code=secret-authorization-code&state=expected-state&iss=https%3A%2F%2Fauth.example",
        )
        result = await callback.callback_handler()

        self.assertEqual(opened, [authorization_url])
        self.assertEqual(result.code, "secret-authorization-code")
        self.assertEqual(result.state, "expected-state")
        self.assertEqual(result.iss, "https://auth.example")
        self.assertIn(b"Authorization complete", response)
        self.assertNotIn(b"secret-authorization-code", response)

    async def test_duplicate_or_error_parameters_fail_closed(self):
        targets = [
            "/callback?code=one&code=two&state=expected",
            "/callback?code=one&state=first&state=second",
            "/callback?code=one&state=unexpected",
            "/callback?error=access_denied&state=expected",
            "/wrong?code=one&state=expected",
        ]
        for target in targets:
            with self.subTest(target=target):
                callback = oauth_cli.LoopbackOAuthCallback(port=0, open_browser=lambda _url: True)
                await callback.redirect_handler("https://auth.example/authorize?state=expected")
                response = await send_callback(callback.bound_port, target)
                with self.assertRaises(oauth_cli.OAuthCallbackError):
                    await callback.callback_handler()
                self.assertIn(b"400 Bad Request", response)


class OAuthCliTests(unittest.TestCase):
    def test_mcp_session_does_not_timeout_before_interactive_callback(self):
        observed = {}

        @asynccontextmanager
        async def fake_streamable_http_client(*_args, **_kwargs):
            yield (object(), object())

        class CapturingClientSession:
            def __init__(self, *_streams, read_timeout_seconds):
                observed["read_timeout_seconds"] = read_timeout_seconds

            async def __aenter__(self):
                return object()

            async def __aexit__(self, *_args):
                return None

        async def open_session():
            async with oauth_cli.mcp_session(None):
                pass

        with (
            patch.object(oauth_cli, "streamable_http_client", fake_streamable_http_client),
            patch.object(oauth_cli, "ClientSession", CapturingClientSession),
        ):
            asyncio.run(open_session())

        self.assertGreaterEqual(
            observed["read_timeout_seconds"],
            oauth_cli.CALLBACK_TIMEOUT_SECONDS,
        )

    def test_probe_only_initializes_and_lists_tools(self):
        session = FakeSession()

        @asynccontextmanager
        async def session_factory(_provider):
            yield session

        result = asyncio.run(oauth_cli.run_oauth_probe("probe", object(), session_factory))

        self.assertEqual(session.calls, ["initialize", "list_tools"])
        self.assertEqual(result["outcome"], "headless_oauth_tool_discovery")
        self.assertTrue(result["headless_authentication_proven"])
        self.assertEqual(result["tool_count"], 2)
        self.assertNotIn("read_only_tool", json.dumps(result))

    def test_probe_accepts_sdk_style_protocol_version_attribute(self):
        session = FakeSession()
        session.initialize = lambda: async_value(SimpleNamespace(protocolVersion="2025-11-25"))

        @asynccontextmanager
        async def session_factory(_provider):
            yield session

        result = asyncio.run(oauth_cli.run_oauth_probe("probe", object(), session_factory))

        self.assertEqual(result["protocol_version"], "2025-11-25")

    def test_provider_mode_never_attaches_callback_to_headless_probe(self):
        callback = oauth_cli.LoopbackOAuthCallback(port=0, open_browser=lambda _url: True)
        headless = oauth_cli.build_provider("probe", object(), callback)
        interactive = oauth_cli.build_provider("bootstrap", object(), callback)

        self.assertFalse(headless._interactive)
        self.assertIsNone(headless.context.redirect_handler)
        self.assertIsNone(headless.context.callback_handler)
        self.assertTrue(interactive._interactive)
        self.assertIsNotNone(interactive.context.redirect_handler)
        self.assertIsNotNone(interactive.context.callback_handler)

    def test_bootstrap_reports_only_sanitized_stored_state_evidence(self):
        store = MemoryStateStore(versioned_state())

        @asynccontextmanager
        async def session_factory(_provider):
            yield FakeSession()

        result = asyncio.run(
            oauth_cli.run_command(
                "bootstrap",
                store=store,
                callback=oauth_cli.LoopbackOAuthCallback(port=0, open_browser=lambda _url: True),
                session_factory=session_factory,
            )
        )

        self.assertTrue(result["stored_state_model_types_valid"])
        self.assertTrue(result["stored_absolute_expiry_finite"])
        self.assertTrue(result["stored_metadata_binding_valid"])
        encoded = json.dumps(result)
        for secret in ("access-old", "refresh-old", "client-id", "auth.example"):
            self.assertNotIn(secret, encoded)

    def test_refresh_proof_marks_only_expiry_and_observes_one_refresh_replacement(self):
        original = versioned_state()
        store = MemoryStateStore(original)
        observed_before_refresh = []

        @asynccontextmanager
        async def session_factory(provider):
            stale = await store.load()
            observed_before_refresh.append(stale)

            async def handler(request):
                if request.url.host == "auth.example":
                    return httpx2.Response(
                        200,
                        json={
                            "access_token": "access-new",
                            "token_type": "Bearer",
                            "expires_in": 3600,
                            "refresh_token": "refresh-rotated",
                        },
                    )
                return httpx2.Response(200)

            async with httpx2.AsyncClient(
                auth=provider,
                transport=httpx2.MockTransport(handler),
            ) as client:
                await client.post(oauth_cli.SERVER_URL)
            yield FakeSession()

        result = asyncio.run(oauth_cli.run_refresh_proof(store, session_factory))

        stale = observed_before_refresh[0]
        self.assertEqual(stale.revision, "2")
        self.assertEqual(stale.state.access_token_expires_at, 1.0)
        self.assertEqual(
            oauth_cli.replace(stale.state, access_token_expires_at=original.state.access_token_expires_at),
            original.state,
        )
        self.assertEqual(store.versioned_state.revision, "3")
        self.assertEqual(result["refresh_state_replacements"], 1)
        self.assertEqual(result["outcome"], "headless_oauth_refresh_validated")
        self.assertTrue(result["stored_state_model_types_valid"])
        self.assertNotIn("refresh-rotated", json.dumps(result))

    def test_refresh_rejection_requires_bootstrap_without_session_or_secret_output(self):
        store = MemoryStateStore(versioned_state())
        network_hosts = []
        session_entries = []
        secret = "refresh-response-secret-must-not-leak"

        @asynccontextmanager
        async def session_factory(provider):
            async def handler(request):
                network_hosts.append(request.url.host)
                return httpx2.Response(
                    400,
                    json={"error": "invalid_grant", "error_description": secret},
                )

            async with httpx2.AsyncClient(
                auth=provider,
                transport=httpx2.MockTransport(handler),
            ) as client:
                await client.post(oauth_cli.SERVER_URL)
            session_entries.append(True)
            yield FakeSession()

        async def rejected(command):
            return await oauth_cli.run_command(
                command,
                store=store,
                session_factory=session_factory,
            )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = oauth_cli.main(argv=["refresh-proof"], command_runner=rejected)

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["outcome"], "oauth_bootstrap_required")
        self.assertEqual(network_hosts, ["auth.example"])
        self.assertEqual(session_entries, [])
        self.assertIsNone(store.versioned_state)
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_registration_failure_is_attempted_once_without_browser_or_secret_output(self):
        registration_calls = []
        browser_calls = []
        secret = "registration-secret-must-not-leak"
        store = MemoryStateStore()
        callback = oauth_cli.LoopbackOAuthCallback(
            port=0,
            open_browser=lambda url: browser_calls.append(url) or True,
        )
        provider = oauth_cli.build_provider("bootstrap", store, callback)

        async def failed_registration(_command):
            async def handler(request):
                if str(request.url) == oauth_cli.SERVER_URL:
                    return httpx2.Response(
                        401,
                        headers={
                            "WWW-Authenticate": (
                                'Bearer resource_metadata="https://agent.robinhood.com/.well-known/'
                                'oauth-protected-resource"'
                            )
                        },
                    )
                if request.url.path == "/.well-known/oauth-protected-resource":
                    return httpx2.Response(
                        200,
                        json={
                            "resource": oauth_cli.SERVER_URL,
                            "authorization_servers": ["https://auth.example"],
                        },
                    )
                if "oauth-authorization-server" in request.url.path:
                    return httpx2.Response(
                        200,
                        json={
                            "issuer": "https://auth.example",
                            "authorization_endpoint": "https://auth.example/authorize",
                            "token_endpoint": "https://auth.example/token",
                            "registration_endpoint": "https://auth.example/register",
                        },
                    )
                if request.url.path == "/register":
                    registration_calls.append(request)
                    return httpx2.Response(400, content=secret.encode())
                return httpx2.Response(404)

            async with httpx2.AsyncClient(
                auth=provider,
                transport=httpx2.MockTransport(handler),
            ) as client:
                await client.post(oauth_cli.SERVER_URL)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = oauth_cli.main(argv=["bootstrap"], command_runner=failed_registration)

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["outcome"], "oauth_client_registration_failed")
        self.assertEqual(len(registration_calls), 1)
        self.assertEqual(browser_calls, [])
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_main_emits_one_sanitized_json_line(self):
        secret = "secret-must-not-leak"

        async def successful(_command):
            return {
                "authentication": "demonstrated",
                "headless_authentication_proven": True,
                "outcome": "headless_oauth_tool_discovery",
                "protocol_version": "2025-11-25",
                "server": "robinhood_trading",
                "tool_count": 2,
            }

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = oauth_cli.main(argv=["probe"], command_runner=successful)

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue())["outcome"], "headless_oauth_tool_discovery")
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_main_classifies_failures_without_exception_text(self):
        secret = "secret-refresh-token"

        async def failed(_command):
            raise RuntimeError(secret)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = oauth_cli.main(argv=["probe"], command_runner=failed)

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["outcome"], "oauth_probe_failed")
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
