"""v2.513 — KGÜP arşivinde EAK dosyası: kgup_surum.kaynak = 'eak' (TPYS EAK.csv biçiminde indirilen emre amade kapasite dosyası; KGÜP gibi
değiştirilemez sürüm kaydı, kantil 'eak'). Sürüm sayacı ve tekil anahtar (plant_id, teslim_gunu, kaynak, surum) zaten kaynak bazında.

Revision ID: v2513_kgup_surum_eak
Revises: v2503_kgup_surum_kaynak
"""
from alembic import op

revision = "v2513_kgup_surum_eak"
down_revision = "v2503_kgup_surum_kaynak"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE kgup_surum DROP CONSTRAINT IF EXISTS kgup_surum_kaynak_check")
    op.execute("ALTER TABLE kgup_surum ADD CONSTRAINT kgup_surum_kaynak_check CHECK (kaynak IN ('pvquant', 'musteri', 'eak'))")


def downgrade() -> None:
    op.execute("DELETE FROM kgup_surum WHERE kaynak = 'eak'")
    op.execute("ALTER TABLE kgup_surum DROP CONSTRAINT IF EXISTS kgup_surum_kaynak_check")
    op.execute("ALTER TABLE kgup_surum ADD CONSTRAINT kgup_surum_kaynak_check CHECK (kaynak IN ('pvquant', 'musteri'))")
