"""v2.598 (Faz 4 paketi F4-C, Stage 4 veri kalitesi) — flag sözlüğü kısıtı, ölçüm satırı künyesi, iş sonucu JSON'u.

scada_hourly:
  flag CHECK (sözlük: services/kalite_sozlugu.FLAGLAR). Mevcut değerler doğrulanır: kısıt NOT VALID eklenir, ardından
    doğrulama denenir; sözlük dışı eski değer varsa kısıt NOT VALID kalır (yeni satırlar yine denetlenir) ve göç bunu NOTICE ile
    söyler — veri sessizce değiştirilmez.
  alinma_zamani TIMESTAMPTZ   satırın sisteme geliş zamanı (geri doldurma: parti oluşturma zamanı; partisiz satırda NULL)
  aralik_dk SMALLINT          kaynak adımı (dakika); yükleme dönüşüm künyesinden; bilinmiyorsa NULL
  kaynak_damga_tipi TEXT      kaynak damgasının anlamı: aralik_basi | aralik_sonu | anlik; bilinmiyorsa NULL
  kaynak TEXT                 scada_dosya | epias | canli | bulut | elle; geri doldurma yalnız partinin format_json'u söylüyorsa
  sinir TEXT                  ölçüm sınırı (inverter_ac | plant_gross_ac | pcc_net | settlement); bilinmiyorsa NULL
jobs_log.sonuc_json JSONB     iş sonucunun yapılı hâli (durum, n_yazilan, uyarı…); `detail` metni geriye uyum için kalır,
                              veri yolu durumu artık regex yerine buradan okur.

Revision ID: v2598_kalite
Revises: v2597_arsiv_kunye
"""
import sys
from pathlib import Path

from alembic import op

revision = "v2598_kalite"
down_revision = "v2597_arsiv_kunye"
branch_labels = None
depends_on = None

# flag sözlüğü: kod tarafıyla tek kaynak (test: test_kalite_sozlugu_v2598::test_goc_flag_kumesi_sozlukle_ayni)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pvquant.services.kalite_sozlugu import FLAGLAR  # noqa: E402

YENI_SUTUNLAR = (("alinma_zamani", "TIMESTAMPTZ"), ("aralik_dk", "SMALLINT"), ("kaynak_damga_tipi", "TEXT"), ("kaynak", "TEXT"), ("sinir", "TEXT"))

KAYNAK_ESLEME = {"epias_realtime": "epias", "modbus_sunspec": "canli", "iec104": "canli", "scada_dosya": "scada_dosya", "dosya": "scada_dosya",
                 "fusionsolar": "bulut", "solaredge": "bulut", "solis": "bulut", "sungrow": "bulut", "growatt": "bulut"}


def upgrade() -> None:
    for ad, tip in YENI_SUTUNLAR:
        op.execute(f"ALTER TABLE scada_hourly ADD COLUMN IF NOT EXISTS {ad} {tip}")
    # geri doldurma: yalnız bilinen — parti zamanı ve partinin açık kaynak etiketi
    op.execute("UPDATE scada_hourly s SET alinma_zamani = b.created_at FROM ingestion_batches b WHERE b.id = s.batch_id AND s.alinma_zamani IS NULL")
    case = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in KAYNAK_ESLEME.items())
    op.execute(f"UPDATE scada_hourly s SET kaynak = (CASE b.format_json->>'kaynak' {case} ELSE NULL END) "
               "FROM ingestion_batches b WHERE b.id = s.batch_id AND s.kaynak IS NULL AND b.format_json->>'kaynak' IS NOT NULL")
    op.execute("ALTER TABLE scada_hourly ADD COLUMN IF NOT EXISTS kaynak_damga_tipi TEXT")
    op.execute("ALTER TABLE scada_hourly DROP CONSTRAINT IF EXISTS scada_hourly_kaynak_check")
    op.execute("ALTER TABLE scada_hourly ADD CONSTRAINT scada_hourly_kaynak_check CHECK (kaynak IS NULL OR kaynak IN ('scada_dosya','epias','canli','bulut','elle'))")
    op.execute("ALTER TABLE scada_hourly DROP CONSTRAINT IF EXISTS scada_hourly_damga_check")
    op.execute("ALTER TABLE scada_hourly ADD CONSTRAINT scada_hourly_damga_check CHECK (kaynak_damga_tipi IS NULL OR kaynak_damga_tipi IN ('aralik_basi','aralik_sonu','anlik'))")
    # flag sözlüğü kısıtı: önce NOT VALID (yeni satırlar denetlenir), sonra mevcut veri doğrulanır; sözlük dışı değer varsa NOT VALID kalır
    op.execute("ALTER TABLE scada_hourly DROP CONSTRAINT IF EXISTS scada_hourly_flag_check")
    op.execute("ALTER TABLE scada_hourly ADD CONSTRAINT scada_hourly_flag_check CHECK (flag IN ({})) NOT VALID".format(", ".join(f"'{f}'" for f in FLAGLAR)))
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TABLE scada_hourly VALIDATE CONSTRAINT scada_hourly_flag_check; "
        "EXCEPTION WHEN check_violation THEN "
        "  RAISE NOTICE 'scada_hourly.flag: sözlük dışı eski değer var — kısıt NOT VALID kaldı (yeni satırlar denetlenir); değerler: %', "
        "    (SELECT string_agg(DISTINCT flag, ', ') FROM scada_hourly WHERE flag NOT IN ({})); "
        "END $$;".format(", ".join(f"'{f}'" for f in FLAGLAR)))
    op.execute("ALTER TABLE jobs_log ADD COLUMN IF NOT EXISTS sonuc_json JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE jobs_log DROP COLUMN IF EXISTS sonuc_json")
    op.execute("ALTER TABLE scada_hourly DROP CONSTRAINT IF EXISTS scada_hourly_flag_check")
    op.execute("ALTER TABLE scada_hourly DROP CONSTRAINT IF EXISTS scada_hourly_damga_check")
    op.execute("ALTER TABLE scada_hourly DROP CONSTRAINT IF EXISTS scada_hourly_kaynak_check")
    for ad, _ in reversed(YENI_SUTUNLAR):
        op.execute(f"ALTER TABLE scada_hourly DROP COLUMN IF EXISTS {ad}")
