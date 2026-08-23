"""Local macOS Keychain implementation of the restart-safe OAuth state seam."""

import asyncio
import fcntl
import hashlib
import json
import os
import platform
import pwd
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

from mcp.shared.auth import OAuthClientInformationFull, OAuthMetadata, OAuthToken

from mcp_oauth_restart_adapter import OAuthState, VersionedOAuthState


KEYCHAIN_SERVICE = "com.ripple.robinhood-mcp-oauth"
KEYCHAIN_ACCOUNT = "local-feasibility-runner"
RECORD_FORMAT = 1


class OAuthStateConflict(Exception):
    """The stored revision changed before an update completed."""


class OAuthStateStoreCorrupt(Exception):
    """The Keychain record cannot be safely restored."""


class OAuthStateStoreUnavailable(Exception):
    """The system Keychain could not complete an operation."""


class SecretBackend(Protocol):
    def get_password(self, service: str, account: str) -> str | None:
        ...

    def set_password(self, service: str, account: str, password: str) -> None:
        ...

    def delete_password(self, service: str, account: str) -> None:
        ...


class MacOSKeychainBackend:
    """Use keyring's explicit macOS backend, ignoring insecure configured fallbacks."""

    def __init__(self) -> None:
        if platform.system() != "Darwin":
            raise OAuthStateStoreUnavailable("The local OAuth store requires macOS Keychain")
        try:
            from keyring.backends.macOS import Keyring

            self._backend = Keyring()
        except Exception:
            raise OAuthStateStoreUnavailable("macOS Keychain is unavailable") from None

    def get_password(self, service: str, account: str) -> str | None:
        return self._backend.get_password(service, account)

    def set_password(self, service: str, account: str, password: str) -> None:
        self._backend.set_password(service, account, password)

    def delete_password(self, service: str, account: str) -> None:
        self._backend.delete_password(service, account)


def _user_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def _lock_path_for_identity(service: str, account: str) -> Path:
    identity = hashlib.sha256(f"{service}\0{account}".encode()).hexdigest()[:24]
    return _user_home() / "Library" / "Caches" / "ripple" / f"oauth-state-{identity}.lock"


def _state_to_dict(state: OAuthState) -> dict:
    return {
        "server_url": state.server_url,
        "resource_url": state.resource_url,
        "issuer": state.issuer,
        "access_token_expires_at": state.access_token_expires_at,
        "tokens": state.tokens.model_dump(mode="json"),
        "client_info": state.client_info.model_dump(mode="json"),
        "oauth_metadata": state.oauth_metadata.model_dump(mode="json"),
    }


def _state_from_dict(payload: object) -> OAuthState:
    expected = {
        "server_url",
        "resource_url",
        "issuer",
        "access_token_expires_at",
        "tokens",
        "client_info",
        "oauth_metadata",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError
    for name in ("server_url", "resource_url", "issuer"):
        if not isinstance(payload[name], str) or not payload[name]:
            raise ValueError
    expires_at = payload["access_token_expires_at"]
    if expires_at is not None and (isinstance(expires_at, bool) or not isinstance(expires_at, (int, float))):
        raise ValueError
    return OAuthState(
        server_url=payload["server_url"],
        resource_url=payload["resource_url"],
        issuer=payload["issuer"],
        access_token_expires_at=expires_at,
        tokens=OAuthToken.model_validate(payload["tokens"]),
        client_info=OAuthClientInformationFull.model_validate(payload["client_info"]),
        oauth_metadata=OAuthMetadata.model_validate(payload["oauth_metadata"]),
    )


class MacOSKeychainOAuthStateStore:
    """Same-host CAS store with secrets held only by macOS Keychain."""

    def __init__(
        self,
        *,
        backend: SecretBackend | None = None,
        service: str = KEYCHAIN_SERVICE,
        account: str = KEYCHAIN_ACCOUNT,
    ) -> None:
        self._backend = backend if backend is not None else MacOSKeychainBackend()
        self._lock_path = _lock_path_for_identity(service, account)
        self._service = service
        self._account = account

    @contextmanager
    def _locked(self):
        self._lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self._lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _load_unlocked(self) -> VersionedOAuthState | None:
        try:
            encoded = self._backend.get_password(self._service, self._account)
        except Exception:
            raise OAuthStateStoreUnavailable("Could not read OAuth state from macOS Keychain") from None
        if encoded is None:
            return None
        try:
            payload = json.loads(encoded)
            if not isinstance(payload, dict) or set(payload) != {"format", "revision", "state"}:
                raise ValueError
            record_format = payload["format"]
            revision = payload["revision"]
            if record_format != RECORD_FORMAT or isinstance(record_format, bool):
                raise ValueError
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                raise ValueError
            state = _state_from_dict(payload["state"])
        except Exception:
            raise OAuthStateStoreCorrupt("Stored OAuth state is invalid") from None
        return VersionedOAuthState(str(revision), state)

    async def load(self) -> VersionedOAuthState | None:
        return await asyncio.to_thread(self._load_sync)

    def _load_sync(self) -> VersionedOAuthState | None:
        with self._locked():
            return self._load_unlocked()

    async def compare_and_swap(self, expected_revision: str | None, state: OAuthState) -> str:
        return await asyncio.to_thread(self._compare_and_swap_sync, expected_revision, state)

    def _compare_and_swap_sync(self, expected_revision: str | None, state: OAuthState) -> str:
        with self._locked():
            current = self._load_unlocked()
            current_revision = current.revision if current is not None else None
            if current_revision != expected_revision:
                raise OAuthStateConflict("OAuth state changed concurrently")
            next_revision = 1 if current is None else int(current.revision) + 1
            encoded = json.dumps(
                {
                    "format": RECORD_FORMAT,
                    "revision": next_revision,
                    "state": _state_to_dict(state),
                },
                separators=(",", ":"),
                sort_keys=True,
            )
            try:
                self._backend.set_password(self._service, self._account, encoded)
            except Exception:
                raise OAuthStateStoreUnavailable("Could not write OAuth state to macOS Keychain") from None
            return str(next_revision)

    async def clear(self, expected_revision: str) -> None:
        await asyncio.to_thread(self._clear_sync, expected_revision)

    def _clear_sync(self, expected_revision: str) -> None:
        with self._locked():
            current = self._load_unlocked()
            if current is None or current.revision != expected_revision:
                raise OAuthStateConflict("OAuth state changed concurrently")
            try:
                self._backend.delete_password(self._service, self._account)
            except Exception:
                raise OAuthStateStoreUnavailable("Could not clear OAuth state from macOS Keychain") from None
