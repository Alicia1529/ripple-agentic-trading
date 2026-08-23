"""Restart-safe OAuth adapter for short-lived MCP feasibility runners."""

import json
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from importlib.metadata import version
from typing import Protocol
from urllib.parse import urlparse

import httpx2
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthMetadata,
    OAuthToken,
    ProtectedResourceMetadata,
)


SUPPORTED_MCP_VERSION = "2.0.0"


class OAuthBootstrapRequired(Exception):
    """The headless runner cannot continue without interactive bootstrap."""


class UnsupportedMcpVersion(Exception):
    """The adapter has not been verified against the installed MCP SDK."""


class OAuthRefreshUnavailable(Exception):
    """Refresh failed without proving that the stored credential is invalid."""


@dataclass(frozen=True)
class OAuthState:
    server_url: str
    resource_url: str
    issuer: str
    access_token_expires_at: float | None
    tokens: OAuthToken = field(repr=False)
    client_info: OAuthClientInformationFull = field(repr=False)
    oauth_metadata: OAuthMetadata = field(repr=False)


@dataclass(frozen=True)
class VersionedOAuthState:
    revision: str
    state: OAuthState


class OAuthStateStore(Protocol):
    async def load(self) -> VersionedOAuthState | None:
        ...

    async def compare_and_swap(self, expected_revision: str | None, state: OAuthState) -> str:
        ...

    async def clear(self, expected_revision: str) -> None:
        ...


class _BufferedTokenStorage:
    def __init__(self) -> None:
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info


