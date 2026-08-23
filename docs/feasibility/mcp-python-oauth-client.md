# Python MCP OAuth for a scheduled runner

Research date: 2026-08-22. This note uses the current MCP Authorization specification (2026-07-28) and the current stable Python MCP SDK v2 documentation/source. It does not inspect or describe any real credential.

## Recommendation

The smallest safe design is a two-stage client with one private token store:

1. An **interactive bootstrap command** uses the authorization-code flow once. A human opens the authorization URL and approves access; a localhost callback returns the authorization code. The command persists both the issued tokens and the registered client information.
2. A **headless runner command** uses that same persisted state. It never opens a browser and fails closed if the SDK requires a new interactive authorization. It may initialize the MCP session and call only the application operations separately allowed by Ripple's execution policy.

This is the shape documented by the SDK: `OAuthClientProvider` is attached to an `httpx2.AsyncClient`, which is passed to `streamable_http_client`; the provider receives the MCP server URL, `OAuthClientMetadata`, a `TokenStorage`, and redirect/callback handlers. The SDK owns discovery, registration, PKCE, `state`/issuer checks, token exchange, and refresh. [Official Python SDK OAuth client guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/oauth-clients.md#the-provider) [Official client example](https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/snippets/clients/oauth_client.py)

Do not treat an OAuth session owned by Codex or another MCP client as the runner's credential. The plain runner should have its own client registration and private storage lifecycle. This follows from the SDK's storage contract: tokens and `OAuthClientInformationFull` are the provider's reusable state, and the guide explicitly says to persist both. [Official Python SDK token-storage guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/oauth-clients.md#token-storage) [Official `TokenStorage` protocol](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L1968-L1993)

Use `ClientCredentialsOAuthProvider` only if the authorization server explicitly provisions a `client_id` and `client_secret` for the `client_credentials` grant. It is the SDK's browser-free machine-to-machine option, but it is not a substitute that a client can assume a user-account server supports. [Official Python SDK machine-to-machine guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/oauth-clients.md#machine-to-machine) [Official provider source](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/extensions/client_credentials.py)

## Bootstrap constraints

- Authorization-code bootstrap is intentionally interactive: the SDK calls `redirect_handler` with the complete authorization URL and then awaits `callback_handler` for `code`, `state`, and optional `iss`. [Official handler documentation](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/oauth-clients.md#the-two-handlers) [Official flow source](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2356-L2427)
- Use an exact registered loopback redirect such as `http://127.0.0.1:<fixed-port>/callback`, bind the callback listener only to loopback, accept one callback, verify through the provider, then close it. The MCP specification requires redirect URIs to be localhost or HTTPS, exact registration/validation, PKCE, and `state` verification. [MCP communication and authorization-code security](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations#communication-security)
- Dynamic client registration is deprecated and optional in the MCP specification. Current clients should prefer pre-registration when available, then a Client ID Metadata Document, and use dynamic registration only as a fallback. Therefore bootstrap must surface a clear unsupported-registration error and must not retry registration indefinitely. [MCP client registration options](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration) [Official SDK registration behavior](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/oauth-clients.md#client-id-metadata-documents)
- Persist the `OAuthToken` and `OAuthClientInformationFull` atomically. The latter can include a `client_secret`; treat the whole record as secret even when the authorization server registered a public client. The SDK's four-method storage protocol does not provide encryption, file permissions, locking, or atomicity; those are application responsibilities. [Official storage protocol](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L1968-L1993) [Official client-information model](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/shared/auth.py)

## Refresh behavior and an important restart gap

Within one provider lifetime, the SDK computes an in-memory expiry time after token exchange, refreshes when the token is expired and a refresh token plus client information exist, preserves an old refresh token when a successful refresh response does not rotate it, and writes the refreshed token back through `TokenStorage`. A failed or invalid refresh clears in-memory tokens and falls through to full authorization. [Official refresh implementation](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2514-L2602) [Official auth-flow branch](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2649-L2684)

However, the current SDK source is not sufficient by itself to prove refresh across short-lived scheduled processes:

- `OAuthToken` stores relative `expires_in`, not an absolute issuance or expiry timestamp. [Official token model](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/shared/auth.py#L743-L755)
- `_initialize()` reloads tokens and client information but does not reconstruct `token_expiry_time`. [Official initialization source](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2604-L2612)
- `is_token_valid()` treats a missing in-memory expiry time as valid. Consequently, after a process restart the provider can send a stale stored access token; a resulting `401` enters the full interactive authorization branch rather than the pre-request refresh branch. This conclusion is a direct inference from the preceding source and the auth-flow branch. [Official validity and refresh predicates](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2042-L2065) [Official auth-flow branch](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2649-L2684)
- `_initialize()` also does not restore discovered authorization-server metadata. The refresh builder uses the discovered `token_endpoint` when present, but otherwise falls back to `/token` on the MCP server's origin. Thus merely restoring expiry can send refresh to the wrong endpoint after restart. This conclusion is a direct inference from the initialization and refresh-builder source. [Official refresh request builder](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2514-L2554) [Official initialization source](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2604-L2612)

For Ripple's start-per-schedule runner, persist an absolute `access_token_expires_at` and the validated authorization-server metadata alongside the SDK models. Use a small, version-pinned adapter that restores `OAuthClientProvider.context.token_expiry_time`, `oauth_metadata`, and the issuer/resource binding before the first request. Reject persisted metadata whose server, resource, or issuer does not match the configured target. This touches SDK internals, so it requires focused contract tests and must be rechecked on every SDK upgrade. The adapter should set an already-expired timestamp when expiry is unknown but a refresh token exists, causing a refresh attempt instead of sending an age-unknown bearer token. If no refresh token exists, the headless command must stop and request a new interactive bootstrap rather than attempting to authorize silently.

## Security boundaries

- Keep the token store outside the repository, plans, logs, and test fixtures. Use the deployment platform's secret manager or OS keyring; never print access tokens, refresh tokens, authorization codes, callback URLs, or client secrets. MCP notes that stolen stored tokens allow requests that appear legitimate and requires secure token storage; public-client refresh tokens must rotate. A client that wants refresh tokens must keep them confidential, request the `refresh_token` grant, and must not assume the authorization server will issue one. [MCP refresh-token requirements](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#refresh-tokens) [MCP token-theft guidance](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations#token-theft)
- Keep the provider's default protected-resource validation. The SDK rejects a protected-resource metadata `resource` that does not match the configured server unless the caller overrides validation. [Official resource-validation source](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/client/auth/oauth2.py#L2628-L2647)
- Let the provider send tokens only in the `Authorization: Bearer` header. MCP requires authorization on every HTTP request, forbids access tokens in URI query strings, and requires audience-bound `resource` parameters in authorization and token requests. [MCP access-token usage](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#access-token-usage) [MCP resource parameter](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#resource-parameter-implementation)
- Separate bootstrap from execution permissions. Possession of a valid bearer token authenticates the runner but does not decide which MCP tools it may call; Ripple's deterministic execution and risk boundaries remain independent.

## Minimum proof before declaring headless authentication feasible

Use a dedicated non-trading test path and sanitized observations only:

1. Bootstrap once and confirm the store contains the expected record *types*, an absolute expiry, and issuer/resource-bound authorization-server metadata, without exposing credential values.
2. Start a fresh Python process and complete MCP `initialize` plus `tools/list` without a browser.
3. Force the locally recorded expiry into the past, start another fresh process, and prove exactly one refresh request succeeds and atomically replaces stored token state.
4. Start another fresh process and prove the rotated/reused refresh token still works.
5. Simulate refresh rejection and prove the runner exits with an "interactive bootstrap required" status without looping, registering repeatedly, or calling a broker tool.
6. Confirm logs and failure artifacts contain no token, authorization code, callback query, client secret, account identifier, balance, position, or order detail.

Steps 1–4 establish the positive live path. Steps 5–6 establish the mock-transport failure path and sanitized local CLI boundary. Completing all six supports the conclusion that the **local credential lifecycle is demonstrated**; it does not prove the production deployment secret store, runner identity, or cross-host coordination boundary.

## Local adapter status

The Phase −1 adapter in `spikes/mcp_oauth_restart_adapter.py` pins MCP Python SDK 2.0.0 and implements the restart seam described above. Mock-transport contract tests cover complete bootstrap persistence, fresh-process restoration, refresh before an expired or age-unknown token is sent, refresh-token rotation, compare-and-swap conflict, invalid-refresh clearing, transient-refresh preservation, binding validation, and rejection of any headless fallback to interactive authorization.

The local feasibility path now also includes:

- `spikes/macos_keychain_oauth_store.py`: an explicit macOS Keychain backend plus same-host file locking for versioned `load` / compare-and-swap / `clear`; each Keychain service/account identity deterministically owns one mode-`0600` lock file containing no secret state.
- `spikes/robinhood_mcp_oauth_cli.py bootstrap`: a one-time interactive command that opens a fixed loopback callback before the HTTPS authorization URL, validates the callback path and state, persists the complete record, and emits only sanitized booleans/aggregate evidence about model types, finite expiry, and metadata bindings.
- `spikes/robinhood_mcp_oauth_cli.py probe`: a separate headless command with no redirect or callback handler. It performs only MCP `initialize` and `tools/list` and emits sanitized aggregate output.
- `spikes/robinhood_mcp_oauth_cli.py refresh-proof`: atomically marks only the stored absolute expiry stale, starts the same headless probe, and requires the store revision to show exactly one refresh replacement.
- `scripts/verify-robinhood-mcp-oauth.sh`: the repeatable local five-stage verification wizard. It runs `refresh-proof` twice as separate processes before an ordinary headless probe, exercising a rotated or reused refresh credential. Run it from any directory; it returns to the repository root itself.
- `spikes/robinhood_mcp_account_probe.py`: a separate read-only follow-up that reuses the headless credential, invokes only `get_accounts`, selects the one account accessible to that identity, keeps its full identifier in memory, and emits only sanitized count/boolean evidence. Run it only when a live account-read verification is intended:

  ```bash
  uv run --no-cache \
    --with-requirements spikes/requirements-robinhood-mcp-auth-probe.txt \
    python spikes/robinhood_mcp_account_probe.py
  ```

The Keychain store is intentionally a local proof, not the Phase 0 production secret-store decision: its file lock provides CAS only to processes on this Mac, and it does not establish deployment auditability or cross-host coordination. The `keyring` project documents macOS Keychain as a supported system backend and notes that processes using the same Python executable may inherit access unless Keychain Access controls are tightened; use a dedicated runtime identity before treating this pattern as production isolation. [Official keyring backend documentation](https://github.com/jaraco/keyring/blob/main/README.rst#using-keyring) [Official keyring security considerations](https://github.com/jaraco/keyring/blob/main/README.rst#security-considerations)

## Local live result — 2026-08-22

Alicia completed the five-stage wizard against Robinhood. Its success exit proves the runner-owned bootstrap stored valid model types, finite absolute expiry, and issuer/resource-bound metadata; two separate fresh Python processes each forced expiry and observed exactly one atomic refresh-state replacement; and a final fresh process completed browser-free MCP `initialize` plus `tools/list`. The OAuth CLI emitted only sanitized aggregate results and called no broker tool. A subsequent separate read-only account probe called `get_accounts` once and selected the one active caller-accessible account from two brokerage accounts without emitting an identifier.

This closes positive-path proof steps 1–4 for the local macOS runner. A command-level mock-transport test closes step 5 by proving an `invalid_grant` refresh response makes exactly one authorization-server request, clears the rejected credential, returns `oauth_bootstrap_required`, and never enters an MCP session. The same test closes the refresh-rejection portion of step 6 by capturing stdout/stderr and proving response secrets are absent; the broader CLI suite independently covers authorization codes, token/client values, backend failures, account identifiers, and arbitrary exception text. These probes create no failure artifact files and emit only fixed-schema sanitized JSON.

All six local proof steps are therefore complete. The macOS Keychain store remains a local feasibility store; selecting a production store with encryption, per-account isolation, atomic CAS, and auditability is still Phase 0 work.
