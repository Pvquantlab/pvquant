"""v2.556 (Aşama 3, K1/K2) — bulut kimlik kasası ve ham saatlik bulut verisi.

bulut_kimlik: sağlayıcı hesabı (FusionSolar userName/systemCode …) ZARF ŞİFRELİ (kasa.py: kayıt başına DEK, ortamdaki KEK ile sarılı; AAD
tenant:plant:saglayici). Düz metin sütunu yoktur. `etiket` maskeli kullanıcı adıdır (gizli değil). `onay_json` sahibin iki onayı (yalnızca okuma +
şifreli saklama) metin, zaman ve aktörle. `cekis_acik` sahibin ayrı adımı; `birim_dogrulandi` gerçek yanıtla birim semantiği sabitlenince (ondan önce
veri yalnız ham tabloya düşer, gölge görünüme yazılmaz). Kota: NBI hesabı başına günlük çağrı sayacı (getKpiStationHour Roundup(n/100)+24).
bulut_saatlik_ham: sağlayıcıdan gelen saatlik dataItemMap olduğu gibi (jsonb) — birim yorumlanmadan saklanır; UI «belgeye göre kWh» notuyla gösterir.
Her iki tablo RLS'li; pvq_app okur/yazar/siler (kimlik silinebilmeli).

Revision ID: v2556_bulut_kimlik
Revises: v2550_kaynak_saatlik
"""
from alembic import op

revision = "v2556_bulut_kimlik"
down_revision = "v2550_kaynak_saatlik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS bulut_kimlik (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      saglayici TEXT NOT NULL,
      bolge TEXT,
      dis_kimlik TEXT,
      kek_id TEXT NOT NULL,
      dek_sarili BYTEA NOT NULL,
      sifreli BYTEA NOT NULL,
      surum SMALLINT NOT NULL DEFAULT 1,
      etiket TEXT,
      onay_json JSONB NOT NULL,
      cekis_acik BOOLEAN NOT NULL DEFAULT FALSE,
      birim_dogrulandi BOOLEAN NOT NULL DEFAULT FALSE,
      kota_gun DATE,
      kota_sayac INT NOT NULL DEFAULT 0,
      son_cekis TIMESTAMPTZ,
      son_durum TEXT,
      son_hata TEXT,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
      guncelleme TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (plant_id, saglayici)
    )""")
    op.execute("ALTER TABLE bulut_kimlik ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bulut_kimlik FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_bulut_kimlik ON bulut_kimlik")
    op.execute("CREATE POLICY p_bulut_kimlik ON bulut_kimlik USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON bulut_kimlik TO pvq_app")
    op.execute("""
    CREATE TABLE IF NOT EXISTS bulut_saatlik_ham (
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      saglayici TEXT NOT NULL,
      ts_utc TIMESTAMPTZ NOT NULL,
      dis_kimlik TEXT,
      alanlar JSONB NOT NULL,
      alinma TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (plant_id, saglayici, ts_utc)
    )""")
    op.execute("ALTER TABLE bulut_saatlik_ham ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bulut_saatlik_ham FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_bulut_saatlik_ham ON bulut_saatlik_ham")
    op.execute("CREATE POLICY p_bulut_saatlik_ham ON bulut_saatlik_ham USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON bulut_saatlik_ham TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bulut_saatlik_ham")
    op.execute("DROP TABLE IF EXISTS bulut_kimlik")
