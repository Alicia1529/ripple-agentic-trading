# Trading Agent System — Final Proposal

> Status: **Final(取代 Claude/PROPOSAL.claude.md 与 Codex/TRADING_AUTOMATION_PROPOSAL.md,两份原提案保留作参考)**
> Date: 2026-08-21 · Owner: Alicia · Role of Claude: 设计、代码、backtest 工具;不执行交易、不持有密钥、不给具体标的买卖建议
> 来源:综合 Claude 提案(学习定位、multi-agent 架构)+ Codex 提案(工程严谨性)+ PROPOSAL_COMPARISON.md 的官方资料核验,并按 Alicia 的最终决策取舍。

---

## 0. 定位

**目标不是赚钱**,$500–1000 本金金钱意义上无关紧要。真实目标:

1. 学习 agent 系统设计——搭一个「不可信 LLM 决策层 + 确定性代码风控层」的完整系统。
2. 搞清楚 multi-agent(3 analyst + PM)相对简单确定性策略、相对被动持有,到底有没有增量价值——这就要求系统里必须同时跑一个**可比较的基线**,不能只有 agent 自己。

**硬约束(本次明确提出,覆盖之前两份草案)**:**Alicia 不承担任何运维工作量。** 系统必须是"部署后自动运行、只在真正需要人决策的稀有事件(如触发熔断)时才通知人",不能有需要每天/每周手动做的事(手动对账、手动导出 CSV、手动确认每笔交易、手动 token 续期)。这条约束直接决定了下面大量的取舍。

**约束来源(2026-08-21 确认)**:Alicia 即将入职 xAI,预期几乎没有维护时间。**这条约束已经过明确核实,不会把架构收窄成单账户/单策略**——Alicia 确认两账户 + 开放孵化池的设计与"零运维"是兼容的,预期系统全程由 LLM 策略驱动,自己只是偶尔看一眼账户。原因是本文档里所有人工介入点都是稀有的高风险事件(每月白名单 review、风控熔断通知、孵化池转正批准),不是日常琐事;其余(对账、成本记账、漏跑检测)全部是自动代码。**`PROPOSAL_COMPARISON.v0.md` 里"应收窄为单一 active 策略"的结论已被本次确认推翻,不要再采纳。**

**范围更新(本次拍板)**:项目从"单一 agent 决策流"扩展为**两个真钱账户,分别跑同一套 3-analyst+PM 架构、只换模型配置**,做模型选择的 A/B 实盘对比;再加一个**开放式 shadow 孵化池**(起步是均值回归 baseline、SPY/QQQ 买入持有两条固定基准,之后可持续加入新的模型配置或策略设计做纸面验证)——表现持续跑赢基准且满 8 周的候选,经 Alicia 人工批准后可转正为新的真钱账户。

---

## 1. 决策记录

