"""v2265_alarm_okundu

Revision ID: v2265_alarm_okundu
Revises: v2264_dis_api
Create Date: 2026-09-06

v2.265 — Dalga 5.17: alarm okundu/atama — alerts.acked_at (acked_by ilk şemadan) + assigned_to.
"""
from alembic import op

revision = "v2265_alarm_okundu"
down_revision = "v2264_dis_api"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acked_at timestamptz")
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS assigned_to uuid")


def downgrade() -> None:
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS assigned_to")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS acked_at")
