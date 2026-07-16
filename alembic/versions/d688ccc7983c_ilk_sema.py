"""ilk_sema

Revision ID: d688ccc7983c
Revises:
Create Date: 2026-07-16
"""
from alembic import op

revision = "d688ccc7983c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    -- BLOK A: uzanti + kimlik tablolari (RLS'siz olanlar)
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    CREATE TABLE tenants(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name TEXT NOT NULL, plan TEXT NOT NULL DEFAULT 'pilot',
      status TEXT NOT NULL DEFAULT 'active',
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE users(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      email TEXT NOT NULL UNIQUE, pw_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('viewer','editor','admin')),
      last_login TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    """)

    op.execute("""
    -- BLOK B: is tablolari (hepsinde tenant_id)
    CREATE TABLE plant_groups(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id), name TEXT NOT NULL);
    CREATE TABLE user_groups(
      user_id UUID REFERENCES users(id), group_id UUID REFERENCES plant_groups(id),
      PRIMARY KEY(user_id, group_id));
    CREATE TABLE plants(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      group_id UUID REFERENCES plant_groups(id),
      name TEXT NOT NULL, lat DOUBLE PRECISION NOT NULL,
      lon DOUBLE PRECISION NOT NULL, tz TEXT NOT NULL,
      capacity_kwp DOUBLE PRECISION NOT NULL,
      tilt DOUBLE PRECISION, azimuth DOUBLE PRECISION,
      panel_tech TEXT DEFAULT 'bifacial', params_json JSONB DEFAULT '{}',
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE ingestion_batches(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),
      filename TEXT, format_json JSONB, mapping_json JSONB,
      transform_json JSONB, quality_json JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE scada_hourly(
      tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),
      ts_utc TIMESTAMPTZ NOT NULL,
      power_kw DOUBLE PRECISION, energy_kwh DOUBLE PRECISION,
      poa_wm2 DOUBLE PRECISION, t_air DOUBLE PRECISION,
      t_module DOUBLE PRECISION, wind_ms DOUBLE PRECISION,
      flag TEXT NOT NULL DEFAULT 'valid', batch_id UUID,
      PRIMARY KEY(plant_id, ts_utc));
    SELECT create_hypertable('scada_hourly','ts_utc',
      partitioning_column=>'plant_id', number_partitions=>8);
    CREATE TABLE calibrations(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),
      mode TEXT NOT NULL, params_json JSONB NOT NULL,
      quality_json JSONB, gate_json JSONB, n_valid_hours INT,
      active BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE ml_models(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),
      artifact_path TEXT NOT NULL, training_report_json JSONB,
      active BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE forecast_runs(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),
      run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      mode TEXT NOT NULL, model TEXT NOT NULL, meteo_source TEXT);
    CREATE TABLE forecast_values(
      tenant_id UUID NOT NULL, run_id UUID NOT NULL REFERENCES forecast_runs(id),
      plant_id UUID NOT NULL, ts_utc TIMESTAMPTZ NOT NULL,
      p50_kw DOUBLE PRECISION NOT NULL, p10_kw DOUBLE PRECISION,
      p90_kw DOUBLE PRECISION, physics_kw DOUBLE PRECISION,
      ml_kw DOUBLE PRECISION,
      PRIMARY KEY(run_id, plant_id, ts_utc));
    SELECT create_hypertable('forecast_values','ts_utc',
      partitioning_column=>'plant_id', number_partitions=>8);
    CREATE INDEX ix_fv_plant_ts ON forecast_values(plant_id, ts_utc);
    CREATE TABLE skill_daily(
      tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),
      date DATE NOT NULL, horizon_bucket TEXT NOT NULL,
      mape DOUBLE PRECISION, rmse DOUBLE PRECISION,
      skill_vs_naive DOUBLE PRECISION,
      PRIMARY KEY(plant_id, date, horizon_bucket));
    CREATE TABLE alerts(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL, plant_id UUID REFERENCES plants(id),
      rule TEXT NOT NULL, severity TEXT NOT NULL DEFAULT 'warning',
      message TEXT NOT NULL, acked_by UUID,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE jobs_log(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      job TEXT NOT NULL, tenant_id UUID, plant_id UUID,
      started TIMESTAMPTZ NOT NULL, finished TIMESTAMPTZ,
      status TEXT NOT NULL, detail TEXT);
    CREATE TABLE api_keys(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      key_hash TEXT NOT NULL, label TEXT,
      revoked BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    """)

    op.execute("""
    -- BLOK C: RLS -- her is tablosuna ayni kalip
    CREATE ROLE pvq_app NOLOGIN;
    GRANT USAGE ON SCHEMA public TO pvq_app;
    GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA public TO pvq_app;
    DO $$ DECLARE t TEXT;
    BEGIN
      FOREACH t IN ARRAY ARRAY['plant_groups','plants','ingestion_batches',
        'scada_hourly','calibrations','ml_models','forecast_runs',
        'forecast_values','skill_daily','alerts','api_keys']
      LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format(
          'CREATE POLICY p_%s ON %I USING (tenant_id = current_setting(''app.tenant_id'')::uuid) '
          'WITH CHECK (tenant_id = current_setting(''app.tenant_id'')::uuid)', t, t);
      END LOOP;
    END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_keys, jobs_log, alerts, skill_daily, "
               "forecast_values, forecast_runs, ml_models, calibrations, "
               "scada_hourly, ingestion_batches, plants, user_groups, "
               "plant_groups, users, tenants CASCADE;")
    op.execute("DROP ROLE IF EXISTS pvq_app;")
