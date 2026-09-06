"""v2.271 — güvenilirlik diyagramı / PIT / keskinlik (SAF) + kapı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import guvenilirlik_service as gs


def _df(n_gun=10, seed=1):
    rng = np.random.default_rng(seed)
    ix = pd.date_range("2026-08-01", periods=24 * n_gun, freq="h", tz="UTC")
    cs = np.clip(3000 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None)
    p50 = cs; y = cs * rng.uniform(0.85, 1.15, len(ix))            # gerçek: ±%15 gürültü
    return pd.DataFrame({"ts_utc": ix, "power_kw": y, "p50": p50, "p10_ham": p50 * 0.95, "p90_ham": p50 * 1.05,   # ham bant dar
                         "p10_kal": p50 * 0.80, "p90_kal": p50 * 1.20})                                          # kalibre bant geniş


def test_guvenilirlik_ham_dar_kalibre_iyi():
    r = gs.hesapla_df(_df(), 4000.0)
    assert r["durum"] == "ok" and r["n_saat"] >= 72 and r["gun_sayisi"] == 10
    ham = {x["tau"]: x["gozlenen"] for x in r["guvenilirlik"]["ham"]}; kal = {x["tau"]: x["gozlenen"] for x in r["guvenilirlik"]["kalibre"]}
    assert abs(ham[0.5] - 0.5) < 0.1 and ham[0.1] > 0.25 and ham[0.9] < 0.75          # dar bant: P10 altı çok, P90 altı az
    assert abs(kal[0.1] - 0.1) < 0.12 and abs(kal[0.9] - 0.9) < 0.12                   # geniş/uygun bant köşegene yakın
    assert r["keskinlik"]["kalibre"] > r["keskinlik"]["ham"] and r["picp80"]["kalibre"] > r["picp80"]["ham"]
    assert r["aralik_skoru_n"]["kalibre"] < r["aralik_skoru_n"]["ham"]                 # ceza, genişlikten ağır basar
    assert len(r["pit"]) == 10 and abs(sum(x["oran"] for x in r["pit"]) - 1) < 0.01


def test_yetersiz_ve_bos():
    assert gs.hesapla_df(_df(n_gun=1), 4000.0)["durum"] == "yetersiz"
    assert gs.hesapla_df(pd.DataFrame(), 4000.0)["durum"] == "veri_yok"
    d = _df(); d["p10_kal"] = np.nan; d["p90_kal"] = np.nan                            # kalibre yoksa ham = kalibre
    r = gs.hesapla_df(d, 4000.0); assert r["keskinlik"]["ham"] == r["keskinlik"]["kalibre"]


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 4000.0})
    monkeypatch.setattr(gs, "hesapla", lambda t, p, gun=60: {"durum": "ok", "n_saat": 100, "pencere_gun": gun})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapi(istemci):
    assert istemci.get("/v1/plants/p1/guvenilirlik?gun=45").json()["pencere_gun"] == 45
    assert istemci.get("/v1/plants/p1/guvenilirlik?gun=5").status_code == 422
