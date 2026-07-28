"""Kalibrasyon: DB'den oku -> mevcut motoru cagir -> DB'ye yaz.
Zeyilname v1.6: quality_json 4 alanli sozlesme (mape_pct/mape_before_pct/
deviation_pct/deviation_before_pct + warnings)."""
from __future__ import annotations
import json, pickle, pathlib
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.services.ingest_service import scada_oku
from pvquant.io.scada import SCADAData
from pvquant.io.meteo import OpenMeteoClient
from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.pipeline.forecast import PlantSpec
from pvquant.pipeline.hybrid_ui import run_hybrid_training, session_ozeti

ARTIFACT_DIR = pathlib.Path("var/artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)



def _kalibrasyon_izgarasi(df: pd.DataFrame, plant: dict) -> pd.DataFrame:
    """scada_oku ciktisini kalibrasyon motorunun istedigi kesintisiz
    saatlik izgaraya oturtur. Mantik frontend/veri_yukleme.py
    _kopru_scadadata_ve_gec'ten TASINDI (Faz 1 saha-kanitli) —
    yeniden yazilmadi. UI kopyasi Anayasa Adim 3'te silinecek."""
    if not isinstance(df.index, pd.DatetimeIndex) or len(df) <= 1:
        return df
    full_range = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="1h",
        tz=df.index.tz,
    )
    df = df.reindex(full_range)
    df.index.name = "timestamp"
    # Gece saatlerinde NaN power_kw -> 0 doldur (gercekte uretim yok)
    # Gunduz NaN'lari NaN kalir (backend duser). Boylece index tam kalir
    # ama gunduzun tam satirlari kesintisiz olur -> %90+ tutarlilik.
    try:
        import pvlib
        solpos = pvlib.solarposition.get_solarposition(
            df.index, plant["lat"], plant["lon"],
        )
        is_night = solpos["apparent_elevation"] < -3.0
        night_nan_mask = is_night.values & df["power_kw"].isna().values
        df.loc[night_nan_mask, "power_kw"] = 0.0
    except Exception:
        # pvlib yoksa fallback: tum NaN'lari 0 yap (daha az temiz ama calisir)
        df["power_kw"] = df["power_kw"].fillna(0.0)
    return df


def _scada_data(tenant_id, plant) -> SCADAData:
    df = _kalibrasyon_izgarasi(scada_oku(tenant_id, plant["id"]), plant)
    def _o(k):
        return df[k] if k in df.columns and df[k].notna().any() else None
    return SCADAData(
        power_kw=df["power_kw"], energy_kwh=_o("energy_kwh"),
        poa_irradiance=_o("poa_wm2"), temp_ambient=_o("t_air"),
        temp_module=_o("t_module"), wind_speed=_o("wind_ms"),
        plant_name=plant["name"], timestep_minutes=60,
    )


def _meteo(plant, df_index):
    start = df_index.min().strftime("%Y-%m-%d")
    end = df_index.max().strftime("%Y-%m-%d")
    return OpenMeteoClient().get_historical(
        latitude=plant["lat"], longitude=plant["lon"],
        start_date=start, end_date=end,
    )


def _plant_spec(plant) -> PlantSpec:
    return PlantSpec(
        p_nom_kwp=plant["capacity_kwp"], latitude=plant["lat"],
        longitude=plant["lon"], tilt=plant.get("tilt") or 20.0,
        azimuth=plant.get("azimuth") or 180.0,
        bifacial_factor=0.7 if plant.get("panel_tech") == "bifacial" else 0.0,
        # B-1 Adım 3: AC kırpma köprüsü (None = kırpma yok, mevcut davranış)
        p_ac_clip_kw=plant.get("ac_limit_kw"),
    )


