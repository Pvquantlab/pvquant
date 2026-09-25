"""v2.366 — bulgu 15: SMA Sunny Explorer ailesi (çok satırlı cihaz başlığı).

Canlıda ölçülen üç kusur: (1) ilk VERİ satırı başlık seçilip 1 Mayıs sessizce
yutuluyordu; (2) örneklemdeki boş satır pandas'ın skip_blank_lines
numaralandırmasıyla çakışıp indeksleri kaydırıyordu; (3) self-healing'de
'kWh;kWh' birim satırı varyantı 'kwh' birebir eşleşmesiyle ad satırını
yeniyordu (pandas kopya adı 'kWh.1' eleği atlatıyordu).
"""
from pvquant.io.ingestion.detection import detect_file_format, ilan_edilen_bicim
from pvquant.io.ingestion.pipeline import ingest_file

SMA_GOVDE = "\r\n".join([
    "sep=;",
    "Version CSV1|Tool SE|Linebreaks CR/LF|Delimiter semicolon|Decimalpoint dot|Precision 3",
    "",
    ";SN: 2130269553;SN: 2130269553",
    ";SB 4000TL-21;SB 4000TL-21",
    ";2130269553;2130269553",
    ";Total yield;Day yield",
    ";Counter;Analog",
    "dd/MM/yyyy;kWh;kWh",
    "01/05/2016;7510.496;6.423",
    "02/05/2016;7523.845;13.349",
    "03/05/2016;7530.578;6.733",
    "04/05/2016;7541.870;11.292",
    "",
])


def _yaz(tmp_path):
    yol = tmp_path / "sma.csv"
    yol.write_bytes("﻿".join(["", SMA_GOVDE]).encode("utf-16-le"))
    return yol


def test_ilan_edilen_bicim_okunur():
    ayrac, ondalik = ilan_edilen_bicim(SMA_GOVDE.split("\r\n"))
    assert ayrac == ";" and ondalik == "."


def test_baslik_ad_satiridir_veri_satiri_degil(tmp_path):
    f = detect_file_format(_yaz(tmp_path))
    assert f.encoding == "utf-16"
    assert f.delimiter == ";" and f.decimal == "."
    # boşluksuz numaralandırmada ad satırı ('';Total yield;Day yield) 5. indeks
    assert f.header_row == 5


def test_uctan_uca_ilk_gun_yutulmaz_sayac_farklanir(tmp_path):
    r = ingest_file(_yaz(tmp_path), capacity_kwp=4.0, latitude=41.0,
                    longitude=29.0, source_timezone="Europe/Istanbul")
    assert r.mapping.timestamp == "Unnamed: 0"     # içerik yedeği (adsız tarih kolonu)
    assert r.mapping.energy == "Total yield"       # ad satırı kazandı, birim satırı değil
    assert len(r.data) == 4                        # 1 Mayıs dahil — yutulmadı
    d = r.data.reset_index()
    # kümülatif sayaç farklandı: 2-4 Mayıs = Day yield ile birebir
    assert abs(float(d["energy_kwh"].iloc[1]) - 13.349) < 0.01
    assert abs(float(d["energy_kwh"].sum()) - (13.349 + 6.733 + 11.292)) < 0.05


def test_gunluk_ozet_bayragi_ve_uyarisi(tmp_path):
    """v2.367 — bulgu 16: günlük-adımlı dosya saatlik karneye 'geçerli' diye
    sızmaz. Satırlar 'gunluk_ozet' bayrağını alır, gece-üretimi kuralı bu
    dosyada koşmaz (gün toplamı gece damgasında tz iması yanlış olur), karne
    açık uyarı taşır."""
    r = ingest_file(_yaz(tmp_path), capacity_kwp=4.0, latitude=41.0,
                    longitude=29.0, source_timezone="Europe/Istanbul")
    bayraklar = set(r.data["flag"])
    assert "gunluk_ozet" in bayraklar and "valid" not in bayraklar
    assert "night_production" not in bayraklar
    assert any("günlük ÖZET" in u for u in r.report.warnings)
    assert r.report.n_rows_valid == 0            # saatlik anlamda geçerli yok


def test_gunluk_ozet_aylik_toplama_girer():
    """scada_oku(gunluk_dahil=True) → aylik_ozet zinciri günlük satırları sayar."""
    import pandas as pd

    from pvquant.services.ingest_service import aylik_ozet
    idx = pd.date_range("2016-05-01 21:00", periods=30, freq="D", tz="UTC")
    df = pd.DataFrame({"power_kw": [None] * 30, "energy_kwh": [10.0] * 30}, index=idx)
    out = aylik_ozet(df, tz="Europe/Istanbul")
    assert abs(float(out[out.ay == "2016-05"]["uretim_mwh"].iloc[0]) - 0.29) < 0.02
