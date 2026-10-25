"""24.10 Faz 1 — PLATFORM YÖNETİMİ yönlendiricisi: /v1/yonetim/* (PVQuant personeli).

Kapsam ayrımı: her uç `platform_yetkisi()` ister (kapsam: platform jetonu); müşteri jetonu 403. Sahip-only uçlar
`platform_yetkisi("sahip")`. Her yazan uç denetim izine düşer (sır yazılmaz). Kiracı verisine erişim
platform_service üzerinden `platform_baglami(aktör)` ile — RLS dışı ama adlı ve izli.
Mevcut müşteri uçları ve sözleşmeleri DEĞİŞMEZ; bu dosya yalnız EKLER."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from apps.api.deps import platform_yetkisi
from apps.api.hiz import limiter
from pvquant.services import platform_service as ps, denetim_service as dz, basvuru_service, sistem_service as ss, kullanim_service as ks

yonetim = APIRouter(prefix="/v1/yonetim", tags=["Platform yönetimi"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _hata(e: Exception) -> HTTPException:
    return HTTPException(422, str(e))


# ---------------- kimlik ----------------
class YGiris(BaseModel):
    email: str
    sifre: str
    kod: str | None = None


@yonetim.post("/giris")
@limiter.limit("5/minute")
def giris(request: Request, g: YGiris):
    r = ps.giris(g.email, g.sifre, g.kod)
    if r is None:
        dz.kaydet("platform", "giris_basarisiz", aktor_eposta=(g.email or "").lower()[:255], ip=_ip(request))
        raise HTTPException(401, "hatali")
    if r.get("token"):
        dz.kaydet("platform", "giris", aktor_eposta=r["email"], ip=_ip(request))
    return r


@yonetim.post("/oturum/yenile")
def oturum_yenile(c=Depends(platform_yetkisi())):
    y = ps.oturum_yenile(c["sub"])
    if y is None:
        raise HTTPException(401, "hesap etkin değil")
    return y


@yonetim.get("/ben")
def ben(c=Depends(platform_yetkisi())):
    b = ps.ben(c["sub"])
    if b is None:
        raise HTTPException(404, "kullanıcı yok")
    return b


class Parola(BaseModel):
    eski: str
    yeni: str


@yonetim.post("/parola")
def parola(p: Parola, c=Depends(platform_yetkisi())):
    try:
        ps.parola_degistir(c["sub"], p.eski, p.yeni)
    except ValueError as e:
        raise _hata(e)
    return {"tamam": True}


class Kod(BaseModel):
    kod: str


@yonetim.post("/iki-adim/baslat")
def iki_adim_baslat(c=Depends(platform_yetkisi())):
    try:
        return ps.iki_adim_baslat(c["sub"])
    except ValueError as e:
        raise _hata(e)


@yonetim.post("/iki-adim/dogrula")
def iki_adim_dogrula(k: Kod, request: Request, c=Depends(platform_yetkisi())):
    try:
        ps.iki_adim_dogrula(c["sub"], k.kod)
    except ValueError as e:
        raise _hata(e)
    dz.kaydet("platform", "iki_adim_ac", aktor_id=c["sub"], aktor_eposta=c["email"], ip=_ip(request))
    return {"tamam": True}


# ---------------- operatörler (sahip) ----------------
class OperatorIstek(BaseModel):
    email: str
    rol: str = "operator"


class OperatorGuncelle(BaseModel):
    rol: str | None = None
    aktif: bool | None = None
    iki_adim_sifirla: bool = False


@yonetim.get("/operatorler")
def operatorler(c=Depends(platform_yetkisi("sahip"))):
    return {"operatorler": ps.operator_listesi(), "roller": list(ps.ROLLER)}


@yonetim.post("/operatorler", status_code=201)
def operator_ekle(p: OperatorIstek, request: Request, c=Depends(platform_yetkisi("sahip"))):
    """Geçici parola YALNIZ bu yanıtta."""
    try:
        y = ps.operator_ekle(p.email, p.rol)
    except ValueError as e:
        raise _hata(e)
    dz.kaydet("platform", "operator_ekle", aktor_id=c["sub"], aktor_eposta=c["email"], nesne_tur="platform_user", nesne_id=y["id"],
              ayrinti={"email": y["email"], "rol": y["rol"]}, ip=_ip(request))
    return y


@yonetim.put("/operatorler/{pid}")
def operator_guncelle(pid: str, p: OperatorGuncelle, request: Request, c=Depends(platform_yetkisi("sahip"))):
    try:
        if not ps.operator_guncelle(pid, rol=p.rol, aktif=p.aktif, iki_adim_sifirla=p.iki_adim_sifirla):
            raise HTTPException(404, "operatör yok")
    except ValueError as e:
        raise _hata(e)
    dz.kaydet("platform", "operator_guncelle", aktor_id=c["sub"], aktor_eposta=c["email"], nesne_tur="platform_user", nesne_id=pid,
              ayrinti=p.model_dump(), ip=_ip(request))
    return {"tamam": True}


# ---------------- kiracılar ----------------
class KiraciIstek(BaseModel):
    firma: str
    yonetici_eposta: str
    plan: str = "pilot"


class KiraciGuncelle(BaseModel):
    ad: str | None = None
    plan: str | None = None
    durum: str | None = None     # active | suspended
    notlar: str | None = None


@yonetim.get("/kiracilar")
def kiracilar(c=Depends(platform_yetkisi())):
    return {"kiracilar": ps.kiraci_listesi(c["sub"])}


@yonetim.post("/kiracilar", status_code=201)
def kiraci_olustur(p: KiraciIstek, request: Request, c=Depends(platform_yetkisi())):
    """Kiracı + ilk yönetici; parola rastgele, kimseye gösterilmez; 72 saatlik davet bağlantısı e-postalanır
    (posta yoksa bağlantı bir kez yanıtta — denetim izine yazılmaz)."""
    try:
        y = ps.kiraci_olustur(c["sub"], p.firma, p.yonetici_eposta, p.plan)
    except ValueError as e:
        raise _hata(e)
    dz.kaydet("platform", "kiraci_olustur", aktor_id=c["sub"], aktor_eposta=c["email"], tenant_id=y["tenant_id"],
              nesne_tur="tenant", nesne_id=y["tenant_id"],
              ayrinti={"firma": p.firma, "yonetici_eposta": p.yonetici_eposta.lower(), "plan": p.plan, "davet_gonderildi": y["davet_gonderildi"]},
              ip=_ip(request))
    return y


@yonetim.get("/kiracilar/{tid}")
def kiraci(tid: str, c=Depends(platform_yetkisi())):
    d = ps.kiraci_detay(c["sub"], tid)
    if d is None:
        raise HTTPException(404, "kiracı yok")
    return d


@yonetim.put("/kiracilar/{tid}")
def kiraci_guncelle(tid: str, p: KiraciGuncelle, request: Request, c=Depends(platform_yetkisi())):
    """Askıya alma (durum=suspended): kiracının tüm oturumları ≤60 sn içinde düşer, giriş 403 «hesap askıda»."""
    try:
        y = ps.kiraci_guncelle(c["sub"], tid, status=p.durum, plan=p.plan, ad=p.ad, notlar=p.notlar)
    except ValueError as e:
        raise _hata(e)
    if y is None:
        raise HTTPException(404, "kiracı yok")
    dz.kaydet("platform", "kiraci_guncelle", aktor_id=c["sub"], aktor_eposta=c["email"], tenant_id=tid, nesne_tur="tenant", nesne_id=tid,
              ayrinti={"eski": y["eski"], "yeni": y["yeni"], "notlar_degisti": p.notlar is not None}, ip=_ip(request))
    return {"tamam": True, **y}


# ---------------- kiracı kullanıcıları ----------------
class KullaniciGuncelle(BaseModel):
    aktif: bool | None = None
    rol: str | None = None


@yonetim.get("/kullanicilar")
def kullanicilar(q: str = "", limit: int = 100, c=Depends(platform_yetkisi())):
    return {"kullanicilar": ps.kullanici_ara(c["sub"], q, limit)}


@yonetim.put("/kullanicilar/{uid}")
def kullanici_guncelle(uid: str, p: KullaniciGuncelle, request: Request, c=Depends(platform_yetkisi())):
    """Mevcut kiracı kuralıyla (son etkin yönetici düşürülemez) — auth_service.kullanici_guncelle."""
    from pvquant.services import auth_service
    k = ps.kullanici_getir(c["sub"], uid)
    if k is None:
        raise HTTPException(404, "kullanıcı yok")
    try:
        auth_service.kullanici_guncelle(k["tenant_id"], uid, p.rol, p.aktif)
    except ValueError as e:
        raise _hata(e)
    dz.kaydet("platform", "kullanici_guncelle", aktor_id=c["sub"], aktor_eposta=c["email"], tenant_id=k["tenant_id"],
              nesne_tur="user", nesne_id=uid, ayrinti={"email": k["email"], "rol": p.rol, "aktif": p.aktif}, ip=_ip(request))
    return {"tamam": True}


@yonetim.post("/kullanicilar/{uid}/parola-sifirlama")
def kullanici_parola_sifirlama(uid: str, request: Request, c=Depends(platform_yetkisi())):
    """Destek: 24 saatlik parola belirleme bağlantısı e-postalanır (posta yoksa bağlantı bir kez yanıtta)."""
    y = ps.davet_gonder(c["sub"], uid, saat=24)
    if y is None:
        raise HTTPException(404, "kullanıcı yok ya da pasif")
    dz.kaydet("platform", "parola_sifirlama_gonder", aktor_id=c["sub"], aktor_eposta=c["email"], nesne_tur="user", nesne_id=uid,
              ayrinti={"gonderildi": y["gonderildi"]}, ip=_ip(request))
    return y


@yonetim.post("/kullanicilar/{uid}/iki-adim-sifirla")
def kullanici_iki_adim_sifirla(uid: str, request: Request, c=Depends(platform_yetkisi())):
    from pvquant.services import iki_adim_service
    k = ps.kullanici_getir(c["sub"], uid)
    if k is None or not iki_adim_service.yonetici_sifirla(k["tenant_id"], uid):
        raise HTTPException(404, "kullanıcı yok")
    dz.kaydet("platform", "iki_adim_sifirla", aktor_id=c["sub"], aktor_eposta=c["email"], tenant_id=k["tenant_id"],
              nesne_tur="user", nesne_id=uid, ip=_ip(request))
    return {"tamam": True}


# ---------------- vitrin başvuruları (platform) ----------------
@yonetim.get("/basvurular")
def basvurular(c=Depends(platform_yetkisi())):
    return {"basvurular": basvuru_service.listele()}


@yonetim.post("/basvurular/{bid}/okundu")
def basvuru_okundu(bid: str, request: Request, c=Depends(platform_yetkisi())):
    if not basvuru_service.okundu_isaretle(bid):
        raise HTTPException(404, "başvuru yok")
    dz.kaydet("platform", "basvuru_okundu", aktor_id=c["sub"], aktor_eposta=c["email"], nesne_tur="basvuru", nesne_id=bid, ip=_ip(request))
    return {"tamam": True}


# ---------------- denetim izi ----------------
@yonetim.get("/denetim")
def denetim(tenant_id: str | None = None, eylem: str | None = None, kapsam: str | None = None, limit: int = 100,
            once_id: int | None = None, c=Depends(platform_yetkisi())):
    return {"kayitlar": dz.listele(tenant_id=tenant_id, eylem=eylem, kapsam=kapsam, limit=limit, once_id=once_id)}


# ---------------- sistem izleme (25.10 Faz 3) ----------------
# Salt okunur uçlar: denetim izine yazılmaz (diğer GET'ler gibi). Hata ayrıntısı (jobs_log.detail) burada GÖRÜNÜR —
# müşteri /v1/isler'de bilerek yoktur; platform personeli zaten günlüğe bakacak kişidir.
@yonetim.get("/sistem")
def sistem(c=Depends(platform_yetkisi())):
    return ss.ozet(c["sub"])


@yonetim.get("/isler")
def isler(saat: int = 48, yalniz_hata: bool = False, job: str | None = None, tenant_id: str | None = None, limit: int = 200,
          c=Depends(platform_yetkisi())):
    return ss.isler(c["sub"], saat=saat, yalniz_hata=yalniz_hata, job=job or None, tenant_id=tenant_id or None, limit=limit)


@yonetim.get("/santraller")
def santraller(sorunlu: bool = False, c=Depends(platform_yetkisi())):
    return ss.santraller(c["sub"], sorunlu=sorunlu)


# ---------------- kullanım (25.10 Faz 4) ----------------
@yonetim.get("/kullanim")
def kullanim(ay: str | None = None, tenant_id: str | None = None, c=Depends(platform_yetkisi())):
    """Salt okunur: ay 'YYYY-MM' (boşsa bu ay). tenant_id verilirse o kiracının günlük kırılımı, yoksa tüm kiracıların ay özeti."""
    try:
        return ks.gunler(c["sub"], tenant_id, ay) if tenant_id else ks.ozet(c["sub"], ay)
    except ValueError as e:
        raise _hata(e)
