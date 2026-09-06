"""v2.275 — toplayıcı çıktısı (saatlik/15 dk, enerji korunur), EAK etkin kuralı, KÜPST katsayıları, kapılar."""
import io
from datetime import date

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import toplayici_service as ts
from pvquant.services import dengesizlik_service as dz
from pvquant.services.kgup_service import eak_etkin

LAT, LON = 37.87, 32.49


def _df():
    ix = pd.date_range("2026-09-06 21:00", periods=30, freq="h", tz="UTC")     # İstanbul 7 Eyl 00:00'dan
    cs = np.clip(3000 * np.sin(np.pi * (ix.tz_convert("Europe/Istanbul").hour - 5) / 14), 0, None)
    return pd.DataFrame({"p50_kw": cs, "p10_kw": cs * 0.9, "p90_kw": cs * 1.1}, index=ix)


def test_tablo_saatlik_ve_15dk():
    t = ts.tablo_uret(_df(), date(2026, 9, 7), "UEVCB1", 3.6, LAT, LON, 60)
    assert len(t) == 24 and list(t.columns) == ["Tarih", "Saat", "UEVCB", "P10_MW", "P50_MW", "P90_MW", "EAK_MW"]
    assert t["P50_MW"].max() <= 3.6 and t["Tarih"].iloc[0] == "07.09.2026" and t["Saat"].iloc[0] == 0
    q = ts.tablo_uret(_df(), date(2026, 9, 7), "UEVCB1", 3.6, LAT, LON, 15)
    assert len(q) == 96 and "Ceyrek" in q and set(q["Ceyrek"]) == {0, 15, 30, 45}
    # enerji korunur: 15 dk ortalamalarının saatlik ortalaması ≈ saatlik değer (tavan kırpması hariç saatlerde)
    saat = q.groupby("Saat")["P50_MW"].mean(); h = t.set_index("Saat")["P50_MW"]
    m = h < 3.5
    assert np.allclose(saat[m].values, h[m].values, rtol=0.02)
    with pytest.raises(ValueError):
        ts.tablo_uret(_df().iloc[:5], date(2026, 9, 7), "U", 3.6, LAT, LON, 60)
    assert list(ts.eslesme_uygula(t, {"P50_MW": "Forecast", "yok": "x"}).columns)[4] == "Forecast"
    icerik, mime, uz = ts.dosya(t, "xlsx"); assert uz == "xlsx" and len(icerik) > 1000
    csv = ts.dosya(t, "csv")[0].decode("utf-8-sig"); assert csv.splitlines()[0] == "Tarih;Saat;UEVCB;P10_MW;P50_MW;P90_MW;EAK_MW" and "," in csv.splitlines()[8]


def test_eak_etkin():
    p = {"capacity_kwp": 4514.0, "ac_limit_kw": 3600.0, "params_json": {}}
    assert eak_etkin(p, date(2026, 9, 7)) == {"eak_mw": 3.6, "kaynak": "ac_tavani"}
    p["params_json"] = {"eak_kw": 3000}
    assert eak_etkin(p, date(2026, 9, 7))["kaynak"] == "eak_alani"
    p["params_json"] = {"eak_kw": 3000, "eak_gecici": {"kw": 1500, "bitis": "2026-09-10"}}
    assert eak_etkin(p, date(2026, 9, 7)) == {"eak_mw": 1.5, "kaynak": "gecici", "bitis": "2026-09-10"}
    assert eak_etkin(p, date(2026, 9, 11))["kaynak"] == "eak_alani"          # bitiş geçti
    assert eak_etkin({"capacity_kwp": 1000.0, "params_json": '{"eak_kw": 5000}'}, date(2026, 1, 1))["eak_mw"] == 1.0   # kurulu gücü aşamaz


def test_kupst_katsayilari():
    k = dz.katsayilar({"segment": "lisansli_serbest"})
    assert k.kupst_n == 0.03 and k.kupst_tolerans == 0.10 and k.kupst_kgup_yukumlu
    assert dz.katsayilar({"segment": "lisanssiz_dagitim"}).kupst_n == 0.0
    assert dz.katsayilar({"segment": "lisansli_yekdem", "kupst_n": 0.05, "kupst_tolerans": 0.08}).kupst_n == 0.05
    assert dz.katsayilar(None).kupst_n == 0.0
    # KÜPST toleransın ÜSTÜNDEKİ sapmadan hesaplanır
    ix = pd.date_range("2026-08-01", periods=3, freq="h", tz="UTC")
    fiyat = pd.DataFrame({"ptf": 2000.0, "smf": 2500.0, "kaynak": "senaryo"}, index=ix)
    df = pd.DataFrame({"ts_utc": ix, "gercek_kw": [1000.0, 1000.0, 1000.0], "kgup_kw": [1000.0, 1050.0, 1500.0], "naif_kw": np.nan})
    r = dz.hesapla_df(df, fiyat, dz.katsayilar({"segment": "lisansli_serbest"}))
    assert r["toplam"]["kupst_tl"] == round((0.5 - 0.1 * 1.5) * 2500 * 0.03, 0) and r["katsayilar"]["kupst_tolerans"] == 0.1


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 4514.0, "ac_limit_kw": 3600.0, "lat": LAT, "lon": LON, **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {**depo["params_json"], **k}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    monkeypatch.setattr(ts, "uret", lambda t, plant, g, fmt, adim: {"icerik": b"x;y", "mime": "text/csv", "dosya_adi": f"T_{g}_{adim}.{fmt}"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    j = istemci.put("/v1/plants/p1/eak", json={"eak_kw": 3000, "gecici_kw": 1500, "gecici_bitis": "2099-01-01"}).json()
    assert j["eak_bugun"]["kaynak"] == "gecici" and j["eak_kw"] == 3000.0
    assert istemci.put("/v1/plants/p1/eak", json={"eak_kw": 9000}).status_code == 422
    t = istemci.put("/v1/plants/p1/eak", json={"gecici_kw": None, "gecici_bitis": None}).json()      # null = temizle
    assert t["eak_gecici"] is None and t["eak_bugun"]["kaynak"] == "eak_alani" and t["eak_kw"] == 3000.0
    assert istemci.put("/v1/plants/p1/eak", json={"eak_kw": None}).json()["eak_bugun"]["kaynak"] == "ac_tavani"
    y = istemci.get("/v1/plants/p1/toplayici?fmt=csv&adim=15&gun=2026-09-07")
    assert y.status_code == 200 and "T_2026-09-07_15.csv" in y.headers["content-disposition"]
    assert istemci.get("/v1/plants/p1/toplayici?fmt=pdf").status_code == 422
