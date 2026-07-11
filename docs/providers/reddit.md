# Provider Access Spike: Reddit / Community Signals

| | |
|---|---|
| **Capability** | Community signals — mentions, complaints, interest around product categories |
| **Verified on** | 2026-07-11 |
| **Target market** | United States |
| **Legal entity** | Existing US LLC |
| **Operator residency** | Unspecified — notes that depend on it are flagged |
| **Use** | Single-user internal research tool |
| **Final classification** | `needs_approval` (manual browsing + manual evidence is the guaranteed floor) |

## 1. Official documentation

- Data API Wiki (registration, rate limits): <https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki>
- Developer Platform & Accessing Reddit Data: <https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data>
- Responsible Builder Policy: <https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy>
- Data API Terms: <https://www.redditinc.com/policies/data-api-terms> · Developer Terms: <https://www.redditinc.com/policies/developer-terms>
- Deleted-content obligations: <https://support.reddithelp.com/hc/en-us/articles/26417433892756>
- Endpoint reference: <https://www.reddit.com/dev/api/> · app console: <https://www.reddit.com/prefs/apps>

## 2. Access & approval requirements

Mechanics: Reddit account → create an app at `/prefs/apps` (client ID + secret) → OAuth2. No payment, no company. **But since 2025–26, Reddit's Responsible Builder Policy requires explicit prior approval via a request form before any API data access** — self-service access is gone. Reddit's App Review decides commercial vs non-commercial treatment, and its commercial definition ("by a business **or on behalf of a business** or as part of a monetized product or service") plausibly captures product research for a for-profit ecommerce venture — the definition is purpose-based, so it applies whether or not a legal entity exists yet — and honest disclosure may route to the paid/contract track. **Operator residency:** no country restriction found anywhere, but the Developer Terms text (age/sanctions/eligibility clauses) could not be read directly — unverified. This may vary depending on the operator's country and legal entity.

## 3. Geographic & dataset coverage

Global dataset regardless of caller location. Relevance note (judgment, not doc claim): Reddit skews English/US-EU — well matched to a US target market for product-category demand and pain-point signals. Listings capped ~1,000 items; keyword search reaches older posts; bulk/historical (Pushshift) is now moderators-only.

## 4. Pricing & rate limits

- **Free tier (after approval):** non-commercial use within **100 queries/min per OAuth client** (10-minute rolling average; `X-Ratelimit-*` headers). Ample for one user.
- **Unauthenticated:** ~10 QPM, unsupported and freely throttled.
- **Commercial:** **$0.24 per 1,000 calls** under a negotiated contract (2023 rate, still cited in 2026). Enterprise licensing is far above our scale.

## 5. Storage & usage restrictions

- **Deletion sync is mandatory:** content deleted/removed on Reddit must be deleted from our systems (posts, comments, author-identifying info); Reddit recommends purging within **48 hours** and states retention of deleted content **even de-identified** violates the terms. Practical design: don't warehouse raw Reddit text long-term; store derived notes/summaries + evidence URLs, and re-check stored raw snippets periodically.
- **No sharing/selling** of Reddit data without written approval; internal single-user use is the safest posture.
- **AI training explicitly prohibited.** Our LLM *reads and summarizes* fetched content at inference time — a different act from training, but the exact clause text could not be read directly, so treat "inference-time processing is fine" as **plausible but unverified**; state it explicitly in the App Review request.

## 6. Arbitrary ecommerce product search?

**Yes, for posts:** `GET /search` (site-wide) and `GET /r/{sub}/search?restrict_sr=1` accept arbitrary keywords with sort (relevance/hot/top/new/comments), time filters, `limit` ≤100, cursor pagination. Limitations: searches posts, not full comment text; Reddit's relevance ranking is mediocre.

## 7. Minimal test request

The unauthenticated probe was blocked by the research sandbox's own egress proxy (never reached Reddit). Run from a normal machine:

1. `curl -A "linux:ecom-research-probe:v0.1 (by /u/USERNAME)" "https://www.reddit.com/r/BuyItForLife/search.json?q=posture+corrector&restrict_sr=1&sort=new&t=year&limit=5"` — documents current unauthenticated posture (JSON at ~10 QPM, or 403/429).
2. After app creation: `POST https://www.reddit.com/api/v1/access_token` (client_credentials, basic auth).
3. `GET https://oauth.reddit.com/search?q=trunk+organizer&sort=new&t=month&limit=10` with the bearer token; read `X-Ratelimit-Remaining` to confirm the real quota.

## 8. Fallback options

- **Manual floor (guaranteed, $0):** logged-in browsing of reddit.com/search and niche subreddits (r/BuyItForLife etc.) with manual evidence entry — fully permitted ordinary site use, genuinely workable at a few product ideas/week.
- **Official data partners** (Brandwatch, Sprinklr, Sprout Social, Talkwalker, Meltwater) — enterprise-priced, no small-scale licensed reseller exists.
- **Unlicensed archives/scrapers** (PullPush, Arctic Shift, Apify/Bright Data) — outside Reddit's terms; account-ban and legal exposure; **not for this tool**.
- **Reddit for Researchers / Pushshift** — academic-/moderator-only; unavailable.

## 9. Final classification & rationale

**`needs_approval`.** Technically a strong fit (arbitrary keyword search, generous free quota), no country barrier found — but the Responsible Builder Policy's explicit-approval gate plus Reddit's broad commercial-use definition make the outcome discretionary, possibly routing to the $0.24/1k-calls contract track. Apply with an honest description (single-user, read-only, low-volume research; summarizes but does not train; honors deletion sync) and build the manual-evidence workflow in parallel so the capability ships regardless of Reddit's decision.

## Sources

- <https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki> — registration, 100/10 QPM, rate-limit headers, request form
- <https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy> — approval-before-access requirement, no AI training, enforcement
- <https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data> — commercial definition, contract requirement, App Review
- <https://support.reddithelp.com/hc/en-us/articles/26417433892756> — deletion-sync obligations, 48-hour recommendation
- <https://www.redditinc.com/policies/data-api-terms>, <https://www.redditinc.com/policies/developer-terms> — canonical terms (direct fetch blocked in research sandbox; eligibility clauses unverified)
- <https://techcrunch.com/2024/05/09/reddit-locks-down-its-public-data-in-new-content-policy-says-use-now-requires-a-contract/> — commercial use requires contract
- <https://octolens.com/blog/reddit-api-pricing>, <https://www.techloy.com/reddit-api-pricing-in-2026-complete-guide-for-developers-and-businesses/> — $0.24/1k calls current in 2026
- <https://data365.co/blog/reddit-api-limits>, <https://painonsocial.com/blog/reddit-api-rate-limits-guide> — rate-limit corroboration
- <https://data365.co/blog/reddit-search-api>, <https://docs.zernio.com/reddit-search/search-reddit> — search endpoint parameters
- <https://www.meltwater.com/en/blog/meltwater-reddit-data-partner> — official data partners
- <https://support.reddithelp.com/hc/en-us/articles/16470271632404-Pushshift-Access-Request>, <https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program> — restricted programs
- <https://www.socialcrawl.dev/blog/reddit-data-api-2026>, <https://www.redditapis.com/blogs/reddit-data-api-2026> — approval-gate reports (vendor blogs, low confidence)

**Country/entity dependencies:** none found; the entity-relevant trigger is Reddit's *purpose-based* commercial definition, not business registration. Developer Terms eligibility text unverified (site unreachable from research sandbox) — this may vary depending on the operator's country and legal entity.
