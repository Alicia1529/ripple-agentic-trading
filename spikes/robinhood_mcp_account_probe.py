#!/usr/bin/env python3
"""Select the one Robinhood account accessible to the local OAuth runner."""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Mapping

from macos_keychain_oauth_store import MacOSKeychainOAuthStateStore
from robinhood_mcp_oauth_cli import (
    SERVER_NAME,
    LoopbackOAuthCallback,
    SessionFactory,
    build_provider,
    mcp_session,
)


class AccountBindingError(Exception):
    """The authenticated identity cannot be bound to exactly one account."""


@dataclass(frozen=True)
class AgenticAccountBinding:
    """Private in-process account identifier for later broker calls."""

    account_number: str


@dataclass(frozen=True)
class AccountProbeResult:
    binding: AgenticAccountBinding
    evidence: Mapping[str, Any]


def _field(value: Any, name: str) -> Any:
    camel_name = "structuredContent" if name == "structured_content" else name
    for candidate in (name, camel_name):
        if isinstance(value, Mapping) and candidate in value:
            return value[candidate]
        if hasattr(value, candidate):
            return getattr(value, candidate)
    raise AccountBindingError("Robinhood account response is malformed")


def select_agentic_account(response: Any) -> tuple[AgenticAccountBinding, int, bool]:
    structured = _field(response, "structured_content")
    data = _field(structured, "data")
    accounts = _field(data, "accounts")
    if accounts is None:
        accounts = []
    if not isinstance(accounts, list):
        raise AccountBindingError("Robinhood account response is malformed")

    accessible = []
    for account in accounts:
        if not isinstance(account, Mapping) or not isinstance(account.get("agentic_allowed"), bool):
            raise AccountBindingError("Robinhood account response is malformed")
        if account["agentic_allowed"]:
            accessible.append(account)
    if len(accessible) != 1:
        raise AccountBindingError("Expected exactly one accessible Robinhood account")

    selected = accessible[0]
    account_number = selected.get("account_number")
    deactivated = selected.get("deactivated")
    permanently_deactivated = selected.get("permanently_deactivated")
    state = selected.get("state")
    if (
        not isinstance(account_number, str)
        or not account_number
        or not isinstance(deactivated, bool)
        or not isinstance(permanently_deactivated, bool)
        or not isinstance(state, str)
        or not state
    ):
        raise AccountBindingError("Robinhood account response is malformed")
    active = state == "active" and not deactivated and not permanently_deactivated
    return AgenticAccountBinding(account_number), len(accounts), active


async def run_account_probe(provider: Any, session_factory: SessionFactory = mcp_session) -> AccountProbeResult:
    async with session_factory(provider) as session:
        await session.initialize()
        response = await session.call_tool("get_accounts", {})
    binding, account_count, active = select_agentic_account(response)
    return AccountProbeResult(
        binding=binding,
        evidence={
            "account_binding_demonstrated": True,
            "accessible_account_active": active,
            "brokerage_account_count": account_count,
            "outcome": "agentic_account_binding_selected",
            "server": SERVER_NAME,
        },
    )


async def run_command() -> AccountProbeResult:
    store = MacOSKeychainOAuthStateStore()
    callback = LoopbackOAuthCallback()
    provider = build_provider("probe", store, callback)
    return await run_account_probe(provider)


def main(argv=None, command_runner=run_command) -> int:
    logging.disable(logging.CRITICAL)
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        evidence = {
            "account_binding_demonstrated": False,
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
                "account_binding_demonstrated": False,
                "outcome": "account_binding_failed",
                "server": SERVER_NAME,
            }
            status = 1
    print(json.dumps(evidence, separators=(",", ":"), sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
