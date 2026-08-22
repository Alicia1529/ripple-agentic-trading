# Codex 提案：交易自动化系统

**状态：** 提案阶段  
**日期：** 2026-08-21  
**项目负责人：** Alicia  
**提案方：** Codex  

> 本文档是 Codex 为 Alicia 的交易自动化项目提出的设计与实施方案。券商选择、交易策略、风险限制、税务处理和资金分配等最终决策，均须由 Alicia 审核批准。

## 1. Executive summary

This proposal recommends a staged, risk-controlled trading automation system with three distinct responsibilities:

1. **Robinhood Agentic account:** isolated small-capital automation experiment, initially funded with $250 and capped at $500–$1,000 after validation.
2. **Schwab:** deterministic medium-frequency trading and “做 T” strategies once the execution system has passed paper and small-live validation.
3. **Fidelity and existing Schwab accounts:** read-only portfolio monitoring and a weekly decision report; trades in long-term accounts remain manually approved.

The system will support multiple strategies across different brokerage accounts or within one account. A strategy-level capital ledger will show how much capital was assigned, how much cash was actually deployed, current exposure, trading costs, realized and unrealized P&L, and remaining capacity.

The project will not attempt professional high-frequency trading. Retail brokerage APIs, small capital, spread and slippage costs, account rules, and the absence of exchange co-location make true HFT unsuitable. The practical target is systematic trading on hourly, daily, and multi-day horizons.

The system will keep AI and execution responsibilities separate. AI may research, summarize, explain signals, and detect anomalies. Deterministic code must enforce symbol allowlists, position sizing, loss limits, order limits, tax-lot restrictions, and emergency shutdown rules.

## 2. Objectives

### 2.1 Primary objectives

- Produce a weekly portfolio report across Fidelity, Schwab, and Robinhood.
- Research and validate one simple, explainable medium-frequency ETF strategy.
- Run the strategy in simulation and paper trading before risking capital.
- Conduct a small, isolated live experiment without exposing long-term assets.
- Build a complete audit trail for every signal, risk decision, order, fill, and reconciliation event.
- Attribute capital usage, positions, costs, and performance to each strategy even when several strategies share one brokerage account.

### 2.2 Non-objectives

- Professional or latency-arbitrage HFT.
- Guaranteed returns or income targets.
- Unrestricted autonomous AI trading.
- Options, short selling, leveraged ETFs, penny stocks, or borrowed margin in the initial release.
- Browser automation, credential scraping, or reverse-engineered Fidelity/Robinhood private endpoints.
- Management of accounts belonging to other people.

## 3. Brokerage roles

| Brokerage | Proposed role | Initial permissions | Rationale |
|---|---|---|---|
| Robinhood | Small isolated automation experiment | Read all connected Robinhood accounts; trade only in the dedicated Agentic account | Official Trading MCP, small-dollar fractional trading, and account-level isolation make it the fastest controlled experiment |
| Schwab | Conditional medium-frequency and 做 T production candidate | Read-only first; live orders enabled only after validation and a broker-selection review | Conventional Trader API supports deterministic strategy and broker-adapter architecture; this advantage must outweigh token operations, fractional-share, and paper/live limitations |
| Fidelity | Long-term core holdings | Read-only monitoring; manual trade approval | Strong long-term account experience, but no public retail stock-trading API |

Robinhood is preferred for the first live experiment because its Agentic account isolates write access. Schwab is only a **candidate**, not the predetermined final broker, for a later deterministic production system. A conventional API is generally easier to test, replay, reconcile, schedule without an LLM, and place behind a portable broker adapter. This is an engineering distinction, not a claim that Schwab produces better returns.

### 3.1 Why Schwab is a conditional production candidate

Schwab is proposed for medium-frequency and 做 T only when the strategy needs a conventional, deterministic execution path:

```text
scheduled market data -> versioned signal -> hard risk checks
                      -> order API -> fill reconciliation
```

