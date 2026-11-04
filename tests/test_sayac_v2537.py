"""v2.537 — Sayaç sayfası doğrulama turu (04.11 brifi): SCADA ↔ sayaç kıyasında payda ve kapsam (kısmi gün, eksik saat, tahmini/elle değer),
yüzde tanımı, çok günlü pencere; sayıların birbirine bağlı kimlikleri."""
from datetime import datetime, timezone

import pandas as pd

from pvquant.services import sayac_service as ss


def _idx(bas, n):
    return pd.date_range(bas, periods=n, freq="h", tz="UTC")


def test_kismi_gun_payda_yalniz_ortak_saatler():
    """SCADA 24 saat, sayaç 18 saat: günlük fark ve yüzde yalnız 18 ortak saatin toplamlarıyla; saat_scada/saat_sayac ayrı sayılır."""
    idx = _idx(datetime(2026, 10, 9, 21, tzinfo=timezone.utc), 24)   # 10 Ekim TSİ 00:00–23:00
    scada = pd.DataFrame({"kwh": 100.0, "flag": "valid", "kaynak": "scada_dosya"}, index=idx)
    sayac = pd.DataFrame({"veris_kwh": 97.0, "nitelik": "olculmus", "kaynak": "osos"}, index=idx[:18])
    f = ss.fark_df(scada, sayac).iloc[0]
    assert f["gun"] == "2026-10-10" and f["saat_scada"] == 24 and f["saat_sayac"] == 18 and f["saat_ortak"] == 18
    assert f["scada_kwh"] == 2400 and f["sayac_kwh"] == 18 * 97 and f["ortak_scada_kwh"] == 1800 and f["ortak_sayac_kwh"] == 18 * 97
    assert f["fark_kwh"] == -54.0 and f["fark_pct"] == -3.0 and f["olc_fark_pct"] == -3.0       # payda ortak SCADA (1800), günlük SCADA (2400) değil


def test_tahmini_ve_elle_saatler_olculmus_karsilastirmaya_girmez():
    idx = _idx(datetime(2026, 10, 1, 5, tzinfo=timezone.utc), 5)
    scada = pd.DataFrame({"kwh": [100.0, 100.0, 100.0, 100.0, 100.0], "flag": "valid", "kaynak": "scada_dosya"}, index=idx)
    sayac = pd.DataFrame({"veris_kwh": [90.0, 50.0, 95.0, 20.0, 97.0], "nitelik": ["olculmus", "tahmini", "olculmus", "elle", "doldurulmus"], "kaynak": "osos"}, index=idx)
    f = ss.fark_df(scada, sayac).iloc[0]
    assert f["saat_ortak"] == 5 and f["saat_tahmini"] == 2 and f["saat_olculmus"] == 2             # elle ne tahmini ne ölçülmüş sayılır
    assert f["fark_pct"] == round((352 - 500) / 500 * 100, 1) and f["olc_fark_pct"] == round((185 - 200) / 200 * 100, 1)


def test_sifir_scada_yuzde_vermez_ve_bos_taraf():
    assert ss._kiyas(0.0, 10.0, 3)["fark_pct"] is None and ss._kiyas(None, None, 0)["saat"] == 0
    idx = _idx(datetime(2026, 10, 1, 5, tzinfo=timezone.utc), 3)
    scada = pd.DataFrame({"kwh": 0.0, "flag": "valid", "kaynak": "scada_dosya"}, index=idx)     # gece: SCADA 0
    sayac = pd.DataFrame({"veris_kwh": 0.0, "nitelik": "olculmus", "kaynak": "osos"}, index=idx)
    f = ss.fark_df(scada, sayac).iloc[0]
    assert f["saat_ortak"] == 3 and f["fark_kwh"] == 0.0 and pd.isna(f["fark_pct"])


def test_cok_gunlu_pencere_kimlikleri():
    """3 gün: 1. gün tam, 2. gün yalnız SCADA, 3. gün yalnız sayaç → kapsam sayıları birbirini tamamlar."""
    g1 = _idx(datetime(2026, 10, 4, 21, tzinfo=timezone.utc), 24); g2 = _idx(datetime(2026, 10, 5, 21, tzinfo=timezone.utc), 24); g3 = _idx(datetime(2026, 10, 6, 21, tzinfo=timezone.utc), 24)
    scada = pd.DataFrame({"kwh": 50.0, "flag": "valid", "kaynak": "scada_dosya"}, index=g1.append(g2))
    sayac = pd.DataFrame({"veris_kwh": 48.0, "nitelik": "olculmus", "kaynak": "epys"}, index=g1.append(g3))
    f = ss.fark_df(scada, sayac)
    assert list(f["gun"]) == ["2026-10-05", "2026-10-06", "2026-10-07"]
    assert list(f["saat_ortak"]) == [24, 0, 0] and list(f["saat_scada"]) == [24, 24, 0] and list(f["saat_sayac"]) == [24, 0, 24]
    assert f.loc[0, "fark_pct"] == -4.0 and pd.isna(f.loc[1, "fark_pct"]) and pd.isna(f.loc[2, "fark_pct"])
    ortak = int(f["saat_ortak"].sum()); yalniz_scada = int(f["saat_scada"].sum()) - ortak; yalniz_sayac = int(f["saat_sayac"].sum()) - ortak
    assert (ortak, yalniz_scada, yalniz_sayac) == (24, 24, 24)
