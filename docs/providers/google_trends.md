# Provider Access Spike: Google Trends / Search Demand

| | |
|---|---|
| **Capability** | Search-demand / trends data (interest over time, related queries) |
| **Verified on** | 2026-07-11 |
| **Context assumed** | Individual in Egypt, no registered company, single-user internal research tool |
| **Final classification** | `paid_option` (official API: `needs_approval`; pytrends/scraping: `blocked` as a compliant route) |

## 1. Official documentation

- Official Google Trends API (alpha): <https://developers.google.com/search/apis/trends>
- Launch announcement (2025-07-24): <https://developers.google.com/search/blog/2025/07/trends-api>
- SerpApi Google Trends engine: <https://serpapi.com/google-trends-api> · pricing <https://serpapi.com/pricing>
- Glimpse: <https://meetglimpse.com/google-trends-api/> · pricing <https://meetglimpse.com/pricing/>
- DataForSEO Google Trends: <https://docs.dataforseo.com/v3/keywords_data-google_trends-overview/> · pricing <https://dataforseo.com/pricing/keywords-data/google-trends>
- Google Ads API (Keyword Planner alternative): <https://developers.google.com/google-ads/api/docs/api-policy/developer-token>, <https://developers.google.com/google-ads/api/docs/api-policy/access-levels>

## 2. Access & approval requirements

- **Official Trends API: still an access-controlled alpha as of 2026-07** ("very limited number of testers"). Application via a form describing intended use; approval is discretionary and rolling. No country restriction documented, so an Egyptian individual **can apply**, but a single-user internal tool is a weak application. The alpha's exact terms are shown only to admitted testers — unverifiable without approval.
- **SerpApi / DataForSEO / Glimpse:** ordinary commercial signup (email + card); no Egypt/entity restrictions found. Realistic for an individual.
- **Google Ads API (Keyword Planner):** needs a Google Ads account (Egypt supported for individuals — government-ID verification track; EGP billing since May 2025), a manager account, and a reviewed Basic Access developer-token application that expects a functioning website. Possible but heavyweight; approval for an internal tool uncertain.

## 3. Geographic & dataset coverage

- **Official alpha:** interest-over-time with *consistent scaling across requests*; daily/weekly/monthly/yearly aggregation; region and sub-region breakdown (ISO 3166-2, so `EG` works); rolling ~1,800-day window; data current to ~2 days ago. Related-queries coverage in the alpha is unconfirmed — treat interest-over-time as the only confirmed dataset.
- **SerpApi:** mirrors the public Trends UI — TIMESERIES (multi-term), RELATED_QUERIES, RELATED_TOPICS, interest-by-region; any Trends geo incl. EG; 2004–present.
- **DataForSEO:** UI-equivalent explore endpoint, up to 5 keywords/task.
- **Glimpse:** Trends-equivalent plus modeled **absolute search volume** (their differentiator).
- **Keyword Planner:** monthly search volume per country incl. Egypt, but volumes are bucketed ranges for low/no-spend accounts.

## 4. Pricing & rate limits

| Route | Cost | Limits |
|---|---|---|
| Official alpha | Free | ~10,000 "points"/day reported by a tester (1 five-year daily series ≈ 1,825 points → ~5 terms/day) — tester report, not official |
| SerpApi | Free 250 searches/mo; ~$25/1k, ~$75/5k/mo | Hourly throughput ≈ 20% of plan volume |
| DataForSEO | $0.00225/task (queued) or $0.009/task (live), ≤5 keywords/task | Pay-as-you-go, credits don't expire |
| Glimpse | ~$49–99/mo reported (conflicting third-party figures); **API pricing not public (contact sales)** | Unknown |
| Ads API | Free | 15,000 operations/day at Basic Access |

## 5. Storage & usage restrictions

