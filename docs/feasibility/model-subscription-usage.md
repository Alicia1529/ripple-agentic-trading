# Model subscription usage for the daily analyst workflow

Status: research snapshot, 2026-08-22

## Question

Can one ChatGPT Plus/Codex subscription and one Claude Pro/Claude Code
subscription reliably run Ripple's unattended daily workload: three analyst
runs followed by one PM run, or about four model invocations per model account
per trading day?

## Conclusion

**Do not make either consumer subscription the reliability boundary for the
daily production workflow.** Four short runs per trading day are a plausible
fit for light personal use, but neither vendor promises a fixed number of
equivalent runs, reserved capacity, or a service level for the subscription.
Consumption depends on task complexity, context, model, tools, and concurrent
usage; scheduled and cloud runs also consume the account's allowances.

Subscription-backed runs are suitable for a monitored feasibility trial and
may reduce early cost. The supported dependable fallback is metered API access:
an OpenAI API key for the OpenAI leg and a Claude Platform API key (or a
supported cloud provider) for the Anthropic leg. The runner should treat
subscription exhaustion or authentication expiry as a fail-closed condition,
then either use an explicitly enabled, budget-capped API fallback or skip the
cycle and alert. It must never silently change providers or models.

## OpenAI: ChatGPT Plus and Codex

### What the subscription includes

