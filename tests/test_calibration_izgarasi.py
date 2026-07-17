"""Fable 5 v1.7 kalici bekcisi:
  calib_service._kalibrasyon_izgarasi bosluklu SCADA'yi kesintisiz saatlik
  izgaraya oturturur.

Fable 5 v1.7 kabul: 'zaman adimi tutarsiz medyan 0d 01:00:00, kayitlarin
%78'i' turu ValueError'un bir daha dogmamasi icin kilit."""
from __future__ import annotations
import pandas as pd
import numpy as np
import pytest

from pvquant.services.calib_service import _kalibrasyon_izgarasi
from pvquant.pipeline.utils import _detect_timestep_hours


def test_kalibrasyon_izgarasi_bosluklu_veriyi_kesintisiz_yapar():
    """Bekci: bosluklu ham SCADA -> izgaralanmis cikti kesintisiz.

    Senaryo: MERKAS'in yasadigi durum — %22 satir eksik (anomali + gece).
    Ham veri _detect_timestep_hours'tan ValueError alir; izgaralama
    sonrasi almamali."""
    # Ham bosluklu veri: 30 gun, gunduz 06-19 UTC + %20 rastgele dusuk
    rng = np.random.default_rng(42)
    saatler = []
    for gun in range(30):
        for saat in range(6, 20):
            if rng.random() < 0.20:
                continue
            saatler.append(
                pd.Timestamp("2024-01-01", tz="UTC") +
                pd.Timedelta(days=gun, hours=saat)
            )
    df_bosluklu = pd.DataFrame(
        {"power_kw": np.random.default_rng(0).uniform(0, 3000, len(saatler))},
        index=pd.DatetimeIndex(saatler),
    )

    # 1) Ham veri ValueError firlatmali (senaryonun kanıtı)
    with pytest.raises(ValueError):
        _detect_timestep_hours(df_bosluklu.index)

    # 2) Izgaraladiktan sonra ValueError FIRLATMAMALI (bekcinin isi)
    df_izgara = _kalibrasyon_izgarasi(df_bosluklu, {"lat": 37.87, "lon": 32.49})
    dt_saat = _detect_timestep_hours(df_izgara.index)
    assert dt_saat == pytest.approx(1.0, rel=0.01)
