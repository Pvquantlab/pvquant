"""0007_iklim_yil

Revision ID: d4e52a0c0007
Revises: c3d41f9b0006
Create Date: 2026-07-31

v2.78-A — 20 yil serpilisinin HAZIR-SONUC katmani (KUTU-2 sayfasi ay basina
yillarin ham noktalarini cizer; kuantil tablosu tek basina serpili veremez).
Kalip 0006 ile ayni (skill_daily fotografi); GRANT dersi bu kez dogumda:
pvq_app=arw (0006'daki izin vakasi tekrarlanmaz).
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd4e52a0c0007'
down_revision: Union[str, Sequence[str], None] = 'c3d41f9b0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS iklim_yil ("
        " tenant_id uuid NOT NULL,"
        " plant_id uuid NOT NULL REFERENCES plants(id),"
        " yil integer NOT NULL,"
        " ay smallint NOT NULL CHECK (ay BETWEEN 1 AND 12),"
        " ghi_kwh_m2 double precision,"
        " hesap_zamani timestamptz NOT NULL DEFAULT now(),"
        " PRIMARY KEY (plant_id, yil, ay))"
    )
    op.execute("ALTER TABLE iklim_yil ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE iklim_yil FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_iklim_yil ON iklim_yil")
    op.execute(
        "CREATE POLICY p_iklim_yil ON iklim_yil"
        " USING (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
        " WITH CHECK"
        " (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON iklim_yil TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iklim_yil")