ChatGPT Plus is currently $20/month and includes Codex across the web, CLI, IDE,
and supported cloud integrations. OpenAI describes Plus as supporting "a few
focused coding sessions each week," not a fixed call quota. ChatGPT Work and
Codex share usage, and Pro is presented as a multiple of Plus limits rather
than a fixed request count. [OpenAI Codex pricing](https://learn.chatgpt.com/docs/pricing)

OpenAI says Codex consumption varies with task size and complexity, selected
model, execution location, codebase size, and duration. Usage from Codex,
ChatGPT Work, and other agentic surfaces draws from the same agentic usage and
credit pool. A task that reaches a limit may finish its current turn, but later
turns must wait, use credits, reset, or upgrade. The account exposes both a
five-hour and a weekly usage window.
[Using Codex with a ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)

Therefore, **four invocations is not a stable capacity unit**. One invocation
may consume a fraction of the allowance while a long or context-heavy analyst
run may consume much more. Other interactive activity on the same account can
also reduce the headroom available to the daily job.

### Scheduled and cloud work

Cloud delegation is included, but it is not free of the subscription limit.
OpenAI explicitly says local and cloud task cost varies by where and how the
task runs and that the relevant agentic products share the same pool.
[Using Codex with a ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)

For usage-based ChatGPT plans, OpenAI's rate card is even more explicit: local
tasks, cloud tasks, automations, code review, auto review, and delegated workers
are all metered by their actual token consumption. This is not the Plus billing
scheme, but it confirms that scheduling does not make the model work
resource-free. [ChatGPT token rate card](https://help.openai.com/en/articles/20001415-chatgpt-rate-card-enterprise-token-based-pricing)

### Unattended credentials

OpenAI documents an **API key** as the option that is "great for automation in
shared environments like CI" and supports Codex in the CLI and SDK with
token-based billing. The same pricing page does not make that production-
automation claim for a personal ChatGPT login. [OpenAI Codex pricing](https://learn.chatgpt.com/docs/pricing)

OpenAI's consumer terms also prohibit sharing account credentials,
programmatically extracting data or output, and circumventing rate limits.
Consequently, Ripple should not export, share, scrape, or repurpose a ChatGPT
session credential as a general service credential. Native Codex scheduling
under the subscribing user's own account is supported, but a custom unattended
runner should use the documented API-key path. [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/)

### Metered fallback and price level

The supported fallback is the OpenAI Responses API/Codex SDK authenticated with
an OpenAI API key. Current standard short-context prices include:

- GPT-5.6 Sol: $5.00/M input tokens, $0.50/M cached input, $30.00/M output.
- GPT-5.6 Terra: $2.00/M input, $0.20/M cached input, $12.00/M output.
- GPT-5.6 Luna: $0.20/M input, $0.02/M cached input, $1.20/M output.

OpenAI also offers Batch at a discount and higher-priced processing modes;
tools and long context can add charges. Prices and model availability are
mutable configuration, not constants to bake into the scheduler.
[OpenAI API pricing](https://openai.com/api/pricing/)

## Anthropic: Claude Pro and Claude Code

### What the subscription includes

Claude Pro includes Claude Code, and Claude app and Claude Code activity share
the same usage limits. Anthropic says consumption varies with message length,
conversation length, file attachments, project complexity, codebase size, and
auto-accept behavior. When the limit is reached, the choices are to wait for a
reset, enable extra usage, upgrade, or move to pay-as-you-go Console usage.
[Claude Code with Pro or Max](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)

Claude's error documentation describes rolling session and weekly allowances,
not a guaranteed request count. It also recommends reducing concurrency and
long context when limits bind. [Claude Code error reference](https://code.claude.com/docs/en/errors)

Thus four daily invocations are likely modest only if they remain short and
serial. They are still not guaranteed: a long-context analyst, parallel
subagents, cache misses, or unrelated account usage can exhaust the shared
allowance.

### Scheduled and cloud work

Anthropic's cloud Routines are explicitly subscription-metered. They consume
usage like interactive sessions and also have a separate per-account daily run
cap; when either cap is reached, additional runs are rejected unless metered
extra usage is enabled. Cloud sessions likewise share rate limits with all
other Claude and Claude Code activity, and parallel sessions consume more.
[Claude Code Routines](https://code.claude.com/docs/en/web-scheduled-tasks),
[Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web)

The exact daily Routine cap is account-visible rather than published as a
stable numeric guarantee. Four scheduled runs therefore need a live
preflight/usage check and an alert path, not an assumption that the subscription
will always admit all four.

### Unattended credentials

Anthropic supports non-interactive `claude -p` and documents a one-year
`CLAUDE_CODE_OAUTH_TOKEN`, generated by `claude setup-token`, specifically for
CI pipelines and scripts without browser login. The token is scoped to model
requests and still authenticates against the user's subscription.
[Claude Code authentication](https://code.claude.com/docs/en/authentication),
[programmatic Claude Code](https://code.claude.com/docs/en/headless)

This is narrower than permission to turn consumer credentials into a shared
service. Anthropic says subscription OAuth is for ordinary use of native
Anthropic applications, prohibits third-party developers from routing requests
through consumer plan credentials on users' behalf, and directs products and
services to API-key authentication. [Claude Code legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)

For Ripple, a single owner's local, low-volume scheduled proof can use the
documented subscription token. A shared, production, or capacity-sensitive
runner should use a Claude Platform API key. Even the subscription token can
expire or fail to refresh, so the job must detect authentication failure before
doing downstream work.

### Metered fallback and price level

The supported fallback is Claude Platform pay-as-you-go using an API key; the
Console supports prepaid credits and optional auto-reload. Current standard
prices include:

- Claude Sonnet 5: $2/M input tokens and $10/M output.
- Claude Sonnet 4.6/4.5: $3/M input and $15/M output.
- Claude Haiku 4.5: $1/M input and $5/M output.

Prompt-cache reads are currently 0.1x base input price; cache writes and tools
can add costs. [Claude Platform pricing](https://platform.claude.com/docs/en/about-claude/pricing),
[Anthropic API billing](https://support.anthropic.com/en/articles/8977456-how-do-i-pay-for-my-api-usage)

## Anthropic Agent SDK credit status

Anthropic announced and then paused a planned separate monthly credit for
Agent SDK and `claude -p` subscription usage. Its dated June 16 Help Center
update says the credit is unavailable and that Agent SDK, `claude -p`, and
third-party app usage continue to draw from subscription limits. This report
uses that current status; the older planned behavior preserved on the page is
reference material, not an active capacity source.
[Paused Agent SDK credit announcement](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)

## Recommended Phase -1 decision

1. Run the four-call daily workflow serially in feasibility mode, with small,
   bounded context and explicit model selection.
2. Measure actual input, cached-input, output, duration, limit rejections, and
   authentication failures for at least several trading days; never log model
   or subscription secrets.
3. Keep API fallback **off by default** until the owner configures a per-day and
   per-month spend cap. If enabled, record which provider/model served each run.
4. Before the PM step, require all three analyst results from the same cycle;
   do not substitute a missing analyst silently after a subscription rejection.
5. Treat subscription limits as opportunistic capacity. Use metered APIs for
   any production SLO or unattended workflow whose missed daily run is
   unacceptable.

## Remaining unknowns to prove locally

- The actual token/context footprint of each of Ripple's three analyst prompts
  and PM synthesis prompt.
- The current account-specific Codex five-hour/weekly headroom and Claude
  rolling/weekly headroom after the owner's unrelated interactive usage.
- The current per-account daily cap for Claude Routines and whether four runs
  are admitted at the desired times.
- Whether OpenAI native scheduled tasks expose enough deterministic output and
  failure state for Ripple's orchestration contract, or whether the runner must
  invoke the API directly.
- How each vendor reports a partial run that starts before a limit is reached
  but exhausts allowance mid-cycle.
- Whether an enabled metered overage/fallback switches automatically; Ripple
  should test and disable any silent billing transition it cannot audit.
