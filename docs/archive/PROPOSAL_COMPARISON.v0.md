# Trading proposal 研究对比(v0,研究过程记录)

> **Status: 参考材料,非最终方案 —— 最终方案见 [/PROPOSAL.md](PROPOSAL.md)。本文件内容(含"单一 active 策略""Alicia 入职 xAI 后零维护"等结论)未经 Alicia 在本对话内确认,如与 /PROPOSAL.md 冲突,以 /PROPOSAL.md 为准。**
> 日期：2026-08-21  
> 范围：`Claude/PROPOSAL.claude.md` 与 `Codex/TRADING_AUTOMATION_PROPOSAL.md`  
> 支撑材料：`Claude/CLAUDE.md` 与 `Codex/BROKER_COST_RESEARCH.md`

## 执行结论

**不建议原样选任何一份。新增的最高优先级约束是：系统必须简单、维护成本低，并能在 Alicia 入职 xAI、几乎没有维护时间后安全地长期运行。**

因此最佳方向调整为：**以 Claude 版的“学习不可信 agent + 确定性风控”作为研究目标，但把长期运行版本缩减为单 agent、单 broker、单策略、每日一次；采用 Codex 版的对账、幂等和失败即停机机制。3 analyst + PM 仅作为以后有时间时的离线实验，不进入首个长期运行版本。**

原因是两份提案实际上优化了不同目标：

- Claude 版明确把项目定位为学习“不可信 LLM 决策层 + 确定性代码风控层”，教育价值优先于短期收益（`Claude/PROPOSAL.claude.md:8-15`）。它的三 analyst + PM 架构因此与目标一致（`Claude/PROPOSAL.claude.md:28-32,41-72`）。
- Codex 版把首版定位为简单、可解释、确定性的 ETF 策略，明确不做 multi-agent（`Codex/TRADING_AUTOMATION_PROPOSAL.md:24-33,109-130,317-329`）。它不完全满足学习 agent system 的核心目标，却是更成熟的实盘工程设计。

## 不可协商的运行约束

1. **无人维护是正常状态。** 系统不能依赖每日查看日志、手动刷新 token、修 prompt 或处理普通异常。
2. **安全失败。** 数据过期、模型/API 失败、订单状态未知或对账不一致时，默认不下新单并发送一条告警；不得自动反复重试下单。
3. **单一执行路径。** v1 只保留一个交易 broker、一个账户、一个调度任务和一个 active 策略；可以注册多个策略 adapter，但其他策略只能处于 shadow 或 disabled 状态。
4. **低变更频率。** universe、模型、prompt、策略参数和风险参数都版本化；没有人工批准不得自动修改。
5. **维护预算。** 目标为正常月份每月人工维护不超过 30 分钟；若系统持续超过该预算，应削减功能而不是增加运维组件。
6. **无需在线 dashboard。** 使用 broker 原生账户界面、结构化日志和失败告警；不自建需要持续维护的前端、数据库服务或微服务。

## 核心对比

| 维度 | Claude 版 | Codex 版 | 评估 |
|---|---|---|---|
| 真实目标 | 学习 multi-agent 与 LLM safety | 构建可运营的系统化交易与组合监控 | 学习目标取 Claude，但长期运行架构必须按低维护约束缩减 |
| 决策层 | 3 analyst + PM LLM | 版本化确定性策略；AI 主要写报告 | 长期 v1 采用一个 active LLM 策略 + 可插拔策略 seam；其他策略做 shadow 对比 |
| 可评估性 | 记录 score/confidence，可做 calibration | 策略固化、回放、样本外与敏感性测试 | 应合并：必须有确定性 baseline 才能判断 agent 是否带来价值 |
| 风控 | 简洁、硬约束，20% 单票、3 笔/日、-5% 日损、-15% 回撤 | 多层风控，加入 0.5% 计划单笔损失、1% 日损、10% 暂停新仓、15% 停机 | Codex 更完整；Claude 的 5% 日损对小额 pilot 过宽 |
| 执行安全 | 可插拔 adapter，记录裁剪/拒绝 | 唯一 client order ID、幂等、unknown-state 阻断、partial fill、前后对账、stale-data 停机 | Codex 明显更强；这些是上实盘前的必要项 |
| 验证路径 | 搭建 → 8 周 paper → $500–1,000 live | 只读对账 → backtest → 8–12 周 forward/paper → $250 人工确认 → 限制自动化 | 资本起点取决于风险偏好；Alicia 已明确接受直接以 $500–1,000 实盘 |
| 实盘 gate | 8 周、MDD <15%、无重大 bug；明确不证明 alpha | 回测、样本外、故障注入、前 20 笔人工确认、至少 50 笔后才增资 | 合并两者的工程 gate；不把 $250 起步或前 20 笔人工确认设为硬门槛 |
| 账本/对账 | 未详述 | 每笔订单强制 `strategy_id`/`account_id`，虚拟子账本与 broker 对账 | 若首版只有一个 agent 策略，可简化实现，但字段和对账不能删 |
| 监控报告 | 只报事实，不给买卖建议 | 含 Hold/Watch/Reduce/Buy candidate，但不自动交易长期账户 | Claude 边界更干净；建议首版采用 fact-only |
| 范围 | 相对聚焦，但 4 次 LLM 调用链和多类数据源仍增加维护面 | 包含多券商、多策略账本、税务、dashboard，预估 120–240 小时 | 两者都要缩减；v1 只允许一个 active 策略和一个 broker，但接口允许切换策略 |
| 运行成本 | LLM 上限 $30/月 | 基础设施约 $1.20–$11/月，AI 另计 | 口径不同；统一成“基础设施与 AI 分账，总运行上限 $30/月” |

