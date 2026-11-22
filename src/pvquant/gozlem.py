"""Gözlem (Sentry) başlatıcısı — tek yer, sır sızdırmaz ayarlar (G1, 22.11.2026).

Neden: sentry-sdk 2.x varsayılanları istek gövdesini («medium» boyuta kadar) ve istisna anındaki yerel değişkenleri olaya ekler.
Giriş uçlarının alanları Türkçe (`sifre`, `kod`) olduğundan Sentry'nin İngilizce süzgeç listesi onları tanımaz; EPİAŞ CAS girişinde
kullanıcı adı/şifre yerel değişkendedir. Çevrimdışı deneyde (sahte taşıyıcı) ikisi de olaya düştü; bu ayarlarla düşmedi, hata türü ve
yığın izi korundu. API ve worker aynı başlatıcıyı çağırır; `PVQ_SENTRY_DSN` boşsa ya da sentry-sdk kurulu değilse sessizce geçer.
"""
from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode

# Sentry'nin varsayılan İngilizce listesine ek: Türkçe alan adları ve bu projeye özgü sır anahtarları — TAM anahtar eşleşmesi
# (büyük/küçük duyarsız). `kod` ve `email` bilerek yalnız tam eşleşmede: alt dize olsalardı `kodlama`, `email_dogrulandi` gibi
# sır olmayan alanlar da örtülürdü.
SIR_ANAHTARLARI: tuple[str, ...] = ("sifre", "parola", "kod", "kullanici", "tgt", "pw_hash", "kek", "totp", "kurtarma", "jeton", "anahtar", "x-api-key",
                                       "x-toplayici-anahtar", "x_toplayici_anahtar", "kullanici_adi", "username", "email", "eposta", "e_posta")

# QA İ-2 (22.11): Sentry EventScrubber anahtarı TAM eşler; `epias_sifre`, `yeni_sifre`, `sifre_tekrar`, `access_token` gibi bileşik
# anahtarlar açık kalırdı. Bu dar kök listesi ALT DİZE olarak eşlenir (fazla örtme güvenli taraftır).
SIR_KOKLERI: tuple[str, ...] = ("sifre", "parola", "password", "passwd", "secret", "token", "jeton", "tgt", "anahtar", "api_key",
                                  "apikey", "pw_hash", "totp", "kurtarma", "kek", "authorization", "cookie", "eposta", "e_posta", "e-posta")


def sirli_anahtar(anahtar: object, tam_liste: set[str] | list[str] | tuple[str, ...]) -> bool:
    """SAF: anahtar sır mı? Tam listede (küçük harf) ya da SIR_KOKLERI'nden birini alt dize olarak içeriyorsa evet."""
    if not isinstance(anahtar, str):
        return False
    k = anahtar.lower()
    return k in tam_liste or any(kok in k for kok in SIR_KOKLERI)


def _suzgec():
    """PVQuant süzgeci: Sentry EventScrubber + bileşik anahtar (alt dize) eşleşmesi + tags/contexts/query_string taraması.
    (QA İ-2/İ-3, 22.11: SDK 2.x tags, contexts ve sorgu dizesini hiç süzmez; kök sınıf yalnız request/extra/user/breadcrumbs/frames/spans.)"""
    from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber
    from sentry_sdk.utils import AnnotatedValue

    class PvqSuzgec(EventScrubber):
        def scrub_dict(self, d: object) -> None:
            if not isinstance(d, dict):
                return
            for k, v in d.items():
                if sirli_anahtar(k, self.denylist):
                    d[k] = AnnotatedValue.substituted_because_contains_sensitive_data()
                elif self.recursive:
                    self.scrub_dict(v)
                    self.scrub_list(v)

        def _sorgu_suz(self, sorgu: str) -> str:
            ciftler = [(k, "[Filtered]" if sirli_anahtar(k, self.denylist) else v)
                       for k, v in parse_qsl(sorgu, keep_blank_values=True)]
            return urlencode(ciftler)

        def scrub_breadcrumbs(self, event) -> None:
            super().scrub_breadcrumbs(event)
            # httpx/httplib kırıntıları giden isteğin sorgu dizesini `data["http.query"]`de ham tutar (22.11 test bulgusu).
            for kirinti in (event.get("breadcrumbs") or {}).get("values", []) or []:
                veri = kirinti.get("data") if isinstance(kirinti, dict) else None
                if isinstance(veri, dict) and isinstance(veri.get("http.query"), str) and veri["http.query"]:
                    veri["http.query"] = self._sorgu_suz(veri["http.query"])

        def scrub_event(self, event) -> None:
            super().scrub_event(event)
            for alan in ("tags", "contexts"):
                if isinstance(event.get(alan), dict):
                    self.scrub_dict(event[alan])
            istek = event.get("request")
            sorgu = istek.get("query_string") if isinstance(istek, dict) else None
            if isinstance(sorgu, str) and sorgu:
                istek["query_string"] = self._sorgu_suz(sorgu)

    return PvqSuzgec(denylist=list(DEFAULT_DENYLIST) + list(SIR_ANAHTARLARI), recursive=True)


def sentry_ayarlari(dsn: str) -> dict:
    """SAF: `sentry_sdk.init` için sözlük. Yerel değişken yok, istek gövdesi asla, PII yok, iz örnekleme kapalı, PVQuant sır süzgeci."""
    return {
        "dsn": dsn,
        "traces_sample_rate": 0,
        "include_local_variables": False,
        "max_request_body_size": "never",
        "send_default_pii": False,
        "event_scrubber": _suzgec(),
    }


def sentry_baslat(dsn: str | None = None) -> bool:
    """`PVQ_SENTRY_DSN` (ya da verilen dsn) varsa Sentry'yi sır sızdırmaz ayarlarla başlatır. Döner: başlatıldı mı.
    sentry-sdk kurulu değilse ya da DSN boşsa False (geliştirme ortamı; uygulama aynen açılır)."""
    dsn = (dsn if dsn is not None else os.environ.get("PVQ_SENTRY_DSN", "")) or ""
    if not dsn.strip():
        return False
    try:
        import sentry_sdk
    except ImportError:
        return False
    sentry_sdk.init(**sentry_ayarlari(dsn.strip()))
    return True
