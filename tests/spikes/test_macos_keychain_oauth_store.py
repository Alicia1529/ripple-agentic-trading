import asyncio
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

from mcp.shared.auth import OAuthClientInformationFull, OAuthMetadata, OAuthToken


STORE_PATH = Path(__file__).resolve().parents[2] / "spikes" / "macos_keychain_oauth_store.py"
sys.path.insert(0, str(STORE_PATH.parent))
STORE_SPEC = importlib.util.spec_from_file_location("ripple_macos_keychain_oauth_store", STORE_PATH)
store_module = importlib.util.module_from_spec(STORE_SPEC)
STORE_SPEC.loader.exec_module(store_module)


class MemorySecretBackend:
    def __init__(self):
        self.values = {}

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, password):
        self.values[(service, account)] = password

    def delete_password(self, service, account):
        del self.values[(service, account)]


class FailingSecretBackend(MemorySecretBackend):
    def get_password(self, service, account):
        raise RuntimeError("backend leaked secret-access-token")


def oauth_state(access_token="access-token"):
    return store_module.OAuthState(
        server_url="https://agent.robinhood.com/mcp/trading",
        resource_url="https://agent.robinhood.com/mcp/trading",
        issuer="https://auth.example",
        access_token_expires_at=1234.5,
        tokens=OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh-token",
            scope="mcp:tools",
        ),
        client_info=OAuthClientInformationFull(
            client_id="client-id",
            client_secret="client-secret",
            grant_types=["authorization_code", "refresh_token"],
            issuer="https://auth.example",
        ),
        oauth_metadata=OAuthMetadata(
            issuer="https://auth.example",
            authorization_endpoint="https://auth.example/authorize",
            token_endpoint="https://auth.example/token",
            registration_endpoint="https://auth.example/register",
        ),
    )


class MacOSKeychainOAuthStateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        home_patch = patch.object(store_module, "_user_home", return_value=Path(self.temp_dir.name))
        home_patch.start()
        self.addCleanup(home_patch.stop)
        self.backend = MemorySecretBackend()
        self.store = store_module.MacOSKeychainOAuthStateStore(
            backend=self.backend,
        )
        self.lock_path = self.store._lock_path

    def test_lock_identity_is_determined_by_keychain_identity(self):
        same_identity = store_module.MacOSKeychainOAuthStateStore(backend=self.backend)
        another_account = store_module.MacOSKeychainOAuthStateStore(
            backend=self.backend,
            account="another-local-runner",
        )

        self.assertEqual(self.store._lock_path, same_identity._lock_path)
        self.assertNotEqual(self.store._lock_path, another_account._lock_path)
        with self.assertRaises(TypeError):
            store_module.MacOSKeychainOAuthStateStore(
                backend=self.backend,
                lock_path=Path(self.temp_dir.name) / "other.lock",
            )

    def test_round_trip_keeps_secret_state_in_keychain_backend(self):
        revision = asyncio.run(self.store.compare_and_swap(None, oauth_state()))
        loaded = asyncio.run(self.store.load())

        self.assertEqual(revision, "1")
        self.assertEqual(loaded.revision, "1")
        self.assertEqual(loaded.state.tokens.access_token, "access-token")
        self.assertEqual(loaded.state.client_info.client_secret, "client-secret")
        self.assertNotIn("access-token", repr(loaded))
        self.assertNotIn("client-secret", repr(loaded))
        self.assertFalse(self.lock_path.read_text())

    def test_compare_and_swap_rejects_stale_writer_without_overwrite(self):
        first_revision = asyncio.run(self.store.compare_and_swap(None, oauth_state("first")))
        second_store = store_module.MacOSKeychainOAuthStateStore(
            backend=self.backend,
        )
        second_revision = asyncio.run(
            second_store.compare_and_swap(first_revision, oauth_state("second"))
        )

        with self.assertRaises(store_module.OAuthStateConflict):
            asyncio.run(self.store.compare_and_swap(first_revision, oauth_state("stale")))

        loaded = asyncio.run(self.store.load())
        self.assertEqual(second_revision, "2")
        self.assertEqual(loaded.state.tokens.access_token, "second")

    def test_clear_requires_current_revision(self):
        revision = asyncio.run(self.store.compare_and_swap(None, oauth_state()))

        with self.assertRaises(store_module.OAuthStateConflict):
            asyncio.run(self.store.clear("0"))
        self.assertIsNotNone(asyncio.run(self.store.load()))

        asyncio.run(self.store.clear(revision))
        self.assertIsNone(asyncio.run(self.store.load()))

    def test_malformed_keychain_record_fails_closed_without_leaking_payload(self):
        secret = "malformed-secret-access-token"
        self.backend.set_password(
            store_module.KEYCHAIN_SERVICE,
            store_module.KEYCHAIN_ACCOUNT,
            json.dumps({"format": 999, "secret": secret}),
        )

        with self.assertRaises(store_module.OAuthStateStoreCorrupt) as raised:
            asyncio.run(self.store.load())

        self.assertNotIn(secret, str(raised.exception))

    def test_backend_failures_are_sanitized(self):
        failing_store = store_module.MacOSKeychainOAuthStateStore(
            backend=FailingSecretBackend(),
        )

        with self.assertRaises(store_module.OAuthStateStoreUnavailable) as raised:
            asyncio.run(failing_store.load())

        self.assertNotIn("secret-access-token", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
