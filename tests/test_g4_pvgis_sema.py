"""G4-P1 (26.11.2026) — PVGIS 5.3 bileşen şeması (poa_global yok) ve saat ortası damgası: sarmalayıcı ağsız sınanır."""
import pandas as pd

from pvquant.ext.kaynak import uydu_isinim as ui


def _sahte(*a, **k):
    idx = pd.date_range("2018-06-21 12:30", periods=24, freq="h", tz="UTC")                 # 05:30–04:30 yerel (Etc/GMT+7)
    df = pd.DataFrame({"poa_direct": [0.0] * 2 + [500.0] * 11 + [0.0] * 11, "poa_sky_diffuse": [0.0] * 2 + [100.0] * 11 + [0.0] * 11,
                       "poa_ground_diffuse": 0.0, "solar_elevation": 0.0, "temp_air": 20.0, "wind_speed": 2.0, "Int": 0}, index=idx)
    df.index.name = "time"
    return df, {"inputs": {}}


def test_bilesen_semasi_ve_saat_basi(monkeypatch):
    monkeypatch.setattr(ui.pvlib.iotools, "get_pvgis_hourly", _sahte)
    c = ui.pvgis_saatlik(39.74, -105.18, 2018, 2018, veri_tabani="PVGIS-ERA5")
    assert list(c.df.index[:2]) == [pd.Timestamp("2018-06-21 12:00", tz="UTC"), pd.Timestamp("2018-06-21 13:00", tz="UTC")]   # :30 → :00
    assert 550.0 <= c.df["ghi"].max() <= 600.0 and (c.df["ghi"] >= c.df["dhi"]).all() and c.df["ghi"].iloc[0] == 0.0
    assert c.df["temp_air"].iloc[0] == 20.0 and c.df["wind_speed_10m"].iloc[0] == 2.0


def test_eski_sema_poa_global_ve_saat_basi_saf(monkeypatch):
    def eski(*a, **k):
        df, m = _sahte()
        df["poa_global"] = df["poa_direct"] + df["poa_sky_diffuse"] + 1.0
        return df.drop(columns=["poa_direct"]), m
    monkeypatch.setattr(ui.pvlib.iotools, "get_pvgis_hourly", eski)
    c = ui.pvgis_saatlik(39.74, -105.18, 2018, 2018)
    assert 550.0 <= c.df["ghi"].max() <= 601.0
    i = ui.pvgis_saat_basi(pd.DatetimeIndex(["2018-01-01 05:10", "2018-01-01 06:30"]))
    assert str(i.tz) == "UTC" and list(i.hour) == [5, 6] and list(i.minute) == [0, 0]
