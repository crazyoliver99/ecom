"""Keepa provider adapter (licensed Amazon price/rank API).

This is the reference implementation for the Atlas provider pattern:
1. Provider-specific logic is fully isolated (this module)
2. Adapters emit provider-agnostic Signals (defined in app/signals/)
3. New providers follow the same pattern without modifying existing adapters
4. The second provider should take ~10% of the effort of the first

TODO: Implement Keepa API client
- Keepa API docs: https://keepa.com/api/
- Requires API key (licensed_data compliance)
- Target: US bestsellers in a single fixed category (e.g., Home Office)
- Observation types:
  * keepa_bestseller_product: ASIN, title, sales_rank, sales_velocity, reviews
- Rate limiting: Per Keepa's API quota
- Fact detection: sales_rank → sales_rank_history fact (all timestamps), score new bestseller
- Signal detection:
  * new_bestseller_detected: when sales_rank < 100k and no prior fact
  * rank_improved: when sales_rank < prior_fact.sales_rank
"""

# Stub: implementation deferred to Phase 3 when Keepa subscription is active
