"""Pipeline yardımcı fonksiyonları.

Frekans-agnostik model desteği için ortak yardımcılar.
"""
from __future__ import annotations

import pandas as pd


def _detect_timestep_hours(index: pd.DatetimeIndex) -> float:
    """Zaman ekseninden ortalama adımı saat cinsinden döner.

    Fonksiyon medyanı kullanır (tek bir aykırı boşluk sonucu bozmasın).
    Tutarlılık kontrolü yapar: kayıtların en az %90'ı medyana yakın olmalı.

    Args:
        index: DatetimeIndex. En az 2 kayıt gerekli.

    Returns:
        Saat cinsinden zaman adımı.
        Örnekler:
          - Saatlik veri: 1.0
          - 30 dakikalık: 0.5
          - 15 dakikalık: 0.25
          - 5 dakikalık: 0.0833...
          - 1 dakikalık: 0.0167...

    Raises:
        ValueError: 2'den az kayıt varsa veya zaman adımı tutarsızsa.

    Example:
        >>> import pandas as pd
        >>> idx = pd.date_range("2024-01-01", periods=96, freq="15min")
        >>> _detect_timestep_hours(idx)
        0.25
    """
    if len(index) < 2:
        raise ValueError(
            f"En az 2 kayıt gerekli, {len(index)} bulundu"
        )

    diffs = index.to_series().diff().dropna()
    median_diff = diffs.median()

    # Tutarlılık kontrolü: %90'ının medyana yakın olmasını bekle
    # Tolerans: 1 dakika (tam saat başında farklı zaman dilimleri için)
    close_to_median = (diffs - median_diff).abs() < pd.Timedelta("1min")
    consistency = close_to_median.mean()

    if consistency < 0.90:
        raise ValueError(
            f"Zaman adımı tutarsız: medyan {median_diff}, "
            f"kayıtların sadece %{consistency*100:.0f}'ı bu adımda. "
            f"Boşluklu veya karışık frekanslı veri modele girmez."
        )

    return median_diff.total_seconds() / 3600.0


def _detect_timestep_minutes(index: pd.DatetimeIndex) -> int:
    """Zaman ekseninden ortalama adımı dakika cinsinden (int) döner.

    _detect_timestep_hours()'un dakika versiyonu. SCADAData gibi
    dakika-tabanlı arayüzler için pratik.

    Args:
        index: DatetimeIndex. En az 2 kayıt gerekli.

    Returns:
        Dakika cinsinden zaman adımı (en yakın int'e yuvarlanmış).
        Örnekler:
          - Saatlik: 60
          - 30 dk: 30
          - 15 dk: 15
          - 5 dk: 5
          - 1 dk: 1

    Raises:
        ValueError: 2'den az kayıt varsa veya zaman adımı tutarsızsa.

    Example:
        >>> import pandas as pd
        >>> idx = pd.date_range("2024-01-01", periods=96, freq="15min")
        >>> _detect_timestep_minutes(idx)
        15
    """
    hours = _detect_timestep_hours(index)
    return int(round(hours * 60))
