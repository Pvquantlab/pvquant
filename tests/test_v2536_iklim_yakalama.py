"""v2.536 — 04.11 canlı bulguları: (1) PVGIS «time» adlı indeksle aylık toplam (pandas 3'te düşüyordu), (2) SARAH-3 kapsam dışında
PVGIS-ERA5 yedeği, (3) açılış yakalaması cron slotunu kaçıran işi görür."""
import numpy as np
import pandas as pd
import pvlib
import pytest
import requests

from pvquant.io import arsiv_isinim
from pvquant.services import isler_service
from pvquant.services.iklim_service import aylik_toplamlar, iklim_hesapla


def test_aylik_toplamlar_time_adli_indeksle():
    ix = pd.date_range("2020-01-01", "2020-12-31 23:00", freq="h", tz="UTC", name="time")   # PVGIS/pvlib indeks adı
    df = pd.DataFrame({"ghi": 300.0}, index=ix)
    t = aylik_toplamlar(df, tz="Europe/Istanbul")
    assert list(t.columns) == ["yil", "ay", "ghi_kwh_m2"] and len(t[t["yil"] == 2020]) == 12   # tz kayması 2021-01 kıymığı ekler (tam_yillar atar)
    assert t.loc[(t["yil"] == 2020) & (t["ay"] == 7), "ghi_kwh_m2"].iloc[0] == pytest.approx(31 * 24 * 300 / 1000)


def _sarah_disi(*a, **k):
    raise requests.HTTPError("Location out of the spatial coverage of the radiation database selected. Please, selectanother database (PVGIS-ERA5).")


def _pvgis_sahte(lat, lon, raddatabase=None, **k):
    if raddatabase == "PVGIS-SARAH3" and lon < -30:   # Meteosat alanı dışı (Colorado)
        _sarah_disi()
    ix = pd.date_range("2023-06-01 00:30", periods=48, freq="h", tz="UTC", name="time")   # ERA5 damgası saat ortası
    yuk = np.clip(60 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None)
    return pd.DataFrame({"poa_direct": np.where(yuk > 0, 500.0, 0.0), "poa_sky_diffuse": np.where(yuk > 0, 100.0, 0.0),
                         "poa_ground_diffuse": 0.0, "solar_elevation": yuk, "temp_air": 25.0, "wind_speed": 2.0, "Int": 0}, index=ix), {}


def test_pvgis_era5_yedegi(monkeypatch):
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", _pvgis_sahte)
    tr = arsiv_isinim.pvgis_df(37.87, 32.49, 2023, 2023)
    assert tr.attrs["kaynak"] == "pvgis-sarah3" and "ghi" in tr
    co = arsiv_isinim.pvgis_df(39.74, -105.18, 2023, 2023)             # PVDAQ Golden: SARAH-3 dışı → ERA5
    assert co.attrs["kaynak"] == "pvgis-era5" and "ERA5" in co.attrs["etiket"] and len(co) == len(tr) and co["ghi"].max() > 0
    # kapsam dışı değil, başka HTTP hatası → yükselir (sessizce ERA5'e düşmez)
    def _baska(*a, **k): raise requests.HTTPError("Server error")
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", _baska)
    with pytest.raises(requests.HTTPError):
        arsiv_isinim.pvgis_df(37.87, 32.49, 2023, 2023)


def test_iklim_hesapla_pvgis_yolu_uctan_uca(monkeypatch):
    """Canlı hata zinciri: pvgis_df → iklim_serisi → aylik_toplamlar (time adlı indeks) → beklenti."""
    from pvquant import config
    monkeypatch.setenv("PVQUANT_METEO_KAYNAK", "acik"); config.get_settings.cache_clear()
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", _pvgis_sahte)
    monkeypatch.setattr(arsiv_isinim, "PVGIS_ILK_YIL", 2023)
    t, b = iklim_hesapla(39.74, -105.18, yil_sayisi=1, tz="America/Denver")
    assert not t.empty and set(b.columns) >= {"ay", "p10", "p50", "p90", "yil_sayisi"}
    config.get_settings.cache_clear()


def test_kacan_isler_slot_olcutu():
    slot = {"gece_meteo": (1, 0), "sabah_tahmin": (2, 0), "gece_skill": (0, 30)}
    simdi = pd.Timestamp("2026-11-04 02:04", tz="UTC")                # v2.532 dağıtımı: yeni süreç 02:03:43'te doğdu
    dun = {"gece_meteo": pd.Timestamp("2026-11-03 01:00", tz="UTC"), "sabah_tahmin": pd.Timestamp("2026-11-03 02:00", tz="UTC"),
           "gece_skill": pd.Timestamp("2026-11-04 00:30", tz="UTC")}
    assert isler_service.kacan_isler(dun, slot, simdi) == ["gece_meteo", "sabah_tahmin"]   # bugünkü slotları geçmiş, koşu yok; skill koştu
    bugun = {**dun, "gece_meteo": pd.Timestamp("2026-11-04 01:00:07", tz="UTC"), "sabah_tahmin": pd.Timestamp("2026-11-04 02:00:03", tz="UTC")}
    assert isler_service.kacan_isler(bugun, slot, simdi) == []
    eski = {**dun, "gece_skill": pd.Timestamp("2026-11-02 00:30", tz="UTC")}
    assert isler_service.kacan_isler(eski, slot, pd.Timestamp("2026-11-04 00:10", tz="UTC")) == ["gece_skill"]   # 00:30 henüz gelmedi → dünkü slot esas; 3 Kas koşusu yok
    assert isler_service.kacan_isler({}, slot, simdi) == ["gece_meteo", "sabah_tahmin", "gece_skill"]            # hiç kayıt yok
    assert isler_service.kacan_isler({"gece_meteo": "2026-11-04 00:58"}, {"gece_meteo": (1, 0)}, simdi) == []     # 5 dk pay, tz'siz dize
