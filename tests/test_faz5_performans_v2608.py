"""v2.608 (Faz 5 F5-F) — yük ölçümü (test DB, yerel): 25 santrallik kiracıda hizmet sağlığı (kiracı geneli, küme tabanlı tek sorgu/sinyal),
Genel bakış (tek santral; içinde hizmet sağlığı kiracı geneli hesaplanır) ve platform özeti süreleri. Sınırlar cömert (laptop, soğuk önbellek);
asıl çıktı `-s` ile basılan sayılar (kanit/F5-F). F5-C incelemesindeki «kiracı geneli hesap» kararı bu sayılara dayanır."""
from __future__ import annotations

import datetime as dt
import time
import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import genel_bakis_service as gb
from pvquant.services import hizmet_sagligi_service as hs

UTC = dt.timezone.utc
SIMDI = dt.datetime(2026, 11, 20, 8, 0, tzinfo=UTC)
N = 25


@pytest.fixture()
def buyuk_kiraci():
    t = str(uuid.uuid4()); pids = [str(uuid.uuid4()) for _ in range(N)]
    gun0 = dt.datetime(2026, 11, 19, 21, 0, tzinfo=UTC)
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'PERF Kiracı', 'active')"), {"t": t})
        for i, p in enumerate(pids):
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :a, 1000, 37.0, 32.0, 'Europe/Istanbul', "
                           "CAST('{\"segment\": \"lisansli_serbest\", \"uevcb\": \"40W000000000001A\"}' AS jsonb))"), {"p": p, "t": t, "a": f"PERF {i:02d}"})
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag, alinma_zamani) "
                           "SELECT CAST(:t AS uuid), :p, :s0 - make_interval(hours => g), 10, 'valid', :s0 - make_interval(hours => g) FROM generate_series(1, 168) g"),
                      {"t": t, "p": p, "s0": SIMDI})
            rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket, veri_kalitesi_json) "
                                 "VALUES(CAST(:t AS uuid), :p, :r, 'B', 'barhdadi_bennis', 'acik-nwp', '{}', 'yayin', '{}') RETURNING id"), {"t": t, "p": p, "r": SIMDI - dt.timedelta(hours=5)}).scalar()
            s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw) SELECT CAST(:t AS uuid), :r, :p, :g0 + make_interval(hours => g), 100 FROM generate_series(0, 47) g"),
                      {"t": t, "r": rid, "p": p, "g0": gun0})
            s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status) VALUES('sabah_tahmin', CAST(:t AS uuid), :p, :z, :z, 'ok')"),
                      {"t": t, "p": p, "z": SIMDI - dt.timedelta(hours=5)})
    yield t, pids
    with bakim_baglami() as s:
        for tb in ("forecast_values", "forecast_runs", "scada_hourly", "jobs_log"):
            s.execute(text(f"DELETE FROM {tb} WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        s.execute(text("DELETE FROM plants WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


def _sure(f, tekrar=3):
    en = []
    for _ in range(tekrar):
        b = time.perf_counter(); r = f(); en.append(time.perf_counter() - b)
    return r, min(en), max(en)


def test_sureler_25_santral(buyuk_kiraci):
    from pvquant.services import plant_service
    t, pids = buyuk_kiraci
    o, hmin, hmax = _sure(lambda: hs.ozet(t, simdi=SIMDI))
    assert len(o["santraller"]) == N and o["ozet"]["durum"] in ("saglikli", "veri_bekleniyor", "dikkat")
    plant = {**plant_service.getir(t, pids[0]), "id": pids[0]}
    g, gmin, gmax = _sure(lambda: gb.ozet(t, plant, simdi=SIMDI))
    assert g["bugun"]["beklenen_kwh"] == 2400.0 and g["riskler"]["kiraci"]["santral"] == N
    p, pmin, pmax = _sure(lambda: hs.platform_ozet("00000000-0000-4000-8000-000000000001", tenant_id=t, simdi=SIMDI))
    assert len(p["santraller"]) == N
    print(f"\n[F5-F yük] N={N} santral, 168 sa ölçüm + 48 sa tahmin/santral (test DB): hizmet_sagligi.ozet {hmin*1000:.0f}–{hmax*1000:.0f} ms; "
          f"genel_bakis.ozet {gmin*1000:.0f}–{gmax*1000:.0f} ms; platform_ozet(tek kiracı) {pmin*1000:.0f}–{pmax*1000:.0f} ms (3 tekrar, en az–en çok)")
    assert hmin < 3.0 and gmin < 3.0 and pmin < 3.0   # cömert sınır; gerileme yakalamak için
