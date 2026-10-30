"""04 #14 (v2.511) — toplayıcı/GTŞ portföyünde KÜPST UEVÇB bazında: üyelerin program ve gerçekleşeni toplanır, sapma brüt (14907 Md.1(3)),
KÜPSM = max(|ΣG − ΣK| − m·ΣK, 0), KÜPST = KÜPSM·max(750, PTF, SMF)·n (m 0,25 / n 0,01, 1.11.2026'dan; öncesi hesaplanamaz).
Santrallere dağılım anahtarı sözleşmeseldir (mevzuatta tanımsız): sapma | uretim | kurulu | esit; Σ üye = UEVÇB."""
import numpy as np
import pandas as pd
import pytest

from pvquant.ext.turkiye import dengesizlik as d

IST = "Europe/Istanbul"


def _idx(gun: str, n=3):
    return pd.date_range(pd.Timestamp(f"{gun} 10:00", tz=IST), periods=n, freq="h").tz_convert("UTC")


def _veri(gun="2026-11-05"):
    i = _idx(gun)
    K = {"a": pd.Series([10.0, 10.0, 10.0], index=i), "b": pd.Series([10.0, 10.0, 10.0], index=i)}
    G = {"a": pd.Series([13.0, 10.0, 18.0], index=i), "b": pd.Series([7.0, 10.0, 10.0], index=i)}
    P = pd.Series([3400.0] * 3, index=i); S = pd.Series([3400.0] * 3, index=i)
    return i, K, G, P, S


def test_uevcb_toplaminda_netlesen_sapma_ve_tutar():
    i, K, G, P, S = _veri()
    r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"})
    u = r["uevcbler"]["U1"]["saatlik"]
    assert list(u["udups"]) == [0.0, 0.0, 8.0]                      # saat 0: +3 ve −3 toplamda sıfırlanır
    assert list(u["kupsm"]) == [0.0, 0.0, 3.0]                      # 8 − 0,25·20
    assert u["kupst"].iloc[2] == pytest.approx(3.0 * 3400.0 * 0.01)  # 102 TL
    assert u["durum"].iloc[2] == "ok" and float(u["m"].iloc[0]) == 0.25 and float(u["n"].iloc[0]) == 0.01
    # tek başına hesaplansaydı saat 0'da iki santral de KÜPSM taşırdı (|3| − 0,25·10 = 0,5): UEVÇB toplamı daha düşük
    assert float(u["kupst"].sum()) < 2 * 0.5 * 3400.0 * 0.01 + float(u["kupst"].iloc[2])


def test_dagitim_anahtarlari_toplami_uevcb():
    i, K, G, P, S = _veri()
    for anahtar in d.PORTFOY_ANAHTARLARI:
        r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"}, kurulu_guc={"a": 12.0, "b": 4.0}, dagitim_anahtari=anahtar)
        g = r["uevcbler"]["U1"]; top = g["saatlik"]["kupst"]
        toplam = sum(g["uyeler"][ad]["kupst"] for ad in g["uyeler"])
        assert np.allclose(toplam.values, top.values)
        assert np.allclose((g["uyeler"]["a"]["pay"] + g["uyeler"]["b"]["pay"]).values, 1.0)
    r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"}, dagitim_anahtari="sapma")
    assert r["uevcbler"]["U1"]["uyeler"]["a"]["kupst"].iloc[2] == pytest.approx(102.0) and r["uevcbler"]["U1"]["uyeler"]["b"]["kupst"].iloc[2] == 0.0
    r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"}, dagitim_anahtari="esit")
    assert r["uevcbler"]["U1"]["uyeler"]["a"]["kupst"].iloc[2] == pytest.approx(51.0)
    r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"}, kurulu_guc={"a": 12.0, "b": 4.0}, dagitim_anahtari="kurulu")
    assert r["uevcbler"]["U1"]["uyeler"]["a"]["kupst"].iloc[2] == pytest.approx(76.5)
    assert "mevzuatta tanımsız" in r["etiket"]
    with pytest.raises(ValueError):
        d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"}, dagitim_anahtari="yok")


def test_gruplama_ve_bos_kod():
    i, K, G, P, S = _veri()
    K["c"] = K["a"].copy(); G["c"] = G["a"].copy()
    r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1", "c": ""})
    assert set(r["uevcbler"]) == {"U1", d.UEVCB_TANIMSIZ} and r["uevcbler"][d.UEVCB_TANIMSIZ]["uyeler"].keys() == {"c"}
    assert r["uevcbler"][d.UEVCB_TANIMSIZ]["saatlik"]["kupst"].iloc[0] == pytest.approx((3.0 - 2.5) * 3400.0 * 0.01)   # tek santral: |13−10| − 0,25·10


def test_1_11_2026_oncesi_hesaplanamaz():
    i, K, G, P, S = _veri("2026-10-05")
    r = d.portfoy_kupst_saatlik(K, G, P, S, uevcb={"a": "U1", "b": "U1"})
    u = r["uevcbler"]["U1"]["saatlik"]
    assert u["kupst"].isna().all() and (u["durum"] == "kupst_hesaplanamaz").all()
    assert "belirsiz" in r["uevcbler"]["U1"]["kural_dayanak"]
