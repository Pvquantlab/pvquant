"""v2279_skill_cliper

Revision ID: v2279_skill_cliper
Revises: v2274_meteo_nem
Create Date: 2026-09-07

v2.279 — Tablo 3.2 satır 6: Yang 2019 referansı — iklimsel + akıllı persistans optimal konveks birleşimi (CLIPER) WMAPE'si
ve ona karşı beceri; skill_daily'ye iki kolon.
"""
from alembic import op

revision = "v2279_skill_cliper"
down_revision = "v2274_meteo_nem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE skill_daily ADD COLUMN IF NOT EXISTS cliper_wmape double precision")
    op.execute("ALTER TABLE skill_daily ADD COLUMN IF NOT EXISTS skill_vs_cliper double precision")


def downgrade() -> None:
    op.execute("ALTER TABLE skill_daily DROP COLUMN IF EXISTS skill_vs_cliper")
    op.execute("ALTER TABLE skill_daily DROP COLUMN IF EXISTS cliper_wmape")
