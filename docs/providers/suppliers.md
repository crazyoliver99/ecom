# Provider Access Spike: Suppliers (CJ Dropshipping, AliExpress, Alibaba)

| | |
|---|---|
| **Capability** | Supplier data — product cost, shipping options/times, stock, for margin & shipping-difficulty estimates |
| **Verified on** | 2026-07-11 |
| **Context assumed** | Individual in Egypt, no registered company, single-user internal research tool |
| **Final classification** | CJ Dropshipping: `usable_now` · AliExpress affiliate API: `needs_approval` · Alibaba.com: `manual_only` |

## 1. Official documentation

- CJ Dropshipping docs: <https://developers.cjdropshipping.com/> (mirror <https://developers.cjdropshipping.cn/en/api/api2/>) — auth, product, logistics endpoints
- AliExpress Open Platform: <https://openservice.aliexpress.com/doc/doc.htm> · API reference <https://openservice.aliexpress.com/doc/api.htm> · affiliate portal <https://portals.aliexpress.com/>
- AliExpress API Use Agreement: <https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202201220006_10755.html>
- Alibaba.com Open Platform: <https://openapi.alibaba.com/doc/doc.htm>

## 2. Access & approval requirements

- **CJ: self-serve, no approval.** Free account (email signup, no card, no business registration); API key self-generated in the dashboard (My CJ → Authorization → API). No Egypt restriction found; CJ positions itself "worldwide to worldwide" — though no explicit supported-country list is published, so treat Egypt acceptance as high-probability, confirmed at signup.
- **AliExpress: two human-review gates.** (1) Affiliate program acceptance — requires declaring a promotion channel (website/social/YouTube), review takes days; (2) Open Platform app approval (~1–2 business days) — individuals can upload personal ID where a business license is requested. Open internationally; no Egypt exclusion found but not explicitly confirmed. The deeper `aliexpress.ds.*` API tier needs seller-center registration + endpoint whitelisting (heavier `needs_approval`).
- **Alibaba.com:** developer registration open, but the API surface is ISV/seller-transaction oriented; no verifiable open product-search API for non-partners.

## 3. Geographic & dataset coverage

- **CJ:** millions of SKUs with per-variant warehouse locations (China + overseas); `freightCalculate` quotes arbitrary origin→destination country pairs — so shipping cost/time to **any customer market** (US, EU, GCC, EG) is directly queryable. Products include price, variants, stock, `listedNum` (how many stores list it — a demand proxy).
- **AliExpress affiliate:** the affiliate-promotable AliExpress catalog; `aliexpress.affiliate.product.query` supports `ship_to_country`, `delivery_days`, currency/language targeting — and returns `lastest_volume` (recent orders count), the single best free demand signal in this whole spike.
- **Alibaba.com:** B2B wholesale; effectively manual browsing for us.

## 4. Pricing & rate limits

- **CJ: free.** Documented at roughly **1 call/second (QPS 1)**; `getAccessToken` returns the same token for 24h. Full per-endpoint quota table not retrievable from the research sandbox — **verify in the docs after signup**; historically some endpoints enforce long minimum intervals, so the ingestion layer must queue requests.
- **AliExpress: free.** No official public per-token limit table; app console reportedly shows a "flow rate" limit of 5,000 for new apps; heavy sync loads can trigger temporary token freezes.
- **Alibaba.com:** account-level call counting; exceeding limits forces a paid subscription.

## 5. Storage & usage restrictions

- **AliExpress — strict:** the API Use Agreement forbids storing/using "operation data" without written consent and the Developer DPA requires destroying data on termination. The affiliate API is contractually intended for *promotion*, not pure market analytics. Practical stance for us: fetch on demand, store the derived metrics and evidence references we need for a decision, do not warehouse their catalog long-term.
- **CJ:** API terms text could not be read from the research sandbox — **unverified, not "no restrictions"**; re-check at signup.
- **Alibaba:** platform rules prohibit copying/distributing user data.

## 6. Arbitrary ecommerce product search?

- **CJ: yes** — free-text keyword search (`product/listV2?keyWord=...`), plus category/warehouse filters. Limitation: searches CJ's catalog only; "arbitrary product" works to the extent CJ carries an equivalent.
- **AliExpress: yes** — `aliexpress.affiliate.product.query` with free-text `keywords`, price filters, `ship_to_country`, sort; returns price, rating (`evaluate_rate`), order counts.
- **Alibaba: effectively no** (for a non-partner individual).

## 7. Minimal test request

No-credential probes from the research sandbox were blocked by its egress proxy (CONNECT 403), so run these after signup:

