"""v2204_bant_ic

Revision ID: v2204_bant_ic
Revises: v2163_aktif_tekillik
Create Date: 2026-08-26

v2.204 — saatlik IC bant (P25-P75) kolonlari. NULLABLE: eski kosular ve
Mod A/B (fizik) durustce bantsiz kalir; UI kolon doluysa cizer. Uslup
e9c74a2d0008 emsali: idempotent ADD COLUMN, veri dokunusu yok (eski
satirlara deger UYDURULMAZ — dogru yol yeniden kalibrasyon, v2.178 ilkesi).
"""
from alembic import op

revision = "v2204_bant_ic"
down_revision = "v2163_aktif_tekillik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE forecast_values"
        " ADD COLUMN IF NOT EXISTS p25_kw double precision"
    )
    op.execute(
        "ALTER TABLE forecast_values"
        " ADD COLUMN IF NOT EXISTS p75_kw double precision"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE forecast_values DROP COLUMN IF EXISTS p25_kw")
    op.execute("ALTER TABLE forecast_values DROP COLUMN IF EXISTS p75_kw")
