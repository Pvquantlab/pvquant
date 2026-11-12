"""v2.602 (Faz 4 paketi F4-H, Stage 10 denetim izi) — `denetim_izi` sertleştirme.

- Bulgu M1: dış API itme izi `kapsam='dis_api'` ile yazılıyordu, CHECK yalnız platform|musteri kabul ediyordu → INSERT reddediliyor,
  `kaydet` yutuyordu: iz kayboluyordu. CHECK kümesine `dis_api` eklenir.
- Uygulama rolleri (pvq_app, pvq_api) denetim izinden satır SİLEMEZ ve GÜNCELLEYEMEZ; saklama temizliği yalnız SECURITY DEFINER
  `denetim_izi_temizle(eylemler, ay)` işleviyle (sahip yetkisi; yalnız platform kapsamı, verilen eylemler, `ay` aydan eski) koşar —
  worker pvq_api ile çağırır (v2.606 öz-inceleme: doğrudan DELETE pvq_api'de reddediliyordu) ve kendisi platform izine yazılır.
- `ayrinti` standardı şema değil sözleşme: ayar değişikliklerinde {"degisen": {alan: {"eski", "yeni"}}, "ayar_sha": {"eski", "yeni"}}
  (`denetim_service.ayar_degisikligi_kaydet`); sonuç meta'ları `ayar_sha` taşır, «etkilenen hesaplar» sorgusu bununla eşler.
- Kiracı okuması için tenant_id RLS politikası AYRI KARAR (bu göçte yok; okuma API katmanında tenant_id ile süzülür).

Revision ID: v2602_denetim
Revises: v2601_piyasa_fiyat_surum
"""
from alembic import op

revision = "v2602_denetim"
down_revision = "v2601_piyasa_fiyat_surum"
branch_labels = None
depends_on = None

KAPSAMLAR = ("platform", "musteri", "dis_api")


def upgrade() -> None:
    op.execute("ALTER TABLE denetim_izi DROP CONSTRAINT IF EXISTS denetim_izi_kapsam_check")
    op.execute("ALTER TABLE denetim_izi ADD CONSTRAINT denetim_izi_kapsam_check CHECK (kapsam IN ('platform','musteri','dis_api'))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_denetim_nesne ON denetim_izi(nesne_tur, nesne_id, zaman DESC)")
    for rol in ("pvq_app", "pvq_api"):
        op.execute(f"REVOKE UPDATE, DELETE ON denetim_izi FROM {rol}")
    # saklama temizliği: tek izinli silme yolu (sahip yetkisiyle; parametreler dar: platform kapsamı + eylem listesi + ay)
    op.execute("""
CREATE OR REPLACE FUNCTION denetim_izi_temizle(eylemler text[], ay integer) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE n integer;
BEGIN
  IF ay IS NULL OR ay <= 0 THEN RETURN 0; END IF;
  DELETE FROM denetim_izi WHERE kapsam = 'platform' AND eylem = ANY(eylemler) AND zaman < now() - (ay * interval '1 month');
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$""")
    op.execute("REVOKE ALL ON FUNCTION denetim_izi_temizle(text[], integer) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION denetim_izi_temizle(text[], integer) TO pvq_api")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS denetim_izi_temizle(text[], integer)")
    for rol in ("pvq_app", "pvq_api"):
        op.execute(f"GRANT UPDATE, DELETE ON denetim_izi TO {rol}")
    op.execute("DROP INDEX IF EXISTS ix_denetim_nesne")
    op.execute("ALTER TABLE denetim_izi DROP CONSTRAINT IF EXISTS denetim_izi_kapsam_check")
    # dis_api satırları silinmez (denetim izi): eski CHECK NOT VALID eklenir — yeni satırlar denetlenir, mevcutlar durur
    op.execute("ALTER TABLE denetim_izi ADD CONSTRAINT denetim_izi_kapsam_check CHECK (kapsam IN ('platform','musteri')) NOT VALID")
