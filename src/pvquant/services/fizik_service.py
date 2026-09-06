"""v2.274 — Dalga 3 tamamlayıcısı (★): fizik terimlerini santral bazında AÇMA/KAPAMA + etki önizlemesi.

v2.255/v2.256 terimleri (geliş açısı kaybı, spektral düzeltme, kirlenme, kar örtüsü) boru hattında hazırdı ama yalnız
params_json'dan okunuyordu; panelden değiştirme yolu yoktu. Bu servis: doğrulanmış yazma (params_birlestir) ve
"açsam ne değişir?" önizlemesi — arşivdeki son koşunun meteosuyla salt-fizik hesabı, mevcut ↔ aday spec; 7 günlük
enerji farkı (%). Model çekirdeğine dokunmaz. McClear (CAMS) açık gök referansı DEĞERLENDİRİLDİ, alınmadı: yalnız geçmiş
için üretilir (≈2 gün gecikme), tahmin ufkunda yok → eğitim/servis kt tutarsızlığı; açık gök seçeneği Ineichen (ayar) kaldı.
"""
from __future__ import annotations

import pandas as pd

SECENEK = {
    "iam_model": ("none", "physical", "ashrae", "martin_ruiz"),
    "spectral_model": ("none", "first_solar"),
    "soiling_model": ("none", "kimber"),
    "kar_model": ("none", "nrel"),
}
SAYISAL = {"soiling_gunluk_kayip": (0.0, 0.02), "soiling_temizleme_mm": (0.5, 30.0), "soiling_baslangic": (0.0, 0.3)}
ETIKET = {"iam_model": "Geliş açısı kaybı", "spectral_model": "Spektral düzeltme", "soiling_model": "Kirlenme", "kar_model": "Kar örtüsü"}


def dogrula(ayar: dict) -> dict:
    """SAF. Bilinmeyen anahtar/değer → ValueError; yalnız izinli anahtarlar döner."""
    out = {}
    for k, v in (ayar or {}).items():
        if k in SECENEK:
            if v not in SECENEK[k]:
                raise ValueError(f"{ETIKET[k]}: geçersiz seçenek")
            out[k] = v
        elif k in SAYISAL:
            lo, hi = SAYISAL[k]
            try:
                f = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"{k}: sayı olmalı")
            if not (lo <= f <= hi):
                raise ValueError(f"{k}: {lo}–{hi} aralığında olmalı")
            out[k] = f
        else:
            raise ValueError(f"bilinmeyen alan: {k}")
    return out


def durum(plant: dict) -> dict:
    from pvquant.services.calib_service import _pj
    pj = _pj(plant)
    return {**{k: pj.get(k) or "none" for k in SECENEK}, **{k: pj.get(k) for k in SAYISAL},
            "secenekler": {k: list(v) for k, v in SECENEK.items()}, "etiket": ETIKET,
            "not": {"spectral_model": "nem verisi gerekir; meteoroloji kaynağında nem yoksa etkisizdir (uydurma yok)",
                    "soiling_model": "yağış verisiyle çalışır; günlük kayıp ve temizleme eşiği santrale göre ayarlanır",
                    "kar_model": "kar yağışı verisi gerekir; açık veri kaynağında kar alanı yoksa etkisizdir"}}


def ayar_yaz(tenant_id, plant_id, ayar: dict) -> dict:
    from pvquant.services import plant_service
    temiz = dogrula(ayar)
    pj = plant_service.params_birlestir(tenant_id, plant_id, **temiz)
    return durum({"params_json": pj})


def onizle(tenant_id, plant: dict, aday: dict, gun: int = 7) -> dict:
    """Arşivdeki son koşu meteosuyla salt fizik: mevcut spec ↔ aday spec; günlük kWh ve toplam fark."""
    from pvquant.io.meteo import OpenMeteoClient
    from pvquant.pipeline.forecast import forecast_7day
    from pvquant.services.calib_service import _pj, _plant_spec
    aday = dogrula(aday)
    meteo = OpenMeteoClient().get_forecast(latitude=plant["lat"], longitude=plant["lon"], days=gun)
    mevcut = _plant_spec(plant)
    aday_plant = dict(plant); aday_plant["params_json"] = {**_pj(plant), **aday}
    yeni = _plant_spec(aday_plant)
    tz = plant.get("tz") or "UTC"
    def gunluk(spec):
        h = forecast_7day(meteo, spec).hourly["p_ac_kw"]
        h = h.tz_convert(tz) if h.index.tz is not None else h.tz_localize("UTC").tz_convert(tz)
        return (h.resample("D").sum() / 1.0).round(1)
    a = gunluk(mevcut); b = gunluk(yeni)
    idx = a.index.intersection(b.index)
    ta, tb = float(a.loc[idx].sum()), float(b.loc[idx].sum())
    return {"gun": [{"tarih": d.date().isoformat(), "mevcut_kwh": float(a[d]), "aday_kwh": float(b[d]),
                     "fark_pct": round(100 * (b[d] - a[d]) / a[d], 2) if a[d] > 0 else None} for d in idx],
            "toplam_mevcut_kwh": round(ta, 1), "toplam_aday_kwh": round(tb, 1),
            "toplam_fark_pct": round(100 * (tb - ta) / ta, 2) if ta > 0 else None,
            "nem_var": meteo.relative_humidity is not None, "kar_var": meteo.snowfall is not None,
            "yagis_var": meteo.precipitation is not None, "kaynak": meteo.kaynak}