## Claude 版评估

### 优点

1. **目标、架构、实验指标一致。** 三个独立 analyst 的 score 和 confidence 全部落盘，可以分别计算方向准确率、Brier score 和 calibration（`Claude/PROPOSAL.claude.md:29-32,67-72`）。
2. **安全边界正确。** LLM 不能 override 硬风控，越权意图也会被记录（`Claude/PROPOSAL.claude.md:55-58,71-86`）。
3. **范围足够聚焦。** 每日决策、固定白名单、不做 HFT，与小资金和全职时间约束相符（`Claude/PROPOSAL.claude.md:23-37`）。
4. **对样本量认识准确。** 它明确说 8 周 paper 只是工程 sanity check，不能证明 alpha（`Claude/PROPOSAL.claude.md:90-100`）。

### 主要缺口

1. **没有 deterministic baseline。** 若 agent 系统产生收益或损失，无法区分是策略信号、LLM 角色分工、PM 聚合还是市场 beta 导致。
2. **缺少 backtest / walk-forward / untouched out-of-sample 门槛。** 仅靠 8 周 paper 既不能证明 alpha，也很难覆盖多市场状态。
3. **运维风控不足。** 未规定幂等 key、订单 unknown state、部分成交、数据过期、鉴权失败、开盘前对账和故障注入。
4. **$500–1,000 的实盘起点不是缺陷。** Alicia 已明确接受 paper 后直接使用这笔资本，因此无需强制 $250 起步、前 20 笔人工确认或逐级增资。这里仍应保留工程 gate，并明确这笔实验资本可以全部损失（`Claude/PROPOSAL.claude.md:95-103`）。
5. **-5% 日损阈值过宽。** 对 $500–1,000 教学 pilot，一天容许损失 5% 与“小 blast radius”不一致（`Claude/PROPOSAL.claude.md:76-84`）。
6. **关键策略语义未定义。** `direction/score/confidence` 如何转换为 target position/order、信号的时间 horizon、标签和数据截止时间都未规定。

## Codex 版评估

### 优点

1. **实盘运维设计完整。** 幂等、对账、部分成交、鉴权失败、数据过期和 unexpected holdings 都有明确停机语义（`Codex/TRADING_AUTOMATION_PROPOSAL.md:353-364`）。
2. **验证阶梯成熟。** 先对账，再样本外研究，再 forward/paper，再人工确认小额 live，最后才限制自动化（`Codex/TRADING_AUTOMATION_PROPOSAL.md:368-420`）。
3. **成本口径正确。** 明确“$0 commission ≠ 零成本”，要记录 spread、slippage、部分成交、订阅和 AI 成本（`Codex/TRADING_AUTOMATION_PROPOSAL.md:197-223`）。
4. **账本可审计。** `strategy_id`/`account_id`、虚拟 cash/lots/orders/fills/P&L 以及 broker 对账不变式都已明确（`Codex/TRADING_AUTOMATION_PROPOSAL.md:225-299`）。
5. **broker 决策更谨慎。** Schwab 只是 candidate，需用实测认证、碎股、数据、限流、订单和成交质量后才能晋级（`Codex/TRADING_AUTOMATION_PROPOSAL.md:44-81`）。

### 主要缺口

1. **与声明的学习目标偏离。** 它主动排除 multi-agent，让 AI 退到报告层，几乎不会产生想要观测的“不可信 LLM 决策层”数据。
2. **v1 范围过大。** 多券商、多策略虚拟账本、税务 lot、周报、dashboard 和 live adapter 一起上，对小额教学 pilot 不成比例。文档自己估计 120–240 小时（`Codex/TRADING_AUTOMATION_PROPOSAL.md:182-195`）。
3. **策略仍然空缺。** 首个 ETF 策略、参数、信号频率和市场数据授权都尚未决定（`Codex/TRADING_AUTOMATION_PROPOSAL.md:317-320`）。
4. **部分 gate 仍需量化。** 例如“acceptable drawdown”、“stable neighboring parameters”、“persistent underperformance”没有预注册阈值（`Codex/TRADING_AUTOMATION_PROPOSAL.md:389-405,443-451`）。
5. **周报中 Buy/Reduce candidate 与 fact-only 边界冲突。** 若周报用于长期账户，建议首版只报事实、暴露和异常（`Codex/TRADING_AUTOMATION_PROPOSAL.md:301-315`）。

