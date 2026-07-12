"""Aşama 4 — Doğrulama: PV'ye özgü kalite kuralları.

İlke: ŞÜPHELİ SATIR SİLİNMEZ, BAYRAKLANIR. Veri 'flag' kolonuyla
saklanır; kalibrasyon/hibrit eğitimi yalnız VALID satırları kullanır
ama ham gerçek her zaman denetlenebilir kalır.

Kuralların sahadaki anlamı:

  - NEGATIVE_POWER: gece inverterin şebekeden çektiği küçük öz tüketim
    normaldir (-%0.5 kapasiteye kadar tolere edilir, 0'a kırpılır);
    büyük negatifler ölçüm hatasıdır.
  - NIGHT_PRODUCTION: güneş ufkun altındayken üretim > 0 ise bu, BİR
    NUMARALI saat dilimi hatası belirtisidir (UTC veriyi yerel sanmak
    üretimi 3 saat kaydırır). Bu bayrak çoksa ingestion pipeline'ı
    kullanıcıya 'saat dilimini kontrol et' uyarısı üretir.
  - OVER_CAPACITY: DC kurulu gücün üstü fiziksel olarak imkansızdır
    (kısa süreli irradiance enhancement için %5 pay bırakılır).
  - FROZEN_VALUE: aynı sıfır-dışı değerin uzun tekrarı veri toplama
    arızasıdır; gerçek üretim asla saatlerce sabit kalmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .contracts import QualityReport, RowFlag

#: Gece tespiti için güneş yükseklik eşiği (derece). -3°: sivil
#: alacakaranlığın hemen altı; panel bu açıda anlamlı üretemez.
NIGHT_ELEVATION_DEG = -3.0

#: Gece "üretim var" saymak için eşik: kapasitenin binde 5'i.
NIGHT_POWER_FRACTION = 0.005

#: Negatif tolerans: kapasitenin binde 5'ine kadar öz tüketim normal.
NEGATIVE_TOLERANCE_FRACTION = 0.005

#: Kapasite aşımı payı (irradiance enhancement kısa süreli %5 verebilir).
OVER_CAPACITY_FACTOR = 1.05

#: Donmuş değer: aynı sıfır-dışı değerin ardışık tekrar eşiği (saat).
FROZEN_RUN_HOURS = 4


def _solar_elevation(index: pd.DatetimeIndex, latitude: float,
                     longitude: float) -> pd.Series:
    """pvlib ile güneş yükseklik açısı (derece)."""
    import pvlib

    solpos = pvlib.solarposition.get_solarposition(index, latitude, longitude)
    return solpos["apparent_elevation"]


def validate(
    df: pd.DataFrame,
    capacity_kwp: float,
    latitude: float,
    longitude: float,
    dst_flags: pd.Series | None = None,
) -> tuple[pd.DataFrame, QualityReport]:
    """Kanonik frame'i bayraklar ve kalite karnesi üretir.

    Args:
        df: transform_to_canonical çıktısı (saatlik, UTC, power_kw'lı).
        capacity_kwp: DC kurulu güç — kapasite/negatif eşikler için.
        latitude, longitude: gece tespiti (güneş pozisyonu) için.
        dst_flags: transform'dan gelen DST belirsizlik işaretleri.

    Returns:
        (flag kolonu eklenmiş df, QualityReport)
    """
    out = df.copy()
    n_read = len(out)
    flags = pd.Series(RowFlag.VALID.value, index=out.index, dtype="object")

    power = out["power_kw"]

    # --- 1. Okunamayan güç ---
    flags[power.isna()] = RowFlag.UNPARSEABLE.value

    # --- 2. Tekrarlanan timestamp ---
    dup = out.index.duplicated(keep="first")
    flags[dup] = RowFlag.DUPLICATE_TIME.value

    # --- 3. Negatif güç ---
    neg_tol = -NEGATIVE_TOLERANCE_FRACTION * capacity_kwp
    small_neg = (power < 0) & (power >= neg_tol)
    out.loc[small_neg, "power_kw"] = 0.0          # öz tüketim → 0'a kırp
    big_neg = power < neg_tol
    flags[big_neg & (flags == RowFlag.VALID.value)] = RowFlag.NEGATIVE_POWER.value

    # --- 4. Kapasite aşımı ---
    over = power > OVER_CAPACITY_FACTOR * capacity_kwp
    flags[over & (flags == RowFlag.VALID.value)] = RowFlag.OVER_CAPACITY.value

    # --- 5. Gece üretimi (saat dilimi hatası dedektörü) ---
    elevation = _solar_elevation(out.index, latitude, longitude)
    night = elevation < NIGHT_ELEVATION_DEG
    night_prod = night & (power > NIGHT_POWER_FRACTION * capacity_kwp)
    flags[night_prod & (flags == RowFlag.VALID.value)] = RowFlag.NIGHT_PRODUCTION.value

    # --- 6. Donmuş değer ---
    nonzero = power.fillna(0) > 0.01 * capacity_kwp
    same_as_prev = power.diff().abs() < 1e-9
    run_id = (~(same_as_prev & nonzero)).cumsum()
    run_len = run_id.groupby(run_id).transform("size")
    frozen = same_as_prev & nonzero & (run_len >= FROZEN_RUN_HOURS)
    flags[frozen & (flags == RowFlag.VALID.value)] = RowFlag.FROZEN_VALUE.value

    # --- 7. DST belirsizliği ---
    if dst_flags is not None:
        dst_aligned = dst_flags.reindex(out.index).fillna(False).astype(bool)
        flags[dst_aligned & (flags == RowFlag.VALID.value)] = RowFlag.DST_AMBIGUOUS.value

    out["flag"] = flags

    # --- Boşluk analizi (beklenen saatlik ızgaraya göre) ---
    gap_hours, gap_periods = _find_gaps(out.index)

    counts = flags.value_counts().to_dict()
    report = QualityReport(
        n_rows_read=n_read,
        n_rows_valid=int((flags == RowFlag.VALID.value).sum()),
        flag_counts={str(k): int(v) for k, v in counts.items()},
        gap_hours=gap_hours,
        gap_periods=gap_periods[:20],   # UI'da ilk 20 dönem yeter
        coverage_start=str(out.index.min()) if n_read else None,
        coverage_end=str(out.index.max()) if n_read else None,
    )

    # --- Akıllı uyarılar ---
    n_night = int(counts.get(RowFlag.NIGHT_PRODUCTION.value, 0))
    if n_read > 0 and n_night > 0.02 * n_read:
        report.warnings.append(
            "DİKKAT: Gece saatlerinde yaygın üretim tespit edildi. Bu, "
            "büyük ihtimalle saat dilimi seçiminin yanlış olduğunu "
            "gösterir — 'Kaynak saat dilimi' ayarını kontrol edin."
        )
    if capacity_kwp > 0 and power.notna().any():
        peak = float(power.max())
        if peak < 0.3 * capacity_kwp:
            report.warnings.append(
                f"Tepe güç ({peak:.0f} kW) kurulu gücün ({capacity_kwp:.0f} kWp) "
                "%30'unun altında. Birim (kW/MW) veya kapasite girişini "
                "kontrol edin."
            )
    return out, report


def _find_gaps(index: pd.DatetimeIndex) -> tuple[int, list[tuple[str, str]]]:
    """Saatlik ızgarada eksik dönemleri bulur."""
    if len(index) < 2:
        return 0, []
    full = pd.date_range(index.min(), index.max(), freq="1h", tz=index.tz)
    missing = full.difference(index)
    if missing.empty:
        return 0, []
    # Ardışık eksikleri dönemlere grupla
    periods: list[tuple[str, str]] = []
    start = prev = missing[0]
    for t in missing[1:]:
        if (t - prev) > pd.Timedelta(hours=1):
            periods.append((str(start), str(prev)))
            start = t
        prev = t
    periods.append((str(start), str(prev)))
    return len(missing), periods