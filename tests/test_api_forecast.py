"""v2.72 — API forecast kapisi testleri (DB'siz: dependency_overrides + monkeypatch).

Ilk API test dosyasi. DB yerine:
- kimlik: app.dependency_overrides[gecerli_kullanici] -> sahte claims
- veri:   forecast_service.son_kosu / kosu_gecmisi monkeypatch
Gercek HTTP zinciri (routing, validasyon, JSON serilestirme) sinanir.
"""
import datetime as dt
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici

TENANT = "11111111-1111-1111-1111-111111111111"
PLANT = "22222222-2222-2222-2222-222222222222"


def _sahte_df(saat: int = 5, nan_ilk: bool = False) -> pd.DataFrame:
    ix = pd.date_range("2026-07-30 00:00", periods=saat, freq="h", tz="UTC")
    df = pd.DataFrame({
        "p50_kw": np.linspace(0, 400, saat),
        "p10_kw": np.linspace(0, 300, saat),
        "p90_kw": np.linspace(0, 500, saat),
        "p25_kw": np.linspace(0, 340, saat),   # v2.204: ic bant
        "p75_kw": np.linspace(0, 460, saat),
        "physics_kw": np.linspace(0, 380, saat),
        "ml_kw": np.linspace(0, 390, saat),
    }, index=ix)
    if nan_ilk:
        df.iloc[0, df.columns.get_loc("p10_kw")] = np.nan
    return df


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {
        "sub": "u", "tenant_id": TENANT, "role": "viewer", "exp": 0}
    yield TestClient(api_main.app), monkeypatch
    api_main.app.dependency_overrides.clear()


def _servisleri_tak(monkeypatch, df, kosu_var=True, gunes=None):
    from pvquant.services import forecast_service as fs
    from pvquant.services import gunes_service as gs
    monkeypatch.setattr(fs, "son_kosu", lambda t, p: df)
    meta = [SimpleNamespace(run_at=dt.datetime(2026, 7, 30, 2, 0), mode="C",
                            model="hybrid")] if kosu_var else []
    monkeypatch.setattr(fs, "kosu_gecmisi", lambda t, p, n=1: meta)
    # v2.203: dogus/batis servisini de tak — DB'siz test, sahte cift
    monkeypatch.setattr(gs, "dogus_batis",
                        lambda t, p, lo, hi: gunes if gunes is not None else [])


def test_forecast_200_sekil_ve_saat_kirpma(istemci):
    c, mp = istemci
    _servisleri_tak(mp, _sahte_df(saat=5))
    r = c.get(f"/v1/plants/{PLANT}/forecast?hours=3")
    assert r.status_code == 200
    g = r.json()
    assert g["plant_id"] == PLANT and g["mode"] == "C"
    assert g["hours"] == 3 and len(g["series"]) == 3  # 5 satirdan ilk 3'u
    ilk = g["series"][0]
    assert set(ilk) == {"ts_utc", "p10_kw", "p50_kw", "p90_kw",
                        "p25_kw", "p75_kw"}   # v2.204: ic bant alanlari
    assert ilk["ts_utc"].startswith("2026-07-30T00:00")


def test_forecast_ic_bant_kolonu_yoksa_null(istemci):
    """v2.204 geriye uyum: eski koşu çerçevesinde p25/p75 kolonu YOK —
    yanıt null döner, uydurma yok, 500 yok."""
    c, mp = istemci
    df = _sahte_df(saat=3).drop(columns=["p25_kw", "p75_kw"])
    _servisleri_tak(mp, df)
    g = c.get(f"/v1/plants/{PLANT}/forecast").json()
    assert g["series"][0]["p25_kw"] is None
    assert g["series"][0]["p75_kw"] is None


def test_forecast_nan_json_null_olur(istemci):
    c, mp = istemci
    _servisleri_tak(mp, _sahte_df(saat=3, nan_ilk=True))
    r = c.get(f"/v1/plants/{PLANT}/forecast")
    assert r.status_code == 200
    assert r.json()["series"][0]["p10_kw"] is None  # NaN JSON'a sizmaz


def test_forecast_gunes_alani_gecer(istemci):
    """v2.203: dogus/batis ciftleri yanita `gunes` olarak biner; servis
    dusmusse alan bos liste kalir (tahmin serisi OLMEZ)."""
    c, mp = istemci
    cift = [{"gun": "2026-07-30",
             "dogus_utc": "2026-07-30T02:48:00+00:00",
             "batis_utc": "2026-07-30T17:42:00+00:00"}]
    _servisleri_tak(mp, _sahte_df(saat=5), gunes=cift)
    g = c.get(f"/v1/plants/{PLANT}/forecast").json()
    assert g["gunes"] == cift


def test_forecast_gunes_servisi_duserse_seri_olmez(istemci):
    c, mp = istemci
    _servisleri_tak(mp, _sahte_df(saat=3))
    from pvquant.services import gunes_service as gs
    def patla(t, p, lo, hi):
        raise RuntimeError("pvlib yok")
    mp.setattr(gs, "dogus_batis", patla)
    r = c.get(f"/v1/plants/{PLANT}/forecast")
    assert r.status_code == 200 and r.json()["gunes"] == []


def test_forecast_kosu_yoksa_404(istemci):
    c, mp = istemci
    _servisleri_tak(mp, None, kosu_var=False)
    r = c.get(f"/v1/plants/{PLANT}/forecast")
    assert r.status_code == 404


def test_forecast_hours_sinir_disi_422(istemci):
    c, mp = istemci
    _servisleri_tak(mp, _sahte_df())
    assert c.get(f"/v1/plants/{PLANT}/forecast?hours=0").status_code == 422
    assert c.get(f"/v1/plants/{PLANT}/forecast?hours=385").status_code == 422


def test_forecast_gecersiz_token_401():
    c = TestClient(api_main.app)  # override YOK — gercek kimlik katmani
    r = c.get(f"/v1/plants/{PLANT}/forecast",
              headers={"Authorization": "Bearer sahte-token"})
    assert r.status_code == 401
