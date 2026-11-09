"""v2.550 (Aşama 1, D4/D5) — cihaz / kaynak / ölçüm sınırı kimliği ve gölge kanonik saatlik görünüm.

canli_ornek: `cihaz_id` (SunSpec seri no, 'santral' ya da 'scada'), `kaynak` (modbus_sunspec | iec104; v2.554), `sinir` (inverter_ac | plant_gross_ac | pcc_net | settlement), `profil` (1xx | 7xx) eklendi; birincil
anahtar (plant_id, cihaz_id, ts_utc) oldu — aynı santralda iki inverter aynı anda çakışmaz (Codex L10/G10). Var olan satırlar 'santral' cihazıyla korunur.
kaynak_saatlik: her kaynağın (bugün yalnız modbus_sunspec; dosya/EPİAŞ zaten scada_hourly'de) cihaz ve sınır kimlikli saatlik değeri, tamlık
(measured_complete | measured_partial | estimated), yöntem (sayac | entegrasyon), kapsama, revizyon ve köken. Eklemeli (insert-only): geç gelen ya da
değişen değer yeni revizyon; eski satır silinmez. scada_hourly tüketicileri DEĞİŞMEZ; bu tablo gölge görünümdür (kaynak_secim_service okur).

Revision ID: v2550_kaynak_saatlik
Revises: v2546_canli_ornek
"""
from alembic import op

revision = "v2550_kaynak_saatlik"
down_revision = "v2546_canli_ornek"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE canli_ornek ADD COLUMN IF NOT EXISTS cihaz_id TEXT NOT NULL DEFAULT 'santral'")
    op.execute("ALTER TABLE canli_ornek ADD COLUMN IF NOT EXISTS sinir TEXT NOT NULL DEFAULT 'inverter_ac' CHECK (sinir IN ('inverter_ac','plant_gross_ac','pcc_net','settlement'))")
    op.execute("ALTER TABLE canli_ornek ADD COLUMN IF NOT EXISTS profil TEXT")
    op.execute("ALTER TABLE canli_ornek DROP CONSTRAINT IF EXISTS canli_ornek_kaynak_check")   # v2.554 (S4): IEC 104 örnekleri de ham tabloya
    op.execute("ALTER TABLE canli_ornek ADD CONSTRAINT canli_ornek_kaynak_check CHECK (kaynak IN ('modbus_sunspec','iec104'))")
    op.execute("ALTER TABLE canli_ornek DROP CONSTRAINT IF EXISTS canli_ornek_pkey")
    op.execute("ALTER TABLE canli_ornek ADD PRIMARY KEY (plant_id, cihaz_id, ts_utc)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS kaynak_saatlik (
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      kaynak TEXT NOT NULL,
      cihaz_id TEXT NOT NULL DEFAULT 'santral',
      sinir TEXT NOT NULL DEFAULT 'inverter_ac' CHECK (sinir IN ('inverter_ac','plant_gross_ac','pcc_net','settlement')),
      ts_utc TIMESTAMPTZ NOT NULL,
      revizyon INT NOT NULL DEFAULT 1,
      power_kw DOUBLE PRECISION,
      energy_kwh DOUBLE PRECISION,
      tamlik TEXT NOT NULL CHECK (tamlik IN ('measured_complete','measured_partial','estimated')),
      yontem TEXT NOT NULL,
      kapsama_dk DOUBLE PRECISION,
      n_ornek INT,
      sinir_interpolasyon BOOLEAN NOT NULL DEFAULT FALSE,
      batch_id UUID,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (plant_id, kaynak, cihaz_id, sinir, ts_utc, revizyon)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS kaynak_saatlik_plant_ts ON kaynak_saatlik(plant_id, ts_utc DESC)")
    op.execute("ALTER TABLE kaynak_saatlik ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE kaynak_saatlik FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_kaynak_saatlik ON kaynak_saatlik")
    op.execute("CREATE POLICY p_kaynak_saatlik ON kaynak_saatlik USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON kaynak_saatlik TO pvq_app")   # eklemeli: revizyon yeni satır, eski silinmez


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kaynak_saatlik")
    op.execute("ALTER TABLE canli_ornek DROP CONSTRAINT IF EXISTS canli_ornek_pkey")
    op.execute("ALTER TABLE canli_ornek ADD PRIMARY KEY (plant_id, ts_utc)")
    op.execute("ALTER TABLE canli_ornek DROP CONSTRAINT IF EXISTS canli_ornek_kaynak_check")
    op.execute("ALTER TABLE canli_ornek ADD CONSTRAINT canli_ornek_kaynak_check CHECK (kaynak IN ('modbus_sunspec'))")
    op.execute("ALTER TABLE canli_ornek DROP COLUMN IF EXISTS profil, DROP COLUMN IF EXISTS sinir, DROP COLUMN IF EXISTS cihaz_id")
