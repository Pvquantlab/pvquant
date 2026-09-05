"""v2258_piyasa

Revision ID: v2258_piyasa
Revises: v2254_hijyen
Create Date: 2026-09-06

v2.258 — Dalga 4.14: piyasa_fiyat — EPİAŞ Şeffaflık'tan çekilen saatlik PTF/SMF/sistem yönü. Kamuya açık
piyasa verisi: tenant'sız, RLS'siz (kiracıya özgü hiçbir şey taşımaz). kaynak = 'epias' ya da 'senaryo'.
"""
from alembic import op

revision = "v2258_piyasa"
down_revision = "v2254_hijyen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS piyasa_fiyat ("
        " ts_utc timestamptz PRIMARY KEY,"
        " ptf double precision,"
        " smf double precision,"
        " yon text,"
        " kaynak text NOT NULL DEFAULT 'epias',"
        " guncelleme timestamptz NOT NULL DEFAULT now())"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON piyasa_fiyat TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS piyasa_fiyat")
