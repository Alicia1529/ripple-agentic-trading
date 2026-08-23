#!/usr/bin/env python3
"""Read-only Robinhood Trading MCP authentication feasibility probe."""

import asyncio
import json
import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlparse


SERVER_NAME = "robinhood_trading"
EXPECTED_URL = "https://agent.robinhood.com/mcp/trading"
URL_ENV = "ROBINHOOD_MCP_URL"
ACCESS_TOKEN_ENV = "ROBINHOOD_MCP_ACCESS_TOKEN"


class ProbeSession(Protocol):
    status_codes: Sequence[int]

    async def initialize(self) -> Any:
        ...

    async def list_tools(self) -> Any:
        ...


SessionFactory = Callable[["ProbeConfig"], AsyncContextManager[ProbeSession]]


@dataclass(frozen=True)
class ProbeConfig:
    url: str
    access_token: str | None = field(default=None, repr=False)


class MalformedProtocolResponse(Exception):
    pass


class ObservedSession:
    def __init__(self, session: Any, status_codes: Sequence[int], challenges: Sequence[str]):
        self._session = session
        self.status_codes = status_codes
        self.challenges = challenges

    async def initialize(self) -> Any:
        return await self._session.initialize()

    async def list_tools(self) -> Any:
        return await self._session.list_tools()


def _field(value: Any, *names: str) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    raise MalformedProtocolResponse


def _load_config(environ: Mapping[str, str]) -> ProbeConfig:
    url = environ.get(URL_ENV, "").strip()
    if url != EXPECTED_URL:
        raise ValueError
    access_token = environ.get(ACCESS_TOKEN_ENV)
    if access_token is not None and (not access_token or "\r" in access_token or "\n" in access_token):
        raise ValueError
    return ProbeConfig(url=url, access_token=access_token)


def _failure(outcome: str) -> Mapping[str, Any]:
    return {
        "authentication": "not_demonstrated",
        "headless_authentication_proven": False,
        "outcome": outcome,
        "server": SERVER_NAME,
    }


def _https_url(value: Any) -> str:
    if not isinstance(value, str):
        raise MalformedProtocolResponse
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise MalformedProtocolResponse
    return value


def _resource_metadata_url(challenges: Sequence[str]) -> str:
    for challenge in challenges:
        if not isinstance(challenge, str) or not challenge.lower().startswith("bearer "):
            continue
        rest = challenge[7:].strip()
        params = {}
        while rest:
            match = re.match(r"([!#$%&'*+.^_`|~0-9A-Za-z-]+)=\"((?:\\.|[^\"])*)\"", rest)
            if not match:
                raise MalformedProtocolResponse
            params[match.group(1).lower()] = match.group(2).replace(r'\"', '"')
            rest = rest[match.end():].lstrip()
            if rest:
                if not rest.startswith(","):
                    raise MalformedProtocolResponse
                rest = rest[1:].lstrip()
        if "resource_metadata" in params:
            return _https_url(params["resource_metadata"])
    raise MalformedProtocolResponse


def _authorization_metadata_url(issuer: str) -> str:
    parsed = urlparse(_https_url(issuer))
    path = parsed.path.strip("/")
    suffix = "/.well-known/oauth-authorization-server"
    return f"https://{parsed.netloc}{suffix}{'/' + path if path else ''}"


async def discover_oauth_metadata(config: ProbeConfig, challenges: Sequence[str], http_transport: Any = None) -> Mapping[str, Any]:
    """Read public OAuth metadata only; never starts an authorization flow."""
    import httpx2

    resource_url = _resource_metadata_url(challenges)
    async with httpx2.AsyncClient(follow_redirects=False, transport=http_transport) as client:
        resource_response = await client.get(resource_url)
        if resource_response.is_redirect or resource_response.status_code != 200:
            raise MalformedProtocolResponse
        resource = resource_response.json()
        if not isinstance(resource, Mapping) or _https_url(resource.get("resource")) != config.url:
            raise MalformedProtocolResponse
        servers = resource.get("authorization_servers")
        if not isinstance(servers, list) or len(servers) != 1:
            raise MalformedProtocolResponse
        issuer = _https_url(servers[0])
        auth_response = await client.get(_authorization_metadata_url(issuer))
        if auth_response.is_redirect or auth_response.status_code != 200:
            raise MalformedProtocolResponse
        metadata = auth_response.json()
    if not isinstance(metadata, Mapping) or _https_url(metadata.get("issuer")) != issuer:
        raise MalformedProtocolResponse
    authorization_endpoint = metadata.get("authorization_endpoint")
    token_endpoint = metadata.get("token_endpoint")
    if authorization_endpoint is not None:
        _https_url(authorization_endpoint)
    if token_endpoint is not None:
        _https_url(token_endpoint)
    if metadata.get("registration_endpoint") is not None:
        _https_url(metadata["registration_endpoint"])
        registration = "registration_endpoint"
    elif metadata.get("client_id_metadata_document_supported") is True:
        registration = "client_id_metadata"
    else:
        registration = "none"
    return {
        "authentication": "not_demonstrated",
        "authorization_endpoint_advertised": authorization_endpoint is not None,
        "client_registration": registration,
        "headless_authentication_proven": False,
        "outcome": "oauth_metadata_discovered",
        "server": SERVER_NAME,
        "token_endpoint_advertised": token_endpoint is not None,
    }


