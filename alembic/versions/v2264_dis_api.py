"""v2264_dis_api

Revision ID: v2264_dis_api
Revises: v2258_piyasa
Create Date: 2026-09-06

v2.264 — Dalga 5.16: dışa dönük API anahtarları + webhook'lar.
api_keys: prefix (aramada kullanılır, sır değildir), scopes (kapsam listesi), expires_at, rpm (dakikada istek),
last_used_at. Anahtarın kendisi ASLA saklanmaz; yalnız sha256 özeti (key_hash, ilk şemadan).
webhooks: kiracının olay alıcıları; secret HMAC imzası için sunucuda tutulur (alıcı doğrulasın diye), yalnız
oluşturulurken bir kez gösterilir. RLS ilk şemanın kalıbıyla.
"""
from alembic import op

revision = "v2264_dis_api"
down_revision = "v2258_piyasa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS prefix text")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS scopes jsonb NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS expires_at timestamptz")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS rpm integer NOT NULL DEFAULT 120")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS last_used_at timestamptz")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS api_keys_prefix_ux ON api_keys(prefix) WHERE prefix IS NOT NULL")
    op.execute(
        "CREATE TABLE IF NOT EXISTS webhooks ("
        " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
        " tenant_id uuid NOT NULL,"
        " plant_id uuid REFERENCES plants(id),"
        " url text NOT NULL,"
        " secret text NOT NULL,"
        " events jsonb NOT NULL DEFAULT '[\"tahmin.yeni\"]'::jsonb,"
        " active boolean NOT NULL DEFAULT true,"
        " created_at timestamptz NOT NULL DEFAULT now(),"
        " last_sent_at timestamptz,"
        " last_status integer,"
        " fail_count integer NOT NULL DEFAULT 0)")
    op.execute("ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE webhooks FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_webhooks ON webhooks")
    op.execute("CREATE POLICY p_webhooks ON webhooks USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON webhooks TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhooks")
    op.execute("DROP INDEX IF EXISTS api_keys_prefix_ux")
    for c in ("prefix", "scopes", "expires_at", "rpm", "last_used_at"):
        op.execute(f"ALTER TABLE api_keys DROP COLUMN IF EXISTS {c}")
