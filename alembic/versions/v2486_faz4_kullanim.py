"""v2.486 — Faz 4 kullanım sayaçları + paylaşımlı hız penceresi (25.10.2026, docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §6
«Kullanım + sınırlayıcılar»):

- kullanim_sayac: kiracı × gün × tür günlük sayaç (UPSERT). Yalnız mevcut tablolarda izi olmayan türler yazılır (dis_api,
  webhook, webhook_hata); rapor/koşu/SCADA/yükleme sayıları report_log, forecast_runs, scada_hourly, ingestion_batches'ten
  TÜRETİLİR — tahmin/rapor/SCADA işleme koduna kanca yoktur. RLS YOK (sistem tablosu; platform okur, yazım sistem bağlamından).
- hiz_pencere: 60 sn'lik PAYLAŞIMLI sayaç (anahtar × pencere). Süreç içi token bucket 4 uvicorn işçisinde anahtar başına
  rpm'i fiilen 4× yapıyordu; pencere tek tabloda tüm işçiler için sayar. Eski pencereler artış sorgusunda silinir, cron yok.

Revision ID: v2486_faz4_kullanim
Revises: v2485_faz3_sistem
"""
from alembic import op

revision = "v2486_faz4_kullanim"
down_revision = "v2485_faz3_sistem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS kullanim_sayac(
      tenant_id UUID NOT NULL,
      gun DATE NOT NULL,
      tur TEXT NOT NULL,
      adet BIGINT NOT NULL DEFAULT 0,
      guncelleme TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (tenant_id, gun, tur));
    CREATE INDEX IF NOT EXISTS ix_kullanim_gun ON kullanim_sayac(gun DESC);
    CREATE TABLE IF NOT EXISTS hiz_pencere(
      anahtar TEXT NOT NULL,
      pencere TIMESTAMPTZ NOT NULL,
      adet INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (anahtar, pencere));
    GRANT SELECT, INSERT, UPDATE, DELETE ON kullanim_sayac TO pvq_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON hiz_pencere TO pvq_app;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hiz_pencere; DROP TABLE IF EXISTS kullanim_sayac;")
