"""24.10 Faz 1 — hız sınırlayıcı tek yerde (main ve yonetim yönlendiricisi paylaşır; dairesel import olmasın).
Anahtar: istemci IP'si — Faz 0'dan beri uvicorn --proxy-headers ile Caddy'nin ilettiği gerçek adres.

26.10 denetim-3: slowapi'nin bellek deposu SÜREÇ BAŞINA sayar; compose 4 uvicorn işçisi → «5/dk» fiilen ~20/dk/IP idi.
Giriş uçları artık ayrıca `paylasimli_sinir` ile hiz_pencere tablosunda (Faz 4) işçiler arası sayılır; slowapi katmanı
DB'ye ulaşılamadığında (pencere_say 0 döner) süreç içi yedek olarak kalır.

Faz 0 §24 #3 (21.11): paylaşımlı sayaç yazılamadığında (pencere_say == 0; başarı hiç 0 vermez) hesap ve IP pencereleri SÜREÇ İÇİ YEDEK
sayaçla sürer (aynı sabit pencere hizası, aynı limit; işçi başına → 4 işçide en çok 4× tolerans). Kapı kapanmaz (kalıcı yanlış
yapılandırma sahibi kilitlemesin), sayım durmaz; durum kullanim_service.sayac_durumu() ve sistem sağlığında.
Sınırlar (R3 QA itiraz 3): yedek sayımlar DB'ye taşınmaz (DB dönünce paylaşımlı sayaç sıfırdan sürer); dalgalı arızada iki bağımsız
sayaç → hesap tavanı 10 + 10×işçi'ye kadar gevşer (sürekli arızada 10×işçi); tam DB kesintisinde giriş 500 verir ve yedekteki +1 rezerv
geri alınamaz (DB dönene dek o işçide kalır); tavan aşımında en düşük adetli anahtarlar atılır (kilitli hesap anahtarı korunur).
`platform_sahip.py --kilit-ac` yalnız paylaşımlı sayacı siler — yedek sözlükteki kilit pencere sonunda (≤ 15 dk) kendiliğinden düşer."""
import threading
import time

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

YEDEK_AZAMI_ANAHTAR = 5000   # bellek tavani; asilirsa once suresi gecen pencereler, sonra en eski anahtar silinir
_YEDEK: dict[str, tuple[int, int]] = {}   # anahtar -> (pencere baslangici epoch, adet)
_YEDEK_KILIT = threading.Lock()


def _pencere_basi(saniye: int) -> int:
    e = int(time.time())
    return e - e % saniye   # kullanim_service.pencere_basi ile ayni hiza


def _yedek_say(anahtar: str, saniye: int) -> int:
    bas = _pencere_basi(saniye)
    with _YEDEK_KILIT:
        p, n = _YEDEK.get(anahtar, (bas, 0))
        n = n + 1 if p == bas else 1
        _YEDEK.pop(anahtar, None)
        _YEDEK[anahtar] = (bas, n)   # sona tasinir; en eski basta kalir
        if len(_YEDEK) > YEDEK_AZAMI_ANAHTAR:
            simdi = int(time.time())
            for k in [k for k, (p2, _) in _YEDEK.items() if simdi - p2 > 3600]:
                del _YEDEK[k]
            if len(_YEDEK) > YEDEK_AZAMI_ANAHTAR:   # R3 QA itiraz 2: en eski degil, EN DUSUK adetli anahtarlar atilir; kilitli hesap korunur
                for k in sorted(_YEDEK, key=lambda k: _YEDEK[k][1])[: len(_YEDEK) - YEDEK_AZAMI_ANAHTAR]:
                    if k != anahtar:
                        del _YEDEK[k]
        return n


def _yedek_azalt(anahtar: str, saniye: int) -> None:
    bas = _pencere_basi(saniye)
    with _YEDEK_KILIT:
        k = _YEDEK.get(anahtar)
        if k is not None and k[0] == bas and k[1] > 0:
            _YEDEK[anahtar] = (bas, k[1] - 1)


def yedek_sifirla() -> None:
    """Test/CLI: süreç içi yedek sayaç tablosunu boşaltır."""
    with _YEDEK_KILIT:
        _YEDEK.clear()


def _say(anahtar: str, saniye: int) -> tuple[int, bool]:
    """Paylaşımlı sayaç; 0 (arıza) → süreç içi yedek. Döner (adet, yedek_mi)."""
    from pvquant.services import kullanim_service
    n = kullanim_service.pencere_say(anahtar, saniye)
    return (n, False) if n > 0 else (_yedek_say(anahtar, saniye), True)


def hesap_siniri(ad: str, hesap: str, limit: int, saniye: int) -> None:
    """A3 (Faz 0, 21.11): IP'den bağımsız, HESAP başına sabit pencere (ör. platform girişi 10/15 dk) — dağıtık kaba kuvvet ve kurtarma kodu
    denemesine karşı. Hesap varlığı sızmaz: var olmayan e-posta da sayılır; aşımda aynı 429 gövdesi.
    R2 (§24, 21.11): yalnız BAŞARISIZ denemeler sayılır. QA itiraz 1 (yarış): deneme ATOMİK rezerve edilir (`pencere_say` +1); sınır aşıldıysa
    rezerv geri alınır ve 429; başarılı girişte (`hesap_basarili`) rezerv geri alınır → sayaçta yalnız başarısızlıklar kalır ve eş zamanlı
    denemeler tavanı aşamaz. Meşru başarılı girişler kilidi tetiklemez; kilit sunucuda `platform_sahip.py --kilit-ac` ile açılır
    (paylaşımlı sayaçta; sayaç arızasında süreç içi yedek kilidi yalnız pencere sonunda, ≤ 15 dk, düşer — R3 QA itiraz 5)."""
    from pvquant.services import kullanim_service
    anahtar = kullanim_service.hesap_anahtari(ad, hesap)
    n, yedek = _say(anahtar, saniye)
    if n > limit:
        (_yedek_azalt if yedek else kullanim_service.pencere_azalt)(anahtar, saniye)   # reddedilen deneme eklenmez (kilit uzamaz)
        raise HTTPException(429, f"Rate limit exceeded: {limit} per {saniye} second")


def hesap_basarili(ad: str, hesap: str, saniye: int) -> None:
    """R2: başarılı deneme (jeton ya da «kod bekleniyor») rezervi geri alır — yalnız başarısızlıklar sayaçta kalır."""
    from pvquant.services import kullanim_service
    anahtar = kullanim_service.hesap_anahtari(ad, hesap)
    kullanim_service.pencere_azalt(anahtar, saniye)
    _yedek_azalt(anahtar, saniye)   # rezerv yedekteyse orada geri alinir; yoksa no-op


def paylasimli_sinir(request: Request, ad: str, limit: int, saniye: int = 60) -> None:
    """IP başına sabit pencere, DB'de paylaşımlı; aşılınca 429 (slowapi ile aynı kod ve gövde biçimi)."""
    ip = get_remote_address(request)
    n, _yedek = _say(f"{ad}:{ip}", saniye)   # 24/#3: sayac arizasinda surec ici yedek; IP penceresi de kapisiz kalmaz
    if n > limit:
        raise HTTPException(429, f"Rate limit exceeded: {limit} per {saniye} second")
