"""v2.485 — Faz 3 sistem izleme (25.10.2026, docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §6 «Sistem izleme»):

- sistem_nabiz: bileşen başına TEK satır (worker her 5 dk UPSERT eder). jobs_log'a yazılmaz: o tablo müşterinin «gece
  işleri» listesine tenant'sız satırları da taşır, nabız orada görünürdü. RLS YOK (sistem tablosu; yalnız platform okur).
  Mevcut tablolar, politikalar ve müşteri sözleşmeleri DEĞİŞMEZ; bu geçiş yalnız EKLER.

Revision ID: v2485_faz3_sistem
Revises: v2480_faz1_platform
"""
from alembic import op

revision = "v2485_faz3_sistem"
down_revision = "v2480_faz1_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS sistem_nabiz(
      bilesen TEXT PRIMARY KEY,
      zaman TIMESTAMPTZ NOT NULL DEFAULT now(),
      ayrinti JSONB NOT NULL DEFAULT '{}'::jsonb);
    GRANT SELECT, INSERT, UPDATE ON sistem_nabiz TO pvq_app;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sistem_nabiz")
