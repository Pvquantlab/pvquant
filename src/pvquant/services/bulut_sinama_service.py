"""09.11.2026 v2.547 (P4b-3) — inverter bulutu BAĞLANTI SINAMASI (sahibin tetiklediği, yalnız okuma).
v2.548 (H1): «kapandi» işaretli sağlayıcı sınanmaz → saglayici_kapandi. v2.562 (K3/K4): sicildeki her etkin bağlayıcı için tek akış — giris(kimlik) + santraller().

Anahtar/şifre SAKLANMAZ: istek gövdesiyle gelir, sınama süresince bellekte tutulur, sonuçla birlikte yazılmaz; denetim izine yalnız sağlayıcı ve durum düşer.
Saklama ayrı adımdır (bulut_kimlik_service, iki onayla, zarf şifreli).
Sonuçlar: ok (giriş + santral listesi okundu) · kimlik_hatasi · saglayici_kapandi · saglayici_desteklenmiyor · ayar_hatasi · baglanti_hatasi · onay_yok.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pvquant.io.bulut import AKTIF_SAGLAYICILAR, SAGLAYICILAR


def kimlik_etiketi(kod: str, alan: str) -> str:
    return (SAGLAYICILAR.get(kod, {}).get("kimlik_etiketleri") or {}).get(alan, alan)


def sina(saglayici: str, kimlik: dict, onay: bool, bolge: str | None = None, transport=None) -> dict:
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not onay:
        return {"durum": "onay_yok", "zaman": simdi, "aciklama": "Yalnızca veri okuma izni onayı işaretlenmeden bağlantı sınanmaz."}
    kod = (saglayici or "").strip().lower()
    if kod in SAGLAYICILAR and kod not in AKTIF_SAGLAYICILAR:
        return {"durum": "saglayici_kapandi", "zaman": simdi, "aciklama": SAGLAYICILAR[kod]["not"]}
    sg = AKTIF_SAGLAYICILAR.get(kod)
    if not sg:
        return {"durum": "saglayici_desteklenmiyor", "zaman": simdi, "aciklama": f"Bu sağlayıcı için bağlantı henüz yok; sınanabilen: {', '.join(v['ad'] for v in AKTIF_SAGLAYICILAR.values())}."}
    eksik = [kimlik_etiketi(kod, a) for a in sg["kimlik_alanlari"] if not (kimlik or {}).get(a)]
    if eksik:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": f"Eksik kimlik alanı: {', '.join(eksik)}."}
    try:
        c = sg["sinif"](bolge or sg.get("varsayilan_bolge"), transport=transport)
        try:
            c.giris({a: kimlik[a] for a in sg["kimlik_alanlari"]})
            santraller = c.santraller()
        finally:
            c.kapat()
    except ValueError as e:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": str(e)}
    except Exception as e:   # noqa: BLE001 — sınıflandırma aşağıda; mesajda kimlik yok
        msg = str(e)
        if "kimlik" in msg or "(305)" in msg or "(401)" in msg or "geçersiz" in msg or "yetki" in msg:
            return {"durum": "kimlik_hatasi", "zaman": simdi, "aciklama": f"Kimlik doğrulanamadı: {msg}"}
        return {"durum": "baglanti_hatasi", "zaman": simdi, "aciklama": f"Sağlayıcıya ulaşılamadı ya da yanıt okunamadı ({type(e).__name__}: {msg})."}
    ilk = santraller[0] if santraller else None
    return {"durum": "ok", "zaman": simdi, "saglayici": kod,
            "ozet": {"santral_sayisi": len(santraller), "ilk_santral": (ilk or {}).get("ad"), "ilk_kapasite_kwp": (ilk or {}).get("kapasite_kwp"), "saat_dilimi": (ilk or {}).get("saat_dilimi"),
                     "uc": (ilk or {}).get("uc"),
                     "santraller": [{"kimlik": x.get("kimlik"), "ad": x.get("ad"), "kapasite_kwp": x.get("kapasite_kwp")} for x in santraller[:100]]},   # v2.556 (K1): kimlik saklarken santral seçimi
            "not": "Yalnızca okuma sınaması: giriş yapıldı ve santral listesi okundu; anahtar saklanmadı. Düzenli çekiş için kimlik ayrıca, iki onayla şifreli saklanır."}
