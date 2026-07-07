"""Pipeline yardımcı fonksiyonları.

Frekans-agnostik model desteği için ortak yardımcılar.
"""
from __future__ import annotations

import pandas as pd

from pvquant.io.meteo import MeteoData


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


# --- Faz 1.6 Adim 3.1: Meteo Alignment [BEGIN] ---
def _align_meteo_to_scada(
    meteo: MeteoData,
    target_index: pd.DatetimeIndex,
) -> MeteoData:
    """MeteoData'yi hedef zaman indeksine hizalar (lineer interpolasyon).

    Frekans-agnostik kalibrasyon icin kritik. 1h meteo + 15dk SCADA gibi
    durumlarda meteo'yu SCADA cozunurlugune upsample eder. Ayni cozunurlukte
    ise pratik olarak no-op'tur (identity).

    Yaklasim:
      1. Meteo serilerini bir DataFrame'de birlestir.
      2. Meteo ve hedef index'in birlesimi ile reindex et (arada NaN olusur).
      3. time-based interpolation ile NaN'lari doldur.
      4. Yalniz hedef index'i dondur.

    GHI icin ozel dikkat: Gece saatlerinde meteo zaten 0 raporlar; iki 0
    arasi interpolasyon yine 0 verir. Gunduz-gece gecisi (ornegin gundogumu)
    ise linear interpolasyon ile makul sekilde yumuşatilir.

    Hedef index meteo araligi disina taşarsa: uc noktalarda NaN kalir
    (interpolate limit_direction="both" ile forward/backward fill yapiyoruz;
    bu durumda uc degerler tekrar edilir). Kalibrasyon downstream'de
    intersection kullandigi icin bu satirlar zaten elenir.

    Args:
        meteo: Kaynak MeteoData (herhangi bir cozunurlukte).
        target_index: Hedef DatetimeIndex (genelde SCADA'nin index'i).

    Returns:
        target_index'e hizalanmis yeni MeteoData nesnesi.
        Latitude/longitude/timezone alanlari kaynaktan kopyalanir.

    Example:
        >>> import pandas as pd
        >>> from pvquant.io.meteo import MeteoData
        >>> hourly_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        >>> quarter_idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        >>> # meteo = MeteoData(ghi=..., temp_air=..., wind_speed_10m=..., ...)
        >>> # aligned = _align_meteo_to_scada(meteo, quarter_idx)
        >>> # aligned.ghi has 96 points instead of 24
    """
    # --- Faz 1.7: defansif duplicate temizligi ---
    # Defansif: kaynak meteo'da duplicate timestamp varsa (Open-Meteo DST bug'i gibi),
    # ilkini tut. reindex() duplicate index'te patlar.
    def _dedupe(s: pd.Series | None) -> pd.Series | None:
        if s is None:
            return None
        if s.index.duplicated().any():
            return s[~s.index.duplicated(keep="first")]
        return s

    # 1. Meteo serilerini bir DataFrame'de topla (duplicate temizligi ile)
    df = pd.DataFrame({
        "ghi": _dedupe(meteo.ghi),
        "temp_air": _dedupe(meteo.temp_air),
        "wind_speed_10m": _dedupe(meteo.wind_speed_10m),
    })
    # --- Faz 1.7: opsiyonel serilerde de dedupe ---
    if meteo.relative_humidity is not None:
        df["relative_humidity"] = _dedupe(meteo.relative_humidity)
    if meteo.cloud_cover is not None:
        df["cloud_cover"] = _dedupe(meteo.cloud_cover)

    # 2. Meteo ve hedef index'in birlesimi ile reindex
    combined_index = df.index.union(target_index).sort_values()
    df_reindexed = df.reindex(combined_index)

    # 3. Time-based interpolation. limit_direction="both" ile uc noktalarda
    #    forward/backward fill yaparak NaN birakmayiz. Meteo araligi
    #    disindaki hedef noktalar en yakin gozlem degeriyle doldurulur.
    df_interpolated = df_reindexed.interpolate(
        method="time",
        limit_direction="both",
    )

    # 4. Yalniz hedef index'i cikart
    df_target = df_interpolated.loc[target_index]

    # 5. Yeni MeteoData olustur
    return MeteoData(
        ghi=df_target["ghi"],
        temp_air=df_target["temp_air"],
        wind_speed_10m=df_target["wind_speed_10m"],
        relative_humidity=(
            df_target["relative_humidity"]
            if meteo.relative_humidity is not None
            else None
        ),
        cloud_cover=(
            df_target["cloud_cover"] if meteo.cloud_cover is not None else None
        ),
        latitude=meteo.latitude,
        longitude=meteo.longitude,
        timezone=meteo.timezone,
    )
