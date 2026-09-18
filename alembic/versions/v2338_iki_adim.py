"""v2338_iki_adim

Revision ID: v2338_iki_adim
Revises: v2335_parola_sifirlama
Create Date: 2026-09-18

v2.338 — TOTP iki adımlı doğrulama. users.totp_secret (base32; NULL = 2FA yok)
ve totp_aktif (kayıt tamamlanınca true). Kurtarma kodları ayrı tabloda ve
YALNIZ özetiyle saklanır (parola kalıbı); telefon kaybında tek kullanımlık
giriş sağlar. TOTP sırrı doğrulama için geri okunabilir olmalıdır, bu yüzden
özetlenemez — kısıtlı sütunda düz tutulur (alan şifrelemesi ileri iş, koddaki
mevcut güvenlik düzeyiyle tutarlı; sır yalnız kayıt anında istemciye döner,
sonra hiçbir uç geri vermez).
"""
from alembic import op

revision = "v2338_iki_adim"
down_revision = "v2335_parola_sifirlama"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE users ADD COLUMN totp_secret TEXT;
    ALTER TABLE users ADD COLUMN totp_aktif BOOLEAN NOT NULL DEFAULT false;
    CREATE TABLE kurtarma_kodlari(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      kod_hash TEXT NOT NULL,
      kullanildi_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE INDEX ix_kurtarma_user ON kurtarma_kodlari(user_id);
    GRANT SELECT, INSERT, UPDATE, DELETE ON kurtarma_kodlari TO pvq_app;
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE kurtarma_kodlari;
    ALTER TABLE users DROP COLUMN totp_aktif;
    ALTER TABLE users DROP COLUMN totp_secret;
    """)
