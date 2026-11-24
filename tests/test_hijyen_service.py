"""v2.254 — hijyen_service.bayrakla_df (SAF) + /hijyen kapısı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services.hijyen_service import bayrakla_df

CAP, TAVAN = 1000.0, 800.0
PLANT = "22222222-2222-2222-2222-222222222222"


def _df():
    ts = pd.date_range("2026-07-01", periods=24 * 3, freq="h", tz="UTC")
    g = np.clip(np.sin((np.asarray(ts.hour) - 6) / 12 * np.pi), 0, None)
    beklenen = 1000 * g
    guc = np.minimum(beklenen, TAVAN).astype(float)                    # 1. gün: tavan platosu
    guc[24 + 10: 24 + 15] = 300.0                         # 2. gün 10–14: şebeke kısıntısı (düz, düşük)
    guc[48 + 12] = beklenen[48 + 12] * 0.5                # 3. gün: tek saatlik bulut → kısıntı DEĞİL
    return pd.DataFrame({"ts_utc": ts, "power_kw": guc, "beklenen_kw": beklenen})


def test_kirpma_ve_kisinti_ayrimi():
    b = bayrakla_df(_df(), TAVAN, CAP).set_index("ts_utc")
    assert b.kirpma.sum() == 9 and b.kirpma.iloc[:24].sum() == 5            # 1. gün 5 (10–14); 2. gün plato kısıntıya, 3. günde 12:00 buluta gitti
    k = b.kisinti
    assert k.iloc[24 + 10: 24 + 15].all() and k.sum() == 5                  # yalnız 2. gün bloğu
    assert not k.iloc[48 + 12]                                              # tek saatlik bulut kısıntı değil
    assert b.kayip_kwh.iloc[24 + 10: 24 + 15].gt(0).all() and b.kayip_kwh.sum() == pytest.approx(float((b.beklenen_kw - b.power_kw)[k].sum()))
    assert not (b.kirpma & b.kisinti).any()


def test_beklenen_yoksa_kisinti_aranmaz_tavan_yoksa_kirpma_aranmaz():
    d = _df(); d["beklenen_kw"] = np.nan
    b = bayrakla_df(d, TAVAN, CAP); assert b.kisinti.sum() == 0 and b.kirpma.sum() > 0
    b2 = bayrakla_df(_df(), None, CAP); assert b2.kirpma.sum() == 0 and b2.kisinti.sum() == 5
    assert bayrakla_df(pd.DataFrame(columns=["ts_utc", "power_kw", "beklenen_kw"]), TAVAN, CAP).empty


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import hijyen_service
    monkeypatch.setattr(hijyen_service, "ozet", lambda t, p, gun=30: {"pencere_gun": gun, "kisinti_kayip_kwh": 123.4, "kisinti_aranabildi": True})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_hijyen_kapisi(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/hijyen?gun=60").json()["kisinti_kayip_kwh"] == 123.4
    assert istemci.get(f"/v1/plants/{PLANT}/hijyen?gun=1").status_code == 422


# ── G2-B6 (24.11.2026): tam kesinti bayrağı ──────────────────────────────────
def _gun(beklenen_kw):
    ix = pd.date_range("2026-10-18 03:00", periods=16, freq="h", tz="UTC")   # 06–21 TSİ
    return ix, pd.Series(beklenen_kw, index=ix)


def test_tam_kesinti_ardisik_sifir_saatler_bayraklanir():
    """Kıvanç 18.10 vakası: 23.900 → 8.150 → 0 × 8 saat; beklenen ≥ %30 kWp → kisinti, kayıp = beklenen."""
    from pvquant.services.hijyen_service import bayrakla_df
    ix, bek = _gun([0, 3000, 20000, 22000, 25000, 27000, 28000, 27000, 25000, 22000, 18000, 12000, 5000, 500, 0, 0])
    guc = pd.Series([0, 3680, 23900, 8150, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], index=ix, dtype=float)
    d = bayrakla_df(pd.DataFrame({"ts_utc": ix, "power_kw": guc.values, "beklenen_kw": bek.values}), tavan_kw=35000.0, capacity_kwp=52500.0).set_index("ts_utc")
    kesinti = d.index[4:11]                                                  # 10–16 TSİ: beklenen ≥ 15.750 (%30) ve gerçek 0
    assert d.loc[kesinti, "kisinti"].all() and np.allclose(d.loc[kesinti, "kayip_kwh"], bek.loc[kesinti])
    assert not d.loc[d.index[:4], "kisinti"].any()                           # üretimli sabah saatleri bayraksız
    assert not d.loc[d.index[11:], "kisinti"].any()                          # 17 TSİ+ : beklenen < %30 → omuz, bayraksız (bilinçli)


def test_tek_saatlik_dusus_ve_omuz_saatleri_bayraklanmaz():
    from pvquant.services.hijyen_service import bayrakla_df
    ix, bek = _gun([0, 2200, 9000, 20000, 29000, 30000, 29000, 20000, 9000, 2500, 1200, 400, 0, 0, 0, 0])
    guc = pd.Series([0, 380, 9790, 18490, 630, 21380, 25830, 9790, 7000, 1000, 1000, 300, 0, 0, 0, 0], index=ix, dtype=float)
    d = bayrakla_df(pd.DataFrame({"ts_utc": ix, "power_kw": guc.values, "beklenen_kw": bek.values}), tavan_kw=35000.0, capacity_kwp=52500.0).set_index("ts_utc")
    assert not d["kisinti"].any()            # 10 TSİ tek saatlik 630 kW düşüşü (bulut) ve 07/15–17 omuz saatleri (beklenen < %30) bayraksız


def test_tam_kesinti_kirpma_onceligi_ve_beklenen_yoksa_aranmaz():
    from pvquant.services.hijyen_service import bayrakla_df
    ix, bek = _gun([0] * 4 + [30000] * 8 + [0] * 4)
    guc = pd.Series([0] * 4 + [0] * 8 + [0] * 4, index=ix, dtype=float)
    d0 = bayrakla_df(pd.DataFrame({"ts_utc": ix, "power_kw": guc.values, "beklenen_kw": np.nan}), tavan_kw=35000.0, capacity_kwp=52500.0)
    assert not d0["kisinti"].any()           # tire ilkesi: beklenen yoksa kesinti aranmaz
    d1 = bayrakla_df(pd.DataFrame({"ts_utc": ix, "power_kw": guc.values, "beklenen_kw": bek.values}), tavan_kw=35000.0, capacity_kwp=52500.0)
    assert int(d1["kisinti"].sum()) == 8 and not d1["kirpma"].any()
