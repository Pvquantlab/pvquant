"""v2268_meteo_arsiv

Revision ID: v2268_meteo_arsiv
Revises: v2265_alarm_okundu
Create Date: 2026-09-06

v2.268 — Dalga 0: açık NWP koşu arşivi (nokta serileri). Kamuya açık meteoroloji: tenant'sız, RLS'siz
(piyasa_fiyat kalıbı). Anahtar: kaynak + koşu zamanı + nokta (3 ondalık) + saat.
"""
from alembic import op

revision = "v2268_meteo_arsiv"
down_revision = "v2265_alarm_okundu"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS meteo_arsiv ("
        " kaynak text NOT NULL, kosu_zamani timestamptz NOT NULL,"
        " lat double precision NOT NULL, lon double precision NOT NULL, ts_utc timestamptz NOT NULL,"
        " ghi double precision, dni double precision, dhi double precision, temp_air double precision,"
        " wind_speed_10m double precision, cloud_cover double precision, precipitation double precision,"
        " PRIMARY KEY (kaynak, kosu_zamani, lat, lon, ts_utc))")
    op.execute("CREATE INDEX IF NOT EXISTS meteo_arsiv_nokta_ts ON meteo_arsiv(lat, lon, ts_utc)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON meteo_arsiv TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS meteo_arsiv")
