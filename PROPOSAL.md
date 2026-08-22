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

**范围更新(本次拍板)**:项目从"单一 agent 决策流"扩展为**两个真钱账户,分别跑同一套 3-analyst+PM 架构、只换模型配置**,做模型选择的 A/B 实盘对比;再加一个**开放式 shadow 孵化池**(起步是均值回归 baseline、SPY/QQQ 买入持有两条固定基准,之后可持续加入新的模型配置或策略设计做纸面验证)——表现持续跑赢基准且满 8 周的候选,经 Alicia 人工批准后可转正为新的真钱账户。

---

## 1. 决策记录

| # | 决策点 | 结论 | 理由 |
|---|--------|------|------|
| D1 | 真实目标 | 学习 agent 系统设计 + 可比较基线验证 | 本金太小,收益本身无意义 |
| D2 | 账户数量 | **两个 Robinhood Agentic 真钱账户**,同属一个 RH 登录,各自独立跑一整套 3-analyst+PM 流程(Alpaca 只做 paper 验证,不作为长期并行账户) | 需要真实对比两套模型配置的实盘表现;两个账户各自的 broker 对账单就是权威数据,不需要共享账户时那套"谁能持有哪个标的/禁止静默对冲/虚拟账本对账"冲突处理逻辑,比塞进一个账户更简单、更符合"零运维"。同属一个 RH 登录,不新增 OAuth/CSV 这类运维负担,不违反"不想要太多账户"的初衷(那条顾虑针对的是跨多个不同券商) |
| D2a | **两账户模型差异** | 两个账户跑**同一套** analyst 分工、risk layer、universe、决策频率,**只有模型配置(分析师模型/PM 模型)不同** | 控制变量,确保对比出来的差异是模型能力差异,不是策略设计差异;沿用原提案 D10"模型名全部做成配置项,harness 支持 A/B"的设计意图 |
| D2b | **两账户资金** | 每个账户各自 $500–1000,**总敞口 $1000–2000**(不是共享 $500–1000) | Alicia 已确认接受;§6 成本预算与风控数值按"每账户独立计算"处理 |
| D3 | 决策频率 | 每日收盘后一次,两个账户同步执行 | 与"零运维"和"不需要中频"的结论一致;RH Agentic 本身也不适合中频(见 §7 官方资料核验) |
| D4 | Agent 分工 | 每个账户内部:3 个独立 analyst 打分 + PM 聚合(强模型) | 沿用 Claude 提案,是本项目的学习核心 |
| D5 | **基线 = 开放式 shadow 孵化池(本次拍板)** | 除两个真钱账户外,系统维护一个**不下真实订单**的 shadow 孵化池:起步至少包含①均值回归、②SPY/QQQ 被动持有 两条固定基准,池子本身**开放**,之后可以随时加入新的候选——新的模型配置(Model Config C/D...)或新的策略设计(趋势跟踪、情绪驱动等),数量不预设上限 | 没有基线就无法判断"multi-agent 架构本身"以及"模型选择"是否真的带来增量;开放式设计让日后测试新想法不需要改架构,只需要注册一个新 candidate |
| D5a | **Shadow → 真钱账户 转正门槛(本次拍板)** | 候选必须同时满足:①在 shadow 池里连续跑满**至少 8 周**;②同一窗口内**同时跑赢**均值回归基线和 SPY/QQQ 被动持有;③无重大执行 bug、risk layer 校验通过。满足后系统只生成通知,**不自动开户**——是否真的开一个新 RH 账户、投入 $500–1000,由 Alicia 人工拍板 | 8 周窗口与 Phase 1 gate 一致,避免用不同标准制造混淆;"同时跑赢两条基准"确保转正的策略是真的有增量,不是运气;开户/入金是重大财务决策,保留人工最后一步,符合"实盘决策与责任归 Alicia"的边界声明,也不违反"零运维"(这是稀有的一次性决策,不是日常操作) |
| D6 | Risk layer | 规则只存在于代码,不存在于 prompt;每个真钱账户独立套用同一组风控参数(基于各自账户自身权益计算);所有拦截/裁剪记录 `{原始指令, 触发规则, 实际执行, account_id}` | 不可协商;account_id 只是审计标签,不是 Codex 式跨策略共享账本,不引入冲突处理复杂度 |
| D7 | 资金投入节奏 | Paper 验证通过后**两个账户同时直接投入各自 $500–1000**,不设起步阶梯、不要求前 20 笔人工逐笔确认 | Alicia 已确认接受这个节奏 |
| D8 | 交易 universe | 两账户共用同一份固定白名单 ~15 只高流动性大盘股 + 2–3 只 ETF,每月人工 review(这是唯一保留的、频率很低的人工步骤) | 隔离选股与择时能力,同时把"人工"成本压到月级;两账户共用白名单也是控制变量的一部分 |
| D9 | v1 禁止 | 做空、杠杆、options | adapter 层直接拒绝,两账户一致 |
| D10 | 部署 | GitHub Actions daily scheduled workflow,同一次 run 里顺序/并行处理两个账户 | 免费、自动;已知限制见 §7 |
| D11 | Fidelity/Schwab 监控 pipeline | **v1 不做**(原 Claude 提案 §5"方案3") | 需要 Schwab OAuth 续期或 Fidelity 每周手动 CSV,两者都是运维负担,与"零运维"直接冲突;如果你后续仍想要多账户周报,这是一个独立项目,不在本提案范围内 |

