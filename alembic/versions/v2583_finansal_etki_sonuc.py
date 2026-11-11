"""v2.583 (Faz 2 paketi F2-E, Stage 2 meta ve Stage 6 geçmiş) — Finansal Etki Merkezi sonuçları: YALNIZ EKLEME.

finansal_etki_sonuc: bir santral için bir dönem (gün / hafta / ay / çeyrek / yıl kodu) ve bir sözlük sürümüyle derlenen üretim özeti, satış
geliri, uzlaştırma bileşenleri (resmî eşleme ve göstergelerle), üretim düşüklüğü, ileri maruziyet, birleşik toplam ve yeniden üretim metası
(kural sürümü, fiyat kaynağı sayımı, program/üretim kaynağı, tarife özeti ve özeti, bildirim sürümü, yazılım sürümü, hesap zamanı).
Eski satır hiç güncellenmez/silinmez; yeni hesap yeni satırdır (Stage 6: varsayımların geçmiş sürümleri). Senaryo hesapları (pozisyon
geçersiz kılma) KAYDEDİLMEZ; resmî değerlerin üzerine senaryo yazılmaz. Uygulama rolü (pvq_app) yalnız SELECT/INSERT alır.
Var olan dengesizlik / mutabakat / tarife tabloları ve servisleri DOKUNULMAZ.

Revision ID: v2583_finansal_etki_sonuc
Revises: v2574_dogrulama_sonuc
"""
from alembic import op

revision = "v2583_finansal_etki_sonuc"
down_revision = "v2574_dogrulama_sonuc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS finansal_etki_sonuc (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      hesap_zamani TIMESTAMPTZ NOT NULL DEFAULT now(),
      donem_tur TEXT NOT NULL,
      donem_kodu TEXT NOT NULL,
      donem_bas DATE NOT NULL,
      donem_bit DATE NOT NULL,
      uretim_girdisi TEXT NOT NULL DEFAULT 'scada',
      sozluk_surumu TEXT NOT NULL,
      uretim_json JSONB NOT NULL,
      gelir_json JSONB NOT NULL,
      uzlastirma_json JSONB NOT NULL,
      dusukluk_json JSONB,
      maruziyet_json JSONB,
      toplam_json JSONB NOT NULL,
      meta_json JSONB NOT NULL
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS finansal_etki_sonuc_plant_donem ON finansal_etki_sonuc(plant_id, donem_kodu, hesap_zamani DESC)")
    op.execute("ALTER TABLE finansal_etki_sonuc ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE finansal_etki_sonuc FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_finansal_etki_sonuc ON finansal_etki_sonuc")
    op.execute("CREATE POLICY p_finansal_etki_sonuc ON finansal_etki_sonuc USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON finansal_etki_sonuc TO pvq_app")   # yalnız ekleme


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS finansal_etki_sonuc")
