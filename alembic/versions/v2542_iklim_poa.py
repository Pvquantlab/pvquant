"""v2.542 (P8b-2 kalanı; IH-104/IH-099) — iklim beklentisine düzlem-içi (POA) ışınım P10/P50/P90: aynı PVGIS-SARAH3 saatlik arşivinin
pvlib ile santralın eğim/azimutuna düzlem dönüşümü (Hay-Davies; albedo 0,2). Düzlem-içi ölçen sensörün ışınım endeksi (ölçülen / P50) artık
aynı düzlemde kıyaslanır; aylık toplam üzerinden dönüşüm yapılmaz. Hesap aylık iklim işinde; eğim/azimut girilmemiş santralda sütunlar boş kalır.

Revision ID: v2542_iklim_poa
Revises: v2541_olay
"""
from alembic import op

revision = "v2542_iklim_poa"
down_revision = "v2541_olay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for k in ("poa_p10_kwh_m2", "poa_p50_kwh_m2", "poa_p90_kwh_m2", "poa_egim", "poa_azimut"):
        op.execute(f"ALTER TABLE iklim_beklenti ADD COLUMN IF NOT EXISTS {k} DOUBLE PRECISION")


def downgrade() -> None:
    for k in ("poa_azimut", "poa_egim", "poa_p90_kwh_m2", "poa_p50_kwh_m2", "poa_p10_kwh_m2"):
        op.execute(f"ALTER TABLE iklim_beklenti DROP COLUMN IF EXISTS {k}")
