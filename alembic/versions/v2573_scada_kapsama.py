"""v2.573 (Faz 1 paketi F1-B, Stage 3 ölçüm verisi) — saat başına ölçüm kapsaması.

scada_hourly.kapsama_dk SMALLINT NULL: saatin kaç dakikası ölçümle kaplı (15 dk kaynakta 4 örnek = 60; 1 örnek = 15). Dosya yolunda
transform adımı hesaplar; canlı örnekleme tam saatleri 60 yazar; eski satırlar ve EPİAŞ/bulut yolları NULL = bilinmiyor (uydurulmaz).
45 dakikanın altındaki saat yükleme doğrulamasında 'partial_hour' bayrağı alır (geçerli üretim serisine girmez). Veri silinmez.

Revision ID: v2573_scada_kapsama
Revises: v2572_kosu_kunyesi
"""
from alembic import op

revision = "v2573_scada_kapsama"
down_revision = "v2572_kosu_kunyesi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE scada_hourly ADD COLUMN IF NOT EXISTS kapsama_dk SMALLINT")


def downgrade() -> None:
    op.execute("ALTER TABLE scada_hourly DROP COLUMN IF EXISTS kapsama_dk")
