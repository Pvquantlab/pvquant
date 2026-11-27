"""Faz 1 Mod B — veri sözleşmesi regresyonları (28.11.2026; formül/parametre/eşik değişmedi).

Kanıtlanmış iki adapter kusuru ve pinleri:
  F1 `SCADAData.to_hourly`: hiç örneği olmayan / tüm örnekleri NaN olan saatte enerji 0 yazılıyordu (güç NaN iken) → NaN kalır.
  F2 `OpenMeteoClient._parse_response`: yerel saat dilimli yanıtta DST ayıklaması sonrası `tz_localize('infer')` düşünce yerel saat
     sessizce UTC sayılıyordu (Berlin örneğinde 2 sa kayma) → açık OpenMeteoError. Üretim yolu UTC ister; UTC yanıt davranışı pinlenir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.io.meteo import OpenMeteoClient, OpenMeteoError
from pvquant.io.scada import SCADAData


def _scada(power: pd.Series, energy: pd.Series, adim: int = 15) -> SCADAData:
    return SCADAData(power_kw=power, energy_kwh=energy, poa_irradiance=None, temp_ambient=None, temp_module=None,
                     wind_speed=None, plant_name="t", timestep_minutes=adim)


def test_to_hourly_satiri_olmayan_saat_enerji_nan_kalir():
    t = pd.date_range("2025-06-01 08:00", periods=16, freq="15min", tz="UTC")
    t = t[t.hour != 10]                                   # 10:00–10:45 hiç satır yok
    h = _scada(pd.Series(100.0, index=t), pd.Series(25.0, index=t)).to_hourly()
    assert h.timestep_minutes == 60
    assert np.isnan(h.power_kw.loc["2025-06-01 10:00"])
    assert np.isnan(h.energy_kwh.loc["2025-06-01 10:00"])          # eskiden 0.0 (uydurma)
    assert h.energy_kwh.loc["2025-06-01 08:00"] == pytest.approx(100.0)   # 4 × 25 kWh korunur
    assert h.power_kw.loc["2025-06-01 08:00"] == pytest.approx(100.0)


def test_to_hourly_tum_ornekleri_nan_saat_enerji_nan_kismi_saat_toplanir():
    t = pd.date_range("2025-06-01 08:00", periods=16, freq="15min", tz="UTC")
    e = pd.Series(25.0, index=t)
    e[t.hour == 9] = np.nan                               # saat var, ölçüm yok
    e.iloc[12] = np.nan                                   # 11:00 kovasında 1 örnek eksik → kalan 3 toplanır (75)
    h = _scada(pd.Series(100.0, index=t), e).to_hourly()
    assert np.isnan(h.energy_kwh.loc["2025-06-01 09:00"])
    assert h.energy_kwh.loc["2025-06-01 11:00"] == pytest.approx(75.0)
    assert h.energy_kwh.loc["2025-06-01 08:00"] == pytest.approx(100.0)


def _yanit(tz: str, bas: str = "2024-10-27 00:00", n: int = 8) -> dict:
    times = pd.date_range(bas, periods=n, freq="h")
    return {"hourly": {"time": [x.strftime("%Y-%m-%dT%H:%M") for x in times],
                       "shortwave_radiation": [0, 0, 0, 0, 0, 10, 50, 100][:n],
                       "temperature_2m": [1.0] * n, "wind_speed_10m": [1.0] * n},
            "timezone": tz, "latitude": 52.5, "longitude": 13.4}


def test_open_meteo_yerel_tz_dst_belirsizligi_sessizce_utc_sayilmaz():
    # 27.10.2024 Europe/Berlin: 02:00 iki kez yaşanır; Open-Meteo tekini verir → 'infer' çözemez. Eskiden dizi UTC etiketlenirdi (2 sa hata).
    with pytest.raises(OpenMeteoError, match="Europe/Berlin"):
        OpenMeteoClient()._parse_response(_yanit("Europe/Berlin"))


def test_open_meteo_utc_yanit_davranisi_pinli_ghi_aralik_basi():
    m = OpenMeteoClient()._parse_response(_yanit("UTC"))
    assert str(m.ghi.index.tz) == "UTC"
    assert m.ghi.index[0] == pd.Timestamp("2024-10-27 00:00", tz="UTC")
    # v2.382 sözleşmesi: Open-Meteo «önceki saat ortalaması» t damgası → aralık başı: değer bir saat geri alınır, son saat 0.
    assert m.ghi.iloc[-2] == pytest.approx(100.0) and m.ghi.iloc[-1] == 0.0
    assert m.temp_air.iloc[0] == 1.0 and m.wind_speed_10m.iloc[0] == 1.0


def test_open_meteo_yerel_tz_belirsizlik_yoksa_dogru_yerellesir():
    # DST geçişi olmayan gün: yerel saat dilimi doğru uygulanır (Berlin 01.07 00:00 = 30.06 22:00 UTC)
    m = OpenMeteoClient()._parse_response(_yanit("Europe/Berlin", bas="2024-07-01 00:00"))
    assert m.ghi.index[0].tz_convert("UTC") == pd.Timestamp("2024-06-30 22:00", tz="UTC")
