# Provider Access Spike: Competitor Stores

| | |
|---|---|
| **Capability** | Competitor-store analysis (what a Shopify/WooCommerce store sells, prices, how established it is) |
| **Verified on** | 2026-07-11 |
| **Target market** | United States |
| **Legal entity** | Existing US LLC |
| **Operator residency** | Unspecified — notes that depend on it are flagged |
| **Use** | Single-user internal research tool |
| **Final classification** | `paid_option` for systematic data (StoreLeads-class); `manual_only` floor is usable now at $0. **Automated storefront scraping: blocked by policy.** |

## 1. Official documentation

- Shopify API License & Terms of Use: <https://www.shopify.com/legal/api-terms>
- Shopify ToS / AUP: <https://www.shopify.com/legal/terms>, <https://www.shopify.com/legal/aup>
- Shopify robots.txt docs: <https://shopify.dev/docs/storefronts/themes/seo/robots-txt>
- StoreLeads: <https://storeleads.app/> · FAQ <https://storeleads.app/help/faq> · sales-estimate methodology <https://storeleads.app/help/faq/how-is-estimated-sales-calculated>
- BuiltWith: <https://builtwith.com/plans> · Wappalyzer: <https://www.wappalyzer.com/pricing/> · SimilarWeb: <https://www.similarweb.com/>
- Meta Ad Library (public web UI, used as cross-reference): <https://www.facebook.com/ads/library>

## 2. Access & approval requirements

- **Scraping Shopify storefronts (incl. `/products.json`): no permitted route exists.** Shopify's API Terms prohibit "copy, scrape, mine, or create derivative works of … any Merchant Store … except as authorized by Shopify in writing", and the standard store-level ToS template used by most stores prohibits "spider, crawl, or scrape" (e.g. <https://shopify.supply/terms-of-service>). Technical availability of the endpoint does not create permission.
- **WooCommerce:** self-hosted; the individual store's terms govern. Our policy treats "no explicit permission" conservatively — same rules.
- **StoreLeads / Wappalyzer / SimilarWeb / BuiltWith:** self-serve signup, email + card, no company registration, no approval. This may vary depending on the operator's country and legal entity.
- **Meta Ad Library web UI:** free, no login, covers commercial ads globally — a legitimate cross-reference for a competitor's ad footprint.

## 3. Geographic & dataset coverage

