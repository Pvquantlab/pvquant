"""v2.574 (Faz 1 paketi F1-C, Stage 4–5) — bağımsız doğrulama sonuçları: YALNIZ EKLEME.

dogrulama_sonuc: bir santral (ya da plant_id NULL = portföy) için bir dönem, bir koşu seçim kuralı ve bir sözlük sürümüyle hesaplanan
metrikler, kesitler, referans kıyası, veri bütünlüğü ve yeniden üretim metası (koşu kümesi ve saat kümesi özetleri, yazılım sürümü,
hesap zamanı). Eski satır hiç güncellenmez/silinmez; geç gelen veri yeni satır olur. Mevcut `skill_daily` ve gece karnesi DOKUNULMAZ.
Uygulama rolü (pvq_app) yalnız SELECT/INSERT alır; UPDATE/DELETE yetkisi verilmez (pvq_api rolü BYPASSRLS ve geniş yetkilidir — v2488;
bu tabloda da UPDATE/DELETE çağrısı kodda yoktur, rol düzeyinde kısıt ayrı karar).

Revision ID: v2574_dogrulama_sonuc
Revises: v2573_scada_kapsama
"""
from alembic import op

revision = "v2574_dogrulama_sonuc"
down_revision = "v2573_scada_kapsama"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS dogrulama_sonuc (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID REFERENCES plants(id),
      hesap_zamani TIMESTAMPTZ NOT NULL DEFAULT now(),
      donem_bas DATE NOT NULL,
      donem_bit DATE NOT NULL,
      kural TEXT NOT NULL,
      kaynak TEXT NOT NULL DEFAULT 'scada',
      sozluk_surumu TEXT NOT NULL,
      metrik_json JSONB NOT NULL,
      kesit_json JSONB,
      referans_json JSONB,
      butunluk_json JSONB,
      meta_json JSONB NOT NULL
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS dogrulama_sonuc_plant_zaman ON dogrulama_sonuc(plant_id, kural, hesap_zamani DESC)")
    op.execute("ALTER TABLE dogrulama_sonuc ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dogrulama_sonuc FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_dogrulama_sonuc ON dogrulama_sonuc")
    op.execute("CREATE POLICY p_dogrulama_sonuc ON dogrulama_sonuc USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON dogrulama_sonuc TO pvq_app")   # yalnız ekleme


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dogrulama_sonuc")
