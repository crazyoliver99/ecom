"""Keepa provider adapter — licensed Amazon price/rank/review history API.

This is the reference provider for Atlas. It returns raw observations only and
never writes to the database (see providers/README.md and FOUNDATION.md §8): the
collection job in app/collection turns what this returns into observations,
facts, signals, and events.

API shape (confirmed against Keepa's official Java backend `Request.java` and the
public `keepa` Python client docs):
- Base URL: https://api.keepa.com
- GET /bestsellers?key=<KEY>&domain=<n>&category=<id>
    -> {"bestSellersList": {"asinList": [ASIN, ...]}, "tokensLeft": int, ...}
  The asinList is ordered best-first (strongest sales rank first).
- GET /product?key=<KEY>&domain=<n>&asin=<csv up to 100>&stats=1
    -> {"products": [{"asin","title","stats":{"current":[...]},"salesRanks",...}],
        "tokensLeft": int, ...}
- domain 1 == amazon.com (US). Quota is token-based; HTTP 429 when exhausted.

The API key is read only from KEEPA_API_KEY (via Settings) and is never logged or
placed in an exception message.
"""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from urllib.parse import urlencode

# Keepa CSV column indices (from Keepa's documented csv layout). Index 3 is the
# Amazon sales-rank series; stats.current[3] is the current sales rank, or -1 when
# Keepa has no data for it.
KEEPA_CSV_SALES_RANK = 3
KEEPA_NO_DATA = -1

US_DOMAIN = 1
DEFAULT_BASE_URL = "https://api.keepa.com"

# A transport takes (url, timeout_seconds) and returns (status_code, body_bytes).
# Injected in tests so the client can be exercised without network access.
Transport = Callable[[str, float], tuple[int, bytes]]


class KeepaError(Exception):
    """Base class for all Keepa adapter failures."""


class KeepaConfigError(KeepaError):
    """Missing/invalid configuration (e.g. no API key)."""


class KeepaAuthError(KeepaError):
    """Authentication/authorization failure (HTTP 401/403). Not retried."""


class KeepaRateLimitError(KeepaError):
    """Quota/rate limit exhausted (HTTP 429). Retried, then surfaced."""


class KeepaTransientError(KeepaError):
    """Transient failure (network error or HTTP 5xx). Retried, then surfaced."""


def _urllib_transport(url: str, timeout: float) -> tuple[int, bytes]:
    """Default transport backed by the standard library."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        # HTTP errors carry a status and a body — hand both back for classification.
        return exc.code, exc.read()


class KeepaClient:
    """Thin, resilient HTTP client for the two endpoints this milestone needs.

    Resilience: per-request timeout, bounded retries with exponential backoff for
    transient (5xx / network) and rate-limit (429) failures, and explicit error
    classification so callers can distinguish a config problem from a quota
    problem from an outage.
    """

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        domain: int = US_DOMAIN,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not api_key:
            raise KeepaConfigError(
                "Keepa API key is missing — set KEEPA_API_KEY in the environment."
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._domain = domain
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._transport = transport or _urllib_transport
        self._sleep = sleep

    def get_bestsellers(self, category_id: int, *, use_rank_average: bool = False) -> dict:
        """Fetch the bestseller ASIN list for one category (ordered best-first)."""
        params = {"domain": self._domain, "category": category_id}
        if use_rank_average:
            params["range"] = 90
        return self._request("bestsellers", params)

    def get_products(self, asins: list[str], *, stats: bool = True) -> dict:
        """Fetch product objects for up to 100 ASINs in one call."""
        if not asins:
            return {"products": []}
        if len(asins) > 100:
            raise KeepaError("Keepa accepts at most 100 ASINs per product request")
        params = {"domain": self._domain, "asin": ",".join(asins)}
        if stats:
            params["stats"] = 1
        return self._request("product", params)

    def _request(self, path: str, params: dict) -> dict:
        # The key goes on the wire but is never stored on the instance URL nor put
        # into any exception, so it cannot leak through logs or error messages.
        query = urlencode({"key": self._api_key, **params})
        url = f"{self._base_url}/{path}?{query}"
        safe_target = f"/{path}"

        attempt = 0
        while True:
            try:
                status, body = self._transport(url, self._timeout)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < self._max_retries:
                    self._backoff(attempt)
                    attempt += 1
                    continue
                raise KeepaTransientError(
                    f"network error calling Keepa {safe_target}: {exc}"
                ) from exc

            if status == 200:
                return self._parse(body, safe_target)
            if status in (401, 403):
                raise KeepaAuthError(
                    f"Keepa rejected the API key (HTTP {status}) on {safe_target}"
                )
            if status == 429:
                if attempt < self._max_retries:
                    self._backoff(attempt)
                    attempt += 1
                    continue
                raise KeepaRateLimitError(
                    f"Keepa quota/rate limit exhausted (HTTP 429) on {safe_target}"
                )
            if 500 <= status < 600:
                if attempt < self._max_retries:
                    self._backoff(attempt)
                    attempt += 1
                    continue
                raise KeepaTransientError(f"Keepa server error (HTTP {status}) on {safe_target}")
            raise KeepaError(f"Keepa returned unexpected HTTP {status} on {safe_target}")

    def _parse(self, body: bytes, safe_target: str) -> dict:
        try:
            return json.loads(body)
        except (ValueError, TypeError) as exc:
            raise KeepaError(f"Keepa returned invalid JSON on {safe_target}: {exc}") from exc

    def _backoff(self, attempt: int) -> None:
        # Exponential: base, 2*base, 4*base, ...
        self._sleep(self._backoff_base * (2**attempt))


def extract_sales_rank(product: dict) -> int | None:
    """Pull the current Amazon sales rank out of a Keepa product object.

    Prefers stats.current[3] (the SALES series). Falls back to the most recent
    value in salesRanks. Returns None when Keepa reports no rank data (-1) or the
    field is absent — the caller treats "no rank" as "no fact", never as rank 0.
    """
    stats = product.get("stats")
    if isinstance(stats, dict):
        current = stats.get("current")
        if isinstance(current, list) and len(current) > KEEPA_CSV_SALES_RANK:
            rank = current[KEEPA_CSV_SALES_RANK]
            if isinstance(rank, int) and rank != KEEPA_NO_DATA and rank > 0:
                return rank

    sales_ranks = product.get("salesRanks")
    if isinstance(sales_ranks, dict) and sales_ranks:
        # Each value is a flat [timestamp, rank, timestamp, rank, ...] history;
        # the last element is the most recent rank.
        for history in sales_ranks.values():
            if isinstance(history, list) and len(history) >= 2:
                rank = history[-1]
                if isinstance(rank, int) and rank != KEEPA_NO_DATA and rank > 0:
                    return rank
    return None
