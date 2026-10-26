"""24.10 Faz 1 — hız sınırlayıcı tek yerde (main ve yonetim yönlendiricisi paylaşır; dairesel import olmasın).
Anahtar: istemci IP'si — Faz 0'dan beri uvicorn --proxy-headers ile Caddy'nin ilettiği gerçek adres.

26.10 denetim-3: slowapi'nin bellek deposu SÜREÇ BAŞINA sayar; compose 4 uvicorn işçisi → «5/dk» fiilen ~20/dk/IP idi.
Giriş uçları artık ayrıca `paylasimli_sinir` ile hiz_pencere tablosunda (Faz 4) işçiler arası sayılır; slowapi katmanı
DB'ye ulaşılamadığında (pencere_say 0 döner, kapı açık kalır) süreç içi yedek olarak kalır."""
from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def paylasimli_sinir(request: Request, ad: str, limit: int, saniye: int = 60) -> None:
    """IP başına sabit pencere, DB'de paylaşımlı; aşılınca 429 (slowapi ile aynı kod ve gövde biçimi)."""
    from pvquant.services import kullanim_service
    ip = get_remote_address(request)
    if kullanim_service.pencere_say(f"{ad}:{ip}", saniye) > limit:
        raise HTTPException(429, f"Rate limit exceeded: {limit} per {saniye} second")
