"""v2.597 (Faz 4 paketi F4-B, Stage 3 tahmin arşivi) — künye, etiket sözlüğü, değişmezlik, bakım bağlamı, q̂ geçmişi, NWP bileşen künyesi.

forecast_runs:
  cozunurluk_dk INT NOT NULL DEFAULT 60      değer satırlarının çözünürlüğü (arşiv saatlik; 15 dk geldiğinde satır kendini söyler)
  satir_sayisi INT                            yazılan değer satırı sayısı (eski `ufuk_saat` anlamı buraya taşınır)
  ufuk_saat INT                               ANLAM DÜZELTİLDİ: koşu anından son tahmin saatine kadar ileri saat sayısı; mevcut
                                              satırlar değerlerden yeniden hesaplanır (max(ts_utc) − run_at)
  nwp_bilesenler_json JSONB                   NWP bileşenleri → koşu zamanı ({"ECMWF IFS": ..., "ICON-EU": ..., "GFS": ...}); bilinmiyorsa NULL
  spec_json JSONB                             koşuda kullanılan PlantSpec anlık görüntüsü (kalibre katsayılar işlenmiş)
  artefakt_sha16 TEXT                         yüklenen hibrit artefaktının SHA-256 ilk 16 hex'i (Mod C), yoksa NULL
  konformal_q_json / sapma_oran_json / ufuk_sigma_json JSONB   uygulanan katman ayarları (bant arşivden yeniden kurulabilir)
  ensemble_kosu_zamani TIMESTAMPTZ            bant GEFS üyelerinden geldiyse üye koşusunun yayın zamanı
  veri_kalitesi_json JSONB                    meteo yaşı, kalibrasyon/konformal yaşı, kırpılan saat (sayı uydurulmaz: bilinmeyen NULL)
  etiket TEXT NOT NULL DEFAULT 'yayin' CHECK  sözlük: yayin | gun_ici | elle | backtest | simulasyon | sentetik | demo | yeniden_kurma
    geri doldurma: model='backtest' ya da meteo_source='open-meteo-arsiv' → 'backtest'; meteo_source='sentetik_tohum' → 'sentetik';
    NULL → 'yayin' (gece/program koşusu); 'gun_ici' / 'elle' olduğu gibi.

Değişmezlik: forecast_runs ve forecast_values üzerinde UPDATE/DELETE tetikleyiciyle reddedilir; yalnız bakım bağlamı
(`SELECT set_config('app.arsiv_bakim','1',true)`; Python: `pvquant.db.bakim_baglami()`) geçer. pvq_api / pvq_app'ten
UPDATE ve DELETE yetkisi de kaldırılır (uygulama kodu arşivi hiç değiştirmez — v2.176 ilkesi artık şemada).

konformal_ayar_gecmis: yalnız-ekleme q̂ sürüm geçmişi (konformal_ayar UPSERT'i geçmişi eziyordu; bant yeniden kurma için sürüm gerekir).
meteo_kosu_kunye: NWP koşusunun bileşen künyesi (kaynak, koşu zamanı, nokta) → {model: koşu zamanı}; arşiv satırları harmanlı
olduğundan bileşen zamanları ayrıca tutulmazsa bilinemiyordu.
skill_daily: hesap_zamani + yeniden_hesap_sayisi (ölçüm yeniden yüklendi / hijyen yeniden bayrakladı → karne sessizce değişmesin;
yalnız «yeniden hesaplandı» bayrağı; yalnız-ekleme karne AYRI karar).

Revision ID: v2597_arsiv_kunye
Revises: v2588_portfoy_varliklari
"""
from alembic import op

revision = "v2597_arsiv_kunye"
down_revision = "v2588_portfoy_varliklari"
branch_labels = None
depends_on = None

ETIKETLER = ("yayin", "gun_ici", "elle", "backtest", "simulasyon", "sentetik", "demo", "yeniden_kurma")