| # | 决策点 | 结论 | 理由 |
|---|--------|------|------|
| D1 | 真实目标 | 学习 agent 系统设计 + 可比较基线验证 | 本金太小,收益本身无意义 |
| D2 | 账户数量 | **两个 Robinhood Agentic 真钱账户**,同属一个 RH 登录,各自独立跑一整套 3-analyst+PM 流程(Alpaca 只做 paper 验证,不作为长期并行账户) | 需要真实对比两套模型配置的实盘表现;两个账户各自的 broker 对账单就是权威数据,不需要共享账户时那套"谁能持有哪个标的/禁止静默对冲/虚拟账本对账"冲突处理逻辑,比塞进一个账户更简单、更符合"零运维"。同属一个 RH 登录,不新增 OAuth/CSV 这类运维负担,不违反"不想要太多账户"的初衷(那条顾虑针对的是跨多个不同券商) |
| D2a | **两账户模型差异 + 具体落地(本次拍板)** | 两个账户跑**同一套** analyst 分工、risk layer、universe、决策频率,**只有模型配置不同**;具体分工:**账户 A = Claude(Decision Run 跑成 Claude Code 云端 scheduled routine,吃 Alicia 已有的 Claude Pro 订阅额度)、账户 B = OpenAI(Decision Run 跑成 Codex 云端 Automations,吃 Alicia 已有的 ChatGPT Plus 订阅额度)** | 控制变量,确保对比出来的差异是模型能力差异,不是策略设计差异;两边都是 Alicia 已经在付费的订阅,边际 LLM 成本趋近 $0(见 §6);前提是订阅的用量额度够用——**Phase 0 需要实测确认**,额度不够就临时退化成 metered API(不影响架构,只影响账单) |
| D2b | **两账户资金** | 每个账户各自 $500–1000,**总敞口 $1000–2000**(不是共享 $500–1000) | Alicia 已确认接受;§6 成本预算与风控数值按"每账户独立计算"处理 |
| D3 | 决策频率 + **Decision/Execution 分离(本次修正)** | 每日收盘后一次生成信号并持久化为 `OrderPlan`(§2.2);**当晚不下单**,次日开盘后约 9:35am ET 才由 Execution Agent 重新校验并执行(§2.1、§2.3) | 决策时机由信息可得性决定,执行时机由市场流动性/执行质量决定,两者是不同问题,不能混为一谈(见 §2);开盘后执行也彻底避开了"RH Agentic 休市下单行为未知"这个问题(§7 对应假设已不再需要验证) |
| D3a | **默认订单类型** | **限价单/marketable-limit** 为默认,限价设在决策时价格的一个可配置缓冲带内(如 ±0.5%,即 `price_tolerance_pct`);市价单需要策略显式声明理由;Phase 0 不引入 VWAP/TWAP 等复杂执行算法 | 隔夜到次日开盘之间有跳空风险,限价单能限制最差成交价;沿用 Codex 提案"限价单默认、市价单需正当理由"的风控原则;Phase 0 优先确定性和可调试性 |
| D4 | Agent 分工 | 每个账户内部:3 个独立 analyst 打分 + PM 聚合(强模型) | 沿用 Claude 提案,是本项目的学习核心 |
| D5 | **基线 = 开放式 shadow 孵化池(本次拍板)** | 除两个真钱账户外,系统维护一个**不下真实订单**的 shadow 孵化池:起步至少包含①均值回归、②SPY/QQQ 被动持有 两条固定基准,池子本身**开放**,之后可以随时加入新的候选——新的模型配置(Model Config C/D...)或新的策略设计(趋势跟踪、情绪驱动等),数量不预设上限 | 没有基线就无法判断"multi-agent 架构本身"以及"模型选择"是否真的带来增量;开放式设计让日后测试新想法不需要改架构,只需要注册一个新 candidate |
| D5a | **Shadow → 真钱账户 转正门槛(本次拍板)** | 候选必须同时满足:①在 shadow 池里连续跑满**至少 8 周**;②同一窗口内**同时跑赢**均值回归基线和 SPY/QQQ 被动持有;③无重大执行 bug、risk layer 校验通过。满足后系统只生成通知,**不自动开户**——是否真的开一个新 RH 账户、投入 $500–1000,由 Alicia 人工拍板 | 8 周窗口与 Phase 1 gate 一致,避免用不同标准制造混淆;"同时跑赢两条基准"确保转正的策略是真的有增量,不是运气;开户/入金是重大财务决策,保留人工最后一步,符合"实盘决策与责任归 Alicia"的边界声明,也不违反"零运维"(这是稀有的一次性决策,不是日常操作) |
| D6 | Risk layer | 规则只存在于代码,不存在于 prompt;每个真钱账户独立套用同一组风控参数(基于各自账户自身权益计算);所有拦截/裁剪记录 `{原始指令, 触发规则, 实际执行, account_id}` | 不可协商;account_id 只是审计标签,不是 Codex 式跨策略共享账本,不引入冲突处理复杂度 |
| D7 | 资金投入节奏 | Paper 验证通过后**两个账户同时直接投入各自 $500–1000**,不设起步阶梯、不要求前 20 笔人工逐笔确认 | Alicia 已确认接受这个节奏 |
| D8 | 交易 universe | 两账户共用同一份固定白名单 ~15 只高流动性大盘股 + 2–3 只 ETF,每月人工 review(这是唯一保留的、频率很低的人工步骤) | 隔离选股与择时能力,同时把"人工"成本压到月级;两账户共用白名单也是控制变量的一部分 |
| D9 | v1 禁止 | 做空、杠杆、options | adapter 层直接拒绝,两账户一致 |
| D10 | 部署 | Decision Run:账户 A 走 Claude Code 云端 routine,账户 B 走 Codex 云端 Automations(见 D2a);Shadow 孵化池的 Decision Run 用 GitHub Actions(不需要真钱账户订阅,metered API 即可,量很小)。Execution Run(两个真钱账户,~9:35am ET 次日):**统一用 GitHub Actions 跑纯代码脚本**,不经过任何 LLM session,理由见此前讨论(下单权限不能给到做决策推理的 agent) | 免费(GH Actions 部分)/ 订阅额度内(Claude Code、Codex 部分);已知限制见 §7 |
| D10a | **时区正确性(本次新增)** | 不用"写死一个 UTC 时间点"的 cron。改成:**调度器每隔 5–10 分钟触发一次(在目标时间前后一个宽松窗口内),脚本自己用带时区库(如 Python `zoneinfo`,`America/New_York`)算出当前真实 ET 时间,不在目标窗口内就直接空跑退出**;GitHub Actions cron 只认 UTC 且没有时区参数,Claude Code/Codex 云端调度是否原生支持 IANA 时区目前未经确认(见 §7),这个模式不管调度器怎么实现都正确,不需要每年手动改两次夏令时 | 美股开收盘时间锚定在 ET,夏令时切换(3月/11月)会让任何写死的 UTC 时间偏移一小时;用运行时计算真实 ET 时间 + 窗口内幂等检查,规避对调度器时区能力的依赖,同时保持零运维(不需要人工每年切换 cron 表达式) |
| D11 | Fidelity/Schwab 监控 pipeline | **v1 不做**(原 Claude 提案 §5"方案3") | 需要 Schwab OAuth 续期或 Fidelity 每周手动 CSV,两者都是运维负担,与"零运维"直接冲突;如果你后续仍想要多账户周报,这是一个独立项目,不在本提案范围内 |

