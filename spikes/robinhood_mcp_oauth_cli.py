#!/usr/bin/env python3
"""Bootstrap and verify restart-safe Robinhood MCP OAuth without tool calls."""

import asyncio
import json
import logging
import math
import secrets
import sys
import webbrowser
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any, AsyncContextManager, Callable, Mapping, Protocol
from urllib.parse import parse_qsl, urlsplit

import httpx2
from mcp import ClientSession
from mcp.client.auth import OAuthRegistrationError
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata

from macos_keychain_oauth_store import (
    MacOSKeychainOAuthStateStore,
    OAuthStateConflict,
)
from mcp_oauth_restart_adapter import (
    OAuthBootstrapRequired,
    OAuthState,
    OAuthRefreshUnavailable,
    RestartSafeOAuthClientProvider,
    VersionedOAuthState,
    validate_oauth_state,
)


SERVER_NAME = "robinhood_trading"
SERVER_URL = "https://agent.robinhood.com/mcp/trading"
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 8765
CALLBACK_PATH = "/callback"
CALLBACK_TIMEOUT_SECONDS = 300
MCP_READ_TIMEOUT_SECONDS = CALLBACK_TIMEOUT_SECONDS + 30
MAX_REQUEST_BYTES = 8192


class OAuthCallbackError(Exception):
    """The local authorization callback was absent or invalid."""


class ProbeSession(Protocol):
    async def initialize(self) -> Any:
        ...

    async def list_tools(self) -> Any:
        ...


SessionFactory = Callable[[Any], AsyncContextManager[ProbeSession]]


def _single_parameter(pairs: list[tuple[str, str]], name: str, *, required: bool) -> str | None:
    values = [value for key, value in pairs if key == name]
    if len(values) > 1 or (required and len(values) != 1):
        raise OAuthCallbackError("OAuth callback parameters are invalid")
    if not values:
        return None
    value = values[0]
    if not value or len(value) > 4096:
        raise OAuthCallbackError("OAuth callback parameters are invalid")
    return value