- **StoreLeads:** ~13.6M active stores across 408 platforms (Shopify, WooCommerce, Square Online, …), global coverage with public per-country reports (the per-country report pattern was verified via <https://storeleads.app/reports/shopify/EG/top-stores>; the US target market's report is expected at the analogous `/US/` URL — confirm during the test plan). Per-store: platform, installed apps and technologies with install dates, traffic estimates, estimated monthly sales (modeled), ship-to countries, ~60 filters.
- **BuiltWith / Wappalyzer:** tech detection on any public domain, any country.
- **SimilarWeb:** global traffic estimates, but 30–50% error reported for sites under ~100k monthly visits — many small competitor stores fall below reliable thresholds.

## 4. Pricing & rate limits

Vendor pages were not directly reachable from the research sandbox; figures below come from the cited third-party trackers and **must be re-confirmed on the vendor pricing page before purchase**.

| Service | Free tier | Relevant paid tier |
|---|---|---|
| StoreLeads | Public country/tech reports | Premium $75/mo; **Pro $250/mo (CSV export + API)** |
| Wappalyzer | 50 lookups/mo | Pro $250/mo (20k API credits) |
| BuiltWith | Single-site lookup | Basic $295/mo; Pro $495/mo (API) |
| SimilarWeb | Basic free lookup | Starter ~$125–149/mo |
| Meta Ad Library web | Free | — |

API rate limits for StoreLeads/BuiltWith are account-gated: **unknown, because not publicly verifiable**.

## 5. Storage & usage restrictions

- Shopify's terms bar building/storing a scraped index of Merchant Store data — so our system stores **no scraped storefront data at all**.
- StoreLeads Pro licenses CSV/API export for internal workflows; redistribution limits live in account-gated terms (**unknown until signup**).
- Manual evidence (screenshots/notes of publicly displayed prices for internal research) is ordinary market research; we do not retain personal data (reviewer names etc.).

## 6. Can arbitrary competitor stores be analyzed?

Yes, through three compliant lenses: (1) licensed store-intelligence lookups (StoreLeads — broad but not guaranteed for every micro-store); (2) tech detection (Wappalyzer/BuiltWith — any domain); (3) manual browsing of the public storefront plus Meta Ad Library cross-reference. What is technically possible but **not** permitted: automated `/products.json` harvesting (still works on most stores, ~250 items/page — documented as capability evidence, not permission; Shopify-wide Cloudflare bot protection increasingly blocks it anyway).

## 7. Minimal test request

The one allowed no-credential probe (fetching a StoreLeads public per-country report) was blocked by the research sandbox's own egress proxy, not by the vendor — **re-run from a normal machine**:

1. Open `https://storeleads.app/reports/shopify/US/top-stores` (the target market's report) — confirm public report quality (no account needed).
2. StoreLeads trial/Premium: look up 3 known competitor domains; success = ≥2 found with sales + traffic estimates populated.
3. Wappalyzer free tier: same 3 domains, verify platform/app detection.
4. SimilarWeb free lookup: same domains; "insufficient data" for small stores is a finding, not a failure.
5. Meta Ad Library web: search each competitor's brand; record active-ad count manually.
6. Only if 2–5 prove value: StoreLeads Pro ($250/mo) and test its API on a single domain.

## 8. Fallback options

- **Manual analysis floor ($0, usable now):** catalog & prices from collection/product pages, "sold out" signals, review counts/recency, shipping/returns pages, visible apps and theme, WHOIS/domain age, Wayback history, social profiles, Meta Ad Library footprint — recorded as dated manual evidence with URLs.
- StoreLeads public reports (free) for market-level context.
- Wappalyzer's 50 free lookups/mo for tech detection.
- If a data need can't be met by licensed providers or manual evidence, the answer is "we don't get that data" — never a scraping exception.

## 9. Final classification & rationale

**`paid_option`** for systematic competitor data (StoreLeads Pro when volume justifies it), with a **`manual_only` floor that is usable now at $0**. Automated storefront scraping is **blocked by policy** regardless of technical feasibility: Shopify's platform terms and near-universal store ToS prohibit it, and the hiQ v. LinkedIn endgame (breach-of-contract consent judgment, injunction, data destruction — <https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/>) shows "public" does not mean "permitted"; litigation exposure varies with the operator's country and legal entity, and our stance is ToS-respecting regardless of jurisdiction. 

### Policy (adopted with this record)

- We will **not** send automated requests to competitor storefronts — no HTML crawling, no `/products.json` or `/collections/*/products.json` calls, no headless browsers, no scheduled re-checks — regardless of robots.txt.
- We will **not** circumvent any technical control (bot detection, rate limits, login walls); encountering one is a stop signal.
- Systematic competitor data comes **exclusively from licensed providers** with export/API rights, stored within each provider's license, never resold or republished.
- The **manual-evidence workflow** is first-class: the user reads public storefronts and the Meta Ad Library and records findings with URL + date; the system analyzes what the human recorded but never fetches store pages itself.
- No personal data from stores (reviewer names, staff details) — aggregate/commercial facts only.
- Re-verify this policy against Shopify's legal pages every ~6 months or when a provider changes terms.

## Sources

- <https://www.shopify.com/legal/api-terms> — prohibition on scraping/deriving from Merchant Stores without written authorization (quoted via search; direct fetch blocked by research-sandbox proxy)
- <https://shopify.supply/terms-of-service>, <https://mxwraps.us/policies/terms-of-service> — standard store ToS template: "spider, crawl, or scrape" prohibited
- <https://shopify.dev/docs/storefronts/themes/seo/robots-txt>, <https://logeix.com/shopify-seo/robots-txt> — default robots.txt scope (crawl management, not permission)
- <https://community.shopify.com/t/how-to-paginate-or-get-a-list-of-all-products-using-domain-com-products-json/99991>, <https://dev.to/dentedlogic/the-shopify-productsjson-trick-scrape-any-store-25x-faster-with-python-4p95>, <https://tendem.ai/blog/scraping-shopify-stores-product-catalogs> — /products.json technical behavior + Cloudflare bot protection (capability evidence only)
- <https://storeleads.app/>, <https://storeleads.app/help/faq/what-data-is-available-for-domains>, <https://storeleads.app/help/faq/how-is-estimated-sales-calculated>, <https://storeleads.app/reports/shopify/EG/top-stores> — coverage, attributes, methodology, verified example of the public per-country report pattern
- <https://www.outboundsalestools.com/tools/storeleads/>, <https://syncgtm.com/blog/store-leads-review-2026> — StoreLeads tiers (third-party; re-confirm before purchase)
- <https://derrick-app.com/tools/builtwith-pricing>, <https://www.g2.com/products/builtwith/pricing> — BuiltWith tiers (third-party)
- <https://prospeo.io/s/wappalyzer-pricing-reviews-pros-and-cons>, <https://coldiq.com/tools/wappalyzer> — Wappalyzer free tier and Pro credits
- <https://www.saaspricepulse.com/tools/similarweb>, <https://thatmarketingbuddy.com/pricing/similarweb> — SimilarWeb tiers and small-site accuracy limits
- <https://www.facebook.com/ads/library>, <https://transparency.meta.com/researchtools/ad-library-tools/> — Ad Library web UI as free cross-reference
- <https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/>, <https://www.privacyworld.blog/2022/12/linkedins-data-scraping-battle-with-hiq-labs-ends-with-proposed-judgment/> — hiQ v. LinkedIn outcome

**Unverifiable without an account:** StoreLeads API rate limits and redistribution terms; BuiltWith exact API quotas; SimilarWeb API pricing.
