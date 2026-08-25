"""v2205_gunluk_beklenti

Revision ID: v2205_gunluk_beklenti
Revises: v2204_bant_ic
Create Date: 2026-08-26

v2.205 — GUNLUK BEKLENTI ARSIVI (forecast_daily): her santral-yerel gun
icin, GUN BASLAMADAN verilmis en taze kosunun kWh toplamlari. Aylik
'gerceklesen vs beklenti' kiyasinin kalici hakem verisi (gece karnesi
felsefesi: kiyas, gunden ONCE soylenmis sozle yapilir).

Uslup iklim_beklenti (c3d41f9b0006) fotografinin kopyasi: PK(plant_id,gun),
FK plants, FORCED RLS + tek policy, GRANT S/I/U (DELETE bilerek yok —
'gecmis sonuc degistirilmez; yenisi eklenir'). Idempotent.
"""
from alembic import op

revision = "v2205_gunluk_beklenti"
down_revision = "v2204_bant_ic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS forecast_daily ("
        " tenant_id uuid NOT NULL,"
        " plant_id uuid NOT NULL REFERENCES plants(id),"
        " gun date NOT NULL,"
        " p50_kwh double precision NOT NULL,"
        " p10_kwh double precision,"
        " p90_kwh double precision,"
        " run_id uuid NOT NULL REFERENCES forecast_runs(id),"
        " saat_sayisi integer NOT NULL,"
        " hesap_zamani timestamptz NOT NULL DEFAULT now(),"
        " PRIMARY KEY (plant_id, gun))"
    )
    op.execute("ALTER TABLE forecast_daily ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE forecast_daily FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_forecast_daily ON forecast_daily")
    op.execute(
        "CREATE POLICY p_forecast_daily ON forecast_daily"
        " USING (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
        " WITH CHECK"
        " (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON forecast_daily TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forecast_daily")