---

## 2. 系统架构:Decision / Execution 两阶段分离

**核心原则(本次采纳,取代上一版"收盘后当晚提交订单"的设计)**:投资决策(何时产生 target portfolio)与订单执行(何时真正下单)是两个独立问题。决策时机由信息可得性决定(收盘数据什么时候齐);执行时机由市场流动性/执行质量决定(开盘瞬间流动性薄、价差大)。**不能因为信号是收盘后生成的,就假设订单应该收盘后立刻提交**——这是上一版设计的一个概念性错误,本次改正。

### 2.1 每日时间线(以 US Eastern Time 为准)

账户 A、账户 B、shadow 孵化池共用**同一个市场数据快照时刻**(控制变量,保证对比公平),但各自独立产出决策(账户 A 用 Claude、账户 B 用 OpenAI/Codex,见 D2a;shadow candidate 是不同策略/配置)。

**时区处理(D10a)**:下面时间线上的每个触发点,实际调度都不是"精确写死的 UTC 时刻",而是"调度器高频轮询 + 脚本自己用 `America/New_York` 时区库判断是否到点,没到点就空跑退出"。这样无论用 GitHub Actions(只认 UTC)还是 Claude Code/Codex 的云端调度,夏令时切换都不需要人工干预。

```
4:00 PM ET   收盘
4:00–4:15    等待当日行情数据落定(避免用未最终修正的数据)
4:15–4:30    Decision Run(三条并行的调度,共用同一个市场快照 as_of):
             - 账户 A:Claude Code 云端 routine
             - 账户 B:Codex 云端 Automations
             - Shadow 孵化池:GitHub Actions
             各自执行:
             1. Market Data Snapshot
             2. Analyst Agent(s) 生成 signal/expected return(各自的模型配置)
             3. Portfolio Manager 生成 target portfolio
             4. Risk Engine 校验约束(§3 风控规则)
             5. Order Planner 把 target portfolio 转成具体订单
             6. 持久化 OrderPlan(见 §2.2)并 commit/push 回仓库,状态 = pending

Overnight    不下单,不改动已生成的 OrderPlan

次日 ~9:35   Execution Run(GitHub Actions scheduled job,开盘后约 5 分钟,不卡 9:30:00 整;
             只处理两个真钱账户,shadow 池走虚拟 Fill Simulator,见 §2.5):
             1. 加载昨天持久化的 OrderPlan
             2. Revalidate 账户状态(见 §2.3)
             3. 检查当前持仓、可用资金
             4. 检查价格是否超出预设容差带(见 §2.3)
             5. 执行通过校验的订单
             6. 监控成交(fill)
             7. 对账持仓
             8. 持久化执行结果/日志并 commit/push 回仓库
```

**为什么改成两次独立 run**:①执行永远发生在开盘之后,不再需要验证"RH Agentic 休市下单会怎样"这个此前标记为未经官方文档确认的假设(§7 对应条目已标记为不再需要验证);②9:35 而不是精确 9:30:00,是为了避开开盘瞬间流动性最薄、价差最大的几分钟,Phase 0 优先要确定性和可调试性,不引入 VWAP/TWAP 之类的复杂执行算法;③decision 和 execution 分离让复盘时能清楚分清"这笔亏损是判断错了,还是执行时价格已经变了",也让 backtest 更容易做到时序一致(见 §2.4)。

### 2.2 OrderPlan 数据模型

Decision 阶段的输出是一份持久化、**生成后即不可变(immutable)**的 `OrderPlan`:

```yaml
order_plan_id: uuid
decision_time: 2026-08-21T16:25:00-04:00     # ET
account_id: account_A                          # account_B / shadow:mean_reversion / shadow:spy_qqq / shadow:candidate_C ...
model_config_version: config_A_v3              # 用于复现
market_snapshot_as_of: 2026-08-21T16:00:00-04:00
status: pending                                 # pending → executed | aborted | partially_executed

target_portfolio:
  AAPL: 15%
  MSFT: 10%
  ...
  cash: 20%

orders:
  - order_id: uuid
    symbol: AAPL
    side: BUY
    qty: 12
    order_type: LIMIT
    limit_price: 227.50              # 生成时价格 + D3a 缓冲带
    price_tolerance_pct: 0.5%        # 执行时用于判断是否 gap 过大
    reference_price_at_decision: 226.40
```