The reasons are:

- The trading loop can run as ordinary application code without requiring an AI agent to interpret a prompt for every decision.
- Account, order, and market-data functions can be isolated behind a broker adapter, making the strategy and risk engine easier to unit test and later migrate.
- Strategy versions, input data, intended orders, API responses, and fills can be replayed as a deterministic audit trail.
- A conventional API fits hourly, daily, and multi-day scheduling better than an interactive natural-language workflow.
- thinkorswim is useful for manual inspection and paper experimentation alongside the API integration.

These advantages do **not** establish Schwab as automatically superior. Before enabling Schwab live orders, the implementation must compare Schwab against Robinhood Agentic and, if opening another broker is acceptable, Alpaca or Interactive Brokers. The comparison must cover:

- Fractional-share support for the intended instruments and $500–$1,000 capital level.
- Authentication and token-renewal operational burden.
- Market-data coverage, latency, rate limits, and historical-data quality.
- Order types, order preview, client order identifiers, and reconciliation behavior.
- Paper-to-live parity.
- Actual spread, slippage, rejection rate, and fill quality during the pilot.
- Ability to isolate strategies by account and enforce strategy-level budgets.

Schwab should **not** be selected if small-dollar fractional execution is essential and unsupported for the strategy, if recurring authentication prevents reliable unattended operation, or if its paper/live gap cannot be validated safely. In that case, Robinhood Agentic may remain the execution venue, or a separate API-first broker should be evaluated. The final broker is selected by measured execution and operational reliability, not by this proposal's initial preference.

## 4. Proposed system

```text
Broker APIs / approved aggregators / CSV imports
                    |
                    v
          Normalized portfolio store
                    |
          +---------+----------+
          |                    |
          v                    v
 Weekly analysis engine   Deterministic strategy engine
          |                    |
          v                    v
 AI-written report          Risk engine
                               |
                               v
                     Human approval gate
                               |
                               v
                         Broker adapter
                               |
                               v
                 Fills, reconciliation, alerts
```

### 4.1 Components

- `portfolio_monitor`: imports balances, positions, tax lots, orders, and transactions.
- `strategy_engine`: creates deterministic signals from explicitly versioned rules.
- `risk_engine`: accepts or rejects intended orders using immutable live-trading limits.
- `broker_adapter`: previews, submits, cancels, and reconciles orders.
- `reporter`: creates weekly portfolio and strategy reports.
- `audit_log`: records inputs, decisions, API responses, fills, overrides, and failures.
- `strategy_ledger`: maintains virtual sub-accounts for strategy budgets, cash, positions, costs, and P&L attribution.

### 4.2 Technology choices

- Python for the initial implementation.
- SQLite for the first local version; PostgreSQL only if operational needs justify it.
- `vectorbt` for fast research and parameter exploration.
- Robinhood Trading MCP for the isolated Agentic account.
- Schwab Trader API, optionally through `schwab-py`, behind an internal adapter.
- Fidelity Access-compatible aggregation or manual CSV export for Fidelity holdings.
- OS keychain or a dedicated secret manager for credentials and tokens.
- Email or Telegram for reports and urgent execution alerts.

The first version will remain a small modular application rather than a microservice or multi-agent system.

### 4.3 Cost model and budget

All prices below are planning figures checked against first-party pricing pages on **2026-08-21**. Broker, regulatory, data, and cloud prices may change and must be rechecked before live launch.

#### Published external costs

