"""v2.597 (Faz 4 F4-A, Stage 2): PlantSpec kurulumunun TEK noktası.

Eskiden dört kopya vardı: `calib_service._plant_spec` (santral satırı → PlantSpec), `forecast_service.uret_ve_kaydet`
(üstüne kalibre katsayılar), `scripts/dev_skill_backtest.py` (aynı katsayıları YANLIŞ yuvaya — bg'yi bifacial_factor'a —
yazıyordu) ve `fizik_service.onizle` (kalibrasyonsuz). Bundan sonra hepsi `plant_spec_kur(plant, kalibrasyon_params)`
çağırır; kalibre katsayıların PlantSpec'e nasıl işlendiği yalnız burada yazılıdır.

SAF: DB yok, ağ yok. Girdi santral satırı (dict ya da satır benzeri) + kalibrasyon params_json (dict / JSON metni / None).
"""
from __future__ import annotations

import json

from pvquant.pipeline.forecast import PlantSpec


def params_json(plant) -> dict:
    """plants.params_json — dict ya da JSON metni ya da None → dict (bozuk metin → {})."""
    pj = plant.get("params_json") if hasattr(plant, "get") else None
    if isinstance(pj, str):
        try:
            return json.loads(pj)
        except Exception:
            return {}
    return pj or {}


def _sozluk(params) -> dict:
    if params is None:
        return {}
    if isinstance(params, str):
        return json.loads(params)
    return dict(params)


def plant_spec_kur(plant, kalibrasyon_params=None) -> PlantSpec:
    """Santral satırı (+ aktif kalibrasyonun params_json'u) → PlantSpec.

    Kalibre katsayılar (v2.133 kuralı, değişmedi): `eta_bos` doğrudan BoS verimine; `bg` GEOMETRİK BG'dir →
    `bifacial_gain_geometric` (BF = bifaciality 0,7 panel teknolojisinden kurulur, kalibrasyon ona dokunmaz).
    Kalibrasyon yoksa ya da anahtar yoksa alan varsayılanında kalır."""
    pj = params_json(plant)
    spec = PlantSpec(
        p_nom_kwp=plant["capacity_kwp"], latitude=plant["lat"],
        longitude=plant["lon"], tilt=plant.get("tilt") or 20.0,
        azimuth=plant.get("azimuth") or 180.0,
        bifacial_factor=0.7 if plant.get("panel_tech") == "bifacial" else 0.0,
        # B-1 Adım 3: AC kırpma köprüsü (None = kırpma yok)
        p_ac_clip_kw=plant.get("ac_limit_kw"),
        # v2.255: santral params_json ile açılan fizik terimleri (varsayılan kapalı)
        iam_model=pj.get("iam_model") or "none",
        spectral_model=pj.get("spectral_model") or "none",
        # v2.256: kirlenme/kar — saha profili
        soiling_model=pj.get("soiling_model") or "none",
        soiling_gunluk_kayip=float(pj.get("soiling_gunluk_kayip") or 0.0015),
        soiling_temizleme_mm=float(pj.get("soiling_temizleme_mm") or 6.0),
        soiling_baslangic=float(pj.get("soiling_baslangic") or 0.0),
        kar_model=pj.get("kar_model") or "none",
        # v2.381: izleyici — params_json.izleyici = "tek_eksen" ile açılır
        izleyici=pj.get("izleyici") or "sabit",
        izleyici_max_aci=float(pj.get("izleyici_max_aci") or 60.0),
        izleyici_gcr=float(pj.get("izleyici_gcr") or 0.35),
        izleyici_capraz_egim=float(pj.get("izleyici_capraz_egim") or 0.0),
    )
    pr = _sozluk(kalibrasyon_params)
    if pr.get("eta_bos"):
        spec.eta_bos = pr["eta_bos"]
    if pr.get("bg") is not None:
        spec.bifacial_gain_geometric = pr["bg"]
    return spec
