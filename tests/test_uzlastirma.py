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
