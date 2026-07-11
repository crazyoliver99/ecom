"""The guard rails themselves must be tested — they protect the real database."""

import pytest

from tests.db_safety import ensure_test_database_url, load_test_database_url


def test_accepts_databases_clearly_marked_as_test():
    for name in ("ecom_test", "test_ecom", "mytestdb"):
        url = f"postgresql+psycopg://u:p@localhost:5432/{name}"
        assert ensure_test_database_url(url) == url


def test_rejects_development_looking_databases():
    for name in ("ecom", "production", "app"):
        with pytest.raises(RuntimeError, match="Refusing to run tests"):
            ensure_test_database_url(f"postgresql+psycopg://u:p@localhost:5432/{name}")


def test_rejects_garbage_urls():
    with pytest.raises(RuntimeError, match="not a valid database URL"):
        ensure_test_database_url("::not a url::")


def test_never_falls_back_to_database_url(tmp_path, monkeypatch):
    # Even with DATABASE_URL present (env + .env), missing TEST_DATABASE_URL must fail.
    monkeypatch.chdir(tmp_path)  # hide the project's real .env
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://u:p@h:5432/ecom\n")

    environ = {"DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/ecom"}
    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL is not set"):
        load_test_database_url(environ)


def test_reads_test_url_from_env_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://u:p@h:5432/ecom\n"
        "TEST_DATABASE_URL=postgresql+psycopg://u:p@h:5432/ecom_test\n"
    )
    assert load_test_database_url({}) == "postgresql+psycopg://u:p@h:5432/ecom_test"
