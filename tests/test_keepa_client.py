"""Tests for the Keepa HTTP client: parsing, error classification, retries.

All network I/O is replaced by an injected transport, so these run offline.
"""

import json

import pytest
from app.providers.keepa import (
    KeepaAuthError,
    KeepaClient,
    KeepaConfigError,
    KeepaError,
    KeepaRateLimitError,
    KeepaTransientError,
    extract_sales_rank,
)


def _json_body(obj) -> bytes:
    return json.dumps(obj).encode()


class ScriptedTransport:
    """Returns queued (status, body) responses; records the URLs it was called
    with so tests can assert on retries and parameters."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[str] = []

    def __call__(self, url, timeout):
        self.calls.append(url)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client(transport, **kwargs):
    # sleep is a no-op so backoff does not slow the suite.
    return KeepaClient(
        "secret-key",
        transport=transport,
        sleep=lambda _s: None,
        max_retries=2,
        **kwargs,
    )


class TestConfig:
    def test_missing_key_raises_config_error(self):
        with pytest.raises(KeepaConfigError):
            KeepaClient(None)

    def test_empty_key_raises_config_error(self):
        with pytest.raises(KeepaConfigError):
            KeepaClient("")


class TestSuccess:
    def test_bestsellers_parsed_and_params(self):
        body = {"bestSellersList": {"asinList": ["A1", "A2"]}, "tokensLeft": 99}
        transport = ScriptedTransport([(200, _json_body(body))])
        client = _client(transport)
        result = client.get_bestsellers(12345)
        assert result["bestSellersList"]["asinList"] == ["A1", "A2"]
        url = transport.calls[0]
        assert "bestsellers?" in url
        assert "domain=1" in url
        assert "category=12345" in url

    def test_products_parsed_and_params(self):
        body = {"products": [{"asin": "A1", "title": "Widget"}], "tokensLeft": 98}
        transport = ScriptedTransport([(200, _json_body(body))])
        client = _client(transport)
        result = client.get_products(["A1", "A2"])
        assert result["products"][0]["asin"] == "A1"
        url = transport.calls[0]
        assert "product?" in url
        assert "asin=A1%2CA2" in url  # comma-encoded
        assert "stats=1" in url

    def test_empty_asins_short_circuits(self):
        transport = ScriptedTransport([])
        client = _client(transport)
        assert client.get_products([]) == {"products": []}
        assert transport.calls == []

    def test_too_many_asins_rejected(self):
        client = _client(ScriptedTransport([]))
        with pytest.raises(KeepaError, match="at most 100"):
            client.get_products([f"A{i}" for i in range(101)])


class TestErrorClassification:
    def test_auth_error_not_retried(self):
        transport = ScriptedTransport([(403, b"")])
        client = _client(transport)
        with pytest.raises(KeepaAuthError):
            client.get_bestsellers(1)
        assert len(transport.calls) == 1  # no retry on auth failure

    def test_rate_limit_retried_then_raised(self):
        transport = ScriptedTransport([(429, b""), (429, b""), (429, b"")])
        client = _client(transport)  # max_retries=2 -> 3 attempts total
        with pytest.raises(KeepaRateLimitError):
            client.get_bestsellers(1)
        assert len(transport.calls) == 3

    def test_rate_limit_recovers_on_retry(self):
        body = {"bestSellersList": {"asinList": []}}
        transport = ScriptedTransport([(429, b""), (200, _json_body(body))])
        client = _client(transport)
        result = client.get_bestsellers(1)
        assert result["bestSellersList"]["asinList"] == []
        assert len(transport.calls) == 2

    def test_server_error_retried_then_transient(self):
        transport = ScriptedTransport([(500, b""), (503, b""), (500, b"")])
        client = _client(transport)
        with pytest.raises(KeepaTransientError):
            client.get_bestsellers(1)
        assert len(transport.calls) == 3

    def test_network_error_retried_then_transient(self):
        transport = ScriptedTransport(
            [OSError("connection reset"), OSError("connection reset"), OSError("boom")]
        )
        client = _client(transport)
        with pytest.raises(KeepaTransientError):
            client.get_bestsellers(1)
        assert len(transport.calls) == 3

    def test_unexpected_status_raises_generic(self):
        transport = ScriptedTransport([(418, b"")])
        client = _client(transport)
        with pytest.raises(KeepaError):
            client.get_bestsellers(1)

    def test_invalid_json_raises(self):
        transport = ScriptedTransport([(200, b"not json")])
        client = _client(transport)
        with pytest.raises(KeepaError, match="invalid JSON"):
            client.get_bestsellers(1)

    def test_api_key_never_in_exception(self):
        transport = ScriptedTransport([(403, b"")])
        client = _client(transport)
        try:
            client.get_bestsellers(1)
        except KeepaAuthError as exc:
            assert "secret-key" not in str(exc)


class TestExtractSalesRank:
    def test_from_stats_current(self):
        product = {"stats": {"current": [10, 20, 30, 1234]}}  # index 3 = SALES
        assert extract_sales_rank(product) == 1234

    def test_no_data_sentinel_returns_none(self):
        product = {"stats": {"current": [10, 20, 30, -1]}}
        assert extract_sales_rank(product) is None

    def test_falls_back_to_sales_ranks_history(self):
        product = {"salesRanks": {"12345": [1000000, 5000, 1000100, 4200]}}
        assert extract_sales_rank(product) == 4200

    def test_missing_everything_returns_none(self):
        assert extract_sales_rank({"asin": "A1"}) is None
