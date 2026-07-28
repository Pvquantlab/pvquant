"""Performans doğrulama metrikleri.

Model tahminini gerçek SCADA üretimiyle karşılaştırmak için kullanılan
standart metrikler.

Tüm fonksiyonlar şu ortak kurala uyar:
- predicted, actual: aynı uzunluk ve indeks
- NaN değerler otomatik filtrelenir
- Yüzde değerler 0-100 ölçeğinde (0.05 değil 5.0)

Referans:
    IEC 61724-1:2021. Photovoltaic system performance — Part 1: Monitoring.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _align_and_clean(predicted: pd.Series, actual: pd.Series) -> tuple[pd.Series, pd.Series]:
    """İki seriyi indeks bazında hizalar ve NaN değerleri çıkarır."""
    df = pd.concat([predicted.rename("pred"), actual.rename("act")], axis=1).dropna()
    return df["pred"], df["act"]


def mape(predicted: pd.Series, actual: pd.Series, threshold: float = 0.0) -> float:
    """Mean Absolute Percentage Error.

    .. code::

        MAPE = mean( |predicted - actual| / actual ) * 100

    Args:
        predicted: Tahmin serisi.
        actual: Gerçek üretim serisi.
        threshold: Bu eşiğin altındaki actual değerleri analize dahil edilmez
            (sabah/akşam saatlerinde küçük değerler MAPE'yi şişirir).

    Returns:
        MAPE değeri, %.
    """
    pred, act = _align_and_clean(predicted, actual)
    if threshold > 0:
        mask = act > threshold
        pred, act = pred[mask], act[mask]
    if len(act) == 0:
        return float("nan")
    return float(np.mean(np.abs(pred - act) / act) * 100)


def rmse(predicted: pd.Series, actual: pd.Series) -> float:
    """Root Mean Squared Error (predicted ve actual'ın birimi cinsinden).

    .. code::

        RMSE = sqrt( mean( (predicted - actual)^2 ) )
    """
    pred, act = _align_and_clean(predicted, actual)
    if len(act) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((pred - act) ** 2)))


def nmbe(predicted: pd.Series, actual: pd.Series) -> float:
    """Normalized Mean Bias Error.

    .. code::

        NMBE = mean(predicted - actual) / mean(actual) * 100

    Pozitif = model üst tahmin yapıyor; negatif = alt tahmin.
    """
    pred, act = _align_and_clean(predicted, actual)
    if len(act) == 0 or act.mean() == 0:
        return float("nan")
    return float((pred - act).mean() / act.mean() * 100)


def performance_ratio(
    energy_actual: pd.Series,
    poa_irradiance: pd.Series,
    p_nom_kwp: float,
    g_stc: float = 1000.0,
) -> float:
    """IEC 61724-1 Performance Ratio (PR).

    .. code::

        Y_f = E_AC / P_nom                    (final yield, saat/gün)
        Y_r = sum(G_poa) / G_STC * dt         (reference yield)
        PR  = Y_f / Y_r

    Args:
        energy_actual: Saatlik AC enerji üretimi, kWh.
        poa_irradiance: Saatlik POA ışınımı, W/m².
        p_nom_kwp: Sistem nominal gücü, kWp.
        g_stc: Referans ışınım, W/m².

    Returns:
        PR değeri (0-1 arası). Sağlıklı bir santralde 0.75-0.85 arası.
    """
    e, g = _align_and_clean(energy_actual, poa_irradiance)
    if len(e) == 0:
        return float("nan")
    y_f = e.sum() / p_nom_kwp
    # G_poa W/m², saatlik veride dt=1h → kWh/m²/g_stc kWh/m² = saat
    y_r = (g / g_stc).sum()
    if y_r == 0:
        return float("nan")
    return float(y_f / y_r)


@dataclass(frozen=True)
class ValidationReport:
    """Doğrulama metriklerinin özet raporu.

    Attributes:
        mape_pct: Mean Absolute Percentage Error, %.
        rmse: Root Mean Squared Error (predicted birimi).
        nmbe_pct: Normalized Mean Bias Error, %.
        n_samples: Analize giren geçerli saat sayısı.
        total_predicted: Toplam tahmin (kWh).
        total_actual: Toplam gerçek (kWh).
        total_deviation_pct: Toplam sapma yüzdesi.
    """

    mape_pct: float
    rmse: float
    nmbe_pct: float
    n_samples: int
    total_predicted: float
    total_actual: float
    total_deviation_pct: float
    # v2.51: agirlikli MAPE = sum|hata|/sum(gercek). Kucuk paydalara
    # dayanikli; MAPE ile yan yana raporlanir, esikler DEGISMEDI.
    wmape_pct: float = float("nan")

    def __str__(self) -> str:
        return (
            f"ValidationReport(\n"
            f"  MAPE        = {self.mape_pct:.2f} %\n"
            f"  WMAPE       = {self.wmape_pct:.2f} %\n"
            f"  RMSE        = {self.rmse:.2f} (predicted units)\n"
            f"  NMBE        = {self.nmbe_pct:+.2f} %\n"
            f"  Toplam fark = {self.total_deviation_pct:+.2f} %\n"
            f"  n           = {self.n_samples}\n"
            f")"
        )


def validate(
    predicted: pd.Series,
    actual: pd.Series,
    threshold: float = 0.0,
) -> ValidationReport:
    """Tek seferde tüm metrikleri hesaplar ve özet rapor döner.

    Args:
        predicted: Model tahmini (saatlik kW veya kWh).
        actual: Gerçek SCADA verisi (aynı birim).
        threshold: Bu değerin altındaki actual'lar dışlanır.

    Returns:
        ValidationReport.
    """
    pred, act = _align_and_clean(predicted, actual)
    if threshold > 0:
        mask = act > threshold
        pred, act = pred[mask], act[mask]

    total_pred = float(pred.sum())
    total_act = float(act.sum())
    total_dev = (total_pred - total_act) / total_act * 100 if total_act > 0 else float("nan")

    return ValidationReport(
        mape_pct=mape(pred, act, threshold=0),
        rmse=rmse(pred, act),
        nmbe_pct=nmbe(pred, act),
        n_samples=len(pred),
        total_predicted=total_pred,
        total_actual=total_act,
        total_deviation_pct=float(total_dev),
        wmape_pct=(float(np.sum(np.abs(pred - act)) / total_act * 100)
                   if total_act > 0 else float("nan")),
    )
