# Codex 调研备忘录：券商与交易自动化成本

> 调研日期：2026-08-21  
> 口径：仅使用服务提供方的一手官方页面。金额均为美元。价格和产品能力可能变化，正式接入前须再次确认。

## 结论

- 对美国上市股票和 ETF，Schwab、Fidelity、Robinhood 的线上佣金都可以是 **$0**；这不代表交易总成本为零，仍有买卖价差、滑点、价格冲击、监管费、税务成本和策略亏损。
- **Schwab 是中频/做 T 的 production candidate，不是默认胜者。** 原因是它有面向程序开发的官方 Trader API，能把行情、账户、固定规则、风控、下单和对账连成确定性流程；其官方说明明确列出实时/历史行情、回测、自动化工作流及股票/ETF/期权下单能力。[Schwab Trader API 用途](https://www.schwab.com/learn/story/ways-ai-trading-tools-help-increase-efficiency)
- Robinhood Agentic 更适合独立的 $500–$1,000 AI 实验账户，但它把第三方 AI agent 放在交易执行路径中，是新产品，且 agent 可以在被授权后不逐笔确认地下单；当前只支持 long equities/options，limited margin 可复用未结算资金但不能借款。[Robinhood Agentic 概览](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)、[使用 agent 交易及限制](https://robinhood.com/us/en/support/articles/trading-with-your-agent/)
- Fidelity 适合长期核心账户及只读周报。Fidelity Access 是用户授权的数据共享连接，不等于向个人开发者开放的零售交易 API；Fidelity 还明确要求聚合商从 screen scraping 转向安全连接。因此 proposal 不应计划用 Fidelity 网页自动化下单。[Fidelity Access](https://www.fidelity.com/security/fidelity-access-data-security)、[Fidelity 关于 screen scraping 的公告](https://newsroom.fidelity.com/pressreleases/fidelity-takes-steps-to-address-screen-scraping/s/2f33bc18-f16d-4b66-9868-626ada9ba32b)

## 1. 券商明示费用

| 项目 | Schwab | Fidelity | Robinhood |
|---|---:|---:|---:|
| 开户/维护零售经纪账户 | $0 | 无最低开户额/零售账户费为 $0 | $0 |
| 在线美国上市股票/ETF | $0 | $0 | $0 commission |
| 标准期权 | $0 base + $0.65/张 | $0 base + $0.65/张 | 股票/ETF 期权 commission-free；指数期权另有合约、交易所及监管费 |
| 经纪人协助股票/ETF | $25 service charge | 依渠道定价，不用于本项目 | 不用于本项目 |
| 转出 ACATS | 以正式 fee schedule 为准 | 以正式 fee schedule 为准 | $100/每个转出账户（部分或全部） |
| 自动交易/API 独立订阅费 | 官方公开页面未列单独 Trader API 价格，不能据此承诺永久免费 | 无面向本方案的个人交易 API | 官方 Agentic 页面未列独立 MCP/Agentic 价格，不能据此承诺永久免费 |

来源：[Schwab 定价](https://www.schwab.com/pricing)、[Schwab Trading](https://www.schwab.com/trading)、[Fidelity 佣金与费用](https://www.fidelity.com/trading/commissions-margin-rates/)、[Robinhood 交易费用](https://robinhood.com/us/en/support/articles/trading-fees-on-robinhood/)、[Robinhood 转出](https://robinhood.com/us/en/support/articles/transfer-stocks-out-of-your-robinhood-account/)

Robinhood 当前还公开了以下细项：

- Gold 是可选订阅，**$5/月或 $50/年**，不是股票/ETF 零佣金的前提。[Robinhood Gold](https://robinhood.com/us/en/support/articles/gold-overview/)
- 自 2026-04-04 起，其披露的 SEC 卖出费率为每 $1,000,000 本金 $20.60；名义金额不超过 $500 的股票卖出不向用户转嫁该费。
- 2026 年股票卖出 TAF 为 $0.000195/股；卖出不超过 50 股时 Robinhood 不向用户收取。ADR 还可能有存托费。
- Crypto 若使用 exchange routing，费用档位为 **0.00%–0.95%**；API v2 成交会计入交易量，当前在 maker/taker 全面推出前按 taker rate 收费。[Robinhood crypto fee tiers](https://robinhood.com/us/en/support/articles/crypto-fee-tiers/)

## 2. 数据聚合成本

### SnapTrade

- Personal 当前为 **$0/月**，适合本人账户的只读周报和个人工具。[SnapTrade Personal](https://snaptrade.com/personal)
- 商业版 Starter 为 $0、最多 5 个 connected accounts；Pay-as-you-go real-time 为 **$2/connected user/月**，含可用券商的 trading；daily read-only 为 **$1/connected user/月**，手动同步 **$0.05/次**。[SnapTrade pricing](https://snaptrade.com/pricing)
- 但当前 Broker Access Guide 将 **Fidelity 和 Schwab 都列为 Read Only**；所以 SnapTrade 可作为多账户汇总层，却不能替代 Schwab 直接 Trader API 的生产下单层。[SnapTrade Broker Access Guide](https://docs.snaptrade.com/docs/broker-access-guide)

### Plaid Investments

- Investments 按 connected Item 的 subscription 模型计费，Investments Refresh 按请求计费；精确生产价格不公开，要申请 Production 或联系 sales。[Plaid Investments](https://plaid.com/docs/investments/)、[Plaid billing](https://plaid.com/docs/account/billing/)
- 2026-04-15 起符合条件的新团队可申请免费 Trial，最多 10 个 Production Items，并含 Investments/Refresh；Fidelity、Schwab 连接可能仍需机构级额外审批。[Plaid pricing plans](https://support.plaid.com/hc/en-us/articles/16110502116887-What-are-Plaid-s-prices-and-pricing-plans-and-how-do-they-differ)

因此个人 pilot 首选预算是 **SnapTrade Personal $0**；Plaid 只作为备选，不能在取得 production 报价前填一个虚构月费。

## 3. 托管与基础设施成本

第一阶段可以在本人电脑上定时运行，增量托管费为 **$0**。需要 24/7 运行时，可选：

- AWS Lightsail 常驻 Linux VM：公开入门档约 **$5/月**，符合条件的实例前三个月免费。[AWS Lightsail pricing](https://aws.amazon.com/lightsail/pricing/)
- Serverless 小系统：Lambda 每月有 100 万请求和 400,000 GB-s 免费额度；EventBridge Scheduler 每月有 1,400 万次免费调用；Secrets Manager 为 **$0.40/secret/月 + $0.05/10,000 API 调用**。[AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)、[EventBridge pricing](https://aws.amazon.com/eventbridge/pricing/)、[Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/)

对于每小时检查、每周生成报告的个人系统，合理的基础云预算是 **$0–$5/月**，另加约 **$1.20–$2/月** 的 3–5 个 secrets（若采用 Secrets Manager）。日志超额、短信、商业行情和备份另计。

## 4. Pilot 月度预算建议

| 成本项 | 最小本地方案 | 推荐小型生产方案 |
|---|---:|---:|
| Schwab/Fidelity/Robinhood 股票 ETF 佣金 | $0 | $0 |
| Schwab Trader API | 未发现公开独立订阅价；接入前确认 | 同左 |
| Robinhood Agentic MCP | 未发现公开独立产品价；接入前确认 | 同左 |
| Robinhood Gold | $0（不用） | $0；确需权益时 $4.17/月（按 $50 年付折算） |
| 多账户只读聚合 | SnapTrade Personal $0 | SnapTrade Personal $0；商业化后另算 |
| 运行环境 | 本地 $0 | $0–$5/月 |
| 密钥托管 | 本地系统 Keychain $0 | 约 $1.20–$2/月 |
| AI 平台/API | 不计入；依现有 Codex/第三方 AI 套餐 | 单列用量上限，取得实际报价后填入 |
| 合计（不含 AI、监管费、税和交易损耗） | **约 $0/月** | **约 $1.20–$11/月** |

这里的 **$500–$1,000 是策略资本，不是软件成本**。建议会计账本分开记录：`capital_allocated`、`commissions`、`regulatory_fees`、`spread_slippage`、`data_cost`、`infrastructure_cost` 和 `AI_cost`，避免把本金、费用和亏损混在一起。

## 5. 为什么 Schwab 只是 production candidate

### 支持它的理由

1. **官方直接交易接口。** Schwab 官方明确称 Trader API 可接实时/历史行情、账户信息、第三方 AI/量化模型，并能下股票、ETF、期权订单及回测想法。[Schwab Trader API](https://www.schwab.com/learn/story/ways-ai-trading-tools-help-increase-efficiency)
2. **确定性执行更容易。** 策略信号、资金配额、幂等订单、最大亏损和 kill switch 可以全部写成代码，不必让 LLM 在每次交易时解释自然语言。
3. **生产运维边界清楚。** 可以对订单提交、查询、部分成交、撤单、账户对账分别测试，出现异常时也更容易重放审计。
4. **活跃交易配套。** thinkorswim 免费随账户提供；Schwab 官方还列出 paper trading 和 1,100+ 标的 24/5 交易。但 paperMoney 与 Trader API 实盘不可假设为同一执行环境，必须另外做接口级模拟和小额验证。[Schwab Trading](https://www.schwab.com/trading)

### 不直接选定它的理由

1. **小额资金不一定最优。** Schwab 官方比较页将其 fractional share 范围列为 S&P 500，而 Fidelity/Robinhood 的小额碎股更灵活；$500–$1,000 账户会受仓位粒度影响。[Fidelity 对交易与碎股的官方比较](https://www.fidelity.com/why-fidelity/trading)
2. **API 成本与限制需实测。** 公开页面未提供独立 Trader API 价目，也不能从“交易平台免费”推导出所有 API 行情、调用量或未来使用都免费。
3. **没有证据证明收益更高。** API 工程质量只降低操作风险，不创造策略 alpha。
4. **Robinhood Agentic 上线更快。** 它提供专门隔离账户，并原生暴露 agent 工具；若目标是快速做 $250–$1,000 的受控 AI 实验，Robinhood 可以先跑。

所以决策门槛应写成：**Schwab 只有在 Trader API 开通成功、认证/限流稳定、模拟与实盘订单语义验证通过、碎股粒度满足策略、且无未接受的附加费用后，才从 candidate 晋级为 production broker。**