## 官方资料核验

1. **Robinhood Agentic 的专用账户和下单预览有官方依据。** Robinhood 说明 agent 可读取所有 Robinhood 账户数据，但只能在 Agentic 账户下单；官方工具列表包含 `review_equity_order`、`place_equity_order` 和 `cancel_equity_order`。用户也可以允许 agent 不经逐笔确认直接下单。来源：[Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)、[Trading with your agent](https://robinhood.com/us/en/support/articles/trading-with-your-agent/)。
2. **未找到 Claude 所称“现成 kill switch”的对等官方产品说明。** 官方说明确认可取消 pending order，但同时警告 agent 可能“difficult to monitor or stop in real time”。因此 kill switch 应由项目实现并实测，不应当成 broker 已验证能力。
3. **Alpaca paper 可用，但不等于 live parity。** Alpaca 官方说明 paper 不模拟市场冲击、订单信息泄露、延迟滑点、队列位置、价格改善、监管费和股息；paper-only 账户还只有 IEX 数据权限。来源：[Alpaca Paper Trading](https://docs.alpaca.markets/us/docs/paper-trading)。
4. **“Alpaca 是唯一有完整 paper 环境的主流路径”是未证实的过度表述。** 当前证据只能支持“Alpaca 提供免费、API 规格高度相似的 paper 环境”，不能支持“唯一”。这个词应删除。
5. **GitHub Actions 只适合非精确定时的收盘后批处理。** GitHub 官方明确说 scheduled event 可在高负载时延迟，负载足够高时甚至可能丢弃 queued jobs。因此它可生成收盘后信号/周报，但不应直接承担“次日开盘时刻”的精确下单。来源：[GitHub Actions troubleshooting](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows)。
6. **Robinhood 支持多个普通投资账户，但尚不能确认多个 Agentic 账户或逐 agent 的独立写权限。** Robinhood 当前允许每位美国用户最多 10 个 self-directed individual investing accounts，并明确可用不同账户分隔策略；但 Agentic 文档只确认 agent 能读取所有 Robinhood 账户、只能在“your Robinhood Agentic account”中下单。官方页面没有明确说明可以创建多个 Agentic 账户，或将不同 MCP/agent 分别绑定到不同写账户。因此 v1 不能依赖“每个 LLM strategy 一个 Robinhood Agentic account”，必须在开户流程中实测或向 Robinhood Support 确认。来源：[Multiple investing accounts FAQ](https://robinhood.com/us/en/support/articles/multiple-investing-accounts-faq/)、[Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)。

## 推荐的混合方案

### 长期运行目标架构

```text
每日一次 scheduled workflow
        |
        v
单一官方数据源 / 单一 broker
        |
        +----> deterministic baseline（只记录，不交易）
        |
        v
Strategy module（选择一个 active adapter）
        |
        +----> LLM strategy A / LLM strategy B / future multi-agent
        |
        v
确定性 risk + reconciliation
        |
        v
同一个 broker adapter
        |
        +----> 成功：静默记录
        +----> 失败：停止新单 + 单条告警
```

默认不设 PM agent，不做 analyst 辩论，不上 PostgreSQL、微服务、自建 dashboard、多策略虚拟账本或多个 live broker。只要一个 Python package、一个 workflow、一个配置文件和一套测试。策略可以替换，但执行链不分叉。

### LLM 策略 seam

不同 LLM 交易策略统一实现一个小 interface：

```python
class TradingStrategy(Protocol):
    def propose(self, context: DecisionContext) -> StrategyProposal: ...
```

`DecisionContext` 由系统统一构建，包含 `as_of`、白名单、市场数据快照、当前仓位、可用资金和允许的数据 profile。`StrategyProposal` 只包含：

```text
strategy_id
strategy_version
model_id
prompt_version
as_of
target_weights
confidence
rationale
```

interface 的完整约束：

- 策略只能返回目标仓位，不能访问 broker 凭证，也不能直接创建、修改或取消订单。
- 所有策略使用相同的 `as_of` 和输入快照，避免不同数据截止时间造成不可比较或 look-ahead。
- 输出 schema 校验失败、超时或模型调用失败时，本轮策略结果作废，不下新单。
- risk module 将目标仓位转换为合法订单；broker adapter 只接受 risk module 的输出。
- `strategy_id + strategy_version + as_of` 进入决策日志和 client order ID，保证可追踪与防重复。

策略注册表只需要三种运行状态：

| 状态 | 行为 |
|---|---|
| `active` | 允许其 proposal 经过风控后进入执行；v1 同时最多一个 |
| `shadow` | 使用同一输入运行并记录结果，但永不下单 |
| `disabled` | 不运行 |

这样可以低成本比较不同 LLM 策略：把新策略先设为 `shadow`，观察后通过一次配置变更将它和当前 `active` 策略互换。因为 v1 不允许多个策略同时持有真实仓位，所以无需维护复杂的虚拟子账本或策略间成交分配。

若 Robinhood 后续明确支持多个 Agentic 账户及账户级写权限，`active` 限制可以从“全系统最多一个”放宽为“每个账户最多一个”，并在配置中固定 `strategy_id -> account_id`。在此之前，不允许策略自行选择账户，也不根据 prompt 中的账户名称路由订单。

### v0：明确实验合同

- 首版只启用 **1 个 active LLM strategy + 1 个 shadow deterministic baseline**。策略 seam 从第一天就是真实 seam，因为至少已有两个 adapter；不提前实现三 analyst + PM。
- 固定信号 horizon、数据 cutoff、标签、score-to-position 函数、交易 universe 和评估指标。
- 验收：同一输入可重放，没有 look-ahead leakage，所有模型输出符合 schema。

### v1：只读 + shadow mode

- 优先实现 market-data snapshot、decision log、risk decision log、cost log 和每日对账。
- active LLM strategy 与 shadow baseline 使用同一快照产生 proposal，但不下单。
- 加入 Codex 的 stale data、重复事件、partial fill、timeout、reconnect 与 token expiry 故障测试。
- 所有普通成功运行保持静默；仅在跳过运行、对账失败或风控停机时告警，避免形成需要每天查看的运维负担。

### v2：Alpaca paper

- 连续 8–12 周，但同时保留更长历史 backtest / walk-forward 结果。
- 不只看 P&L；评估各策略的 direction、confidence calibration、相对 deterministic baseline 的增益、换手、滑点敏感性和风控拦截率。
- 在仿真中额外加入 paper 没有覆盖的 2/5/10 bps 成本压力测试。

### v3：$500–1,000 隔离账户 live

- Alicia 已接受直接投入 $500–1,000，不要求前 20 笔逐笔人工确认；仍需开启交易通知和人工可用的紧急停机路径。
- 日损建议从 **1%** 起步，10% 回撤禁止新仓并人工复核，15% 停机；保留 20% 单标的上限和 3 笔/日上限。
- 每笔订单必须有 client order ID、strategy ID、input snapshot、model/prompt version、risk result 和 fill reconciliation。
- workflow 漏跑时不补单；恢复后等待下一个正常周期，避免无人值守时的追赶执行和重复下单。

### v4：扩大范围

- 初始 live 可以自动执行，但任何重复下单、风控穿透、静默失败或无法解释的对账差异都立即停机。
- 运行一段预先约定的观察期且无运维事故后，再扩大标的数量、决策频率或券商范围。
- 在 Alicia 没有稳定维护时间期间，默认**不扩大**到 Schwab live、多策略虚拟账本、盘中频率或 multi-agent；它们扩大的是维护面，而不只是资本风险。

## 最终取舍

**应采纳 Claude 的：**

- 项目的学习定位；
- analyst 输出的可观测 schema，并将其推广为所有 LLM 策略共享的 `StrategyProposal`；
- 代码风控高于 prompt 的原则；
- 固定白名单、每日低频、fact-only 周报；
- paper gate 不证明 alpha 的清醒边界。

**应采纳 Codex 的：**

- deterministic baseline 与样本外验证；
- 幂等、partial fills、stale data、对账和故障注入；
- 回测、故障注入和渐进扩大系统权限；资本可按 Alicia 的风险偏好直接使用 $500–1,000；
- 更严格的日损阈值和分层回撤处置；
- 真实交易成本记录和 broker 候选的实测门槛。

**应推迟的 Codex 范围：**

- 多 broker live 执行；
- 多策略共享账户的完整虚拟分账；
- 税务 lot 自动化和复杂 dashboard；
- Schwab 做 T 和盘中频率。

**也应推迟 Claude 的 3 analyst + PM 作为默认 active 策略。** 未来仍可把整套 multi-agent 工作流封装成一个 `TradingStrategy` adapter，在 shadow mode 中评估；内部复杂度不能泄漏到调度、风控或 broker 层。

一句话决策：**生产版本做成一个“策略可换、执行链唯一、默认安静、异常即停”的小程序；不同 LLM 策略共享同一 interface，任何时刻只有一个拥有真实交易权。**
