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


def test_json_dosya_insan_diliyle_reddedilir(tmp_path):
    """v2.369 — bulgu 20 (T8 canlı): FusionSolar JSON'u (.csv kılığında bile)
    boş kolonlu çıkışsız sihirbaza değil, açık Türkçe redde gider."""
    import pytest

    y = tmp_path / "huawei.csv"
    y.write_text('{"success": true, "data": [{"dataItemMap": {"inverter_power": 18330}}]}',
                 encoding="utf-8")
    with pytest.raises(ValueError, match="JSON görünüyor"):
        detect_file_format(y)


def test_json_onizleme_ucu_422_mesajla(tmp_path, monkeypatch):
    """Önizleme ucu JSON'da yapılandırılmış sihirbaz değil düz 422 mesaj döner."""
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici

    api_main.app.dependency_overrides[gecerli_kullanici] = (
        lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0})
    monkeypatch.setattr(api_main.plant_service, "getir",
                        lambda t, p: {"tz": "Europe/Istanbul", "capacity_kwp": 1000.0,
                                      "lat": 37.0, "lon": 35.0})
    try:
        y = c_dosya = {"dosya": ("h.csv", b'{"success": true, "data": []}', "text/csv")}
        c = TestClient(api_main.app)
        r = c.post("/v1/plants/p1/scada/preview", files=c_dosya)
        assert r.status_code == 422
        assert "JSON görünüyor" in r.json()["detail"]
    finally:
        api_main.app.dependency_overrides.clear()


def test_iso_tarihli_adsiz_kolon_gunfirst_tuzagina_dusmez(tmp_path):
    """v2.370 — Growatt PVDAQ (T9 ön-sınavı): ISO tarihli adsız zaman kolonu
    dayfirst=True ile ayın 13'ünden sonrası NaT olup yedeği düşürüyordu;
    çözüm transform'un iki-adaylı sağlam çözücüsü. Günlük özette donmuş-değer
    kuralı da koşmaz (eşit günlük tepeler arıza değildir)."""
    satirlar = [",ac_power_inv_1_daily_max,ac_energy_inv_1_daily_sum"]
    for g in range(1, 29):
        satirlar.append(f"2024-01-{g:02d},{2.0},{8.0}")   # eşit tepeler: frozen tetiklemesin
    y = tmp_path / "growatt.csv"
    y.write_text("\n".join(satirlar), encoding="utf-8")
    r = ingest_file(y, capacity_kwp=4.0, latitude=34.0, longitude=-118.0,
                    source_timezone="America/Los_Angeles")
    assert r.mapping.timestamp == "Unnamed: 0"
    assert len(r.data) == 28                      # ayın 13'ünden sonrası da çözüldü
    bayraklar = set(r.data["flag"])
    assert bayraklar == {"gunluk_ozet"}           # frozen/night yok


def test_oran_sezgisi_birim_donusumu_karnede_soylenir(tmp_path):
    """v2.371 — bulgu 21 (T9 canlı): kapasite yanlış girilince MW varsayımı
    sessizce zinciri şişiriyordu; oran-sezgisi dönüşümü artık karneye yazılır."""
    satirlar = ["time,ac_power"]
    for g in range(1, 11):
        for h in (9, 12, 15):
            satirlar.append(f"2024-06-{g:02d} {h:02d}:00,2.1")   # ~2 kW ama kapasite 1000
    y = tmp_path / "sisik.csv"
    y.write_text("\n".join(satirlar), encoding="utf-8")
    r = ingest_file(y, capacity_kwp=1000.0, latitude=37.0, longitude=35.0,
                    source_timezone="Europe/Istanbul")
    assert r.transform.power_unit == "MW" and r.transform.power_unit_source == "oran"
    assert any("MW varsayılıp" in u for u in r.report.warnings)
