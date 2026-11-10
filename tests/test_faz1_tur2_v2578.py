"""v2.578 (Faz 1 F1-G, tur 2 entegrasyon) — dogrulama_sonuc kiracı izolasyonu (RLS: okuma ve çapraz yazma) ve bağımsız doğrulama API'sinin santral yetkisi."""
from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import olcum_uygunluk_service as ou


def _sonuc(plant):
    iz = ou.saat_izgarasi("2026-09-01 06:00", "2026-09-01 15:00")
    olc = pd.DataFrame({"power_kw": 300.0, "energy_kwh": 300.0, "flag": "valid", "kirpma": False, "kapsama_dk": 60}, index=iz)
    saatler = ou.siniflandir(iz, olc)
    tahmin = pd.DataFrame({"ts_utc": iz, "run_at": pd.Timestamp("2026-08-31 03:00", tz="UTC"), "run_id": "r1", "p50_kw": 330.0, "p10_kw": None, "p90_kw": None,
                           "physics_kw": 330.0, "model": "barhdadi_bennis", "meteo_source": "acik-nwp", "etiket": None})
    return bd.hesapla_saf(tahmin, saatler, ou.dokum(saatler), plant, date(2026, 9, 1), date(2026, 9, 2), "gun_oncesi")


@pytest.fixture()
def iki_kiraci():
    ids = {}
    with sistem_baglami() as s:
        for ad in ("a", "b"):
            tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
            s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, :n, 'active')"), {"t": tid, "n": f"tur2-{ad}"})
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) VALUES(:p, :t, :n, 1000, 900, 37.0, 32.0, 'Europe/Istanbul', '{}')"),
                      {"p": pid, "t": tid, "n": f"Tur2 {ad.upper()} GES"})
            ids[ad] = (tid, {"id": pid, "tenant_id": tid, "name": f"Tur2 {ad.upper()} GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul", "params_json": {}, "archived": False})
    yield ids
    with sistem_baglami() as s:
        for tid, p in ids.values():
            s.execute(text("DELETE FROM dogrulama_sonuc WHERE tenant_id=:t"), {"t": tid}); s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": p["id"]}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_dogrulama_sonuc_rls_okuma_ve_capraz_yazma(iki_kiraci):
    (ta, pa), (tb, pb) = iki_kiraci["a"], iki_kiraci["b"]
    kid = bd.kaydet(ta, _sonuc(pa), pa["id"])
    assert bd.son(ta, pa["id"], "gun_oncesi", 1) and bd.son(ta, pa["id"], "gun_oncesi", 1)["id"] == kid
    assert bd.son(tb, pa["id"], "gun_oncesi", 1) is None                                    # B, A'nın sonucunu göremez
    with tenant_baglami(tb) as s:
        assert s.execute(text("SELECT count(*) FROM dogrulama_sonuc")).scalar() == 0           # RLS: B bağlamında A satırı yok
    with pytest.raises((DBAPIError, ProgrammingError)):                                        # B bağlamında A kiracısına yazma: WITH CHECK reddeder
        with tenant_baglami(tb) as s:
            s.execute(text("INSERT INTO dogrulama_sonuc(tenant_id, plant_id, donem_bas, donem_bit, kural, sozluk_surumu, metrik_json, meta_json) "
                           "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), '2026-09-01', '2026-09-02', 'gun_oncesi', 'x', '{}', '{}')"), {"t": ta, "p": pa["id"]})
    with sistem_baglami() as s:
        assert s.execute(text("SELECT count(*) FROM dogrulama_sonuc WHERE tenant_id=:t"), {"t": ta}).scalar() == 1   # yalnız A'nın kendi kaydı


def test_api_baska_kiracinin_santrali_404(iki_kiraci):
    (ta, pa), (tb, pb) = iki_kiraci["a"], iki_kiraci["b"]
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tb, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        assert c.get(f"/v1/plants/{pa['id']}/dogrulama/bagimsiz").status_code == 404
        assert c.get(f"/v1/plants/{pa['id']}/rapor-sablon/bagimsiz-dogrulama").status_code == 404
        r = c.get(f"/v1/plants/{pb['id']}/dogrulama/bagimsiz?gun=7"); assert r.status_code == 200 and r.json()["metrik"]["n_saat"] == 0   # kendi santralı: boş ama 200
        r = c.get("/v1/portfoy/dogrulama/bagimsiz?gun=7"); assert r.status_code == 200 and {x["plant_id"] for x in r.json()["santraller"]} == {pb["id"]}
    finally:
        api_main.app.dependency_overrides.clear()