---

## 2. 系统架构

```
┌────────────────────────────────────────────────────────────────────────┐
│  GitHub Actions (daily, after market close)                            │
│                                                                          │
│  ══════════════ 真钱账户 A(Model Config A)══════════════               │
│  Market Data ──► Analyst A/B/C (Model Config A) ──► PM (Model Config A) │
│                        score+confidence(logged)         │ target orders │
│                                                            ▼            │
│                                              RISK LAYER A(独立实例,     │
│                                              基于账户A自身权益计算)      │
│                                                            │            │
│                                              RH Agentic 账户 A          │
│                                                                          │
│  ══════════════ 真钱账户 B(Model Config B)══════════════               │
│  Market Data ──► Analyst A/B/C (Model Config B) ──► PM (Model Config B) │
│                        score+confidence(logged)         │ target orders │
│                                                            ▼            │
│                                              RISK LAYER B(独立实例,     │
│                                              基于账户B自身权益计算)      │
│                                                            │            │
│                                              RH Agentic 账户 B          │
│                                                                          │
│  ══════════════ Shadow 孵化池(轻量 strategy_ledger,不下真实订单,开放式)══ │
│  Deterministic Baseline(均值回归) ──► 虚拟 intended order(纯记账)       │
│  SPY / QQQ buy-and-hold ────────────► 虚拟净值曲线(纯记账)              │
│  Candidate C / D / ...(新模型配置或新策略设计,随时可加)──► 虚拟记账,    │
│      同样过一遍(虚拟)risk layer,与真钱账户逻辑一致                     │
│           │                                                            │
│           ▼ 满足 D5a 转正门槛(8周+跑赢基准+无bug)时                    │
│      生成通知 ──► Alicia 人工批准 ──► 开新 RH 账户,变成真钱账户        │
│                                                                          │
│  真钱账户与 shadow 线,同一次 run 里一起产出可比较的净值曲线              │
└────────────────────────────────────────────────────────────────────────┘
```

**关键设计约束**:

- Analyst 输出 schema:`{ticker, direction, score∈[-1,1], confidence∈[0,1], rationale}`,全部落盘,并打上 `account_id`(A/B)方便复盘时区分。
- **两个真钱账户完全独立**:各自的 risk layer 实例、各自的 execution adapter 调用、各自的 broker 对账单。不共享账户,因此不需要 Codex 式的"跨策略共享账户"冲突处理逻辑(谁能持有哪个标的、禁止静默对冲、虚拟账本与 broker 对账的强一致性校验)——这套复杂度被两账户隔离天然规避掉了。
- **Shadow 孵化池**是轻量版 `strategy_ledger`:池内每个 candidate(均值回归、SPY/QQQ,以及日后加入的新模型配置/新策略)只做纯虚拟记账(价格数据或虚拟 LLM 决策 → mark-to-market),从不调用 execution adapter、不触碰任何真实账户,因此不存在资金冲突问题,复杂度远低于 Codex 提案里给真钱多策略设计的那套账本。池子开放意味着加新 candidate 只是注册一条新记录,不需要改动架构。
- **Shadow → 真钱 转正是唯一允许账户数量增长的路径**:candidate 连续 8 周同时跑赢均值回归基线和 SPY/QQQ、且无执行 bug,系统才生成通知;是否真的开新 RH 账户、投入资金,由 Alicia 人工批准,系统不会自动开户或自动入金。
- Risk layer 与 prompt 的分工:prompt 里的风控是*建议*,代码里的风控是*约束*,两个账户各自套用同一套风控参数值,但状态(今日已开仓数、当前回撤等)完全独立。
- Execution adapter 可插拔,v1 启用 Alpaca paper(验证)与 RH Agentic(两个真钱账户复用同一套 adapter 实现,只是 credential/account 不同)。

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

