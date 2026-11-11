"""v2.588 (Faz 3 paketi F3-A) — Portföy varlıkları: kuruluş, portföy, zamanlı üyelik, DSG grubu, toplayıcı kapsamı, ticari sözleşme, portföy sonucu.

Santral sahibi, işletmeci, toplayıcı ve DSG yöneticisi FARKLI kuruluşlar olabilir; ilişkiler ayrı tablolarda ve TARİHLİDİR
(gecerli_bas / gecerli_bit): üyelik ya da sözleşme değişince eski kayıt silinmez, tarihle kapatılır; geçmiş dönem hesabı o tarihteki
üyelikle kurulur. Ana veri tablolarında DELETE yetkisi yok (pvq_app SELECT/INSERT/UPDATE). `portfoy_sonuc` YALNIZ EKLEME
(finansal_etki_sonuc kalıbı): hesap anındaki üyelik ve sözleşme anlık görüntüsü meta_json'da taşınır.
Geriye uyumluluk: `plants.params_json.dsg_kodu` beyanı korunur; üyelik tablosu boşsa DSG gruplaması beyana düşer.
Var olan tahmin / uzlaştırma / FEM tabloları ve servisleri DOKUNULMAZ.

Revision ID: v2588_portfoy_varliklari
Revises: v2583_finansal_etki_sonuc
"""
from alembic import op

revision = "v2588_portfoy_varliklari"
down_revision = "v2583_finansal_etki_sonuc"
branch_labels = None
depends_on = None

TABLOLAR = ("kurulus", "portfoy", "portfoy_uyelik", "dsg_grubu", "toplayici_kapsami", "ticari_sozlesme", "portfoy_sonuc")


def _rls(tablo: str, yetki: str) -> None:
    op.execute(f"ALTER TABLE {tablo} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tablo} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS p_{tablo} ON {tablo}")
    op.execute(f"CREATE POLICY p_{tablo} ON {tablo} USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               f"WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute(f"GRANT {yetki} ON {tablo} TO pvq_app")


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS kurulus (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      ad TEXT NOT NULL,
      tur TEXT NOT NULL CHECK (tur IN ('sahip','isletmeci','toplayici','dsg_yoneticisi','gts','diger')),
      epias_kodu TEXT,
      notlar TEXT,
      aktif BOOLEAN NOT NULL DEFAULT true,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (tenant_id, ad)
    )""")
    op.execute("""
    CREATE TABLE IF NOT EXISTS portfoy (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      ad TEXT NOT NULL,
      tur TEXT NOT NULL CHECK (tur IN ('toplayici','dsg','isletme','ozel')),
      kurulus_id UUID REFERENCES kurulus(id),
      gecerli_bas DATE NOT NULL,
      gecerli_bit DATE,
      notlar TEXT,
      olusturan UUID,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (tenant_id, ad),
      CHECK (gecerli_bit IS NULL OR gecerli_bit >= gecerli_bas)
    )""")
    op.execute("""
    CREATE TABLE IF NOT EXISTS portfoy_uyelik (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      portfoy_id UUID NOT NULL REFERENCES portfoy(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      gecerli_bas DATE NOT NULL,
      gecerli_bit DATE,
      kaynak TEXT NOT NULL DEFAULT 'beyan' CHECK (kaynak IN ('beyan','belge','paylasim')),
      belge_adi TEXT,
      belge_sha256 TEXT,
      dogrulama TEXT NOT NULL DEFAULT 'beyan' CHECK (dogrulama IN ('beyan','belgeli','dogrulandi')),
      notlar TEXT,
      olusturan UUID,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK (gecerli_bit IS NULL OR gecerli_bit >= gecerli_bas)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS portfoy_uyelik_portfoy ON portfoy_uyelik(portfoy_id, gecerli_bas)")
    op.execute("CREATE INDEX IF NOT EXISTS portfoy_uyelik_plant ON portfoy_uyelik(plant_id, gecerli_bas)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS dsg_grubu (
      portfoy_id UUID PRIMARY KEY REFERENCES portfoy(id),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      dsg_kodu TEXT NOT NULL,
      yonetici_kurulus_id UUID REFERENCES kurulus(id),
      netlesme_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("""
    CREATE TABLE IF NOT EXISTS toplayici_kapsami (
      portfoy_id UUID PRIMARY KEY REFERENCES portfoy(id),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      kurulus_id UUID REFERENCES kurulus(id),
      sorumluluk_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("""
    CREATE TABLE IF NOT EXISTS ticari_sozlesme (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      portfoy_id UUID REFERENCES portfoy(id),
      plant_id UUID REFERENCES plants(id),
      taraf_a_kurulus_id UUID REFERENCES kurulus(id),
      taraf_b_kurulus_id UUID REFERENCES kurulus(id),
      tur TEXT NOT NULL CHECK (tur IN ('satis','dsg_uyelik','toplayici','isletme')),
      gecerli_bas DATE NOT NULL,
      gecerli_bit DATE,
      satis_modeli TEXT,
      uzlastirma_modeli TEXT,
      dengesizlik_sorumlusu TEXT CHECK (dengesizlik_sorumlusu IS NULL OR dengesizlik_sorumlusu IN ('santral','toplayici','dsg','gts')),
      dagitim_yontemi TEXT CHECK (dagitim_yontemi IS NULL OR dagitim_yontemi IN ('sapma','esit','uretim','sabit_pay','ozel')),
      parametreler_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      belge_adi TEXT,
      belge_sha256 TEXT,
      dogrulama TEXT NOT NULL DEFAULT 'beyan' CHECK (dogrulama IN ('beyan','belgeli','dogrulandi')),
      notlar TEXT,
      olusturan UUID,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK (gecerli_bit IS NULL OR gecerli_bit >= gecerli_bas),
      CHECK (portfoy_id IS NOT NULL OR plant_id IS NOT NULL)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS ticari_sozlesme_portfoy ON ticari_sozlesme(portfoy_id, gecerli_bas)")
    op.execute("CREATE INDEX IF NOT EXISTS ticari_sozlesme_plant ON ticari_sozlesme(plant_id, gecerli_bas)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS portfoy_sonuc (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      portfoy_id UUID NOT NULL REFERENCES portfoy(id),
      hesap_zamani TIMESTAMPTZ NOT NULL DEFAULT now(),
      tur TEXT NOT NULL CHECK (tur IN ('tahmin','sapma','dsg','finans','revizyon')),
      donem_kodu TEXT NOT NULL,
      donem_bas DATE NOT NULL,
      donem_bit DATE NOT NULL,
      sonuc_json JSONB NOT NULL,
      meta_json JSONB NOT NULL
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS portfoy_sonuc_portfoy_tur ON portfoy_sonuc(portfoy_id, tur, donem_kodu, hesap_zamani DESC)")
    for t in ("kurulus", "portfoy", "portfoy_uyelik", "dsg_grubu", "toplayici_kapsami", "ticari_sozlesme"):
        _rls(t, "SELECT, INSERT, UPDATE")   # ana veri: silme yok, tarihle kapatma
    _rls("portfoy_sonuc", "SELECT, INSERT")   # yalnız ekleme


def downgrade() -> None:
    for t in reversed(TABLOLAR):
        op.execute(f"DROP TABLE IF EXISTS {t}")
