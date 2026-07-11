# Provider Access Spike: <Provider / Capability Name>

| | |
|---|---|
| **Capability** | <which system capability this serves, e.g. "Meta ad intelligence"> |
| **Verified on** | <YYYY-MM-DD — the date every claim below was checked against live sources> |
| **Context assumed** | <country of residence, entity status, intended use — classifications may differ for other contexts> |
| **Final classification** | `usable_now` / `needs_approval` / `paid_option` / `manual_only` / `blocked` |

> Every factual claim in this record must cite the source URL it was verified
> at. "Unknown, because <reason>" is an acceptable answer; an empty field is
> not. Re-verify this record when the provider errors persistently or before
> building an adapter on it (FOUNDATION.md §8.1).

## 1. Official documentation

<Primary docs URLs.>

## 2. Access & approval requirements

<Registration, identity/business verification, app review, waitlists —
and explicitly whether the assumed context (country/entity) can complete them.>

## 3. Geographic & dataset coverage

<Which countries/regions, which data fields we would actually get.>

## 4. Pricing & rate limits

<Free-tier boundaries, paid tiers, request/token limits, overage behavior.>

## 5. Storage & usage restrictions

<Can responses be stored? For how long? Attribution/display rules?
Prohibitions relevant to our use case? Deletion obligations?>

## 6. Arbitrary ecommerce product search?

<Can we search any product/keyword, or only restricted subsets?>

## 7. Minimal test request

<Exact endpoint + parameters. If executed: the (redacted) request and response.
If gated behind access we don't have: the exact plan to run once granted.>

## 8. Fallback options

<Alternative providers if this route fails, with pricing where public.>

## 9. Final classification & rationale

<The classification from the header, justified in a few sentences.
An adapter may only be built for `usable_now` or an accepted `paid_option`
route (FOUNDATION.md §8.1).>

## Sources

<Every URL cited above, one line each: URL — what claim it supports.>
