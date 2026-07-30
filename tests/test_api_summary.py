"""v2.74-A — /summary kapisi (DB'siz: uc servis monkeypatch)."""
import datetime as dt
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici

PLANT = "22222222-2222-2222-2222-222222222222"


def _sahte_ozet():
    from pvquant.services.ozet_service import GununOzeti
    o = GununOzeti()
    o.mode = "C"; o.sapma_pct = 4.98
    o.icgoru_cumlesi = "Yarın beklenen üretim bugünle aynı seviyede."
    o.bugun_kwh = 30356.0; o.yarin_kwh = 30626.0; o.hafta_mwh = 213.0
    o.yarin_hava = "açık"; o.model_alt = "yıllık enerji sapması %4,98"
    o.kalibrasyon_tarihi = dt.date(2026, 7, 22)
    o.hava_3gun = [{"gun": "BUGÜN", "derece": 34.0, "kwhm2": 7.9}]
    o.gunler = ["BUGÜN", "YARIN"]; o.gunluk_mwh = [30.4, 30.6]
    o.son_scada_tarihi = dt.datetime(2026, 4, 30, 21, 0)
    o.islenen_saat = 8760; o.anomali_sayisi = 3297
    return o


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {
        "sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service, ozet_service, ingest_service
    # plant_service.getir DICT dondurur — sahte de dict (canli durusma dersi).
    row = {"id": PLANT, "name": "Konya GES", "capacity_kwp": 4514.0,
           "ac_limit_kw": 3560.0, "lat": 37.87, "lon": 32.48,
           "tz": "Europe/Istanbul", "tilt": 25.0, "azimuth": 180.0,
           "panel_tech": "bifacial"}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: row)
    monkeypatch.setattr(ozet_service, "gunun_ozeti", lambda t, s: _sahte_ozet())
    # aylik_ozet'in GERCEK kolonlari: ay, uretim_mwh, saat, kapsam_pct (v2.68).
    monkeypatch.setattr(ingest_service, "aylik_uretim", lambda t, p: pd.DataFrame(
        {"ay": ["2026-06", "2026-07"], "uretim_mwh": [870.1, 812.5],
         "saat": [710, 700], "kapsam_pct": [98.6, 94.0]}))
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_summary_200_sekil(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/summary")
    assert r.status_code == 200
    g = r.json()
    assert g["plant"]["name"] == "Konya GES" and g["plant"]["ac_limit_kw"] == 3560.0
    assert g["mode"] == "C" and g["sapma_pct"] == 4.98
    assert g["gunler"] == [{"etiket": "BUGÜN", "mwh": 30.4},
                           {"etiket": "YARIN", "mwh": 30.6}]
    assert g["aylik"][0] == {"ay": "2026-06", "mwh": 870.1,
                             "saglam_saat": 710, "kapsam_pct": 98.6}
    assert g["saglik"]["anomali"] == 3297
    assert g["kalibrasyon_tarihi"] == "2026-07-22"  # datetime JSON'a ISO gecer


def test_summary_santral_yoksa_404(istemci, monkeypatch):
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: None)
    assert istemci.get(f"/v1/plants/{PLANT}/summary").status_code == 404


def test_summary_bos_aylik_bos_liste(istemci, monkeypatch):
    from pvquant.services import ingest_service
    monkeypatch.setattr(ingest_service, "aylik_uretim",
                        lambda t, p: pd.DataFrame())
    r = istemci.get(f"/v1/plants/{PLANT}/summary")
    assert r.status_code == 200 and r.json()["aylik"] == []
