"""v2247_skill_sfa

Revision ID: v2247_skill_sfa
Revises: v2205_gunluk_beklenti
Create Date: 2026-09-06

v2.247 — Dalga 1.2: karneye Solar Forecast Arbiter sözlüğü. skill_daily'ye kapasiteye
normalize üç kolon: nmae, nrmse, nmbe (yüzde, payda plants.capacity_kwp). Mevcut WMAPE
(mape) ve naif/skill KALIR — yeni kolonlar yanına gelir. nrmse geçmiş satırlar için aynı
özdeşlikle backfill edilir (rmse zaten saklıydı: nrmse = rmse/capacity*100 — türetme
değil, birim çevirisi); nmae/nmbe saatlik veri istediğinden geçmişe yazılmaz (NULL = '—').
"""
from alembic import op

revision = "v2247_skill_sfa"
down_revision = "v2205_gunluk_beklenti"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for kol in ("nmae", "nrmse", "nmbe"):
        op.execute(f"ALTER TABLE skill_daily ADD COLUMN IF NOT EXISTS {kol} DOUBLE PRECISION")
    op.execute(
        "UPDATE skill_daily s SET nrmse = s.rmse / p.capacity_kwp * 100.0 "
        "FROM plants p WHERE p.id = s.plant_id AND s.nrmse IS NULL "
        "AND s.rmse IS NOT NULL AND p.capacity_kwp > 0")


def downgrade() -> None:
    for kol in ("nmae", "nrmse", "nmbe"):
        op.execute(f"ALTER TABLE skill_daily DROP COLUMN IF EXISTS {kol}")
