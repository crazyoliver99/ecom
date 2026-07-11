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


def test_schedule_missing_key_exits_2(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused@localhost:5432/unused")
    monkeypatch.delenv("KEEPA_API_KEY", raising=False)
    config_module.get_settings.cache_clear()

    exit_code = main(["schedule", "--max-cycles", "1"])
    assert exit_code == 2

    config_module.get_settings.cache_clear()


def test_schedule_parses_options():
    args = build_parser().parse_args(
        ["schedule", "--interval-seconds", "30", "--max-cycles", "2", "--category", "7"]
    )
    assert args.command == "schedule"
    assert args.interval_seconds == 30
    assert args.max_cycles == 2
    assert args.category == 7


def test_morning_report_no_data(monkeypatch, migrated_db, capsys):
    """morning-report prints a friendly message and exits 0 when there are no
    successful runs. Runs against the migrated test database."""
    monkeypatch.setenv("DATABASE_URL", migrated_db)
    config_module.get_settings.cache_clear()

    import app.core.db as db_module

    db_module._engine = None
    db_module._session_factory = None

    exit_code = main(["morning-report"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "No successful collection runs yet" in out

    config_module.get_settings.cache_clear()
    db_module._engine = None
    db_module._session_factory = None