| Cost item | Current published price | Proposed treatment |
|---|---:|---|
| Schwab online U.S.-listed stocks and ETFs | $0 commission | Included as $0 explicit commission; spread, slippage, regulatory, and exceptional service fees still tracked |
| Schwab options | $0 base + $0.65 per contract | Outside initial scope |
| Schwab Trader API | No separate public price found | Do not assume permanent free/unlimited use; confirm approval, entitlements, limits, and any charges before selection |
| Fidelity online U.S. stocks and ETFs | $0 commission | Monitoring/manual-trade account only; implicit execution costs still tracked when evaluating recommendations |
| Robinhood listed stocks and ETFs | $0 commission | Used for the pilot; regulatory fees and implicit execution costs still apply |
| Robinhood Agentic MCP | No separate product price found on the official support pages reviewed | Reconfirm during onboarding; do not infer that future usage will remain free |
| Robinhood Gold | Optional $5/month or $50/year | Not included in the base plan unless a required feature justifies it; Agentic onboarding must be rechecked for any product-specific requirement |
| Robinhood ACATS transfer out | $100 | Avoid unnecessary transfers; fractional shares may be liquidated rather than transferred |
| SnapTrade Personal / Starter | $0 for up to 5 connected accounts | Preferred first option for personal multi-broker monitoring if approved connections cover the accounts; current guide lists Fidelity and Schwab as read-only |
| SnapTrade pay-as-you-go daily read-only | $1 per connected user/month; manual sync $0.05 | Optional fallback if the free personal plan is insufficient |
| SnapTrade pay-as-you-go real-time | $2 per connected user/month | Optional; trading support depends on the connected broker |
| Plaid Investments | Exact production price not publicly listed | Do not adopt until production access and an exact quote are obtained |
| Local execution on an existing computer | $0 incremental hosting | Default during research, read-only monitoring, and early paper trading |
| Small cloud VM | DigitalOcean from $4/month; AWS Lightsail public-IPv4 Linux from $5/month | Optional only after unattended operation is justified |
| Cloud secret storage | AWS Secrets Manager $0.40/secret/month plus API-call charges | Optional; 3–5 secrets imply roughly $1.20–$2/month before API-call charges |
| AI platform/API usage | Depends on the selected Codex/third-party plan; not priced in this proposal | Must have a separate monthly cap before unattended production use |

Primary pricing sources:

- Schwab pricing: https://www.schwab.com/pricing
- Fidelity commissions: https://www.fidelity.com/trading/commissions-margin-rates
- Robinhood trading fees: https://robinhood.com/us/en/support/articles/trading-fees-on-robinhood/
- Robinhood Gold: https://robinhood.com/us/en/support/articles/gold-overview/
- Robinhood transfer-out fee: https://robinhood.com/us/en/support/articles/transfer-stocks-out-of-your-robinhood-account/
- SnapTrade pricing: https://snaptrade.com/pricing
- Plaid Investments pricing notes: https://plaid.com/docs/investments/
- DigitalOcean Droplet pricing: https://www.digitalocean.com/pricing/droplets
- AWS Lightsail bundles: https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html
- AWS Secrets Manager pricing: https://aws.amazon.com/secrets-manager/pricing/

#### Recommended cash budget

| Stage | One-time cash cost | Recurring cash cost | Trading capital |
|---|---:|---:|---:|
| Read-only local MVP | $0 | $0/month if free connections work | $0 |
| Backtest and forward simulation | $0–$50 contingency for data/export tools | $0–$10/month | $0 |
| Human-approved Robinhood pilot | $0 | $0–$10/month | $250 |
| Limited unattended pilot | $0–$50 operational contingency | Approximately $1.20–$11/month before AI usage and trading losses | $250–$500 |
| Validated multi-strategy operation | Review required | $5–$50/month before premium market data | Up to $1,000 under this proposal |

The low end assumes an existing computer, free broker data, free SnapTrade Personal access, and no Robinhood Gold. A small hosted setup is expected to be roughly **$1.20–$11/month before AI usage, market-data upgrades, trading losses, tax, and regulatory charges**. Higher ranges in the table are **budget ceilings, not vendor quotes**. Any recurring software expense above $50/month requires explicit approval because it is economically disproportionate to a $500–$1,000 trading account.

#### Engineering effort estimate

Codex's planning estimate, excluding account-approval waiting time:

| Deliverable | Estimated effort |
|---|---:|
| Read-only data ingestion and first weekly report | 20–40 hours |
| Strategy ledger and multi-strategy attribution | 20–40 hours |
| First research-grade strategy and backtest | 20–40 hours |
| Risk engine, broker adapter, reconciliation, and fault tests | 40–80 hours |
| Paper runner, operating dashboard, alerts, and runbook | 20–40 hours |
| **Total to a controlled live pilot** | **120–240 hours** |

This is an effort estimate, not a promise or labor invoice. Calendar duration also depends on broker approvals, OAuth setup, data quality, and the required 8–12 week forward-validation period.

#### Trading-cost measurement

“$0 commission” must never be recorded as “zero cost.” Each fill will track:

- Explicit commission and regulatory fees.
- Bid/ask spread paid relative to the decision-time midpoint.
- Slippage between intended/reference price and actual fill.
- Partial-fill and cancel/replace effects.
- Subscription, data, and hosting costs allocated to the strategy.
- AI model/API usage allocated to the strategy or explicitly recorded as an account-level research cost.
- Tax impact as a separate reporting estimate, not as guaranteed tax advice.

For planning only, liquid ETF backtests will initially run sensitivity cases at **2, 5, and 10 basis points per round trip**. These are stress-test assumptions, not broker quotes. A strategy must remain acceptable at the conservative case before paper trading.

Monthly strategy net performance will use:

```text
net strategy P&L
  = realized P&L + unrealized P&L
    - explicit broker/regulatory fees
    - measured spread and slippage
    - allocated data/hosting/subscription costs
```

Shared infrastructure costs will default to allocation by each strategy's share of approved capital. The report will also show the raw unallocated account-level cost so allocation assumptions remain visible.

The ledger will keep at least these separate fields rather than mixing capital and cost: `capital_allocated`, `commissions`, `regulatory_fees`, `spread_slippage`, `data_cost`, `infrastructure_cost`, `AI_cost`, `tax_estimate`, and `strategy_pnl`.

## 4.4 Multi-strategy capital allocation and accounting

Every live or simulated order must belong to exactly one `strategy_id` and one brokerage `account_id`. Each strategy will have a separately approved capital budget, even when multiple strategies use the same brokerage account.

The system will distinguish these measures:

| Measure | Meaning |
|---|---|
| Allocated capital | Maximum capital approved for the strategy |
| Reserved cash | Cash held for open orders or expected strategy obligations |
| Deployed capital | Cash cost of currently open long positions |
| Gross exposure | Sum of absolute market value of strategy positions |
| Net exposure | Long market value minus short market value; initially long-only |
| Available capacity | Allocated capital minus deployed and reserved capital |
| Realized P&L | P&L from closed strategy lots |
| Unrealized P&L | Mark-to-market P&L of open strategy lots |
| Trading costs | Commissions, regulatory fees, spread/slippage estimate, and other attributable costs |
| Data and infrastructure cost | Strategy share of paid data, aggregation, hosting, secrets, backup, and alerting |
| AI cost | Strategy-attributable model/API usage; otherwise reported as unallocated research overhead |
| Net strategy value | Strategy cash plus marked positions after attributed costs |

Example allocation:

| Account | Strategy | Approved budget |
|---|---|---:|
| Robinhood Agentic | ETF mean reversion | $250 |
| Robinhood Agentic | Trend following | $250 |
| Schwab trading account | 做 T — QQQ | $300 |
| Schwab trading account | Sector rotation | $200 |

The allocation is a hard ceiling, not a performance target. A strategy may use less than its approved budget.

### Separate accounts versus shared accounts

Using a different brokerage account for each strategy provides the cleanest isolation, broker-native P&L, and simplest emergency shutdown. It also creates more account administration and may fragment small amounts of capital.

