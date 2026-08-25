# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-24 22:12 PDT — README safety layers

- Outcome: documented supported deterministic checks and separated code, LLM/workflow, and human safety responsibilities in `README.md`.
- Clarity: stated the prompt-enforced execution gap and promoted the existing scope-compilation note into a dedicated Learning section.
- Behavior: documentation only; risk code, prompts, values, schemas, execution, state, and all invariants are unchanged.
- Evidence: core tests, both fixture dry cycles, internal link checks, and `git diff --check` pass.
- Next/risk: keep this summary aligned with the authoritative architecture and invariants as the live loop changes.

## 2026-08-24 22:28 PDT — Clear current documentation model

- Outcome: restored clear purpose, glossary, agent routing, system walkthrough, responsibility, artifact, timing, and safety structures without reviving retired architecture.
- Scope: Account A alone owns the hosted path; Account B remains a tested fixture lane with no hosted Decision, Execution, schedule, or MCP binding.
- Sources: aligned Proposal, Architecture, Decisions, Invariants, TODO, Runbook, README, and routine contracts; code and risk behavior are unchanged.
- Evidence: 30 core tests, both fixture dry cycles, internal links, and `git diff --check` pass.
- Next/risk: complete Account A hosted acceptance and the reviewed live loop in `docs/TODO.md`.

## 2026-08-24 23:12 PDT — Strategy catalog and shadow execution

- Outcome: added filename-identified account configs, strategy validation/attribution, live/shadow/dry-run cohorts, and T+1 quote Shadow Fills with ending virtual state.
- Migration: `account_a` is manual dry-run, `account_b` is shadow; uppercase state remains immutable legacy evidence.
- Structure: split four routine contracts and aligned Proposal, Architecture, Decisions, Invariants, Runbook, TODO, README, and glossary.
- Evidence: 36 core tests, catalog/cohort commands, both fixture cycles, artifact inspection, internal links, credential scan, and `git diff --check` pass.
- Next/risk: configure shadow schedules; live loop remains gated, and both lanes still select the same strategy.
