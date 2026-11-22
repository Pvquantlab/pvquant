"""G1 (22.11.2026): Sentry olaylarına sır sızmaz — hedefli güvenlik testleri.

Kurgu: gerçek sentry-sdk, sahte taşıyıcı (ağ yok). `before_send` süzgeçten GEÇMİŞ olayı toplar ve None döndürür
(olay taşıyıcıya hiç gitmez). Sahte sırlar yalnız bu dosyada yaşar; gerçek hiçbir kimlik kullanılmaz.
Üç sızıntı yolu sınanır: istek gövdesi + Authorization/Cookie başlığı (giriş ucu), CAS 401 anındaki yerel
değişkenler (EPİAŞ kullanıcı/şifre/TGT), Türkçe anahtarlı extra/breadcrumb verisi. Her yolda hata türü, mesajı ve
yığın izinin KORUNDUĞU da doğrulanır (hata izleme işlevi kaybolmaz).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

sentry_sdk = pytest.importorskip("sentry_sdk")
from fastapi import FastAPI, Header  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sentry_sdk.client import NonRecordingClient  # noqa: E402
from sentry_sdk.transport import Transport  # noqa: E402

from pvquant.gozlem import (  # noqa: E402
    SIR_ANAHTARLARI,
    SIR_KOKLERI,
    sentry_ayarlari,
    sentry_baslat,
    sirli_anahtar,
)

KOK = Path(__file__).resolve().parents[1]
SAHTE_DSN = "https://sahteanahtar@o0.ingest.sentry.io/0"

# Sahte sırlar — rastgele biçim, gerçek hiçbir hesapla ilgisi yok.
PAROLA = "GIZLI-PAROLA-123"
KOD = "734519"
EPOSTA = "musteri.deneme@ornek-ges.com.tr"
EPIAS_KULLANICI = "epias-kullanici@ornek-ges.com.tr"
EPIAS_SIFRE = "EPIAS-GIZLI-SIFRE-9x"
TGT = "TGT-4f3a-cas-gizli-bilet"
JETON = "JETON-GIZLI-eyJhbGciOi"
CEREZ = "pvq_oturum=CEREZ-GIZLI-77"
SIRLAR = (PAROLA, KOD, EPOSTA, EPIAS_KULLANICI, EPIAS_SIFRE, TGT, JETON, "CEREZ-GIZLI-77")


class _AgsizTasiyici(Transport):
    """Hiçbir zarfı göndermez (ağ yok)."""

    def capture_envelope(self, envelope):
        return None


@pytest.fixture
def olaylar():
    """Sır sızdırmaz ayarlarla Sentry'yi başlatır; süzgeçten geçmiş olayları listeye toplar, hiçbirini göndermez."""
    toplanan: list[dict] = []

    def before_send(olay, _ipucu):
        toplanan.append(olay)
        return None  # taşıyıcıya gitmez

    ayar = sentry_ayarlari(SAHTE_DSN)
    ayar["before_send"] = before_send
    ayar["transport"] = _AgsizTasiyici()  # emniyet kemeri: before_send kaçırsa bile ağ yok
    sentry_sdk.init(**ayar)
    sentry_sdk.get_isolation_scope().clear()  # önceki testin tag/extra/kırıntıları taşınmasın (süzgeç yine de hepsini görür)
    try:
        yield toplanan
    finally:
        sentry_sdk.get_isolation_scope().clear()
        sentry_sdk.get_client().close(timeout=0)
        sentry_sdk.get_global_scope().set_client(NonRecordingClient())


def _dokum(olaylar: list[dict]) -> str:
    return json.dumps(olaylar, default=str, ensure_ascii=False)


def _sir_yok(olaylar: list[dict], sirlar: tuple[str, ...] = SIRLAR) -> None:
    dokum = _dokum(olaylar)
    sizan = {s: dokum[max(0, dokum.find(s) - 120):dokum.find(s)] for s in sirlar if s in dokum}
    assert not sizan, f"olaya sızan sahte sırlar (bağlam): {sizan}"


def _cerceveler(olay: dict) -> list[dict]:
    return olay["exception"]["values"][0]["stacktrace"]["frames"]


# ─── 1) Giriş ucu: istek gövdesi + Authorization/Cookie başlığı ──────────────────────────────────────────────────────

class Giris(BaseModel):  # modül düzeyinde: Python 3.14 tembel açıklamalarda yerel sınıf FastAPI'ce çözülemez (422)
    email: str
    sifre: str
    kod: str | None = None


