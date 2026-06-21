"""POST /calibration-scada — SCADA POA + T_air ile tezin saf modelini uygula.

Bu endpoint Open-Meteo'yu hiç çağırmaz. SCADA CSV'sinden:
  - power_kw (gerçek üretim)
  - poa_global (W/m²) — FusionSolar'dan ölçülmüş POA
  - t_air (°C) — FusionSolar'dan ortam sıcaklığı

okur ve tezdeki Bölüm 3.3.7 yöntemini birebir uygular:
  - Saatlik (BG · BF · A)_h değerini izole et (Denklem 3.8)
  - Işınım-ağırlıklı yıllık ortalama al
  - BG = ortalama_net_katki / (BF · A)
  - η_BoS'u toplam üretim oranıyla fit et

Tezdeki sonuç: %2.59 yıllık sapma. Aynı sonucu burada da yakalamayı hedefliyoruz.
"""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from pvquant.api.schemas.plant import PlantSpecSchema
from pvquant.models.power import (
    BarhdadiBennisParams,
    eta_rel_barhdadi_bennis,
    G_STC,
)
from pvquant.models.temperature import cell_temperature_noct

router = APIRouter(prefix="/calibration-scada", tags=["calibration"])


class ScadaCalibrationResponse(BaseModel):
    """SCADA-only kalibrasyon sonucu."""

    original_plant: PlantSpecSchema
    calibrated_plant: PlantSpecSchema
    bg: float
    eta_bos: float
    yearly_bifacial_gain_pct: float
    yearly_actual_mwh: float
    yearly_model_mwh: float
    deviation_pct: float
    n_valid_hours: int
    monthly_breakdown: list[dict[str, Any]]
    notes: list[str]


