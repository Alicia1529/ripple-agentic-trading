# Robinhood MCP headless-authentication probe

On 2026-08-22, the read-only probe made one unauthenticated request to `https://agent.robinhood.com/mcp/trading` with an otherwise empty environment. The endpoint returned a 401 challenge, and public OAuth metadata discovery completed without redirects, credentials, an authorization flow, client registration, token exchange, refresh, MCP tool call, or broker operation.

Sanitized result:

```json
{"authentication":"not_demonstrated","authorization_endpoint_advertised":true,"client_registration":"registration_endpoint","headless_authentication_proven":false,"outcome":"oauth_metadata_discovered","server":"robinhood_trading","token_endpoint_advertised":true}
```

This proves only that the endpoint advertises OAuth metadata after an unauthenticated challenge. It does not prove that client registration is permitted, that any headless flow exists, or that authentication, token refresh, account selection, or any order behavior works.
