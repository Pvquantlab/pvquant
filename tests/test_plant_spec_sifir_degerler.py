"""v2.669 geometri kusuru (28.11.2026): `plant.get("tilt") or 20.0` kalıbı geçerli 0°'yi varsayılanla değiştiriyordu.
Düzeltme: `sayi_veya` / `egim_azimut` (None/eksik/bozuk → varsayılan; 0 korunur); tüm çağrı yerleri tek yardımcıya bağlandı.
Fiziksel formül değişmedi; izleyicide yüzey açıları güneşten türediği için tilt/azimut spec alanı sayısal sonucu etkilemez (pinlenir)."""
from __future__ import annotations

import pandas as pd
import pytest

from pvquant.services.plant_spec_service import egim_azimut, plant_spec_kur, sayi_veya

P = {"capacity_kwp": 1000.0, "lat": 37.0, "lon": 35.0, "panel_tech": "monofacial", "ac_limit_kw": None, "params_json": {}}


@pytest.mark.parametrize("tilt,azimuth,bek", [
    (0, 0, (0.0, 0.0)),            # düz çatı + kuzey: 0 geçerli
    (0.0, 180.0, (0.0, 180.0)),
    (None, None, (20.0, 180.0)),   # eksik → eski varsayılan
    (25.0, 90.0, (25.0, 90.0)),    # normal
    ("12.5", "200", (12.5, 200.0)),
    ("", "abc", (20.0, 180.0)),    # bozuk → varsayılan
    (float("nan"), 180.0, (20.0, 180.0)),
])
def test_egim_azimut_sifir_korunur_eksik_varsayilan(tilt, azimuth, bek):
    assert egim_azimut(dict(P, tilt=tilt, azimuth=azimuth)) == bek
    s = plant_spec_kur(dict(P, tilt=tilt, azimuth=azimuth))
    assert (s.tilt, s.azimuth) == bek


def test_anahtar_hic_yoksa_varsayilan():
    assert egim_azimut(P) == (20.0, 180.0)
    assert sayi_veya(True, 5.0) == 5.0 and sayi_veya(0, 5.0) == 0.0 and sayi_veya("0", 5.0) == 0.0


def test_sabit_egim_sifir_poa_degisir_izleyici_etkilenmez():
    """Önce/sonra: sabit yapıda tilt 0 artık 20 sayılmaz (POA farkı beklenir); izleyicide spec.tilt sonucu etkilemez (pin)."""
    from pvquant.io.meteo import MeteoData
    from pvquant.pipeline.forecast import forecast_7day
    idx = pd.date_range("2026-06-21", periods=48, freq="h", tz="UTC")
    ghi = pd.Series([0.0] * 5 + [100, 300, 500, 700, 800, 850, 800, 700, 500, 300, 100, 20] + [0.0] * 7, index=idx[:24]).reindex(idx).fillna(0.0)
    ghi.iloc[24:] = ghi.iloc[:24].to_numpy()
    m = MeteoData(ghi=ghi, temp_air=pd.Series(25.0, index=idx), wind_speed_10m=pd.Series(2.0, index=idx), relative_humidity=None,
                  cloud_cover=None, latitude=37.0, longitude=35.0, timezone="UTC")
    s0 = plant_spec_kur(dict(P, tilt=0.0, azimuth=180.0))
    s20 = plant_spec_kur(dict(P, tilt=20.0, azimuth=180.0))
    e0 = forecast_7day(m, s0).total_kwh
    e20 = forecast_7day(m, s20).total_kwh
    assert s0.tilt == 0.0 and e0 != pytest.approx(e20)                         # eskiden ikisi de 20° → eşitti
    t0 = plant_spec_kur(dict(P, tilt=0.0, params_json={"izleyici": "tek_eksen"}))
    t20 = plant_spec_kur(dict(P, tilt=20.0, params_json={"izleyici": "tek_eksen"}))
    assert forecast_7day(m, t0).total_kwh == pytest.approx(forecast_7day(m, t20).total_kwh)   # izleyici: tilt alanı kullanılmaz


def test_diger_servisler_ayni_yardimciyi_kullanir():
    import inspect

    from pvquant.services import (
        calib_service,
        guc_matrisi_service,
        kayip_service,
        report_service,
        retrospektif_kalibrasyon,
    )
    for mod in (calib_service, guc_matrisi_service, kayip_service, report_service, retrospektif_kalibrasyon):
        src = inspect.getsource(mod)
        assert 'get("tilt") or' not in src and 'get("azimuth") or' not in src, mod.__name__
        assert "egim_azimut" in src, mod.__name__