def test_giris_govdesi_ve_basliklar_sizmaz_hata_izi_korunur(olaylar):
    app = FastAPI()

    @app.post("/v1/auth/login")
    def login(g: Giris, authorization: str | None = Header(default=None)):
        parola_yerel = g.sifre  # yerel değişken sızıntı yolu (include_local_variables)
        raise RuntimeError(f"giriş akışında beklenmeyen hata (uzunluk {len(parola_yerel)})")

    with TestClient(app, raise_server_exceptions=False) as ist:
        cevap = ist.post("/v1/auth/login", json={"email": EPOSTA, "sifre": PAROLA, "kod": KOD},
                         headers={"Authorization": f"Bearer {JETON}", "Cookie": CEREZ})
    assert cevap.status_code == 500, cevap.text
    assert len(olaylar) == 1, "tam bir hata olayı yakalanmalı (izleme korunur)"
    olay = olaylar[0]
    _sir_yok(olaylar)
    # İzleme korunur: tür, mesaj, yığın izi, istek bağlamı (URL/yöntem) yerinde.
    ist_ = olay["exception"]["values"][0]
    assert ist_["type"] == "RuntimeError" and "giriş akışında" in ist_["value"]
    assert any(c.get("function") == "login" for c in _cerceveler(olay))
    assert all("vars" not in c for c in _cerceveler(olay)), "yerel değişkenler olaya eklenmemeli"
    assert olay["request"]["method"] == "POST" and "/v1/auth/login" in olay["request"]["url"]
    # Gövde hiç aktarılmaz: SDK yerine boş değer + _meta «rem: !config» işareti koyar.
    assert olay["request"].get("data") in (None, ""), "istek gövdesi asla aktarılmamalı"
    assert olay["_meta"]["request"]["data"][""]["rem"][0][0] == "!config"
    basliklar = {k.lower(): v for k, v in olay["request"].get("headers", {}).items()}
    assert basliklar.get("authorization") in (None, "[Filtered]")
    assert basliklar.get("cookie") in (None, "[Filtered]")


# ─── 2) EPİAŞ CAS 401: yerel değişkenlerdeki kullanıcı/şifre/TGT ────────────────────────────────────────────────────

def _sahte_cas_girisi(kullanici: str, sifre: str, eski_tgt: str) -> str:
    """epias.tgt()'nin iskeleti: form gövdesi + 401 → HTTPStatusError. Yereller: kullanici, sifre, eski_tgt, veri, basliklar."""
    veri = {"username": kullanici, "password": sifre}
    basliklar = {"TGT": eski_tgt}
    istek = httpx.Request("POST", "https://giris.epias.com.tr/cas/v1/tickets", data=veri, headers=basliklar)
    cevap = httpx.Response(401, request=istek, text='{"error":"CAS hatası: kullanıcı adı ya da şifre hatalı"}')
    cevap.raise_for_status()
    return "ulaşılmaz"


def test_cas_401_yerel_degiskenler_sizmaz_hata_turu_korunur(olaylar):
    try:
        _sahte_cas_girisi(EPIAS_KULLANICI, EPIAS_SIFRE, TGT)
    except httpx.HTTPStatusError as e:
        sentry_sdk.capture_exception(e)
    sentry_sdk.flush(timeout=0)
    assert len(olaylar) == 1
    olay = olaylar[0]
    _sir_yok(olaylar)
    ist_ = olay["exception"]["values"][0]
    assert ist_["type"] == "HTTPStatusError" and "401" in ist_["value"]
    assert any(c.get("function") == "_sahte_cas_girisi" for c in _cerceveler(olay))
    assert all("vars" not in c for c in _cerceveler(olay))


# ─── 3) Türkçe anahtarlı extra / kullanıcı / breadcrumb verisi (özyinelemeli süzgeç) ────────────────────────────────

def test_turkce_anahtarlar_extra_ve_breadcrumbta_suzulur(olaylar):
    sentry_sdk.set_extra("epias_oturum", {"kullanici": EPIAS_KULLANICI, "sifre": EPIAS_SIFRE,
                                          "ic": {"tgt": TGT, "jeton": JETON, "guvenli": "kalir"}})
    sentry_sdk.set_user({"email": EPOSTA, "id": "u-1"})
    sentry_sdk.add_breadcrumb(category="auth", message="giriş denemesi", data={"kod": KOD, "parola": PAROLA, "adim": 2})
    sentry_sdk.capture_message("deneme olayı")
    sentry_sdk.flush(timeout=0)
    assert len(olaylar) == 1
    olay = olaylar[0]
    _sir_yok(olaylar)
    ek = olay["extra"]["epias_oturum"]
    assert ek["kullanici"] == "[Filtered]" and ek["sifre"] == "[Filtered]"
    assert ek["ic"]["tgt"] == "[Filtered]" and ek["ic"]["jeton"] == "[Filtered]" and ek["ic"]["guvenli"] == "kalir"
    kirinti = next(b for b in olay["breadcrumbs"]["values"] if b.get("category") == "auth")
    assert kirinti["data"]["kod"] == "[Filtered]" and kirinti["data"]["parola"] == "[Filtered]"
    assert kirinti["data"]["adim"] == 2 and kirinti["message"] == "giriş denemesi"  # süzgeç yalnız sır anahtarlarını örter
    assert olay["user"].get("id") == "u-1" and olay["user"].get("email") == "[Filtered]"  # kimlik no kalır, e-posta örtülür


