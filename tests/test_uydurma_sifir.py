"""v2.156: uydurma-0 avı — iki bacak.

(1) transpose_perez girdisi-eksik saatlerde NaN korur: open-meteo radyasyon
ufku ötesini (NaN) eski fillna(0) 'üretim 0' yalanına çeviriyordu; şartname
"veri yoksa '—', asla uydurma 0" der. Gece (GHI=0 GERÇEK değer) 0 kalır —
iki NaN türü ayrışır. (2) Ufuk 15 güne kırpıldı (kullanıcı kararı 18 Ağu);
elle '16' kalıntıları kaynak taramasıyla kilitlenir.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
from pvquant.config import get_settings              # noqa: E402
from pvquant.models import irradiance                # noqa: E402


def _poa(ghi):
    """Gerçek üreticiyle küçük koşu: öğle saatleri, Konya koordinatı."""
    ts = pd.date_range("2026-08-18 09:00", periods=len(ghi), freq="h", tz="UTC")
    sol = irradiance.solar_position(ts, 37.87, 32.49, 1000)
    dni_extra, airmass = irradiance.extra_radiation_and_airmass(
        ts, sol["apparent_zenith"])
    g = pd.Series(ghi, index=ts)
    dec = irradiance.decompose_ghi_erbs(g, sol["apparent_zenith"], ts)
    return irradiance.transpose_perez(
        surface_tilt=20, surface_azimuth=180,
        solar_zenith=sol["apparent_zenith"], solar_azimuth=sol["azimuth"],
        dni=dec["dni"], ghi=g, dhi=dec["dhi"],
        dni_extra=dni_extra, airmass=airmass, albedo=0.2)


def test_girdisi_eksik_saat_nan_kalir():
    p = _poa([600.0, np.nan, 700.0])
    assert np.isnan(p.global_.iloc[1]) and np.isnan(p.beam.iloc[1])
    assert p.global_.iloc[0] > 0 and p.global_.iloc[2] > 0


def test_gercek_sifir_gece_sifir_kalir():
    """GHI=0 GERÇEK bir ölçümdür (gece) — 0 kalır, NaN'lanmaz."""
    p = _poa([0.0, 0.0])
    assert float(p.global_.iloc[0]) == 0.0 and not np.isnan(p.global_.iloc[0])


def test_ufuk_15_gun():
    """Kayıtlı karar (18 Ağu): open-meteo radyasyon ufku ~15 gün."""
    assert get_settings().forecast_horizon_days == 15


def test_elle_16_kalintisi_yok():
    """Sözleşme ve sayfa kopyaları ufuk/GUN_SAYISI'ndan türer (yorumlar hariç)."""
    def kod(p):
        return "\n".join(l.split("#", 1)[0]
                         for l in (KOK / p).read_text().splitlines())
    assert "== 16" not in kod("src/pvquant/services/report_html_service.py")
    assert "forecast_horizon_days" in kod("src/pvquant/services/report_html_service.py")
    assert "range(16)" not in kod("reporting/html/build_s06.py")
    for s in ("build_s01.py", "build_s02.py", "build_s03.py", "build_s04.py"):
        assert "16 gün" not in kod("reporting/html/" + s), s
