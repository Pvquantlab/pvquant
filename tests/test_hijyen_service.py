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