# ─── 3b) QA İ-1/İ-2/İ-3 (22.11): toplayıcı başlığı, bileşik anahtarlar, tags/contexts/sorgu dizesi ───────────────────────

TOPLAYICI = "TOPLAYICI-GIZLI-ab12"


def test_toplayici_basligi_ve_sorgu_dizesi_suzulur(olaylar):
    app = FastAPI()

    @app.post("/v1/edge/ornekler")
    def ornekler(x_toplayici_anahtar: str = Header(..., alias="X-Toplayici-Anahtar")):
        raise RuntimeError("toplayıcı akışında hata")

    @app.get("/v1/auth/sifirla")
    def sifirla(jeton: str, sayfa: int = 1):
        raise RuntimeError("sıfırlama akışında hata")

    with TestClient(app, raise_server_exceptions=False) as ist:
        assert ist.post("/v1/edge/ornekler", headers={"X-Toplayici-Anahtar": TOPLAYICI, "X-API-Key": JETON}).status_code == 500
        assert ist.get("/v1/auth/sifirla", params={"jeton": JETON, "sayfa": 2}).status_code == 500
    assert len(olaylar) == 2
    dokum = _dokum(olaylar)
    assert TOPLAYICI not in dokum and JETON not in dokum
    basliklar = {k.lower(): v for k, v in olaylar[0]["request"]["headers"].items()}
    assert basliklar["x-toplayici-anahtar"] == "[Filtered]" and basliklar["x-api-key"] == "[Filtered]"
    assert olaylar[1]["request"]["query_string"] == "jeton=%5BFiltered%5D&sayfa=2"  # sır örtülür, sayfa kalır


def test_bilesik_anahtarlar_tags_ve_contexts_suzulur(olaylar):
    sentry_sdk.set_extra("ayar", {"epias_sifre": EPIAS_SIFRE, "yeni_sifre": PAROLA, "sifre_tekrar": PAROLA,
                                  "access_token": JETON, "kullanici_adi": EPIAS_KULLANICI, "kod_adi": "guneş", "kodlama": "utf-8",
                                  "email_dogrulandi": True, "santral_sayisi": 3})
    sentry_sdk.set_tag("tgt", TGT)
    sentry_sdk.set_tag("santral", "Deneme Lab")
    sentry_sdk.set_context("epias", {"kullanici": EPIAS_KULLANICI, "sifre": EPIAS_SIFRE, "ortam": "canli"})
    sentry_sdk.capture_message("deneme olayı 2")
    sentry_sdk.flush(timeout=0)
    assert len(olaylar) == 1
    olay = olaylar[0]
    _sir_yok(olaylar, (EPIAS_SIFRE, PAROLA, JETON, TGT, EPIAS_KULLANICI))
    ek = olay["extra"]["ayar"]
    assert all(ek[k] == "[Filtered]" for k in ("epias_sifre", "yeni_sifre", "sifre_tekrar", "access_token"))
    assert ek["kullanici_adi"] == "[Filtered]"  # tam listede: kullanıcı adı kimlik parçası («kullanici» kök değil: kullanici_id kalsın)
    assert ek["kod_adi"] == "guneş" and ek["kodlama"] == "utf-8" and ek["email_dogrulandi"] is True and ek["santral_sayisi"] == 3
    assert olay["tags"]["tgt"] == "[Filtered]" and olay["tags"]["santral"] == "Deneme Lab"
    assert olay["contexts"]["epias"]["kullanici"] == "[Filtered]" and olay["contexts"]["epias"]["sifre"] == "[Filtered]"
    assert olay["contexts"]["epias"]["ortam"] == "canli"


