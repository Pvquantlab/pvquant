"""v2.605 (Faz 4 F4-K, Stage 13) — arayüz entegrasyonunun arka uç ayağı: tahmin ucu etiket + hava tahmini kaynak zamanları, koşu listesi aynı alanlar,
özet sağlık bloğunda ortak sözlükten tazelik rozeti."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import forecast_service as fs
from pvquant.services import kalite_sozlugu as ks


@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'ui-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'UI GES', 1000, 37.0, 32.0, 'Europe/Istanbul', '{}')"), {"p": pid, "t": tid})
        rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket, nwp_kosu_zamani, nwp_bilesenler_json) "
                             "VALUES(CAST(:t AS uuid), :p, '2026-10-24T03:12:00Z', 'B', 'barhdadi_bennis', 'acik-nwp', '{}', 'gun_ici', '2026-10-24T00:00:00Z', "
                             "CAST(:b AS jsonb)) RETURNING id"), {"t": tid, "p": pid, "b": '{"ECMWF IFS": "2026-10-24T00:00:00+00:00", "ICON-EU": "2026-10-24T00:00:00+00:00"}'}).scalar()
        for h in range(24):
            s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw) VALUES(:t, :r, :p, :ts, 100, 80, 120)"),
                      {"t": tid, "r": rid, "p": pid, "ts": pd.Timestamp("2026-10-25", tz="UTC").to_pydatetime() + pd.Timedelta(hours=h)})
    yield tid, pid
    with bakim_baglami() as s:
        for t in ("forecast_values", "forecast_runs"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tid})


def test_db_tahmin_ucu_etiket_ve_hava_kaynaklari(santral):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    tid, pid = santral
    k = fs.kosu_gecmisi(tid, pid, n=1)
    assert k and k[0].etiket == "gun_ici" and dict(k[0].nwp_bilesenler) == {"ECMWF IFS": "2026-10-24T00:00:00+00:00", "ICON-EU": "2026-10-24T00:00:00+00:00"}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        j = c.get(f"/v1/plants/{pid}/forecast?hours=24").json()
        assert j["etiket"] == "gun_ici" and j["nwp_bilesenler"]["ICON-EU"].startswith("2026-10-24T00:00") and j["nwp_kosu_zamani"].startswith("2026-10-24T00:00") and j["hours"] == 24
        r = c.get(f"/v1/plants/{pid}/runs").json()
        assert r[0]["etiket"] == "gun_ici" and r[0]["nwp_bilesenler"]["ECMWF IFS"].startswith("2026-10-24")
    finally:
        api_main.app.dependency_overrides.clear()


def test_tazelik_rozeti_sozlukten():
    simdi = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
    assert ks.tazelik_durumu(datetime(2026, 11, 12, 6, 0, tzinfo=timezone.utc), simdi)["kod"] == "taze"
    g = ks.tazelik_durumu(datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc), simdi)
    assert g["kod"] == "gecikmis" and g["yas_saat"] > 48 and g["etiket"] and ks.tazelik_durumu(None)["kod"] == "eksik"