When strategies share one brokerage account, the broker normally reports only the account's net position. The internal `strategy_ledger` must therefore maintain virtual cash, lots, orders, fills, and P&L for each strategy. At every reconciliation point, the following invariant must hold:

```text
sum(strategy virtual cash and positions)
    = broker account cash and positions
      - explicitly recorded unallocated assets
```

Any unexplained difference blocks new orders.

### Initial conflict policy

To avoid ambiguous attribution, the initial system will enforce:

- One strategy owns a symbol within a shared account at a time.
- Two strategies in the same account may not hold opposing intentions in the same symbol.
- Orders may not be netted silently across strategies.
- Transfers of cash or positions between strategy ledgers require an explicit, logged allocation event.
- A fill is assigned to the originating strategy using the internal order ID; partial fills preserve the same attribution.
- Strategy-level and account-level risk limits both apply. The stricter limit wins.
- Each strategy has its own pause and kill switch; the account also has a global kill switch.

Allowing multiple strategies to trade the same symbol in one account is possible later, but requires a formally specified virtual-lot and fill-allocation policy. It is excluded from the first live release because a broker may net buys and sells while the internal strategies intend separate economic positions.

### Capital dashboard

The operating dashboard and weekly report will include:

- Capital allocated and actual capital deployed by account and strategy.
- Cash reserved for open orders.
- Remaining strategy capacity.
- Current positions and exposure by strategy.
- Gross and net P&L before and after trading costs.
- Turnover, fill quality, and estimated slippage.
- Drawdown and risk-limit utilization.
- Capital transfers and allocation changes during the reporting period.
- Unallocated account cash and assets.

No strategy may borrow unused budget from another strategy unless a new allocation event is explicitly approved and recorded.

## 5. Weekly portfolio report

The weekly report will contain:

- Account value, cash, positions, cost basis, and realized/unrealized P&L.
- Capital allocated, deployed, reserved, and available for every account and strategy.
- Exposure by account, security, sector, asset type, and investment theme.
- Concentration warnings and correlated positions.
- Upcoming earnings, dividends, and known corporate events.
- Available tax-lot data, long/short-term status, and possible wash-sale concerns.
- A decision list labeled `Hold`, `Watch`, `Reduce candidate`, or `Buy candidate`.
- Reasoning, risk factors, invalidation conditions, and missing-data warnings for every recommendation.
- Changes since the previous report.

Recommendations will not automatically trigger trades in Fidelity or long-term Schwab accounts.

## 6. Strategy scope

The first strategy will trade only highly liquid U.S. ETFs on hourly or daily signals. Candidate instruments include SPY, QQQ, IWM, and selected liquid sector ETFs. The exact universe will be fixed before backtesting.

A later 做 T strategy may operate on specifically designated trading lots. It must never sell protected long-term lots and must consider:

- Tax-lot identity and holding period.
- Wash-sale windows across relevant accounts.
- Earnings and corporate-event blackout windows.
- Unsettled funds and brokerage account restrictions.
- Maximum permitted turnover.

AI-generated or self-modifying strategy rules are outside the initial scope.

## 7. Risk policy

### 7.1 Instrument and account limits

- Long equities and unleveraged ETFs only.
- Approved-symbol allowlist required.
- No options, shorts, crypto, leveraged/inverse ETFs, or low-priced securities initially.
- Trades may occur only in the dedicated experimental account until production approval.

### 7.2 Position and loss limits

- Initial live funding: **$250**.
- Maximum eventual experimental funding without a new review: **$1,000**.
- Maximum position: **20% of experimental account equity**.
- Each strategy also has an explicit dollar budget and a maximum strategy exposure. Account and strategy limits are evaluated together.
- Maximum planned loss per trade: **0.5% of account equity**.
- Daily realized and unrealized loss stop: **1%**.
- At **10% total drawdown**: block new positions and require review.
- At **15% total drawdown**: close strategy positions where orderly execution is possible and disable live trading.
- Maximum three new orders per day.
- Limit orders by default; any use of market orders must be explicitly justified by the strategy.

