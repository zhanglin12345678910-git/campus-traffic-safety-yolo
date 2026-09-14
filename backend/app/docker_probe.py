from __future__ import annotations

import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "agent_runs",
    "agent_steps",
    "alembic_version",
    "detection_results",
    "inspection_images",
    "inspection_tasks",
    "knowledge_documents",
    "manual_reviews",
    "reports",
    "risk_assessments",
    "users",
}


def alembic_config() -> Config:
    # No ini file: callers only need the script location, and loading
    # alembic.ini would reconfigure logging for the whole process.
    config = Config()
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


def expected_revision() -> str:
    """Return the migration head so the probe never lags behind new revisions."""
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    if head is None:
        raise RuntimeError("Alembic 迁移目录没有可用的 head 版本")
    return head


def inspect_database(
    engine: Engine,
    *,
    required_dialect: str = "mysql",
    expected: str | None = None,
) -> dict[str, object]:
    expected = expected or expected_revision()
    tables = set(inspect(engine).get_table_names())
    missing = sorted(EXPECTED_TABLES - tables)
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    dialect = engine.dialect.name
    dialect_matches = dialect == required_dialect
    revision_matches = revision == expected
    return {
        "status": "passed" if not missing and dialect_matches and revision_matches else "failed",
        "dialect": dialect,
        "required_dialect": required_dialect,
        "database": engine.url.database,
        "revision": revision,
        "expected_revision": expected,
        "revision_matches": revision_matches,
        "tables": sorted(tables),
        "missing_tables": missing,
        "dialect_matches": dialect_matches,
    }


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        result = inspect_database(engine)
        print(json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
