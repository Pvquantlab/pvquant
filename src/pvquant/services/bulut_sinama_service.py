"""09.11.2026 v2.547 (P4b-3) — inverter bulutu BAĞLANTI SINAMASI (sahibin tetiklediği, yalnız okuma).

Anahtar/şifre SAKLANMAZ: istek gövdesiyle gelir, sınama süresince bellekte tutulur, sonuçla birlikte yazılmaz; denetim izine yalnız sağlayıcı ve
durum düşer. Düzenli çekiş için kimlik bilgisinin saklanması gerekir — bu, ayrı bir karar (şifreli saklama) olmadan yapılmaz.
Sonuçlar: ok (giriş + santral listesi okundu) · kimlik_hatasi · saglayici_desteklenmiyor · ayar_hatasi · baglanti_hatasi · onay_yok.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pvquant.io.bulut import SAGLAYICILAR

KIMLIK_ETIKET = {"kullanici": "Northbound kullanıcı adı", "sistem_kodu": "systemCode", "api_anahtari": "API anahtarı"}


def sina(saglayici: str, kimlik: dict, onay: bool, bolge: str | None = None, transport=None) -> dict:
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not onay:
        return {"durum": "onay_yok", "zaman": simdi, "aciklama": "Yalnızca veri okuma izni onayı işaretlenmeden bağlantı sınanmaz."}
    sg = SAGLAYICILAR.get((saglayici or "").strip().lower())
    if not sg:
        return {"durum": "saglayici_desteklenmiyor", "zaman": simdi, "aciklama": f"Bu sağlayıcı için bağlayıcı henüz yok; desteklenen: {', '.join(v['ad'] for v in SAGLAYICILAR.values())}."}
    eksik = [KIMLIK_ETIKET[a] for a in sg["kimlik_alanlari"] if not (kimlik or {}).get(a)]
    if eksik:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": f"Eksik kimlik alanı: {', '.join(eksik)}."}
    try:
        if saglayici == "fusionsolar":
            from pvquant.io.bulut.fusionsolar import FusionSolarHata
            c = sg["sinif"](bolge or "intl", transport=transport)
            try:
                c.giris(kimlik["kullanici"], kimlik["sistem_kodu"])
                santraller = c.santraller()
            finally:
                c.kapat()
            hata_sinifi = FusionSolarHata
        else:
            from pvquant.io.bulut.solaredge import SolarEdgeHata
            c = sg["sinif"](kimlik["api_anahtari"], transport=transport)
            try:
                santraller = c.santraller()
            finally:
                c.kapat()
            hata_sinifi = SolarEdgeHata
    except ValueError as e:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": str(e)}
    except Exception as e:   # noqa: BLE001 — sınıflandırma aşağıda
        msg = str(e)
        if "kimlik" in msg or "403" in msg or "305" in msg:
            return {"durum": "kimlik_hatasi", "zaman": simdi, "aciklama": f"Kimlik doğrulanamadı: {msg}"}
        return {"durum": "baglanti_hatasi", "zaman": simdi, "aciklama": f"Sağlayıcıya ulaşılamadı ya da yanıt okunamadı ({type(e).__name__}: {msg})."}
    ilk = santraller[0] if santraller else None
    return {"durum": "ok", "zaman": simdi, "saglayici": saglayici,
            "ozet": {"santral_sayisi": len(santraller), "ilk_santral": (ilk or {}).get("ad"), "ilk_kapasite_kwp": (ilk or {}).get("kapasite_kwp"), "saat_dilimi": (ilk or {}).get("saat_dilimi")},
            "not": "Yalnızca okuma sınaması: giriş yapıldı ve santral listesi okundu; anahtar saklanmadı. Üretim verisi bu bağlantıdan henüz çekilmez."}
