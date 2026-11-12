"""v2.602 (Faz 4 F4-H) — SANTRAL AYAR DAMGASI: hesap sonucunu etkileyen santral ayarlarının (params_json alt kümesi) içerik sha'sı.

Sonuç meta'ları (`finansal_etki_sonuc.meta_json.ayar_sha`) ve ayar değişikliği izleri (`denetim_izi.ayrinti.ayar_sha {eski, yeni}`) aynı damgayı
taşır; «bu ayar değişikliğinden hangi kayıtlı hesaplar etkilendi?» sorusu damga eşlemesiyle yanıtlanır (`denetim_service.etkilenen_sonuclar`).
Saf; formül yok. Anahtar kümesi: tarife, EAK/kısıt, KÜPST geçersiz kılma, pozisyon, segment/UEVÇB/DSG/toplayıcı, LÜY, sayaç/uzlaştırma girdisi,
EPİAŞ santral kimliği, lisans yıllık üretimi, depolama. Fizik terimleri ve alarm kuralları hesaba girmez (tahmin/alarm katmanı), damga dışıdır."""
from __future__ import annotations

import hashlib
import json

AYAR_ANAHTARLARI: tuple[str, ...] = (
    "tarife", "eak_kw", "eak_gecici", "kupst_n", "kupst_tolerans", "pozisyon_kaynagi", "pozisyon_sabit_mwh",
    "segment", "uevcb", "dsg_kodu", "toplayici_portfoyu", "piyasa_katilimcisi", "gts_toplayici_adi", "yek_g_kayitli", "lisans_yillik_uretim_mwh",
    "luy_istisna", "uzlastirma_girdi", "sayac_turu", "epias_santral_id", "dengeleme_birimi",
    "depolama_gucu_mw", "depolama_kapasite_mwh", "ariza_sayisi_ay",
)


def ayar_ozeti(params_json) -> dict:
    """Damgaya giren anahtarların mevcut değerleri (yoksa alan yok); iz ayrıntısında eski/yeni karşılaştırması için."""
    pj = params_json if isinstance(params_json, dict) else (json.loads(params_json) if params_json else {})
    return {k: pj[k] for k in AYAR_ANAHTARLARI if k in pj and pj[k] is not None}


def ayar_sha16(params_json) -> str:
    """Kanonik JSON (anahtar sıralı, ASCII dışı korunur) SHA-256'nın ilk 16 hex'i. Damga dışı anahtar değişince damga değişmez."""
    return hashlib.sha256(json.dumps(ayar_ozeti(params_json), sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:16]


def degisenler(eski, yeni) -> dict:
    """Damga anahtarlarında eski→yeni farkları: {alan: {"eski": …, "yeni": …}} (yalnız değişenler)."""
    e, y = ayar_ozeti(eski), ayar_ozeti(yeni)
    return {k: {"eski": e.get(k), "yeni": y.get(k)} for k in AYAR_ANAHTARLARI if e.get(k) != y.get(k)}