YENI_SUTUNLAR = (
    ("cozunurluk_dk", "INT NOT NULL DEFAULT 60"), ("satir_sayisi", "INT"), ("nwp_bilesenler_json", "JSONB"), ("spec_json", "JSONB"),
    ("artefakt_sha16", "TEXT"), ("konformal_q_json", "JSONB"), ("sapma_oran_json", "JSONB"), ("ufuk_sigma_json", "JSONB"),
    ("ensemble_kosu_zamani", "TIMESTAMPTZ"), ("veri_kalitesi_json", "JSONB"),
)

TETIKLEYICI_FN = """
CREATE OR REPLACE FUNCTION pvq_arsiv_degismez() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('app.arsiv_bakim', true) = '1' THEN
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'tahmin arşivi değişmez: % % reddedildi (bakım bağlamı gerekir: set_config(''app.arsiv_bakim'',''1'',true))', TG_OP, TG_TABLE_NAME
    USING ERRCODE = 'integrity_constraint_violation';
END $$;
"""


def upgrade() -> None:
    # 1. künye sütunları
    for ad, tip in YENI_SUTUNLAR:
        op.execute(f"ALTER TABLE forecast_runs ADD COLUMN IF NOT EXISTS {ad} {tip}")
    # 2. ufuk_saat anlamı: eski değer satır sayısıydı → satir_sayisi; ufuk_saat değerlerden (ileri saat) yeniden kurulur
    op.execute("UPDATE forecast_runs SET satir_sayisi = ufuk_saat WHERE satir_sayisi IS NULL AND ufuk_saat IS NOT NULL")
    op.execute(
        "UPDATE forecast_runs r SET ufuk_saat = x.u FROM ("
        " SELECT f.run_id, FLOOR(EXTRACT(EPOCH FROM (max(f.ts_utc) - r2.run_at)) / 3600.0)::int AS u"
        " FROM forecast_values f JOIN forecast_runs r2 ON r2.id = f.run_id GROUP BY f.run_id, r2.run_at) x "
        "WHERE x.run_id = r.id")
    # 3. etiket sözlüğü: geri doldurma, varsayılan, NOT NULL, CHECK
    op.execute(
        "UPDATE forecast_runs SET etiket = CASE"
        " WHEN meteo_source = 'sentetik_tohum' THEN 'sentetik'"
        " WHEN model = 'backtest' OR meteo_source = 'open-meteo-arsiv' THEN 'backtest'"
        " WHEN etiket IS NULL THEN 'yayin' ELSE etiket END")
    op.execute("ALTER TABLE forecast_runs ALTER COLUMN etiket SET DEFAULT 'yayin'")
    op.execute("ALTER TABLE forecast_runs ALTER COLUMN etiket SET NOT NULL")
    op.execute("ALTER TABLE forecast_runs DROP CONSTRAINT IF EXISTS forecast_runs_etiket_check")
    op.execute("ALTER TABLE forecast_runs ADD CONSTRAINT forecast_runs_etiket_check CHECK (etiket IN ({}))".format(", ".join(f"'{e}'" for e in ETIKETLER)))
    # 4. değişmezlik: tetikleyici + yetki
    op.execute(TETIKLEYICI_FN)
    for t in ("forecast_runs", "forecast_values"):
        op.execute(f"DROP TRIGGER IF EXISTS tg_{t}_degismez ON {t}")
        op.execute(f"CREATE TRIGGER tg_{t}_degismez BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION pvq_arsiv_degismez()")
        op.execute(f"REVOKE UPDATE, DELETE ON {t} FROM pvq_api")
        op.execute(f"REVOKE UPDATE, DELETE ON {t} FROM pvq_app")
    # 5. konformal q̂ geçmişi (yalnız ekleme)
    op.execute(
        "CREATE TABLE IF NOT EXISTS konformal_ayar_gecmis ("
        " id BIGSERIAL PRIMARY KEY, tenant_id UUID NOT NULL, plant_id UUID NOT NULL REFERENCES plants(id),"
        " alpha DOUBLE PRECISION NOT NULL, grup TEXT NOT NULL, q_hat_json JSONB NOT NULL, n INT NOT NULL, pencere_gun INT NOT NULL,"
        " hesap_zamani TIMESTAMPTZ NOT NULL DEFAULT now(), kaynak TEXT NOT NULL DEFAULT 'gece')")
    op.execute("CREATE INDEX IF NOT EXISTS ix_konformal_ayar_gecmis_plant ON konformal_ayar_gecmis(plant_id, hesap_zamani)")
    op.execute("ALTER TABLE konformal_ayar_gecmis ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_konformal_ayar_gecmis ON konformal_ayar_gecmis")
    op.execute("CREATE POLICY p_konformal_ayar_gecmis ON konformal_ayar_gecmis USING (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON konformal_ayar_gecmis TO pvq_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE konformal_ayar_gecmis_id_seq TO pvq_app")
    op.execute("GRANT SELECT ON konformal_ayar_gecmis TO pvq_api")
    op.execute("REVOKE UPDATE, DELETE ON konformal_ayar_gecmis FROM pvq_api")   # varsayılan yetkiler yazma veriyor; yalnız ekleme
    op.execute("REVOKE UPDATE, DELETE ON konformal_ayar_gecmis FROM pvq_app")
    # mevcut ayar geçmişin ilk satırı olsun (bilgi zaten kayıttaydı)
    op.execute(
        "INSERT INTO konformal_ayar_gecmis(tenant_id, plant_id, alpha, grup, q_hat_json, n, pencere_gun, hesap_zamani, kaynak) "
        "SELECT tenant_id, plant_id, alpha, grup, q_hat_json, n, pencere_gun, hesap_zamani, 'goc_v2597' FROM konformal_ayar")
    # 6. NWP bileşen künyesi
    op.execute(
        "CREATE TABLE IF NOT EXISTS meteo_kosu_kunye ("
        " kaynak TEXT NOT NULL, kosu_zamani TIMESTAMPTZ NOT NULL, lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL,"
        " bilesenler_json JSONB NOT NULL, cekim_utc TIMESTAMPTZ NOT NULL DEFAULT now(),"
        " PRIMARY KEY (kaynak, kosu_zamani, lat, lon))")
    op.execute("GRANT SELECT, INSERT ON meteo_kosu_kunye TO pvq_app")
    op.execute("REVOKE UPDATE, DELETE ON meteo_kosu_kunye FROM pvq_api")
    # 7. karne yeniden hesap bayrağı
    op.execute("ALTER TABLE skill_daily ADD COLUMN IF NOT EXISTS hesap_zamani TIMESTAMPTZ")
    op.execute("ALTER TABLE skill_daily ADD COLUMN IF NOT EXISTS yeniden_hesap_sayisi INT NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE skill_daily DROP COLUMN IF EXISTS yeniden_hesap_sayisi")
    op.execute("ALTER TABLE skill_daily DROP COLUMN IF EXISTS hesap_zamani")
    op.execute("DROP TABLE IF EXISTS meteo_kosu_kunye")
    op.execute("DROP TABLE IF EXISTS konformal_ayar_gecmis")
    for t in ("forecast_runs", "forecast_values"):
        op.execute(f"DROP TRIGGER IF EXISTS tg_{t}_degismez ON {t}")
        op.execute(f"GRANT UPDATE, DELETE ON {t} TO pvq_api")
        op.execute(f"GRANT UPDATE ON {t} TO pvq_app")
    op.execute("DROP FUNCTION IF EXISTS pvq_arsiv_degismez()")
    op.execute("ALTER TABLE forecast_runs DROP CONSTRAINT IF EXISTS forecast_runs_etiket_check")
    op.execute("ALTER TABLE forecast_runs ALTER COLUMN etiket DROP NOT NULL")
    op.execute("ALTER TABLE forecast_runs ALTER COLUMN etiket DROP DEFAULT")
    op.execute("UPDATE forecast_runs SET etiket = NULL WHERE etiket = 'yayin'")
    op.execute("UPDATE forecast_runs SET ufuk_saat = satir_sayisi WHERE satir_sayisi IS NOT NULL")
    for ad, _ in reversed(YENI_SUTUNLAR):
        op.execute(f"ALTER TABLE forecast_runs DROP COLUMN IF EXISTS {ad}")
