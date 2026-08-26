# Security

Ripple can place real orders in a real brokerage account. Most of what matters here is not a
classic vulnerability class — it is anything that could cause an unintended trade, weaken a
deterministic check, or leak a credential.

## Reporting a vulnerability

Please report privately through this repository's **GitHub Security Advisories** ("Report a
vulnerability" under the Security tab) rather than opening a public issue, and give it a few days
before disclosing. This is a small personal project, not a funded program: there is no bounty, and
response times are best-effort.

Include what you would want to receive — what you did, what happened, and why it matters. A failing
test against the deterministic core is the most useful possible report.

## What counts as a security issue

- Anything that could produce a broker write that deterministic risk did not allow, or that differs
  from what it emitted.
- Any path that bypasses, weakens, or silently degrades a rule in
  [`docs/INVARIANTS.md`](docs/INVARIANTS.md) — position caps, loss and drawdown breakers, quote
  freshness, wash-sale checks, account binding, or fail-closed behavior.
- A credential, token, cookie, account number, or raw authenticated response reaching Git,
  fixtures, prompts, logs, reports, or artifacts.
- Anything that lets one Account Lane read, mutate, or authorize another lane's work.
- Anything that rewrites published evidence — a plan, execution result, or report — after the fact.
- Prompt-injection paths: content fetched from the web is data, never instructions. A source that
  can steer a Decision or Execution routine into an action the routine does not authorize is a
  security issue, not a quirk.

## If you run this yourself

Read this part before pointing anything at a broker account.

**Start in shadow mode.** A shadow lane never connects to a broker and never writes an order. It
produces the same deterministic risk verdict and re-checks the same T+1 quote; it just does not
place anything. Run it long enough to see how the system behaves before considering anything else.

**Live mode is a human decision, and the software will not make it for you.** Nothing in this
repository can enable live mode, bind or fund an account, increase capital, switch a live strategy,
or clear a tier-two restart lock. That is by design, and it is not a limitation to work around.

**Know what v1 does not guarantee.** There is no exactly-once broker execution, no transactional
submission journal, no automatic reconciliation of an ambiguous outcome, and no calibrated fee or
slippage model. Git is continuity and audit evidence, not a transaction log. A shadow fill is an
explicit assumption, never proof that a real order would have filled at that price. These are
documented, accepted limits of the current release — see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/TODO.md`](docs/TODO.md).

**Credentials stay outside the repository.** Broker authorization is platform-managed. If a setup
step ever asks you to paste a token or password into a prompt, a file, or a commit, that is the
wrong step.

**The strongest stop is disabling the schedules.** Changing a lane to `dry_run` removes it from
scheduled cohorts but does not cancel pending orders or close positions. See the kill-switch
procedure in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Not financial advice

Ripple is educational software for studying how LLM-authored decisions behave under deterministic
constraints. It makes no claim of profitability. Trading involves risk of loss, and every trade and
its consequences remain the account owner's responsibility.