`OrderPlan` 一旦生成,Execution Agent 只能:**照单执行 / 整体 abort / 按当前可用资金等比缩量 / 因风控或账户状态变化拒绝某几笔订单**。Execution Agent **不能**重新跑一遍 analyst/PM 推理,不能凭"现在看法变了"改变方向或加仓——那是篡改已有决策,破坏可复现性、可审计性和归因分析。

- 允许:标的隔夜跳空 >预设阈值 → 执行守卫拒绝该笔订单。
- 不允许:PM 昨天决定买 NVDA,Execution Agent 今天自己觉得不该买了 → 卖出。

如果 abort,系统等下一次正常的 decision run,不补跑、不追单——与 §5 "workflow 漏跑不补单"是同一条原则。

### 2.3 Execution 阶段的 Revalidation 与 Abort 条件

Execution Agent 下单前重新检查的是"昨晚的决策今天是否还站得住",不是重新决策:

| 检查项 | 触发条件 | 行为 |
|---|---|---|
| 账户状态对账 | 当前持仓/现金与 OrderPlan 生成时的假设不一致 | Abort 该 OrderPlan,记录差异,发通知(低概率事件) |
| 价格容差 | 开盘价相对 `reference_price_at_decision` 超出 `price_tolerance_pct` | 该笔订单 abort,不自动追价、不重新推理,等下一次 decision run |
| 可用资金/购买力 | 资金不足以执行完整订单 | 按比例缩量或 abort 超出部分,记录 |
| Risk Layer 复核 | 用当前账户权益重新过一遍 §3 规则(如隔夜权益变化导致原订单超过 20% 仓位上限) | 裁剪或拒绝,复用 §3 现有逻辑 |
| 数据新鲜度 | 无法取得当前行情/账户状态(API 失败等) | 不下单,记录并通知,等下一周期 |

这套逻辑复用 §3 的 risk layer 代码,只是多了一层"价格/账户状态是否仍然有效"的前置校验,不引入新的决策逻辑。

**已持有仓位的止损/止盈复查(独立于新 OrderPlan,每个 Execution Run 都做)**:每次 Execution Run 除了处理当天的 `OrderPlan`,还要对该账户**所有已持有的仓位**重新算一遍止损/止盈条件——不管今天有没有新的决策、新的 thesis 多有说服力。任何一个持仓触发止损/止盈,立即按 §3 规则平仓/减仓,不受当天 Decision Run 输出影响。这条参考自 FriesTrader 的设计原则("a good story never cancels a stop-loss"),弥补了此前设计里"只校验新订单、没有独立复查存量持仓"的漏洞。

### 2.4 回测/实盘时序一致性(防 Look-Ahead Bias)

**规则**:如果信号使用 Day T 收盘价或其他日终数据生成,无论历史回测还是 paper/live 的表现计算,都不能假设成交价等于 Day T 收盘价——必须建模为 **Day T+1 开盘附近成交**。

- 错误:T 日收盘价 $220 生成信号 → 回测假设就在 $220 成交。
- 正确:T 日收盘生成信号 → 成交建模在 T+1 开盘(或开盘后几分钟)。

这条规则同样约束 shadow 孵化池的记账(§4):均值回归 baseline、SPY/QQQ、以及未来加入的 candidate,虚拟成交价必须用 **T+1 开盘价**标记,不能直接拿生成信号当天的收盘价打勾——否则 baseline 相当于比真钱账户多了一天信息优势,对比就不公平。日后如果给均值回归策略调参做历史 backtest,也必须遵守同一时序语义,保证 backtest 与生产环境行为一致。

### 2.5 系统架构图

```
共享 Market Data Snapshot(同一个 as_of 时间戳,两账户 + shadow 池共用,只是决策独立)
                    │
        ┌───────────┼───────────────────────┐
        ▼                                   ▼                               ▼
   账户 A 决策流                        账户 B 决策流                  Shadow 孵化池(每个 candidate 一份)
   Analyst(Config A) → PM(Config A)     Analyst(Config B) → PM(Config B)   Analyst/规则 → PM 或规则引擎
        ▼                                   ▼                               ▼
   Risk Engine A                        Risk Engine B                  虚拟 Risk Engine(逻辑一致)
        ▼                                   ▼                               ▼
   Order Planner → OrderPlan A          Order Planner → OrderPlan B    Order Planner → 虚拟 OrderPlan
        │ (持久化,overnight 不变)             │                               │
════════════════════════════ 次日 ~9:35 ET ═══════════════════════════════════
        ▼                                   ▼                               ▼
   Execution Revalidation A(§2.3)       Execution Revalidation B(§2.3)   虚拟 Fill Simulator
        ▼                                   ▼                          (按 T+1 开盘价标记,§2.4)
   RH Agentic 账户 A                     RH Agentic 账户 B                    ▼
        ▼                                   ▼                          虚拟净值曲线
   Fill Monitoring → Position Reconciliation → Audit/Metrics/Logs(两账户独立记录,互不影响)
```

