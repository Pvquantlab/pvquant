"""v2.276 — DSG netleştirmesi (SAF) + gün içi tazeleme (monkeypatch) + kapı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.io import acik_nwp
from pvquant.services import dengesizlik_service as dz


def _prog(sapma_kw):
    ix = pd.date_range("2026-08-01", periods=48, freq="h", tz="UTC")
    g = np.full(48, 1000.0)
    return pd.DataFrame({"ts_utc": ix, "gercek_kw": g, "kgup_kw": g - sapma_kw, "naif_kw": np.nan})


def test_dsg_netlesme():
    fiyat = pd.DataFrame({"ptf": 2000.0, "smf": 2500.0, "kaynak": "senaryo"}, index=pd.date_range("2026-08-01", periods=48, freq="h", tz="UTC"))
    r = dz.dsg_hesapla_df({"A": _prog(+200), "B": _prog(-200)}, fiyat)      # A fazla, B açık → net sıfır
    assert r["santral"] == 2 and r["ayri_tl"] > 0 and r["net_tl"] == 0 and r["kazanc_tl"] == r["ayri_tl"] and r["kazanc_pct"] == 100.0
    tek = dz.dsg_hesapla_df({"A": _prog(+200)}, fiyat)
    assert tek["kazanc_tl"] == 0                                                  # tek santral: netleşme yok
    assert dz.dsg_hesapla_df({}, fiyat)["ayri_tl"] is None
    assert dz.dsg_hesapla_df({"A": _prog(100).iloc[:10], "B": _prog(50)}, fiyat)["not"] == "ortak saat yetersiz"


def test_gun_ici_tazele(monkeypatch, tmp_path):
    ix = pd.date_range("2026-09-06", periods=240, freq="h", tz="UTC")
    e = pd.DataFrame({"ghi": 300.0, "dni": 200.0, "dhi": 100.0, "temp_air": 25.0, "wind_speed_10m": 2.0, "cloud_cover": 10.0, "precipitation": 0.0, "relative_humidity": 40.0}, index=ix)
    i = pd.DataFrame({"ghi": 500.0, "dni": 300.0, "dhi": 150.0, "temp_air": 27.0, "wind_speed_10m": 3.0, "cloud_cover": 5.0}, index=ix[12:132])
    i_kosu = pd.Timestamp("2026-09-06 12:00", tz="UTC")
    monkeypatch.setattr(acik_nwp, "icon_indir", lambda dizin=None, kosu=None: (tmp_path, i_kosu))
    monkeypatch.setattr(acik_nwp, "icon_noktalar", lambda kd, n: {(37.87, 32.49): i})
    monkeypatch.setattr(acik_nwp, "_arsivden_son_kosu_df", lambda la, lo: (e, pd.Timestamp("2026-09-06 06:00", tz="UTC")))
    yazilan = {}
    monkeypatch.setattr(acik_nwp, "_arsive_yaz", lambda rows: yazilan.setdefault("rows", rows) and len(rows))
    monkeypatch.setattr(acik_nwp, "eski_temizle", lambda d, t=2: [])
    r = acik_nwp.gun_ici_tazele([(37.87, 32.49)], tmp_path)
    rows = yazilan["rows"]
    assert r["satir"] == len(rows) == 240 and rows[0]["z"] == i_kosu.to_pydatetime()     # ufuk ECMWF omurgasıyla korunur
    assert abs(rows[200]["temp_air"] - 25.0) < 1e-6 and rows[50]["temp_air"] > 25.0        # ICON dışı saatler omurga, içi harman
    monkeypatch.setattr(acik_nwp, "_arsivden_son_kosu_df", lambda la, lo: (e, pd.Timestamp("2026-09-06 15:00", tz="UTC")))
    r2 = acik_nwp.gun_ici_tazele([(37.87, 32.49)], tmp_path)
    assert r2["satir"] == 0 and "atlandı" in r2["hata"][0]                                   # daha yeni arşiv varsa yazılmaz


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    monkeypatch.setattr(dz, "dsg_ozet", lambda t, gun=30: {"santral": 1, "n_saat": 100, "ayri_tl": 10.0, "net_tl": 10.0, "kazanc_tl": 0.0, "pencere_gun": gun, "fiyat": {"epias_saat": 0, "senaryo_saat": 100}, "not": "tek"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_dsg_kapisi(istemci):
    assert istemci.get("/v1/portfoy/dsg?gun=45").json()["pencere_gun"] == 45
    assert istemci.get("/v1/portfoy/dsg?gun=5").status_code == 422
