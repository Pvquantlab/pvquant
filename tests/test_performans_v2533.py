"""04.11.2026 v2.533 (P8a performans katmanı I): gerçekleşen kayıp ayrışımı (kWh/TL/EPI), PR'da kırpma işareti, kullanılabilirlik sözleşme eşiği."""
import numpy as np
import pandas as pd

from pvquant.services import kayip_ayrisimi_service as ka
from pvquant.services import kullanilabilirlik_service as ks
from pvquant.services.pr_service import pr_hesapla

CAP = 5000.0


def _df(gun=3):
    ts = pd.date_range("2026-10-20", periods=24 * gun, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour + 3 - 6) / 12 * np.pi), 0, None)          # İstanbul güneşi
    bek = CAP * 0.8 * g
    guc = bek * 0.95                                                      # %5 açıklanmayan sapma
    df = pd.DataFrame({"ts_utc": ts, "beklenen_kw": bek, "power_kw": guc, "flag": "valid", "kirpma": False})
    return df


def test_kayip_ayrisimi_nedenler_kwh_tl_epi():
    df = _df()
    ts = df["ts_utc"]
    # 1. gün 09–11 UTC: olay kaydı talimat (üretim 0); 2. gün 09 UTC: şebeke kısıtı bayrağı (üretim yarı); 2. gün 10–11: kırpma; 3. gün 09: otomatik arıza; 3. gün 10: satır yok
    g1 = ts.dt.day == 20; g2 = ts.dt.day == 21; g3 = ts.dt.day == 22
    df.loc[g1 & ts.dt.hour.isin([9, 10]), "power_kw"] = 0.0
    df.loc[g2 & (ts.dt.hour == 9), ["flag", "power_kw"]] = ["kisinti", 1000.0]
    df.loc[g2 & ts.dt.hour.isin([10, 11]), "kirpma"] = True
    df.loc[g3 & (ts.dt.hour == 9), "power_kw"] = 0.0
    df.loc[g3 & (ts.dt.hour == 10), "power_kw"] = np.nan
    olay = {pd.Timestamp("2026-10-20 09:00", tz="UTC"): "talimat", pd.Timestamp("2026-10-20 10:00", tz="UTC"): "talimat"}
    fiyat = pd.Series(2000.0, index=pd.DatetimeIndex(ts))                   # 2.000 TL/MWh
    r = ka.hesapla_df(df, CAP, olay, fiyat)
    assert r["durum"] == "ok"
    s = {x["neden"]: x for x in r["satirlar"]}
    assert s["talimat"]["saat"] == 2 and s["talimat"]["kpi_disi"] is True and s["talimat"]["kayip_kwh"] > 0
    assert abs(s["talimat"]["kayip_tl"] - s["talimat"]["kayip_kwh"] / 1000 * 2000) < 1.0
    assert s["kisinti"]["saat"] == 1 and s["kirpma"]["saat"] == 2 and s["kirpma"]["kayip_kwh"] is None and "AC sınırı" in s["kirpma"]["not"]
    assert s["ariza_otomatik"]["saat"] == 1 and s["ariza_otomatik"]["kpi_disi"] is False
    assert s["veri_yok"]["saat"] == 1 and s["veri_yok"]["kayip_kwh"] is None
    assert s["aciklanmayan"]["saat"] == r["mumkun_saat"] - 7 and s["aciklanmayan"]["kayip_kwh"] > 0 and s["aciklanmayan"]["kayip_tl"] is None
    assert r["toplam_kayip_kwh"] == round(sum(x["kayip_kwh"] for x in r["satirlar"] if x["kayip_kwh"] and x["neden"] != "aciklanmayan"), 1)   # açıklanmayan toplama girmez
    assert 0.6 < r["epi"] < 0.95 and r["fiyatsiz_saat"] == 0
    # fiyat yoksa TL yok, kWh var
    r2 = ka.hesapla_df(df, CAP, olay, None)
    assert r2["satirlar"][0]["kayip_tl"] is None and r2["toplam_kayip_tl"] == 0 and r2["fiyatsiz_saat"] > 0
    assert ka.hesapla_df(df.iloc[:30], CAP)["durum"] == "yetersiz" and ka.hesapla_df(pd.DataFrame(), CAP)["durum"] == "veri_yok"