**多账户处理说明**:与"多账户共享同一份决策、只按各自资金规模缩放执行"的通用模式不同——账户 A/B **故意**跑独立的决策流水线(不同模型配置),这是 D2a 的设计目的(A/B 对比模型能力)。两账户真正共享的只是市场数据快照的时间点和 universe(控制变量),不共享 target portfolio。如果日后想让多个账户执行同一份决策(比如把某个转正的 candidate 复制到多个账户),需要另外设计"共享决策、按账户资金/持仓/购买力生成各自订单"的模式,不在本次范围内。

**关键设计约束**:

- Analyst 输出 schema:`{ticker, direction, score∈[-1,1], confidence∈[0,1], rationale}`,全部落盘,并打上 `account_id` 与 `order_plan_id`,把 signal → OrderPlan → 执行结果串起来,方便审计。
- **两个真钱账户完全独立**:各自的 risk layer 实例、各自的 execution adapter 调用、各自的 broker 对账单。不共享账户,因此不需要 Codex 式的"跨策略共享账户"冲突处理逻辑——这套复杂度被两账户隔离天然规避掉了。
- **Shadow 孵化池**是轻量版 `strategy_ledger`:池内每个 candidate 同样走 Decision Run 生成 OrderPlan,但没有 Execution Run/Broker 这一段,由虚拟 Fill Simulator 按 T+1 开盘价直接标记成交(§2.4),从不调用 execution adapter、不触碰任何真实账户,复杂度远低于 Codex 提案里给真钱多策略设计的那套账本。池子开放意味着加新 candidate 只是注册一条新记录,不需要改动架构。
- **Shadow → 真钱 转正是唯一允许账户数量增长的路径**:candidate 连续 8 周同时跑赢均值回归基线和 SPY/QQQ、且无执行 bug,系统才生成通知;是否真的开新 RH 账户、投入资金,由 Alicia 人工批准,系统不会自动开户或自动入金。
- Risk layer 与 prompt 的分工:prompt 里的风控是*建议*,代码里的风控是*约束*,两个账户各自套用同一套风控参数值,但状态(今日已开仓数、当前回撤等)完全独立。
- Execution adapter 可插拔,v1 启用 Alpaca paper(验证)与 RH Agentic(两个真钱账户复用同一套 adapter 实现,只是 credential/account 不同),且现在只在 ~9:35am 之后被调用,不在收盘后调用。

---

## 3. Risk Layer 规格(代码强制)

**两个真钱账户各自套用下表全部规则,数值相同但按各自账户自身权益独立计算,互不影响**(账户 A 触发熔断不会暂停账户 B)。

| 规则 | 数值 | 触发后行为 | 变更说明 |
|------|------|-----------|---------|
| 单一标的仓位上限 | 账户自身权益的 20% | 裁剪订单至上限 | 沿用原值 |
| 单日新开仓上限 | 3 笔/账户 | 超出直接丢弃并记录 | 沿用原值 |
| **单日亏损熔断** | **−1%**(浮亏+已实现,按账户自身权益) | 当日该账户禁止新开仓,只许平仓 | **从原 −5% 收紧**——因为跳过了前 20 笔人工确认,系统全自动下单,风控阈值必须更保守 |
| **累计回撤(10%)** | 该账户高点回撤 −10% | 该账户禁止新开仓 + 生成通知(**唯一需要你看一眼的场景**) | 新增中间档,不是原来一步到 −15% |
| 累计回撤(15%) | 该账户高点回撤 −15% | 该账户整体停机,需人工重启;**另一账户不受影响,继续独立运行** | 沿用原值,新增"互不拖累"说明 |
| 禁止项(v1) | 做空、杠杆、options | adapter 层直接拒绝,两账户一致 | 沿用原值 |
| **Wash-sale 跨账户检测(本次新增)** | IRS wash-sale 规则按人头算,不按账户算;检测窗口 30 天(可配) | **只拦截买入**(新开仓/加仓),从不拦截止损/止盈/平仓卖出——风控不能为了避税让位;命中时该笔买入 abort,记录并标记供年底报税参考 | 两个真钱账户都在 Alicia 名下,账户 A 卖出亏损标的、账户 B 买回同一标的会触发真实 wash sale,不是学术假设;参考 FriesTrader 的 `wash_sale_avoidance` 设计,检测范围覆盖 `linked_accounts`(账户 A + 账户 B,以及 Alicia 名下其他相关账户) |

所有被拦截/裁剪的指令写入日志:`{原始指令, 触发规则, 实际执行, account_id}`。

**Wash-sale 检测的已知局限(如实记录)**:这套检测只能覆盖本系统能看到的账户和交易。如果 Alicia 在系统管不到的其他账户(比如未来手动操作的账户)买回同一标的,系统无法预防——那部分风险只能靠人工自己注意,不属于本系统的责任范围。

