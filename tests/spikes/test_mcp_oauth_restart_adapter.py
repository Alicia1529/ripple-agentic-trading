import asyncio
import importlib.util
import logging
import time
import unittest
from pathlib import Path

import httpx2
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthMetadata,
    OAuthToken,
    ProtectedResourceMetadata,
)


ADAPTER_PATH = Path(__file__).resolve().parents[2] / "spikes" / "mcp_oauth_restart_adapter.py"
ADAPTER_SPEC = importlib.util.spec_from_file_location("ripple_mcp_oauth_restart_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(ADAPTER_SPEC)
ADAPTER_SPEC.loader.exec_module(adapter)

SERVER_URL = "https://agent.robinhood.com/mcp/trading"
ISSUER = "https://auth.example"


class MemoryStateStore:
    def __init__(self, versioned_state=None):
        self.versioned_state = versioned_state
        self.saved = []
        self.cleared = []
        self.reject_swap = False

    async def load(self):
        return self.versioned_state

    async def compare_and_swap(self, expected_revision, state):
        if self.reject_swap:
            raise RuntimeError("stale OAuth state")
        revision = str(len(self.saved) + 2)
        self.saved.append((expected_revision, state))
        self.versioned_state = adapter.VersionedOAuthState(revision, state)
        return revision

    async def clear(self, expected_revision):
        self.cleared.append(expected_revision)
        self.versioned_state = None


def stored_state(
    *,
    expires_at,
    refresh_token="refresh-old",
    server_url=SERVER_URL,
    issuer=ISSUER,
    token_endpoint=ISSUER + "/token",
):
    state = adapter.OAuthState(
        server_url=server_url,
        resource_url=server_url,
        issuer=issuer,
        access_token_expires_at=expires_at,
        tokens=OAuthToken(
            access_token="access-old",
            expires_in=3600,
            refresh_token=refresh_token,
        ),
        client_info=OAuthClientInformationFull(
            client_id="client-id",
            grant_types=["authorization_code", "refresh_token"],
            issuer=issuer,
        ),
        oauth_metadata=OAuthMetadata(
            issuer=issuer,
            authorization_endpoint=issuer + "/authorize",
            token_endpoint=token_endpoint,
        ),
    )
    return adapter.VersionedOAuthState("1", state)


def provider(store):
    return adapter.RestartSafeOAuthClientProvider(
        SERVER_URL,
        OAuthClientMetadata(
            client_name="Ripple feasibility probe",
            redirect_uris=["http://127.0.0.1:8765/callback"],
        ),
        store,
        interactive=False,
    )


def bootstrap_provider(store):
    instance = adapter.RestartSafeOAuthClientProvider(
        SERVER_URL,
        OAuthClientMetadata(
            client_name="Ripple feasibility probe",
            redirect_uris=["http://127.0.0.1:8765/callback"],
        ),
        store,
        interactive=True,
    )
    instance.context.client_info = stored_state(expires_at=None).state.client_info
    instance.context.oauth_metadata = stored_state(expires_at=None).state.oauth_metadata
    instance.context.auth_server_url = ISSUER
    instance.context.protected_resource_metadata = ProtectedResourceMetadata(
        resource=SERVER_URL,
        authorization_servers=[ISSUER],
    )
    return instance


async def request_with(provider_instance, handler):
    async with httpx2.AsyncClient(
        auth=provider_instance,
        transport=httpx2.MockTransport(handler),
    ) as client:
        return await client.post(SERVER_URL, headers={"MCP-Protocol-Version": "2025-11-25"})


class RestartSafeOAuthClientProviderTests(unittest.TestCase):
    def test_bootstrap_token_exchange_atomically_persists_complete_state(self):
        store = MemoryStateStore()
        instance = bootstrap_provider(store)
        response = httpx2.Response(
            200,
            json={
                "access_token": "access-new",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "refresh-new",
            },
        )

        asyncio.run(instance._handle_token_response(response))

        self.assertEqual(store.saved[0][0], None)
        self.assertEqual(store.saved[0][1].tokens.access_token, "access-new")
        self.assertEqual(store.saved[0][1].client_info.client_id, "client-id")
        self.assertGreater(store.saved[0][1].access_token_expires_at, time.time())

    def test_bootstrap_without_refresh_token_is_not_persisted(self):
        store = MemoryStateStore()
        instance = bootstrap_provider(store)
        response = httpx2.Response(
            200,
            json={"access_token": "access-new", "token_type": "Bearer", "expires_in": 3600},
        )

        with self.assertRaises(adapter.OAuthBootstrapRequired):
            asyncio.run(instance._handle_token_response(response))

        self.assertEqual(store.saved, [])

    def test_token_exchange_failures_do_not_expose_response_body(self):
        secret = "authorization-code-or-secret"
        responses = [
            httpx2.Response(400, content=("failure " + secret).encode()),
            httpx2.Response(200, json={"error_description": secret}),
        ]
        for response in responses:
            with self.subTest(status=response.status_code):
                instance = bootstrap_provider(MemoryStateStore())
                with self.assertLogs("mcp.client.auth.oauth2", level="ERROR") as captured:
                    try:
                        asyncio.run(instance._handle_token_response(response))
                    except adapter.OAuthBootstrapRequired as raised:
                        caught = raised
                        logging.getLogger("mcp.client.auth.oauth2").exception("OAuth flow error")
                    else:
                        self.fail("expected OAuthBootstrapRequired")

                self.assertNotIn(secret, str(caught))
                self.assertNotIn(secret, "\n".join(captured.output))

    def test_malformed_successful_refresh_does_not_log_or_clear_state(self):
        secret = "refresh-secret-must-not-leak"
        store = MemoryStateStore(stored_state(expires_at=time.time() - 1))

        async def handler(_request):
            return httpx2.Response(200, json={"error_description": secret})

        with self.assertNoLogs("mcp.client.auth.oauth2", level="ERROR"):
            with self.assertRaises(adapter.OAuthRefreshUnavailable) as raised:
                asyncio.run(request_with(provider(store), handler))

        self.assertNotIn(secret, str(raised.exception))
        self.assertEqual(store.cleared, [])
        self.assertIsNotNone(store.versioned_state)

    def test_interactive_bootstrap_clears_invalid_state_with_revision(self):
        store = MemoryStateStore(
            stored_state(expires_at=time.time() + 60, server_url="https://wrong.example/mcp")
        )
        instance = adapter.RestartSafeOAuthClientProvider(
            SERVER_URL,
            OAuthClientMetadata(
                client_name="Ripple feasibility probe",
                redirect_uris=["http://127.0.0.1:8765/callback"],
            ),
            store,
            interactive=True,
        )

        asyncio.run(instance._initialize())

        self.assertEqual(store.cleared, ["1"])
        self.assertTrue(instance._initialized)

    def test_fresh_process_restores_unexpired_token_without_refresh(self):
        store = MemoryStateStore(stored_state(expires_at=time.time() + 3600))
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx2.Response(200)

        response = asyncio.run(request_with(provider(store), handler))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([call.url.host for call in calls], ["agent.robinhood.com"])
        self.assertEqual(calls[0].headers["authorization"], "Bearer access-old")
        self.assertEqual(store.saved, [])
        self.assertNotIn("access-old", repr(store.versioned_state))
        self.assertNotIn("client-id", repr(store.versioned_state))

    def test_expired_token_refreshes_then_atomically_replaces_state(self):
        store = MemoryStateStore(stored_state(expires_at=time.time() - 1))
        calls = []

        async def handler(request):
            calls.append(request)
            if request.url.host == "auth.example":
                return httpx2.Response(
                    200,
                    json={
                        "access_token": "access-new",
                        "token_type": "Bearer",
                        "expires_in": 7200,
                        "refresh_token": "refresh-new",
                    },
                )
            self.assertEqual(request.headers["authorization"], "Bearer access-new")
            return httpx2.Response(200)

        response = asyncio.run(request_with(provider(store), handler))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([call.url.host for call in calls], ["auth.example", "agent.robinhood.com"])
        self.assertEqual(store.saved[0][0], "1")
        self.assertEqual(store.saved[0][1].tokens.refresh_token, "refresh-new")
        self.assertGreater(store.saved[0][1].access_token_expires_at, time.time())

    def test_unknown_expiry_refreshes_before_sending_access_token(self):
        store = MemoryStateStore(stored_state(expires_at=None))
        calls = []

        async def handler(request):
            calls.append(request)
            if request.url.host == "auth.example":
                return httpx2.Response(
                    200,
                    json={"access_token": "access-new", "token_type": "Bearer", "expires_in": 60},
                )
            return httpx2.Response(200)

        asyncio.run(request_with(provider(store), handler))

        self.assertEqual([call.url.host for call in calls], ["auth.example", "agent.robinhood.com"])
        self.assertEqual(store.saved[0][1].tokens.refresh_token, "refresh-old")

    def test_invalid_grant_clears_state_without_calling_resource(self):
        store = MemoryStateStore(stored_state(expires_at=time.time() - 1))
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx2.Response(
                400,
                json={"error": "invalid_grant", "error_description": "secret-must-be-ignored"},
            )

        with self.assertRaises(adapter.OAuthBootstrapRequired):
            asyncio.run(request_with(provider(store), handler))

        self.assertEqual([call.url.host for call in calls], ["auth.example"])
        self.assertEqual(store.cleared, ["1"])

    def test_transient_and_ambiguous_refresh_errors_preserve_state(self):
        cases = [
            (429, {"error": "temporarily_unavailable"}),
            (400, {"error": "temporarily_unavailable"}),
            (408, None),
            (503, None),
            (400, "malformed"),
        ]
        for status, payload in cases:
            with self.subTest(status=status, payload=payload):
                store = MemoryStateStore(stored_state(expires_at=time.time() - 1))

                async def handler(_request, status=status, payload=payload):
                    if payload == "malformed":
                        return httpx2.Response(status, content=b"{")
                    if payload is not None:
                        return httpx2.Response(status, json=payload)
                    return httpx2.Response(status)

                with self.assertRaises(adapter.OAuthRefreshUnavailable):
                    asyncio.run(request_with(provider(store), handler))

                self.assertEqual(store.cleared, [])
                self.assertIsNotNone(store.versioned_state)

    def test_missing_or_mismatched_state_fails_before_network(self):
        cases = [
            MemoryStateStore(),
            MemoryStateStore(stored_state(expires_at=time.time() + 60, server_url="https://wrong.example/mcp")),
            MemoryStateStore(stored_state(expires_at=time.time() + 60, refresh_token=None)),
            MemoryStateStore(stored_state(expires_at=time.time() + 60, token_endpoint="http://auth.example/token")),
            MemoryStateStore(stored_state(expires_at=time.time() + 60, issuer="https://user@auth.example")),
        ]
        for store in cases:
            with self.subTest(store=store):
                calls = []

                async def handler(request):
                    calls.append(request)
                    return httpx2.Response(200)

                with self.assertRaises(adapter.OAuthBootstrapRequired):
                    asyncio.run(request_with(provider(store), handler))
                self.assertEqual(calls, [])

    def test_stale_state_write_aborts_before_resource_request(self):
        store = MemoryStateStore(stored_state(expires_at=time.time() - 1))
        store.reject_swap = True
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx2.Response(
                200,
                json={"access_token": "access-new", "token_type": "Bearer", "expires_in": 60},
            )

        with self.assertRaises(RuntimeError):
            asyncio.run(request_with(provider(store), handler))

        self.assertEqual([call.url.host for call in calls], ["auth.example"])

    def test_server_rejection_never_starts_interactive_authorization(self):
        store = MemoryStateStore(stored_state(expires_at=time.time() + 3600))
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx2.Response(401)

        with self.assertRaises(adapter.OAuthBootstrapRequired):
            asyncio.run(request_with(provider(store), handler))

        self.assertEqual([call.url.host for call in calls], ["agent.robinhood.com"])


if __name__ == "__main__":
    unittest.main()
