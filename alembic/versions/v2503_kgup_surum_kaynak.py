"""v2.503 — KGÜP arşivinde kaynak ayrımı (F-06 müşteri KGÜP içe alma): kgup_surum.kaynak = 'pvquant' (PVQuant'ın ürettiği/indirilen dosya) |
'musteri' (müşterinin TPYS'ye bildirdiğini beyan ettiği dosya, panelden yüklenir). Sürüm sayacı kaynak bazında; tekil anahtar genişler.
Müşteri dosyası da değiştirilemez kayıttır (pvq_app UPDATE/DELETE yok). Kıyas (öneri ↔ bildirilen) okuma tarafında.

Revision ID: v2503_kgup_surum_kaynak
Revises: v2502_kgup_surum
"""
from alembic import op

revision = "v2503_kgup_surum_kaynak"
down_revision = "v2502_kgup_surum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE kgup_surum ADD COLUMN IF NOT EXISTS kaynak TEXT NOT NULL DEFAULT 'pvquant'")
    op.execute("ALTER TABLE kgup_surum DROP CONSTRAINT IF EXISTS kgup_surum_kaynak_check")
    op.execute("ALTER TABLE kgup_surum ADD CONSTRAINT kgup_surum_kaynak_check CHECK (kaynak IN ('pvquant', 'musteri'))")
    op.execute("ALTER TABLE kgup_surum DROP CONSTRAINT IF EXISTS kgup_surum_plant_id_teslim_gunu_surum_key")
    op.execute("ALTER TABLE kgup_surum ADD CONSTRAINT kgup_surum_plant_gun_kaynak_surum_key UNIQUE (plant_id, teslim_gunu, kaynak, surum)")


def downgrade() -> None:
    op.execute("ALTER TABLE kgup_surum DROP CONSTRAINT IF EXISTS kgup_surum_plant_gun_kaynak_surum_key")
    op.execute("DELETE FROM kgup_surum WHERE kaynak <> 'pvquant'")
    op.execute("ALTER TABLE kgup_surum ADD CONSTRAINT kgup_surum_plant_id_teslim_gunu_surum_key UNIQUE (plant_id, teslim_gunu, surum)")
    op.execute("ALTER TABLE kgup_surum DROP COLUMN IF EXISTS kaynak")
