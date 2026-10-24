"""v2.280 — hiyerarşik uzlaştırma (SAF): bottom-up tek santral, MinT iki santral tutarlılık; kapı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import uzlastirma_service as uz


def _tahmin(seed, olcek):
    ix = pd.date_range("2026-09-07", periods=48, freq="h", tz="UTC")
    p = pd.Series(np.clip(olcek * np.sin(np.pi * (ix.hour - 3) / 12), 0, None), index=ix)
    return pd.DataFrame({"p50": p, "p10": p * 0.9, "p90": p * 1.1})


def test_bottom_up_tek_santral():
    out, meta = uz.uzlastir_df({"A": _tahmin(0, 1000)}, None)
    assert meta["yontem"] == "bottom-up" and np.allclose(out["p50"], out["A__p50"]) and (out["p10"] <= out["p50"]).all()


def test_mint_iki_santral_tutarli():
    rng = np.random.default_rng(1)
    ix = pd.date_range("2026-07-01", periods=24 * 20, freq="h", tz="UTC")
    art = pd.DataFrame({"A": rng.normal(50, 100, len(ix)), "B": rng.normal(-30, 60, len(ix))}, index=ix)   # A sistematik yüksek
    out, meta = uz.uzlastir_df({"A": _tahmin(0, 1000), "B": _tahmin(1, 600)}, art)
    assert meta["yontem"].startswith("MinT") and meta["tutarli"] is True
    assert np.allclose(out["p50"], out["A__p50"] + out["B__p50"], atol=1e-6)     # toplam korunur
    assert (out["p10"] <= out["p50"]).all() and (out["p90"] >= out["p50"]).all()
    out2, meta2 = uz.uzlastir_df({"A": _tahmin(0, 1000), "B": _tahmin(1, 600)}, art.iloc[:50])     # az artık → bottom-up
    assert meta2["yontem"] == "bottom-up"
    with pytest.raises(ValueError):
        uz.uzlastir_df({}, None)


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    monkeypatch.setattr(uz, "portfoy_tahmini", lambda t, gun=7: {"durum": "ok", "yontem": "bottom-up", "gunler": [], "n_saat": 0})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapi(istemci):
    assert istemci.get("/v1/portfoy/tahmin?gun=3").json()["yontem"] == "bottom-up"
    assert istemci.get("/v1/portfoy/tahmin?gun=99").status_code == 422


# v2.477 — canlı 500: artık tablosunda sütunu olmayan santral (SCADA'sı eski) MinT yolunu KeyError ile düşürüyordu.
def _artik_ab(gun=20):
    rng = np.random.default_rng(2)
    ix = pd.date_range("2026-07-01", periods=24 * gun, freq="h", tz="UTC")
    return pd.DataFrame({"A": rng.normal(50, 100, len(ix)), "B": rng.normal(-30, 60, len(ix))}, index=ix)


def test_eksik_artik_sutunu_bottom_up_toplam_korunur():
    tahminler = {"A": _tahmin(0, 1000), "B": _tahmin(1, 600), "C": _tahmin(2, 300)}
    out, meta = uz.uzlastir_df(tahminler, _artik_ab())          # C'nin artığı hiç yok → KeyError değil, dürüst bottom-up
    assert meta["yontem"] == "bottom-up" and meta["artik_eksik"] == ["C"]
    assert np.allclose(out["p50"], out["A__p50"] + out["B__p50"] + out["C__p50"], atol=1e-6)
    assert (out["p10"] <= out["p50"]).all() and (out["p90"] >= out["p50"]).all()


class _Satir:
    def __init__(self, d): self._mapping = d


class _Oturum:
    def __init__(self, santraller): self._s = santraller
    def execute(self, *a, **k): return [_Satir(p) for p in self._s]
    def connection(self): return None


@pytest.fixture()
def eksik_artik_kiraci(monkeypatch):
    import contextlib
    import pvquant.db as db
    from pvquant.services import forecast_service
    santraller = [{"id": i, "name": n, "tz": "Europe/Istanbul", "capacity_kwp": c}
                  for i, (n, c) in enumerate([("A", 1000.0), ("B", 600.0), ("C", 300.0)])]
    monkeypatch.setattr(db, "tenant_baglami", lambda t: contextlib.nullcontext(_Oturum(santraller)))
    art = _artik_ab().stack().rename("artik").reset_index()
    art.columns = ["ts_utc", "name", "artik"]
    monkeypatch.setattr(uz.pd, "read_sql", lambda *a, **k: art)
    def son_kosu(tenant_id, plant_id):
        t = _tahmin(0, santraller[int(plant_id)]["capacity_kwp"])
        return pd.DataFrame({"p50_kw": t["p50"], "p10_kw": t["p10"], "p90_kw": t["p90"]})
    monkeypatch.setattr(forecast_service, "son_kosu", son_kosu)
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_portfoy_tahmin_eksik_artikli_kiraci_200(eksik_artik_kiraci):
    r = eksik_artik_kiraci.get("/v1/portfoy/tahmin?gun=7")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["durum"] == "ok" and j["yontem"] == "bottom-up" and j["artik_gun"] == 20
    assert set(j["santral_bugun_mwh"]) == {"A", "B", "C"}                       # tahminli tüm santraller girer
    assert j["gunler"] and abs(j["gunler"][0]["p50_mwh"] - sum(j["santral_bugun_mwh"].values())) < 0.2
    assert "C" in j["not"]                                                         # not, eksik artığı adıyla söyler