**关于"零运维"与风控通知的关系**:上表里除了每月一次的白名单 review,其余全部自动运行。只有某个账户触发 10%/15% 回撤熔断这种**低概率事件**时,系统才会主动通知你——这不是日常运维,是安全阀,性质不同。两个账户各自独立触发,互不拖累;如果系统按设计运行,你大概率整个 Phase 1/2 都不会收到任何需要处理的通知。

**关于 kill switch 的诚实说明(官方资料核验结果)**:Robinhood 官方文档**没有**提供"一键立即清仓"的现成 kill switch 产品能力,只能撤销 pending order;官方文档本身也提示 agent 可能"difficult to monitor or stop in real time"。本系统的"kill switch"实际含义是:代码层面的开关能立刻停止生成新订单、撤销所有 pending 订单;已持有的仓位需要用正常卖单逐步平掉,不是瞬时清空。这个限制写进代码注释和 runbook,避免高估这项能力。

---

## 4. Baseline & Benchmark(复盘系统核心)

复盘/周期性报告(不是日常运维,是自动生成的记录文件)起步包含**四条曲线**的对比,**之后随 shadow 池加入新 candidate 会持续增加**:

1. **账户 A 曲线**:Model Config A 的 3-analyst + PM 聚合后,经过 risk layer A 的实际净值(真钱)。
2. **账户 B 曲线**:Model Config B 的 3-analyst + PM 聚合后,经过 risk layer B 的实际净值(真钱)。
3. **均值回归 baseline 曲线**:同一 universe、同一市场快照,用简单确定性规则(如 N 日偏离均值超过阈值反向开仓)生成 `OrderPlan`,由虚拟 Fill Simulator 按 **T+1 开盘价**标记成交(§2.4),不受任何 LLM 影响。
4. **SPY / QQQ 被动持有曲线**:从两个真钱账户实际启动交易的当天起,把等额本金买入 SPY 和 QQQ 并持有至今的净值,同样按 T+1 开盘价标记建仓,纯记账,不下单。
5. **(开放)Shadow candidate 曲线**:每个新加入孵化池的模型配置或策略设计各一条,纯虚拟记账,持续对照 8 周转正门槛(见 D5a)。

评估维度:
- **模型选择增益**:账户 A vs 账户 B——同样的 analyst 分工、同样的 risk layer、同样的 universe,只有模型不同,差异就是模型能力的差异(这是本次范围扩展最核心的学习目标)。
- **agent 架构增益**:账户 A/B 分别相对均值回归 baseline 的增益——判断 multi-agent 决策本身是否比一个简单规则更好。
- **主动管理增益**:账户 A/B、baseline 分别相对 SPY/QQQ 被动持有的增益——判断这一整套系统是否值得做,相对什么都不做(买指数)有没有优势。
- 每个 analyst 的方向准确率、confidence calibration(reliability diagram),按账户分别统计。

**任何一条对比曲线的计算逻辑本身是一次性写好的代码,不需要你手动维护。**

---

## 5. Phase 计划

- **Phase 0 — 搭建**(~1–2 周):项目骨架、`OrderPlan` 数据模型与持久化(§2.2)、账户 A 的 Claude Code routine + 账户 B 的 Codex Automations + shadow 池与 Execution Run 的 GitHub Actions workflow(§2.1、D10)、D10a 的时区自检逻辑、risk layer + 执行时 revalidation 单测(含"LLM 越权指令被拦截"的对抗性测例,两账户各一套独立实例)、Alpaca paper 接入(单账户验证即可)、Model Config A/B 两套配置跑通、均值回归 baseline + SPY/QQQ 记账逻辑(按 §2.4 用 T+1 开盘价标记,不用信号当天收盘价)。**另需实测确认 §7 列出的三项假设**(双 Agentic 账户绑定独立 agent、Pro/Plus 订阅额度是否够用、两个云端调度平台的时区行为),确认结果不理想则调整 D2/D2a/D10a 的实现方式。
- **Phase 1 — Paper**(8 周):Model Config A + Model Config B 两套 3-analyst+PM 全量运行(仍在 Alpaca paper,不需要开两个 paper 账户,同一 paper 账户内用两个 `account_id` 标签区分即可)+ baseline + benchmark 同步运行,**同样按 §2.1 的 Decision Run / Execution Run 两阶段跑**(paper 环境也不在收盘后立刻下单),保证 paper 阶段验证的就是 Phase 2 实盘要用的那套时序逻辑,不是另一套简化版本,每日自动记录决策链与四条净值曲线。
  - Gate(工程 sanity check,不证明 alpha):连续跑满 8 周;两套配置都无重大执行 bug(无重复下单、无风控穿透、无静默失败);四条曲线数据完整、可复盘。
  - **明确注记**:Alpaca paper 不模拟 market impact、订单信息泄露、延迟滑点、队列位置、价格改善、监管费、股息,paper-only 账户只有 IEX 数据权限。这意味着 paper 阶段的表现**天然比实盘乐观**,gate 通过不代表实盘也会通过,只代表工程没有明显 bug。
