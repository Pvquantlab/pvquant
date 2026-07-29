"""Hibrit model UI köprüsü — Streamlit'in çağırdığı, Streamlit'siz test edilen katman.

Tasarım (Tur 5):
  - UI'daki akış DEĞİŞMEZ: fizik kalibrasyonu her zaman önce koşar.
  - Kullanıcı isterse "Hibritle iyileştir" der; bu modül HybridResidualModel'i
    MEVCUT historical_meteo'yu paylaşarak eğitir (kendi API çağrısı YOK),
    holdout metriklerini çıkarır ve session sözlüğüne yazılacak özeti üretir.
  - Hibrit HERHANGİ bir nedenle patlarsa: ok=False + error döner, istisna
    YÜKSELMEZ — UI fiziğe sessizce düşer, hata arka planda loglanır.

Session anahtar sözleşmesi (frontend bu adları kullanır):
  st.session_state["hybrid_model"]  : eğitilmiş HybridResidualModel (predict için)
  st.session_state["hybrid_report"] : session_ozeti() çıktısı (dict)
  st.session_state["hybrid_active"] : bool — rozet/rapor Mod C sinyali
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger("pvquant.hybrid_ui")


# --------------------------------------------------------------------- sonuç
@dataclass
class HybridUIResult:
    ok: bool
    error: Optional[str] = None
    model: Any = None                          # HybridResidualModel
    holdout_mape_pct: Optional[float] = None   # hibrit
    holdout_wmape_pct: Optional[float] = None  # v2.51-B: hibrit agirlikli
    holdout_rmse_kw: Optional[float] = None    # hibrit
    physics_mape_pct: Optional[float] = None   # aynı holdout'ta fizik
    physics_wmape_pct: Optional[float] = None  # v2.51-B: fizik agirlikli
    improvement_pct: Optional[float] = None    # (fizik-hibrit)/fizik*100
    holdout_hours: Optional[int] = None
    trained_at: Optional[datetime] = None
    coverage_p10_p90_pct: Optional[float] = None    # v2.57: gunduz-kosullu kapsama
    band_width_mean_kw: Optional[float] = None      # v2.57: P10-P90 ort. genislik
    band_width_pct_of_p50: Optional[float] = None   # v2.57: genislik / p50 toplami
    raw_report: dict = field(default_factory=dict)


def session_ozeti(res: HybridUIResult) -> dict:
    """st.session_state['hybrid_report'] içeriği — raporlar.py bunu okur."""
    return {
        "holdout_mape_pct": res.holdout_mape_pct,
        "holdout_wmape_pct": res.holdout_wmape_pct,
        "physics_wmape_pct": res.physics_wmape_pct,
        "holdout_rmse_kw": res.holdout_rmse_kw,
        "physics_mape_pct": res.physics_mape_pct,
        "improvement_pct": res.improvement_pct,
        "holdout_hours": res.holdout_hours,
        "trained_at": res.trained_at,
        "coverage_p10_p90_pct": res.coverage_p10_p90_pct,
        "band_width_mean_kw": res.band_width_mean_kw,
        "band_width_pct_of_p50": res.band_width_pct_of_p50,
    }


# --------------------------------------------------------------- profil kur
def _plant_profile(plant_ctx: dict, plant_name: str = "Santral"):
    """UI plant_context sözlüğünden PlantProfile üretir.

    UI yalnız kapasite/konum/dilim toplar; panel-inverter detayları
    referans-santral sınıfı varsayılanlarla doldurulur (demo betiğiyle
    aynı). İleride sihirbaz bu alanları toplarsa buradan geçer.
    """
    from pvquant.models_v2.contracts import (
        InverterSpec, Location, MountingSpec, PanelSpec, PlantProfile,
    )
    kwp = float(plant_ctx["capacity_kwp"])
    # B-1 v2.27 Yol A: AC tavanı varsa uygula, yoksa geriye uyumlu (kwp/21)
    ac_limit = plant_ctx.get("ac_limit_kw")
    inv_ac = (float(ac_limit) / 21.0) if ac_limit else (kwp / 21.0)
    return PlantProfile(
        plant_id=plant_name.replace(" ", "_")[:32] or "PLANT",
        name=plant_name,
        location=Location(
            latitude=float(plant_ctx["latitude"]),
            longitude=float(plant_ctx["longitude"]),
            timezone=plant_ctx.get("timezone", "Europe/Istanbul"),
            elevation_m=float(plant_ctx.get("elevation_m", 1000)),
        ),
        dc_capacity_kwp=kwp,
        panel_count=int(plant_ctx.get("panel_count", max(1, round(kwp * 1000 / 545)))),
        panel=PanelSpec(
            technology=plant_ctx.get("panel_technology", "bifacial"),
            nominal_power_w=545,
            temperature_coefficient_gamma=-0.34,
            noct_celsius=45,
            bifaciality_factor=0.7,
        ),
        mounting=MountingSpec(
            mount_type="ground_fixed",
            tilt_degrees=float(plant_ctx.get("tilt", 20)),
            azimuth_degrees=float(plant_ctx.get("azimuth", 180)),
            height_above_ground_m=2.0,
        ),
        inverter=InverterSpec(ac_capacity_kw=inv_ac, count=21, efficiency=0.98),
    )


# --------------------------------------------------------------------- eğitim
def run_hybrid_training(
    scada,
    historical_meteo,
    plant_ctx: dict,
    plant_name: str = "Santral",
) -> HybridUIResult:
    """Hibrit modeli eğitir; UI'nın 'Hibritle iyileştir' butonu bunu çağırır.

    Meteo paylaşımı: HistoricalData.data'ya ghi/t_air/wind_speed kolonları
    historical_meteo'dan REINDEX ile enjekte edilir — HybridResidualModel
    saha meteo verisi gördüğünde kendi Open-Meteo çağrısını ATLAR
    (models_v2'deki kısayol). Böylece tek meteo çekişi olur.
    """
    try:
        from pvquant.models_v2.contracts import HistoricalData
        from pvquant.models_v2.hybrid_residual import HybridResidualModel

        p = scada.power_kw
        idx = p.index
        df = pd.DataFrame({"timestamp": idx, "power_kw": p.values})

        # meteo enjeksiyonu (paylaşım — kendi fetch'i yok)
        for kolon, seri in (
            ("ghi", historical_meteo.ghi),
            ("t_air", historical_meteo.temp_air),
            ("wind_speed", historical_meteo.wind_speed_10m),
        ):
            df[kolon] = seri.reindex(idx).values
        # SCADA'nın kendi sensörleri varsa onlar da girsin
        if scada.poa_irradiance is not None:
            df["poa_global"] = scada.poa_irradiance.reindex(idx).values
        if getattr(scada, "temp_module", None) is not None:
            df["t_module"] = scada.temp_module.reindex(idx).values

        profil = _plant_profile(plant_ctx, plant_name)
        model = HybridResidualModel(profil)
        model.calibrate(HistoricalData(plant_id=profil.plant_id, data=df))

        r = dict(getattr(model, "_training_report", {}) or {})

        def _san(v):
            # v2.57: NaN JSON'a "NaN" olarak gider, Postgres jsonb reddeder
            try:
                return None if v is None or v != v else float(v)
            except TypeError:
                return None
        hib = r.get("mape_pct_hybrid_holdout")
        whib = r.get("wmape_pct_hybrid_holdout")
        fiz = r.get("mape_pct_physics_holdout")
        wfiz = r.get("wmape_pct_physics_holdout")
        iyilesme = None
        if hib is not None and fiz not in (None, 0):
            iyilesme = (fiz - hib) / fiz * 100.0
        logger.info("Hibrit egitim tamam: holdout MAPE %%%.1f", hib if hib is not None else -1.0)
        return HybridUIResult(
            ok=True, model=model,
            holdout_mape_pct=hib,
            holdout_wmape_pct=whib,
            physics_wmape_pct=wfiz,
            holdout_rmse_kw=r.get("rmse_kw_hybrid_holdout"),
            physics_mape_pct=fiz,
            improvement_pct=iyilesme,
            holdout_hours=int(r["holdout_hours"]) if r.get("holdout_hours") else None,
            coverage_p10_p90_pct=_san(r.get("coverage_p10_p90_holdout_pct")),
            band_width_mean_kw=_san(r.get("band_width_mean_kw")),
            band_width_pct_of_p50=_san(r.get("band_width_pct_of_p50")),
            trained_at=datetime.now(timezone.utc),
            raw_report=r,
        )
    except Exception as e:                     # bilinçli geniş yakalama:
        logger.exception("Hibrit eğitim başarısız — fiziğe düşülüyor")
        return HybridUIResult(ok=False, error=f"{type(e).__name__}: {e}")


# ------------------------------------------------------------- tahmin adaptörü
def hybrid_forecast_hourly(model, meteo) -> Optional[pd.DataFrame]:
    """Eğitilmiş hibrit model + MeteoData -> raporlama uyumlu saatlik çerçeve.

    Dönen kolonlar: p50_kw, p10_kw (alt), p90_kw (üst), energy_kwh, poa,
    temp_cell, p_dc_kw — pipeline ForecastResult.hourly ile aynı dil.

    Kantil notu (dürüstlük): models_v2 güven aralığı yalnız DÖNEM TOPLAMI
    kantillerini verir (p10/p50/p90 toplam kWh). Saatlik bant, toplam
    oranlarının saatliğe ölçeklenmesiyle türetilir — şekil korunur,
    saat-bazlı asimetri taşınmaz. Saatlik kantil, modelin kendi yol
    haritasında; adaptör o gün tek satır değişir.

    Adlandırma köprüsü: models_v2 p10=0.10 kantili (DÜŞÜK senaryo).
    Raporlamada p10_kw=alt bant, p90_kw=üst bant olarak eşlenir; IEA
    aşılma dilinde 'P90' bu ALT banda karşılık gelir (kutu etiketleri
    zaten bu dili kullanıyor).
    """
    try:
        from pvquant.models_v2.contracts import ForecastInput, OperationConfig

        fi = ForecastInput(
            source="open_meteo", resolution_minutes=60,
            data=pd.DataFrame({
                "timestamp": meteo.ghi.index,
                "ghi": meteo.ghi.values,
                "t_air": meteo.temp_air.values,
                "wind_speed": meteo.wind_speed_10m.values,
            }),
        )
        res = model.predict(fi, OperationConfig(
            operation_mode="calibrated", confidence_intervals=True))
        ts = res.timeseries.copy()
        ts = ts.set_index(pd.DatetimeIndex(ts["timestamp_utc"], tz="UTC")
                          if ts["timestamp_utc"].dt.tz is None
                          else ts["timestamp_utc"])
        h = pd.DataFrame(index=ts.index)
        h["p50_kw"] = ts["ac_power_kw"].values
        h["poa"] = ts.get("poa_global", pd.Series(0.0, index=ts.index)).values
        h["temp_cell"] = ts.get("t_cell", pd.Series(25.0, index=ts.index)).values
        h["p_dc_kw"] = ts.get("dc_power_kw", h["p50_kw"] * 1.03).values
        h["energy_kwh"] = h["p50_kw"]          # saatlik çözünürlük
        if res.confidence is not None and res.confidence.p50_total_kwh > 0:
            c = res.confidence
            h["p10_kw"] = h["p50_kw"] * (c.p10_total_kwh / c.p50_total_kwh)
            h["p90_kw"] = h["p50_kw"] * (c.p90_total_kwh / c.p50_total_kwh)
        return h
    except Exception:
        logger.exception("Hibrit tahmin başarısız — fiziğe düşülüyor")
        return None
