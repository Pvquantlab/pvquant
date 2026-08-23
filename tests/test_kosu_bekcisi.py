"""v2.176 — başsız-run bekçisi (kosu_cercevesi_denetle).

Backtest kök sebebinin yapısal kapanışı: v2.164 (son_kosu = son DOLU koşu)
ve v2.171 (kosu_gecmisi EXISTS süzgeci) belirtiyi GİZLİYORDU; bu bekçi
kaynağı KAPATIR — values taşımayacak koşu için run satırı hiç açılmaz.
Son-bekçi (işlem-içi sayım == satır sayısı, tutmazsa rollback) DB işi
olduğundan burada değil; kanıt makamı canlı koşular + kod okuması
(tenant_baglami istisna yolunda rollback, v2.176 commit-öncesi sayım).
"""
import pandas as pd
import pytest

from pvquant.services.forecast_service import kosu_cercevesi_denetle


def _saglikli(n=48):
    i = pd.date_range("2026-04-15", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"p50_kw": [100.0] * n}, index=i)


def test_bos_cerceve_run_acilmadan_duser():
    """15 Nis senaryosu: meteo arşivi aralık için boş döner → çerçeve boş.
    Eski dünyada bu, SQLAlchemy'nin boş-liste davranışına EMANETTİ
    (uygulama ayrıntısı, sözleşme değil); artık açık ValueError."""
    with pytest.raises(ValueError, match="başsız run"):
        kosu_cercevesi_denetle(_saglikli(0))
    with pytest.raises(ValueError, match="başsız run"):
        kosu_cercevesi_denetle(None)


def test_degersiz_cerceve_duser():
    """Satır var ama p50 tamamı NaN (ya da kolon yok) → değersiz koşu,
    run açılmaz. Kısmî NaN serbesttir — gece saatleri meşru NaN taşır."""
    d = _saglikli(); d["p50_kw"] = float("nan")
    with pytest.raises(ValueError, match="tamamı NaN"):
        kosu_cercevesi_denetle(d)
    with pytest.raises(ValueError):
        kosu_cercevesi_denetle(pd.DataFrame({"x": [1.0]}))


def test_saglikli_ve_kismi_nan_gecer():
    """Sağlıklı çerçeve ve kısmî-NaN çerçeve sessizce geçer — bekçi
    yalnız başsız/değersiz koşuyu keser, sağlıklı yolu yavaşlatmaz."""
    kosu_cercevesi_denetle(_saglikli())
    d = _saglikli()
    d.loc[d.index[:10], "p50_kw"] = float("nan")
    kosu_cercevesi_denetle(d)
