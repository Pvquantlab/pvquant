"""v2.606 (Faz 4 F4-L, Stage 14) — performans ölçümü: program_df küme tabanlı sorgu eski korelasyonlu sorguyla BİREBİR (denklik; kesim öncesi/sonrası koşular,
geriye bakışlı koşu dışarıda, dünkü saat, bayraklı saat); iş süreleri (jobs_log) iş başına dağılım; elle koşu süresi ölçülür (arka plana alınmaz)."""
from __future__ import annotations

import time
import uuid

import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.ext.turkiye import kurallar as kr
from pvquant.services import dengesizlik_service as ds
from pvquant.services import isler_service
from pvquant.services import kalite_sozlugu as ks
from pvquant.services.karne_kurali import yayin_kosu_sql

TZ = "Europe/Istanbul"
_GUN_IST = "CAST(g.ts_utc AT TIME ZONE 'Europe/Istanbul' AS date)"
# v2.606 öncesi korelasyonlu biçim (dengesizlik_service'ten taşındı; üretimde yok) — denklik testinin karşılaştırma tabanı
PROGRAM_DF_SQL_ESKI = (
    f"WITH g AS (SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND {ks.sql_kosulu('uzlastirma')} "
    f"  AND ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND {ks.sql_kosulu('uzlastirma')}) - (:g * INTERVAL '1 day')) "
    "SELECT g.ts_utc, g.power_kw AS gercek_kw, "
    " (SELECT f.p50_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
    f"   WHERE f.plant_id=:p AND f.ts_utc=g.ts_utc AND {yayin_kosu_sql('r')} "
    "   AND r.run_at <= ((date_trunc('day', g.ts_utc AT TIME ZONE 'Europe/Istanbul') - INTERVAL '1 day' "
    f"     + {kr.kgup_kesim_sql(_GUN_IST)}) AT TIME ZONE 'Europe/Istanbul') "
    "   ORDER BY r.run_at DESC LIMIT 1) AS kgup_kw, "
    f" (SELECT s2.power_kw FROM scada_hourly s2 WHERE s2.plant_id=:p AND {ks.sql_kosulu('uzlastirma', 's2')} AND s2.ts_utc = g.ts_utc - INTERVAL '24 hour') AS naif_kw "
    "FROM g ORDER BY g.ts_utc")


@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'perf-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'PERF GES', 1000, 37.0, 32.0, :tz, '{}')"), {"p": pid, "t": tid, "tz": TZ})
        for g in range(1, 8):   # 1–7 Eylül 2026; 3 Eylül 12:00 bayraklı; 5 Eylül SCADA yok (program yalnız ölçümlü saatlere kurulur)
            if g == 5:
                continue
            for h in range(24):
                ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=TZ).tz_convert("UTC").to_pydatetime()
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, :f, 60)"),
                          {"t": tid, "p": pid, "ts": ts, "kw": float(10 * g + h), "f": ("frozen_value" if (g == 3 and h == 12) else "valid")})
            gun0 = pd.Timestamp(f"2026-09-{g:02d}", tz=TZ)
            # üç koşu (D-1 = teslim gününden önceki gün, UTC takvimi: gun0 = D 00:00 TSİ = D-1 21:00 UTC → normalize D-1 00:00 UTC):
            # D-1 03:00 UTC (kesim 12:30 UTC öncesi, p50 = 1000+h), D-1 13:00 UTC = 16:00 TSİ (kesim SONRASI, p50 = 2000+h), D-1 10:00 UTC backtest (dışarıda)
            d1 = gun0.tz_convert("UTC").normalize()
            for ra, etiket, taban in ((d1 + pd.Timedelta(hours=3), "yayin", 1000.0), (d1 + pd.Timedelta(hours=13), "yayin", 2000.0), (d1 + pd.Timedelta(hours=10), "backtest", 3000.0)):
                rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket) "
                                     "VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}', :e) RETURNING id"), {"t": tid, "p": pid, "ra": ra.to_pydatetime(), "e": etiket}).scalar()
                for h in range(24):
                    ts = (gun0 + pd.Timedelta(hours=h)).tz_convert("UTC").to_pydatetime()
                    s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw) VALUES(:t, :r, :p, :ts, :kw, :kw, :kw)"),
                              {"t": tid, "r": rid, "p": pid, "ts": ts, "kw": taban + h})
    yield tid, pid
    with bakim_baglami() as s:
        for t in ("forecast_values", "forecast_runs", "scada_hourly", "jobs_log"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tid})


def _eski(tid, pid, gun=90):
    from pvquant.db import tenant_baglami
    with tenant_baglami(tid) as s:
        return pd.read_sql(text(PROGRAM_DF_SQL_ESKI), s.connection(), params={"p": pid, "g": gun}, parse_dates=["ts_utc"])


