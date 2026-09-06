"""v2.281 — Tablo 3.3 satır 4: PVsyst tarzı kayıp ağacı (rapor dili) — tipik yıl ışınımından şebekeye adım adım.

Işınım: PVGIS-SARAH3 son tam yılı (2023) saatlik; transpozisyon/IAM/ışınım seviyesi/sıcaklık adımları saatlikten hesaplanır
(pvquant.ext.standart.kayip_agaci); kirlenme/kar santral ayarından, kırpma ve kısıntı son 30 günün hijyen özetinden,
kullanılabilirlik otomatik tespitten; gölge/uyumsuzluk/kablo/evirici PVsyst tipik varsayılan — her satır kaynağını söyler
(hesaplanan | ayar | ölçüm | varsayılan). Sonuç params_json.kayip_agaci'nda saklanır (ayda bir; panelden yenile).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

VARSAYILAN = {"golge": 0.01, "modul_kalitesi": 0.01, "uyumsuzluk": 0.01, "dc_kablo": 0.01, "inverter": 0.02, "ac_kablo": 0.01}


def agac_hesapla(df: pd.DataFrame, plant: dict, oranlar_ek: dict, kaynaklar: dict, sebeke_kwh: float | None = None) -> dict:
    """SAF (pvlib hesabı). df: saatlik UTC ghi/dni/dhi/temp_air/wind_speed_10m. oranlar_ek: adım→oran (ayar/ölçüm)."""
    from pvquant.ext.standart import kayip_agaci as ka
    from pvquant.services.calib_service import _plant_spec
    spec = _plant_spec(plant)
    gamma = float(getattr(spec, "effective_gamma", None) or getattr(spec, "gamma_pdc", None) or -0.0035)
    iam_b = 0.05 if getattr(spec, "iam_model", "none") != "none" else 0.0
    oranlar, ghi, poa = ka.oranlari_saatlikten(df["ghi"], df["dni"], df["dhi"], df["temp_air"], df["wind_speed_10m"], float(plant["lat"]), float(plant["lon"]),
                                              float(plant.get("tilt") or 20), float(plant.get("azimuth") or 180), gamma=gamma, iam_b=iam_b, **{**VARSAYILAN, **oranlar_ek})
    if iam_b == 0.0:
        oranlar["iam"] = 0.0
    kap = float(plant["capacity_kwp"])
    son = ka.agac(ghi, poa, alan_m2=kap, eta_stc=1.0, oranlar=oranlar, sebeke_kwh=sebeke_kwh)
    kaynak = {"transpozisyon": "hesaplanan", "iam": ("hesaplanan" if iam_b else "kapalı (ayar)"), "isinim_seviyesi": "hesaplanan", "sicaklik": "hesaplanan",
              **{k: "varsayılan" for k in VARSAYILAN}, **kaynaklar}
    satirlar = [{"adim": r["adim"], "etiket": r["etiket"], "giren_kwh": round(float(r["giren"]), 0), "cikan_kwh": round(float(r["cikan"]), 0),
                 "kayip_kwh": round(float(r["kayip_kwh"]), 0), "kayip_pct": round(float(r["kayip_pct"]), 2), "kaynak": kaynak.get(r["adim"], "—")}
                for _, r in son.tablo.iterrows()]
    return {"satirlar": satirlar, "ghi_kwh_m2": round(ghi, 1), "poa_kwh_m2": round(poa, 1), "nominal_dc_kwh": round(son.nominal_dc_kwh, 0),
            "sebeke_kwh": round(son.sebeke_kwh, 0), "pr": round(son.sebeke_kwh / son.nominal_dc_kwh, 3) if son.nominal_dc_kwh else None,
            "ozgul_kwh_kwp": round(son.sebeke_kwh / kap, 0)}


def hesapla(tenant_id, plant: dict, kaydet: bool = True) -> dict:
    from pvquant.io import arsiv_isinim
    from pvquant.services import hijyen_service, kullanilabilirlik_service
    from pvquant.services.calib_service import _pj
    df = arsiv_isinim.pvgis_df(float(plant["lat"]), float(plant["lon"]), arsiv_isinim.PVGIS_SON_YIL, arsiv_isinim.PVGIS_SON_YIL)
    if df.empty:
        return {"durum": "veri_yok"}
    pj = _pj(plant)
    ek, kay = {}, {}
    if pj.get("soiling_model") == "kimber":
        ek["soiling"] = min(0.15, float(pj.get("soiling_gunluk_kayip") or 0.0015) * 20); kay["soiling"] = "ayar (kirlenme modeli)"
    else:
        ek["soiling"] = 0.0; kay["soiling"] = "kapalı (ayar)"
    ek["spektral"] = 0.01 if pj.get("spectral_model") == "first_solar" else 0.0; kay["spektral"] = "ayar" if ek["spektral"] else "kapalı (ayar)"
    try:
        h = hijyen_service.ozet(tenant_id, plant["id"], 30)
        ek["kirpma"] = round(h["kirpma_saat"] / h["saat"] * 0.3, 4) if h.get("saat") else 0.0; kay["kirpma"] = "ölçüm (son 30 gün, kırpma saati payı×0,3)"
        ek["kisinti"] = 0.0; kay["kisinti"] = "ölçüm (kısıntı yok)" if not h.get("kisinti_saat") else "ölçüm"
        if h.get("kisinti_kayip_kwh") and h.get("beklenen_saat"):
            ek["kisinti"] = min(0.2, float(h["kisinti_kayip_kwh"]) / max(1.0, float(plant["capacity_kwp"]) * 5 * 30))
    except Exception:   # noqa: BLE001
        kay["kirpma"] = kay["kisinti"] = "hesaplanamadı"
    try:
        k = kullanilabilirlik_service.hesapla(tenant_id, plant, 30)
        if k.get("A_t") is not None:
            ek["kullanilabilirlik"] = round(1 - float(k["A_t"]), 4); kay["kullanilabilirlik"] = "ölçüm (otomatik tespit, 30 gün)"
    except Exception:   # noqa: BLE001
        pass
    out = {"durum": "ok", "hesap_zamani": datetime.now(timezone.utc).isoformat(), "yil": arsiv_isinim.PVGIS_SON_YIL,
           "kaynak": "PVGIS-SARAH3 (JRC), CC BY 4.0 — tipik yıl ışınımı", **agac_hesapla(df, plant, ek, kay)}
    if kaydet:
        from pvquant.services import plant_service
        plant_service.params_birlestir(tenant_id, plant["id"], kayip_agaci=json.loads(json.dumps(out)))
    return out
