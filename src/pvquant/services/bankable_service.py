"""v2.278 — Tablo 3.1 satır 6: bankable yıllık beklenti (P50/P75/P90/P99) + belirsizlik bütçesi + TMY — ücretsiz veriyle.

Solargis/Meteonorm'un ücretli "bankable" katmanının açık veri muadili: PVGIS-SARAH3 (CC BY 4.0) 2005–2023 saatlik ışınım
→ her yıl için FİZİK boru hattı (santralin kalibre katsayılarıyla; hibrit/ML düzeltme yıllık ölçekte uygulanmaz, dürüstçe
söylenir) → yıllık kWh dağılımı → belirsizlik bütçesi (pvquant.ext.kaynak.belirsizlik: yıllar arası + kaynak + model +
ölçüm, kök-kare-toplam) → P-değerleri 1 yıl ve 10 yıl. TMY: ISO 15927-4 (FS) ile ay-yıl seçimi; P90 senaryo yılı.
Sonuç plants.params_json.bankable içinde saklanır (ayda bir worker; panelden 'yenile'). Ağır iş (~1–2 dk).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pvquant.ext.kaynak import belirsizlik as bz
from pvquant.ext.kaynak import tmy as tmy_mod

SIGMA_KAYNAK = 0.04   # uydu türevli GHI (SARAH-3) tipik kaynak belirsizliği
SIGMA_MODEL = 0.03    # fizik zinciri (transpozisyon + sıcaklık + sistem)


def _meteodata(df_yil: pd.DataFrame, lat: float, lon: float):
    from pvquant.io.meteo import MeteoData
    return MeteoData(ghi=df_yil["ghi"].astype(float), temp_air=df_yil["temp_air"].astype(float), wind_speed_10m=df_yil["wind_speed_10m"].astype(float),
                     relative_humidity=None, cloud_cover=None, latitude=lat, longitude=lon, timezone="UTC", kaynak="pvgis-sarah3", nwp_model="PVGIS-SARAH3 (JRC)")


def yillik_enerji(df: pd.DataFrame, plant: dict, spec, tam_yil_esik: float = 0.95) -> pd.DataFrame:
    """Her tam yıl için fizik koşusu → kWh ve GHI kWh/m². df: saatlik UTC (ghi/temp_air/wind_speed_10m)."""
    from pvquant.pipeline.forecast import forecast_7day
    rows = []
    for yil, g in df.groupby(df.index.year):
        if len(g) < tam_yil_esik * 8760:
            continue
        fr = forecast_7day(_meteodata(g, float(plant["lat"]), float(plant["lon"])), spec)
        kwh = float(fr.hourly["p_ac_kw"].clip(lower=0).sum())
        rows.append({"yil": int(yil), "kwh": round(kwh, 0), "ghi_kwh_m2": round(float(g["ghi"].sum()) / 1000.0, 1), "saat": int(len(g))})
    return pd.DataFrame(rows).set_index("yil") if rows else pd.DataFrame(columns=["kwh", "ghi_kwh_m2", "saat"])


def butce_uygula(yillik_kwh: pd.Series, capacity_kwp: float, sigma_kaynak: float = SIGMA_KAYNAK, sigma_model: float = SIGMA_MODEL,
                 sigma_olcum: float = 0.0, N_yil: int = 10) -> dict:
    """SAF. Yıllık kWh → P-değerleri (1 yıl / N yıl), özgül verim, bileşenler."""
    b = bz.butce(yillik_kwh, sigma_kaynak, sigma_model, sigma_olcum, N_yil)
    return {"p50_kwh": round(b.p50, 0), "ozgul_verim_kwh_kwp": round(b.p50 / capacity_kwp, 1),
            "sigma_toplam": round(b.sigma_goreli, 4), "bilesenler": {k: round(v, 4) for k, v in b.bilesenler.items()},
            "bir_yil": {f"p{p}": round(v, 0) for p, v in b.olasiliklar.items()},
            "n_yil": {f"p{p}": round(v, 0) for p, v in b.olasiliklar_N_yil.items()}, "N_yil": N_yil, "yil_sayisi": int(yillik_kwh.dropna().shape[0])}


def hesapla(tenant_id, plant: dict, kaydet: bool = True) -> dict:
    from pvquant.io import arsiv_isinim
    from pvquant.services.calib_service import _plant_spec
    df, ilk, son = arsiv_isinim.iklim_serisi(float(plant["lat"]), float(plant["lon"]), 20)
    if df is None or df.empty:
        return {"durum": "veri_yok", "not": "uydu türevli ışınım arşivi alınamadı"}
    spec = _plant_spec(plant)
    y = yillik_enerji(df, plant, spec)
    if len(y) < 5:
        return {"durum": "yetersiz", "yil_sayisi": int(len(y)), "not": "en az 5 tam yıl gerekir"}
    but = butce_uygula(y["kwh"], float(plant["capacity_kwp"]))
    ghi_b = bz.butce(y["ghi_kwh_m2"], SIGMA_KAYNAK, 0.0, 0.0, 10)
    try:
        tmy, secim = tmy_mod.tmy_uret(df[["ghi", "temp_air", "wind_speed_10m"]])
        p90_yil, p90_ghi, _ = tmy_mod.pxx_yili(df, 90)
        tmy_bilgi = {"secilen_yillar": {str(a): int(yy) for a, yy in secim.items()}, "p90_yili": p90_yil, "p90_yili_ghi": round(p90_ghi, 1),
                     "tmy_ghi_kwh_m2": round(float(tmy["ghi"].sum()) / 1000.0, 1)}
    except Exception as e:   # noqa: BLE001 — TMY başarısızlığı bütçeyi düşürmez
        tmy_bilgi = {"hata": f"{type(e).__name__}: {e}"}
    out = {"durum": "ok", "hesap_zamani": datetime.now(timezone.utc).isoformat(), "kaynak": "PVGIS-SARAH3 (JRC), CC BY 4.0",
           "donem": f"{int(y.index.min())}–{int(y.index.max())}", "mod": "fizik (kalibre katsayılar; hibrit düzeltme yıllık ölçekte uygulanmaz)",
           **but, "ghi": {"p50_kwh_m2": round(ghi_b.p50, 1), "p90_kwh_m2_1yil": round(ghi_b.olasiliklar[90], 1), "sigma_yillar_arasi": round(ghi_b.bilesenler["yillar_arasi"], 4)},
           "yillar": [{"yil": int(i), "kwh": float(r["kwh"]), "ghi_kwh_m2": float(r["ghi_kwh_m2"])} for i, r in y.iterrows()], "tmy": tmy_bilgi,
           "not": "Kaynak belirsizliği %4 ve model belirsizliği %3 varsayılan (uydu türevli GHI için tipik); ölçüm kalibresi olan sahada düşer. Ölçüm kalibreli finans raporu için bağımsız doğrulama gerekir."}
    try:   # v2.281: tarife tanımlıysa yıllık gelir P50/P90 (TL); PTF tipi için senaryo/EPİAŞ yıllık ortalama
        from pvquant.services import tarife_service, piyasa_service
        t = tarife_service.tarife_getir(plant)
        if t:
            ptf_ort = piyasa_service.SENARYO_PTF if t["tip"] == "ptf" else None
            f = tarife_service.ortalama_fiyat_tl_mwh(t, ptf_ort)
            if f:
                out["gelir"] = {"tip": t["tip"], "fiyat_tl_mwh": round(f, 1), "p50_tl": round(but["p50_kwh"] / 1000 * f, 0),
                                "p90_1yil_tl": round(but["bir_yil"]["p90"] / 1000 * f, 0), "p90_nyil_tl": round(but["n_yil"]["p90"] / 1000 * f, 0),
                                "not": "PTF tipi için senaryo yıllık ortalama; eskalasyon uygulanmadı" if t["tip"] == "ptf" else None}
    except Exception:   # noqa: BLE001
        pass
    if kaydet:
        from pvquant.services import plant_service
        plant_service.params_birlestir(tenant_id, plant["id"], bankable=json.loads(json.dumps(out)))
    return out


def getir(plant: dict) -> dict | None:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = json.loads(pj)
    return pj.get("bankable")
