# Robinhood MCP equity-order tool schemas

Research date: 2026-08-22. This is a read-only snapshot of the first-party `robinhood_trading` MCP tool declarations exposed to the current authenticated Codex session. The declarations were inspected through the session's tool registry without invoking a Robinhood tool. All schema and behavioral claims below come from those runtime declarations; the separate local result records the later read-only account call. [R1]

## `get_accounts`

`get_accounts` takes no arguments. It returns nullable `data.accounts`; each non-null account includes a full `account_number`, caller-relative `agentic_allowed`, account state/deactivation fields, brokerage and trading types, default status, options level, and an `rhs_account_number`. Nickname, affiliate, management type, linked crypto account number, and unsettled funds are optional. Account and crypto identifiers must be masked except when passed unchanged to another broker tool. [R1]

The declaration says exactly one account is accessible to the current agent identity and that `agentic_allowed` is the sole eligibility signal; nickname text must not be used to infer eligibility. Ripple's local probe therefore selects only when exactly one account has that signal, keeps the full identifier in process memory, and fails closed on zero, multiple, or malformed candidates. It reports account count and sanitized booleans only. [R1]

### Local live result — 2026-08-22

After the OAuth wizard completed, the plain local runner invoked `get_accounts` once. The sanitized result reported two brokerage accounts, exactly one caller-accessible binding, and an active selected account. No account identifier, nickname, balance, position, or order detail was emitted. This proves one local credential-to-account binding; it does not yet prove the second independent binding required by the target architecture.

## Account selection and shared order semantics

All four tools require an explicit `account_number`. The current account declaration directs callers to use its unique accessible account for trades; the order declarations also require the account to be explicitly identified in each call rather than omitted. Review, place, and cancel additionally require `agentic_allowed=true`; `get_equity_orders` does not declare that restriction. Cancellation requires the same account that owns the order. [R1]

`review_equity_order` and `place_equity_order` share these order fields and rules: [R1]

| Input | Required | Declared meaning |
| --- | --- | --- |
| `account_number` | yes | Explicit agentic-enabled brokerage account |
| `side` | yes | `buy` or `sell` |
| `symbol` | yes | Stock symbol |
| `type` | yes | `market`, `limit`, `stop_market`, or `stop_limit` |
| `quantity` | exactly one of this / `dollar_amount` | Share count as a string |
| `dollar_amount` | exactly one of this / `quantity` | USD notional as a string; valid only for `market` |
| `limit_price` | conditional | Required for `limit` and `stop_limit` |
| `stop_price` | conditional | Required for `stop_market` and `stop_limit` |
| `market_hours` | no | `regular_hours` (default), `extended_hours`, or `all_day_hours` |
| `time_in_force` | no | `gfd` (default) or `gtc` |
| `tax_lots` | no | Sell-only array of `{open_lot_id, quantity}`; at most 30, quantities must sum to order quantity |

Share quantities may be fractional only for market orders in regular hours, on an eligible account, to at most six decimal places, with no short selling. Dollar-based orders are market-only and regular-hours-only; the server computes shares from `last_trade_price`. Fractional orders are also regular-hours-only. Extended-hours and all-day-hours orders must be limit orders. Specified tax lots are US-account, sell-only, and unavailable with dollar amounts, stop orders, all-day-hours, or fractional-share limit orders. [R1]

## `review_equity_order`

The required and optional inputs are exactly the shared fields above. There is no `ref_id` or other client order/idempotency key. The tool simulates an order and does not place it. [R1]

`data` returns:

- Echoes: required `symbol`, `side`, and `type`; optional `quantity`, `dollar_amount`, `limit_price`, and `stop_price`.
- `order_checks`: required arbitrary object. `{}` means no alerts; a non-empty object contains an `alert_type` plus alert-specific details whose shapes may evolve.
- `market_data_disclosure`: optional compliance disclosure string that the declaration requires clients to display verbatim.
- `quote_data`: required but nullable quote object with the exact fields below.
- Top-level `guide`: presentation and confirmation instructions. [R1]

| `quote_data` field | Meaning |
| --- | --- |
| `symbol`, `state`, `has_traded` | Ticker, listing state, and whether the instrument has ever traded |
| `ask_price`, `bid_price` | Current lowest sell and highest buy prices |
| `venue_ask_time`, `venue_bid_time` | Ask and bid timestamps |
| `last_trade_price`, `venue_last_trade_time` | Most recent regular-hours trade and timestamp |
| `last_non_reg_trade_price`, `venue_last_non_reg_trade_time` | Nullable most recent non-regular trade and timestamp |
| `previous_close`, `adjusted_previous_close`, `previous_close_date` | Raw prior print, corporate-action-adjusted prior close, and nullable trading date |

## `place_equity_order`

