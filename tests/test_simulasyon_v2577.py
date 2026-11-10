"""v2.577 (Faz 1 F1-F2) — geriye dönük simülasyon kipi: geriye bakışlı koşular yalnız açıkça istenince dâhil, sonuç kaydedilmez, rapor etiketi."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import olcum_uygunluk_service as ou
from pvquant.services import sablon_rapor_service as srs

PLANT = {"id": "p1", "name": "Sim GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul"}


def _veri():
    iz = ou.saat_izgarasi("2026-09-01 06:00", "2026-09-01 15:00")
    olc = pd.DataFrame({"power_kw": 300.0, "energy_kwh": 300.0, "flag": "valid", "kirpma": False, "kapsama_dk": 60}, index=iz)
    saatler = ou.siniflandir(iz, olc)
    tahmin = pd.DataFrame({"ts_utc": iz, "run_at": pd.Timestamp("2026-08-31 03:00", tz="UTC"), "run_id": "bt", "p50_kw": 330.0, "p10_kw": None, "p90_kw": None,
                           "physics_kw": 330.0, "model": "backtest", "meteo_source": "open-meteo-arsiv", "etiket": None})
    return tahmin, saatler


def test_simulasyon_kipi_backtest_kosusunu_dahil_eder_ve_etiketler():
    tahmin, saatler = _veri()
    assert bd.kosu_sec(tahmin, "gun_oncesi", "Europe/Istanbul").empty                    # varsayılan: geriye bakışlı dışarıda
    sec = bd.kosu_sec(tahmin, "gun_oncesi", "Europe/Istanbul", simulasyon=True)
    assert len(sec) == len(tahmin) and (sec["model"] == "simulasyon").all()
    s = bd.hesapla_saf(tahmin, saatler, ou.dokum(saatler), PLANT, date(2026, 9, 1), date(2026, 9, 2), "gun_oncesi", simulasyon=True)
    assert s["meta"]["simulasyon"] is True and s["metrik"]["wmape"] == 10.0
    s0 = bd.hesapla_saf(tahmin, saatler, ou.dokum(saatler), PLANT, date(2026, 9, 1), date(2026, 9, 2), "gun_oncesi")
    assert s0["meta"]["simulasyon"] is False and s0["metrik"]["n_saat"] == 0
    with pytest.raises(ValueError):
        bd.kaydet("t", s, "p1")                                                             # simülasyon kaydedilmez (DB'ye gitmeden)
    r = srs.bagimsiz_dogrulama("t", PLANT, sonuc=s)                                        # etiket meta'dan okunur
    assert "GERİYE DÖNÜK SİMÜLASYON" in r.bolumler[0][1] and "OKUNMAZ" in r.bolumler[0][1]
    assert srs.dogrulama_durumu(s)[0] == "GERİYE DÖNÜK SİMÜLASYON"
