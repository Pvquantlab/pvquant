"""TASLAK — ÇALIŞTIRILMADI (29.10.2026, F-06 KGÜP sürüm arşivi). `alembic/versions/` dışında durur; alembic bu dosyayı YÜKLEMEZ.

Amaç: üretilen/indirilen her KGÜP/EAK dosyasının değiştirilemez kaydı — «15:30'da hangi tahmine dayanarak bu programı bildirdim»
belgesi (DUY m.69(1),(5),(6); itiraz 12 ay m.133(5)). Saklama en az 15 ay; varsayılan 24 ay (VARSAYIM).
Uygulamaya alınınca: dosya adı v25xx_kgup_surum.py olarak versions/ altına, down_revision = o anki head, RLS politikası tenant bazlı.
"""
from alembic import op

revision = "v2501_kgup_surum"
down_revision = None   # TASLAK: gerçek head yazılacak
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS kgup_surum ("
        " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
        " tenant_id uuid NOT NULL REFERENCES tenants(id),"
        " plant_id uuid NOT NULL REFERENCES plants(id),"
        " teslim_gunu date NOT NULL,"                       # program günü (İstanbul)
        " surum int NOT NULL,"                              # aynı gün için 1, 2, 3… (yeniden üretim yeni sürüm açar)
        " kantil text NOT NULL,"                            # p10|p25|p50|p75|p90
        " run_id uuid NOT NULL,"                            # kaynak koşu (forecast_runs)
        " run_at timestamptz NOT NULL,"
        " kesim timestamptz NOT NULL,"                      # D-1 15:30 IST kesimi
        " eak_mw double precision,"
        " eak_kaynak text,"                                 # gecici|eak_alani|ac_tavani|kurulu_guc
        " eak_gerekce text,"                                # arıza/bakım notu (müşteri)
        " sha256 char(64) NOT NULL,"
        " dosya bytea NOT NULL,"                            # CSV baytları (BOM dâhil) — değiştirilemez
        " dosya_adi text NOT NULL,"
        " sablon_json jsonb,"
        " indiren uuid REFERENCES users(id),"
        " indirme_at timestamptz,"
        " olusturma timestamptz NOT NULL DEFAULT now(),"
        " UNIQUE (plant_id, teslim_gunu, surum))"
    )
    op.execute("ALTER TABLE kgup_surum ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY kgup_surum_tenant ON kgup_surum USING (tenant_id = current_setting('app.tenant_id', true)::uuid)")
    op.execute("GRANT SELECT, INSERT ON kgup_surum TO pvq_app")           # UPDATE/DELETE YOK: kayıt değiştirilemez
    op.execute("CREATE INDEX IF NOT EXISTS kgup_surum_plant_gun ON kgup_surum(plant_id, teslim_gunu DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kgup_surum")