- **Official alpha:** terms visible only to admitted testers — **unknown, because access-gated**.
- **All third-party providers (SerpApi/DataForSEO/Glimpse) scrape Google without a license** (Google offers none publicly). Google's ToS prohibit automated access (<https://policies.google.com/terms>). SerpApi's model: it assumes *collection* liability, not downstream *use*; its "US Legal Shield" excludes cheaper plans — and **Google sued SerpApi in Dec 2025** (<https://ipwatchdog.com/2025/12/26/google-sues-serpapi-parasitic-scraping-circumvention-protection-measures/>), so continuity risk is real. Store only the derived metrics we need; keep the provider swappable.
- **Keyword Planner:** internal analysis is within Permissible Use; redistribution restricted.

## 6. Arbitrary ecommerce product search?

Yes on every route — all accept free-text terms. Caveats: long-tail product terms often return sparse/zero Trends data; only Glimpse/Keyword Planner give absolute volume rather than a relative index.

## 7. Minimal test request

- **Executed 2026-07-11 (auth-gate probe):** unauthenticated `GET https://trends.googleapis.com/v1alpha/trends:fetchTimeSeries?terms=wireless%20earbuds` → **HTTP 404** (not 401/403): the v1alpha surface isn't even publicly discoverable without an allowlisted project — consistent with closed alpha.
- **Plan (SerpApi free tier, after signup):**
  `GET https://serpapi.com/search.json?engine=google_trends&q=wireless+earbuds&data_type=TIMESERIES&geo=EG&date=today+12-m&api_key=***`, then the same query with `data_type=RELATED_QUERIES`.
- **Plan (DataForSEO):** `POST /v3/keywords_data/google_trends/explore/live` with `[{"keywords":["wireless earbuds"],"location_code":2818,"date_from":"2025-07-01"}]` (~$0.009).

## 8. Fallback options

1. **DataForSEO** — cheapest pay-per-task; no subscription.
2. **SerpApi** — free 250/mo for prototyping; lawsuit risk noted above.
3. **SearchApi.io** (<https://www.searchapi.io/docs/google-trends>) — similar engine, unverified in detail.
4. **Glimpse** — if absolute volumes become worth enterprise pricing.
5. **Keyword Planner via Ads API** — free but approval-gated, coarse ranges.
6. **pytrends** — repo archived (last push 2024-08-10), breaks with 429s, violates Google ToS: **not a compliant route**.
7. **Manual floor:** read trends.google.com by hand, record numbers as manual evidence.

## 9. Final classification & rationale

**`paid_option`.** The only official API remains a closed alpha with tiny quotas (worth applying to in parallel — it's free — but not plannable). Scraping routes are non-compliant. What actually works today for arbitrary product keywords from Egypt with no entity requirement is a paid third-party provider: start on **SerpApi's free tier** for prototyping, adopt **DataForSEO pay-per-task** for production use, and isolate everything behind the `TrendsProvider` interface because these vendors carry real legal/continuity risk.

## Sources

- <https://developers.google.com/search/apis/trends> — alpha status, application form (surfaced via search; direct fetch blocked by sandbox proxy)
- <https://developers.google.com/search/blog/2025/07/trends-api> — launch scope: consistent scaling, aggregations, geo breakdown, 1,800-day window
- <https://willmanntobias.medium.com/some-first-discoveries-testing-google-trends-api-v1alpha-7580a31cef01> — tester-reported quota (~10k points/day)
- <https://ppc.land/google-opens-alpha-testing-for-new-trends-api-targeting-developers-and-journalists/> — application form details
- <https://www.scrapingbee.com/blog/best-google-trends-api/>, <https://meetglimpse.com/google-trends-api/> — 2026 confirmations alpha remains limited
- <https://serpapi.com/google-trends-api>, <https://serpapi.com/pricing>, <https://serpapi.com/legal>, <https://serpapi.com/us-legal-shield> — engine parameters, tiers, liability model
- <https://ipwatchdog.com/2025/12/26/google-sues-serpapi-parasitic-scraping-circumvention-protection-measures/> — Google v. SerpApi (Dec 2025)
- <https://docs.dataforseo.com/v3/keywords_data-google_trends-overview/>, <https://docs.dataforseo.com/v3/keywords_data-google-trends-explore-live/>, <https://dataforseo.com/pricing/keywords-data/google-trends> — endpoints and per-task pricing
- <https://www.trendsmcp.ai/trendsmcp-vs-glimpse>, <https://checkthat.ai/brands/glimpse/pricing> — conflicting Glimpse pricing reports
- <https://developers.google.com/google-ads/api/docs/api-policy/access-levels>, <https://developers.google.com/google-ads/api/docs/api-policy/developer-token> — Ads API access process and limits
- <https://support.google.com/adspolicy/answer/9872280?hl=en&co=GENIE.CountryCode%3DEG> — Egypt individual advertiser verification
- <https://english.ahram.org.eg/News/532880.aspx> — EGP billing for Google in Egypt
- <https://www.authoritas.com/blog/understanding-googles-search-volume-buckets-a-deep-dive-into-how-search-volumes-really-work>, <https://support.google.com/google-ads/thread/381084048> — Keyword Planner volume buckets
- <https://github.com/GeneralMills/pytrends> — archived status (GitHub API, checked 2026-07-11)
- <https://policies.google.com/terms> — automated-access prohibition

**Country/entity dependencies:** no Egypt bar found for the alpha application or the paid providers (their full ToS were not directly readable from the research sandbox); Google Ads fully supports Egyptian individuals; SerpApi's US Legal Shield is a US-law construct of untested value to an Egyptian individual.
