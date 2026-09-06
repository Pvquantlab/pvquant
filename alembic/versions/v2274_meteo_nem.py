"""v2274_meteo_nem

Revision ID: v2274_meteo_nem
Revises: v2273_meteo_uye
Create Date: 2026-09-06

v2.274 — Dalga 3 tamamlayıcısı: meteo_arsiv.relative_humidity (ECMWF 2 m çiy noktasından; spektral terim için).
"""
from alembic import op

revision = "v2274_meteo_nem"
down_revision = "v2273_meteo_uye"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE meteo_arsiv ADD COLUMN IF NOT EXISTS relative_humidity double precision")


def downgrade() -> None:
    op.execute("ALTER TABLE meteo_arsiv DROP COLUMN IF EXISTS relative_humidity")
