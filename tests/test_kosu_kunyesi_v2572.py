"""v2.572 (Faz 1 F1-A, Stage 2) — koşu künyesi: forecast_runs sütunları dolu yazılır, elle koşu ana kovaya girmez, NWP yayın zamanı taşınır."""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.io.meteo import MeteoData
from pvquant.services import karne_kurali as kk


def _satir(ts, run_at, etiket=None, model="barhdadi_bennis", meteo="acik-nwp"):
    def _utc(x):
        x = pd.Timestamp(x)
        return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")
    return {"ts_utc": _utc(ts), "run_at": _utc(run_at), "etiket": etiket, "model": model, "meteo_source": meteo, "p50_kw": 1.0}


def test_elle_kosu_ana_ve_gun_ici_kovaya_girmez_programda_sayilir():
    # teslim günü 12.11 (İstanbul); gece koşusu 11.11 02:00 UTC, elle koşu 11.11 09:00 UTC (kesim 12:30 UTC öncesi), gün içi 11.11 09:30 UTC
    saatler = pd.date_range("2026-11-12 05:00", "2026-11-12 14:00", freq="h", tz="UTC")
    df = pd.DataFrame([_satir(t, "2026-11-11 02:00") for t in saatler] + [_satir(t, "2026-11-11 09:00", "elle") for t in saatler]
                      + [_satir(t, "2026-11-11 09:30", "gun_ici") for t in saatler])
    sec = kk.karne_secimi(df)
    ana = kk.ana_kovalar(sec)
    assert (ana["run_at"] == pd.Timestamp("2026-11-11 02:00", tz="UTC")).all() and len(ana) == len(saatler)   # yalnız gece koşusu
    assert set(sec.loc[sec["kova"] == kk.KOVA_GUN_ICI, "etiket"]) == {"gun_ici"}
    assert not sec["etiket"].eq("elle").any()
    prog = kk.program_kovasi(df)
    assert (prog["etiket"] == "gun_ici").all()   # kesim öncesi son koşu 09:30 gün içi; elle 09:00 ondan önce
    prog2 = kk.program_kovasi(df[df["etiket"] != "gun_ici"])
    assert (prog2["etiket"] == "elle").all() and len(prog2) == len(saatler)   # gün içi olmasaydı program kaynağı elle koşu olurdu (kgup ile aynı)


def test_sentetik_tohum_disarida():
    df = pd.DataFrame([_satir("2026-11-12 08:00", "2026-11-11 02:00", meteo="sentetik_tohum"), _satir("2026-11-12 08:00", "2026-11-11 02:00")])
    sec = kk.karne_secimi(df)
    assert len(sec) == 1 and sec.iloc[0]["meteo_source"] == "acik-nwp"
    assert kk.KURAL_SURUMU != "2026-11-10"


def _sentetik_meteo(bas: str, gun: int, kosu_zamani=None) -> MeteoData:
    ix = pd.date_range(bas, periods=gun * 24, freq="h", tz="UTC")
    saat = np.arange(len(ix)) % 24
    ghi = pd.Series(np.clip(850 * np.sin(np.pi * (saat - 3) / 12), 0, None), index=ix)
    return MeteoData(ghi=ghi, temp_air=pd.Series(20.0, index=ix), wind_speed_10m=pd.Series(3.0, index=ix), relative_humidity=None, cloud_cover=None,
                     latitude=37.0, longitude=32.0, timezone="UTC", kaynak="acik-nwp", nwp_model="test", kosu_zamani=kosu_zamani)


def test_meteodata_kosu_zamani_varsayilani_ve_arsiv_cercevesi():
    assert _sentetik_meteo("2026-11-12", 1).kosu_zamani is None
    from pvquant.io import acik_nwp
    ix = pd.date_range("2026-11-12", periods=24, freq="h", tz="UTC")
    df = pd.DataFrame({"ghi": 0.0, "temp_air": 10.0, "wind_speed_10m": 2.0}, index=ix)
    md = acik_nwp._cerceve_to_meteodata(df, 37.0, 32.0, kosu_zamani=pd.Timestamp("2026-11-11 18:00"))
    assert md.kosu_zamani == pd.Timestamp("2026-11-11 18:00", tz="UTC")
    assert acik_nwp._cerceve_to_meteodata(df, 37.0, 32.0).kosu_zamani is None


@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'kunye-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Künye GES', 1200, 1000, 37.0, 32.0, 'Europe/Istanbul', '{}')"), {"p": pid, "t": tid})
        cid = s.execute(text("INSERT INTO calibrations(tenant_id, plant_id, mode, params_json, active) VALUES(:t, :p, 'B', '{\"eta_bos\": 0.85}', true) RETURNING id"),
                        {"t": tid, "p": pid}).scalar()
    yield tid, {"id": pid, "tenant_id": tid, "name": "Künye GES", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul", "params_json": {}}, str(cid)
    with sistem_baglami() as s:
        for t in ("forecast_values", "forecast_runs", "calibrations"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_uret_ve_kaydet_kunye_yazar(santral, monkeypatch):
    tid, plant, cid = santral
    from pvquant.services import forecast_service as fs
    yayin = pd.Timestamp("2026-11-11 18:00", tz="UTC")

    class _Stub:
        def get_forecast(self, latitude, longitude, days):
            return _sentetik_meteo("2026-11-12", 3, kosu_zamani=yayin)
    monkeypatch.setattr(fs, "OpenMeteoClient", _Stub)
    monkeypatch.setenv("PVQ_SURUM", "test-abc123")
    run_id = fs.uret_ve_kaydet(tid, plant, etiket="elle")
    with sistem_baglami() as s:
        r = s.execute(text("SELECT mode, kalibrasyon_id, ml_model_id, konformal_hesap_zamani, nwp_kosu_zamani, ufuk_saat, kapasite_kwp, yazilim_surumu, etiket, "
                           "meteo_ozet_json->>'etiket' AS json_etiket, (SELECT count(*) FROM forecast_values v WHERE v.run_id=forecast_runs.id) AS n "
                           "FROM forecast_runs WHERE id=CAST(:r AS uuid)"), {"r": run_id}).mappings().one()
    assert r["mode"] == "B" and str(r["kalibrasyon_id"]) == cid and r["ml_model_id"] is None and r["konformal_hesap_zamani"] is None
    assert pd.Timestamp(r["nwp_kosu_zamani"]).tz_convert("UTC") == yayin
    assert r["ufuk_saat"] == r["n"] and r["ufuk_saat"] > 0
    assert float(r["kapasite_kwp"]) == 1200.0 and r["yazilim_surumu"] == "test-abc123"
    assert r["etiket"] == "elle" and r["json_etiket"] == "elle"


def test_yazilim_surumu_bos_ise_none(monkeypatch):
    from pvquant.surum import yazilim_surumu
    monkeypatch.setenv("PVQ_SURUM", "  ")
    assert yazilim_surumu() is None
    monkeypatch.setenv("PVQ_SURUM", "v2.572-3-gabc")
    assert yazilim_surumu() == "v2.572-3-gabc"
