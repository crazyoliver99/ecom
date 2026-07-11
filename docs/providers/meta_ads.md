# Provider Access Spike: Meta Ad Intelligence

| | |
|---|---|
| **Capability** | Meta ad intelligence — which ecommerce products are advertised on Facebook/Instagram, by whom, since when |
| **Verified on** | 2026-07-11 |
| **Target market** | United States |
| **Legal entity** | Planned US LLC (not yet formed) |
| **Operator residency** | Unspecified — notes that depend on it are flagged |
| **Use** | Single-user internal research tool |
| **Final classification** | `needs_approval` (official API, EU-commercial-ads only) + `manual_only` (web UI, global) + `paid_option` (third-party tools) |

## 1. Official documentation

- Ad Library API landing: <https://www.facebook.com/ads/library/api>
- Graph API `ads_archive` reference: <https://developers.facebook.com/docs/graph-api/reference/ads_archive/>
- Transparency tools overview: <https://transparency.meta.com/researchtools/ad-library-tools/>
- Ad Library web UI: <https://www.facebook.com/ads/library/> · downloadable report: <https://www.facebook.com/ads/library/report/>
- Identity confirmation (API prerequisite): <https://www.facebook.com/ID>
- Rate limiting: <https://developers.facebook.com/docs/graph-api/overview/rate-limiting/>

## 2. Access & approval requirements

Official API path: (1) identity + location confirmation at facebook.com/ID with government ID (hours to days); (2) Meta developer account + app with the "Ad Library API" product, accepting the "Authorized Access to Public Information" terms; (3) user access token with `ads_read` (1h short-lived, exchangeable for 60-day). No formal App Review is reported for `ads_archive`. No company required — the person operating the tool verifies with personal government ID (a legal entity adds nothing to this step). **Identity-confirmation availability and accepted ID types depend on the operator's country of residence** — the current supported-country list at facebook.com/ID is login-gated and could not be confirmed; it is settled only by attempting it. This may vary depending on the operator's country and legal entity. Web UI: no account needed.

## 3. Geographic & dataset coverage — **the crux of this record**

**The API is NOT a general commercial-ads API:**

- **Outside the EU/UK**, `ads_archive` returns only **social-issue/electoral/political ads** (plus US special-category ads). Ordinary ecommerce ads shown in the US (**our target market**) and every other non-EU market are visible in the browser but **not returned by the API**, even with `ad_type=ALL`.
- **EU (DSA Art. 39):** ALL ads delivered to EU users — including commercial/ecommerce — are in the library and retrievable via API with `ad_type=ALL` + EU `ad_reached_countries`; archived ~1 year after last impression; EU-only fields include `eu_total_reach`, target age/gender/location breakdowns. (Note: Meta ended *political* ads in the EU in Oct 2025 under TTPA, so the EU library is now effectively commercial-only going forward.)
- **Fields per ad:** page name/ID, creative bodies/titles, `ad_snapshot_url`, delivery start/stop, platforms, languages. **Spend/impressions ranges: political ads only.** Commercial EU ads get reach, not spend.
- **Web UI:** any country, "All ads" keyword/advertiser search — but non-EU shows only *currently active* commercial ads, no spend/reach.
- **Downloadable report:** political only — useless for us.

