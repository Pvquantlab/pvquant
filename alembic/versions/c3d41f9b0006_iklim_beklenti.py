"""0006_iklim_beklenti

Revision ID: c3d41f9b0006
Revises: bcf5dfdf8e6c
Create Date: 2026-07-31

v2.77-B — aylik iklim beklentisi HAZIR-SONUC tablosu (KUTU-2: zamanlayici
hesaplar, ekran okur). DDL uslubu skill_daily fotografinin kopyasi
(31 Tem 2026, \\d skill_daily + pg_policies):
  - PK (plant_id, ay), FK plants(id), tenant_id uuid NOT NULL
  - FORCED row security + p_iklim_beklenti (USING/WITH CHECK ayni kalip)
Idempotent: dolu DB'de sessiz gecer, taze DB'de kurar.
Birim adda (capacity_kwp emsali): ghi_*_kwh_m2.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c3d41f9b0006'
down_revision: Union[str, Sequence[str], None] = 'bcf5dfdf8e6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS iklim_beklenti ("
        " tenant_id uuid NOT NULL,"
        " plant_id uuid NOT NULL REFERENCES plants(id),"
        " ay smallint NOT NULL CHECK (ay BETWEEN 1 AND 12),"
        " ghi_p10_kwh_m2 double precision,"
        " ghi_p50_kwh_m2 double precision,"
        " ghi_p90_kwh_m2 double precision,"
        " yil_sayisi integer,"
        " hesap_zamani timestamptz NOT NULL DEFAULT now(),"
        " PRIMARY KEY (plant_id, ay))"
    )
    op.execute("ALTER TABLE iklim_beklenti ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE iklim_beklenti FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_iklim_beklenti ON iklim_beklenti")
    op.execute(
        "CREATE POLICY p_iklim_beklenti ON iklim_beklenti"
        " USING (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
        " WITH CHECK"
        " (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
    )
    # canli durusma dersi: uygulama SET LOCAL ROLE pvq_app ile kosar —
    # GRANT'siz tablo ona kapali. Set skill_daily fotografinin kopyasi
    # (pvq_app=arw): SELECT, INSERT, UPDATE; DELETE bilerek yok.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON iklim_beklenti TO pvq_app"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iklim_beklenti")
