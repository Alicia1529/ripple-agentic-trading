# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-26 00:01 PDT — Shadow branch corrected in the system diagrams

- Outcome: the Mermaid diagrams in [`ARCHITECTURE.md`](ARCHITECTURE.md), [`README.md`](../README.md), and [`PROPOSAL.md`](../PROPOSAL.md) now show shadow skipping only the Robinhood call, not the risk verdict or the T+1 marketability check.
- Correction: the previous "assumed T+1 quote fill" label understated [`shadow.py`](../ripple/shadow.py), which records `not_filled`/`limit_not_marketable` when the 9:35 quote misses the planned limit.
- Scope: diagram labels and evidence edges only; prose, code, configurations, and state are unchanged.
- Evidence: all three diagrams render through mermaid-cli; `git diff --check` passes.

## 2026-08-26 00:03 PDT — V2 Lite unleveraged buying-power basis

- Outcome: [`growth_momentum_v2_lite.md`](../strategies/growth_momentum_v2_lite.md) may use broker-authorized pending-deposit early access only through `unleveraged_buying_power`; margin and additive pending deposits remain forbidden.
- Execution: [`EXECUTION_LIVE.md`](../routines/EXECUTION_LIVE.md) maps the same fresh broker value to `execution_context.account.cash`; deterministic baseline mismatch still aborts.
- Scope: policy and routine text only; no schema, risk, config, Decision, Execution, or broker write changed.
- Evidence: all 53 tests and `git diff --check` pass.
- Next/risk: a future live Decision may use this basis; if Robinhood reduces early access before Execution, baseline matching safely aborts the plan.

## 2026-08-26 00:22 PDT — Account A manual Live Decision

- Outcome: manual `growth_momentum_v2_lite` Decision published plan `7c532d74-af10-5285-ba6f-49cad0c388f6` for trade date 2026-08-27 with zero orders and 100% cash.
- Rationale: Robinhood returned the expected 2026-08-25 daily bar as interpolated with zero volume across the universe, so the SPY regime and candidate eligibility were not verifiable.
- Evidence: [`2026-08-27`](../state/accounts/account_a/trading_days/2026-08-27) is credential-free, schema-valid, and strategy/account bound; 53 tests pass.
- Scope/risk: Decision only; no Execution, shadow, review, placement, cancellation, or broker write occurred. A later Execution still requires separate authority and current baseline matching.
