"""v2.281 — kullanılabilirlik (SAF), tarife doğrulama/gelir, kayıp ağacı (pvlib, kısa sentetik yıl), şablon rapor üretimi, kapılar."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import kullanilabilirlik_service as ks, tarife_service as tsv, kayip_service as kys, sablon_rapor_service as srs


def test_kullanilabilirlik_df():
    ix = pd.date_range("2026-08-01", periods=24 * 10, freq="h", tz="UTC")
    bek = pd.Series(np.clip(3000 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None), index=ix)
    guc = bek * 0.95; guc.iloc[100:110] = 0.0                    # 10 saat sıfır üretim (gündüz) → arıza
    df = pd.DataFrame({"ts_utc": ix, "beklenen_kw": bek.values, "power_kw": guc.values, "flag": "valid"})
    df.loc[105, "flag"] = "kisinti"                               # biri kısıntı → hariç
    r = ks.hesapla_df(df, 4000.0)
    assert r["durum"] == "ok" and r["haric_saat"] == 1 and 5 <= r["ariza_saat"] <= 9 and 0.9 < r["A_t"] < 1 and 0.9 < r["A_e"] < 1
    assert ks.hesapla_df(df.iloc[:30], 4000.0)["durum"] == "yetersiz"


def test_tarife():
    assert tsv.dogrula({"tip": "sabit", "tl_mwh": "2500"})["tl_mwh"] == 2500.0
    assert tsv.dogrula({"tip": "yekdem", "usd_cent_kwh": 7.3, "kur_tl_usd": 40})["kur_tl_usd"] == 40.0
    for kotu in ({"tip": "x"}, {"tip": "sabit", "tl_mwh": -1}, {"tip": "ptf", "prim_oran": 5}):
        with pytest.raises(ValueError):
            tsv.dogrula(kotu)
    assert tsv.ortalama_fiyat_tl_mwh({"tip": "yekdem", "usd_cent_kwh": 7.3, "kur_tl_usd": 40}) == 2920.0
    assert tsv.ortalama_fiyat_tl_mwh({"tip": "ptf", "prim_oran": 0.1}, 2000.0) == 2200.0 and tsv.ortalama_fiyat_tl_mwh({"tip": "ptf"}) is None
    ix = pd.date_range("2026-08-01", periods=24, freq="h", tz="UTC")
    g = tsv.gelir_df(pd.Series(1000.0, index=ix), {"tip": "sabit", "tl_mwh": 2500.0})
    assert abs(g["gelir_tl"].sum() - 24 * 2500) < 1e-6


def test_kayip_agaci(monkeypatch):
    ix = pd.date_range("2023-06-01", periods=24 * 5, freq="h", tz="UTC")
    z = np.clip(np.sin(np.pi * (ix.hour - 3) / 12), 0, None)
    df = pd.DataFrame({"ghi": 900 * z, "dni": 700 * z, "dhi": 150 * z, "temp_air": 25.0, "wind_speed_10m": 2.0}, index=ix)
    plant = {"id": "p", "name": "K", "lat": 37.87, "lon": 32.49, "tilt": 20, "azimuth": 180, "capacity_kwp": 4000.0, "panel_tech": "mono", "params_json": {"iam_model": "physical"}}
    r = kys.agac_hesapla(df, plant, {"soiling": 0.02, "kirpma": 0.0}, {"soiling": "ayar"})
    adimlar = {s["adim"]: s for s in r["satirlar"]}
    assert adimlar["soiling"]["kayip_pct"] == 2.0 and adimlar["soiling"]["kaynak"] == "ayar" and adimlar["sicaklik"]["kayip_pct"] > 0
    assert r["sebeke_kwh"] < r["nominal_dc_kwh"] and 0.6 < r["pr"] < 0.95 and adimlar["inverter"]["kaynak"] == "varsayılan"


def test_sablon_uret(monkeypatch):
    from pvquant.ext.platform import rapor_sablon as rs
    monkeypatch.setattr(srs, "kullanilabilirlik", lambda t, p, gun=30: rs.Rapor("Kullanılabilirlik", "son 30 gün", "K", [("Özet", pd.DataFrame([{"A": 1.0}]))]))
    icerik, ad = srs.uret("t", {"name": "Konya GES"}, "kullanilabilirlik", gun=30)
    assert ad.startswith("kullanilabilirlik_Konya_GES_") and b"<h1>Kullan" in icerik
    with pytest.raises(KeyError):
        srs.uret("t", {"name": "K"}, "yok")


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "K", "capacity_kwp": 4000.0, **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {**depo["params_json"], **k}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    monkeypatch.setattr(ks, "hesapla", lambda t, p, gun=30: {"durum": "ok", "A_t": 0.99, "pencere_gun": gun})
    def sahte_uret(t, p, ad, **k):
        if ad not in srs.SABLONLAR:
            raise KeyError(ad)
        return (b"<html>x</html>", "x.html")
    monkeypatch.setattr(srs, "uret", sahte_uret)
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    assert istemci.get("/v1/plants/p1/kullanilabilirlik?gun=3").json()["pencere_gun"] == 7          # alt sınır 7
    assert istemci.put("/v1/plants/p1/tarife", json={"tarife": {"tip": "sabit", "tl_mwh": 2500}}).json()["tarife"]["tl_mwh"] == 2500.0
    assert istemci.get("/v1/plants/p1/tarife").json()["tarife"]["tip"] == "sabit"
    assert istemci.put("/v1/plants/p1/tarife", json={"tarife": {"tip": "sabit", "tl_mwh": -5}}).status_code == 422
    assert istemci.get("/v1/plants/p1/kayip-agaci").status_code == 404
    y = istemci.get("/v1/plants/p1/rapor-sablon/fatura"); assert y.status_code == 200 and "x.html" in y.headers["content-disposition"]
    assert istemci.get("/v1/plants/p1/rapor-sablon/yok").status_code == 422
