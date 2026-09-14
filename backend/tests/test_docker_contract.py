from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from fastapi import FastAPI
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings
from app.docker_probe import EXPECTED_TABLES, alembic_config, expected_revision, inspect_database


def test_docker_schema_probe_matches_application_models(app: FastAPI) -> None:
    application_tables = set(inspect(app.state.database.engine).get_table_names())

    assert application_tables == EXPECTED_TABLES - {"alembic_version"}


def test_docker_schema_probe_validates_revision_tables_and_dialect(app: FastAPI) -> None:
    engine = app.state.database.engine
    head = expected_revision()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": head})

    result = inspect_database(engine, required_dialect="sqlite")

    assert result["status"] == "passed"
    assert result["dialect"] == "sqlite"
    assert result["revision"] == head
    assert result["revision_matches"] is True
    assert result["missing_tables"] == []
    assert set(result["tables"]) == EXPECTED_TABLES

    wrong_dialect = inspect_database(engine, required_dialect="mysql")
    assert wrong_dialect["status"] == "failed"
    assert wrong_dialect["dialect_matches"] is False

    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = 'stale_revision'"))
    stale_revision = inspect_database(engine, required_dialect="sqlite")
    assert stale_revision["status"] == "failed"
    assert stale_revision["revision_matches"] is False


def test_docker_schema_probe_accepts_database_migrated_to_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Run the real migrations the container entrypoint runs, so a probe that
    # lags behind a new revision fails here instead of in Docker acceptance.
    database_url = f"sqlite:///{(tmp_path / 'probe.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        command.upgrade(alembic_config(), "head")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    try:
        result = inspect_database(engine, required_dialect="sqlite")
    finally:
        engine.dispose()

    assert result["status"] == "passed", result
    assert result["revision"] == expected_revision()
