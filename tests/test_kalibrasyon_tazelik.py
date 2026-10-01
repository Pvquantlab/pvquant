"""v2.380 (bulgu 31) — cron kalibrasyonunun tazelik hükmü.

1 Eki canlı: 639 gündür veri gelmeyen kobay, ay-başı cron'uyla Mod B'ye
geçip %98,6 sapmalı karne üretti. Sapma katmanının 3 günlük bekçisi vardı
(v2.274), kalibrasyonun hiç yoktu. Hüküm saf fonksiyonda: worker cron'u
bayatsa atlar, panelden elle kalibrasyon serbest kalır."""
import pandas as pd

from pvquant.services.calib_service import (KALIBRASYON_TAZELIK_GUN,
                                            kalibrasyon_bayat_mi)

SIMDI = pd.Timestamp("2026-10-01 12:00", tz="UTC")


def test_bayat_veri_cron_kalibrasyonunu_durdurur():
    bayat, neden = kalibrasyon_bayat_mi(pd.Timestamp("2024-12-31 23:00", tz="UTC"), SIMDI)
    assert bayat and f"(>{KALIBRASYON_TAZELIK_GUN})" in neden and "63" in neden


def test_taze_veri_gecer():
    bayat, neden = kalibrasyon_bayat_mi(SIMDI - pd.Timedelta(days=2), SIMDI)
    assert not bayat


def test_esik_siniri_ve_hic_olcum():
    tam_esik = SIMDI - pd.Timedelta(days=KALIBRASYON_TAZELIK_GUN)
    assert not kalibrasyon_bayat_mi(tam_esik, SIMDI)[0]          # eşik dâhil: taze
    assert kalibrasyon_bayat_mi(tam_esik - pd.Timedelta(days=1), SIMDI)[0]
    bayat, neden = kalibrasyon_bayat_mi(None, SIMDI)
    assert bayat and "hiç ölçüm" in neden


def test_naif_damga_utc_sayilir():
    # veri_ozeti bazı sürücülerde tz'siz döndürebilir — hüküm yine çalışır
    assert kalibrasyon_bayat_mi(pd.Timestamp("2024-12-31 23:00"), SIMDI)[0]
