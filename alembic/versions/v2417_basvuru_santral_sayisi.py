"""v2417_basvuru_santral_sayisi

Revision ID: v2417_basvuru_santral_sayisi
Revises: v2338_iki_adim
Create Date: 2026-10-09

v2.417 — teklif netliği: SSS «santral sayısına göre belirlenir» derken formda
bu alan yoktu; teklifin ikinci parametresi (kurulu güçle birlikte) artık
başvuruda isteğe bağlı toplanır. SMALLINT yeter (1..500 servis doğrulaması).
"""
from alembic import op

revision = "v2417_basvuru_santral_sayisi"
down_revision = "v2338_iki_adim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE vitrin_basvurulari ADD COLUMN santral_sayisi SMALLINT")


def downgrade() -> None:
    op.execute("ALTER TABLE vitrin_basvurulari DROP COLUMN santral_sayisi")
