"""v2.78-B — /monthly kapisi (DB'siz). Sahte df'ler GERCEK kolon adlarini
tasir: iklim_oku -> ay/ghi_p10_kwh_m2/.../yil_sayisi/hesap_zamani;
iklim_yil_oku -> yil/ay/ghi_kwh_m2."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici

PLANT = "22222222-2222-2222-2222-222222222222"


def _sahte_beklenti():
    return pd.DataFrame({
        "ay": [1, 7], "ghi_p10_kwh_m2": [71.6, 229.5],
        "ghi_p50_kwh_m2": [77.9, 240.7], "ghi_p90_kwh_m2": [88.6, 251.0],
        "yil_sayisi": [20, 20],
        "hesap_zamani": pd.to_datetime(["2026-07-31 00:31", "2026-07-31 00:31"],
                                       utc=True)})


def _sahte_yillik():
    return pd.DataFrame({"yil": [2005, 2005, 2024], "ay": [1, 7, 7],
                         "ghi_kwh_m2": [74.2, 233.1, 228.7]})


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {
        "sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import iklim_service as iks
    monkeypatch.setattr(iks, "iklim_oku", lambda t, p: _sahte_beklenti())
    monkeypatch.setattr(iks, "iklim_yil_oku", lambda t, p: _sahte_yillik())
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_monthly_200_sekil(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/monthly")
    assert r.status_code == 200
    g = r.json()
    assert g["beklenti"][1] == {"ay": 7, "p10": 229.5, "p50": 240.7,
                                "p90": 251.0, "yil_sayisi": 20}
    assert g["yillik"][2] == {"yil": 2024, "ay": 7, "ghi_kwh_m2": 228.7}
    assert g["hesap_zamani"].startswith("2026-07-31")


def test_monthly_hesaplanmamis_404(istemci, monkeypatch):
    from pvquant.services import iklim_service as iks
    monkeypatch.setattr(iks, "iklim_oku",
                        lambda t, p: pd.DataFrame())
    assert istemci.get(f"/v1/plants/{PLANT}/monthly").status_code == 404
