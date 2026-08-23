# Robinhood MCP headless-authentication probe

On 2026-08-22, the read-only probe made one unauthenticated request to `https://agent.robinhood.com/mcp/trading` with an otherwise empty environment. The endpoint returned a 401 challenge, and public OAuth metadata discovery completed without redirects, credentials, an authorization flow, client registration, token exchange, refresh, MCP tool call, or broker operation.

Sanitized result:

```json
{"authentication":"not_demonstrated","authorization_endpoint_advertised":true,"client_registration":"registration_endpoint","headless_authentication_proven":false,"outcome":"oauth_metadata_discovered","server":"robinhood_trading","token_endpoint_advertised":true}
```

This proves only that the endpoint advertises OAuth metadata after an unauthenticated challenge. It does not prove that client registration is permitted, that any headless flow exists, or that authentication, token refresh, account selection, or any order behavior works.

## Authenticated Codex observation

Later on 2026-08-22, an already-authorized Codex MCP connection successfully listed the Robinhood tool surface, returned 56 scanner filter specifications, and completed an account-level read. Only aggregate success/eligibility booleans were observed; no account identifier, balance, position, or order was written to the repository. No write or trading tool was called.

This proves that Alicia's Codex connection is authenticated and can reach account-scoped reads. It does **not** provide a credential to the plain Python runner: the runner must own a separate bootstrap, token-storage, and refresh lifecycle. See `mcp-python-oauth-client.md` for the SDK boundary and the remaining cross-process refresh gap.

The probe now accepts an optional `ROBINHOOD_MCP_ACCESS_TOKEN` supplied by the process environment. With a valid token it performs only MCP `initialize` and `tools/list`, returns a sanitized success record, and exits zero. A rejected token fails closed without falling back to metadata discovery. This path is covered with a mock transport; it has not been run against Robinhood because no runner-owned token has been bootstrapped.
