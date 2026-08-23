# X API as a supplementary equity-news source

**Checked:** 2026-08-22
**Scope:** Official X developer documentation, pricing, and terms only. No authenticated API or Developer Console access was used.

## Recommendation

**Reject X integration for v1. Reconsider it only as a later, measured experiment after the primary financial-news pipeline is stable.**

X now offers self-serve read and search access under pay-per-use pricing, so access itself is feasible. It is nevertheless a poor v1 fit for Ripple:

1. Ripple already has a primary financial-news feed; X is optional and has no demonstrated incremental value for one daily decision at 9:00 PM ET.
2. Post reads cost **$0.005 per returned Post**, so noisy queries turn directly into variable spend. A small hard cap is affordable, but a useful recall target has not been validated.
3. The public pricing table does not list a price for the News resource even though the News endpoints are documented as self-serve. X directs developers to the authenticated Developer Console for current per-endpoint rates, so the cost of the most purpose-built endpoint cannot be established from public documentation alone.
4. X requires stored X Content to reflect later deletions and modifications. That creates ongoing compliance work and conflicts with Ripple's requirement that the exact inputs in a `DecisionSnapshot` remain immutable for audit and controlled A/B comparison.
5. Ripple sends decision inputs to third-party model providers. X permits analysis only for the use case approved by X, restricts transferring or providing access to licensed material to third parties, and prohibits using X Content to train or fine-tune foundation/frontier models. The public terms do not expressly confirm that transmitting raw X Content to an external inference provider is permitted. This should be resolved with X before such a design is implemented; this report is not legal advice.

The recommendation is v1-specific, not a claim that X data has no value. A later experiment could test a tightly capped, Post-ID-first ingestion path against the primary feed before accepting its cost and compliance burden.

## Current read and search access

### Recent Post search

