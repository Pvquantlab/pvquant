"""v2.249 — pr_service.pr_hesapla (DB'siz) ve /pr kapisi (sahte servis)."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services.pr_service import pr_hesapla

CAP = 1000.0
PLANT = "22222222-2222-2222-2222-222222222222"


def _df(poa=True, tmod=True, gun=30):
    ts = pd.date_range("2026-06-01", periods=24 * gun, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour - 6) / 12 * np.pi), 0, None)
    poa_s = 900 * g
    tm = 25 + 20 * g
    guc = CAP * poa_s / 1000 * 0.85 * (1 - 0.0035 * (tm - 25))      # PR_stc = 0,85
    return pd.DataFrame({"ts_utc": ts, "power_kw": guc, "poa_wm2": poa_s if poa else np.nan, "t_module": tm if tmod else np.nan})


def test_pr_hesapla_ok_ve_sicaklik_duzeltmesi():
    r = pr_hesapla(_df(), CAP)
    assert r["durum"] == "ok" and r["gun"] == 30 and r["poa_orani"] == 1.0
    assert 0.75 < r["PR"] < 0.85 and r["PR_sicaklik"] is not None and r["Y_r"] > 0 and r["Y_f"] > 0 and 0 < r["CF"] < 0.5


def test_poa_yoksa_pr_yazilmaz():
    r = pr_hesapla(_df(poa=False), CAP)
    assert r["durum"] == "poa_yok" and r["PR"] is None and r["gun"] == 30 and r["poa_orani"] == 0.0
    d = _df(); d.loc[d.index[: 24 * 10], "poa_wm2"] = np.nan          # %66 kapsama < %95
    assert pr_hesapla(d, CAP)["durum"] == "poa_yok"


def test_t_module_yoksa_pr_var_prime_yok():
    r = pr_hesapla(_df(tmod=False), CAP)
    assert r["durum"] == "ok" and r["PR"] is not None and r["PR_sicaklik"] is None


def test_bos_ve_kapasitesiz():
    assert pr_hesapla(pd.DataFrame(), CAP)["durum"] == "veri_yok"
    assert pr_hesapla(_df(), 0.0)["durum"] == "veri_yok"


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import pr_service
    monkeypatch.setattr(pr_service, "pr_karti", lambda t, p, gun=30: {"durum": "ok", "PR": 0.81, "pencere_gun": gun})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_pr_kapisi(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/pr?gun=60"); assert r.status_code == 200 and r.json()["PR"] == 0.81 and r.json()["pencere_gun"] == 60
    assert istemci.get(f"/v1/plants/{PLANT}/pr?gun=3").status_code == 422
