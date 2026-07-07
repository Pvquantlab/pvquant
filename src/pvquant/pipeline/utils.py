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


# --- Faz 1.9.4: akilli outlier tespiti ---
def clean_scada_outliers(
    scada,
    plant,
    downtime_min_duration_min: int = 60,
    spike_max_frac: float = 1.10,
    spike_negative_frac: float = 0.05,
    spike_local_deviation: float = 0.50,
    spike_local_window: int = 5,
    daytime_high_threshold_frac: float = 0.05,
    daytime_low_threshold_frac: float = 0.02,
    daytime_high_elevation_deg: float = 30.0,
    daytime_low_elevation_deg: float = 10.0,
) -> tuple:
    """SCADA verisinden akilli outlier tespiti + zengin rapor.

    Iki anomali tipi:

    1) **Downtime**: Adaptif esik (gunes elevation'a bagli).
       - Elevation > high_deg: p < nominal * high_frac (siki)
       - Elevation 10-30°: p < nominal * low_frac (gevsek)
       - Elevation < low_deg: tespit yok (gundogumu/batisi)
       - Downtime "candidate"lar >= min_duration_min ardisik olmali

    2) **Spike**: Iki katmanli tespit.
       - Mutlak: p > nominal * spike_max_frac veya p < -nominal * spike_negative_frac
       - Yerel: p, komsu spike_local_window medianindan %spike_local_deviation+
         farkli (izole tepe veya cukur)

    Rapor: outlier_report dict icinde:
      {
        "total_removed": int,
        "removed_frac": float,
        "downtime": {"count": int, "events": int, "longest_event_min": float,
                     "longest_event_start": str},
        "spike": {"count": int, "max_value_kw": float,
                  "max_frac_of_nominal": float, "hour_distribution": dict},
      }

    Args:
        scada: SCADAData
        plant: PlantSpec
        downtime_min_duration_min: Downtime min sure (dk)
        spike_max_frac: Fiziksel spike ust siniri
        spike_negative_frac: Fiziksel spike alt siniri
        spike_local_deviation: Yerel spike icin median'dan sapma orani
        spike_local_window: Yerel spike icin komsu penceresi (±N)
        daytime_high_threshold_frac: Yuksek gunes esigi (nominal * X)
        daytime_low_threshold_frac: Dusuk gunes esigi (nominal * X)
        daytime_high_elevation_deg: Yuksek gunes acisi esigi (°)
        daytime_low_elevation_deg: Dusuk gunes acisi esigi (°)

    Returns:
        (temizlenmis_scada, outlier_report_dict)
    """
    from dataclasses import replace
    import numpy as np
    import pandas as pd
    from pvquant.models import irradiance

    p = scada.power_kw
    n_total = len(p)
    nominal = plant.p_nom_kwp

    # --- 1) MUTLAK SPIKE (nominal * 1.10 usti veya asiri negatif) ---
    abs_spike_max = nominal * spike_max_frac
    abs_spike_min = -nominal * spike_negative_frac
    abs_spike_mask = (p > abs_spike_max) | (p < abs_spike_min)

    # --- 2) YEREL SPIKE (median filter tabanli) ---
    # Rolling median with window ±spike_local_window
    window = 2 * spike_local_window + 1
    rolling_median = p.rolling(window=window, center=True, min_periods=1).median()
    # Mutlak referans: nominal * 0.05 (cok kucuk uretimde spike hesabi anlamsiz)
    # Bolme ile normalize: |p - median| / max(median, nominal*0.05) > deviation
    min_ref = nominal * 0.05
    ref = rolling_median.where(rolling_median.abs() > min_ref, min_ref)
    rel_diff = (p - rolling_median).abs() / ref
    local_spike_mask = (rel_diff > spike_local_deviation) & (~abs_spike_mask)
    # Sadece gunduz saatlerinde uygula (gece 0'a yakin degerlerde anlamsiz)
    # (asagida hesaplanacak is_daytime ile filtrele)

    spike_mask = abs_spike_mask | local_spike_mask

    # --- 3) ADAPTIF DOWNTIME ---
    times = p.index
    solpos = irradiance.solar_position(
        times=times,
        latitude=plant.latitude,
        longitude=plant.longitude,
        altitude=plant.altitude_m,
    )
    elevation = 90.0 - solpos["zenith"]
    elevation.index = p.index

    # Elevation'a bagli esik
    high_thresh = nominal * daytime_high_threshold_frac
    low_thresh = nominal * daytime_low_threshold_frac

    # Yuksek gunes: sıkı eşik
    high_daytime = elevation > daytime_high_elevation_deg
    downtime_high = high_daytime & (p < high_thresh)

    # Orta gunes: gevsek eşik
    mid_daytime = (elevation > daytime_low_elevation_deg) & (elevation <= daytime_high_elevation_deg)
    downtime_mid = mid_daytime & (p < low_thresh)

    # Dusuk gunes: tespit yok

    downtime_candidate = (downtime_high | downtime_mid) & (~spike_mask)

    # Lokal spike'i sadece gunduz'e uygula
    is_daytime = elevation > daytime_low_elevation_deg
    local_spike_mask = local_spike_mask & is_daytime
    spike_mask = abs_spike_mask | local_spike_mask

    # Ardisiklik kontrolu
    dt_hours = (p.index[1] - p.index[0]).total_seconds() / 3600.0
    dt_minutes = dt_hours * 60.0
    min_points = max(1, int(round(downtime_min_duration_min / dt_minutes)))

    group_ids = (~downtime_candidate).cumsum()
    group_lengths = downtime_candidate.groupby(group_ids).transform("sum")
    downtime_mask = downtime_candidate & (group_lengths >= min_points)

    # --- 4) BIRLESIK MASKE ---
    remove_mask = spike_mask | downtime_mask
    keep_mask = ~remove_mask

    n_removed = int(remove_mask.sum())
    n_downtime = int(downtime_mask.sum())
    n_spike_abs = int(abs_spike_mask.sum())
    n_spike_local = int(local_spike_mask.sum())
    n_spike_total = int(spike_mask.sum())

    # --- 5) SCADA'yi filtrele ---
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

    # --- 6) ZENGIN RAPOR ---
    # Downtime olaylari (ardisik gruplar)
    downtime_events_info = {"events": 0, "longest_event_min": 0.0, "longest_event_start": None}
    if n_downtime > 0:
        # Ardisik gruplari bul
        dt_group_ids = (~downtime_mask).cumsum()[downtime_mask]
        event_lengths = dt_group_ids.value_counts()
        n_events = len(event_lengths)
        longest_len = int(event_lengths.max())
        longest_len_min = longest_len * dt_minutes
        # En uzun olayin baslangicini bul
        longest_group_id = event_lengths.idxmax()
        longest_start = dt_group_ids[dt_group_ids == longest_group_id].index[0]
        downtime_events_info = {
            "events": int(n_events),
            "longest_event_min": float(longest_len_min),
            "longest_event_start": str(longest_start),
        }

    # Spike raporu
    spike_info = {"max_value_kw": 0.0, "max_frac_of_nominal": 0.0, "hour_distribution": {}}
    if n_spike_total > 0:
        spike_values = p[spike_mask]
        max_val = float(spike_values.abs().max())
        spike_info = {
            "max_value_kw": max_val,
            "max_frac_of_nominal": max_val / nominal,
            "hour_distribution": (
                spike_values.index.hour
                if hasattr(spike_values.index, "hour")
                else pd.DatetimeIndex(spike_values.index).hour
            ).value_counts().sort_index().to_dict(),
        }

    outlier_report = {
        "total_removed": n_removed,
        "removed_frac": n_removed / n_total if n_total > 0 else 0.0,
        "downtime": {
            "count": n_downtime,
            **downtime_events_info,
        },
        "spike": {
            "count": n_spike_total,
            "count_absolute": n_spike_abs,
            "count_local": n_spike_local,
            **spike_info,
        },
    }
    return cleaned, outlier_report
