"""03.11 (v2.528 inceleme) — Portföy özet kartı («Yarın» = santral P50 toplamı, portfoy_service.gunluk_toplamlar) ile
«Portföyün günlük üretim tahmini» tablosu (uzlastirma_service.uzlastir_df bottom-up, gün toplamı) aynı koşulardan
aynı sayıyı vermeli. İki yol ayrı sorgu kullanır; bu test saf fonksiyonlarla tutarlılığı sabitler."""
import numpy as np
import pandas as pd

from pvquant.services import portfoy_service as ps
from pvquant.services import uzlastirma_service as us


def _kosu(seed: int, kwp: float) -> pd.DataFrame:
    idx = pd.date_range("2026-10-24 21:00", periods=48, freq="h", tz="UTC")   # İstanbul 25.10 00:00 – 26.10 23:00
    r = np.random.default_rng(seed)
    p50 = np.clip(np.sin(np.linspace(0, 4 * np.pi, 48)) * kwp * 0.8 + r.normal(0, kwp * 0.02, 48), 0, None)
    return pd.DataFrame({"p50_kw": p50, "p10_kw": p50 * 0.8, "p90_kw": p50 * 1.15}, index=idx)


def test_ozet_yarin_ile_gunluk_tablo_ayni_sayi():
    kosular = {"A": _kosu(1, 15230), "B": _kosu(2, 52500), "C": _kosu(3, 260000)}
    ozet = {ad: ps.gunluk_toplamlar(df, "Europe/Istanbul") for ad, df in kosular.items()}
    yarin = "2026-10-25"
    kart = ps._toplam([ozet[ad][yarin]["p50_kwh"] for ad in kosular])              # özet kartı yolu (kWh)
    uz, meta = us.uzlastir_df({ad: pd.DataFrame({"p50": df["p50_kw"], "p10": df["p10_kw"], "p90": df["p90_kw"]})
                               for ad, df in kosular.items()}, None)
    yerel = uz.index.tz_convert("Europe/Istanbul")
    tablo = uz.groupby(yerel.date)["p50"].sum() / 1000.0                            # tablo yolu (MWh)
    assert meta["yontem"] == "bottom-up" and meta["santral"] == 3
    assert round(kart / 1000.0, 1) == round(float(tablo[pd.Timestamp(yarin).date()]), 1)
    # bir santralin koşusu yoksa kart «—» (None) olur; tablo kalan santrallerle devam eder — bu fark görünür olmalı
    assert ps._toplam([ozet["A"][yarin]["p50_kwh"], None]) is None
