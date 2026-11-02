"""v2.527 (P2b-2) — EPYS saatlik uzlaştırma detayı: müşterinin EPYS «Uzlaştırma Dönemi Detay Listeleme» / «Dengesizlik Uzlaştırma» / «KÜPST Detay»
ekranlarından indirdiği saatlik XLSX/CSV satırları (PTF, SMF, UEVM, UEÇM, KUDÜP, BUDÜP, YALM, YATM, pozitif/negatif EDM ve EDT, KÜPSM, KÜPST; 02-24)
santral ve dönem bazında saklanır; PVQuant dökümüyle saat saat, eş kapsamlı kıyas (saatlik_detay_service). Her yükleme ayrı yukleme_id; silme/güncelleme
yok (geçmiş korunur). RLS kiracı bağlamı; pvq_app SELECT/INSERT. Resmî dosya başlıkları görülmedi (kılavuz ekran adlarından türetildi).

Revision ID: v2527_saatlik_detay
Revises: v2523_sayac
"""
from alembic import op

revision = "v2527_saatlik_detay"
down_revision = "v2523_sayac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS uzlastirma_saatlik (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      donem DATE NOT NULL,
      yukleme_id UUID NOT NULL,
      ts_utc TIMESTAMPTZ NOT NULL,
      versiyon TEXT,
      kaynak_ekran TEXT NOT NULL CHECK (kaynak_ekran IN ('detay', 'dengesizlik', 'kupst')),
      ptf DOUBLE PRECISION, smf DOUBLE PRECISION,
      uevm_mwh DOUBLE PRECISION, uecm_mwh DOUBLE PRECISION,
      kudup_mwh DOUBLE PRECISION, budup_mwh DOUBLE PRECISION, yalm_mwh DOUBLE PRECISION, yatm_mwh DOUBLE PRECISION,
      edm_poz_mwh DOUBLE PRECISION, edm_neg_mwh DOUBLE PRECISION, edt_poz_tl DOUBLE PRECISION, edt_neg_tl DOUBLE PRECISION,
      kupsm_mwh DOUBLE PRECISION, kupst_tl DOUBLE PRECISION,
      dosya_adi TEXT, sha256 TEXT, yukleyen UUID,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS uzl_saatlik_plant_donem ON uzlastirma_saatlik(plant_id, donem, yukleme_id, ts_utc)")
    op.execute("ALTER TABLE uzlastirma_saatlik ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE uzlastirma_saatlik FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_uzl_saatlik ON uzlastirma_saatlik")
    op.execute("CREATE POLICY p_uzl_saatlik ON uzlastirma_saatlik USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON uzlastirma_saatlik TO pvq_app")   # güncelleme/silme yok — her yükleme yeni sürüm


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS uzlastirma_saatlik")
