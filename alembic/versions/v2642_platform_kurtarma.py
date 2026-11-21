"""v2642 — platform sahibi/operatörü için 2FA KURTARMA KODLARI (Faz 0 C3-a / A3, 21.11.2026; rapor §22-R).

Müşteri `kurtarma_kodlari` kalıbının platform kopyası, FK hedefi farklı olduğundan AYRI tablo. Kod: 128 bit rastgele (base32 26 kar.),
saklanan yalnız SHA-256 özeti (geri çözülmez; 128 bit sır için yavaş özet gereksiz); tek kullanım atomik UPDATE; `grup_id` aynı üretim turu
(rotasyonda eski grup silinir). RLS yok (platform tablosu). Geri dönüş: tablo düşer; kod yolu tablo yokken TOTP ile çalışmaya devam eder.

Revision ID: v2642_platform_kurtarma
Revises: v2609_abonelik
"""
from alembic import op

revision = "v2642_platform_kurtarma"
down_revision = "v2609_abonelik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS platform_kurtarma_kodlari(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      platform_user_id UUID NOT NULL REFERENCES platform_kullanicilar(id) ON DELETE CASCADE,
      kod_hash TEXT NOT NULL UNIQUE,
      grup_id UUID NOT NULL,
      kullanildi_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE INDEX IF NOT EXISTS ix_platform_kurtarma_user ON platform_kurtarma_kodlari(platform_user_id);
    """)
    for rol in ("pvq_app", "pvq_api"):
        op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{rol}') THEN "
                   f"GRANT SELECT, INSERT, UPDATE, DELETE ON platform_kurtarma_kodlari TO {rol}; END IF; END $$;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS platform_kurtarma_kodlari")