Inputs are the shared review fields plus optional `ref_id`. `ref_id` is a UUID idempotency key: generate it once for a logical order and reuse the same value only for retries of that order. Omitting it uses a server-generated key and loses client-to-gateway idempotency. This is the only one of the four declarations with a client-supplied idempotency/order key. [R1]

`data.order` is optional and nullable. When present, it contains: [R1]

| Field | Meaning |
| --- | --- |
| `id`, `instrument_id`, `symbol` | Order, instrument, and ticker identifiers |
| `side`, `state`, `placed_agent` | Direction, lifecycle state, and placement source. Declared states include `new`, `queued`, `unconfirmed`, `partially_filled`, `filled`, `cancelled`, `rejected`, `failed`, `voided`, `pending_cancelled`, `partially_filled_rest_cancelled`, `locating`, and `locate_failed` |
| `type`, `trigger` | Upstream type and trigger; combine them to recover market/limit/stop type |
| `quantity`, `dollar_based_amount`, `cumulative_quantity` | Nullable requested shares, nullable requested USD notional (`amount`, `currency_code`), and shares filled so far |
| `price`, `stop_price`, `average_price` | Limit, stop, and weighted-average fill prices |
| `time_in_force`, `market_hours` | Duration and trading session |
| `created_at`, `last_transaction_at` | Creation and latest fill/cancel/reject time |
| `executions` | Nullable fills, each with `id`, `price`, `quantity`, `fees`, and `timestamp` |
| `fees`, `reject_reason` | Cumulative fees and optional rejection reason |

For dollar orders, `dollar_based_amount` is populated while `quantity` may remain null until the first fill; `cumulative_quantity` is always expressed in shares. A successful response means submitted, not necessarily filled. The top-level `guide` states how to communicate that distinction. [R1]

## `cancel_equity_order`

Required inputs are `account_number` and `order_id`; there are no optional inputs and no idempotency key. `order_id` is the UUID returned by order history and must belong to the selected account. `data.accepted` is a required boolean. `accepted=true` means the broker accepted an asynchronous cancellation request, not that cancellation has completed; the declaration directs callers to check history for `pending_cancelled`, `cancelled`, `partially_filled_rest_cancelled`, or a fill that raced the cancel. The response also contains top-level `guide`. [R1]

## `get_equity_orders` (order history)

The current registry exposes order history through `get_equity_orders`; there is no separate equity-order-history tool. [R1]

`account_number` is required. All other inputs are optional: [R1]

| Input | Meaning |
| --- | --- |
| `created_at_gte` | Inclusive UTC/ISO-8601 or `YYYY-MM-DD` lower bound; naive values are UTC |
| `cursor` | Cursor query parameter from the prior page's `next` URL |
| `order_id` | Single-order filter; preserves `orders[]` shape with at most one result |
| `placed_agent` | Source filter such as `user`, `agentic`, `recurring`, or `drip` |
| `state` | One of the declared filter values: `new`, `queued`, `confirmed`, `unconfirmed`, `partially_filled`, `filled`, `cancelled`, `rejected`, `failed`, or `voided` |
| `symbol` | Symbol filter; triggers a symbol-to-instrument lookup |

`data.orders` is a nullable array (whose item schema is also nullable) ordered newest first. Each non-null order has exactly the same order fields documented for `place_equity_order`. `data.next` is an optional next-page URL and is empty when pagination is complete. The top-level `guide` gives presentation rules, including using dollar semantics until a dollar order has a meaningful cumulative share quantity. There is no declared upper-date bound, page-size input, or client idempotency key. [R1]

No review identifier or approval token is returned by `review_equity_order`; placement repeats the order parameters. No declaration states that review output is cryptographically or transactionally bound to a later placement. [R1]

## What schema inspection does not prove

Without invoking the tools, this snapshot does not prove:

- that live account eligibility, symbol tradability, fractional eligibility, buying power, or tax-lot eligibility will pass;
- actual minimum/maximum notionals, share increments beyond the stated six-decimal fractional ceiling, enum rejection behavior, or session availability for a particular instrument;
- the concrete shapes of current or future `order_checks` alerts;
- that `ref_id` deduplicates correctly across real transient failures, process restarts, or ambiguous broker responses;
- submission, fill, rejection, cancellation-race, pagination, ordering, retention, or history-completeness behavior;
- which nullable or optional output fields Robinhood populates for any particular live order.

Those properties require separately authorized, deliberately scoped live tests. This document provides contract-shape evidence only and must not be treated as execution evidence.

## Source

- **[R1] First-party runtime tool registry:** current-session declarations for `mcp__robinhood_trading__get_accounts`, `mcp__robinhood_trading__review_equity_order`, `mcp__robinhood_trading__place_equity_order`, `mcp__robinhood_trading__cancel_equity_order`, and `mcp__robinhood_trading__get_equity_orders`, inspected 2026-08-22 without calling any Robinhood tool. Because this is a session-local runtime contract rather than a public web page, it has no stable external URL.
