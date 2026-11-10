"""v2.570 (Faz 0 onay paketi 2, GV-01/GV-02) — TOTP ve webhook sırları için zarf sütunları + TOTP son kabul edilen zaman adımı.

users / platform_kullanicilar: totp_zarf JSONB (kasa zarfı; düz `totp_secret` geçiş döneminde kalır, dönüşümden sonra NULL), totp_son_adim BIGINT
(tekrar koruması). webhooks: secret_zarf JSONB (düz `secret` geçiş döneminde kalır). Sütun düşürme yok; dönüşüm `scripts/sirlari_kasaya_tasi.py`
ile DB sahibiyle, geri alma `--geri`. Downgrade yalnız yeni sütunları düşürür — önce `--geri` koşulmalı.

Revision ID: v2570_sir_kasasi
Revises: v2564_bulut_oauth
"""
from alembic import op

revision = "v2570_sir_kasasi"
down_revision = "v2564_bulut_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for tablo in ("users", "platform_kullanicilar"):
        op.execute(f"ALTER TABLE {tablo} ADD COLUMN IF NOT EXISTS totp_zarf JSONB")
        op.execute(f"ALTER TABLE {tablo} ADD COLUMN IF NOT EXISTS totp_son_adim BIGINT")
    op.execute("ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS secret_zarf JSONB")
    op.execute("ALTER TABLE webhooks ALTER COLUMN secret DROP NOT NULL")   # zarf doluyken düz sütun NULL (prova: NOT NULL kısıtı dönüşümü ve yeni webhook oluşturmayı kırıyordu)


def downgrade() -> None:
    # önce `scripts/sirlari_kasaya_tasi.py --geri` koşulmalı; düz sütun dolunca NOT NULL geri gelir
    op.execute("UPDATE webhooks SET secret='' WHERE secret IS NULL")
    op.execute("ALTER TABLE webhooks ALTER COLUMN secret SET NOT NULL")
    op.execute("ALTER TABLE webhooks DROP COLUMN IF EXISTS secret_zarf")
    for tablo in ("users", "platform_kullanicilar"):
        op.execute(f"ALTER TABLE {tablo} DROP COLUMN IF EXISTS totp_son_adim")
        op.execute(f"ALTER TABLE {tablo} DROP COLUMN IF EXISTS totp_zarf")