def test_giden_httpx_kirintisinda_sorgu_dizesi_suzulur(olaylar):
    """Bulgu (22.11 test sırası): httpx entegrasyonu giden isteğin sorgusunu kırıntı `data["http.query"]`de ham tutuyordu."""
    tasiyici = httpx.MockTransport(lambda istek: httpx.Response(200, json={"tamam": True}))
    with httpx.Client(transport=tasiyici) as ist:
        ist.get("https://seffaflik.ornek.test/v1/veri", params={"jeton": JETON, "gun": "2026-11-22"})
    sentry_sdk.capture_message("deneme olayı 3")
    sentry_sdk.flush(timeout=0)
    assert len(olaylar) == 1
    _sir_yok(olaylar, (JETON,))
    # Not: önceki testlerin TestClient kırıntıları da taşınabilir (kapsam temizliğine rağmen) → URL'ye göre seç; hepsi süzülmüş olmalı.
    kirintilar = [b for b in olaylar[0]["breadcrumbs"]["values"] if isinstance(b.get("data"), dict) and "http.query" in b["data"]]
    assert kirintilar, "httpx kırıntısı kaydedilmeli (izleme korunur)"
    assert all("jeton=%5BFiltered%5D" in b["data"]["http.query"] or "jeton" not in b["data"]["http.query"] for b in kirintilar)
    bizim = next(b for b in kirintilar if b["data"]["url"] == "https://seffaflik.ornek.test/v1/veri")
    assert bizim["data"]["http.query"] == "jeton=%5BFiltered%5D&gun=2026-11-22"


def test_sirli_anahtar_saf_kurali():
    tam = {k.lower() for k in SIR_ANAHTARLARI}
    assert all(sirli_anahtar(k, tam) for k in ("sifre", "Sifre", "epias_sifre", "yeni_parola", "ACCESS_TOKEN", "x-toplayici-anahtar",
                                               "kullanici", "kod", "email", "pw_hash"))
    assert not any(sirli_anahtar(k, tam) for k in ("kodlama", "kod_adi", "email_dogrulandi", "santral", "kurulu_guc_kw", 5, None))
    assert "kod" not in SIR_KOKLERI and "email" not in SIR_KOKLERI


# ─── 4) Başlatıcı sözleşmesi ve çağrı noktaları ────────────────────────────────────────────────────────────────────

def test_ayarlar_sir_sizdirmaz_sozlesmesi():
    a = sentry_ayarlari(SAHTE_DSN)
    assert a["include_local_variables"] is False
    assert a["max_request_body_size"] == "never"
    assert a["send_default_pii"] is False
    assert a["traces_sample_rate"] == 0
    liste = {k.lower() for k in a["event_scrubber"].denylist}
    assert type(a["event_scrubber"]).__name__ == "PvqSuzgec" and isinstance(a["event_scrubber"], __import__("sentry_sdk.scrubber", fromlist=["EventScrubber"]).EventScrubber)
    assert {"password", "secret", "authorization"} <= liste, "Sentry varsayılan listesi korunmalı"
    assert set(SIR_ANAHTARLARI) <= liste
    assert a["event_scrubber"].recursive is True


def test_dsn_bos_ya_da_sdk_yoksa_sessiz(monkeypatch):
    monkeypatch.delenv("PVQ_SENTRY_DSN", raising=False)
    assert sentry_baslat() is False
    monkeypatch.setenv("PVQ_SENTRY_DSN", "   ")
    assert sentry_baslat() is False
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)  # import → ImportError
    assert sentry_baslat(SAHTE_DSN) is False


def test_dsn_varsa_baslatir_ve_ayarlar_istemcide(monkeypatch):
    monkeypatch.setenv("PVQ_SENTRY_DSN", SAHTE_DSN)
    try:
        assert sentry_baslat() is True
        sec = sentry_sdk.get_client().options
        assert sec["include_local_variables"] is False and sec["max_request_body_size"] == "never"
        assert sec["send_default_pii"] is False and sec["traces_sample_rate"] == 0
    finally:
        sentry_sdk.get_client().close(timeout=0)
        sentry_sdk.get_global_scope().set_client(NonRecordingClient())


def test_api_ve_worker_yalniz_ortak_baslaticiyi_kullanir():
    """Pin: ham `sentry_sdk.init(` çağrısı apps/ altında geri gelmesin; iki servis de gozlem.sentry_baslat'ı çağırsın."""
    for yol in ("apps/api/main.py", "apps/worker/main.py"):
        metin = (KOK / yol).read_text(encoding="utf-8")
        assert "sentry_sdk.init(" not in metin, f"{yol}: ham Sentry başlatması yasak (G1)"
        assert "from pvquant.gozlem import sentry_baslat" in metin and "_sentry_baslat()" in metin
    kaynak = (KOK / "src").rglob("*.py")
    ham = [str(p.relative_to(KOK)) for p in kaynak if "sentry_sdk.init(" in p.read_text(encoding="utf-8") and p.name != "gozlem.py"]
    assert ham == [], f"gozlem.py dışında Sentry başlatması: {ham}"
