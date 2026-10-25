"""v2.493 — Faz 6 kuruluş ayarları (26.10.2026, docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §6 satır 5; denetim O7):

- tenants.yonetici_2fa_zorunlu BOOLEAN NOT NULL DEFAULT false — kiracı yöneticisi kendisi açar (isteğe bağlı politika). Açıkken 2FA'sız
  yönetici hesabı girişten sonra yalnız kurulum uçlarını görür (deps.gecerli_kullanici). Editör/izleyici etkilenmez. Varsayılan kapalı:
  mevcut hiçbir kiracının davranışı değişmez.

Revision ID: v2493_faz6_kurulus
Revises: v2492_faz5_planlar
"""
from alembic import op

revision = "v2493_faz6_kurulus"
down_revision = "v2492_faz5_planlar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS yonetici_2fa_zorunlu BOOLEAN NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS yonetici_2fa_zorunlu")
