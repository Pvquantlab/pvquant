"""v2.609 (Faz 6 paketi F6-A) — abonelik / hak (entitlement) / kota katmanı: `plan_modulleri`, `kiraci_abonelik`, `abonelik_gecmisi`,
`planlar` yeni kota sütunları.

Mevcut `planlar` (v2492, uyarı kipi) ve `tenants.plan/status` KORUNUR; abonelik satırı tek kaynaktır ama `tenants.plan` ve `status` ile
çift yazılır (eski okuyucular bozulmaz). Zorlama bu göçle AÇILMAZ: kapı davranışı `Settings.abonelik_zorlama` (varsayılan «uyari»).

- plan_modulleri: plan → modül varsayılanı (dahil, sinir JSONB); tohum 00 planı §3 matrisi. Sistem tablosu, RLS yok.
- kiraci_abonelik: kiracı başına tek satır (plan, durum, tarihler, modül ek/çıkar, kota ezme, sözleşme notu); RLS (kiracı kendi satırını okur,
  platform pvq_api BYPASSRLS ile yazar); geri doldurma: her kiracıya satır — plan NULL ise 'pilot' (tenants.plan da 'pilot' yazılır),
  pilot kiracıda pilot_bitis = oluşturma + 60 gün (varsayım; 00 §13/5), süresi geçmişse 'sona_erdi' (yetki_service.durum_turet ile aynı), status suspended → askida.
- abonelik_gecmisi: yalnız ekleme (uygulama rollerinde UPDATE/DELETE yok; temizlik bakım bağlamı); RLS.
- Her iki tabloda tenants FK ON DELETE CASCADE: kiracı silme yalnız bakım/test işidir (üretimde uç yok); mevcut 30+ test fixture'ı kiracıyı
  doğrudan siler, abonelik satırı onları kilitlememeli (geçmiş kiracıyla birlikte gider; yalnız-ekleme kuralı uygulama rolleri içindir).

Revision ID: v2609_abonelik
Revises: v2603_dis_api
"""
from alembic import op

revision = "v2609_abonelik"
down_revision = "v2603_dis_api"
branch_labels = None
depends_on = None

PILOT_GUN = 60   # 00 §13/5: varsayım, ticari karar bekliyor

# 00 §3 matrisi — plan → (modül, dahil, sınır). Sınır JSONB yalnız bilgi/uyarı; kapı sözleşmesi yetki_service'te.
TOHUM = [
    ("pilot", "tahmin", True, None), ("pilot", "dogruluk", True, None), ("pilot", "veri", True, '{"baglanti": 1}'),
    ("pilot", "alarm", True, '{"kurallar": "temel"}'), ("pilot", "kgup", True, '{"revizyon": false}'),
    ("standart", "tahmin", True, None), ("standart", "dogruluk", True, None), ("standart", "veri", True, None), ("standart", "alarm", True, None),
    ("standart", "kgup", True, None), ("standart", "finansal_etki", True, None), ("standart", "mutabakat", True, None), ("standart", "rapor_gelismis", True, None),
    ("standart", "paylasim", True, None), ("standart", "portfoy_dsg", True, '{"portfoy": 1}'), ("standart", "dis_api", True, '{"kapsamlar": "oku"}'),
    ("kurumsal", "tahmin", True, None), ("kurumsal", "dogruluk", True, None), ("kurumsal", "veri", True, None), ("kurumsal", "alarm", True, None),
    ("kurumsal", "kgup", True, None), ("kurumsal", "finansal_etki", True, None), ("kurumsal", "mutabakat", True, None), ("kurumsal", "rapor_gelismis", True, None),
    ("kurumsal", "paylasim", True, None), ("kurumsal", "portfoy_dsg", True, None), ("kurumsal", "dis_api", True, None),
    ("kurumsal", "santral_yetki", True, '{"durum": "gelistirmede"}'), ("kurumsal", "sozlesme", True, '{"durum": "sinirli"}'),
    ("kurumsal", "entegrasyon", True, '{"durum": "is_bazli"}'), ("kurumsal", "destek_oncelik", True, None),
]
DURUMLAR = ("pilot", "aktif", "sona_eriyor", "yenileme_bekliyor", "askida", "sona_erdi", "feshedildi")


