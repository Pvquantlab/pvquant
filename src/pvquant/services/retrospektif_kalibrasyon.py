"""G4-P1 (26.11.2026) — RETROSPEKTİF kalibrasyon deneyi: DB yok, ağ yok, yazma yok; üretim kalibrasyon yolu (`calib_service.kalibre_et`)
DEĞİŞMEZ ve çağrılmaz.

Faz 1 G4 kapısı (Mod B: n_valid ≥ 100 gündüz saati, holdout WMAPE, |toplam sapma| ≤ %30) geçmiş dış veriyle — PVDAQ Golden 33 2018
(ext/kaynak/pvdaq) + analiz/uydu meteosu (PVGIS ERA5 / CAMS) — denenir. Üretim yolundaki `kalibrasyon_penceresi` (02.10.2026 NWP arşiv
kesimi) burada UYGULANMAZ, çünkü kesim «kendi arşivimizin ışınımı kaymış» bulgusu içindir; dış meteo bu kusuru taşımaz. Bu bilerek ve
açıkça etiketlenir: sonuç «retrospektif model deneyi»dir, operasyonel iddia DEĞİLDİR, `calibrations` tablosuna yazılmaz, canlıya
taşınmaz. Aynı motor fonksiyonları kullanılır: `calibrate_from_scada`, `_kronolojik_holdout`, `mod_b_kapisi`, `plant_spec_kur`.
"""
from __future__ import annotations

import pandas as pd

ETIKET = "retrospektif_model_deneyi"
GEREKLI = ("power_kw",)


def scada_cercevesi(df: pd.DataFrame, plant: dict):
    """Saatlik ölçüm çerçevesi (ts_utc index; power_kw, energy_kwh?, poa_wm2?, t_air?, t_module?) → SCADAData (kesintisiz saatlik ızgara).
    `kalibrasyon_penceresi` uygulanmaz (bkz. modül notu)."""
    from pvquant.io.scada import SCADAData
    from pvquant.services.calib_service import _kalibrasyon_izgarasi
    for k in GEREKLI:
        if k not in df.columns:
            raise ValueError(f"ölçüm çerçevesinde {k} yok")
    d = df.copy()
    if not isinstance(d.index, pd.DatetimeIndex):
        d.index = pd.to_datetime(d.index, utc=True)
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    d = d.sort_index()
    d = _kalibrasyon_izgarasi(d, plant)

    def _o(k):
        return d[k] if k in d.columns and d[k].notna().any() else None
    return SCADAData(power_kw=d["power_kw"], energy_kwh=_o("energy_kwh"), poa_irradiance=_o("poa_wm2"), temp_ambient=_o("t_air"),
                     temp_module=_o("t_module"), wind_speed=_o("wind_ms"), plant_name=str(plant.get("name") or "retrospektif"),
                     timestep_minutes=60)


def meteo_cercevesi(df: pd.DataFrame, lat: float, lon: float, kaynak: str = "analiz") -> object:
    """Saatlik meteo çerçevesi (ts_utc index; ghi, temp_air, wind_speed_10m?) → MeteoData (UTC). Eksik rüzgar → 1 m/s sabit (not düşülür)."""
    from pvquant.io.meteo import MeteoData
    d = df.copy()
    if not isinstance(d.index, pd.DatetimeIndex):
        d.index = pd.to_datetime(d.index, utc=True)
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    d = d.sort_index()
    if "ghi" not in d.columns or "temp_air" not in d.columns:
        raise ValueError("meteo çerçevesinde ghi ve temp_air gerekir")
    ruzgar = d["wind_speed_10m"] if "wind_speed_10m" in d.columns else pd.Series(1.0, index=d.index)
    return MeteoData(ghi=d["ghi"].astype(float).clip(lower=0.0), temp_air=d["temp_air"].astype(float), wind_speed_10m=ruzgar.astype(float),
                     relative_humidity=None, cloud_cover=None, latitude=float(lat), longitude=float(lon), timezone="UTC",
                     kaynak=kaynak, nwp_model=kaynak)


def kalibre_et_retrospektif(scada_df: pd.DataFrame, meteo, plant: dict, *, meteo_kaynak: str = "analiz") -> dict:
    """Mod B retrospektif kalibrasyon + kronolojik holdout + G2-C1 Mod B kapısı. Döner (yazmaz): etiket, mode (B | atlandi), kapi,
    eta_bos, bg, n_valid_hours, wmape_pct, sapma_pct, holdout{…}, pencere{…}, uyarilar, meteo_kaynak, not."""
    from pvquant.pipeline.calibration import calibrate_from_scada
    from pvquant.services.calib_service import _kronolojik_holdout, mod_b_kapisi
    from pvquant.services.plant_spec_service import plant_spec_kur
    scada = scada_cercevesi(scada_df, plant)
    spec = plant_spec_kur(plant)
    idx = scada.power_kw.index
    pencere = {"bas": idx.min().isoformat(), "bit": idx.max().isoformat(), "saat": len(idx), "gecerli_saat": int(scada.power_kw.notna().sum())}
    try:
        cr = calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=spec, fit_bg=True, fit_eta_bos=True, clean_outliers=True)
    except ValueError as e:   # motorun asgari veri kuralı (ör. <100 saat) — deney düşmez, «atlandı» olarak raporlanır
        return {"etiket": ETIKET, "mode": "atlandi", "kapi": f"motor: {e}", "eta_bos": None, "bg": None, "n_valid_hours": 0,
                "wmape_pct": None, "wmape_once_pct": None, "sapma_pct": None, "holdout": {}, "uyarilar": [], "pencere": pencere,
                "santral": {"ad": plant.get("name"), "kwp": plant.get("capacity_kwp"), "panel_tech": plant.get("panel_tech"), "bifacial_factor": spec.bifacial_factor},
                "meteo_kaynak": meteo_kaynak, "not": "retrospektif model deneyi: motor asgari veri kuralı; yazılmaz"}
    try:
        holdout = _kronolojik_holdout(scada, meteo, spec)
    except Exception as e:   # ölçüm yardımcı; deney düşmez
        holdout = {"wmape_holdout_pct": None, "mape_holdout_pct": None, "holdout_saat": None, "holdout_not": f"hesaplanamadı: {type(e).__name__}"}
    sapma = getattr(cr.validation_after, "total_deviation_pct", None)
    kapi_ok, kapi_neden = mod_b_kapisi(cr.n_valid_hours, holdout.get("wmape_holdout_pct"), sapma)
    return {"etiket": ETIKET, "mode": "B" if kapi_ok else "atlandi", "kapi": kapi_neden,
            "eta_bos": float(cr.eta_bos), "bg": float(cr.bg), "n_valid_hours": int(cr.n_valid_hours),
            "wmape_pct": getattr(cr.validation_after, "wmape_pct", None), "wmape_once_pct": getattr(cr.validation_before, "wmape_pct", None),
            "sapma_pct": sapma, "holdout": holdout, "uyarilar": list(cr.warnings or []) + list(cr.notes or []),
            "pencere": pencere,
            "santral": {"ad": plant.get("name"), "kwp": plant.get("capacity_kwp"), "panel_tech": plant.get("panel_tech"), "bifacial_factor": spec.bifacial_factor},
            "meteo_kaynak": meteo_kaynak,
            "not": "retrospektif model deneyi: kalibrasyon_penceresi uygulanmadı; calibrations tablosuna YAZILMAZ; operasyonel iddia değildir"}
