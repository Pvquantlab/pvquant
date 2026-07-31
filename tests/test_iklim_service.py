"""v2.77-A — iklim_service saf fonksiyonlari (DB'siz, agsiz).
Sahte df GERCEK sekli tasir: tz-aware UTC saatlik indeks + 'ghi' kolonu
(to_dataframe pvlib dili — ars probu dersi #3)."""
import numpy as np
import pandas as pd
import pytest


def _sahte_ghi(yillar, temmuz_wm2=500.0, aralik_wm2=150.0):
    """Sentetik saatlik GHI: her yil ayni desen — Tem sabit 500, Ara 150,
    diger aylar 300 W/m2. Ay toplamlari boylece elle dogrulanabilir."""
    ix = pd.date_range(f"{yillar[0]}-01-01", f"{yillar[-1]}-12-31 23:00",
                       freq="h", tz="UTC")
    v = np.full(len(ix), 300.0)
    v[ix.month == 7] = temmuz_wm2
    v[ix.month == 12] = aralik_wm2
    return pd.DataFrame({"ghi": v}, index=ix)


def test_aylik_toplamlar_elle_dogrulanir():
    from pvquant.services.iklim_service import aylik_toplamlar
    df = _sahte_ghi([2020])
    t = aylik_toplamlar(df)
    tem = t[(t["yil"] == 2020) & (t["ay"] == 7)]["ghi_kwh_m2"].iloc[0]
    assert tem == pytest.approx(31 * 24 * 500 / 1000)   # 372.0
    ara = t[(t["yil"] == 2020) & (t["ay"] == 12)]["ghi_kwh_m2"].iloc[0]
    assert ara == pytest.approx(31 * 24 * 150 / 1000)   # 111.6
    assert len(t) == 12


def test_aylik_beklenti_kuantiller_ve_yil_sayisi():
    from pvquant.services.iklim_service import aylik_toplamlar, aylik_beklenti
    df = _sahte_ghi([2020, 2021, 2022])   # uc yil ayni desen -> p10=p50=p90
    b = aylik_beklenti(aylik_toplamlar(df))
    assert list(b["ay"]) == list(range(1, 13))
    tem = b[b["ay"] == 7].iloc[0]
    assert tem["yil_sayisi"] == 3
    assert tem["p10"] == tem["p50"] == tem["p90"] == pytest.approx(372.0)
    assert (b["p10"] <= b["p50"]).all() and (b["p50"] <= b["p90"]).all()


def test_tz_ay_siniri_durust():
    """31 Mart 21:00 UTC, Istanbul'da 1 Nisan'dir (aylik_ozet emsali)."""
    from pvquant.services.iklim_service import aylik_toplamlar
    ix = pd.date_range("2024-03-31 20:00", periods=4, freq="h", tz="UTC")
    df = pd.DataFrame({"ghi": [1000.0] * 4}, index=ix)
    t = aylik_toplamlar(df, tz="Europe/Istanbul")
    mart = t[t["ay"] == 3]["ghi_kwh_m2"].iloc[0]
    nisan = t[t["ay"] == 4]["ghi_kwh_m2"].iloc[0]
    assert mart == pytest.approx(1.0) and nisan == pytest.approx(3.0)


def test_tam_yillar_tz_kiymigi_atilir():
    """tz kaydirmasi yil sinirinda kiymik uretir (31 Ara 21:00 UTC ->
    1 Oca, sonraki yil). Pencere disi yillar dagilimi zehirlemez."""
    from pvquant.services.iklim_service import aylik_toplamlar, tam_yillar
    ix = pd.date_range("2020-01-01 00:00", "2020-12-31 23:00",
                       freq="h", tz="UTC")
    df = pd.DataFrame({"ghi": [100.0] * len(ix)}, index=ix)
    t = aylik_toplamlar(df, tz="Europe/Istanbul")
    assert 2021 in set(t["yil"])                      # kiymik gercekten dogar
    t2 = tam_yillar(t, 2020, 2020)
    assert set(t2["yil"]) == {2020} and len(t2) == 12