# --- Faz 1.6 Adim 3.1: Meteo Alignment [END] ---


# --- Faz 1.9.3: SCADA outlier temizligi ---
def clean_scada_outliers(
    scada,
    plant,
    downtime_threshold_frac: float = 0.02,
    downtime_min_duration_min: int = 60,
    spike_max_frac: float = 1.10,
    spike_negative_frac: float = 0.05,
) -> tuple:
    """SCADA verisinden downtime ve spike outlier'lari filtrele.

    Iki anomali tipi tespit eder ve filtreler:
      1. **Downtime**: Solar zenith < 85 (gunduz) VE guc < nominal * threshold_frac
         (dusuk uretim) VE >= min_duration_min sure ardisik.
      2. **Spike**: Guc > nominal * spike_max_frac (fiziksel maksimum ustu) veya
         guc < -nominal * spike_negative_frac (asiri negatif).

    Args:
        scada: SCADAData - temizlenecek veri
        plant: PlantSpec - nominal guc ve konum icin
        downtime_threshold_frac: Downtime esik oran (nominal * X)
        downtime_min_duration_min: Downtime min sure (dk)
        spike_max_frac: Spike ust siniri (nominal * X)
        spike_negative_frac: Spike alt siniri (-nominal * X)

    Returns:
        (temizlenmis_scada, bilgi_dict)
    """
    from dataclasses import replace
    from pvquant.models import irradiance

    p = scada.power_kw
    n_total = len(p)
    nominal = plant.p_nom_kwp

    # 1. Spike tespiti
    spike_max = nominal * spike_max_frac
    spike_min = -nominal * spike_negative_frac
    spike_mask = (p > spike_max) | (p < spike_min)
    n_spike = int(spike_mask.sum())

    # 2. Downtime tespiti - solar zenith hesapla
    times = p.index
    solpos = irradiance.solar_position(
        times=times,
        latitude=plant.latitude,
        longitude=plant.longitude,
        altitude=plant.altitude_m,
    )
    is_daytime = solpos["zenith"] < 85.0
    is_daytime.index = p.index

    low_power = p < (nominal * downtime_threshold_frac)
    downtime_candidate = is_daytime & low_power & (~spike_mask)

    # Ardisiklik kontrolu
    dt_hours = (p.index[1] - p.index[0]).total_seconds() / 3600.0
    dt_minutes = dt_hours * 60.0
    min_points = max(1, int(round(downtime_min_duration_min / dt_minutes)))

    group_ids = (~downtime_candidate).cumsum()
    group_lengths = downtime_candidate.groupby(group_ids).transform("sum")
    downtime_mask = downtime_candidate & (group_lengths >= min_points)
    n_downtime = int(downtime_mask.sum())

    # 3. Toplam filtreleme
    remove_mask = spike_mask | downtime_mask
    keep_mask = ~remove_mask
    n_removed = int(remove_mask.sum())

    def _filter(s):
        if s is None:
            return None
        return s[keep_mask.reindex(s.index, fill_value=True)]

    cleaned = replace(
        scada,
        power_kw=_filter(scada.power_kw),
        energy_kwh=_filter(scada.energy_kwh),
        poa_irradiance=_filter(scada.poa_irradiance),
        temp_ambient=_filter(scada.temp_ambient),
        temp_module=_filter(scada.temp_module),
        wind_speed=_filter(scada.wind_speed),
    )

    info = {
        "total_removed": n_removed,
        "downtime_removed": n_downtime,
        "spike_removed": n_spike,
        "removed_frac": n_removed / n_total if n_total > 0 else 0.0,
    }
    return cleaned, info
