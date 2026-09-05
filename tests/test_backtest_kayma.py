"""v2.253 — backtest_service ve kayma_service SAF fonksiyonları + kapılar (DB/ağ yok)."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services.backtest_service import konformal_backtest_df, ozet
from pvquant.services.kayma_service import kayma_hesapla

CAP = 1000.0
PLANT = "22222222-2222-2222-2222-222222222222"


def _gecmis(gun=60, genislik=0.3, seed=0):
    ts = pd.date_range("2026-06-01", periods=24 * gun, freq="h", tz="UTC"); rng = np.random.default_rng(seed)
    g = np.clip(np.sin((ts.hour - 6) / 12 * np.pi), 0, None); p50 = 800 * g
    ger = p50 * (1 + rng.normal(0, 0.1, len(ts)))
    return pd.DataFrame({"ts_utc": ts, "power_kw": ger, "p50": p50, "p10": p50 * (1 - genislik), "p90": p50 * (1 + genislik)})[g > 0]


def test_backtest_sizintisiz_ve_hedefe_yaklastirir():
    bt = konformal_backtest_df(_gecmis(), CAP, egitim_gun=21, test_gun=7, adim_gun=7)
    assert len(bt) >= 4 and (bt.picp_ham > 0.95).all()
    assert ((bt.picp_kal - 0.8).abs() < (bt.picp_ham - 0.8).abs()).all() and (bt.bant_kal_n < bt.bant_ham_n).all()
    o = ozet(bt); assert o["hukum"].startswith("kalibrasyon hedefe yakla") and o["pencere"] == len(bt)
    assert ozet(konformal_backtest_df(pd.DataFrame(), CAP))["hukum"] == "yetersiz"


def test_kayma_hesapla_sapma_ve_hukum():
    idx = pd.date_range("2026-07-01", periods=24 * 20, freq="h", tz="UTC"); rng = np.random.default_rng(1)
    g = np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None)
    ars = pd.DataFrame({"ghi": 900 * g, "temp_air": 25 + 5 * g, "wind_speed_10m": rng.gamma(2, 1.5, len(idx))}, index=idx)
    tah = ars.copy(); tah["ghi"] *= 1.15
    tah["wind_speed_10m"] = rng.gamma(2, 3.0, len(idx))
    r = kayma_hesapla(ars, tah)
    oz = {o["ad"]: o for o in r["ozellikler"]}
    assert 14 < oz["ghi"]["sapma_pct"] < 16 and oz["temp_air"]["hukum"] == "uyumlu" and oz["wind_speed_10m"]["hukum"] == "KAYMA"
    assert r["hukum"] == "KAYMA" and r["kaynak"]["egitim"].startswith("arşiv")
    assert kayma_hesapla(ars.iloc[:10], tah.iloc[:10])["hukum"] == "yetersiz"


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service, backtest_service, kayma_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5})
    monkeypatch.setattr(backtest_service, "konformal_backtest", lambda t, pl, gun=90: {"pencere": 3, "picp_ham_ort": 0.95, "picp_kal_ort": 0.81, "hedef": 0.8, "hukum": "ok", "satirlar": []})
    monkeypatch.setattr(kayma_service, "kayma_denetimi", lambda pl, gun=30: {"n_saat": 700, "ozellikler": [], "hukum": "uyumlu", "gun": gun})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/backtest?gun=60").json()["picp_kal_ort"] == 0.81
    assert istemci.get(f"/v1/plants/{PLANT}/backtest?gun=10").status_code == 422
    assert istemci.get(f"/v1/plants/{PLANT}/kayma?gun=14").json()["gun"] == 14
    assert istemci.get(f"/v1/plants/{PLANT}/kayma?gun=99").status_code == 422