def _require_https(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise OAuthCallbackError("OAuth URL is unsafe")


class LoopbackOAuthCallback:
    """Single-use loopback receiver opened before browser authorization begins."""

    def __init__(
        self,
        *,
        host: str = CALLBACK_HOST,
        port: int = CALLBACK_PORT,
        path: str = CALLBACK_PATH,
        timeout_seconds: float = CALLBACK_TIMEOUT_SECONDS,
        open_browser: Callable[[str], bool] | None = None,
    ) -> None:
        if host != CALLBACK_HOST or not path.startswith("/") or "?" in path or "#" in path:
            raise ValueError("Loopback callback configuration is invalid")
        self._host = host
        self._port = port
        self._path = path
        self._timeout_seconds = timeout_seconds
        self._open_browser = open_browser if open_browser is not None else lambda url: webbrowser.open(url, new=2)
        self._server: asyncio.Server | None = None
        self._result: asyncio.Future[AuthorizationCodeResult] | None = None
        self._expected_state: str | None = None
        self.bound_port: int | None = None

    @property
    def redirect_uri(self) -> str:
        return f"http://{self._host}:{self._port}{self._path}"

    async def redirect_handler(self, authorization_url: str) -> None:
        if self._server is not None:
            raise OAuthCallbackError("OAuth callback is already active")
        _require_https(authorization_url)
        auth_pairs = parse_qsl(urlsplit(authorization_url).query, keep_blank_values=True)
        self._expected_state = _single_parameter(auth_pairs, "state", required=True)
        self._result = asyncio.get_running_loop().create_future()
        try:
            self._server = await asyncio.start_server(
                self._handle_connection,
                self._host,
                self._port,
                limit=MAX_REQUEST_BYTES,
            )
            socket = self._server.sockets[0]
            self.bound_port = socket.getsockname()[1]
        except OAuthCallbackError:
            await self._close()
            raise
        except Exception:
            await self._close()
            raise OAuthCallbackError("Could not start the OAuth callback") from None
        try:
            await asyncio.to_thread(self._open_browser, authorization_url)
        except Exception:
            pass

    async def callback_handler(self) -> AuthorizationCodeResult:
        if self._server is None or self._result is None:
            raise OAuthCallbackError("OAuth callback is not active")
        try:
            return await asyncio.wait_for(self._result, timeout=self._timeout_seconds)
        except TimeoutError:
            raise OAuthCallbackError("OAuth callback timed out") from None
        finally:
            await self._close()

    async def _close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def _parse_target(self, target: str) -> AuthorizationCodeResult:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or parsed.fragment or parsed.path != self._path:
            raise OAuthCallbackError("OAuth callback path is invalid")
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        if any(name == "error" for name, _value in pairs):
            raise OAuthCallbackError("OAuth authorization was not completed")
        code = _single_parameter(pairs, "code", required=True)
        state = _single_parameter(pairs, "state", required=True)
        issuer = _single_parameter(pairs, "iss", required=False)
        if self._expected_state is None or not secrets.compare_digest(state, self._expected_state):
            raise OAuthCallbackError("OAuth callback state does not match")
        if issuer is not None:
            _require_https(issuer)
        return AuthorizationCodeResult(code=code, state=state, iss=issuer)

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        status = "400 Bad Request"
        body = b"Authorization failed. You may close this window."
        try:
            request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
            if len(request) > MAX_REQUEST_BYTES:
                raise OAuthCallbackError("OAuth callback request is too large")
            first_line = request.split(b"\r\n", 1)[0].decode("ascii")
            method, target, version = first_line.split(" ")
            if method != "GET" or version not in ("HTTP/1.0", "HTTP/1.1"):
                raise OAuthCallbackError("OAuth callback request is invalid")
            result = self._parse_target(target)
            if self._result is None or self._result.done():
                raise OAuthCallbackError("OAuth callback was already received")
            self._result.set_result(result)
            status = "200 OK"
            body = b"Authorization complete. You may close this window."
        except Exception:
            if self._result is not None and not self._result.done():
                self._result.set_exception(OAuthCallbackError("OAuth callback was invalid"))
        response = (
            f"HTTP/1.1 {status}\r\nContent-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
        ).encode("ascii") + body
        writer.write(response)
        try:
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()


def build_provider(command: str, state_store: Any, callback: LoopbackOAuthCallback) -> RestartSafeOAuthClientProvider:
    if command not in ("bootstrap", "probe", "refresh-proof"):
        raise ValueError("Unknown OAuth command")
    interactive = command == "bootstrap"
    return RestartSafeOAuthClientProvider(
        SERVER_URL,
        OAuthClientMetadata(
            client_name="Ripple Robinhood MCP feasibility probe",
            redirect_uris=[callback.redirect_uri],
        ),
        state_store,
        interactive=interactive,
        redirect_handler=callback.redirect_handler if interactive else None,
        callback_handler=callback.callback_handler if interactive else None,
    )


@asynccontextmanager
async def mcp_session(provider: RestartSafeOAuthClientProvider):
    async with httpx2.AsyncClient(auth=provider, follow_redirects=False, timeout=30) as client:
        async with streamable_http_client(
            SERVER_URL,
            http_client=client,
            terminate_on_close=False,
        ) as streams:
            async with ClientSession(
                *streams,
                read_timeout_seconds=MCP_READ_TIMEOUT_SECONDS,
            ) as session:
                yield session


def _field(value: Any, name: str) -> Any:
    camel_name = "protocolVersion" if name == "protocol_version" else name
    for candidate in (name, camel_name):
        if isinstance(value, Mapping) and candidate in value:
            return value[candidate]
        if hasattr(value, candidate):
            return getattr(value, candidate)
    raise ValueError("MCP response is malformed")


async def run_oauth_probe(command: str, provider: Any, session_factory: SessionFactory = mcp_session) -> Mapping[str, Any]:
    async with session_factory(provider) as session:
        initialized = await session.initialize()
        protocol_version = _field(initialized, "protocol_version")
        listed = await session.list_tools()
        tools = _field(listed, "tools")
    if not isinstance(protocol_version, str) or not protocol_version or not isinstance(tools, list):
        raise ValueError("MCP response is malformed")
    return {
        "authentication": "demonstrated",
        "headless_authentication_proven": command == "probe",
        "outcome": (
            "headless_oauth_tool_discovery"
            if command == "probe"
            else "interactive_oauth_bootstrap_completed"
        ),
        "protocol_version": protocol_version,
        "server": SERVER_NAME,
        "tool_count": len(tools),
    }


def _stored_state_evidence(stored: VersionedOAuthState | None) -> Mapping[str, bool]:
    if stored is None:
        raise OAuthBootstrapRequired("OAuth state is missing")
    validate_oauth_state(stored.state, SERVER_URL)
    expiry = stored.state.access_token_expires_at
    if (
        expiry is None
        or isinstance(expiry, bool)
        or not isinstance(expiry, (int, float))
        or not math.isfinite(expiry)
    ):
        raise OAuthBootstrapRequired("OAuth absolute expiry is invalid")
    return {
        "stored_absolute_expiry_finite": True,
        "stored_metadata_binding_valid": True,
        "stored_state_model_types_valid": True,
    }


async def run_refresh_proof(
    store: Any,
    session_factory: SessionFactory = mcp_session,
) -> Mapping[str, Any]:
    before = await store.load()
    _stored_state_evidence(before)
    stale_state = replace(before.state, access_token_expires_at=1.0)
    stale_revision = await store.compare_and_swap(before.revision, stale_state)
    marked = await store.load()
    if (
        marked is None
        or marked.revision != stale_revision
        or marked.state != stale_state
        or replace(marked.state, access_token_expires_at=before.state.access_token_expires_at)
        != before.state
    ):
        raise OAuthStateConflict("OAuth expiry marker changed concurrently")

    callback = LoopbackOAuthCallback()
    provider = build_provider("refresh-proof", store, callback)
    probe = await run_oauth_probe("probe", provider, session_factory)
    after = await store.load()
    evidence = _stored_state_evidence(after)
    try:
        replacements = int(after.revision) - int(stale_revision)
    except (TypeError, ValueError):
        raise OAuthStateConflict("OAuth state revision is invalid") from None
    if replacements != 1:
        raise OAuthStateConflict("OAuth refresh did not replace state exactly once")
    return {
        **probe,
        **evidence,
        "expiry_stale_writes": 1,
        "outcome": "headless_oauth_refresh_validated",
        "refresh_state_replacements": replacements,
    }


async def run_command(
    command: str,
    *,
    store: Any | None = None,
    callback: LoopbackOAuthCallback | None = None,
    session_factory: SessionFactory = mcp_session,
) -> Mapping[str, Any]:
    callback = callback if callback is not None else LoopbackOAuthCallback()
    store = store if store is not None else MacOSKeychainOAuthStateStore()
    if command == "refresh-proof":
        return await run_refresh_proof(store, session_factory)
    provider = build_provider(command, store, callback)
    result = await run_oauth_probe(command, provider, session_factory)
    if command == "bootstrap":
        return {**result, **_stored_state_evidence(await store.load())}
    return result


def _contains_exception(exc: BaseException, kind: type[BaseException]) -> bool:
    if isinstance(exc, kind):
        return True
    return any(_contains_exception(nested, kind) for nested in getattr(exc, "exceptions", ()))


def _failure_outcome(exc: BaseException) -> str:
    cases = (
        (OAuthBootstrapRequired, "oauth_bootstrap_required"),
        (OAuthRefreshUnavailable, "oauth_refresh_unavailable"),
        (OAuthStateConflict, "oauth_state_conflict"),
        (OAuthCallbackError, "oauth_callback_failed"),
        (OAuthRegistrationError, "oauth_client_registration_failed"),
    )
    for kind, outcome in cases:
        if _contains_exception(exc, kind):
            return outcome
    return "oauth_probe_failed"


def main(argv=None, command_runner=run_command) -> int:
    logging.disable(logging.CRITICAL)
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1 or arguments[0] not in ("bootstrap", "probe", "refresh-proof"):
        result = {
            "authentication": "not_demonstrated",
            "headless_authentication_proven": False,
            "outcome": "invalid_command",
            "server": SERVER_NAME,
        }
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        return 1
    try:
        result = asyncio.run(command_runner(arguments[0]))
        status = 0
    except Exception as exc:
        result = {
            "authentication": "not_demonstrated",
            "headless_authentication_proven": False,
            "outcome": _failure_outcome(exc),
            "server": SERVER_NAME,
        }
        status = 1
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
