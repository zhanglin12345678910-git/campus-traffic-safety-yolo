"""add multimodel vision metadata and event storage

Revision ID: 0002_multimodel_vision
Revises: 0001_initial
Create Date: 2026-09-10
"""

import sqlalchemy as sa
from alembic import op


revision = "0002_multimodel_vision"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 0001 intentionally used Base.metadata.create_all().  On a fresh
    # database that call sees the latest ORM metadata, so these columns may
    # already exist before this revision runs.  Inspect first to keep both
    # fresh installs and upgrades of existing local databases safe.
    inspector = sa.inspect(op.get_bind())
    task_columns = {item["name"] for item in inspector.get_columns("inspection_tasks")}
    detection_columns = {item["name"] for item in inspector.get_columns("detection_results")}
    if "vision_events_json" not in task_columns:
        op.add_column(
            "inspection_tasks",
            sa.Column("vision_events_json", sa.Text(), nullable=False, server_default="[]"),
        )
    if "display_name" not in detection_columns:
        op.add_column(
            "detection_results",
            sa.Column("display_name", sa.String(length=160), nullable=False, server_default=""),
        )
    if "model_role" not in detection_columns:
        op.add_column(
            "detection_results",
            sa.Column("model_role", sa.String(length=40), nullable=False, server_default="traffic_sign"),
        )
    if "model_name" not in detection_columns:
        op.add_column(
            "detection_results",
            sa.Column("model_name", sa.String(length=255), nullable=False, server_default=""),
        )
    index_names = {item["name"] for item in inspector.get_indexes("detection_results")}
    if "ix_detection_results_model_role" not in index_names:
        op.create_index("ix_detection_results_model_role", "detection_results", ["model_role"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    index_names = {item["name"] for item in inspector.get_indexes("detection_results")}
    if "ix_detection_results_model_role" in index_names:
        op.drop_index("ix_detection_results_model_role", table_name="detection_results")
    detection_columns = {item["name"] for item in inspector.get_columns("detection_results")}
    for column_name in ("model_name", "model_role", "display_name"):
        if column_name in detection_columns:
            op.drop_column("detection_results", column_name)
    task_columns = {item["name"] for item in inspector.get_columns("inspection_tasks")}
    if "vision_events_json" in task_columns:
        op.drop_column("inspection_tasks", "vision_events_json")
