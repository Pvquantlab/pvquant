"""v2.546 (P4b-2) — Modbus TCP / SunSpec düzenli örnekleme: sahibin açıkça başlattığı («düzenli veri çekişini başlat») salt-okuma örnekleri
(anlık güç W, sayaç Wh, DC güç, durum kodu, olay bitleri) santral × zaman damgası olarak saklanır; saatlik toplama ayrı batch ile scada_hourly'ye
yazılır (kaynak 'modbus_sunspec'; var olan saat üzerine YAZILMAZ — dosya/EPİAŞ verisi korunur). Ham örnekler silinmez. RLS kiracı bağlamı.

Revision ID: v2546_canli_ornek
Revises: v2542_iklim_poa
"""
from alembic import op

revision = "v2546_canli_ornek"
down_revision = "v2542_iklim_poa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS canli_ornek (
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      ts_utc TIMESTAMPTZ NOT NULL,
      kaynak TEXT NOT NULL DEFAULT 'modbus_sunspec' CHECK (kaynak IN ('modbus_sunspec')),
      guc_w DOUBLE PRECISION,
      enerji_wh DOUBLE PRECISION,
      dc_guc_w DOUBLE PRECISION,
      durum_kodu SMALLINT,
      olaylar_json JSONB,
      PRIMARY KEY (plant_id, ts_utc)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS canli_ornek_plant_ts ON canli_ornek(plant_id, ts_utc DESC)")
    op.execute("ALTER TABLE canli_ornek ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE canli_ornek FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_canli_ornek ON canli_ornek")
    op.execute("CREATE POLICY p_canli_ornek ON canli_ornek USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON canli_ornek TO pvq_app")   # ham örnek düzeltilmez, silinmez


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS canli_ornek")