def test_db_program_df_kume_tabanli_eskiyle_birebir(santral):
    tid, pid = santral
    t0 = time.perf_counter(); eski = _eski(tid, pid); t_eski = time.perf_counter() - t0
    t0 = time.perf_counter(); yeni = ds.program_df(tid, pid, gun=90); t_yeni = time.perf_counter() - t0
    eski["ts_utc"] = pd.to_datetime(eski["ts_utc"], utc=True)
    assert len(yeni) == 6 * 24 - 1 == len(eski)   # 6 gün ölçüm, 3 Eylül 12:00 bayraklı dışarıda
    pd.testing.assert_frame_equal(yeni[["ts_utc", "gercek_kw", "kgup_kw", "naif_kw"]].reset_index(drop=True), eski[["ts_utc", "gercek_kw", "kgup_kw", "naif_kw"]].reset_index(drop=True))
    # program yalnız kesim öncesi YAYIN koşusundan: p50 = 1000 + saat (16:00 TSİ koşusu ve backtest dışarıda)
    ist = yeni["ts_utc"].dt.tz_convert(TZ)
    assert ((yeni["kgup_kw"] - 1000.0) == ist.dt.hour.astype(float)).all()
    # dünkü aynı saat: 2 Eylül için 1 Eylül değeri; 1 Eylül için yok; 6 Eylül için 5 Eylül yok (ölçüm yok)
    g2 = yeni[ist.dt.day == 2]; g1 = yeni[ist.dt.day == 1]; g6 = yeni[ist.dt.day == 6]
    assert (g2["naif_kw"].values == (10 + ist[g2.index].dt.hour).astype(float).values).all() and g1["naif_kw"].isna().all() and g6["naif_kw"].isna().all()
    assert yeni[(ist.dt.day == 4) & (ist.dt.hour == 12)]["naif_kw"].isna().all()   # 3 Eylül 12:00 bayraklı → dünkü saat yok
    print(f"program_df süre eski={t_eski * 1000:.1f} ms yeni={t_yeni * 1000:.1f} ms (test DB, 143 saat)")


def test_db_is_sureleri_ve_sonuc_ozeti(santral):
    tid, pid = santral
    with sistem_baglami() as s:
        # göreli zaman damgaları (sabit tarih pencere dışına düşerdi); ortalama için tekil iş kodu (tenant'sız başka satır karışmasın)
        for job, bas_sa, sure_sn, st, sj in (("gece_skill", 3, 42, "ok", '{"durum": "ok", "n": 12, "not": "x"}'),
                                             ("gece_skill", 27, 90, "error", None),
                                             ("perf_test_isi", 2, 5, "ok", '{"durum": "ok", "yazilan": 72}'),
                                             ("perf_test_isi", 1, 5, "error", None)):   # jobs_log.status NOT NULL; hata = status ≠ ok
            s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status, detail, sonuc_json) "
                           "VALUES(:j, CAST(:t AS uuid), NULL, now() - (:b * INTERVAL '1 hour'), now() - (:b * INTERVAL '1 hour') + (:d * INTERVAL '1 second'), :s, '', CAST(:sj AS jsonb))"),
                      {"j": job, "t": tid, "b": bas_sa, "d": sure_sn, "s": st, "sj": sj})
    su = {x["kod"]: x for x in isler_service.sureler(tid, gun=7)}
    assert su["gece_skill"]["n"] >= 2 and su["gece_skill"]["hata"] >= 1 and su["gece_skill"]["en_uzun_sn"] >= 90.0 and su["gece_skill"]["is"] == "Gece karnesi"
    assert su["perf_test_isi"] == {"is": "perf_test_isi", "kod": "perf_test_isi", "n": 2, "hata": 1, "ort_sn": 5.0, "en_uzun_sn": 5.0, "son": su["perf_test_isi"]["son"]}
    assert isler_service._sonuc_ozeti('{"durum": "ok", "n": 12, "not": "x", "bayrak": true}') == {"durum": "ok", "n": 12}
    assert isler_service._sonuc_ozeti(None) is None and isler_service._sonuc_ozeti("bozuk{") is None
    o = isler_service.ozet(tid, saat=48)
    assert "sureler" in o and any(x["sonuc"] == {"durum": "ok", "yazilan": 72} for x in o["isler"])


def test_db_elle_kosu_suresi_olculur(santral, monkeypatch):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    tid, pid = santral
    monkeypatch.setattr("pvquant.services.forecast_service.uret_ve_kaydet", lambda t, row, etiket=None: (time.sleep(0.05), "22222222-2222-2222-2222-222222222222")[1])
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": tid, "role": "admin", "exp": 0}
    try:
        r = TestClient(api_main.app).post(f"/v1/plants/{pid}/forecast/run"); assert r.status_code == 200, r.text
        assert r.json()["sure_sn"] >= 0.05
        from pvquant.services import denetim_service as dz
        iz = dz.listele(tenant_id=tid, eylem="elle_kosu")[0]
        assert iz["ayrinti"]["sure_sn"] >= 0.05 and iz["ayrinti"]["run_id"].startswith("22222222")
    finally:
        api_main.app.dependency_overrides.clear()
        with bakim_baglami() as s:
            s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})


def test_saatlik_hesap_fiyati_eksik_saat_dusunce_hizalama_bozulmaz():
    """Canlı 12.11 03:55 (v2.587 gece_finansal_etki): bir santralda 2 saatin fiyatı yoktu → d.saatlik 22 satır döndü, 24 değerlik konumsal
    atama ValueError verdi. Çerçeve kısa kalınca kalan saatler indeksle hizalanır; düşen saat hesaba girmez (sessizce 0 sayılmaz)."""
    idx = pd.date_range("2026-11-11", periods=24, freq="h", tz="UTC")
    df = pd.DataFrame({"ts_utc": idx, "gercek_kw": 100.0, "kgup_kw": 90.0, "naif_kw": 95.0})
    fiyat = pd.DataFrame({"ptf": 2000.0, "smf": 2100.0, "yon": "acik"}, index=idx)
    fiyat.loc[idx[5:7], ["ptf", "smf"]] = float("nan")   # iki saat fiyatsız
    pv, _, x, _ = ds.saatlik_hesap(df, fiyat, segment="lisansli")
    assert len(x) == 24 and len(pv) == 22 and idx[5] not in pv.index and idx[7] in pv.index
    assert (pv["oneri"] == 0.09).all() and (pv["program_kaynak"] == "oneri").all() and pv["uecm"].fillna(0).eq(0).all()