- **Phase 2 — RH Agentic 实盘(两个账户)+ Shadow 孵化池持续运行**:开设两个 Robinhood Agentic 账户,各自直接投入 $500–1000(总敞口 $1000–2000),账户 A 换 Model Config A 的 RH MCP adapter,账户 B 换 Model Config B 的,均不设人工逐笔确认;开启交易通知,确认"代码开关能立即停止新订单"这条能力在两个账户上都经过实测。**与此同时,shadow 孵化池持续跑**:均值回归、SPY/QQQ 两条基准线常驻,后续可随时注册新的 candidate(新模型配置或新策略设计),每个 candidate 独立计时、独立判断 D5a 转正门槛,互不影响真钱账户的运行。
- **Shadow → 真钱转正(常态化流程,不是单独 Phase)**:任意 candidate 满足 D5a 门槛(8 周 + 同时跑赢均值回归和 SPY/QQQ + 无 bug)时,系统生成通知;Alicia 批准后开新 RH 账户、投入 $500–1000,该账户从此按 Phase 2 的所有规则(独立 risk layer、不设人工逐笔确认)运行。这是账户数量增长的唯一途径,增长速度由 Alicia 的批准节奏决定,系统不会自作主张扩张。
- **Phase 3(可选,需你另外拍板才启动)**:换 broker(如 Schwab)、加盘中频率、辩论式架构 ablation——这些会重新引入运维负担(OAuth 续期、更多监控面等),默认不做。(注:增加模型配置/策略候选**不需要**等 Phase 3,走 shadow 孵化池常态化流程即可。)

**调度可靠性已知限制**:GitHub Actions 官方文档说明高负载时 scheduled job 会被延迟,负载足够高时甚至可能被丢弃——这适用于 Execution Run 和 shadow 池的 Decision Run。账户 A/B 的 Decision Run 分别跑在 Claude Code / Codex 各自的云端调度上,可靠性未经我们验证(§7),按同样的保守假设处理(可能延迟,不假设精确触发)。这些延迟对低频调度影响可以接受(延迟几分钟到一小时不影响策略逻辑),系统会加一条自动检查(当天该跑的 job 没跑,发通知),这也是一次性写好的代码,不是手动巡检。**Execution Run 如果被延迟,§2.3 的价格容差校验会自然起到保护作用**——延迟越久,价格越可能超出容差带,系统会倾向于 abort 而不是拿一个更旧、更不可靠的 OrderPlan 硬冲;abort 后等下一次正常 decision run,不追单、不补跑。

---

## 6. 成本预算

| 项 | 预估 | 说明 |
|---|---|---|
| 账户 A 的 Decision Run(Claude) | **≈ $0/月 新增支出** | 吃 Alicia 已有的 Claude Pro 订阅额度,不是额外开销;前提是额度够用(Phase 0 待验证,见 §7) |
| 账户 B 的 Decision Run(Codex/OpenAI) | **≈ $0/月 新增支出** | 吃 Alicia 已有的 ChatGPT Plus 订阅额度,同上;Codex 定价档位待 Alicia 自行在 openai.com 核实(我这边访问官方定价页被 403 拦截,只查到第三方聚合数据) |
| 部署(GitHub Actions) | $0 | 免费额度内;承担 Execution Run(两账户)+ shadow 孵化池的 Decision Run |
| Shadow 孵化池 LLM 调用(metered API) | 非 LLM 策略(均值回归等)≈ $0;每加一个 LLM 驱动的新模型配置候选约 +$10–20/月 | 孵化池不像两个真钱账户那样有现成订阅可用(避免为验证阶段的候选也去开新订阅),用 metered API 更灵活,反正候选阶段调用量小 |
| 市场数据 | $0 | yfinance / Alpaca free tier |
| Alpaca paper | $0 | 免费 |
| **月度合计** | **≈ $0–20/月新增**(两个真钱账户订阅覆盖,孵化池候选按 metered 计) | **兜底方案**:如果 Pro/Plus 订阅额度撞上限,账户 A/B 的 Decision Run 退化成 metered API,那时月度合计回到 ≤$60 量级——这是成本上限,不是预期值 |

一次性/资本项(不计入月度):**两个** RH Agentic 账户各入金 $500–1000,**总计 $1000–2000**,本金,Phase 2 才入,可全损。**每笔 shadow → 真钱转正会新增一个账户的入金**,金额同样是 $500–1000/账户,由 Alicia 逐笔批准,不预设总账户数上限。

真实交易成本(采纳 Codex 的记账原则,但只做自动记录,不需要你手动核对):每笔成交自动记录 commission、bid/ask spread、slippage、监管费,和 P&L 分开存,不混在一起。

---

## 7. 已知限制(官方资料核验,如实记录而非过度承诺)