所有被拦截/裁剪的指令写入日志:`{原始指令, 触发规则, 实际执行, account_id}`。

**关于"零运维"与风控通知的关系**:上表里除了每月一次的白名单 review,其余全部自动运行。只有某个账户触发 10%/15% 回撤熔断这种**低概率事件**时,系统才会主动通知你——这不是日常运维,是安全阀,性质不同。两个账户各自独立触发,互不拖累;如果系统按设计运行,你大概率整个 Phase 1/2 都不会收到任何需要处理的通知。

**关于 kill switch 的诚实说明(官方资料核验结果)**:Robinhood 官方文档**没有**提供"一键立即清仓"的现成 kill switch 产品能力,只能撤销 pending order;官方文档本身也提示 agent 可能"difficult to monitor or stop in real time"。本系统的"kill switch"实际含义是:代码层面的开关能立刻停止生成新订单、撤销所有 pending 订单;已持有的仓位需要用正常卖单逐步平掉,不是瞬时清空。这个限制写进代码注释和 runbook,避免高估这项能力。

---

## 4. Baseline & Benchmark(复盘系统核心)

复盘/周期性报告(不是日常运维,是自动生成的记录文件)起步包含**四条曲线**的对比,**之后随 shadow 池加入新 candidate 会持续增加**:

1. **账户 A 曲线**:Model Config A 的 3-analyst + PM 聚合后,经过 risk layer A 的实际净值(真钱)。
2. **账户 B 曲线**:Model Config B 的 3-analyst + PM 聚合后,经过 risk layer B 的实际净值(真钱)。
3. **均值回归 baseline 曲线**:同一 universe、同一时间点,用简单确定性规则(如 N 日偏离均值超过阈值反向开仓)生成的 intended order,纯虚拟记账,不下单、不受任何 LLM 影响。
4. **SPY / QQQ 被动持有曲线**:从两个真钱账户实际启动交易的当天起,把等额本金买入 SPY 和 QQQ 并持有至今的净值,纯记账,不下单。
5. **(开放)Shadow candidate 曲线**:每个新加入孵化池的模型配置或策略设计各一条,纯虚拟记账,持续对照 8 周转正门槛(见 D5a)。

评估维度:
- **模型选择增益**:账户 A vs 账户 B——同样的 analyst 分工、同样的 risk layer、同样的 universe,只有模型不同,差异就是模型能力的差异(这是本次范围扩展最核心的学习目标)。
- **agent 架构增益**:账户 A/B 分别相对均值回归 baseline 的增益——判断 multi-agent 决策本身是否比一个简单规则更好。
- **主动管理增益**:账户 A/B、baseline 分别相对 SPY/QQQ 被动持有的增益——判断这一整套系统是否值得做,相对什么都不做(买指数)有没有优势。
- 每个 analyst 的方向准确率、confidence calibration(reliability diagram),按账户分别统计。

**任何一条对比曲线的计算逻辑本身是一次性写好的代码,不需要你手动维护。**

---

## 5. Phase 计划

- **Phase 0 — 搭建**(~1–2 周):项目骨架、risk layer + 单测(含"LLM 越权指令被拦截"的对抗性测例,两账户各一套独立实例)、Alpaca paper 接入(单账户验证即可)、Model Config A/B 两套配置跑通、均值回归 baseline + SPY/QQQ 记账逻辑。
- **Phase 1 — Paper**(8 周):Model Config A + Model Config B 两套 3-analyst+PM 全量运行(仍在 Alpaca paper,不需要开两个 paper 账户,同一 paper 账户内用两个 `account_id` 标签区分即可)+ baseline + benchmark 同步运行,每日自动记录决策链与四条净值曲线。
  - Gate(工程 sanity check,不证明 alpha):连续跑满 8 周;两套配置都无重大执行 bug(无重复下单、无风控穿透、无静默失败);四条曲线数据完整、可复盘。
  - **明确注记**:Alpaca paper 不模拟 market impact、订单信息泄露、延迟滑点、队列位置、价格改善、监管费、股息,paper-only 账户只有 IEX 数据权限。这意味着 paper 阶段的表现**天然比实盘乐观**,gate 通过不代表实盘也会通过,只代表工程没有明显 bug。
