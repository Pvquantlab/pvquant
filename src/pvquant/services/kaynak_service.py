"""v2.270 — Dalga 0: veri kaynakları ve lisans künyesi (Gizlilik Anayasası v2.245 istisnası).

Atıf yalnız üç yerde görünür: panel "Hakkında › Veri kaynakları ve lisanslar", rapor künye sayfası, README.
Liste GERÇEK kullanımı yansıtır: meteo ayarı, arşivde görülen kaynaklar, kalibrasyonların kaydettiği geçmiş
kaynağı, piyasa fiyatının kaynağı. Kullanılmayan kaynağa atıf yapılmaz; ticari kullanıma kapalı kaynak varsa uyarı.
"""
from __future__ import annotations

from pvquant.config import get_settings
from pvquant.ext.kaynak import atif

# Panel için okunur açıklama (ext not_ alanı README/teknik künye içindir; UI'da parametre adı geçmez)
ACIKLAMA = {
    "ecmwf": "Küresel sayısal hava tahmini; 0,25° ızgara, 15 gün ufuk, günde 2 koşu.",
    "icon": "Avrupa bölgesel modeli; ~7 km ızgara, 5 gün ufuk, günde 8 koşu; Türkiye alan içinde.",
    "gfs": "Küresel model (NOAA); 0,25° ızgara, 16 gün ufuk.",
    "cams": "Uydu türevli ışınım serisi; ~2 gün gecikme — kalibrasyon geçmişi.",
    "pvgis": "Uydu türevli ışınım arşivi 2005–2023 — iklim zarfı ve kalibrasyon geçmişi.",
    "era5": "Yeniden analiz arşivi; 0,25°, saatlik.",
    "nasa_power": "Kaba (1°) ışınım arşivi; yalnız eski dönem ve kıyas.",
    "epias": "Piyasa fiyatları (PTF/SMF) — dengesizlik hesabı.",
    "open_meteo": "Ücretsiz katman; ticari kullanıma kapalı.",
}
ARSIV_ETIKET = {"acik-nwp": "Açık NWP harmanı (ECMWF IFS + ICON-EU)"}

ESLEME = {"acik-nwp": ["ecmwf", "icon"], "cams": ["cams"], "pvgis-sarah3": ["pvgis"], "nasa-power": ["nasa_power"],
          "open-meteo": ["open_meteo"], "epias": ["epias"]}


def kullanilan_kaynaklar() -> list[str]:
    cfg = get_settings()
    k: list[str] = ["ecmwf", "icon", "pvgis"] if cfg.meteo_kaynak == "acik" else ["open_meteo"]
    try:
        from sqlalchemy import text
        from pvquant.db import sistem_baglami
        with sistem_baglami() as s:
            for (ad,) in s.execute(text("SELECT DISTINCT kaynak FROM meteo_arsiv")):
                k += ESLEME.get(ad, [])
            for (q,) in s.execute(text("SELECT DISTINCT quality_json->>'meteo_kaynak' FROM calibrations WHERE quality_json ? 'meteo_kaynak'")):
                k += ESLEME.get(q, [])
            if s.execute(text("SELECT 1 FROM piyasa_fiyat WHERE kaynak='epias' LIMIT 1")).first():
                k.append("epias")
    except Exception:   # noqa: BLE001 — DB yoksa (test/örnek kip) ayar listesi yeter
        pass
    sira = list(atif.KAYNAKLAR)
    return sorted(set(k), key=sira.index)


def hakkinda() -> dict:
    from pvquant.io import acik_nwp
    kull = kullanilan_kaynaklar()
    try:
        arsiv = acik_nwp.arsiv_durumu()
    except Exception:   # noqa: BLE001
        arsiv = {}
    return {
        "urun": "PVQuant", "meteo_kaynak": get_settings().meteo_kaynak,
        "kaynaklar": [{"kimlik": k, "ad": atif.KAYNAKLAR[k].ad, "kurum": atif.KAYNAKLAR[k].kurum, "lisans": atif.KAYNAKLAR[k].lisans,
                       "lisans_url": atif.KAYNAKLAR[k].lisans_url, "veri_url": atif.KAYNAKLAR[k].veri_url,
                       "not": ACIKLAMA.get(k, atif.KAYNAKLAR[k].not_)}
                      for k in kull],
        "kunye": atif.kunye(kull), "uyarilar": atif.uyumluluk_denetimi(kull),
        "arsiv": {ARSIV_ETIKET.get(k, k): v for k, v in arsiv.items()},
        "yontem": "Veriler PVQuant tarafından indirilmiş, birleştirilmiş ve işlenmiştir; kaynak kurumlar bu ürünü desteklemez ve sonuçlardan sorumlu değildir.",
    }


def rapor_kunye_satiri() -> str:
    """Rapor künye sayfası için tek satır (PDF/HTML): kaynak adları + lisans."""
    kull = [k for k in kullanilan_kaynaklar() if k != "epias"]
    return "Hava verisi: " + " · ".join(f"{atif.KAYNAKLAR[k].ad} ({atif.KAYNAKLAR[k].lisans})" for k in kull) + \
        " · Gerçekleşme: santral SCADA'sı · Fizik modeli: pvlib. Veriler PVQuant tarafından işlenmiştir; kaynaklar bu ürünü desteklemez."
