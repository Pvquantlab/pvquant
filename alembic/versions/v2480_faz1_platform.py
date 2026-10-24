"""v2.480 — Faz 1 platform kimliği (24.10.2026, docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §3–§6):

- platform_kullanicilar: PVQuant personeli; kiracıya BAĞLI DEĞİL (users.tenant_id NOT NULL ve RLS kalıbı bozulmaz).
  Roller sahip/operator; TOTP alanları; oturum_surumu (Faz 0 ile aynı iptal modeli).
- denetim_izi: kapsam (platform|musteri), aktör, kiracı, eylem, nesne, ayrıntı jsonb, ip. RLS YOK (sistem tablosu;
  platform tümünü, müşteri ileride WHERE tenant_id ile kendi kiracısını okur). Yazım sistem bağlamından.
- tenants.notlar / updated_at: müşteri yönetimi ekranı için.

Revision ID: v2480_faz1_platform
Revises: v2479_faz0_guvenlik
"""
from alembic import op

revision = "v2480_faz1_platform"
down_revision = "v2479_faz0_guvenlik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS platform_kullanicilar(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email TEXT NOT NULL UNIQUE,
      pw_hash TEXT NOT NULL,
      rol TEXT NOT NULL CHECK (rol IN ('sahip','operator')),
      aktif BOOLEAN NOT NULL DEFAULT true,
      totp_secret TEXT,
      totp_aktif BOOLEAN NOT NULL DEFAULT false,
      oturum_surumu INTEGER NOT NULL DEFAULT 0,
      last_login TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE IF NOT EXISTS denetim_izi(
      id BIGSERIAL PRIMARY KEY,
      zaman TIMESTAMPTZ NOT NULL DEFAULT now(),
      kapsam TEXT NOT NULL CHECK (kapsam IN ('platform','musteri')),
      aktor_id UUID,
      aktor_eposta TEXT,
      tenant_id UUID,
      eylem TEXT NOT NULL,
      nesne_tur TEXT,
      nesne_id TEXT,
      ayrinti JSONB NOT NULL DEFAULT '{}'::jsonb,
      ip TEXT);
    CREATE INDEX IF NOT EXISTS ix_denetim_zaman ON denetim_izi(zaman DESC);
    CREATE INDEX IF NOT EXISTS ix_denetim_tenant ON denetim_izi(tenant_id, zaman DESC);
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS notlar TEXT;
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE tenants DROP COLUMN IF EXISTS updated_at;
    ALTER TABLE tenants DROP COLUMN IF EXISTS notlar;
    DROP TABLE IF EXISTS denetim_izi;
    DROP TABLE IF EXISTS platform_kullanicilar;
    """)
