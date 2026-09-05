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
    df = scada_oku(tenant_id, plant["id"])
    # v2.254 (Dalga 3.9): AC tavanında kırpılmış saatler kalibrasyona GİRMEZ — tavanlı güç DC fiziğini
    # yansıtmaz, eta_bos/BG uydurmasını aşağı çeker. Ölçüm silinmez; yalnız bu uydurmada NaN (gündüz NaN
    # → motor düşer). Karne bu saatleri saymaya devam eder (tahmin de tavanı modellemeli).
    if "kirpma" in df.columns:
        df.loc[df["kirpma"].fillna(False).astype(bool), "power_kw"] = float("nan")
    df = _kalibrasyon_izgarasi(df, plant)
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
        # v2.255: santral params_json ile açılan fizik terimleri (varsayılan kapalı)
        iam_model=_pj(plant).get("iam_model") or "none",
        spectral_model=_pj(plant).get("spectral_model") or "none",
    )


def _pj(plant) -> dict:
    """plants.params_json — dict ya da JSON metni ya da None."""
    pj = plant.get("params_json") if hasattr(plant, "get") else None
    if isinstance(pj, str):
        try:
            return json.loads(pj)
        except Exception:
            return {}
    return pj or {}


def fizik_terimleri(tenant_id, plant_id) -> dict:
    """v2.255 — UI sözlüğü: IAM/spektral (santral) + kt referansı (ayar)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.config import get_settings
    with tenant_baglami(tenant_id) as s:
        pj = s.execute(text("SELECT params_json FROM plants WHERE id=:p"), {"p": plant_id}).scalar()
    pj = _pj({"params_json": pj})
    return {"iam": pj.get("iam_model") or "none", "spektral": pj.get("spectral_model") or "none",
            "kt_referans": get_settings().kt_referans}


def _pencere_gun(index) -> int | None:
    """v2.175: kalibrasyon penceresi (takvim günü) — kalibrasyonun GERÇEKTEN
    kullandığı ızgaranın ucundan uca aralığı. Gömülü 120 değil, iddia değil,
    ÖLÇÜM: rapor kontratındaki calibration.window_days bunu taşır; s09
    altyazısının ', N gün' iddiası ve D5'in tavan denetimi (saat ≤ gün×14)
    bu ölçüme dayanır. Boş/tekil indekste None — uydurma pencere yok
    (dürüst-eksiklik: iddia yoksa kart pencereyi söylemez, D5 uyarır)."""
    try:
        if index is None or len(index) < 2:
            return None
        return int((index.max() - index.min()).days) + 1
    except (TypeError, AttributeError, ValueError):
        return None


def kalibre_et(tenant_id, plant: dict, hibrit: bool = False) -> dict:
    scada = _scada_data(tenant_id, plant)
    pencere_gun = _pencere_gun(scada.power_kw.index)   # v2.175: ölçülü pencere
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
        from pvquant.config import get_settings as _gs
        _cfg = _gs()
        HIBRIT_MUTLAK_TAVAN = _cfg.gate_mape_ceiling          # v2.53: ayardan
        HIBRIT_MUTLAK_TAVAN_WMAPE = _cfg.gate_wmape_ceiling   # v2.53: ayardan
        _w = getattr(res, "holdout_wmape_pct", None)
        _wtxt = f"{_w:.1f}" if _w is not None else "yok"
        _taban_ok = ((_w <= HIBRIT_MUTLAK_TAVAN_WMAPE) if _w is not None
                     else (res.holdout_mape_pct is not None
                           and res.holdout_mape_pct <= HIBRIT_MUTLAK_TAVAN))
        # v2.51-C: goreli esik de WMAPE diline tasinir. Ayrisma vakasi #1
        # kaniti: ayni holdout'ta MAPE-iyilesmesi %-43 derken WMAPE
        # hibriti 0,23p onde gormustu — kapi karari yanlis dilden geliyordu.
        _pw = getattr(res, "physics_wmape_pct", None)
        _w_iyi = (float((_pw - _w) / _pw * 100.0)
                  if (_w is not None and _pw is not None and _pw > 0) else None)
        _iyi_etkin = _w_iyi if _w_iyi is not None else res.improvement_pct
        _iyi_dil = "WMAPE" if _w_iyi is not None else "MAPE (yedek yol)"
        if (res.ok and _iyi_etkin is not None
                and _iyi_etkin >= _cfg.gate_min_improvement_pct
                and _taban_ok):
            sonuc["mode"] = "C"
            hyb = res
            gate = {
                "denendi": True, "gecti": True,
                "iyilesme_pct": res.improvement_pct,
                "wmape_iyilesme_pct": _w_iyi,
                "holdout_mape": res.holdout_mape_pct,
                "fizik_mape": res.physics_mape_pct,
                "holdout_wmape": _w,
                "fizik_wmape": getattr(res, "physics_wmape_pct", None),
                "kapsama_p10_p90": getattr(res, "coverage_p10_p90_pct", None),
                "bant_ort_kw": getattr(res, "band_width_mean_kw", None),
                "bant_pct": getattr(res, "band_width_pct_of_p50", None),
            }
        else:
            gate = {
                "denendi": True, "gecti": False,
                "iyilesme_pct": res.improvement_pct,
                "wmape_iyilesme_pct": _w_iyi,
                "holdout_mape": res.holdout_mape_pct,
                "fizik_mape": res.physics_mape_pct,
                "holdout_wmape": _w,
                "fizik_wmape": getattr(res, "physics_wmape_pct", None),
                "kapsama_p10_p90": getattr(res, "coverage_p10_p90_pct", None),
                "bant_ort_kw": getattr(res, "band_width_mean_kw", None),
                "bant_pct": getattr(res, "band_width_pct_of_p50", None),
                "sebep": (res.error
                          or (f"holdout WMAPE %{_wtxt} > "
                              f"%{HIBRIT_MUTLAK_TAVAN_WMAPE:.0f} tavanı (WMAPE)"
                              if not _taban_ok
                              else (f"iyilesme %{_iyi_etkin:.1f} < "
                                    f"{_cfg.gate_min_improvement_pct:g} ({_iyi_dil})"
                                    if _iyi_etkin is not None
                                    else "iyilesme hesaplanamadi"))),            }
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
                 # v2.175: kök iş kapanışı — report_service:127 bu alanı
                 # okuyordu, pipeline yazmıyordu; artık ölçümden yazılıyor.
                 "window_days": pencere_gun,
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
            "WHERE plant_id=:p AND active "
            "ORDER BY created_at DESC LIMIT 1"),
            {"p": plant_id}).first()

def kalibrasyon_ozeti(tenant_id, plant_id):
    """v2.122 — aktif kaydin UI sozlesmesi (JSON-donusur sozluk).
    UYDURMA YOK: kayit ne tasiyorsa o; uyarilar dahil. Yoksa None."""
    r = aktif_kalibrasyon(tenant_id, plant_id)
    if r is None:
        return None
    q = r.quality_json or {}
    pj = r.params_json or {}
    return {
        "mode": r.mode,
        "fizik_terimleri": fizik_terimleri(tenant_id, plant_id),   # v2.255
        "eta_bos": pj.get("eta_bos"), "bg": pj.get("bg"),
        "gecerli_saat": r.n_valid_hours,
        "tarih": r.created_at.isoformat() if r.created_at else None,
        "mape_once": q.get("mape_before_pct"), "mape_sonra": q.get("mape_pct"),
        "wmape_once": q.get("wmape_before_pct"), "wmape_sonra": q.get("wmape_pct"),
        "sapma_once": q.get("deviation_before_pct"), "sapma_sonra": q.get("deviation_pct"),
        "uyarilar": q.get("warnings") or [],
    }


def kalibrasyon_gecmisi(tenant_id, plant_id):
    """Mod gecmisi icin tum kayitlar (eski->yeni)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "SELECT created_at, mode, gate_json FROM calibrations "
            "WHERE plant_id=:p ORDER BY created_at"),
            {"p": plant_id}).fetchall()