def test_olay_saat_haritasi_oncelik():
    bas = pd.Timestamp("2026-10-20", tz="UTC"); bit = pd.Timestamp("2026-10-21", tz="UTC")
    olaylar = [{"tur": "ariza", "baslangic": pd.Timestamp("2026-10-20 08:30", tz="UTC"), "bitis": pd.Timestamp("2026-10-20 11:00", tz="UTC")},
               {"tur": "talimat_yat", "baslangic": pd.Timestamp("2026-10-20 10:00", tz="UTC"), "bitis": pd.Timestamp("2026-10-20 12:00", tz="UTC")},
               {"tur": "planli_bakim", "baslangic": pd.Timestamp("2026-10-20 23:00", tz="UTC"), "bitis": None}]      # açık olay pencere sonuna kadar
    h = ka.olay_saat_haritasi(olaylar, bas, bit)
    assert h[pd.Timestamp("2026-10-20 08:00", tz="UTC")] == "ariza_kaydi" and h[pd.Timestamp("2026-10-20 10:00", tz="UTC")] == "talimat"   # talimat kazanır
    assert h[pd.Timestamp("2026-10-20 11:00", tz="UTC")] == "talimat" and h[pd.Timestamp("2026-10-20 23:00", tz="UTC")] == "planli_bakim"
    assert pd.Timestamp("2026-10-20 12:00", tz="UTC") not in h and len(h) == 5


def _pr_df(gun=30):
    ts = pd.date_range("2026-06-01", periods=24 * gun, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour - 6) / 12 * np.pi), 0, None)
    poa = 900 * g; tm = 25 + 20 * g
    guc = CAP * poa / 1000 * 0.85 * (1 - 0.0035 * (tm - 25))
    return pd.DataFrame({"ts_utc": ts, "power_kw": guc, "poa_wm2": poa, "t_module": tm, "kirpma": False})


def test_pr_kirpma_isareti():
    d = _pr_df()
    r0 = pr_hesapla(d, CAP)
    assert r0["kirpma_saat"] == 0 and r0["PR_kirpma_disi"] == r0["PR"]
    tepe = d["ts_utc"].dt.hour.isin([11, 12, 13])
    d.loc[tepe, "power_kw"] = d.loc[tepe, "power_kw"] * 0.7; d.loc[tepe, "kirpma"] = True   # AC sınırında kırpılmış
    r = pr_hesapla(d, CAP)
    assert r["kirpma_saat"] == 90 and r["PR_kirpma_disi"] > r["PR"] and abs(r["PR_kirpma_disi"] - r0["PR"]) < 0.02
    assert pr_hesapla(d.drop(columns=["kirpma"]), CAP)["kirpma_saat"] == 0


def test_kullanilabilirlik_sozlesme_acigi(monkeypatch):
    monkeypatch.setattr(ks, "_birim_fiyat", lambda plant: (2000.0, "tarife (sabit)"))
    out = {"durum": "ok", "A_t": 0.95, "beklenen_kwh": 100000.0}
    assert ks.sozlesme_acigi({"params_json": {}}, out) is None
    r = ks.sozlesme_acigi({"params_json": {"kullanilabilirlik_sozlesme": 0.98}}, out)
    assert r["acik_puan"] == 0.03 and r["acik_kwh"] == 3000.0 and r["acik_tl"] == 6000.0 and r["fiyat_kaynak"] == "tarife (sabit)" and "alacak değildir" in r["not"]
    assert ks.sozlesme_acigi({"params_json": '{"kullanilabilirlik_sozlesme": 0.9}'}, out)["acik_puan"] == 0.0
    monkeypatch.setattr(ks, "_birim_fiyat", lambda plant: (None, "fiyat yok"))
    r2 = ks.sozlesme_acigi({"params_json": {"kullanilabilirlik_sozlesme": 0.98}}, out)
    assert r2["acik_kwh"] == 3000.0 and r2["acik_tl"] is None
    assert ks.sozlesme_acigi({"params_json": {"kullanilabilirlik_sozlesme": 0.98}}, {"durum": "yetersiz"}) is None
    # hesapla_df beklenen_kwh alanı
    ts = pd.date_range("2026-10-20", periods=72, freq="h", tz="UTC")
    df = pd.DataFrame({"ts_utc": ts, "beklenen_kw": 1000.0, "power_kw": 900.0, "flag": "valid"})
    h = ks.hesapla_df(df, CAP)
    assert h["durum"] == "ok" and h["beklenen_kwh"] == 72000.0