Implication for us: programmatic Meta data will be an **EU-market lens** on product ad activity (a useful proxy for what's being pushed globally), while US-market checks — the target market — stay manual via the web UI.

## 4. Pricing & rate limits

Free. No contractual rate figure published; widely reported empirical behavior ~200 calls/hour per token, monitored via `X-App-Usage`. Web UI free with informal throttling.

## 5. Storage & usage restrictions

Governed by the "Authorized Access to Public Information" terms — **exact current text is behind the developer console (unverified until access)**. Secondary summaries consistently report: intended for transparency research; no resale; no ad-targeting use; no misleading republication; bulk-downloading creatives by scraping `ad_snapshot_url` prohibited under Meta's general ToS. Our stance: store returned metadata as evidence with citations, do not mirror creatives, do not republish raw dumps, and re-read the actual terms at onboarding — competitor/product intelligence is not the API's stated intent, which is a standing compliance caveat.

## 6. Arbitrary ecommerce product search?

- **API:** syntactically yes (`search_terms`, `search_page_ids`) — but commercial results **only for EU-delivered ads**.
- **Web UI:** yes — any keyword, any country, all ad categories. The only official free route to non-EU commercial ads.

## 7. Minimal test request

After identity confirmation + app + token:

```
GET https://graph.facebook.com/v23.0/ads_archive
  ?access_token=***&search_terms=posture corrector&ad_type=ALL
  &ad_reached_countries=['NL']&ad_active_status=ACTIVE
  &fields=id,page_id,page_name,ad_creative_bodies,ad_delivery_start_time,ad_snapshot_url,publisher_platforms,eu_total_reach
  &limit=25
```
Control test: same query with `ad_reached_countries=['US']` — expect no commercial results, confirming that the target market's commercial ads are outside the API's scope. (A credential-free probe from the research sandbox was blocked by its own egress proxy, so the documented 400-OAuth-error auth gate was not observed live.)

## 8. Fallback options

| Tool | Pricing (verify before purchase) | Notes |
|---|---|---|
| **Minea** | Starter $49/mo (Meta only), Premium $99/mo | UI-based ad spy + shop analytics; no public API |
| **PiPiAds** | Basic $49/mo, Advanced $99/mo | TikTok-first but covers Meta; API via pipispy.com |
| **BigSpy** | Basic $9/mo (FB/IG, 20 queries/day), Pro ~$99/mo | Cheapest entry point |

Compliance caveat: these vendors build databases by collecting from Meta surfaces in ways Meta's ToS prohibits *for the collector*; buyer risk is continuity/data quality, and none is Meta-licensed. Manual floor: web Ad Library searches recorded as manual evidence — free, global, compliant.

## 9. Final classification & rationale

**`needs_approval`** for the official API (identity verification + developer setup; availability varies with the operator's country of residence) — and even then it only yields **EU commercial ads**, which we treat as a market lens, not global coverage. **`manual_only`** covers global commercial ads today at $0 via the web UI + our manual evidence workflow. **`paid_option`** (BigSpy $9 → Minea $49) if/when programmatic global ad data becomes worth the compliance caveats. Recommended sequence: start manual immediately; complete facebook.com/ID + developer setup to unlock the EU API lens; defer paid tools until the scoring phase proves the need.

## Sources

- <https://transparency.meta.com/researchtools/ad-library-tools/> — API scope: political/issue ads + "ads that deliver to the EU and associated territories"
- <https://www.facebook.com/ads/library/api>, <https://developers.facebook.com/docs/graph-api/reference/ads_archive/> — access flow and endpoint (verified via search-index content; direct fetch blocked in research sandbox)
- <https://about.fb.com/news/2023/08/new-features-and-additional-transparency-measures-as-the-digital-services-act-comes-into-effect/> — DSA: all EU-delivered ads, 1-year archive, reach/targeting fields
- <https://about.fb.com/news/2025/07/ending-political-electoral-and-social-issue-advertising-in-the-eu/>, <https://www.techpolicy.press/what-data-reveals-about-meta-and-googles-political-ad-ban-in-the-eu/> — EU political-ads ban (Oct 2025)
- <https://about.fb.com/news/2019/06/offering-greater-transparency/> — country-by-country expansion of ad-transparency enforcement (useful when assessing a specific operator country's ID-verification support)
- <https://www.facebook.com/ID>, <https://en-gb.facebook.com/business/help/2992964394067299> — identity confirmation (login-gated; unconfirmed country list)
- <https://developers.facebook.com/docs/graph-api/overview/rate-limiting/> — rate-limit framework
- <https://www.admapix.com/blog/ad-intelligence/meta-ads-library-api-developers>, <https://adlibrary.com/posts/meta-ad-library-api-limitations>, <https://admanage.ai/blog/facebook-ads-library-api>, <https://apidog.com/blog/facebook-ad-library-api/> — EU-only commercial scope, ~200 calls/hr empirical, setup flow
- <https://admakeai.com/blog/meta-ad-library-scraping-terms-of-service>, <https://www.hyperfx.ai/blog/meta-ad-library-api-scraper-guide> — usage-restriction summaries
- <https://gijn.org/stories/guide-investigating-digital-ad-libraries/> — report is political-only
- Minea/PiPiAds/BigSpy pricing: <https://productlair.com/minea-pricing>, <https://affmaven.com/minea-pricing/>, <https://affinco.com/pipiads-pricing/>, <https://affmaven.com/bigspy-pricing-plans/>, <https://www.capterra.com/p/203036/BigSpy/>

**Country/entity dependencies:** identity confirmation is tied to the operator's personal residency and ID, not to any legal entity — this may vary depending on the operator's country and legal entity (the login-gated country list is settled by attempting it); no entity is required anywhere in this capability; third-party tools are constrained only by payment-method availability, which likewise varies by operator country.
