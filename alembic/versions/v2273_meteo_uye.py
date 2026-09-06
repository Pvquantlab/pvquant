"""v2273_meteo_uye

Revision ID: v2273_meteo_uye
Revises: v2268_meteo_arsiv
Create Date: 2026-09-06

v2.273 — Dalga 2 (★): ensemble üye arşivi (GEFS 0.25°, 31 üye). Tenant'sız kamu verisi; 45 gün tutulur.
"""
from alembic import op

revision = "v2273_meteo_uye"
down_revision = "v2268_meteo_arsiv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS meteo_uye ("
        " kaynak text NOT NULL, kosu_zamani timestamptz NOT NULL, lat double precision NOT NULL, lon double precision NOT NULL,"
        " uye integer NOT NULL, ts_utc timestamptz NOT NULL, ghi double precision, temp_air double precision,"
        " wind_speed_10m double precision, cloud_cover double precision,"
        " PRIMARY KEY (kaynak, kosu_zamani, lat, lon, uye, ts_utc))")
    op.execute("CREATE INDEX IF NOT EXISTS meteo_uye_nokta ON meteo_uye(lat, lon, kosu_zamani)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON meteo_uye TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS meteo_uye")
