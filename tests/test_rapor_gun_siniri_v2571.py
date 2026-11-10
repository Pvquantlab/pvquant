"""v2.571 (Faz 0 onay paketi 3, VZ-05/VZ-06) — rapor günü santralın yerel günüdür; Türkiye'de çıktı değişmez, yabancı santralde bölünme kalkar."""
from __future__ import annotations

import inspect
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import aylik_rapor_service as ar
from pvquant.services import report_service as rp
from pvquant.services import sablon_rapor_service as sr


def _seri(tz: str, gunler: list[str], uretim_saat=range(6, 19), kw: float = 100.0) -> pd.DataFrame:
    """Yerel günlerin TÜM saatleri; üretim yalnız uretim_saat aralığında (gece 0). Indeks UTC (forecast_values gibi)."""
    ix = pd.DatetimeIndex([], tz=tz)
    for g in gunler:
        d0 = pd.Timestamp(g).tz_localize(tz); d1 = (pd.Timestamp(g) + pd.Timedelta(days=1)).tz_localize(tz)
        ix = ix.append(pd.date_range(d0, d1, freq="h", inclusive="left"))
    ix = ix.tz_convert("UTC")
    yerel_saat = ix.tz_convert(tz).hour
    e = pd.Series([kw if h in uretim_saat else 0.0 for h in yerel_saat], index=ix)
    return pd.DataFrame({"energy_kwh": e, "p10_kw": e * 0.8, "p90_kw": e * 1.2})


def test_denver_iki_yerel_gun_bolunmez():
    h = _seri("America/Denver", ["2025-07-15", "2025-07-16"])
    gr, tam = rp._tam_yerel_gunler(h, "America/Denver")
    assert list(tam) == [date(2025, 7, 15), date(2025, 7, 16)]
    daily = h["energy_kwh"].groupby(gr).sum().loc[tam]
    assert daily.tolist() == [1300.0, 1300.0]
    # eski UTC gruplaması aynı seriyi üç güne bölüyordu (1200 / 1300 / 100) ve 24-saat süzgeci tek gün bırakıyordu — Faz 0 kanıtı
    utc_gun = h["energy_kwh"].groupby(h.index.tz_convert("UTC").date).sum()
    assert len(utc_gun) == 3 and sorted(utc_gun.tolist()) == [100.0, 1200.0, 1300.0]


def test_yaz_saati_gecis_gunleri_tam_sayilir():
    for g, saat in (("2025-03-09", 23), ("2025-11-02", 25)):
        h = _seri("America/Denver", [g])
        assert len(h) == saat
        _, tam = rp._tam_yerel_gunler(h, "America/Denver")
        assert list(tam) == [date.fromisoformat(g)]
    # 2 saat eksik gün tam değildir
    h = _seri("America/Denver", ["2025-07-15"]).iloc[:-2]
    assert len(rp._tam_yerel_gunler(h, "America/Denver")[1]) == 0


def test_istanbul_eski_ve_yeni_gruplama_birebir():
    """Türkiye (+03, yaz saati yok): üretim saatleri aynı UTC gününde kalır → yerel gün toplamları eski UTC gün toplamlarıyla özdeş (gece 0)."""
    h = _seri("Europe/Istanbul", ["2026-10-05", "2026-10-06", "2026-10-07"])
    gr, tam = rp._tam_yerel_gunler(h, "Europe/Istanbul")
    yeni = h["energy_kwh"].groupby(gr).sum().loc[tam]
    assert list(tam) == [date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)] and yeni.tolist() == [1300.0] * 3
    eski = h["energy_kwh"].groupby(h.index.tz_convert("UTC").date).sum()
    for g in tam:   # eski anahtar aynı tarih, aynı toplam (üretim 06–18 TSİ = 03–15 UTC, aynı gün)
        assert eski.loc[g] == yeni.loc[g]


def test_sablon_ve_aylik_sabit_istanbul_kullanmaz():
    k = inspect.getsource(sr.beklenen_gerceklesen)
    assert "AT TIME ZONE :tz" in k and "'Europe/Istanbul'" not in k
    k2 = inspect.getsource(ar.gunluk)
    assert "AT TIME ZONE :tz" in k2 and "'Europe/Istanbul'" not in k2
    assert ar.donem_cozumle("2026-10", date(2026, 11, 2), "America/Denver")["saat"] == 744
    assert ar.donem_cozumle("2025-03", date(2025, 4, 2), "America/Denver")["saat"] == 743    # yaz saati başlangıcı: 23 saatlik gün
    assert ar.donem_cozumle("2025-03", date(2025, 4, 2))["saat"] == 744                      # İstanbul: değişmez


@pytest.fixture()
def denver():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    tz = "America/Denver"
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'tz-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Golden GES', 1000, 1000, 39.7, -105.2, :tz, '{}')"), {"p": pid, "t": tid, "tz": tz})
        # 15–16 Temmuz 2025 yerel 06–19 saatlik 100 kWh → 1.300 kWh/gün; UTC'de 15 Temmuz 12:00 – 16 Temmuz 01:00 ve 16 Temmuz 12:00 – 17 Temmuz 01:00
        for g in (15, 16):
            for h in range(6, 19):
                ts = pd.Timestamp(datetime(2025, 7, g, h)).tz_localize(tz).tz_convert("UTC").to_pydatetime()
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag) VALUES(:t, :p, :ts, 100, 100, 'valid')"), {"t": tid, "p": pid, "ts": ts})
        rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, mode, model) VALUES (CAST(:t AS uuid), :p, 'C', 'test') RETURNING id"), {"t": tid, "p": pid}).scalar()
        for g in (15, 16):
            s.execute(text("INSERT INTO forecast_daily(tenant_id, plant_id, gun, p50_kwh, p10_kwh, p90_kwh, run_id, saat_sayisi) VALUES(:t, :p, :g, 1300, 1100, 1500, :r, 24)"),
                      {"t": tid, "p": pid, "g": date(2025, 7, g), "r": rid})
    yield tid, {"id": pid, "name": "Golden GES", "capacity_kwp": 1000.0, "ac_limit_kw": 1000.0, "tz": tz, "params_json": {}}
    with sistem_baglami() as s:
        for t in ("forecast_daily", "forecast_runs", "scada_hourly"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_aylik_gunluk_denver_gunleri_bolunmez(denver):
    tid, plant = denver
    df = ar.gunluk(tid, plant, date(2025, 7, 14), date(2025, 7, 18))
    g = df.set_index("gun")
    assert g.loc[date(2025, 7, 15), "kwh"] == 1300 and g.loc[date(2025, 7, 16), "kwh"] == 1300
    assert int(g.loc[date(2025, 7, 15), "saat"]) == 13 and int(g.loc[date(2025, 7, 16), "saat"]) == 13
    assert pd.isna(g.loc[date(2025, 7, 17), "kwh"]) and int(g.loc[date(2025, 7, 17), "saat"]) == 0   # İstanbul günüyle kesilseydi 17'ye 2 saat taşardı
    assert g.loc[date(2025, 7, 15), "sapma_pct"] == 0.0 and g.loc[date(2025, 7, 16), "sapma_pct"] == 0.0
    # dönem sınırı santral gününde: 16 Temmuz tek gün → 1.300 kWh, 13 saat (UTC 17 Temmuz 00–01'e taşan iki saat dâhil)
    tek = ar.gunluk(tid, plant, date(2025, 7, 16), date(2025, 7, 17))
    assert len(tek) == 1 and tek.iloc[0]["kwh"] == 1300 and int(tek.iloc[0]["saat"]) == 13
