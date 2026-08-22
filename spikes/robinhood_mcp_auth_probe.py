#!/usr/bin/env python3
"""Read-only Robinhood Trading MCP authentication feasibility probe."""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncContextManager, Callable, Mapping, Protocol, Sequence


SERVER_NAME = "robinhood_trading"
EXPECTED_URL = "https://agent.robinhood.com/mcp/trading"
URL_ENV = "ROBINHOOD_MCP_URL"


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


class MalformedProtocolResponse(Exception):
    pass


class ObservedSession:
    def __init__(self, session: Any, status_codes: Sequence[int]):
        self._session = session
        self.status_codes = status_codes

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
    return ProbeConfig(url=url)


def _failure(outcome: str) -> Mapping[str, Any]:
    return {
        "authentication": "not_demonstrated",
        "headless_authentication_proven": False,
        "outcome": outcome,
        "server": SERVER_NAME,
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


async def run_probe(config: ProbeConfig, session_factory: SessionFactory) -> Mapping[str, Any]:
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
        return _failure(_classify_exception(exc, getattr(session, "status_codes", ())))

    return {
        "authentication": "not_demonstrated",
        "headless_authentication_proven": False,
        "outcome": "protocol_reachable_tool_discovery",
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

    async def record_status(response: Any) -> None:
        status_codes.append(response.status_code)

    async with httpx2.AsyncClient(
        event_hooks={"response": [record_status]},
        follow_redirects=False,
        transport=http_transport,
    ) as http_client:
        async with streamable_http_client(
            config.url,
            http_client=http_client,
            terminate_on_close=False,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                yield ObservedSession(session, status_codes)


def main(
    environ: Mapping[str, str] = os.environ,
    session_factory: SessionFactory = mcp_session,
    argv: Sequence[str] = (),
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
                    result = asyncio.run(run_probe(config, session_factory))
                except Exception:
                    result = _failure("probe_runtime_failure")
    finally:
        logging.disable(previous_logging_disable)

    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["outcome"] == "authenticated_discovery" else 1


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
