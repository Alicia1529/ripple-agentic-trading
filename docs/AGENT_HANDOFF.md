# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-24 22:05 PDT — GitHub README refresh

- Outcome: rewrote `README.md` as an accessible project overview centered on AI-native development and agentic trading.
- Clarity: added the loop, safety boundaries, quick start, repository map, learning reference, and accurate hosted/live status.
- Behavior: documentation only; trading logic, configurations, schemas, timing, state, and all invariants are unchanged.
- Evidence: README commands and links checked against the repository; core tests and `git diff --check` pass.
- Next/risk: keep the status section aligned with `docs/TODO.md` as hosted and live gates change.

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
