"""API bagimlilik enjeksiyonu: token dogrulama + rol kontrolu."""
import os
import time
import uuid
from fastapi import Header, HTTPException, Depends, Request, Response
from pvquant.services import auth_service
from pvquant.services.auth_service import token_coz


# 26.10 denetim-2: GET olduğu hâlde yazan/sayan uçlar — kimliğe bürünme bunları da açamaz
TEMSIL_YASAK_GET_SONEKLERI = ("/report", "/scada/disa")   # 26.10 denetim-3: ham SCADA dışa aktarımı görüntüleme değildir
# 26.10 Faz 6: 2FA kurulmadan açık kalan müşteri uçları (kurulum, oturum tazeleme, kim olduğunu görme)
MUSTERI_KURULUM_YOLLARI = frozenset({"/v1/iki-adim", "/v1/iki-adim/baslat", "/v1/iki-adim/dogrula", "/v1/oturum/yenile", "/v1/hakkinda"})


def gecerli_kullanici(request: Request, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token gerekli")
    c = token_coz(authorization.removeprefix("Bearer ").strip())
    if c is None:
        raise HTTPException(401, "Gecersiz/suresi dolmus token")
    # 24.10 Faz 1: platform (PVQuant personeli) jetonu müşteri uçlarını AÇAMAZ — iki yüz, iki kapsam.
    if c.get("kapsam") == "platform":
        raise HTTPException(403, "platform jetonu müşteri ucunda geçersiz")
    # 26.10 Faz 5: KİMLİĞE BÜRÜNME jetonu (platform sahibi, müşteri gözüyle) — yalnız GET (salt okunur), rol viewer, 15 dk;
    # `sub` platform aktörüdür: aktiflik/sürüm platform tablosundan, kiracı durumu tenants'tan. Yazma kapıları ayrıca reddeder.
    if c.get("temsil"):
        from pvquant.services import platform_service
        if request.method != "GET" or request.url.path.endswith(TEMSIL_YASAK_GET_SONEKLERI):
            raise HTTPException(403, "görüntüleme oturumu salt okunur")   # rapor üretimi GET ama report_log'a yazar ve kullanım sayar
        d = platform_service.oturum_durumu(c["sub"])
        if d is None or not d["aktif"] or int(c.get("sv", 0)) != d["sv"]:
            raise HTTPException(401, "görüntüleme oturumu geçersiz")
        if platform_service.kiraci_durumu(c["tenant_id"]) != "active":
            raise HTTPException(403, "hesap askıda")
        return {**c, "role": "viewer"}
    # 24.10 Faz 0: imza yetmez — oturum sürümü, aktiflik ve kiracı durumu DB'den (60 sn önbellek) doğrulanır.
    # `sv` iddiası olmayan eski jeton 0 sayılır: sürümü hiç artmamış kullanıcıda geçerli kalır (geriye uyumlu).
    d = auth_service.oturum_durumu(c["sub"])
    if d is None or not d["aktif"]:
        raise HTTPException(401, "hesap etkin değil")
    if d["kiraci_durum"] != "active":
        raise HTTPException(403, "hesap askıda")
    if int(c.get("sv", 0)) != d["sv"]:
        raise HTTPException(401, "oturum geçersiz; yeniden giriş yapın")
    # 26.10 Faz 6 (O7): kiracı politikası «yöneticiler için 2FA zorunlu» açık ve yönetici 2FA'sız → yalnız kurulum uçları
    if d.get("iki_adim_kurulmali") and request.url.path not in MUSTERI_KURULUM_YOLLARI:
        raise HTTPException(403, "iki adımlı doğrulama zorunlu; önce kurun")
    return c  # {"sub","tenant_id","role","exp","sv"}


# 2FA kurulmadan açık kalan platform uçları: kim olduğunu görme, kurulum, parola, oturum tazeleme
PLATFORM_KURULUM_YOLLARI = frozenset({"/v1/yonetim/ben", "/v1/yonetim/iki-adim/baslat", "/v1/yonetim/iki-adim/dogrula",
                                      "/v1/yonetim/parola", "/v1/yonetim/oturum/yenile"})


PLATFORM_MUTLAK_SAAT = 12   # 25.10 O8: ilk girişten itibaren mutlak oturum sınırı (yenileme bunu uzatamaz)


def platform_yetkisi(rol: str | None = None):
    """24.10 Faz 1 — PLATFORM kapısı: yalnız `kapsam: platform` jetonu; platform_kullanicilar'dan aktiflik ve oturum
    sürümü (60 sn önbellek); `rol="sahip"` verilirse operatör 403. Müşteri jetonu burada 403: kapsamlar karışmaz."""
    def _ic(request: Request, authorization: str = Header(...)):
        from pvquant.services import platform_service
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer token gerekli")
        c = token_coz(authorization.removeprefix("Bearer ").strip())
        if c is None:
            raise HTTPException(401, "Gecersiz/suresi dolmus token")
        if c.get("kapsam") != "platform":
            raise HTTPException(403, "platform jetonu gerekli")
        d = platform_service.oturum_durumu(c["sub"])
        if d is None or not d["aktif"]:
            raise HTTPException(401, "hesap etkin değil")
        if int(c.get("sv", 0)) != d["sv"]:
            raise HTTPException(401, "oturum geçersiz; yeniden giriş yapın")
        if c.get("ilk") and time.time() - int(c["ilk"]) > PLATFORM_MUTLAK_SAAT * 3600:
            raise HTTPException(401, "oturum üst sınırı doldu; yeniden giriş yapın")   # 25.10 O8
        # 25.10 denetim Y2: 2FA kurulu değilse jeton YALNIZ kurulum uçlarını açar (arayüz zaten dayatıyordu; artık API de).
        # Durum DB'den (60 sn önbellek; kurulum/sıfırlama önbelleği düşürür) — jeton değişmez, açık oturumlar bozulmaz.
        if not d.get("totp_aktif", False) and request.url.path not in PLATFORM_KURULUM_YOLLARI:
            raise HTTPException(403, "iki adımlı doğrulama kurulumu gerekli")
        if rol == "sahip" and d["rol"] != "sahip":
            raise HTTPException(403, "sahip yetkisi gerekli")
        return {**c, "rol": d["rol"], "email": d["email"]}
    return _ic


def yonetici_yetkisi():
    """v2.264: yalnız admin (API anahtarı ve webhook yönetimi)."""
    def _ic(claims=Depends(gecerli_kullanici)):
        if claims.get("temsil"):
            raise HTTPException(403, "görüntüleme oturumu salt okunur")   # 26.10 denetim-2: rol viewer olsa da açıkça
        if claims["role"] != "admin":
            raise HTTPException(403, "admin gerekli")
        return claims
    return _ic


def api_anahtari(kapsam: str):
    """v2.264: dış API kapısı — X-API-Key başlığı; kapsam zorunlu. 401 (geçersiz), 403 (kapsam), 429 (oran).
    v2.609 (F6-E): anahtar doğrulandıktan sonra abonelik kapısı — `dis_api` modülü ve aylık dış API kotası (uyarı kipinde başlık + iz, zorla kipinde 403/409)."""
    def _ic(request: Request, response: Response, x_api_key: str = Header(..., alias="X-API-Key")):
        from pvquant.services import api_anahtar_service
        try:
            anahtar = api_anahtar_service.dogrula(x_api_key, kapsam)
        except PermissionError as e:
            raise HTTPException(403 if "kapsam" in str(e) else 401, str(e)) from None
        except RuntimeError:
            raise HTTPException(429, "oran siniri: dakikalik istek hakki doldu") from None
        abonelik_kapisi_uygula(request, response, anahtar["tenant_id"], _kapi_hukmu(anahtar["tenant_id"], modul="dis_api", alan="aylik_dis_api", artis=1),
                               kapsam="dis_api", nesne="dis_api", aktor_id=None)
        return anahtar
    return _ic


# ---------------------------------------------------------------- v2.609 (Faz 6 F6-E): abonelik kapıları ----------------------------------------
UYARI_IZI_SN = 3600
_uyari_izi: dict[tuple[str, str, str], float] = {}   # (kiracı, kod, nesne) → son iz zamanı; uyarı kipinde her istekte değil, saatte bir denetim satırı


def _kapi_hukmu(tenant_id, **kw):
    from pvquant.services import yetki_service
    try:
        uuid.UUID(str(tenant_id))
    except ValueError:    # UUID olmayan kiracı kimliği (eski testlerin sahte jetonu): kapı sessiz geçer
        return None
    try:
        return yetki_service.kapi_hukmu(tenant_id, **kw)
    except LookupError:   # kiracı kaydı yok (yarış/test): kapı sessiz geçer, diğer kapılar karar verir
        return None


def abonelik_kapisi_uygula(request: Request, response: Response, tenant_id, hukum: dict | None, *, kapsam: str = "musteri", nesne: str = "", aktor_id=None) -> None:
    """Hükmü kipe göre uygular. Uyarı kipi (varsayılan): yanıt başlığı `X-PVQuant-Abonelik: uyari` + `X-PVQuant-Abonelik-Kod` (bağımlılık yanıtı +
    main.py middleware'i `request.state.abonelik_uyari` ile — dosya/304 dönen uçlarda da) ve denetim izi
    `abonelik_uyari` (kiracı × kod × nesne başına saatte bir; süreç başına). Zorla kipi: HTTP 403/409, detail {kod, mesaj, …} (dış API gövdesi
    `{detail, kod}` istisna işleyicisinden). Kip `Settings.abonelik_zorlama`; «zorla» yalnız açık onayla (00 §13/1)."""
    if hukum is None:
        return
    from pvquant.services import denetim_service, yetki_service
    if yetki_service.zorlama_kipi() == "zorla":
        raise HTTPException(hukum["http"], {"detail": hukum["mesaj"], "mesaj": hukum["mesaj"], "kod": hukum["kod"], **hukum["ayrinti"]})
    response.headers["X-PVQuant-Abonelik"] = "uyari"
    response.headers["X-PVQuant-Abonelik-Kod"] = hukum["kod"]
    request.state.abonelik_uyari = hukum["kod"]   # öz inceleme: uç Response(...) döndürürse bağımlılık başlığı birleşmez → middleware state'ten yazar
    anahtar = (str(tenant_id), hukum["kod"], str(nesne))
    simdi = time.monotonic()
    if simdi - _uyari_izi.get(anahtar, -1e12) >= UYARI_IZI_SN:
        _uyari_izi[anahtar] = simdi
        denetim_service.kaydet(kapsam, "abonelik_uyari", aktor_id=aktor_id, tenant_id=tenant_id, nesne_tur="abonelik", nesne_id=None,
                               ayrinti={"kod": hukum["kod"], "mesaj": hukum["mesaj"], **hukum["ayrinti"], "yol": request.url.path, "yontem": request.method, "kip": "uyari"},
                               ip=request.client.host if request.client else None)


def modul_gerekli(modul: str, *, yazma: bool = False):
    """Uç bir modül ister: Depends(modul_gerekli("finansal_etki")). `yazma=True` ayrıca sona ermiş/kapalı abonelikte yazmayı keser (okuma serbest)."""
    def _ic(request: Request, response: Response, claims=Depends(gecerli_kullanici)):
        abonelik_kapisi_uygula(request, response, claims["tenant_id"], _kapi_hukmu(claims["tenant_id"], modul=modul, yazma=yazma), nesne=modul, aktor_id=claims.get("sub"))
        return claims
    return _ic


def kota_kontrol(alan: str, artis: int = 1):
    """Uç bir kota alanında yer ister (yazma): Depends(kota_kontrol("santral")). Tam sınır = yer yok; sınırsız/ölçülmeyen geçer."""
    def _ic(request: Request, response: Response, claims=Depends(gecerli_kullanici)):
        abonelik_kapisi_uygula(request, response, claims["tenant_id"], _kapi_hukmu(claims["tenant_id"], alan=alan, artis=artis, yazma=True), nesne=alan, aktor_id=claims.get("sub"))
        return claims
    return _ic


def yazma_yetkisi():
    """editor/admin isteyen endpoint'ler icin Depends(yazma_yetkisi())."""
    def _ic(claims=Depends(gecerli_kullanici)):
        if claims.get("temsil"):
            raise HTTPException(403, "görüntüleme oturumu salt okunur")   # 26.10 Faz 5
        if claims["role"] not in ("editor", "admin"):
            raise HTTPException(403, "editor/admin gerekli")
        return claims
    return _ic
