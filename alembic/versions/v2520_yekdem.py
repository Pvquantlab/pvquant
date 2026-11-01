"""v2.520 (P5a) — YEKDEM fiyat verisi: doviz_kuru (TCMB gösterge döviz alış kuru, gün bazında; Cetvel I YEK fiyatı ABD senti/kWh × enerjinin
sisteme verildiği günün kuru — 5346 m.3(1)(16), YEK Yön. m.3(1)(dd)) ve yekdem_fiyat (7189 sayılı CK kapsamındaki tesisler için EPİAŞ'ın
her ay ilan ettiği TL kuruş/kWh fiyatı ve yerli katkı; tesis tipi bazında). İkisi de kamuya açık, kiracısız (RLS yok) sistem tabloları —
piyasa_fiyat (v2258) kalıbı. Tohum: EPİAŞ 01.10.2026 duyurusu (Ağustos–Ekim 2026 güneş ve bütünleşik depolamalı; yerli aksam desteği güneş).
Kasım 2026 ilanı 31.10.2026 taramasında BULUNAMADI — platform yönetimi /v1/yonetim/yekdem-fiyat ile girer.

Revision ID: v2520_yekdem
Revises: v2513_kgup_surum_eak
"""
from alembic import op

revision = "v2520_yekdem"
down_revision = "v2513_kgup_surum_eak"
branch_labels = None
depends_on = None

KAYNAK = "EPİAŞ duyurusu 01.10.2026 (7189 sayılı CK Ek-2 aylık güncelleme)"
TOHUM = [   # (ay, tesis_tipi, fiyat_kr_kwh, yerli_katki_kr_kwh) — depolamalı yerli katkı duyuruda ayrı satır yok → NULL
    ("2026-08-01", "gunes", 278.92, 75.80), ("2026-09-01", "gunes", 284.81, 77.40), ("2026-10-01", "gunes", 289.74, 78.74),
    ("2026-08-01", "gunes_depolamali", 328.98, None), ("2026-09-01", "gunes_depolamali", 335.93, None), ("2026-10-01", "gunes_depolamali", 341.74, None),
]


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS doviz_kuru ("
        " gun date PRIMARY KEY,"
        " usd_alis double precision NOT NULL,"
        " eur_alis double precision,"
        " bulten text,"
        " kaynak text NOT NULL DEFAULT 'tcmb',"
        " guncelleme timestamptz NOT NULL DEFAULT now())"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON doviz_kuru TO pvq_app")
    op.execute(
        "CREATE TABLE IF NOT EXISTS yekdem_fiyat ("
        " ay date NOT NULL,"
        " tesis_tipi text NOT NULL CHECK (tesis_tipi IN ('gunes', 'gunes_depolamali')),"
        " fiyat_kr_kwh double precision NOT NULL,"
        " yerli_katki_kr_kwh double precision,"
        " kaynak text,"
        " guncelleme timestamptz NOT NULL DEFAULT now(),"
        " PRIMARY KEY (ay, tesis_tipi))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON yekdem_fiyat TO pvq_app")
    for ay, tip, fiyat, yerli in TOHUM:
        op.execute(f"INSERT INTO yekdem_fiyat(ay, tesis_tipi, fiyat_kr_kwh, yerli_katki_kr_kwh, kaynak) "
                   f"VALUES ('{ay}', '{tip}', {fiyat}, {'NULL' if yerli is None else yerli}, '{KAYNAK}') ON CONFLICT (ay, tesis_tipi) DO NOTHING")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS yekdem_fiyat")
    op.execute("DROP TABLE IF EXISTS doviz_kuru")
