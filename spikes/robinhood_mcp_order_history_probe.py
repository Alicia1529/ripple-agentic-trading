#!/usr/bin/env python3
"""Prove sanitized read access to Robinhood equity-order history."""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Mapping

from macos_keychain_oauth_store import MacOSKeychainOAuthStateStore
from robinhood_mcp_account_probe import AccountBindingError, select_agentic_account
from robinhood_mcp_oauth_cli import (
    SERVER_NAME,
    LoopbackOAuthCallback,
    SessionFactory,
    build_provider,
    mcp_session,
)


class OrderHistoryProbeError(Exception):
    """The broker's order-history response cannot be safely validated."""


@dataclass(frozen=True)
class OrderHistoryProbeResult:
    evidence: Mapping[str, Any]


def _validate_orders(response: Any) -> None:
    def field(value: Any, name: str) -> Any:
        camel_name = "structuredContent" if name == "structured_content" else name
        for candidate in (name, camel_name):
            if isinstance(value, Mapping) and candidate in value:
                return value[candidate]
            if hasattr(value, candidate):
                return getattr(value, candidate)
        raise OrderHistoryProbeError("Robinhood order-history response is malformed")

    structured = field(response, "structured_content")
    data = field(structured, "data")
    orders = field(data, "orders")
    if orders is None:
        return
    if not isinstance(orders, list) or any(order is not None and not isinstance(order, Mapping) for order in orders):
        raise OrderHistoryProbeError("Robinhood order-history response is malformed")


async def run_order_history_probe(
    provider: Any, session_factory: SessionFactory = mcp_session
) -> OrderHistoryProbeResult:
    async with session_factory(provider) as session:
        await session.initialize()
        accounts_response = await session.call_tool("get_accounts", {})
        binding, _account_count, _active = select_agentic_account(accounts_response)
        history_response = await session.call_tool(
            "get_equity_orders", {"account_number": binding.account_number}
        )
    _validate_orders(history_response)
    return OrderHistoryProbeResult(
        evidence={
            "history_response_well_formed": True,
            "order_history_access_demonstrated": True,
            "outcome": "equity_order_history_read",
            "server": SERVER_NAME,
        }
    )


async def run_command() -> OrderHistoryProbeResult:
    store = MacOSKeychainOAuthStateStore()
    callback = LoopbackOAuthCallback()
    provider = build_provider("probe", store, callback)
    return await run_order_history_probe(provider)


def main(argv=None, command_runner=run_command) -> int:
    logging.disable(logging.CRITICAL)
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        evidence = {
            "order_history_access_demonstrated": False,
            "outcome": "invalid_command",
            "server": SERVER_NAME,
        }
        status = 1
    else:
        try:
            evidence = asyncio.run(command_runner()).evidence
            status = 0
        except Exception:
            evidence = {
                "order_history_access_demonstrated": False,
                "outcome": "order_history_probe_failed",
                "server": SERVER_NAME,
            }
            status = 1
    print(json.dumps(evidence, separators=(",", ":"), sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