| 结论 | 依据 | 对设计的影响 |
|---|---|---|
| RH 无现成 kill switch,只能撤 pending order | [Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)、[Trading with your agent](https://robinhood.com/us/en/support/articles/trading-with-your-agent/) | §3 已改写 kill switch 的真实含义 |
| Alpaca paper 不模拟 market impact/滑点/延迟/股息等 | [Alpaca Paper Trading docs](https://docs.alpaca.markets/us/docs/paper-trading) | §5 Phase 1 gate 注记已加入 |
| GitHub Actions scheduled job 可能延迟或被丢弃 | [GitHub Actions troubleshooting](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows) | §5 加自动化"漏跑检测",不做精确开盘执行假设 |
| RH Agentic 更偏"agent 逐次决策"而非确定性中频 API | 综合调研(BROKER_COST_RESEARCH.md) | 支持 D3(每日频率)的选择 |
| RH 允许最多 10 个 self-directed investing account,Agentic 账户算在其中;但账户与 agent 连接的对应关系(是否可独立连接不同 agent)官方文档未明确说明 | [Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)、[Trading with your agent](https://robinhood.com/us/en/support/articles/trading-with-your-agent/) | 支持 D2(两账户可行);Phase 0 仍需**实测确认**两个 Agentic 账户能否各自独立连接不同的 agent/API credential——这是本提案唯一还留着的、需要 Phase 0 动手验证的假设 |
| ~~RH Agentic 的下单工具在休市时段调用会怎样~~ | — | **已因 §2 的架构修正而不再相关**:新设计下 Execution Run 固定在 ~9:35am ET(开盘后)才调用下单工具,永远不会在休市时段提交订单,这个假设不需要验证了 |
| Claude Code 云端 routine / Codex 云端 Automations 的用量额度,在 Pro / Plus 订阅档位下,能否覆盖每日 3-analyst+PM(4 次调用/账户/天)的实际用量 | 三方聚合定价页(非一手 openai.com,访问被拒),Claude Pro/Codex Plus 官方额度说明未逐条核实 | 支持 D2a 的"边际成本≈$0"假设;Phase 0 需要**实测**,不够则退化为 metered API(§6 已写好兜底方案,不影响架构) |
| Claude Code 云端 routine / Codex 云端 Automations 的定时调度是否原生支持 IANA 时区(如 `America/New_York`),还是只认 UTC/触发时的浏览器本地时区 | 未查到官方明确说明 | 支持 D10a;不管答案是什么,"调度器高频轮询 + 脚本自算 ET 时间再决定是否执行"这个模式都正确,所以这项不确认也不阻塞设计,只是影响调度器配置的具体写法 |

**Phase 0 仍需实测确认的假设(未经官方文档背书,共三项)**:①两个 Agentic 账户能否各自绑定独立 agent/API credential(支持 D2);②Claude Pro / ChatGPT Plus 的用量额度是否够用(支持 D2a 成本假设);③两个云端调度平台的时区行为(支持 D10a,非阻塞项)。应在开真钱账户之前,用小额/paper 环境验证清楚。

---

## 8. 明确排除的范围(v1 不做,避免范围膨胀)

- 多 broker(Schwab/Fidelity)接入与周报 pipeline——运维负担与本次"零运维"约束冲突。
- **Codex 式"共享账户多策略"虚拟账本**(谁能持有哪个标的、禁止静默对冲、虚拟账本与 broker 强一致性对账)——两个真钱策略各自有独立账户,天然不需要这套冲突处理复杂度。**仅有的轻量 `strategy_ledger` 用于两条 shadow 线(均值回归、SPY/QQQ)的纯虚拟记账,不涉及真实资金,不需要冲突处理逻辑。**
- 税务 lot 管理(具体 lot 选择、长短期资本利得优化)——超出学习目标范围;wash-sale 检测已改为纳入 §3(见上方新增规则),不再排除。
- 中频/盘中交易——与"零运维"约束冲突,留给 Phase 3 单独评审。
- 辩论式 multi-agent 架构——留作日后 ablation,不在 v1。
- **Shadow candidate 自动转正**——转正必须经过 D5a 门槛判断 + Alicia 人工批准,系统任何情况下都不能自己开户或自己入金。
- **VWAP/TWAP 等复杂执行算法**——Phase 0 默认限价/marketable-limit 单笔执行(D3a),除非组合规模或实测滑点明显需要,否则不引入更复杂的执行逻辑。
- **Execution Agent 独立于 Decision 阶段重新做投资判断**——Execution Agent 只能执行/abort/缩量/因风控拒绝已持久化的 `OrderPlan`(§2.2),不能重新跑 analyst/PM 推理或凭"现在看法变了"改变交易方向。

---

## 9. 边界声明

Claude(任何界面)负责设计、代码、backtest 工具、复盘 pipeline;不执行交易、不持有密钥、不给具体标的买卖建议。实盘决策与责任归 Alicia。所有 API key / broker credential 只走环境变量、GitHub Actions secrets,或 Claude Code / Codex 各自云端调度的原生 secret 机制,永不进仓库、永不以明文形式出现在 `OrderPlan` 或日志里。