### 7.3 Operational controls

- Unique client order ID and idempotency protection for every order.
- Mandatory `strategy_id` and `account_id` attribution before an order can pass risk checks.
- Pre-trade balance, buying-power, position, market-hours, and stale-data checks.
- No new order while an earlier order has an unknown state.
- Explicit handling of partial fills, rejections, cancel/replace, timeouts, and reconnects.
- Broker reconciliation before and after each trading session.
- Reconcile the sum of strategy virtual ledgers against the broker's account-level cash and net positions.
- Automatic stop on stale data, authentication failure, inconsistent positions, or unexpected holdings.
- Human-accessible kill switch.
- Live risk configuration cannot be modified by the AI reporting layer.

These limits are provisional. They assume the experimental capital can tolerate a 15% project stop-loss and that the user does not require leverage.

## 8. Validation and rollout

### Phase 0 — Account and security setup

- Open a dedicated Robinhood Agentic account.
- Register a Schwab individual developer application if Schwab API access is desired.
- Choose a Fidelity read-only method.
- Configure MFA, credential storage, account allowlists, and emergency access.

**Exit gate:** All connected accounts and permissions are documented; no production credentials are stored in source control.

### Phase 1 — Read-only monitoring

- Normalize data from available accounts.
- Establish strategy budgets and test the virtual sub-account ledger with synthetic deposits, orders, partial fills, fees, and capital transfers.
- Generate and manually review the first weekly report.
- Add missing-data and stale-data detection.
- Verify totals against brokerage statements.

**Exit gate:** Positions, balances, transactions, and strategy allocations reconcile across at least four consecutive weekly reports.

### Phase 2 — Research and backtesting

- Specify one strategy before examining final performance.
- Include splits, dividends, realistic spreads, slippage, delayed fills, and transaction costs.
- Separate training, validation, and untouched out-of-sample periods.
- Run walk-forward and parameter-sensitivity tests.
- Compare against buy-and-hold SPY and cash/T-bill-like baselines.

**Exit gate:** Positive out-of-sample results after costs, acceptable drawdown, no dependence on a tiny number of trades, and stable neighboring parameters.

### Phase 3 — Forward simulation

- Run the same strategy code against live data without placing orders.
- Then run paper trading for 8–12 weeks.
- Test disconnects, stale prices, duplicate callbacks, rejected orders, partial fills, and token expiration.

**Exit gate:** No unauthorized or duplicate orders in fault tests; paper results are explainable and consistent with the modeled strategy.

### Phase 4 — Human-approved live pilot

- Fund the isolated account with $250.
- Require human approval for the first 20 intended trades.
- Compare expected versus actual spread, slippage, fill time, and P&L.

**Exit gate:** At least 20 correctly executed and reconciled trades with no control failures.

### Phase 5 — Limited automation

- Permit unattended execution only for the approved strategy and symbol list.
- Continue daily reconciliation and weekly review.
- Require at least 50 total trades, eight weeks of operation, and no operational incidents before increasing capital to $500.
- Require six months of acceptable live behavior and a formal review before increasing capital to $1,000 or enabling Schwab live orders.

## 9. Evaluation criteria

### 9.1 Engineering success

- Zero unauthorized-symbol or unauthorized-account trades.
- Zero duplicate live orders.
- Every trade is reproducible from stored inputs and strategy version.
- Every dollar of deployed or reserved capital and every open position is attributable to one strategy or explicitly marked unallocated.
- Positions reconcile with the broker.
- Sum of virtual strategy ledgers reconciles with each shared brokerage account.
- Risk limits work during injected failures.
- Paper/live differences are measured rather than ignored.

### 9.2 Strategy success

- Positive out-of-sample return after modeled costs.
- Live execution remains within the slippage assumptions.
- Drawdown stays inside the approved limit.
- Results are not dominated by a few outlier trades.
- Risk-adjusted results justify the complexity relative to a passive benchmark.