def _require_https_url(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise OAuthBootstrapRequired("Stored OAuth metadata contains an unsafe URL")


def validate_oauth_state(state: OAuthState, configured_server_url: str) -> None:
    """Validate stored models and their server/resource/issuer bindings."""
    if not isinstance(state.tokens, OAuthToken):
        raise OAuthBootstrapRequired("Stored OAuth token model is invalid")
    if not isinstance(state.client_info, OAuthClientInformationFull):
        raise OAuthBootstrapRequired("Stored OAuth client model is invalid")
    if not isinstance(state.oauth_metadata, OAuthMetadata):
        raise OAuthBootstrapRequired("Stored OAuth metadata model is invalid")
    if state.server_url != configured_server_url or state.resource_url != configured_server_url:
        raise OAuthBootstrapRequired("OAuth resource binding does not match the configured server")
    if str(state.oauth_metadata.issuer).rstrip("/") != state.issuer.rstrip("/"):
        raise OAuthBootstrapRequired("OAuth issuer binding does not match stored metadata")
    if state.client_info.issuer and state.client_info.issuer.rstrip("/") != state.issuer.rstrip("/"):
        raise OAuthBootstrapRequired("OAuth client registration is bound to another issuer")
    if not state.tokens.refresh_token:
        raise OAuthBootstrapRequired("OAuth refresh token is missing")
    _require_https_url(state.issuer)
    _require_https_url(str(state.oauth_metadata.authorization_endpoint))
    _require_https_url(str(state.oauth_metadata.token_endpoint))
    if state.oauth_metadata.registration_endpoint is not None:
        _require_https_url(str(state.oauth_metadata.registration_endpoint))


class RestartSafeOAuthClientProvider(OAuthClientProvider):
    """OAuth provider that persists the SDK state omitted across process restarts."""

    def __init__(
        self,
        server_url: str,
        client_metadata: OAuthClientMetadata,
        state_store: OAuthStateStore,
        *,
        interactive: bool,
        redirect_handler: Callable[[str], Awaitable[None]] | None = None,
        callback_handler: Callable[[], Awaitable[AuthorizationCodeResult]] | None = None,
    ) -> None:
        installed_version = version("mcp")
        if installed_version != SUPPORTED_MCP_VERSION:
            raise UnsupportedMcpVersion(
                f"mcp {installed_version} is unsupported; expected {SUPPORTED_MCP_VERSION}"
            )
        self._state_store = state_store
        self._state_revision: str | None = None
        self._interactive = interactive
        self._buffer = _BufferedTokenStorage()
        super().__init__(
            server_url,
            client_metadata,
            self._buffer,
            redirect_handler=redirect_handler,
            callback_handler=callback_handler,
        )

    async def _initialize(self) -> None:
        stored = await self._state_store.load()
        if stored is None:
            if not self._interactive:
                raise OAuthBootstrapRequired("OAuth state is missing")
            self._initialized = True
            return

        try:
            self._restore(stored)
        except OAuthBootstrapRequired:
            if not self._interactive:
                raise
            await self._state_store.clear(stored.revision)
            self._state_revision = None
        self._initialized = True

    def _restore(self, stored: VersionedOAuthState) -> None:
        state = stored.state
        self._validate_state(state)
        self._state_revision = stored.revision
        self._buffer.tokens = state.tokens
        self._buffer.client_info = state.client_info
        self.context.current_tokens = state.tokens
        self.context.client_info = state.client_info
        self.context.oauth_metadata = state.oauth_metadata
        self.context.auth_server_url = state.issuer
        self.context.protected_resource_metadata = ProtectedResourceMetadata(
            resource=state.resource_url,
            authorization_servers=[state.issuer],
        )
        self.context.token_expiry_time = (
            state.access_token_expires_at
            if state.access_token_expires_at is not None
            else 1.0
        )

    def _validate_state(self, state: OAuthState) -> None:
        validate_oauth_state(state, self.context.server_url)

    def _capture(self) -> OAuthState:
        context = self.context
        if (
            context.current_tokens is None
            or context.client_info is None
            or context.oauth_metadata is None
            or context.protected_resource_metadata is None
            or not context.auth_server_url
        ):
            raise OAuthBootstrapRequired("OAuth state is incomplete")
        state = OAuthState(
            server_url=context.server_url,
            resource_url=str(context.protected_resource_metadata.resource),
            issuer=context.auth_server_url,
            access_token_expires_at=context.token_expiry_time,
            tokens=context.current_tokens,
            client_info=context.client_info,
            oauth_metadata=context.oauth_metadata,
        )
        self._validate_state(state)
        return state

    async def _persist(self) -> None:
        self._state_revision = await self._state_store.compare_and_swap(
            self._state_revision,
            self._capture(),
        )

    async def _handle_token_response(self, response: httpx2.Response) -> None:
        if response.status_code not in (200, 201):
            await response.aread()
            raise OAuthBootstrapRequired(
                f"OAuth token exchange failed with status {response.status_code}"
            )
        try:
            await super()._handle_token_response(response)
        except Exception:
            raise OAuthBootstrapRequired("OAuth token exchange returned an invalid response") from None
        await self._persist()

    async def _handle_refresh_response(self, response: httpx2.Response) -> bool:
        if response.status_code != 200:
            body = await response.aread()
            try:
                payload = json.loads(body)
                error = payload.get("error") if isinstance(payload, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                error = None

            if error in ("invalid_client", "invalid_grant"):
                if self._state_revision is not None:
                    await self._state_store.clear(self._state_revision)
                    self._state_revision = None
                self.context.clear_tokens()
                self._buffer.tokens = None
                if error == "invalid_client":
                    self.context.client_info = None
                    self._buffer.client_info = None
                if self._interactive:
                    return False
                raise OAuthBootstrapRequired("OAuth refresh credential was rejected")
            raise OAuthRefreshUnavailable(
                f"OAuth refresh failed with status {response.status_code}"
            )

        body = await response.aread()
        try:
            refreshed_tokens = OAuthToken.model_validate_json(body)
        except Exception:
            raise OAuthRefreshUnavailable("OAuth refresh returned an invalid response") from None

        prior_tokens = self.context.current_tokens
        if refreshed_tokens.scope is None and prior_tokens is not None:
            refreshed_tokens.scope = prior_tokens.scope
        if refreshed_tokens.refresh_token is None and prior_tokens is not None:
            refreshed_tokens.refresh_token = prior_tokens.refresh_token
        self.context.current_tokens = refreshed_tokens
        self.context.update_token_expiry(refreshed_tokens)
        await self._buffer.set_tokens(refreshed_tokens)
        await self._persist()
        return True

    async def async_auth_flow(
        self,
        request: httpx2.Request,
    ) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        if self._interactive:
            flow = super().async_auth_flow(request)
            try:
                next_request = await anext(flow)
                while True:
                    response = yield next_request
                    next_request = await flow.asend(response)
            except StopAsyncIteration:
                pass
            return

        async with self.context.lock:
            if not self._initialized:
                await self._initialize()
            self.context.protocol_version = request.headers.get("MCP-Protocol-Version")
            if not self.context.is_token_valid():
                if not self.context.can_refresh_token():
                    raise OAuthBootstrapRequired("OAuth token cannot be refreshed")
                refresh_response = yield await self._refresh_token()
                await self._handle_refresh_response(refresh_response)

            self._add_auth_header(request)
            response = yield request
            if response.status_code in (401, 403):
                raise OAuthBootstrapRequired("OAuth authorization is no longer sufficient")
