"""v2248_skill_olasiliksal

Revision ID: v2248_skill_olasiliksal
Revises: v2247_skill_sfa
Create Date: 2026-09-06

v2.248 — Dalga 1.3: P10–P90 bandının gece sınavı. skill_daily'ye gün+kova başına:
pinball_p10/p50/p90 (kW, kantil kaybı), crps (kW, kantil ızgarasından yaklaşık CRPS),
picp80 (0–1: gerçekleşenin P10–P90 içinde kaldığı saat oranı; hedef 0,80),
kapsama_p10 / kapsama_p90 (0–1: P(gerçek ≤ P10) ve P(gerçek ≤ P90); hedef 0,10 / 0,90 —
reliability diyagramının iki ucu), bant_n (ortalama bant genişliği / kapasite).
Geçmişe backfill yok (saatlik P10/P90 gerektirir); NULL = '—'.
"""
from alembic import op

revision = "v2248_skill_olasiliksal"
down_revision = "v2247_skill_sfa"
branch_labels = None
depends_on = None

KOLONLAR = ("pinball_p10", "pinball_p50", "pinball_p90", "crps", "picp80", "kapsama_p10", "kapsama_p90", "bant_n")


def upgrade() -> None:
    for kol in KOLONLAR:
        op.execute(f"ALTER TABLE skill_daily ADD COLUMN IF NOT EXISTS {kol} DOUBLE PRECISION")


def downgrade() -> None:
    for kol in KOLONLAR:
        op.execute(f"ALTER TABLE skill_daily DROP COLUMN IF EXISTS {kol}")
