"""v2252_konformal

Revision ID: v2252_konformal
Revises: v2248_skill_olasiliksal
Create Date: 2026-09-06

v2.252 — Dalga 2.7: konformal (CQR) bant kalibrasyonu. (1) forecast_values'a p10_ham_kw/p90_ham_kw:
modelin HAM kantilleri saklanır; p10_kw/p90_kw servis edilen (düzeltilmiş) banttır — hakem (gece bant
sınavı) servis edileni, öğrenme (q̂) hamı okur, döngü kendi kuyruğunu kovalamaz. (2) konformal_ayar:
santral başına q̂ sözlüğü (saat-of-day → kW), alpha, n, pencere, hesap zamanı; RLS forecast_daily kalıbı.
"""
from alembic import op

revision = "v2252_konformal"
down_revision = "v2248_skill_olasiliksal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE forecast_values ADD COLUMN IF NOT EXISTS p10_ham_kw DOUBLE PRECISION")
    op.execute("ALTER TABLE forecast_values ADD COLUMN IF NOT EXISTS p90_ham_kw DOUBLE PRECISION")
    op.execute(
        "CREATE TABLE IF NOT EXISTS konformal_ayar ("
        " tenant_id uuid NOT NULL,"
        " plant_id uuid NOT NULL REFERENCES plants(id),"
        " alpha double precision NOT NULL,"
        " grup text NOT NULL,"
        " q_hat_json jsonb NOT NULL,"
        " n integer NOT NULL,"
        " pencere_gun integer NOT NULL,"
        " aktif boolean NOT NULL DEFAULT true,"
        " hesap_zamani timestamptz NOT NULL DEFAULT now(),"
        " PRIMARY KEY (plant_id))"
    )
    op.execute("ALTER TABLE konformal_ayar ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE konformal_ayar FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_konformal_ayar ON konformal_ayar")
    op.execute(
        "CREATE POLICY p_konformal_ayar ON konformal_ayar"
        " USING (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
        " WITH CHECK (tenant_id = (current_setting('app.tenant_id'::text))::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON konformal_ayar TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS konformal_ayar")
    op.execute("ALTER TABLE forecast_values DROP COLUMN IF EXISTS p10_ham_kw")
    op.execute("ALTER TABLE forecast_values DROP COLUMN IF EXISTS p90_ham_kw")
