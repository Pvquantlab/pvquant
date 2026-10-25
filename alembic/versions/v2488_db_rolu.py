"""v2.488 — Uygulama DB rolü süper kullanıcıdan iner (25.10.2026, docs/YONETIM-PANELI-DENETIM-2026-10-25.md Y1;
yol haritası Faz 1 kalemi «DB rolü süper kullanıcıdan indirme»).

- pvq_api: LOGIN, NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION, BYPASSRLS. Uygulama (api + worker) bu rolle bağlanır.
  BYPASSRLS bilinçli: sistem/platform bağlamları (giriş, worker, platform okumaları) bugün süper kullanıcıyla RLS dışı çalışıyor;
  davranış aynı kalır, yalnız süper kullanıcı yetkileri (COPY PROGRAM, dosya okuma, rol/DB yönetimi) gider. Kiracı yolu değişmez:
  tenant_baglami `SET LOCAL ROLE pvq_app` → RLS devrede (pvq_app BYPASSRLS değildir; pvq_api'ye üyelik verilir).
- Parola geçişte YAZILMAZ: sunucuda `ALTER ROLE pvq_api PASSWORD '…'` (.env API_DB_PASSWORD), compose PVQ_DB_URL pvq_api'ye döner;
  alembic ve pg_dump yönetici (pvquant) ile koşmaya devam eder (alembic: dağıtım komutunda -e PVQ_DB_URL; yedek: PVQ_DB_ADMIN_URL).
- Mevcut tüm tablolara S/I/U/D, dizilere USAGE/SELECT/UPDATE; gelecekteki tablolar için ALTER DEFAULT PRIVILEGES (geçişler pvquant ile
  koştuğu sürece otomatik). Hypertable'lara (scada_hourly, forecast_values) ayrıca açık GRANT: TimescaleDB ACL'yi chunk'lara taşır.
- Mevcut RLS politikaları ve pvq_app yetkileri DEĞİŞMEZ.

Revision ID: v2488_db_rolu
Revises: v2486_faz4_kullanim
"""
from alembic import op

revision = "v2488_db_rolu"
down_revision = "v2486_faz4_kullanim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pvq_api') THEN
        CREATE ROLE pvq_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS;
      END IF;
      EXECUTE format('GRANT CONNECT ON DATABASE %I TO pvq_api', current_database());
    END $$;
    GRANT USAGE ON SCHEMA public TO pvq_api;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pvq_api;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO pvq_api;
    GRANT SELECT, INSERT, UPDATE, DELETE ON scada_hourly, forecast_values TO pvq_api;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pvq_api;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO pvq_api;
    GRANT pvq_app TO pvq_api;
    """)


def downgrade() -> None:
    op.execute("""
    REVOKE pvq_app FROM pvq_api;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM pvq_api;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM pvq_api;
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM pvq_api;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM pvq_api;
    REVOKE USAGE ON SCHEMA public FROM pvq_api;
    DROP ROLE IF EXISTS pvq_api;
    """)
