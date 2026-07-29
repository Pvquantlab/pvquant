"""0005_plants_archived_uq

Revision ID: bcf5dfdf8e6c
Revises: 143eef27edea
Create Date: 2026-07-29

El-migration resmilestirmesi (v2.62): plants.archived + iki benzersizlik.
Uc nesne de canli DB'de psql ile onceden kurulmustu; bu migration onlari
deftere gecirir. IF NOT EXISTS / pg_constraint bekcileri sayesinde:
  - var olan DB'de sessiz gecer (yeniden kurmaya calisip patlamaz),
  - taze DB'de gercekten kurar.
DDL, canli DB'nin (psql d-plants) fotografiyla birebir (29 Tem 2026):
  archived boolean NOT NULL DEFAULT false
  plants_tenant_name_uq        UNIQUE CONSTRAINT (tenant_id, name)
  plants_tenant_lower_name_uq  UNIQUE INDEX (tenant_id, lower(name))
Not (veri sozlugu, DDL degil): scada_hourly.flag yeni deger 'yanlis_yil_2006'
kullanimda (Konya 2006-NREL vakasi, silinmeden etiketlendi).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcf5dfdf8e6c'
down_revision: Union[str, Sequence[str], None] = '143eef27edea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE plants ADD COLUMN IF NOT EXISTS "
        "archived boolean NOT NULL DEFAULT false"
    )
    # ifade indeksi (lower(name)) constraint olamaz — UNIQUE INDEX
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS plants_tenant_lower_name_uq "
        "ON plants (tenant_id, lower(name))"
    )
    # duz ikili ise gercek UNIQUE CONSTRAINT; ADD CONSTRAINT'in
    # IF NOT EXISTS'i yok — pg_constraint bekcisiyle
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'plants_tenant_name_uq'
                  AND conrelid = 'plants'::regclass
            ) THEN
                ALTER TABLE plants ADD CONSTRAINT plants_tenant_name_uq
                    UNIQUE (tenant_id, name);
            END IF;
        END $$
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE plants DROP CONSTRAINT IF EXISTS plants_tenant_name_uq")
    op.execute("DROP INDEX IF EXISTS plants_tenant_lower_name_uq")
    op.execute("ALTER TABLE plants DROP COLUMN IF EXISTS archived")
