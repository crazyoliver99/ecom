# Provider Access Spike: Amazon Marketplace Data

| | |
|---|---|
| **Capability** | Marketplace data — prices, review counts/ratings, sales-rank history as demand/competition proxies |
| **Verified on** | 2026-07-11 |
| **Target market** | United States |
| **Legal entity** | Planned US LLC (not yet formed) |
| **Operator residency** | Unspecified — notes that depend on it are flagged |
| **Use** | Single-user internal research tool |
| **Final classification** | `paid_option` via **Keepa** · PA-API 5.0: `blocked` (retired) · Creators API: `blocked` for us · SP-API: not applicable |

## Headline finding

**Amazon PA-API 5.0 was deprecated 2026-04-30 and its endpoint retired 2026-05-15 — it is already dead.** Its successor, the **Creators API**, requires an approved Associates account with **~10 qualifying affiliate sales per trailing 30 days per locale** (auto-suspension below that) — impossible for a research tool that drives no affiliate traffic. That leaves **Keepa** as the only realistic license-compliant option, with scraper-class vendors (Rainforest) as a flagged fallback.

## 1. Official documentation

- Keepa API: <https://keepa.com/#!api> · plans explanation: <https://keepa.com/#!discuss/t/how-our-api-plans-work/410> · official client (endpoints/locales verified directly): <https://github.com/keepacom/api_backend>
- PA-API 5.0 (deprecation notice): <https://webservices.amazon.com/paapi5/documentation/> · license: <https://webservices.amazon.com/paapi5/documentation/read-la.html>
- Creators API: <https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction>
- Rainforest API (Traject Data): <https://trajectdata.com/ecommerce/rainforest-api/> · docs <https://docs.trajectdata.com/rainforestapi> · domains <https://www.rainforestapi.com/docs/product-data-api/reference/amazon-domains>
- SP-API registration (why it's N/A): <https://developer-docs.amazon.com/sp-api/docs/sp-api-registration-overview>

## 2. Access & approval requirements

- **Keepa: self-serve.** Monthly subscription + access key; no approval, no affiliate status, no entity requirement referenced anywhere public. No country restriction found — though keepa.com's own terms were not directly readable from the research sandbox, so confirm at signup; this may vary depending on the operator's country and legal entity. EUR card billing.
- **PA-API 5.0: blocked for everyone** (retired; no new customers).
- **Creators API: blocked for us.** Needs an approved Associates account + the 10-sales/30-day/locale threshold (figure consistent across three independent integrator docs; not read on Amazon's own page — flagged). Associates enrollment and payout mechanics vary by marketplace and by the operator's country and legal entity (some countries' local Associates programs are invitation-only; a US LLC can join amazon.com Associates directly) — but that's moot given the sales threshold: a tool that drives no affiliate traffic can never sustain it.
- **Rainforest: self-serve**, 100-request free trial, no card, no entity requirement stated.
- **SP-API: not applicable** — requires a Professional Amazon selling account (or vetted solution-provider status) and exposes sellers' operational data, not market research for arbitrary products.

## 3. Geographic & dataset coverage

- **Keepa: 11 locales — US, UK, DE, FR, JP, CA, IT, ES, IN, MX, BR** (verified in the official client's locale enum) — **the US target market (amazon.com, `domain=1`) is covered.** Per product: full price history (all price types), **sales-rank history**, buy box, **rating & review-count history**, offers, sellers, categories, deals, best-sellers, and a Product Finder query engine. Keepa is the only source with *native history* — Amazon's own APIs never exposed sales-rank history.
- **Creators API:** live data only, same-marketplace-as-PA-API model; irrelevant given the gate.
- **Rainforest: 24 Amazon domains** (more than Keepa's 11 — relevant only if a locale outside Keepa's coverage ever matters); product/search/offers/reviews/bestsellers/categories/sellers request types; live-scraped (history only by polling).

## 4. Pricing & rate limits

- **Keepa:** token system — subscription grants N tokens/min (tokens expire after 60 min; ~1 token per product's full dataset, surcharges for offers/buybox). Reported tiers: **€49/mo ≈ 20 tokens/min** (≈28k product pulls/day — ample for one user), €459/250, €1,499/1,000, €4,499/4,000; the €19/mo consumer data subscription reportedly includes minimal API access. **Exact euro figures are from third-party 2026 guides — confirm on keepa.com at signup.**
- **Rainforest:** reported tiers $59 / $375 / $1,000 per month (~100k requests at $375), credit multipliers for heavy parameters, free 100-request trial.
- PA-API (historical): 1 TPS/8,640 TPD, capacity earned by affiliate revenue — the model the Creators API inherits.

## 5. Storage & usage restrictions

- **Keepa: the single most important unverified item of this spike.** Keepa publishes API T&C, but the storage/retention clauses could not be read from the research sandbox. **Read them at signup before persisting fetched data.** Mitigation: Keepa's core value is that *they* store the history — every product request returns multi-year history on demand, so our local retention needs are modest (store derived metrics + evidence references, re-fetch history when needed).
- **PA-API/Creators license model (for the record):** prices cacheable ≤1 hour, titles ≤24 hours, no image storage, use tied to sending traffic to Amazon — historical archiving was never permitted. This is why the Associates route was wrong for us regardless of eligibility.
- **Rainforest:** positions its data as "web-scraped data from public domain sources"; customer ToS storage clauses unverified. Honest note: it scrapes Amazon against Amazon's Conditions of Use — vendor absorbs operational risk, but this conflicts with our official-API preference; using it is a business-risk decision, flagged `best_effort`-class sourcing.

## 6. Arbitrary ecommerce product search?

- **Keepa: yes** — keyword `search`, catalog-wide `query` (Product Finder: filter by rank/price/review criteria), `product` by ASIN/UPC/EAN, best-sellers — across its 11 locales.
- **Rainforest: yes** — any keyword/ASIN across its 24 domains.
- **Creators API: technically yes, practically no** (gate).

## 7. Minimal test request

**Keepa (after buying the smallest API plan):**
```
GET https://api.keepa.com/token?key=***                      → token balance / refill rate
GET https://api.keepa.com/product?key=***&domain=1&asin=B07FZ8S74R&stats=90&history=1&rating=1
```
Success: `products[0].csv` history arrays (prices, sales rank), stats, review history; `tokensLeft`/`refillRate` in the envelope.

**Rainforest (free trial):** `GET https://api.rainforestapi.com/request?api_key=***&type=search&amazon_domain=amazon.com&search_term=vitamin+c+serum`.

(No-credential probes from the research sandbox hit its own egress proxy 403 — the vendors' real unauthenticated error responses were not observed; re-run from a normal machine if needed.)

## 8. Fallback options

1. **Rainforest API** — broader locale coverage; scraper-class caveats above.
2. **SerpApi / Oxylabs Amazon endpoints** — same class, unverified in detail.
3. **Keepa website manually** (€19/mo consumer subscription) — if API terms disappoint, manual chart reading + manual evidence entry still works.
4. **Creators API later** — only if you ever become an active Associate with ≥10 monthly qualified sales per locale.

## 9. Final classification & rationale

**`paid_option` via Keepa (~€49/mo)** — self-serve with no approval gate and no documented country/entity requirement (this may vary depending on the operator's country and legal entity; confirm at signup), and the only source of native price/sales-rank/review *history*, which is exactly the demand/competition proxy the scoring engine needs. It covers the US target market plus ten other major marketplaces (Rainforest is the fallback if a locale outside Keepa's coverage ever becomes essential). Caveat: read the retention clause at signup. PA-API is dead; Creators API and SP-API are structurally unavailable to a non-selling, non-affiliate research tool.

## Sources

- <https://github.com/keepacom/api_backend> (+ `AmazonLocale.java`, `Request.java`) — endpoints, parameters, 11 locales — **directly fetched and read**
- <https://github.com/akaszynski/keepa> — subscription + access key requirement
- <https://github.com/internetarchive/openlibrary/issues/12255> — quotes Amazon's official PA-API deprecation notice
- <https://webservices.amazon.com/paapi5/documentation/troubleshooting/api-rates.html>, <https://webservices.amazon.com/paapi5/documentation/read-la.html> — historical PA-API limits and license (via search-indexed content)
- <https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction> — Creators API (proxy-blocked; eligibility corroborated by integrators)
- <https://getaawp.com/docs/article/amazon-creators-api/>, <https://www.keywordrush.com/blog/amazon-pa-api-associatenoteligible-error-is-there-a-new-10-sales-rule/>, <https://guides.freshstore.com/article/745-amazon-creators-api> — 10-sales/30-day threshold (three independent integrators; not read on Amazon's page)
- <https://dev.to/th3nate/amazon-pa-api-v5-is-shutting-down-april-30-2026-here-is-what-changes-at-the-auth-layer-22ek> — deprecation/retirement dates
- <https://geniuslink.com/blog/amazon-associates-egypt/> — example that some countries' local Associates programs are invitation-only (enrollment varies by marketplace)
- <https://affiliate-program.amazon.com/resource-center/receive-your-international-affiliate-earnings-in-your-local-bank/> — international Associates payouts
- <https://keepa.com/#!discuss/t/how-our-api-plans-work/410> — official token-plan explanation
- <https://fbamultitool.com/keepa-subscription-pricing-quick-guide-for-amazon-sellers/>, <https://revenuegeeks.com/keepa-pricing/> — Keepa tier prices (third-party; confirm at signup)
- <https://keepaapi.readthedocs.io/en/latest/product_query.html> — token surcharges
- <https://trajectdata.com/ecommerce/rainforest-api/>, <https://trajectdata.com/pricing/>, <https://www.rainforestapi.com/docs/product-data-api/reference/amazon-domains>, <https://docs.trajectdata.com/rainforestapi> — Rainforest coverage/pricing/request types
- <https://www.asinspotlight.com/blog/asinspotlight-api-vs-rainforest-api>, <https://flybyapis.com/blog/rainforest-api-alternatives/> — Rainforest pricing corroboration
- <https://developer-docs.amazon.com/sp-api/docs/sp-api-registration-overview>, <https://developer.amazonservices.com/private-developer> — SP-API seller requirement
- <https://www.drupal.org/docs/7/modules/amazon-product-advertising-affiliate/caching-and-data> — Associates caching rules summary

**Unverified items requiring signup/normal connection:** (1) **Keepa API storage/retention clause — the most important open question in this spike**; (2) Rainforest customer ToS storage clause; (3) exact current Keepa euro pricing; (4) the 10-sales Creators threshold on Amazon's own page.
