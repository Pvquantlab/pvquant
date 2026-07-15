"""ReportContext — üç rapor formatının tek veri sözleşmesi.

from_results(), UI'daki mevcut nesnelerden (ForecastResult +
CalibrationResult) bağlamı kurar: entegrasyonun tek yapıştırıcısı budur.
Mod B'de P10/P90 YOKTUR — bağlam bunu dürüstçe taşır (has_band=False),
raporlar aralık uydurmaz.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd


@dataclass
class ReportContext:
    # kimlik
    plant_name: str
    capacity_kwp: float
    latitude: float
    longitude: float
    tilt_deg: float
    azimuth_deg: float
    plant_tz: str
    # koşu
    run_at_utc: datetime
    mode: str                 # "A" | "B" | "C"
    model_name: str
    meteo_source: str
    model_version: str = "faz2-ui"
    # veri (hourly UTC index; kolonlar: p50_kw, poa, temp_cell, p_dc_kw,
    #        p_ac_kw, energy_kwh; varsa p10_kw, p90_kw)
    hourly: pd.DataFrame = None
    daily_kwh: pd.Series = None          # yerel gün -> kWh (P50)
    daily_p10: Optional[pd.Series] = None
    daily_p90: Optional[pd.Series] = None
    # kalibrasyon / güven
    eta_bos: Optional[float] = None
    bg: Optional[float] = None
    mape_pct: Optional[float] = None
    deviation_pct: Optional[float] = None
    calibrated_at: Optional[datetime] = None
    n_valid_hours: Optional[int] = None          # kalibrasyondaki geçerli saat
    holdout_mape_pct: Optional[float] = None     # kronolojik son %20 sınavı
    warnings: list[str] = None
    schema_version: str = "1.0.0"

    # ---- türetilmiş KPI'lar (tek yerde yaşar; üç format aynı sayıyı basar) ----
    @property
    def total_kwh(self) -> float:
        return float(self.daily_kwh.sum())

    @property
    def total_mwh(self) -> float:
        return self.total_kwh / 1000.0

    @property
    def has_band(self) -> bool:
        return self.daily_p10 is not None and self.daily_p90 is not None

    @property
    def band_mwh(self) -> Optional[tuple[float, float]]:
        if not self.has_band:
            return None
        return (float(self.daily_p90.sum()) / 1000.0,
                float(self.daily_p10.sum()) / 1000.0)

    @property
    def capacity_factor_pct(self) -> float:
        """IEC 61724-1: E / (P_nom × saat)."""
        saat = len(self.hourly)
        return 100.0 * self.total_kwh / (self.capacity_kwp * saat)

    @property
    def specific_yield(self) -> float:
        """kWh/kWp — dönem özgül verimi (IEC 61724-1)."""
        return self.total_kwh / self.capacity_kwp

    @property
    def period_str(self) -> str:
        from .styles import donem_tr
        h = self.hourly.tz_convert(self.plant_tz)
        return donem_tr(h.index[0], h.index[-1])


def from_results(
    forecast_result,
    calibration_result=None,
    plant_name: str | None = None,
    plant_tz: str = "Europe/Istanbul",
    mode: str = "B",
    plant_context: dict | None = None,
) -> ReportContext:
    """pvquant.pipeline.forecast.ForecastResult (+ CalibrationResult) →
    ReportContext. UI entegrasyonunun çağırdığı tek fonksiyon.

    Santral adı çözüm sırası (ilk dolu olan kazanır):
      1. plant_name argümanı (çağıran açıkça verdiyse)
      2. plant_context dict'inde "plant_name" veya "name" anahtarı
      3. "Santral" (son çare — ama artık nadiren görünür)
    plant_context, UI'daki st.session_state.plant_context'tir; anahtar
    farkını (name/plant_name) burada soğuran tek nokta budur.
    """
    if plant_name is None:
        pc = plant_context or {}
        ham = pc.get("plant_name") or pc.get("name") or "Santral"
        plant_name = normalize_plant_name(ham)
    fr = forecast_result
    h = fr.hourly.copy()
    if h.index.tz is None:                       # güvence: UTC'ye sabitle
        h.index = h.index.tz_localize("UTC")
    h = h.rename(columns={"p_ac_kw": "p50_kw"})
    # Günlük gruplama UTC gün sınırına göre yapılır: forecast penceresi UTC
    # 00:00'da başlar; yerele çevirip gün saymak son günü taşırıp fazladan
    # (sıfıra yakın) 8. gün üretiyordu. Grafik/tablo günleri UTC tabanlı,
    # saatlik profil ise görselde yerele çevrilir (charts.py) — tutarlı.
    daily = h["energy_kwh"].groupby(h.index.tz_convert("UTC").date).sum()
    daily.index = pd.to_datetime(daily.index)

    cr = calibration_result
    # CalibrationResult.validation_after.mape_pct alan adları repoya göre:
    mape = None
    dev = None
    if cr is not None:
        va = getattr(cr, "validation_after", None)
        mape = getattr(va, "mape_pct", None) if va is not None else None
        dev = getattr(va, "deviation_pct", None) if va is not None else None

    return ReportContext(
        plant_name=plant_name,
        capacity_kwp=fr.plant.p_nom_kwp,
        latitude=fr.plant.latitude,
        longitude=fr.plant.longitude,
        tilt_deg=fr.plant.tilt,
        azimuth_deg=fr.plant.azimuth,
        plant_tz=plant_tz,
        run_at_utc=datetime.now(timezone.utc),
        mode=mode,
        model_name=fr.meta.get("power_model", "barhdadi_bennis"),
        meteo_source=fr.meta.get("meteo_source", "open-meteo"),
        hourly=h,
        daily_kwh=daily,
        eta_bos=getattr(cr, "eta_bos", None) if cr else None,
        bg=getattr(cr, "bg", None) if cr else None,
        mape_pct=mape,
        deviation_pct=dev,
        n_valid_hours=getattr(cr, "n_valid_hours", None) if cr else None,
        holdout_mape_pct=getattr(cr, "holdout_mape_pct", None) if cr else None,
        calibrated_at=getattr(cr, "calibrated_at", None) if cr else None,
        warnings=list(getattr(cr, "warnings", []) or []) if cr else [],
    )


import re as _re

_AD_KIRP = _re.compile(
    r"(?i)[_\s-]*(scada|yillik|yıllık|full|data|export|rapor|report"
    r"|20\d{2}|19\d{2})[_\s-]*")


def normalize_plant_name(ham: str) -> str:
    """Dosya adından türeyen santral adını insanileştirir.
    'SANTRAL_GES_yillik_SCADA' -> 'SANTRAL GES'
    Kural: bilinen ekler (scada/yillik/full/data/export/yıl) kırpılır,
    alt çizgiler boşluğa döner, çoklu boşluk teklenir. Büyük harf
    kısaltmalar (GES gibi) korunur."""
    ad = _AD_KIRP.sub(" ", ham or "")
    ad = ad.replace("_", " ").replace("-", " ")
    ad = " ".join(ad.split()).strip()
    return ad or "Santral"
