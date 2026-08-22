# Trading Agent System — Design Proposal

> Status: **Agreed (shared understanding reached)** · Date: 2026-08-21
> Owner: Alicia · Role of Claude: design & code, no trade execution, no buy/sell advice

---

## 0. 定位(为什么做这个)

**目标不是赚钱。** $500–1000 的本金在金钱意义上无关紧要;本项目的真实目标:

1. **学习 agent 系统设计**:亲手搭一个「不可信 LLM 决策层 + 确定性代码风控层」的完整系统 —— 与 LLM safety 系统设计(xAI 方向)同构。
2. **可 scale 的 pilot**:架构上留好换 broker、换模型、加频率的口子,验证后可放大。

由此推出的设计原则:**优先选架构上有教育价值的路线,而不是短期收益最优的路线。**

---

## 1. 决策记录(Design Tree,已闭合)

| # | 决策点 | 结论 | 关键理由 |
|---|--------|------|----------|
| D1 | 真实目标 | 学习 + 可 scale pilot | 本金太小,收益无意义 |
| D2 | HFT(方案1) | **放弃** | 散户无延迟优势;小资金做市 spread 覆盖不了 adverse selection |
| D3 | 资产类别 | 美股 | 生态成熟(Alpaca/TradingAgents 系),与监控侧同市场 |
| D4 | 开发/验证环境 | Alpaca **paper trading** | 唯一有完整 paper 环境的主流路径 |
| D5 | 实盘执行 | **Robinhood Agentic Trading**(MCP)起步,视情况迁 Alpaca live | 隔离账户 + kill switch + trade preview = 现成的 blast-radius 控制;本身是生产级 agent 护栏 case study |
| D6 | Agent 系统 | **从零自建 minimal 版**,不 fork | fork 学到的是配置别人的系统;自建每层决策都是自己的 |
| D7 | 决策频率 | **每日收盘后一次**,次日开盘执行 | 与全职工作兼容;API 成本低一个数量级;避开盘中噪音 |
| D8 | Agent 分工 | 3 个独立 analyst 打分 + PM 聚合(非辩论式) | **可评估性**:每个 analyst 的准确率与 calibration 可单独统计;辩论式留作日后 ablation |
| D9 | 交易 universe | **固定白名单** ~15 只高流动性大盘股 + 2–3 只 ETF,每月人工 review | action space 白名单化;隔离"选股能力"与"择时能力" |
| D10 | 模型选型 | analyst 用便宜模型,PM 用强模型;模型名全部做成配置项 | Alpha Arena 教训:模型选择是最大方差来源,harness 要支持 A/B |
| D11 | 月度 API 预算 | **≤ $30/月** | daily × ~15 标的 × 4 次调用,便宜模型足够 |
| D12 | Paper gate | **宽松版**(见 §4) | 30–60 天样本量不足以证明 alpha;gate 定位是工程 sanity check,不是收益证明 |
| D13 | 监控数据源(方案3) | Schwab 官方 Individual Trader API(**只读**);Fidelity 每周手动 CSV | Fidelity 无散户公开 API;低频需求配不上聚合器的信任面 |
| D14 | 周报定位 | **alert on facts, not opinions** | 输出触发注意的事实,不输出 buy/sell 指令;决策归人 |
| D15 | 部署 | **GitHub Actions** scheduled workflow | 免费、logs 自动留档(决策链复盘)、secrets 内建;加盘中频率再迁云实例 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (daily, after market close)             │
│                                                         │
│  Market Data ──► Analyst A (technical)   ──┐            │
│  (yfinance /     Analyst B (fundamental) ──┼─► PM Agent │
│   Alpaca data)   Analyst C (news/sent.)  ──┘   (strong  │
│                  [cheap models]                 model)  │
│                       │                           │     │
│                  score + confidence          target     │
│                  (per ticker, logged)        orders     │
│                                                   │     │
│              ┌────────────────────────────────────▼───┐ │
│              │  RISK LAYER  (pure code, no LLM)       │ │
│              │  拦截/裁剪一切越权指令 — LLM 无权 override│ │
│              └────────────────────┬───────────────────┘ │
│                                   │                     │
│                      Execution Adapter (可插拔)          │
│                   ┌───────────────┴──────────────┐      │
│              Alpaca paper                RH Agentic MCP  │
│              (Phase 1)                   (Phase 2, live) │
└─────────────────────────────────────────────────────────┘
```

关键设计约束:

- **Analyst 输出 schema**:`{ticker, direction, score∈[-1,1], confidence∈[0,1], rationale}`,全部落盘。confidence 的 calibration(reliability diagram)本身是一个观测目标。
- **PM 聚合**:初版加权平均(权重可配),权重日后可基于各 analyst 历史准确率数据驱动地调。
- **Risk layer 与 prompt 的分工**:prompt 里的风控是*建议*,代码里的风控是*约束*。所有硬限制只存在于 execution adapter 之前的代码层。
- **Execution adapter 可插拔**:Alpaca paper / Alpaca live / RH MCP 三个实现同一接口,切换只改配置。

---

## 3. Risk Layer 规格(代码强制)

| 规则 | 数值 | 触发后行为 |
|------|------|-----------|
| 单一标的仓位上限 | 账户总值 **20%** | 裁剪订单至上限 |
| 单日新开仓上限 | **3 笔** | 超出的订单直接丢弃并记录 |
| 单日亏损熔断 | 当日浮亏 **−5%** | 当日禁止一切新开仓,只允许平仓 |
| 累计回撤熔断 | 高点回撤 **−15%** | **系统整体停机**,需人工重启 |
| 禁止项(v1) | 做空、杠杆、options | adapter 层直接拒绝 |

所有被拦截/裁剪的指令写入日志:`{原始指令, 触发规则, 实际执行}` —— 这份日志同时是 agent 越权行为的观测数据。

---

## 4. Phase 计划与 Paper Gate

**Phase 0 — 搭建**(~1–2 周):项目骨架、risk layer + 单测、Alpaca paper 接入、单 analyst 跑通端到端。
**Phase 1 — Paper**(8 周):三 analyst 全量运行,每日自动记录决策链与净值。

Gate 标准(通过即允许 Phase 2):
1. Paper 连续跑满 **8 周**;
2. Max drawdown **< 15%**;
3. 无重大执行 bug(无重复下单、无风控穿透、无静默失败)。

> 明确注记:此样本量**不足以证明 alpha**,任何收益结果都可能是运气。Gate 验证的是工程质量。跑赢 SPY 只作长期观测指标,不作门槛。

**Phase 2 — RH Agentic 实盘**:$500–1000 入隔离账户,同一 agent 换 RH MCP adapter;开启 trade 通知,熟悉 kill switch。
**Phase 3(可选)**:迁 Alpaca live 获得更细执行控制;加盘中频率;辩论式架构做 ablation 对比。

---

## 5. 监控侧(方案3,独立 pipeline)

每周一早生成报告:

1. 持仓快照 + 周变动归因(每只涨跌对组合的贡献)
2. 集中度与风险暴露(行业/单票占比、与大盘相关性)
3. 每只持仓事件摘要(财报日期、重大新闻)
4. Watchlist 同样分析
5. **「值得你看一眼」清单** — 纯事实提示(如 "X 财报下周四"、"Y 已占组合 32%,超集中度线"),不含买卖建议

数据源:Schwab Individual Trader API(OAuth,只读 scope)+ Fidelity 每周手动导出 CSV(固定放 `data/fidelity/` 目录,脚本自动 pick up)。

---

## 6. 成本预算

| 项 | 月成本 |
|----|--------|
| LLM API(analyst 便宜模型 + PM 强模型) | ≤ $30 |
| 部署(GitHub Actions) | $0 |
| 市场数据(yfinance / Alpaca free tier) | $0 |
| **合计** | **≤ $30/月** |

---

## 7. 参考实现(读,不 fork)

- **TauricResearch/TradingAgents** — multi-agent 架构与角色划分的参考
- **zhound420/swarm-trader** — code-enforced risk layer(任何 agent 不可 override)的参考实现
- **virattt/ai-hedge-fund** — analyst persona 设计参考
- **nof1 Alpha Arena**(blog + 公开日志)— prompt 结构(exit plan、confidence、invalidation conditions)与「同 harness 不同模型方差极大」的实证教训
- **hummingbot**(存档参考)— 已放弃的 HFT 线,如日后好奇做市机制可读

---

## 8. 边界声明

- Claude 负责:系统设计、代码、backtest 工具、报告 pipeline。
- Claude 不做:执行任何交易、持有任何密钥、给出任何具体标的的买卖建议。
- 所有 API key 由 Alicia 持有(GitHub Actions secrets / 本地 env);所有实盘决策与责任归 Alicia。