def kalibre_et(tenant_id, plant: dict, hibrit: bool = False) -> dict:
    scada = _scada_data(tenant_id, plant)
    meteo = _meteo(plant, scada.power_kw.index)
    cr = calibrate_from_scada(
        scada=scada, historical_meteo=meteo, plant=_plant_spec(plant),
        fit_bg=True, fit_eta_bos=True, clean_outliers=True,
    )
    sonuc = {
        "mode": "B", "eta_bos": cr.eta_bos, "bg": cr.bg,
        "warnings": list(cr.warnings or []),
        "n_valid_hours": cr.n_valid_hours,
    }
    gate = None
    hyb = None
    if hibrit:
        res = run_hybrid_training(
            scada=scada, historical_meteo=meteo,
            plant_ctx={
                "capacity_kwp": plant["capacity_kwp"],
                "latitude": plant["lat"], "longitude": plant["lon"],
                "timezone": plant["tz"],
                "tilt": plant.get("tilt") or 20,
                "azimuth": plant.get("azimuth") or 180,
                "panel_technology": plant.get("panel_tech") or "bifacial",
                # B-1 v2.27: AC tavanı kaynağı → PlantProfile ailesi
                "ac_limit_kw": plant.get("ac_limit_kw"),
            },
            plant_name=plant["name"],
        )
      # v2.40: kapi cift kosullu — GORELI iyilesme YETMEZ, MUTLAK taban sart.
        # %35 ustu holdout MAPE "kullanilabilir model" degildir; kapi kapali
        # kalir, sistem Mod B'de durur ve sebep karneye yazilir.
        HIBRIT_MUTLAK_TAVAN = 35.0            # eski MAPE tavani — yedek yol
        HIBRIT_MUTLAK_TAVAN_WMAPE = 25.0      # v2.51-B: birincil kapi (WMAPE)
        _w = getattr(res, "holdout_wmape_pct", None)
        _wtxt = f"{_w:.1f}" if _w is not None else "yok"
        _taban_ok = ((_w <= HIBRIT_MUTLAK_TAVAN_WMAPE) if _w is not None
                     else (res.holdout_mape_pct is not None
                           and res.holdout_mape_pct <= HIBRIT_MUTLAK_TAVAN))
        if (res.ok and res.improvement_pct is not None
                and res.improvement_pct >= 3.0
                and _taban_ok):
            sonuc["mode"] = "C"
            hyb = res
            gate = {
                "denendi": True, "gecti": True,
                "iyilesme_pct": res.improvement_pct,
                "holdout_mape": res.holdout_mape_pct,
                "fizik_mape": res.physics_mape_pct,
                "holdout_wmape": _w,
                "fizik_wmape": getattr(res, "physics_wmape_pct", None),
            }
        else:
            gate = {
                "denendi": True, "gecti": False,
                "iyilesme_pct": res.improvement_pct,
                "holdout_mape": res.holdout_mape_pct,
                "fizik_mape": res.physics_mape_pct,
                "holdout_wmape": _w,
                "fizik_wmape": getattr(res, "physics_wmape_pct", None),
                "sebep": (res.error
                          or (f"holdout WMAPE %{_wtxt} > "
                              f"%{HIBRIT_MUTLAK_TAVAN_WMAPE:.0f} tavanı (WMAPE)"
                              if not _taban_ok
                              else f"iyilesme %{res.improvement_pct:.1f} < 3")),            }
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "UPDATE calibrations SET active=false WHERE plant_id=:p"),
            {"p": plant["id"]})
        cal_id = s.execute(text(
            "INSERT INTO calibrations(tenant_id,plant_id,mode,params_json,"
            " quality_json,gate_json,n_valid_hours,active) "
            "VALUES(:t,:p,:m,:pa,:q,:g,:n,true) RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "m": sonuc["mode"],
             "pa": json.dumps({"eta_bos": cr.eta_bos, "bg": cr.bg}),
             "q": json.dumps({
                 "mape_pct":            getattr(cr.validation_after,  "mape_pct", None),
                 "mape_before_pct":     getattr(cr.validation_before, "mape_pct", None),
                 "wmape_pct":           getattr(cr.validation_after,  "wmape_pct", None),
                 "wmape_before_pct":    getattr(cr.validation_before, "wmape_pct", None),
                 "deviation_pct":       getattr(cr.validation_after,  "total_deviation_pct", None),
                 "deviation_before_pct":getattr(cr.validation_before, "total_deviation_pct", None),
                 "warnings": sonuc["warnings"],
             }, default=str),
             "g": json.dumps(gate) if gate else None,
             "n": cr.n_valid_hours}).scalar()
        if hyb is not None:
            yol = ARTIFACT_DIR / f"hyb_{plant['id']}_{cal_id}.pkl"
            with open(yol, "wb") as f:
                pickle.dump(hyb.model, f)
            s.execute(text(
                "UPDATE ml_models SET active=false WHERE plant_id=:p"),
                {"p": plant["id"]})
            s.execute(text(
                "INSERT INTO ml_models(tenant_id,plant_id,artifact_path,"
                " training_report_json,active) VALUES(:t,:p,:y,:r,true)"),
                {"t": tenant_id, "p": plant["id"], "y": str(yol),
                 "r": json.dumps(session_ozeti(hyb), default=str)})
    sonuc["calibration_id"] = str(cal_id)
    sonuc["gate"] = gate
    return sonuc


def aktif_kalibrasyon(tenant_id, plant_id):
    """UI'nin tek kalibrasyon okuması. Yoksa None."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "SELECT id, mode, params_json, quality_json, gate_json,"
            " n_valid_hours, created_at FROM calibrations "
            "WHERE plant_id=:p AND active LIMIT 1"),
            {"p": plant_id}).first()

def kalibrasyon_gecmisi(tenant_id, plant_id):
    """Mod gecmisi icin tum kayitlar (eski->yeni)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "SELECT created_at, mode, gate_json FROM calibrations "
            "WHERE plant_id=:p ORDER BY created_at"),
            {"p": plant_id}).fetchall()