### 9.3 Mandatory shutdown conditions

- Any order in an unauthorized account or instrument.
- Any order without valid strategy attribution or beyond its strategy capital budget.
- Any breach of a hard loss or position limit.
- Two duplicate-order incidents, or one incident with material exposure.
- Unexplained position mismatch.
- Persistent live underperformance relative to the validated model.
- Repeated parameter changes intended only to preserve attractive backtests.

## 10. Major trade-offs

| Decision | Benefit | Cost / risk |
|---|---|---|
| Robinhood Agentic for pilot | Fast official AI connection and isolated write account | Newer product, AI-platform data exposure, limited production history |
| Schwab for later deterministic trading | Conventional API and portable execution architecture | OAuth/token maintenance and imperfect paper-to-live parity |
| Fidelity remains read-only | Protects long-term assets and avoids unsupported automation | Manual execution remains necessary |
| Hourly/daily rather than HFT | Lower infrastructure and trading-cost burden | Fewer signals and slower feedback |
| Human approval first | Detects design and interpretation errors early | Slower experimentation |
| Simple rules before ML | Easier audit, validation, and failure diagnosis | May miss complex predictive relationships |

## 11. Security and privacy

- Never store brokerage passwords, OAuth tokens, private keys, account exports, or tax documents in Git.
- Use least-privilege connections and dedicated experimental accounts.
- Review what account data an AI platform can access before authorization.
- Treat logs and reports as sensitive financial records.
- Encrypt backups and define a retention policy.
- Revoke all tokens immediately if an AI platform, machine, or credential is compromised.

## 12. Regulatory and tax considerations

- Brokerage implementation of U.S. intraday margin rules must be confirmed before enabling frequent same-day trading.
- Cash accounts must respect settlement and good-faith funding rules.
- Frequent trading may create short-term gains and wash-sale complications.
- The system must not infer that a broker-provided commission rate represents the full cost of trading; spreads, slippage, regulatory fees, and taxes remain relevant.
- This proposal is for the owner's accounts only. Managing or advising other people's accounts would require a separate legal and compliance review.

## 13. Initial deliverables

1. Configuration and threat model.
2. Read-only broker adapters and normalized schema.
3. Strategy capital ledger and account/strategy allocation dashboard.
4. Weekly portfolio report generator.
5. One documented ETF strategy specification.
6. Reproducible backtest with cost and robustness analysis.
7. Risk engine and fault-injection test suite.
8. Paper/forward-trading runner.
9. Human-approved live pilot.
10. Operations runbook covering start, stop, allocation changes, reconciliation, credential renewal, and incidents.

## 14. Decision

Proceed with monitoring and simulation first. Use Robinhood Agentic only as the isolated small-capital pilot. Keep Fidelity read-only. Do not enable Schwab live orders until the complete strategy, risk, reconciliation, and pilot gates have passed.

## References

- Robinhood Agentic Trading overview: https://robinhood.com/us/en/support/articles/agentic-trading-overview/
- Robinhood agent trading tools: https://robinhood.com/us/en/support/articles/trading-with-your-agent/
- Robinhood third-party connection policy: https://robinhood.com/us/en/support/articles/third-party-connections/
- Schwab trading platforms: https://www.schwab.com/trading
- Schwab extended-hours trading: https://www.schwab.com/stocks/extended-hours-trading
- Fidelity fractional shares: https://www.fidelity.com/trading/fractional-shares
- Fidelity Access and data security: https://www.fidelity.com/security/fidelity-access-data-security
- FINRA intraday margin overview: https://syndication.finra.org/content/understanding-new-intraday-margin-requirements
- FINRA frequent intraday trading overview: https://syndication.finra.org/content/frequent-intraday-trading-understanding-basics
- IRS Publication 550: https://www.irs.gov/publications/p550