def upgrade() -> None:
    op.execute("""
    ALTER TABLE planlar ADD COLUMN IF NOT EXISTS ac_mw_limit NUMERIC;
    ALTER TABLE planlar ADD COLUMN IF NOT EXISTS portfoy_limit INTEGER;
    ALTER TABLE planlar ADD COLUMN IF NOT EXISTS aylik_isleme_saat_limit INTEGER;
    UPDATE planlar SET portfoy_limit = 1 WHERE ad = 'standart' AND portfoy_limit IS NULL;
    UPDATE planlar SET portfoy_limit = 0 WHERE ad = 'pilot' AND portfoy_limit IS NULL;
    CREATE TABLE IF NOT EXISTS plan_modulleri(
      plan_ad TEXT NOT NULL REFERENCES planlar(ad) ON UPDATE CASCADE ON DELETE CASCADE,
      modul TEXT NOT NULL,
      dahil BOOLEAN NOT NULL DEFAULT true,
      sinir JSONB,
      PRIMARY KEY (plan_ad, modul));
    GRANT SELECT ON plan_modulleri TO pvq_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON plan_modulleri TO pvq_api;
    """)
    for plan, modul, dahil, sinir in TOHUM:
        op.execute(f"INSERT INTO plan_modulleri(plan_ad, modul, dahil, sinir) VALUES ('{plan}', '{modul}', {'true' if dahil else 'false'}, "
                   f"{('CAST(' + chr(39) + sinir + chr(39) + ' AS jsonb)') if sinir else 'NULL'}) ON CONFLICT (plan_ad, modul) DO NOTHING")
    op.execute(f"""
    CREATE TABLE IF NOT EXISTS kiraci_abonelik(
      tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
      plan TEXT NOT NULL REFERENCES planlar(ad) ON UPDATE CASCADE,
      durum TEXT NOT NULL CHECK (durum IN ({", ".join(chr(39) + d + chr(39) for d in DURUMLAR)})),
      baslangic DATE NOT NULL DEFAULT CURRENT_DATE,
      bitis DATE,
      pilot_bitis DATE,
      modul_ek TEXT[] NOT NULL DEFAULT '{{}}',
      modul_cikar TEXT[] NOT NULL DEFAULT '{{}}',
      kota_ezme JSONB NOT NULL DEFAULT '{{}}',
      sozlesme_notu TEXT,
      teklif_ref TEXT,
      guncelleme TIMESTAMPTZ NOT NULL DEFAULT now(),
      guncelleyen TEXT,
      CHECK (bitis IS NULL OR bitis >= baslangic));
    ALTER TABLE kiraci_abonelik ENABLE ROW LEVEL SECURITY;
    ALTER TABLE kiraci_abonelik FORCE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS p_kiraci_abonelik ON kiraci_abonelik;
    CREATE POLICY p_kiraci_abonelik ON kiraci_abonelik USING (tenant_id = current_setting('app.tenant_id')::uuid)
      WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
    GRANT SELECT ON kiraci_abonelik TO pvq_app;
    GRANT SELECT, INSERT, UPDATE ON kiraci_abonelik TO pvq_api;
    CREATE TABLE IF NOT EXISTS abonelik_gecmisi(
      id BIGSERIAL PRIMARY KEY,
      tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      zaman TIMESTAMPTZ NOT NULL DEFAULT now(),
      aktor TEXT,
      eylem TEXT NOT NULL,
      eski JSONB,
      yeni JSONB,
      gerekce TEXT);
    CREATE INDEX IF NOT EXISTS ix_abonelik_gecmisi_tenant ON abonelik_gecmisi(tenant_id, zaman DESC);
    ALTER TABLE abonelik_gecmisi ENABLE ROW LEVEL SECURITY;
    ALTER TABLE abonelik_gecmisi FORCE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS p_abonelik_gecmisi ON abonelik_gecmisi;
    CREATE POLICY p_abonelik_gecmisi ON abonelik_gecmisi USING (tenant_id = current_setting('app.tenant_id')::uuid)
      WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
    GRANT SELECT ON abonelik_gecmisi TO pvq_app;
    GRANT SELECT, INSERT ON abonelik_gecmisi TO pvq_api;
    GRANT USAGE, SELECT ON SEQUENCE abonelik_gecmisi_id_seq TO pvq_api;
    REVOKE UPDATE, DELETE ON abonelik_gecmisi FROM pvq_app;
    REVOKE UPDATE, DELETE ON abonelik_gecmisi FROM pvq_api;
    """)
    # geri doldurma: plan NULL → pilot (çift yazım: tenants.plan da pilot)
    op.execute("UPDATE tenants SET plan = 'pilot' WHERE plan IS NULL")
    op.execute(f"""
    INSERT INTO kiraci_abonelik(tenant_id, plan, durum, baslangic, pilot_bitis, guncelleyen)
    SELECT t.id, t.plan,
           CASE WHEN t.status = 'suspended' THEN 'askida'
                WHEN t.plan = 'pilot' AND (t.created_at + interval '{PILOT_GUN} days') < now() THEN 'sona_erdi'
                WHEN t.plan = 'pilot' THEN 'pilot'
                ELSE 'aktif' END,
           CAST(t.created_at AT TIME ZONE 'UTC' AS date),
           CASE WHEN t.plan = 'pilot' THEN CAST((t.created_at + interval '{PILOT_GUN} days') AT TIME ZONE 'UTC' AS date) END,
           'goc v2609'
    FROM tenants t WHERE NOT EXISTS (SELECT 1 FROM kiraci_abonelik a WHERE a.tenant_id = t.id)""")
    op.execute("INSERT INTO abonelik_gecmisi(tenant_id, aktor, eylem, yeni, gerekce) "
               "SELECT tenant_id, 'goc v2609', 'geri_doldurma', jsonb_build_object('plan', plan, 'durum', durum, 'pilot_bitis', pilot_bitis), "
               "'v2.609 göçü: mevcut tenants.plan/status/created_at değerlerinden; pilot süresi 60 gün varsayımı' FROM kiraci_abonelik WHERE guncelleyen = 'goc v2609'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS abonelik_gecmisi; DROP TABLE IF EXISTS kiraci_abonelik; DROP TABLE IF EXISTS plan_modulleri;")
    op.execute("ALTER TABLE planlar DROP COLUMN IF EXISTS ac_mw_limit; ALTER TABLE planlar DROP COLUMN IF EXISTS portfoy_limit; "
               "ALTER TABLE planlar DROP COLUMN IF EXISTS aylik_isleme_saat_limit")
