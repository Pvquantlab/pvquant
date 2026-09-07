"""v2.283 — Tablo 3.3 satır 5: IEC 61853 güç matrisi ile modül davranışı.

Matris kaynağı: veri sayfası matrisi (params_json.guc_matrisi = {"G":[...],"T":[...],"P":[[satır=G]...]} , W/kWp)
varsa o; yoksa kalibre sıcaklık katsayısından sentetik IEC 61853-1 matrisi (pvquant.ext.standart.iec61853.matris_uret).
Matris ADR verim modeline uydurulur; tipik yıl (PVGIS-SARAH3 son yılı) düzlem ışınımı + hücre sıcaklığıyla
'iklim-özgü verim oranı' (CSER benzeri) ve ışınım/sıcaklık davranış tablosu üretilir. Sonuç params_json.guc_matrisi_sonuc
(aylık işte tazelenir; panelden 'Hesapla'). Model çekirdeğine DOKUNMAZ — sunum ve teşhis katmanı; düşük ışınım/sıcaklık
davranışı fizik zincirindeki ayarlarla (kt referansı, γ) tutarlı mı sorusuna görünürlük verir.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pvquant.ext.standart import iec61853 as gm

G_SEVIYE = [100, 200, 400, 600, 800, 1000]


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    return json.loads(pj) if isinstance(pj, str) else pj


def matris_getir(plant: dict) -> tuple[pd.DataFrame, dict, str, float]:
    """Döner (matris W/kWp, ADR parametreleri, kaynak metni, gamma)."""
    pj = _pj(plant)
    from pvquant.services.calib_service import _plant_spec
    gamma = float(getattr(_plant_spec(plant), "effective_gamma", None) or -0.0035)
    m = pj.get("guc_matrisi")
    if m and m.get("G") and m.get("T") and m.get("P"):
        M = pd.DataFrame(np.array(m["P"], float), index=[float(g) for g in m["G"]], columns=[float(t) for t in m["T"]])
        kaynak = "veri sayfası matrisi"
    else:
        M = gm.matris_uret(1000.0, gamma_p=gamma)   # W / kWp
        kaynak = "sentetik — kalibre sıcaklık katsayısından (veri sayfası matrisi girilirse onu kullanır)"
    adr = gm.matris_uydur(M, p_stc=1000.0)
    return M, adr, kaynak, gamma


def davranis_tablosu(adr: dict) -> list[dict]:
    """Işınım seviyesi başına verim oranı (η/η_STC, %) — 25 °C ve 50 °C hücre."""
    g = np.array(G_SEVIYE, float)
    e25 = gm.verim(g, np.full(len(g), 25.0), adr)
    e50 = gm.verim(g, np.full(len(g), 50.0), adr)
    return [{"g_wm2": int(gi), "verim_25_pct": round(float(a) * 100, 1), "verim_50_pct": round(float(b) * 100, 1)}
            for gi, a, b in zip(g, e25, e50)]


def hesapla(tenant_id, plant: dict, kaydet: bool = True) -> dict:
    from pvquant.io import arsiv_isinim
    from pvquant.ext.standart import kayip_agaci as ka
    df = arsiv_isinim.pvgis_df(float(plant["lat"]), float(plant["lon"]), arsiv_isinim.PVGIS_SON_YIL, arsiv_isinim.PVGIS_SON_YIL)
    if df is None or df.empty:
        return {"durum": "veri_yok", "not": "uydu türevli ışınım arşivi alınamadı"}
    M, adr, kaynak, gamma = matris_getir(plant)
    poa = ka.transpozisyon(df["ghi"], df["dni"], df["dhi"], float(plant["lat"]), float(plant["lon"]),
                           float(plant.get("tilt") or 20), float(plant.get("azimuth") or 180))
    t_cell = df["temp_air"].astype(float) + poa / (25.0 + 6.84 * df["wind_speed_10m"].astype(float).clip(lower=0.0))
    ed = gm.enerji_derecesi(poa, t_cell, adr, p_stc_kwp=1.0)
    tablo = davranis_tablosu(adr)
    e200 = next(x["verim_25_pct"] for x in tablo if x["g_wm2"] == 200)
    e1000_50 = next(x["verim_50_pct"] for x in tablo if x["g_wm2"] == 1000)
    out = {"durum": "ok", "hesap_zamani": datetime.now(timezone.utc).isoformat(), "kaynak": kaynak, "gamma": round(gamma, 5),
           "yil": arsiv_isinim.PVGIS_SON_YIL, "tablo": tablo,
           "cser": round(float(ed["CSER"]), 3) if np.isfinite(ed["CSER"]) else None,
           "e_dc_kwh_kwp": round(float(ed["E_dc_kwh_per_kwp"]), 0), "h_poa_kwh_m2": round(float(ed["H_poa_kwh_m2"]), 0),
           "dusuk_isinim_kayip_pct": round(100.0 - e200, 1), "sicaklik_50_kayip_pct": round(100.0 - e1000_50, 1),
           "not": "İklim-özgü verim oranı: tipik yılın düzlem ışınımı ve hücre sıcaklığında modülün STC'ye göre ürettiği pay. "
                  "Sentetik matris veri sayfası matrisinin yerini tutmaz; matris girildiğinde hesap onunla yenilenir."}
    if kaydet:
        from pvquant.services import plant_service
        plant_service.params_birlestir(tenant_id, plant["id"], guc_matrisi_sonuc=json.loads(json.dumps(out)))
    return out


def getir(plant: dict) -> dict | None:
    return _pj(plant).get("guc_matrisi_sonuc")
