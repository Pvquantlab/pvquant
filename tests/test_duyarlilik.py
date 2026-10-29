"""v2.508 (04 #2) — WMAPE duyarlılığı: hata deseni ölçekleme (kırpma yoksa hedef = elde), gerçek seviye satırı, maliyet tekdüze artar,
C iş kolu girdisiyle W15 programı kendi seviyesine ölçeklenince T1 W15 toplamı birebir; maliyet_geri_test_df çıktısına «duyarlilik» eklendi."""
import numpy as np
import pandas as pd

from pvquant.services import backtest_service as bt

IST = "Europe/Istanbul"


def _veri(n_gun=10, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-06-01", periods=24 * n_gun, freq="h", tz="UTC")
    saat = idx.tz_convert(IST).hour.values
    prof = np.clip(np.sin((saat - 5) / 14 * np.pi), 0, None) * 8000.0          # kW, 8 MW tepe
    ger = prof * (1 + 0.05 * rng.standard_normal(len(idx))); ger = np.clip(ger, 0, None)
    hata = 0.12 * prof * rng.standard_normal(len(idx))
    df = pd.DataFrame({"ts_utc": idx, "gercek_kw": ger, "kgup_kw": np.clip(ger - hata, 0, 9000), "naif_kw": np.nan})
    fiyat = pd.DataFrame({"ptf": 2400.0, "smf": 2600.0, "yon": "acik", "kaynak": "epias"}, index=idx)
    return df, fiyat


def test_duyarlilik_olcekleme_ve_tekduzelik():
    df, fiyat = _veri()
    d = bt.wmape_duyarlilik_df(df, fiyat, segment="lisansli_serbest", kurulu_guc_mw=12.0)
    assert d is not None and d["wmape_gercek"] > 0
    sev = d["seviyeler"]; hedefler = [r["wmape_hedef"] for r in sev]
    assert hedefler == sorted(hedefler) and sum(r["gercek"] for r in sev) == 1
    for r in sev:
        assert abs(r["wmape_elde"] - r["wmape_hedef"]) < 0.6           # kırpma payı
    toplamlar = [r["toplam_tl"] for r in sev]
    assert all(b >= a for a, b in zip(toplamlar, toplamlar[1:]))        # hata büyüdükçe kalemler artar
    gercek = next(r for r in sev if r["gercek"])
    g = bt.maliyet_geri_test_df(df, fiyat, segment="lisansli_serbest", kurulu_guc_mw=12.0)
    assert g["duyarlilik"] is not None and abs(gercek["toplam_tl"] - g["toplam"]["toplam_tl"]) <= 2   # gerçek satır = geri test toplamı
    # sıfır hata → None (ölçeklenecek desen yok)
    df0 = df.copy(); df0["kgup_kw"] = df0["gercek_kw"]
    assert bt.wmape_duyarlilik_df(df0, fiyat, segment="lisansli_serbest") is None


def test_c_w15_kendi_seviyesi_birebir():
    """C fixture: W15 programı kendi WMAPE'sine ölçeklenince program değişmez → toplam, T1 W15 (911.844 TL, hedef 12 ay yıllaştırılmış) ile aynı
    motor yolundan geçer; burada yalnız ölçeklemenin kimlik olduğunu doğrularız (saatlik toplam fark < 1 TL)."""
    import os
    yol = os.path.join(os.path.dirname(__file__), "data", "c_geri_test_senaryolar.csv")
    c = pd.read_csv(yol)
    c = c[c["seg"].astype(str).ge("2025-10b") | c["seg"].astype(str).str.startswith("2026")].head(24 * 60)
    idx = pd.to_datetime(c["tarih"].astype(str) + " " + c["saat"].astype(int).astype(str) + ":00").dt.tz_localize(IST).dt.tz_convert("UTC")
    ix = pd.DatetimeIndex(idx)
    df = pd.DataFrame({"ts_utc": ix, "gercek_kw": c["A"].values * 1000.0, "kgup_kw": c["F15"].values * 1000.0, "naif_kw": np.nan})
    fiyat = pd.DataFrame({"ptf": c["PTF"].values, "smf": c["SMF"].values, "yon": c["yon"].values, "kaynak": "epias"}, index=ix)
    w0 = bt.wmape_pct(pd.Series(c["F15"].values), pd.Series(c["A"].values))
    d = bt.wmape_duyarlilik_df(df, fiyat, segment="lisansli_serbest", seviyeler=(round(w0, 2),))
    g = bt.maliyet_geri_test_df(df, fiyat, segment="lisansli_serbest")
    gercek = next(r for r in d["seviyeler"] if r["gercek"])
    assert abs(gercek["toplam_tl"] - g["toplam"]["toplam_tl"]) <= 1 and abs(gercek["wmape_elde"] - w0) < 0.05
