"""24.10 Faz 1 — hız sınırlayıcı tek yerde (main ve yonetim yönlendiricisi paylaşır; dairesel import olmasın).
Anahtar: istemci IP'si — Faz 0'dan beri uvicorn --proxy-headers ile Caddy'nin ilettiği gerçek adres."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
