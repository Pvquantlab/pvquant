"""v2.252 — konformal_service SAF fonksiyonları + /konformal kapısı (DB'siz)."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services.konformal_service import q_hat_hesapla_df, uygula_df

CAP = 1000.0
PLANT = "22222222-2222-2222-2222-222222222222"


def _gecmis(gun=30, genislik=0.3, seed=0):
    """Ham bant ±genislik·p50; gerçek p50·(1±%10 gürültü) → bant fazla geniş (PICP≈1)."""
    ts = pd.date_range("2026-07-01", periods=24 * gun, freq="h", tz="UTC"); rng = np.random.default_rng(seed)
    g = np.clip(np.sin((ts.hour - 6) / 12 * np.pi), 0, None); p50 = 800 * g
    ger = p50 * (1 + rng.normal(0, 0.1, len(ts)))
    df = pd.DataFrame({"ts_utc": ts, "power_kw": ger, "p10": p50 * (1 - genislik), "p90": p50 * (1 + genislik)})
    return df[g > 0]


def _picp(df, p10, p90):
    m = df.power_kw > 0.02 * CAP
    return float(((df.power_kw >= p10) & (df.power_kw <= p90))[m].mean())


def test_fazla_genis_bant_daralir_ve_picp_hedefe_yaklasir():
    df = _gecmis()
    ayar = q_hat_hesapla_df(df, CAP)
    assert ayar is not None and ayar["n"] > 24 * 7 and ayar["ort_q"] < 0        # negatif q̂ → daralma
    h = pd.DataFrame({"p50_kw": ((df.p10 + df.p90) / 2).values, "p10_kw": df.p10.values, "p90_kw": df.p90.values}, index=pd.DatetimeIndex(df.ts_utc))
    once = _picp(df, df.p10.values, df.p90.values)
    y = uygula_df(h, ayar, tavan_kw=CAP)
    sonra = _picp(df, y.p10_kw.values, y.p90_kw.values)
    assert once > 0.95 and 0.72 <= sonra <= 0.9
    assert (y.p10_kw <= y.p50_kw + 1e-9).all() and (y.p90_kw >= y.p50_kw - 1e-9).all() and (y.p10_kw >= 0).all()
    assert (y.p10_ham_kw == df.p10.values).all()                                   # ham korunur


def test_dar_bant_genisler():
    df = _gecmis(genislik=0.05)
    ayar = q_hat_hesapla_df(df, CAP); assert ayar["ort_q"] > 0
    h = pd.DataFrame({"p50_kw": ((df.p10 + df.p90) / 2).values, "p10_kw": df.p10.values, "p90_kw": df.p90.values}, index=pd.DatetimeIndex(df.ts_utc))
    y = uygula_df(h, ayar, tavan_kw=CAP)
    assert (y.p90_kw <= CAP + 1e-9).all() and _picp(df, y.p10_kw.values, y.p90_kw.values) > _picp(df, df.p10.values, df.p90.values)


def test_yetersiz_veri_ve_ayarsiz_uygulama():
    assert q_hat_hesapla_df(_gecmis(gun=3), CAP) is None
    assert q_hat_hesapla_df(pd.DataFrame(), CAP) is None
    ts = pd.date_range("2026-07-01", periods=24, freq="h", tz="UTC")
    h = pd.DataFrame({"p50_kw": 100.0, "p10_kw": [None] * 24, "p90_kw": [None] * 24}, index=ts)
    y = uygula_df(h, None, CAP); assert y.p10_kw.isna().all() and "p10_ham_kw" in y


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import konformal_service as ks
    monkeypatch.setattr(ks, "ayar_getir", lambda t, p: {"alpha": 0.2, "grup": "saat", "q_hat": {"12": -30.0, "_genel": -20.0}, "n": 500, "pencere_gun": 60, "hesap_zamani": "2026-09-06T00:35:00+00:00", "ort_q": -30.0})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_konformal_kapisi(istemci, monkeypatch):
    r = istemci.get(f"/v1/plants/{PLANT}/konformal"); j = r.json()
    assert r.status_code == 200 and j["aktif"] and j["ort_q_kw"] == -30.0 and "_genel" not in j["q_hat"] and j["n"] == 500
    from pvquant.services import konformal_service as ks
    monkeypatch.setattr(ks, "ayar_getir", lambda t, p: None)
    assert istemci.get(f"/v1/plants/{PLANT}/konformal").json() == {"aktif": False}