`GET /2/tweets/search/recent` searches the last seven days and is documented as available to all developers. A developer account, Project/App, and Bearer Token are required. Self-serve queries are limited to 512 characters, return 10 Posts by default and at most 100 per request, and support pagination. Operators include keywords, exact phrases, cashtags, `from:`, language, link/media filters, and exclusions such as `-is:retweet`. These are sufficient to build a fixed-universe query, although the 512-character limit may require a few deterministic query groups for 15–18 symbols and company-name aliases. [Search overview](https://docs.x.com/x-api/posts/search/introduction) · [Search operators](https://docs.x.com/x-api/posts/search/integrate/operators) · [Getting access](https://docs.x.com/x-api/getting-started/getting-access)

The documented rate limit is 450 requests per 15 minutes per app or 300 per 15 minutes per user. One daily batch is far below either limit. The endpoint returns reverse-chronological results and supports `start_time`, `end_time`, `since_id`, and pagination, so an ingestion job can define a deterministic cutoff and avoid gaps. [Rate limits](https://docs.x.com/x-api/fundamentals/rate-limits) · [Pagination](https://docs.x.com/x-api/posts/search/integrate/paginate)

### Full-archive Post search

`GET /2/tweets/search/all` searches back to 2006 and is documented for pay-per-use and Enterprise customers. Self-serve requests support up to 500 results and 1,024-character queries. The documented app limit is one request per second and 300 requests per 15 minutes. Ripple does not need full-archive search for daily production ingestion; it would only be relevant to a separately scoped historical evaluation. [Search overview](https://docs.x.com/x-api/posts/search/introduction) · [Rate limits](https://docs.x.com/x-api/fundamentals/rate-limits)

### X News search

`GET /2/news/search` returns X News stories matching a text query. It accepts 1–100 results, a maximum story age from 1 to 720 hours, and fields including headline/name, summary, updated time, finance tickers, organizations, and the IDs of Posts in the story cluster. The endpoint requires a Bearer Token. The general API overview says all endpoints are available on pay-per-use unless marked Enterprise-only; News search is not marked Enterprise-only. Its documented rate limit is 200 requests per 15 minutes for either app or user authentication. [News search](https://docs.x.com/x-api/news/search-news) · [API overview](https://docs.x.com/x-api/overview) · [Rate limits](https://docs.x.com/x-api/fundamentals/rate-limits)

This is structurally closer to Ripple's need than raw Post search because it returns clustered stories and finance ticker context. However, the public pricing table does not identify a `News: Read` rate. Its actual price must therefore be verified in the Developer Console before any cost claim or implementation decision. The real-time `news.new` activity event is explicitly Enterprise/Partner-only, but Ripple's once-daily cadence does not require that stream. [Public pricing](https://docs.x.com/x-api/getting-started/pricing) · [Activity API](https://docs.x.com/x-api/activity/introduction)

## Pricing and low-frequency cost

The self-serve X API is currently credit-based pay-per-use: credits are purchased in advance, there is no subscription or minimum spend, and successful reads consume credits. Failed requests that return no data are not billed. X provides a spending limit, balance monitoring, and optional auto-recharge; reaching the spending limit or exhausting credits blocks requests. [Pricing](https://docs.x.com/x-api/getting-started/pricing) · [Usage and billing](https://docs.x.com/x-api/fundamentals/post-cap)

Public Post reads are **$0.005 per Post returned**, not per search request. The same billable resource is normally deduplicated within a UTC day, but X calls this a soft guarantee. Pay-per-use plans have a documented cap of three million Post reads per monthly billing cycle. That cap is irrelevant at Ripple's intended volume; the variable cost per useful result is the controlling factor. [Pricing](https://docs.x.com/x-api/getting-started/pricing) · [Usage and billing](https://docs.x.com/x-api/fundamentals/post-cap)

Illustrative 30-day Post-search budgets at the published rate:

| System-wide daily Post cap | Approximate monthly cost |
|---:|---:|
| 50 | $7.50 |
| 100 | $15.00 |
| 200 | $30.00 |
| 500 | $75.00 |

These are upper-bound arithmetic examples, not quotes from X and not estimates of useful coverage. Because billing is per returned Post, batching all symbols into fewer requests does not reduce the bill when the same number of unique Posts is returned. Query specificity and a hard result/spend cap matter more than request count. X itself recommends precise filters and caching to control consumption. [Query-building guidance](https://docs.x.com/x-api/posts/search/integrate/build-a-query) · [Usage and billing](https://docs.x.com/x-api/fundamentals/post-cap)

## Operational and terms constraints

### Credentials and availability

An X developer account and registered App are required, and the declared use case is binding. X requires developers to disclose substantive changes and obtain approval before beginning a changed use. Credentials must remain private. X may change or discontinue API features and may require a different access tier. This adds a credential, prepaid balance, usage alert, policy-review, and failure mode to a system whose primary feed does not depend on X. [Developer Policy](https://docs.x.com/developer-terms/policy) · [Developer Agreement](https://docs.x.com/developer-terms/agreement)

A compliant production client would need deterministic time cutoffs; pagination; request and content deduplication; spending and result caps; rate-limit header handling; bounded retry for 429/5xx responses; detection of partial `data` plus `errors` responses; and fail-closed behavior when credits, authorization, or the endpoint are unavailable. The X source must never block or silently change the primary DecisionSnapshot feed. [Response codes and errors](https://docs.x.com/x-api/fundamentals/response-codes-and-errors)

### Stored-content compliance versus immutable snapshots

X says any developer storing X Content offline must keep it current: deleted, protected, suspended, withheld, or modified content must be removed or updated as soon as reasonably possible, and within 24 hours after a request from X or the account owner. X provides compliance streams specifically to propagate these events. [Developer Policy](https://docs.x.com/developer-terms/policy) · [Compliance streams](https://docs.x.com/x-api/compliance/streams/introduction)

That obligation is materially at odds with Ripple's immutable audit bundle: changing or deleting the raw text after a decision means the stored artifact no longer proves exactly what the models saw. Keeping the original text unchanged would preserve Ripple's audit property but violate the stated content-maintenance rule after a deletion or edit. A Post-ID-only record avoids redistributing raw hydrated content and permits rehydration, but it cannot reproduce deleted or edited input. A derived summary may also be covered because the Agreement defines X Content to include copies and derivative works. This is an architectural and terms issue, not just an implementation detail. [Developer Agreement](https://docs.x.com/developer-terms/agreement)

### Model-provider boundary

The Agreement permits integrating X Content into a service or analyzing it only as explicitly approved by X. It also prohibits transferring or providing access to licensed material to a third party except as expressly permitted, and prohibits using the API or X Content to fine-tune or train a foundation/frontier model. The Restricted Uses rules repeat the training prohibition. They do not expressly address ordinary third-party model inference. [Developer Agreement](https://docs.x.com/developer-terms/agreement) · [Restricted uses](https://docs.x.com/developer-terms/restricted-use-cases)

Therefore, it would be unsafe to assume that raw Posts or X News summaries may be sent to Claude/OpenAI merely because Ripple is not training a model. Before reconsideration, the approved use-case description or written X guidance should explicitly cover external LLM inference and the intended retention/audit design.

### Redistribution and public artifacts

X restricts redistribution of hydrated content and generally directs developers to share Post IDs instead. Raw Posts, News payloads, or model prompts containing them must not be committed to Git or published in sanitized reports without confirming that the intended distribution is permitted. [Developer Policy](https://docs.x.com/developer-terms/policy) · [Restricted uses](https://docs.x.com/developer-terms/restricted-use-cases)

## Reconsideration gate

Do not implement X in Phase 0. Reconsider after the primary news pipeline can produce frozen snapshots reliably, and only if all of the following are true:

1. A small offline evaluation, using lawfully obtained data, pre-registers and demonstrates incremental coverage or decision value beyond the primary feed.
2. The Developer Console confirms the current price for the chosen endpoint, including X News if used.
3. The owner approves a hard monthly spend cap and a system-wide daily result cap; auto-recharge remains off unless explicitly approved.
4. X explicitly approves the use case, including external LLM inference and the proposed retention/audit treatment.
5. The architecture records how deletion/edit compliance coexists with reproducible DecisionSnapshots. If it cannot, X remains excluded.

Until those gates pass, the deterministic behavior is simple: **X contributes no input, all comparison lanes continue to share the same primary frozen news snapshot, and X unavailability has no effect on a decision run.**
