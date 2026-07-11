# Provider Access Spike — Summary & Decisions

**Completed:** 2026-07-11 · **Context:** individual in Egypt, no registered company, single-user internal research tool.
All claims are sourced in the individual records in this directory. Third-party pricing figures must be re-confirmed on vendor pages before purchase.

## Recommendation table

| Capability | Recommended route | Classification | Est. monthly cost | Ahmed must do |
|---|---|---|---|---|
| Meta ads | Web Ad Library (manual, global) now; official API after ID verification — **EU commercial ads only** | `needs_approval` (API) / `manual_only` (global) | $0 (API free) | facebook.com/ID verification + developer app |
| TikTok ads | Creative Center + Commercial Content Library (manual); PiPiAds later if needed | `manual_only` (official) / `paid_option` (PiPiAds $49) | $0 now | Free TikTok for Business account |
| TikTok organic | Official APIs unavailable to us; Kalodata later if needed | `blocked` (official) / `paid_option` (Kalodata ~$38) | $0 now | — |
| Google Trends | SerpApi free tier → DataForSEO pay-per-task; apply to official alpha in parallel | `paid_option` | ~$0–10 | SerpApi signup; alpha application |
| Amazon marketplace | **Keepa API** (only native price/rank/review history; PA-API is retired) | `paid_option` | **~€49 (~$53)** | Subscribe; **read retention clause first** |
| Suppliers | **CJ Dropshipping API** (free, self-serve) + AliExpress affiliate API when approved | `usable_now` (CJ) / `needs_approval` (AliExpress) | $0 | CJ signup + API key; start AliExpress application |
| Reddit | Official Data API after Responsible-Builder approval; manual browsing as floor | `needs_approval` | $0 (free tier) | Reddit app + access request |
| Competitor stores | Manual analysis + Meta Ad Library cross-reference; StoreLeads Pro only if proven need | `manual_only` floor / `paid_option` (StoreLeads $250) | $0 now | Nothing yet |

**Scraping policy (binding, from competitor_stores.md):** the system never scrapes storefronts or any surface whose terms prohibit it; missing data is recorded as unavailable, never guessed or scraped.

## Cost roll-up

- **Core recommended stack (start of Phase 3):** Keepa ~$53 + DataForSEO ~$5–10 ≈ **~$60/month**. Everything else in the core plan is free (CJ, Meta API, Reddit free tier, manual surfaces).
- **Optional expansions (adopt only when scoring proves the need):** PiPiAds $49 (TikTok ads, has API) · Kalodata ~$38 (TikTok Shop/organic) · BigSpy $9 or Minea $49 (global Meta ad intel) · StoreLeads Pro $250 (systematic competitor data). Fully-loaded worst case ≈ $460/mo — **not recommended now**.

## Prioritized action list (Ahmed)

1. **CJ Dropshipping** — free signup, generate API key (My CJ → Authorization → API), read the API terms and per-endpoint quotas we couldn't fetch. Unblocks the first real adapter.
2. **Keepa** — read the API T&C retention clause at signup, confirm current pricing, then subscribe (~€49). The retention clause is this spike's most important unverified item.
3. **SerpApi** — free account (250 searches/mo) for trends prototyping; note DataForSEO as the production route.
4. **AliExpress affiliate + Open Platform applications** — needs a declared promotion channel; start now, approval takes days and is discretionary.
5. **Meta** — identity/location confirmation at facebook.com/ID (Egyptian ID; confirm it's supported — login-gated, unverified), then developer app with Ad Library API product.
6. **Reddit** — create account + script app, submit the data-access request describing a single-user, read-only, low-volume research tool that summarizes but does not train on content and honors deletion syncing.
7. **Google Trends alpha application** — free, low odds, no downside.
8. **TikTok for Business** — free account for full Creative Center browsing.

## Uncertainties & country/entity dependencies

1. **Keepa retention clause** — unread (sandbox egress blocked keepa.com); must be read before we persist Keepa data. Mitigation: Keepa serves full history on demand, so we can store only derived metrics.
2. **facebook.com/ID Egypt support** — high confidence (Egypt is on Meta's transparency-enforcement list) but the supported-country list is login-gated.
3. **Reddit approval outcome** — discretionary; Reddit's purpose-based commercial definition may route us to the paid track ($0.24/1k calls).
4. **CJ Egypt registration** — no restriction found, no explicit country list published; confirmed only by signing up. CJ API terms text also unread.
5. **AliExpress approval** — individual-with-personal-ID is documented as workable, but acceptance requires a credible promotion channel; Egypt payout rails unconfirmed.
6. **All third-party pricing** (Keepa tiers, StoreLeads, PiPiAds, BigSpy, Minea, Rainforest) — sourced from trackers/reviews because vendor pages were unreachable from the research sandbox; confirm before paying.
7. **TikTok Commercial Content API** — application outcome unknowable without applying, but the dataset is EU-only regardless, so our classification doesn't depend on it.

## Standing rule

Per FOUNDATION.md §8.1: an adapter may be built **only** for a route classified `usable_now` or an accepted `paid_option`. As of this spike that means: **CJ Dropshipping now; Keepa and a trends provider once subscribed; Meta EU / AliExpress / Reddit after their respective approvals land.** Records are re-verified when a provider errors persistently or before adapter work begins.