def _save_upload(upload: UploadFile) -> str:
    """Geçici dosyaya kaydet."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
        f.write(upload.file.read())
        return f.name


@router.post("/", response_model=ScadaCalibrationResponse)
def calibrate_scada(
    plant_json: str = Form(..., description="PlantSpecSchema JSON string"),
    scada_csv: UploadFile = File(..., description="SCADA CSV (power_kw, poa_global, t_air)"),
) -> ScadaCalibrationResponse:
    """Tezdeki Denklem 3.8 ile saha verisinden BG'yi geri çöz."""
    # Schema parse
    try:
        plant_dict = json.loads(plant_json)
        plant_schema = PlantSpecSchema(**plant_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"plant_json parse hatası: {e}")

    plant = plant_schema.to_dataclass()

    # CSV yükle (doğrudan pandas — SCADA loader alias gerektirmesin)
    csv_path = _save_upload(scada_csv)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV okunamadı: {e}")

    # Gerekli kolonlar
    required = {"timestamp", "power_kw", "poa_global", "t_air"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"SCADA CSV'de eksik kolon: {missing}. Gerekli: {required}",
        )

    notes: list[str] = []

    # 1. Pandas Series yap
    ts = pd.to_datetime(df["timestamp"])
    df = df.assign(timestamp=ts).set_index("timestamp").sort_index()
    poa = df["poa_global"].astype(float)
    t_air = df["t_air"].astype(float)
    actual = df["power_kw"].astype(float)
    notes.append(f"SCADA satır: {len(df)}, dönem: {ts.min().date()} → {ts.max().date()}")

    # 2. Geçerli saat filtresi (tezdeki: G ≥ 50 W/m² ve E > 0)
    threshold = 50.0
    valid_mask = (poa >= threshold) & (actual > 0)
    n_valid = int(valid_mask.sum())
    notes.append(f"Geçerli saat (POA≥50 W/m², E>0): {n_valid}")

    if n_valid < 100:
        raise HTTPException(status_code=400, detail=f"Çok az geçerli saat: {n_valid}")

    poa_v = poa[valid_mask]
    t_air_v = t_air[valid_mask]
    actual_v = actual[valid_mask]

    # 3. Hücre sıcaklığı (NOCT — tezdeki Denklem 3.1)
    t_cell_v = cell_temperature_noct(poa_v, t_air_v, plant.noct)

    # 4. Tezin η_rel(G, T_cell) hesabı — BİFACİAL OLMADAN (ışınım + sıcaklık terimleri)
    params = BarhdadiBennisParams(c1=0.033, c2=-0.0092, gamma=plant.gamma_pdc)
    eta_rel_no_bifacial = eta_rel_barhdadi_bennis(poa_v, t_cell_v, params)

    # 5. Kayıpsız teorik DC güç (Denklem 3.3, bifacial dışında)
    p_dc_no_bifacial = plant.p_nom_kwp * (poa_v / G_STC) * eta_rel_no_bifacial

    # 6. Gerçek η_rel ölçümden (Denklem 3.7):
    # η_rel,gerçek = E_gerçek / (P_nom * G/G0 * η_BoS)
    eta_bos_initial = plant.eta_bos
    eta_rel_actual = actual_v / (plant.p_nom_kwp * (poa_v / G_STC) * eta_bos_initial)

    # 7. Saatlik bifacial katkı izole (Denklem 3.8)
    # (BG · BF · A)_h = η_rel,gerçek / (η_ışınım · η_sıcaklık) − 1
    bifacial_term_hourly = eta_rel_actual / eta_rel_no_bifacial - 1.0

    # 8. Fiziksel filtre: -0.05 < katkı < 0.20 dışı outlier
    physical_mask = (bifacial_term_hourly > -0.05) & (bifacial_term_hourly < 0.20)
    n_physical = int(physical_mask.sum())
    notes.append(f"Fiziksel filtre sonrası: {n_physical}")

    bif_hourly_clean = bifacial_term_hourly[physical_mask]
    poa_clean = poa_v[physical_mask]

    # 9. Işınım-ağırlıklı yıllık ortalama (tezdeki yöntem)
    yearly_bifacial_ratio = float(
        (bif_hourly_clean * poa_clean).sum() / poa_clean.sum()
    )
    yearly_bifacial_pct = yearly_bifacial_ratio * 100
    notes.append(f"Işınım-ağırlıklı yıllık net bifacial katkı: %{yearly_bifacial_pct:.2f}")

    # 10. BG izole (Denklem: BG = bifacial_katkı / (BF · A))
    if plant.bifacial_factor * plant.albedo > 0:
        fitted_bg = float(
            np.clip(yearly_bifacial_ratio / (plant.bifacial_factor * plant.albedo), 0.05, 0.60)
        )
    else:
        fitted_bg = plant.bifacial_gain_geometric
        notes.append("BF veya A 0 → BG fit atlandı")
    notes.append(f"BG: {plant.bifacial_gain_geometric:.4f} → {fitted_bg:.4f}")

    # 11. η_BoS fit — kalibre BG ile toplam tahmin yap, oran al
    eta_rel_full = eta_rel_no_bifacial * (1 + fitted_bg * plant.bifacial_factor * plant.albedo)
    p_dc_full = plant.p_nom_kwp * (poa_v / G_STC) * eta_rel_full
    # E_model = E_h * η_BoS — geçerli saatler için
    total_act = float(actual_v.sum())
    total_pdc_no_bos = float(p_dc_full.sum())
    if total_pdc_no_bos > 0:
        ratio = total_act / (total_pdc_no_bos * eta_bos_initial)
        fitted_eta_bos = float(np.clip(eta_bos_initial * ratio, 0.70, 0.99))
        notes.append(
            f"η_BoS: {eta_bos_initial:.4f} → {fitted_eta_bos:.4f} (oran={ratio:.4f})"
        )
    else:
        fitted_eta_bos = eta_bos_initial

    # 12. Final model çıktısı tüm dönem için (gece saatleri dahil)
    poa_all = poa
    t_air_all = t_air
    actual_all = actual

    valid_all = poa_all >= threshold
    t_cell_all = cell_temperature_noct(poa_all[valid_all], t_air_all[valid_all], plant.noct)
    params_final = BarhdadiBennisParams(c1=0.033, c2=-0.0092, gamma=plant.gamma_pdc)
    eta_rel_all = eta_rel_barhdadi_bennis(poa_all[valid_all], t_cell_all, params_final)
    eta_rel_all_bif = eta_rel_all * (1 + fitted_bg * plant.bifacial_factor * plant.albedo)
    p_model_all = plant.p_nom_kwp * (poa_all[valid_all] / G_STC) * eta_rel_all_bif * fitted_eta_bos

    # 13. Aylık özet
    full_model = pd.Series(0.0, index=poa.index)
    full_model.loc[p_model_all.index] = p_model_all

    monthly = (
        pd.DataFrame({"model": full_model, "actual": actual_all})
        .groupby(pd.Grouper(freq="ME"))
        .sum()
    )
    monthly["deviation_pct"] = (
        (monthly["model"] - monthly["actual"]) / monthly["actual"] * 100
    ).round(2)
    monthly_list = [
        {
            "month": str(idx.strftime("%Y-%m")),
            "actual_mwh": round(row.actual / 1000, 2),
            "model_mwh": round(row.model / 1000, 2),
            "deviation_pct": float(row.deviation_pct) if not pd.isna(row.deviation_pct) else 0.0,
        }
        for idx, row in monthly.iterrows()
    ]

    yearly_actual = float(actual_all.sum())
    yearly_model = float(full_model.sum())
    deviation_pct = (yearly_model - yearly_actual) / yearly_actual * 100

    notes.append(
        f"Yıllık: gerçek={yearly_actual/1000:.1f} MWh, model={yearly_model/1000:.1f} MWh, "
        f"sapma=%{deviation_pct:+.2f}"
    )

    # 14. Calibrated plant
    from dataclasses import replace

    calibrated = replace(
        plant,
        bifacial_gain_geometric=fitted_bg,
        eta_bos=fitted_eta_bos,
    )

    return ScadaCalibrationResponse(
        original_plant=PlantSpecSchema.from_dataclass(plant),
        calibrated_plant=PlantSpecSchema.from_dataclass(calibrated),
        bg=fitted_bg,
        eta_bos=fitted_eta_bos,
        yearly_bifacial_gain_pct=round(yearly_bifacial_pct, 2),
        yearly_actual_mwh=round(yearly_actual / 1000, 2),
        yearly_model_mwh=round(yearly_model / 1000, 2),
        deviation_pct=round(deviation_pct, 2),
        n_valid_hours=n_physical,
        monthly_breakdown=monthly_list,
        notes=notes,
    )
