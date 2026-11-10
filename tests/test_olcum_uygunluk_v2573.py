"""v2.573 (Faz 1 F1-B, Stage 3) — ölçüm uygunluk katmanı: saat durumu/nedeni, kapsama ve kısmi saat, olay dışlaması, eksik saat 0 sayılmaz."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.io.ingestion import RowFlag, ingest_file
from pvquant.services import olcum_uygunluk_service as ou

UTC = timezone.utc


def _ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_siniflandir_oncelik_eksik_bayrak_kismi_olay():
    iz = ou.saat_izgarasi("2026-11-12 00:00", "2026-11-12 07:00")
    o = pd.DataFrame({"power_kw": [0, 10, 20, 30, 40, 50], "energy_kwh": [None, 10, None, 30, 40, None],
                      "flag": ["valid", "over_capacity", "valid", "valid", "valid", "valid"],
                      "kirpma": [False, False, True, False, False, True], "kapsama_dk": [60, 60, 30, None, 60, 45]},
                     index=pd.DatetimeIndex(["2026-11-12 00:00", "2026-11-12 01:00", "2026-11-12 02:00", "2026-11-12 03:00", "2026-11-12 04:00", "2026-11-12 05:00"]))
    olaylar = {_ts("2026-11-12 04:00"): "ariza", _ts("2026-11-12 01:00"): "planli_bakim"}   # 01:00 zaten bayraklı → bayrak kazanır
    df = ou.siniflandir(iz, o, olaylar)
    assert list(df["neden"]) == ["olculdu", "bayrak:over_capacity", "kismi_saat", "olculdu", "olay:ariza", "olculdu", "eksik"]
    assert df.loc[6, "kwh"] != df.loc[6, "kwh"]   # eksik saat NaN (0 değil)
    assert df.loc[2, "kwh"] == 20.0 and df.loc[3, "kwh"] == 30.0 and df.loc[5, "neden"] == "olculdu"   # 45 dk sınırda geçerli
    d = ou.dokum(df)
    assert d["beklenen_saat"] == 7 and d["olculdu_saat"] == 3 and d["kapsama_pct"] == 42.9
    assert d["dislanan"] == {"bayrak:over_capacity": 1, "eksik": 1, "kismi_saat": 1, "olay:ariza": 1}
    assert d["kirpma_saat"] == 2 and d["kapsama_bilinmeyen_saat"] == 1 and d["sinir"] == "plant_gross_ac"
    bos = ou.siniflandir(iz, None)
    assert (bos["neden"] == "eksik").all() and bos["kwh"].isna().all() and ou.dokum(bos)["kapsama_pct"] == 0.0


def test_siniflandir_sayac_niteligi():
    iz = ou.saat_izgarasi("2026-11-12 00:00", "2026-11-12 04:00")
    o = pd.DataFrame({"veris_kwh": [100.0, 110.0, 120.0], "nitelik": ["olculmus", "tahmini", "doldurulmus"]},
                     index=pd.DatetimeIndex(["2026-11-12 00:00", "2026-11-12 01:00", "2026-11-12 02:00"], tz="UTC"))
    df = ou.siniflandir(iz, o, {_ts("2026-11-12 00:00"): "talimat_yat"}, kaynak="sayac")
    assert list(df["neden"]) == ["olay:talimat_yat", "sayac:tahmini", "sayac:doldurulmus", "eksik"]
    d = ou.dokum(df, "sayac")
    assert d["sinir"] == "pcc_net" and d["olculdu_saat"] == 0 and d["dislanan"]["sayac:tahmini"] == 1


def test_olay_saatleri_birlesik_ve_sinir():
    olaylar = [{"tur": "ariza", "baslangic": datetime(2026, 11, 12, 9, 20, tzinfo=UTC), "bitis": datetime(2026, 11, 12, 11, 5, tzinfo=UTC)},
               {"tur": "sebeke_kesintisi", "baslangic": datetime(2026, 11, 12, 10, 0, tzinfo=UTC), "bitis": None}]
    s = ou.olay_saatleri(olaylar, datetime(2026, 11, 12, 10, 0, tzinfo=UTC), datetime(2026, 11, 12, 13, 0, tzinfo=UTC))
    assert s == {_ts("2026-11-12 10:00"): "ariza+sebeke_kesintisi", _ts("2026-11-12 11:00"): "ariza+sebeke_kesintisi", _ts("2026-11-12 12:00"): "sebeke_kesintisi"}
    assert "uzaktan_acma" not in ou.olay_turleri() and {"ariza", "planli_bakim", "talimat_yat", "acil_kesme", "sebeke_kesintisi", "hasar"} <= set(ou.olay_turleri())


def test_15dk_kapsama_kismi_saat_ve_bos_saat_enerjisi(tmp_path):
    times = pd.date_range("2025-05-01", periods=3 * 96, freq="15min", tz="UTC")
    hour = np.array(times.hour) + np.array(times.minute) / 60
    bell = np.clip(np.sin(np.pi * (hour - 3.3) / 13), 0, None) ** 1.6
    power = 4514.0 * 0.8 * bell
    df = pd.DataFrame({"Time": times.tz_localize(None).strftime("%Y-%m-%d %H:%M"), "Active Power (kW)": power.round(2), "Yield(kWh)": (power * 0.25).round(3)})
    # 2 Mayıs 10:xx yalnız :00 (15 dk), 11:xx :00 ve :15 (30 dk), 12:xx üç örnek (45 dk), 13:xx hiç yok
    g = pd.to_datetime(df["Time"])
    df = df[~((g.dt.day == 2) & (g.dt.hour == 10) & (g.dt.minute > 0))]
    df = df[~((g.dt.day == 2) & (g.dt.hour == 11) & (g.dt.minute > 15))]
    df = df[~((g.dt.day == 2) & (g.dt.hour == 12) & (g.dt.minute == 45))]
    df = df[~((g.dt.day == 2) & (g.dt.hour == 13))]
    path = tmp_path / "p15.csv"; df.to_csv(path, index=False)
    r = ingest_file(path, capacity_kwp=4514.0, latitude=37.87, longitude=32.49, source_timezone="UTC")
    d = r.data
    assert "kapsama_dk" in d.columns
    k = {h: d.loc[pd.Timestamp(f"2025-05-02 {h:02d}:00", tz="UTC")] for h in (9, 10, 11, 12, 13)}
    assert k[9]["kapsama_dk"] == 60 and k[9]["flag"] == RowFlag.VALID.value
    assert k[10]["kapsama_dk"] == 15 and k[10]["flag"] == RowFlag.PARTIAL_HOUR.value
    assert k[11]["kapsama_dk"] == 30 and k[11]["flag"] == RowFlag.PARTIAL_HOUR.value
    assert k[12]["kapsama_dk"] == 45 and k[12]["flag"] == RowFlag.VALID.value
    assert pd.isna(k[13]["kapsama_dk"]) and k[13]["flag"] == RowFlag.UNPARSEABLE.value and pd.isna(k[13]["energy_kwh"])   # boş saat 0 değil
    assert any("kısmi saat" in w for w in r.report.warnings) and r.report.flag_counts.get("partial_hour") == 2


def test_saatlik_kaynak_kapsama_60(tmp_path):
    times = pd.date_range("2025-05-01", periods=48, freq="1h", tz="UTC")
    df = pd.DataFrame({"Time": times.tz_localize(None).strftime("%Y-%m-%d %H:%M"), "Active Power (kW)": np.clip(np.sin(np.pi * (times.hour - 3) / 13), 0, None) * 3000})
    path = tmp_path / "p60.csv"; df.to_csv(path, index=False)
    r = ingest_file(path, capacity_kwp=4514.0, latitude=37.87, longitude=32.49, source_timezone="UTC")
    assert (r.data["kapsama_dk"] == 60).all() and "partial_hour" not in r.report.flag_counts


@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'uygunluk-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Uygunluk GES', 1000, 900, 37.0, 32.0, 'Europe/Istanbul', '{}')"), {"p": pid, "t": tid})
        satir = [("2026-10-05 06:00", 100, "valid", False, 60), ("2026-10-05 07:00", 500, "over_capacity", False, 60), ("2026-10-05 08:00", 600, "valid", True, 30),
                 ("2026-10-05 09:00", 700, "valid", False, None), ("2026-10-05 10:00", 0, "valid", False, 60)]   # 11:00 yok
        for ts, kw, fl, kr, kap in satir:
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kirpma, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, :f, :k, :kap)"),
                      {"t": tid, "p": pid, "ts": datetime.fromisoformat(ts).replace(tzinfo=UTC), "kw": kw, "f": fl, "k": kr, "kap": kap})
        s.execute(text("INSERT INTO olay(tenant_id, plant_id, tur, baslangic, bitis, durum, eak_gerekcesi) VALUES(:t, :p, 'ariza', :b, :e, 'kapali', 'kaynak_yetersizligi'), "
                       "(:t, :p, 'planli_bakim', :b2, :e2, 'iptal', 'kaynak_yetersizligi')"),
                  {"t": tid, "p": pid, "b": datetime(2026, 10, 5, 10, 10, tzinfo=UTC), "e": datetime(2026, 10, 5, 10, 50, tzinfo=UTC),
                   "b2": datetime(2026, 10, 5, 6, 0, tzinfo=UTC), "e2": datetime(2026, 10, 5, 7, 0, tzinfo=UTC)})   # iptal olay sayılmaz
    yield tid, {"id": pid, "name": "Uygunluk GES", "capacity_kwp": 1000.0}
    with sistem_baglami() as s:
        for t in ("olay", "scada_hourly"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_saat_durumlari_db(santral):
    tid, plant = santral
    df, d = ou.saat_durumlari(tid, plant, datetime(2026, 10, 5, 6, tzinfo=UTC), datetime(2026, 10, 5, 12, tzinfo=UTC))
    assert list(df["neden"]) == ["olculdu", "bayrak:over_capacity", "kismi_saat", "olculdu", "olay:ariza", "eksik"]
    assert d["beklenen_saat"] == 6 and d["olculdu_saat"] == 2 and d["kirpma_saat"] == 1 and d["kapsama_bilinmeyen_saat"] == 1
    assert d["dislanan"] == {"bayrak:over_capacity": 1, "eksik": 1, "kismi_saat": 1, "olay:ariza": 1}
    assert pd.isna(df.loc[5, "kwh"]) and df.loc[4, "kwh"] == 0.0   # eksik NaN; olaylı saat değeri korunur ama dışlanır
