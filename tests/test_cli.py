"""Tests for the operational CLI."""

import app.core.config as config_module
import pytest
from app.cli import build_parser, main


def test_parser_requires_a_command():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_collect_keepa_parses_options():
    args = build_parser().parse_args(["collect-keepa", "--category", "42", "--max-products", "5"])
    assert args.command == "collect-keepa"
    assert args.category == 42
    assert args.max_products == 5


def test_collect_keepa_missing_key_exits_2(monkeypatch):
    """Without KEEPA_API_KEY the command fails fast with exit code 2 and never
    touches the database."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused@localhost:5432/unused")
    monkeypatch.delenv("KEEPA_API_KEY", raising=False)
    config_module.get_settings.cache_clear()

    exit_code = main(["collect-keepa"])
    assert exit_code == 2

    config_module.get_settings.cache_clear()