def _contains_exception(exc: BaseException, types: Any) -> bool:
    if isinstance(exc, types):
        return True
    return any(_contains_exception(nested, types) for nested in getattr(exc, "exceptions", ()))


def _classify_exception(exc: Exception, status_codes: Sequence[int]) -> str:
    if any(status in (401, 403) for status in status_codes):
        return "authentication_required"
    if any(300 <= status < 400 for status in status_codes):
        return "interactive_authentication_required"
    if _contains_exception(exc, (ConnectionError, OSError, TimeoutError)):
        return "connection_failure"
    if isinstance(exc, MalformedProtocolResponse) or any(200 <= status < 300 for status in status_codes):
        return "malformed_or_invalid_protocol_response"
    return "connection_or_protocol_failure"


async def run_probe(config: ProbeConfig, session_factory: SessionFactory, metadata_discoverer=discover_oauth_metadata) -> Mapping[str, Any]:
    session = None
    try:
        async with session_factory(config) as session:
            initialized = await session.initialize()
            protocol_version = _field(initialized, "protocolVersion", "protocol_version")
            if not isinstance(protocol_version, str) or not protocol_version:
                raise MalformedProtocolResponse

            listed = await session.list_tools()
            tools = _field(listed, "tools")
            if not isinstance(tools, list):
                raise MalformedProtocolResponse
            for tool in tools:
                name = _field(tool, "name")
                if not isinstance(name, str) or not name:
                    raise MalformedProtocolResponse
    except Exception as exc:
        if any(status == 401 for status in getattr(session, "status_codes", ())):
            if config.access_token:
                return _failure("access_token_rejected")
            try:
                return await metadata_discoverer(config, getattr(session, "challenges", ()))
            except Exception:
                return _failure("oauth_metadata_discovery_failed")
        return _failure(_classify_exception(exc, getattr(session, "status_codes", ())))

    return {
        "authentication": "demonstrated" if config.access_token else "not_demonstrated",
        "headless_authentication_proven": False,
        "outcome": "access_token_authenticated_tool_discovery" if config.access_token else "protocol_reachable_tool_discovery",
        "protocol_version": protocol_version,
        "server": SERVER_NAME,
        "tool_count": len(tools),
    }


@asynccontextmanager
async def mcp_session(config: ProbeConfig, http_transport: Any = None):
    """Create an unauthenticated MCP session without redirects or DELETE teardown."""
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    status_codes = []
    challenges = []

    async def record_status(response: Any) -> None:
        status_codes.append(response.status_code)
        if response.status_code == 401:
            challenges.extend(response.headers.get_list("www-authenticate"))

    async with httpx2.AsyncClient(
        event_hooks={"response": [record_status]},
        follow_redirects=False,
        headers={"Authorization": f"Bearer {config.access_token}"} if config.access_token else None,
        transport=http_transport,
    ) as http_client:
        async with streamable_http_client(
            config.url,
            http_client=http_client,
            terminate_on_close=False,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                yield ObservedSession(session, status_codes, challenges)


def main(
    environ: Mapping[str, str] = os.environ,
    session_factory: SessionFactory = mcp_session,
    argv: Sequence[str] = (),
    metadata_discoverer=discover_oauth_metadata,
) -> int:
    previous_logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if argv:
            result = _failure("arguments_not_allowed")
        else:
            try:
                config = _load_config(environ)
            except ValueError:
                result = _failure("missing_or_invalid_config")
            else:
                try:
                    result = asyncio.run(run_probe(config, session_factory, metadata_discoverer))
                except Exception:
                    result = _failure("probe_runtime_failure")
    finally:
        logging.disable(previous_logging_disable)

    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["outcome"] == "access_token_authenticated_tool_discovery" else 1


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
