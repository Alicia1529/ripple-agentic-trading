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
TOKEN_ENV = "ROBINHOOD_MCP_BEARER_TOKEN"


class ProbeSession(Protocol):
    async def initialize(self) -> Any:
        ...

    async def list_tools(self) -> Any:
        ...


SessionFactory = Callable[["ProbeConfig"], AsyncContextManager[ProbeSession]]


@dataclass(frozen=True)
class ProbeConfig:
    url: str
    bearer_token: str


class MalformedProtocolResponse(Exception):
    pass


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
    token = environ.get(TOKEN_ENV, "").strip()
    if not url or not token:
        raise ValueError
    if url != EXPECTED_URL:
        raise ValueError
    return ProbeConfig(url=url, bearer_token=token)


def _classify_exception(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code in (401, 403):
        return "authentication_failure"
    if isinstance(status_code, int) and 300 <= status_code < 400:
        return "interaction_required"
    if isinstance(exc, MalformedProtocolResponse):
        return "malformed_protocol_response"
    if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
        return "connection_failure"
    return "connection_or_authentication_failure"


async def run_probe(config: ProbeConfig, session_factory: SessionFactory) -> Mapping[str, Any]:
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

        return {
            "ok": True,
            "operation": "initialize+tools/list",
            "protocol_version": protocol_version,
            "server": SERVER_NAME,
            "tool_count": len(tools),
        }
    except Exception as exc:
        return {
            "error": _classify_exception(exc),
            "ok": False,
            "server": SERVER_NAME,
        }


@asynccontextmanager
async def mcp_session(config: ProbeConfig):
    """Create an MCP SDK session without interactive authentication."""
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    headers = {"Authorization": "Bearer " + config.bearer_token}
    async with httpx2.AsyncClient(headers=headers, follow_redirects=False) as http_client:
        async with streamable_http_client(config.url, http_client=http_client) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                yield session


def main(
    environ: Mapping[str, str] = os.environ,
    session_factory: SessionFactory = mcp_session,
    argv: Sequence[str] = (),
) -> int:
    previous_logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if argv:
            result = {"error": "arguments_not_allowed", "ok": False, "server": SERVER_NAME}
        else:
            try:
                config = _load_config(environ)
            except ValueError:
                result = {"error": "missing_or_invalid_config", "ok": False, "server": SERVER_NAME}
            else:
                try:
                    result = asyncio.run(run_probe(config, session_factory))
                except Exception:
                    result = {"error": "probe_runtime_failure", "ok": False, "server": SERVER_NAME}
    finally:
        logging.disable(previous_logging_disable)

    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
