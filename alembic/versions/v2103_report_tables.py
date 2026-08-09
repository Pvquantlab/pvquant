"""v2.103 (E.3-a): report_stats (B1+B5 fotograf) + report_log (B6 kimlik/iz).

Kimlik tipleri (UUID/INTEGER) buradan BILINEMEZ — DO blogu plants.id ve
tenants.id tiplerini pg_attribute'tan okuyup tablolari o tiple kurar.
RLS: mevcut tablo kalibi gorulmeden politika YAZILMADI (acik madde —
ornek bir tenant-tablosu migration'i gorunce eslenecek).
"""
from alembic import op

revision = "v2103_report_tables"
down_revision = "e9c74a2d0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    DO $$
    DECLARE tp TEXT; tt TEXT;
    BEGIN
      SELECT format_type(a.atttypid, a.atttypmod) INTO tp
        FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
       WHERE c.relname = 'plants' AND a.attname = 'id';
      SELECT format_type(a.atttypid, a.atttypmod) INTO tt
        FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
       WHERE c.relname = 'tenants' AND a.attname = 'id';
      EXECUTE format(
        'CREATE TABLE IF NOT EXISTS report_stats('
        ' tenant_id %s NOT NULL,'
        ' plant_id  %s NOT NULL,'
        ' key       TEXT NOT NULL,'
        ' value_json JSONB NOT NULL,'
        ' updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),'
        ' PRIMARY KEY(plant_id, key))', tt, tp);
      EXECUTE format(
        'CREATE TABLE IF NOT EXISTS report_log('
        ' id BIGSERIAL PRIMARY KEY,'
        ' tenant_id %s NOT NULL,'
        ' plant_id  %s NOT NULL,'
        ' mode TEXT NOT NULL,'
        ' created_at TIMESTAMPTZ NOT NULL DEFAULT now())', tt, tp);
    END $$;
    CREATE INDEX IF NOT EXISTS ix_report_log_plant
      ON report_log(plant_id, created_at DESC);

    -- Uygulama rolu yetkileri (skill_daily deseni: pvq_app INSERT,SELECT,UPDATE).
    -- Rol yoksa (baska ortam) sessiz gec — kosullu DO blogu.
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pvq_app') THEN
        GRANT INSERT, SELECT, UPDATE ON report_stats TO pvq_app;
        GRANT INSERT, SELECT         ON report_log   TO pvq_app;
        GRANT USAGE, SELECT ON SEQUENCE report_log_id_seq TO pvq_app;
      END IF;
    END $$;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS report_stats; DROP TABLE IF EXISTS report_log;")
