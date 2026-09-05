"""v2.75-A — /skill kapisi (DB'siz). Sahte df GERCEK sekli tasir:
skill_gecmisi kolonlari date/horizon_bucket/mape/skill_vs_naive (parse_dates)."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici

PLANT = "22222222-2222-2222-2222-222222222222"


def _sahte_sk():
    # v2.95: naive_wmape kolonu dogdu. Ilk satir SAKLANAN degeri tasir
    # (11.9 — turetme 11.884'ten kasten farkli: oncelik kaniti), 29 Tem
    # satiri None (eski satir — v2.76 turetme yedegi devrede).
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-07-28", "2026-07-28",
                                "2026-07-29", "2026-07-30"]),
        "horizon_bucket": ["0-24", "24-72", "0-24", "0-24"],
        "mape": [8.2, 14.1, 7.4, 9.0],
        "naive_wmape": [11.9, None, None, 13.5],
        "skill_vs_naive": [31.0, None, 27.0, 35.0],
        # v2.247: SFA kolonlari — 29 Tem satiri migration-oncesi (None)
        "nmae": [4.1, 6.0, None, 4.5],
        "nrmse": [6.2, 9.1, None, 6.8],
        "nmbe": [-0.4, 1.2, None, 0.6],
    })


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {
        "sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import forecast_service as fs
    monkeypatch.setattr(fs, "skill_gecmisi", lambda t, p, gun=120: _sahte_sk())
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_skill_200_toplulastirma_streamlit_kopyasi(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/skill?bucket=0-24")
    assert r.status_code == 200
    g = r.json()
    assert g["kova"] == "0-24" and g["gun_sayisi"] == 3    # nunique(28,29,30)
    assert g["wmape_ort"] == round((8.2 + 7.4 + 9.0) / 3, 3)
    assert g["naife_ustunluk_pct"] == 31.0                  # (31+27+35)/3
    assert g["ilk_tarih"] == "2026-07-28" and g["son_tarih"] == "2026-07-30"
    assert len(g["gunluk"]) == 3
    # v2.95: SAKLANAN naif oncelikli — 11.9 (turetme 11.884 DEGIL).
    assert g["gunluk"][0] == {"tarih": "2026-07-28", "kova": "0-24",
                              "wmape": 8.2, "naif_wmape": 11.9,
                              "nmae": 4.1, "nrmse": 6.2, "nmbe": -0.4}
    # v2.247: SFA ortalamalari yalniz dolu satirlardan (29 Tem None atlanir)
    assert g["nmae_ort"] == 4.3 and g["nrmse_ort"] == 6.5 and g["nmbe_ort"] == 0.1
    # Eski satir (naive_wmape=None): v2.76 turetmesi yedek —
    # 7.4/(1-0.27) = 10.137.
    assert g["gunluk"][1] == {"tarih": "2026-07-29", "kova": "0-24",
                              "wmape": 7.4, "naif_wmape": 10.137,
                              "nmae": None, "nrmse": None, "nmbe": None}


def test_skill_bos_kova_durust_bos(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/skill?bucket=168-999")
    assert r.status_code == 200
    g = r.json()
    assert g["gun_sayisi"] == 0 and g["wmape_ort"] is None
    assert g["nmae_ort"] is None and g["nrmse_ort"] is None
    assert g["gunluk"] == []


def test_skill_gun_sinir_disi_422(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/skill?gun=0").status_code == 422
    assert istemci.get(f"/v1/plants/{PLANT}/skill?gun=366").status_code == 422
