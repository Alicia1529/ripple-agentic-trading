# CLAUDE.md — Trading Agent System

> 完整设计决策见根目录 **[/PROPOSAL.md](../PROPOSAL.md)**(最终版,取代本文件夹里的 PROPOSAL.claude.v0.md)。改代码前先读它。

## 项目一句话

自建 minimal multi-agent 交易系统:3 个独立 analyst(便宜模型)打分 + PM(强模型)聚合 → **代码强制 risk layer** → 可插拔 execution adapter(Alpaca paper → RH Agentic MCP)。目标是学习 agent 系统设计,不是收益。

## 工作约定(不可协商)

1. **Risk layer 规则只存在于代码里,不存在于 prompt 里。** prompt 里的风控是建议,代码里的才是约束。任何人(包括 LLM 输出)不能通过改 prompt 绕过风控。
2. Risk layer 的每条规则必须有单测,包括"LLM 输出越权指令被拦截"的对抗性测例。
3. 所有 analyst/PM 的输出按 schema 落盘:`{ticker, direction, score, confidence, rationale}`。被 risk layer 拦截/裁剪的指令记录 `{原始指令, 触发规则, 实际执行}`。
4. 模型名、白名单、风控数值全部是配置项(config 文件),不硬编码。
5. Execution adapter 实现同一接口;Alpaca paper / Alpaca live / RH MCP 切换只改配置。
6. API keys 只走环境变量 / GitHub Actions secrets,永不进仓库。
7. v1 禁止:做空、杠杆、options。adapter 层直接拒绝。

## Risk Layer 数值(v1)

| 规则 | 值 |
|---|---|
| 单一标的仓位上限 | 20% |
| 单日新开仓 | ≤ 3 笔 |
| 单日亏损熔断 | −5% → 当日只许平仓 |
| 累计回撤熔断 | −15% → 停机,人工重启 |

## Cost Budget

### 月度运行成本(上限 $30/月)

| 项 | 预估 | 说明 |
|---|---|---|
| Analyst LLM 调用 | ~$5–10/月 | 便宜模型 × 3 analyst × ~15 标的 × 每日一次 |
| PM LLM 调用 | ~$5–15/月 | 强模型,每日一次聚合 |
| 部署(GitHub Actions) | $0 | public/private repo 免费额度内 |
| 市场数据 | $0 | yfinance / Alpaca free tier |
| Alpaca paper | $0 | 免费 |
| **月度合计** | **≤ $30** | 超预算 = 设计问题,先降调用量再谈换模型 |

### 一次性 / 资本项(不计入月度)

| 项 | 金额 | 性质 |
|---|---|---|
| RH Agentic 账户入金 | $500–1000 | 本金,Phase 2 才入,可全损 |
| Robinhood Gold(如需) | ~$5/月 | 仅当 Agentic 功能要求时才开,Phase 2 前确认 |

### Cost 观测要求

- 每次 run 记录 token 用量和预估成本,写入 run log。
- 月度成本汇总进周报 pipeline(方案3)的附录。
- 任何单日成本 > $3 视为异常,检查是否有重试风暴或 prompt 膨胀。

## Phase 状态

- [ ] Phase 0:骨架 + risk layer(带单测)+ Alpaca paper 接入 + 单 analyst 端到端
- [ ] Phase 1:三 analyst 全量,paper 8 周,gate 见 PROPOSAL §4
- [ ] Phase 2:RH Agentic MCP 实盘($500–1000 隔离账户)
- [ ] Phase 3(可选):Alpaca live / 盘中频率 / 辩论式 ablation

## 边界

Claude(任何界面)负责设计、代码、backtest 工具、报告 pipeline;不执行交易、不持有密钥、不给具体标的买卖建议。实盘决策与责任归 Alicia。