**CJ (free account + dashboard API key):**
```
POST https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken   {"apiKey": "***"}
GET  https://developers.cjdropshipping.com/api2.0/v1/product/listV2?page=1&size=20&keyWord=hoodie   (header CJ-Access-Token)
POST https://developers.cjdropshipping.com/api2.0/v1/logistic/freightCalculate
     {"startCountryCode":"CN","endCountryCode":"US","products":[{"quantity":1,"vid":"<variant-from-search>"}]}
```
Success: search returns products with prices; freight returns `[{logisticName, logisticPrice, logisticAging}]`. Run the search once without the token header to document the auth-gate error.

**AliExpress (after both approvals):** signed `POST https://api-sg.aliexpress.com/sync` with `method=aliexpress.affiliate.product.query, keywords=hoodie, ship_to_country=US, target_currency=USD, page_size=20` (MD5 bookend signature). Success: products with `target_sale_price` and `lastest_volume`.

## 8. Fallback options

- **AutoDS API:** real API but approval-gated with a **$5,000 one-time activation fee** plus subscription — not sensible for a single-user tool (`paid_option` in name only).
- **Zendrop:** no public API (`blocked`). **Spocket:** no verifiable public developer docs (`manual_only`).
- **Apify/RapidAPI third-party scrapers** for CJ/AliExpress data — usage-priced, but they are unofficial scrapers; ToS risk noted, use at most as a stopgap during the AliExpress approval window, flagged `best_effort`.
- **Manual floor:** browse CJ/AliExpress/Alibaba by hand, record costs and shipping quotes as manual evidence.

## 9. Final classification & rationale

**CJ Dropshipping: `usable_now`** — free, no approval, individual-friendly, keyword search plus per-country freight quotes; the first real supplier adapter should be CJ. Residual unknowns (per-endpoint quotas, API terms text) are checkable in minutes after a free signup. **AliExpress affiliate: `needs_approval`** — the best free demand-signal data (`lastest_volume`), worth starting both applications now, but plan around discretionary review and strict data-retention terms. **Alibaba.com: `manual_only`** for this use case.

## Sources

- <https://developers.cjdropshipping.cn/en/api/api2/api/auth.html> — getAccessToken, QPS 1/sec, 24h token caching (via search snippet of official doc)
- <https://developers.cjdropshipping.cn/en/api/api2/api/product.html> — product search fields incl. `sellPrice`, `listedNum`; `listV2?keyWord=` (via search snippet)
- <https://developers.cjdropshipping.cn/en/api/api2/api/logistic.html> — `freightCalculate` params/response (via search snippet)
- <https://developers.cjdropshipping.com/en/summary/course.html> — self-serve API key path (via search snippet)
- <https://cjdropshipping.com/register.html>, <https://revenuegeeks.com/cjdropshipping-free/> — free signup, no card/company
- <https://openservice.aliexpress.com/doc/doc.htm>, <https://openservice.aliexpress.com/doc/api.htm> — Open Platform registration and API reference
- <https://open.alitrip.com/docs/api.htm?apiId=45803> — `aliexpress.affiliate.product.query` request/response fields incl. `lastest_volume` (official doc mirror)
- <https://wasabitheme.com/blog/aliexpress-affiliate-api/>, <https://elfsight.com/blog/how-to-get-and-use-aliexpress-api-key/> — app types, personal-ID-for-individuals, review timelines, flow-rate limit
- <https://strackr.com/blog/aliexpress-affiliate-program> — affiliate signup requires a promotion channel
- <https://zuplo.com/blog/2024/10/02/aliexpress-api-guide> — DS-tier approval and whitelisting
- <https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202201220006_10755.html>, <https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202201220006_67205.html> — storage prohibition and DPA destruction requirement
- <https://www.oriollopez.com/posts/how-to-use-aliexpress-affiliates-with-nodejs/>, <https://vandevliet.me/how-to-make-aliexpress-affiliate-api-call/> — gateway + signing scheme
- <https://openapi.alibaba.com/doc/doc.htm> — Alibaba registration, quota → paid subscription (via search snippet)
- <https://www.autods.com/api/>, <https://help.autods.com/special-feature/api-feature-automate-product-imports-orders-and-sourcing> — AutoDS API, $5,000 activation
- <https://checkthat.ai/brands/zendrop/pricing>, <https://www.zendrop.com/pricing/> — Zendrop has no API
- <https://apitracker.io/a/spocket-co> — no verifiable Spocket developer docs
- <https://apify.com/muhammetakkurtt/cj-dropshipping-scraper/api>, <https://rapidapi.com/georgekhananaev/api/aliexpress-true-api> — third-party scraper stopgaps

**Country/entity dependencies:** CJ — individual OK, Egypt not explicitly listed (confirm at signup). AliExpress — individual OK via personal ID, approval discretionary, needs a promotion channel; confirm Egypt payout rails at signup. Alibaba — ISV/seller-oriented.
