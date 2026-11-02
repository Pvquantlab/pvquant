"""v2.523 (P4a) — Sayaç serisi: müşterinin OSOS / MASS / EPYS dışa aktarımından yüklediği uzlaştırmaya esas sayaç verisi (saatlik veriş kWh,
isteğe bağlı çekiş), SCADA serisinden AYRI saklanır (scada_hourly dokunulmaz). Her değer kaynak (osos / mass / epys / elle) ve nitelik
(olculmus / tahmini / doldurulmus / elle / yok — EDAŞ portalı durum kodları 06-46) taşır; aynı saat + kaynak yeniden yüklenirse üzerine yazılır
(sayaç verisi düzeltme alır: DUY m.82(4) 12. gün 17:30'a kadar). Yükleme tarihçesi sayac_yukleme'de (silme yok). RLS kiracı bağlamı.

Revision ID: v2523_sayac
Revises: v2522_mutabakat
"""
from alembic import op

revision = "v2523_sayac"
down_revision = "v2522_mutabakat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS sayac_saatlik (
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      ts_utc TIMESTAMPTZ NOT NULL,
      kaynak TEXT NOT NULL CHECK (kaynak IN ('osos', 'mass', 'epys', 'elle')),
      veris_kwh DOUBLE PRECISION,
      cekis_kwh DOUBLE PRECISION,
      nitelik TEXT NOT NULL DEFAULT 'olculmus' CHECK (nitelik IN ('olculmus', 'tahmini', 'doldurulmus', 'elle', 'yok')),
      n_dilim SMALLINT,
      yukleme_id UUID,
      guncelleme TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (plant_id, ts_utc, kaynak)
    )""")
    op.execute("""
    CREATE TABLE IF NOT EXISTS sayac_yukleme (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      kaynak TEXT NOT NULL,
      dosya_adi TEXT,
      sha256 TEXT,
      bicim TEXT,
      bas_utc TIMESTAMPTZ,
      bit_utc TIMESTAMPTZ,
      n_saat INT NOT NULL DEFAULT 0,
      n_satir INT NOT NULL DEFAULT 0,
      nitelik_json JSONB,
      uyarilar_json JSONB,
      yukleyen UUID,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS sayac_yukleme_plant ON sayac_yukleme(plant_id, olusturma DESC)")
    for t, p in (("sayac_saatlik", "p_sayac_saatlik"), ("sayac_yukleme", "p_sayac_yukleme")):
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {p} ON {t}")
        op.execute(f"CREATE POLICY {p} ON {t} USING (tenant_id = current_setting('app.tenant_id')::uuid) "
                   f"WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON sayac_saatlik TO pvq_app")   # yeniden yükleme aynı saati günceller (düzeltme); silme yok
    op.execute("GRANT SELECT, INSERT ON sayac_yukleme TO pvq_app")
    # olay türü «uzaktan açma yapılamadı» (P1 bağımlılığı: Karar 14909 bedel göstergesi olay kaydından sayar)
    op.execute("ALTER TABLE olay DROP CONSTRAINT IF EXISTS olay_tur_check")
    op.execute("ALTER TABLE olay ADD CONSTRAINT olay_tur_check CHECK (tur IN ('planli_bakim', 'ariza', 'talimat_yat', 'talimat_yal', 'acil_kesme', "
               "'sebeke_kesintisi', 'hasar', 'uzaktan_acma'))")


def downgrade() -> None:
    op.execute("ALTER TABLE olay DROP CONSTRAINT IF EXISTS olay_tur_check")
    op.execute("ALTER TABLE olay ADD CONSTRAINT olay_tur_check CHECK (tur IN ('planli_bakim', 'ariza', 'talimat_yat', 'talimat_yal', 'acil_kesme', "
               "'sebeke_kesintisi', 'hasar'))")
    op.execute("DROP TABLE IF EXISTS sayac_saatlik")
    op.execute("DROP TABLE IF EXISTS sayac_yukleme")
