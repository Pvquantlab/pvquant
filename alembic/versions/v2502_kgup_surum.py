"""v2.502 — KGÜP sürüm arşivi (F-06; 29.10.2026 paketi A-1): üretilen ve indirilen her KGÜP/EAK dosyasının DEĞİŞTİRİLEMEZ kaydı.

«15:30'da hangi tahmine dayanarak bu programı bildirdim» belgesi (DUY m.69(1),(5),(6); geriye dönük itiraz 12 ay m.133(5)).
Her satır: teslim günü, sürüm no (aynı gün yeniden üretim yeni sürüm), kantil, kaynak koşu ve kesim, EAK, SHA-256 ve dosya baytları
(BOM dâhil; indirilen dosyayla birebir), indiren kullanıcı. UPDATE/DELETE yetkisi verilmez: kayıt yalnız eklenir. Saklama en az
15 ay (itiraz + fatura itirazı + pay); varsayılan 24 ay (VARSAYIM) — temizlik ayrı iş, bu göçte yok. RLS: kiracı bağlamı.

Revision ID: v2502_kgup_surum
Revises: v2493_faz6_kurulus
"""
from alembic import op

revision = "v2502_kgup_surum"
down_revision = "v2493_faz6_kurulus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS kgup_surum (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      teslim_gunu DATE NOT NULL,
      surum INT NOT NULL,
      kantil TEXT NOT NULL,
      run_id UUID,
      run_at TIMESTAMPTZ,
      kesim TIMESTAMPTZ,
      eak_mw DOUBLE PRECISION,
      eak_kaynak TEXT,
      toplam_mwh DOUBLE PRECISION,
      sha256 CHAR(64) NOT NULL,
      dosya BYTEA NOT NULL,
      dosya_adi TEXT NOT NULL,
      sablon_json JSONB,
      indiren UUID,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (plant_id, teslim_gunu, surum)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS kgup_surum_plant_gun ON kgup_surum(plant_id, teslim_gunu DESC, surum DESC)")
    op.execute("ALTER TABLE kgup_surum ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE kgup_surum FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_kgup_surum ON kgup_surum")
    op.execute("CREATE POLICY p_kgup_surum ON kgup_surum USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON kgup_surum TO pvq_app")   # UPDATE/DELETE YOK — değiştirilemez kayıt


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kgup_surum")
