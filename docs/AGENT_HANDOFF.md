# Agent handoff

Read these rules and the three entries in this file before work. Before handing off, append one chronological entry with local timestamp, outcome, evidence, next action, and only material risk. Keep each entry within 100 words and five bullets, link to authoritative files instead of duplicating them, and retain exactly the latest three entries total.

## 2026-08-25 20:57 PDT — Config-owned deployment inventory

- Outcome: made [`config/*.json`](../config/) the sole authority for current lane identity, mode, strategy, universe, and risk bindings.
- Docs: architecture, proposal, README, runbook, TODO, and routines now describe stable contracts and discover cohorts through the catalog instead of caching concrete bindings.
- Strategy: moved compiler invocation into the selecting Strategy Spec; historical state and handoff facts remain intact.
- Evidence: catalog validation, deployment-detail scans, `git diff --check`, and all 50 core tests pass.
- Risk/next: generic fixture examples require substituting IDs and paths returned by catalog inspection; runtime behavior and configuration are unchanged.

## 2026-08-25 21:14 PDT — Existing execution-timing rationale

- Outcome: captured why the existing prior-evening Decision and T+1 9:35 AM Execution fit both Strategy Specs; the final concise rationale now lives in [`README.md`](../README.md#why-decision-is-prior-evening-and-execution-is-at-935-am).
- Evidence: ties completed-session inputs, frozen prior-close limits, opening-gap checks, and event-signal timing to local contracts and primary NYSE, SEC, and original-research sources.
- Boundary: this is analysis, not a schedule change, trading authorization, or architecture decision; noon and 3 PM remain non-canonical comparisons.
- Risk/next: 9:35 superiority is structurally reasoned, not empirically proven; any observation study or timing change needs separate review.

## 2026-08-25 21:16 PDT — Timing rationale consolidated

- Outcome: removed the standalone timing-analysis document and kept only a concise explanation in [`README.md`](../README.md#why-decision-is-prior-evening-and-execution-is-at-935-am).
- Scope: no schedule, Strategy Spec, routine, configuration, state, or runtime behavior changed.
- Evidence: the README explains completed-session inputs, T+1 opening confirmation, price-anchor freshness, event timing, and Decision/Execution separation without concrete lane bindings.
- Risk/next: the rationale remains structural rather than empirical; any timing experiment still requires separate reviewed shadow evidence.