- **Phase 2 — RH Agentic 实盘(两个账户)+ Shadow 孵化池持续运行**:开设两个 Robinhood Agentic 账户,各自直接投入 $500–1000(总敞口 $1000–2000),账户 A 换 Model Config A 的 RH MCP adapter,账户 B 换 Model Config B 的,均不设人工逐笔确认;开启交易通知,确认"代码开关能立即停止新订单"这条能力在两个账户上都经过实测。**与此同时,shadow 孵化池持续跑**:均值回归、SPY/QQQ 两条基准线常驻,后续可随时注册新的 candidate(新模型配置或新策略设计),每个 candidate 独立计时、独立判断 D5a 转正门槛,互不影响真钱账户的运行。
- **Shadow → 真钱转正(常态化流程,不是单独 Phase)**:任意 candidate 满足 D5a 门槛(8 周 + 同时跑赢均值回归和 SPY/QQQ + 无 bug)时,系统生成通知;Alicia 批准后开新 RH 账户、投入 $500–1000,该账户从此按 Phase 2 的所有规则(独立 risk layer、不设人工逐笔确认)运行。这是账户数量增长的唯一途径,增长速度由 Alicia 的批准节奏决定,系统不会自作主张扩张。
- **Phase 3(可选,需你另外拍板才启动)**:换 broker(如 Schwab)、加盘中频率、辩论式架构 ablation——这些会重新引入运维负担(OAuth 续期、更多监控面等),默认不做。(注:增加模型配置/策略候选**不需要**等 Phase 3,走 shadow 孵化池常态化流程即可。)

**GitHub Actions 已知限制**:官方文档说明高负载时 scheduled job 会被延迟,负载足够高时甚至可能被丢弃。这对"每日收盘后一次"的低频场景影响可以接受(延迟几分钟到几小时不影响策略逻辑),但意味着不能假设它能精确卡在开盘那一刻执行。系统会加一条自动检查(当天该跑的 job 没跑,发通知),这也是一次性写好的代码,不是手动巡检。

---

## 6. 成本预算

| 项 | 预估 | 说明 |
|---|---|---|
| Analyst LLM 调用(账户 A + 账户 B) | ~$10–20/月 | 便宜模型 × 3 analyst × ~15 标的 × 每日一次 × 2 套配置 |
| PM LLM 调用(账户 A + 账户 B) | ~$10–30/月 | 强模型,每日一次聚合 × 2 套配置(两套模型可能价位不同,取上限估算) |
| 部署(GitHub Actions) | $0 | 免费额度内 |
| 市场数据 | $0 | yfinance / Alpaca free tier,两套配置共用同一份行情数据,不重复拉取 |
| Alpaca paper | $0 | 免费 |
| **月度合计(账户 A+B)** | **≤ $60** | 超预算 = 设计问题,先降调用量再谈换模型 |
| Shadow candidate 边际成本 | 非 LLM 策略(均值回归等)≈ $0;LLM 驱动的新模型配置候选,每加一个约 +$10–20/月 | 均值回归、SPY/QQQ 两条固定基准不消耗 LLM 预算;之后加入孵化池的候选如果是新模型配置,按同一套 analyst+PM 调用量估算,超过 $60+候选数×$20 视为异常,提醒你该考虑精简候选数量 |

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
| RH 允许最多 10 个 self-directed investing account,Agentic 账户算在其中;但账户与 agent 连接的对应关系(是否可独立连接不同 agent)官方文档未明确说明 | [Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)、[Trading with your agent](https://robinhood.com/us/en/support/articles/trading-with-your-agent/) | 支持 D2(两账户可行);Phase 0 需要**实测确认**两个 Agentic 账户能否各自独立连接不同的 agent/API credential,这是本提案唯一还没有官方文档背书、需要动手验证的假设 |

---

## 8. 明确排除的范围(v1 不做,避免范围膨胀)

- 多 broker(Schwab/Fidelity)接入与周报 pipeline——运维负担与本次"零运维"约束冲突。
- **Codex 式"共享账户多策略"虚拟账本**(谁能持有哪个标的、禁止静默对冲、虚拟账本与 broker 强一致性对账)——两个真钱策略各自有独立账户,天然不需要这套冲突处理复杂度。**仅有的轻量 `strategy_ledger` 用于两条 shadow 线(均值回归、SPY/QQQ)的纯虚拟记账,不涉及真实资金,不需要冲突处理逻辑。**
- 税务 lot 管理、wash-sale 检测——超出学习目标范围。
- 中频/盘中交易——与"零运维"约束冲突,留给 Phase 3 单独评审。
- 辩论式 multi-agent 架构——留作日后 ablation,不在 v1。
- **Shadow candidate 自动转正**——转正必须经过 D5a 门槛判断 + Alicia 人工批准,系统任何情况下都不能自己开户或自己入金。

---

## 9. 边界声明

Claude(任何界面)负责设计、代码、backtest 工具、复盘 pipeline;不执行交易、不持有密钥、不给具体标的买卖建议。实盘决策与责任归 Alicia。所有 API key 只走环境变量 / GitHub Actions secrets,永不进仓库。
