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


# ---------------- v2.296: ufuk kovaları ----------------
def _ufuklu_df(n_gun=40):
    """Sentetik: yakın ufukta dar, uzak ufukta geniş artık — kovalar farklı q̂ öğrenmeli."""
    import numpy as np
    import pandas as pd
    saatler = pd.date_range("2026-06-01", periods=n_gun * 24, freq="h", tz="UTC")
    kayit = []
    rng = np.random.default_rng(7)
    for u0, sapma in ((6.0, 50.0), (48.0, 300.0), (120.0, 700.0)):
        for ts in saatler:
            if not (6 <= ts.hour <= 16):
                continue
            y = 3000.0 + rng.normal(0, sapma)
            kayit.append({"ts_utc": ts, "power_kw": y, "p10": 2900.0, "p90": 3100.0, "ufuk_saat": u0})
    return pd.DataFrame(kayit)


def test_ufuk_kovalari_ogrenilir_ve_buyur():
    a = q_hat_hesapla_df(_ufuklu_df(), capacity_kwp=4514.0)
    assert a is not None and a["grup"] == "saat_ufuk"
    q = a["q_hat"]
    assert set(q) >= {"0-24", "24-72", "72-168", "_genel"}
    # uzak ufkun q̂'sı yakından büyük olmalı (artık büyüdü)
    o = {k: sum(v for s, v in q[k].items() if s != "_genel") / max(1, len(q[k]) - 1)
         for k in ("0-24", "24-72", "72-168")}
    assert o["0-24"] < o["24-72"] < o["72-168"]
    assert a["kova_n"]["0-24"] > 0 and a["ort_q"] == pytest.approx(o["0-24"], abs=0.5)


def test_uygula_kovaya_gore_ve_eski_ayar_bozulmaz():
    import numpy as np
    import pandas as pd
    a = q_hat_hesapla_df(_ufuklu_df(), capacity_kwp=4514.0)
    run_at = pd.Timestamp("2026-09-01 00:00", tz="UTC")
    ix = pd.date_range(run_at, periods=168, freq="h")
    h = pd.DataFrame({"p50_kw": 3000.0, "p10_kw": 2900.0, "p90_kw": 3100.0}, index=ix)
    y = uygula_df(h, a, tavan_kw=None, run_at=run_at)
    gun1 = (y["p90_kw"] - y["p10_kw"]).iloc[12]           # ufuk ~12 s
    gun5 = (y["p90_kw"] - y["p10_kw"]).iloc[110]          # ufuk ~110 s
    assert gun5 > gun1, "uzak ufkun bandı genişlemeli"
    assert (y["p10_ham_kw"] == 2900.0).all() and (y["p10_kw"] <= y["p50_kw"]).all()
    # eski biçim ('saat') aynen: kovasız ayar her ufka aynı düzeltme
    eski = {"alpha": 0.2, "grup": "saat", "q_hat": {str(s): 40.0 for s in range(24)} | {"_genel": 40.0}}
    ye = uygula_df(h, eski, tavan_kw=None)
    assert float((ye["p90_kw"] - ye["p10_kw"]).iloc[12]) == pytest.approx(float((ye["p90_kw"] - ye["p10_kw"]).iloc[110]))


def test_ogrenilmemis_kova_yakina_duser():
    """Yalnız 0-24 öğrenildiyse 5. günün saati de o kovadan düzeltilir (uydurma q̂ yok)."""
    import pandas as pd
    df = _ufuklu_df()
    a = q_hat_hesapla_df(df[df.ufuk_saat < 24.0], capacity_kwp=4514.0)
    assert a["grup"] == "saat_ufuk" and set(a["q_hat"]) & {"24-72", "72-168"} == set()
    run_at = pd.Timestamp("2026-09-01 00:00", tz="UTC")
    ix = pd.date_range(run_at, periods=168, freq="h")
    h = pd.DataFrame({"p50_kw": 3000.0, "p10_kw": 2900.0, "p90_kw": 3100.0}, index=ix)
    y = uygula_df(h, a, tavan_kw=None, run_at=run_at)
    # AYNI UTC saati, farklı ufuk (12 s vs 108 s): kova öğrenilmediğinden aynı q̂ uygulanmalı
    assert float((y["p90_kw"] - y["p10_kw"]).iloc[108]) == pytest.approx(float((y["p90_kw"] - y["p10_kw"]).iloc[12]))
