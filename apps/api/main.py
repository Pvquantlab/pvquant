"""PVQuant API — ince katman: HTTP -> services -> HTTP."""
import os as _os

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import Response  # v2.261: /kgup CSV eki modül düzeyinde kullanır
from pydantic import BaseModel, Field

# v2.364: İTHALAT ISINDIRMASI — FastAPI'nin sync uçları iş parçacığı havuzunda
# koşar; ağır pipeline zinciri taze işçide İKİ istek tarafından aynı anda İLK
# KEZ tembel-import edilince Python "partially initialized module" /
# KeyError('pvquant.pipeline') yarışı doğuyordu (25 Eyl canlı: dağıtım sonrası
# /forecast ve /fizik-terimleri aralıklı 500 — panel "gelip gidiyor"). Zincir
# burada, açılışta tek iş parçacığıyla bir kez yüklenir; istekler hazır bulur.
import pvquant.pipeline.calibration  # noqa: F401,E402  (forecast+utils+validation zincirini kökten yükler)
from apps.api.deps import api_anahtari, gecerli_kullanici, yazma_yetkisi, yonetici_yetkisi
from pvquant.services import auth_service, plant_service
from pvquant.services.karne_kurali import (
    yayin_kosu_sql as _yayin_sql,  # v2.597 (F4-B): yayımlanmış koşu süzgeci
)
from pvquant.zaman import PIYASA_TZ

try:
    import sentry_sdk
    if _os.environ.get("PVQ_SENTRY_DSN"):
        sentry_sdk.init(dsn=_os.environ["PVQ_SENTRY_DSN"],
                        traces_sample_rate=0)
except ImportError:
    pass  # sentry-sdk kurulu değilse sessiz geç (dev ortamı)

app = FastAPI(title="PVQuant API", version="0.1",
              description="Panel uçları Bearer oturumla; **Dış API** uçları `X-API-Key` başlığıyla (yönetici panelden üretir). "
                          "Dış uçlar kapsam ister (tahmin:oku, kgup:oku), dakikalık oran sınırı uygular ve ETag/If-None-Match destekler.",
              openapi_tags=[{"name": "Dış API", "description": "Müşteri entegrasyonu: saatlik P10/P50/P90 tahmin ve KGÜP programı. "
                                                                "Kimlik: `X-API-Key: pvq_…`. Değişmemişse 304."},
                            {"name": "Yönetim", "description": "API anahtarları ve webhook alıcıları (yalnız admin)."}])

# v2.73-B: dev SPA (vite, :5173) tarayici kapisi. Prod'da SPA ayni alan
# adindan (Caddy /v1) sunulur — oraya CORS gerekmez; liste env ile dar tutulur.
from fastapi import Header as _Header  # v2.561: toplayıcı anahtarı başlığı
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=_os.environ.get(
        "PVQ_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],   # v2.264: PUT (segment) + DELETE (anahtar/webhook); v2.557: PATCH (bulut çekiş ayarı)
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    # v2.94: rapor dosya adi — tarayici bu basligi ancak expose ile gorur
    expose_headers=["Content-Disposition"])

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from apps.api.hiz import (  # 24.10 Faz 1: yonetim yönlendiricisiyle paylaşılır
    limiter,
    paylasimli_sinir,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 24.10 Faz 1: platform yönetimi (/v1/yonetim/*) — ayrı kapsam, ayrı yönlendirici
from apps.api.yonetim import yonetim as _yonetim  # noqa: E402
from pvquant.services import denetim_service as _denetim  # noqa: E402


def _ayar_izi(eylem: str, claims: dict, plant_id, eski_pj, yeni_pj, ek: dict | None = None) -> None:
    """v2.602 (F4-H): santral ayarı değişikliği izi — {degisen: {alan: {eski, yeni}}, ayar_sha: {eski, yeni}} standardı; iz, kapı değildir."""
    _denetim.ayar_degisikligi_kaydet(eylem, aktor_id=claims.get("sub"), tenant_id=claims["tenant_id"], plant_id=str(plant_id), eski_pj=eski_pj or {}, yeni_pj=yeni_pj or {}, ek=ek)


# ---------------------------------------------------------------- v2.603 (F4-I): dış API sözleşmesi ---------------------------------------------
DIS_API_SEMA = "2026-11-12"   # dış API şema sürümü: her /v1/dis yanıtında X-PVQuant-Schema başlığı; yeni uçların gövdesinde schema_version
_DIS_HATA_KODU = {400: "istek_gecersiz", 401: "anahtar_gecersiz", 403: "kapsam_yetersiz", 404: "bulunamadi", 409: "kosu_yok", 413: "dosya_buyuk",
                  422: "istek_gecersiz", 429: "oran_siniri", 500: "sunucu_hatasi", 503: "hizmet_disi"}


def _dis_hata(durum: int, kod: str, mesaj: str) -> HTTPException:
    """Dış API hata gövdesi {detail, kod, schema_version} (istisna işleyicisi kodu okur)."""
    return HTTPException(durum, {"detail": mesaj, "kod": kod})


def _dis_santral(anahtar: dict, plant_id: str) -> dict:
    """Dış API santral çözümleyici: kiracıda yoksa 404 `santral_yok`; anahtarın santral kapsamı (plant_ids) dışındaysa 403 `santral_kapsam_disi`."""
    from pvquant.services import api_anahtar_service
    row = plant_service.getir(anahtar["tenant_id"], plant_id)
    if row is None:
        raise _dis_hata(404, "santral_yok", "santral yok")
    if not api_anahtar_service.santral_izinli(anahtar, row["id"]):
        raise _dis_hata(403, "santral_kapsam_disi", "santral bu anahtarın kapsamında değil")
    return row


from fastapi.exception_handlers import http_exception_handler as _varsayilan_http_hata  # noqa: E402
from fastapi.exception_handlers import request_validation_exception_handler as _varsayilan_dogrulama_hata  # noqa: E402
from fastapi.exceptions import RequestValidationError as _DogrulamaHatasi  # noqa: E402
from starlette.exceptions import HTTPException as _StarletteHTTP  # noqa: E402


@app.exception_handler(_StarletteHTTP)
async def _dis_http_hata(request: Request, exc: _StarletteHTTP):
    """/v1/dis yolunda hata gövdesi {detail, kod, schema_version}; diğer yollar FastAPI varsayılanı (değişmez)."""
    if not request.url.path.startswith("/v1/dis"):
        return await _varsayilan_http_hata(request, exc)
    from fastapi.responses import JSONResponse
    d = exc.detail
    if isinstance(d, dict) and "kod" in d:
        govde = {"detail": d.get("detail"), "kod": d["kod"]}
    else:
        kod = _DIS_HATA_KODU.get(exc.status_code, "hata")
        if exc.status_code == 403 and isinstance(d, str) and "kapsam" not in d:
            kod = "yetki_yok"
        if exc.status_code == 409 and isinstance(d, str) and "koşu" not in d and "kosu" not in d:   # KGÜP «eksik saatler» gibi hesap çatışmaları
            kod = "hesaplanamadi"
        govde = {"detail": d, "kod": kod}
    return JSONResponse({**govde, "schema_version": DIS_API_SEMA}, status_code=exc.status_code, headers=dict(exc.headers or {}))


@app.exception_handler(_DogrulamaHatasi)
async def _dis_dogrulama_hata(request: Request, exc: _DogrulamaHatasi):
    if not request.url.path.startswith("/v1/dis"):
        return await _varsayilan_dogrulama_hata(request, exc)
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": "istek doğrulanamadı", "kod": "istek_gecersiz", "alanlar": [{"konum": list(e.get("loc", [])), "mesaj": e.get("msg")} for e in exc.errors()],
                         "schema_version": DIS_API_SEMA}, status_code=422)


@app.middleware("http")
async def _dis_sema_basligi(request: Request, call_next):
    yanit = await call_next(request)
    if request.url.path.startswith("/v1/dis"):
        yanit.headers["X-PVQuant-Schema"] = DIS_API_SEMA
    return yanit

app.include_router(_yonetim)


class GirisIstek(BaseModel):
    email: str
    sifre: str
    kod: str | None = None          # v2.338: iki adımlı doğrulama kodu (varsa)


@app.post("/v1/auth/login")
@limiter.limit("5/minute")
def login(request: Request, g: GirisIstek):
    paylasimli_sinir(request, "giris", 5, 60)   # 26.10 denetim-3: işçiler arası 5/dk/IP (slowapi süreç başınaydı)
    try:
        r = auth_service.giris(g.email, g.sifre, g.kod)
    except auth_service.KiraciAskida:
        raise HTTPException(403, "hesap askıda")   # 24.10 Faz 0: kiracı status != active
    if r is None:
        raise HTTPException(401, "hatali")
    # v2.338: parola doğru ama 2FA kodu gerekiyor — token YOK, istemci kod ister.
    # 200 döner (401 değil): "yanlış parola" ile "kod gerekli" ayrışsın.
    if r.get("token"):   # 24.10 Faz 1: başarılı giriş denetim izine (parola/jeton yazılmaz)
        _denetim.kaydet("musteri", "giris", aktor_id=r.get("user_id"), aktor_eposta=g.email.lower(),
                        tenant_id=r.get("tenant_id"), ip=request.client.host if request.client else None)
    return r


@app.get("/v1/plants")
def plants(claims=Depends(gecerli_kullanici)):
    return plant_service.listele(claims["tenant_id"])


class PlantIstek(BaseModel):
    name: str
    lat: float
    lon: float
    tz: str = PIYASA_TZ   # v2.599: tek tanım pvquant.zaman
    capacity_kwp: float
    tilt: float | None = None
    azimuth: float | None = None
    panel_tech: str = "bifacial"
    ac_limit_kw: float | None = None   # v2.302: kabuk formu AC tavanını da alır


@app.post("/v1/plants")
def plant_ekle(p: PlantIstek, claims=Depends(yazma_yetkisi())):
    if not (-90 <= p.lat <= 90 and -180 <= p.lon <= 180) or p.capacity_kwp <= 0:
        raise HTTPException(422, "konum ya da kurulu güç geçersiz")
    # v2.361: tz artık formdan gelebiliyor — çöp dilim tüm gün pencerelerini
    # sessizce bozardı; burada IANA adıyla doğrulanır.
    from zoneinfo import ZoneInfo
    try:
        ZoneInfo(p.tz)
    except Exception:
        raise HTTPException(422, "saat dilimi geçersiz (IANA adı bekleniyor, ör. Europe/Istanbul)")
    try:
        pid = plant_service.olustur(claims["tenant_id"], **p.model_dump())
    except ValueError as e:   # v2.302: yinelenen ad insan diliyle döner (500 değil)
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "santral_ekle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=pid,   # v2.602 (F4-H)
                    ayrinti={"ad": p.name, "capacity_kwp": p.capacity_kwp, "tz": p.tz})
    return {"id": pid}


@app.delete("/v1/plants/{plant_id}")
def plant_arsivle(plant_id: str, claims=Depends(yonetici_yetkisi())):
    """v2.303 — silmez, ARŞİVLER (v2.54 sözleşmesi): veri denetim için durur, santral listeden çekilir."""
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        r = plant_service.arsivle(claims["tenant_id"], plant_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not r["arsivlendi"]:
        raise HTTPException(404, "santral yok ya da zaten arşivde")
    _denetim.kaydet("musteri", "santral_arsivle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id)
    return r


@app.get("/v1/plants-arsiv")
def plant_arsiv_listesi(claims=Depends(yonetici_yetkisi())):
    return {"santraller": [{"id": str(x["id"]), "name": x["name"], "capacity_kwp": float(x["capacity_kwp"])}
                           for x in plant_service.arsivli_listele(claims["tenant_id"])]}


@app.post("/v1/plants/{plant_id}/geri-al")
def plant_geri_al(plant_id: str, claims=Depends(yonetici_yetkisi())):
    r = plant_service.geri_al(claims["tenant_id"], plant_id)
    if not r["geri_alindi"]:
        raise HTTPException(404, "arşivde böyle bir santral yok")
    _denetim.kaydet("musteri", "santral_geri_al", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id)
    return r


def _kw(x):
    """JSON NaN tasiyamaz — NaN/None -> null, sayi -> 3 hane (kW)."""
    import math
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), 3)


@app.get("/v1/plants/{plant_id}/forecast")
def forecast(plant_id: str, hours: int = 168,
             claims=Depends(gecerli_kullanici)):
    """v2.72 — son kosunun saatlik P10/P50/P90 serisi (ilk `hours` saat).

    Ince sargi: veri yolu forecast_service.son_kosu (tenant_baglami/RLS
    orada) + kosu_gecmisi(n=1) meta. Baska tenant'in santrali RLS'te
    bos doner -> 404; veri sizintisi yok. hours varsayilani 168 (7 gun,
    sartname); tavan 384 (16 gun ufku, v2.69).
    """
    from pvquant.services import forecast_service, gunes_service
    if not (1 <= hours <= 384):
        raise HTTPException(422, "hours 1-384 araliginda olmali")
    df = forecast_service.son_kosu(claims["tenant_id"], plant_id)
    if df is None:
        raise HTTPException(404, "tahmin kosusu yok")
    kosu = forecast_service.kosu_gecmisi(claims["tenant_id"], plant_id, n=1)
    df = df.iloc[:hours]
    # v2.203: pencerenin gunleri icin astronomik dogus/batis (pvlib SPA).
    # Hesap dusmezse seri OLMEZ — gunes bos doner, grafik isaretsiz cizer.
    try:
        gunes = gunes_service.dogus_batis(
            claims["tenant_id"], plant_id, df.index.min(), df.index.max())
    except Exception:
        gunes = []
    return {
        "plant_id": plant_id,
        "run_at": kosu[0].run_at.isoformat() if kosu else None,
        "mode": kosu[0].mode if kosu else None,
        # v2.605 (F4-K): tahmin etiketi (yayin | gun_ici | elle; eski kayıtta null) ve hava tahmini kaynaklarının üretim zamanları {kaynak: ISO}
        "etiket": (getattr(kosu[0], "etiket", None) if kosu else None),
        "nwp_kosu_zamani": (kosu[0].nwp_kosu_zamani.isoformat() if kosu and getattr(kosu[0], "nwp_kosu_zamani", None) else None),
        "nwp_bilesenler": (getattr(kosu[0], "nwp_bilesenler", None) if kosu else None),
        "hours": int(len(df)),
        "gunes": gunes,
        "series": [
            {"ts_utc": ts.isoformat(), "p10_kw": _kw(r.p10_kw),
             "p50_kw": _kw(r.p50_kw), "p90_kw": _kw(r.p90_kw),
             # v2.204: ic bant — eski kosuda/A-B'de null (durust bantsizlik)
             "p25_kw": _kw(getattr(r, "p25_kw", None)),
             "p75_kw": _kw(getattr(r, "p75_kw", None))}
            for ts, r in df.iterrows()
        ],
    }


class KunyeIstek(BaseModel):
    """v2.599 (F4-E): yeni künye sürümü; verilmeyen alanlar önceki sürümden taşınır."""
    gecerli_bas: str
    dc_kwp: float | None = None
    ac_kw: float | None = None
    eak_kw: float | None = None
    baglanti_turu: str | None = None
    gerilim_kv: float | None = None
    segment: str | None = None
    lisans_durumu: str | None = None
    uevcb_kod: str | None = None
    eic: str | None = None
    epias_santral_id: str | None = None
    sayac_kimligi: str | None = None
    olcum_siniri: str | None = None
    kaynak: str = "beyan"
    dogrulama: str = "beyan"
    belge_adi: str | None = None
    notlar: str | None = None


@app.get("/v1/plants/{plant_id}/kunye")
def santral_kunye(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.599 (F4-E): tarihli santral kimliği — bugün geçerli sürüm, tarihçe, güç tanımları (DC/AC/EAK kaynaklı), beyan uyarıları, sözlük."""
    from pvquant.services import santral_kunye_service as _sk
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    g = _sk.guncel(claims["tenant_id"], plant_id)
    return {"plant_id": plant_id, "guncel": g, "tarihce": _sk.tarihce(claims["tenant_id"], plant_id), "guc": _sk.guc_tanimlari(row, None, g),
            "uyarilar": _sk.beyan_uyarilari(claims["tenant_id"], row), "sozluk": _sk.sozluk()}


@app.post("/v1/plants/{plant_id}/kunye")
def santral_kunye_yeni(plant_id: str, p: KunyeIstek, claims=Depends(yazma_yetkisi())):
    """v2.599 (F4-E): yeni künye sürümü (eski sürüm kapanır; plants çift yazılır; denetim izi)."""
    from pvquant.services import santral_kunye_service as _sk
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    verilen = p.model_dump(exclude_unset=True)
    alanlar = {k: v for k, v in verilen.items() if k in _sk.ALANLAR}
    try:
        if _sk.guncel(claims["tenant_id"], plant_id) is None:
            _sk.ilk_surum(claims["tenant_id"], plant_id, dc_kwp=row["capacity_kwp"], ac_kw=row.get("ac_limit_kw"))
        g = _sk.yeni_surum(claims["tenant_id"], plant_id, gecerli_bas=p.gecerli_bas, aktor_id=claims["sub"], kaynak=p.kaynak, dogrulama=p.dogrulama,
                           belge_adi=p.belge_adi, notlar=p.notlar, **alanlar)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"guncel": g, "tarihce": _sk.tarihce(claims["tenant_id"], plant_id)}


@app.get("/v1/sozluk/durum")
def sozluk_durum(claims=Depends(gecerli_kullanici)):
    """v2.608 (Faz 5 F5-C): hizmet durumu sözlüğü — altı durum, sıra, eşikler. Genel bakış kartları ve hizmet sağlığı bu kodlarla konuşur."""
    from pvquant.services import durum_sozlugu
    return durum_sozlugu.sozluk()


@app.get("/v1/plants/{plant_id}/genel-bakis")
def genel_bakis(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.608 (Faz 5 F5-B): Genel bakış — dört iş sorusu, dört kart (bugün / yarının programı / açık riskler / finansal durum). Mevcut servisleri
    birleştirir, hesap yazmaz; her kartta durum sözlüğü kodu, dönem, tazelik, kapsam, eylem ve hedef sayfa. Değer yoksa null ve neden."""
    from pvquant.services import genel_bakis_service, plant_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return genel_bakis_service.ozet(claims["tenant_id"], {**row, "id": str(row["id"])})


@app.get("/v1/hizmet-sagligi")
def hizmet_sagligi(claims=Depends(gecerli_kullanici)):
    """v2.608 (Faz 5 F5-C): kiracının santralleri için hizmet sağlığı — veri, tahmin, program (KGÜP), mutabakat, alarm boyutları; kuruluş ve portföy
    toplamları. Teknik iş başarısından bağımsız (iş düşmüşken de, iş başarılıyken de yalnız kayıtların kendisine bakar). Hata ayrıntısı yok."""
    from pvquant.services import hizmet_sagligi_service
    return hizmet_sagligi_service.ozet(claims["tenant_id"])


@app.get("/v1/sozluk/kalite")
def sozluk_kalite(claims=Depends(gecerli_kullanici)):
    """v2.598 (Faz 4 F4-C): veri kalitesi sözlüğü — nitelikler, bayrak eşlemeleri, amaç başına geçerli küme, tazelik eşiği.
    Arayüz rozetleri ve dış API bu sözlükten okur; sürüm alanı değişince istemci etiketleri yeniler."""
    from pvquant.services import kalite_sozlugu
    return kalite_sozlugu.sozluk()


@app.get("/v1/plants/{plant_id}/tahmin-arsivi")
def tahmin_arsivi(plant_id: str, hedef: str, yayin_oncesi: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.597 (Faz 4 F4-B) arşiv sorgusu: `hedef` saati (ISO 8601, UTC yoksa UTC sayılır) için `yayin_oncesi` anında
    yayımlanmış olan son koşunun değeri ve koşu künyesi. «Yayımlandı» iddiası yalnız koşu zamanıyla (run_at ≤ yayin_oncesi);
    geriye bakışlı koşular (backtest, simülasyon, sentetik, demo, yeniden kurma) hiç dönmez. Yoksa 404."""
    import pandas as _pd

    from pvquant.services import forecast_service
    try:
        h = _pd.Timestamp(hedef)
        y = _pd.Timestamp(yayin_oncesi) if yayin_oncesi else None
    except (ValueError, TypeError):
        raise HTTPException(422, "hedef / yayin_oncesi ISO 8601 zaman olmalı") from None
    if _pd.isna(h) or (yayin_oncesi and _pd.isna(y)):
        raise HTTPException(422, "hedef / yayin_oncesi ISO 8601 zaman olmalı")
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    out = forecast_service.yayimlanmis_kosu(claims["tenant_id"], plant_id, h, y)
    if out is None:
        raise HTTPException(404, "bu saat için o anda yayımlanmış koşu yok")
    return {"plant_id": plant_id, **out}


def _tarih(x):
    """datetime/None -> ISO/None (JSON guvenli)."""
    return x.isoformat() if hasattr(x, "isoformat") else (x if x else None)


@app.get("/v1/plants/{plant_id}/summary")
def summary(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.74-A — Santralim'in tek servis sozlesmesi (Anayasa 8.4) API'de.

    Streamlit'in veri yolunun kopyasi: plant_service.getir -> santral dict
    -> gunun_ozeti -> aylik_uretim. Alan adlari GununOzeti + kunye ile
    birebir; olmayan/dolmayan alan null (icat yok, sahte deger yok).
    """
    from pvquant.services import kalite_sozlugu as _kalite   # v2.605 (F4-K)
    from pvquant.services import forecast_service, ingest_service, ozet_service, plant_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    # getir dict dondurur (canli durusma dersi: SimpleNamespace sahtesi
    # nitelik erisimiyle bu farki maskeledi — sahte, gercegin seklini tasir).
    santral = {
        "id": str(row["id"]), "name": row["name"],
        "capacity_kwp": float(row["capacity_kwp"]),
        "ac_limit_kw": float(row["ac_limit_kw"])
        if row.get("ac_limit_kw") is not None else None,
        "lat": row["lat"], "lon": row["lon"], "tz": row["tz"],
        "konum_metni": f"{row['lat']:.2f}, {row['lon']:.2f}",
    }
    o = ozet_service.gunun_ozeti(claims["tenant_id"], santral)
    ay = ingest_service.aylik_uretim(claims["tenant_id"], plant_id)
    # v2.205: aylik beklenti (forecast_daily) — servis/tablo dusmusse ozet
    # OLMEZ, beklenti alanlari null kalir (durust yokluk).
    try:
        bek = forecast_service.aylik_beklenti(claims["tenant_id"], plant_id)
    except Exception:
        bek = {}

    def _beklenti(ay_str):
        """Ay TAM kapsanmadan beklenti gosterilmez (kismi toplam yaniltir)."""
        import calendar
        b = bek.get(ay_str)
        if not b:
            return None
        y, m = int(ay_str[:4]), int(ay_str[5:7])
        return _kw(b["mwh"]) if b["gun_sayisi"] >= calendar.monthrange(y, m)[1] else None

    aylik = [] if ay.empty else [
        {"ay": r["ay"], "mwh": _kw(r["uretim_mwh"]),
         # aylik_ozet kolonu 'saat' (v2.68) — 'saglam_saat' degil (canli ders #2)
         "saglam_saat": int(r["saat"]) if "saat" in r else None,
         "kapsam_pct": _kw(r["kapsam_pct"]) if "kapsam_pct" in r else None,
         "beklenti_mwh": _beklenti(r["ay"])}
        for _, r in ay.tail(12).iterrows()]
    return {
        "plant": {**santral,
                  "tilt": row.get("tilt"),
                  "azimuth": row.get("azimuth"),
                  "panel_tech": row.get("panel_tech")},
        "mode": o.mode, "sapma_pct": _kw(o.sapma_pct),
        "anlati": o.icgoru_cumlesi,
        "bugun_kwh": _kw(o.bugun_kwh), "yarin_kwh": _kw(o.yarin_kwh),
        "yarin_hava": o.yarin_hava, "hafta_mwh": _kw(o.hafta_mwh),
        "model_alt": o.model_alt,
        "kalibrasyon_tarihi": _tarih(o.kalibrasyon_tarihi),
        "hava": o.hava_3gun,
        "gunler": [{"etiket": e, "mwh": _kw(v)}
                   for e, v in zip(o.gunler, o.gunluk_mwh)],
        "saglik": {"son_scada": _tarih(o.son_scada_tarihi),
                   "islenen_saat": o.islenen_saat,
                   "anomali": o.anomali_sayisi,
                   "veri_durumu": _kalite.tazelik_durumu(o.son_scada_tarihi)},   # v2.605 (F4-K): tazelik rozeti ortak sözlükten
        "aylik": aylik,
    }


def _naif_wmape(r):
    """Gunluk naif WMAPE: once SAKLANAN kolon (v2.95, sartname S4), yoksa
    v2.76 turetmesi (migration-oncesi satirlar), o da yoksa null — icat yok."""
    nv = r.get("naive_wmape")
    if nv is not None and not pd.isna(nv):
        return _kw(nv)
    sv = r.get("skill_vs_naive")
    if sv is not None and not pd.isna(sv) and sv < 100:
        return _kw(r["mape"] / (1 - sv / 100))
    return None


@app.get("/v1/plants/{plant_id}/kalibrasyon")
def kalibrasyon_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.122 — aktif kalibrasyon ozeti; kayit yoksa 404 (icat yok)."""
    from pvquant.services import calib_service
    k = calib_service.kalibrasyon_ozeti(claims["tenant_id"], plant_id)
    if k is None:
        raise HTTPException(404, "aktif kalibrasyon yok")
    return k


@app.get("/v1/plants/{plant_id}/saat-ay-matrisi")
def saat_ay_matrisi_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.121 — Solargis Tablo 4.3: yerel saat x ay ortalama uretim (kW),
    tum valid SCADA'dan. Bos SCADA'da 200 + bos listeler."""
    from pvquant.services import ozet_service
    return ozet_service.saat_ay_matrisi(claims["tenant_id"], plant_id)


@app.get("/v1/plants/{plant_id}/gunes-yolu")
def gunes_yolu_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.116 — sunpath (Solargis Fig 2.3 gelenegi): yaz/ekinoks/kis
    azimut x yukseklik egrileri + saat isaretleri. Salt astronomi (pvlib);
    santralin lat/lon/tz'sinden hesaplanir, arsiv verisi gerektirmez."""
    from pvquant.services import gunes_service
    return gunes_service.gunes_yolu(claims["tenant_id"], plant_id)


@app.get("/v1/plants/{plant_id}/hata-dagilimi")
def hata_dagilimi_uc(plant_id: str, gun: int = 120, kova: str = "0-24",
                     claims=Depends(gecerli_kullanici)):
    """v2.112 — gunluk sapma dagilimi (F-A, MWh/gun), rapor s08 tanimi.
    Hesap accuracy_service'te; coklu-kosu savunmali. Bos dagilim 200 +
    bos kutular doner."""
    from pvquant.services import accuracy_service
    if not (1 <= gun <= 365):
        raise HTTPException(422, "gun 1-365 araliginda olmali")
    try:
        return accuracy_service.hata_dagilimi(
            claims["tenant_id"], plant_id, gun=gun, kova=kova)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/plants/{plant_id}/saat-profili")
def saat_profili_uc(plant_id: str, gun: int = 30, kova: str = "0-24",
                    claims=Depends(gecerli_kullanici)):
    """v2.532 — saat başına ortalama işaretli hata (p50 − gerçek, kW) ve sistematik sapma saatleri; Kalibrasyon sayfası.
    v2.111'in saat × gün matrisi (/hata-matrisi) kaldırıldı. Kurallar gece_skill ile özdeş (flag='valid', gündüz > %2
    kapasite, yerel gün penceresi). Veri yoksa 200 + boş profil döner."""
    from pvquant.services import accuracy_service
    if not (1 <= gun <= 120):
        raise HTTPException(422, "gun 1-120 araliginda olmali")
    try:
        return accuracy_service.saat_profili(
            claims["tenant_id"], plant_id, gun=gun, kova=kova)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/plants/{plant_id}/alarmlar")
def alarmlar(plant_id: str, n: int = 20,
             claims=Depends(gecerli_kullanici)):
    """v2.239 — zil kapısı. Ham okuma (alarm_service.listele); üretici
    worker'daki günlük taramadır (El Kitabı P4 §3, iki kural). Boş liste
    200 döner — 'alarm yok' durumunu istemci anlatır."""
    from pvquant.services import alarm_service
    if not (1 <= n <= 100):
        raise HTTPException(422, "n 1-100 araliginda olmali")
    return alarm_service.listele(claims["tenant_id"], plant_id, n=n)


# ------------------------------------------------------------------ v2.265: alarm okundu/atama/kurallar + damga --------
class AtaIstek(BaseModel):
    kime: str | None = None


class KuralIstek(BaseModel):
    kurallar: list[str]
    esik: dict[str, float] | None = None
    alicilar: list[str] | None = None   # v2.519 (P7a): santral bazlı alarm alıcıları (e-posta); None → dokunma


@app.post("/v1/plants/{plant_id}/alarmlar/{alarm_id}/okundu")
def alarm_okundu(plant_id: str, alarm_id: str, claims=Depends(gecerli_kullanici)):
    """v2.265 — okundu (kim/ne zaman). Her oturum kullanıcısı işaretleyebilir."""
    from pvquant.services import alarm_service
    if not alarm_service.okundu(claims["tenant_id"], plant_id, alarm_id, claims["sub"]):
        raise HTTPException(404, "alarm yok")
    return {"okundu": True}


@app.post("/v1/plants/{plant_id}/alarmlar/{alarm_id}/ata")
def alarm_ata(plant_id: str, alarm_id: str, p: AtaIstek, claims=Depends(yazma_yetkisi())):
    """v2.265 — atama (kime=null kaldırır); editor/admin."""
    from pvquant.services import alarm_service
    try:
        ok = alarm_service.ata(claims["tenant_id"], plant_id, alarm_id, p.kime)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not ok:
        raise HTTPException(404, "alarm yok")
    return {"atandi": p.kime}


@app.post("/v1/oturum/yenile")
def oturum_yenile(claims=Depends(gecerli_kullanici)):
    """v2.300 — kayan oturum: geçerli jetonla yenisi alınır (rol/durum DB'den taze). Pasif hesap 401."""
    try:
        y = auth_service.oturum_yenile(claims["sub"])
    except auth_service.KiraciAskida:
        raise HTTPException(403, "hesap askıda")   # 24.10 Faz 0
    if y is None:
        raise HTTPException(401, "hesap etkin değil")
    return y


# ---- v2.299: ekip yönetimi ----

class UyeIstek(BaseModel):
    email: str
    rol: str


class UyeGuncelle(BaseModel):
    rol: str | None = None
    aktif: bool | None = None


class ParolaIstek(BaseModel):
    eski: str
    yeni: str


@app.get("/v1/takim", tags=["Yönetim"])
def takim(claims=Depends(yonetici_yetkisi())):
    return {"uyeler": auth_service.takim_listesi(claims["tenant_id"]), "roller": list(auth_service.ROLLER)}


@app.post("/v1/takim", tags=["Yönetim"], status_code=201)
def takim_ekle(p: UyeIstek, claims=Depends(yonetici_yetkisi())):
    """Geçici parola YALNIZ bu yanıtta görünür; üye ilk girişte kendi parolasını değiştirir."""
    try:
        y = auth_service.kullanici_ekle(claims["tenant_id"], p.email, p.rol)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "takim_ekle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=y["id"],
                    ayrinti={"email": y["email"], "rol": y["rol"]})   # geçici parola YAZILMAZ
    return y


@app.put("/v1/takim/{uye_id}", tags=["Yönetim"])
def takim_guncelle(uye_id: str, p: UyeGuncelle, claims=Depends(yonetici_yetkisi())):
    try:
        if not auth_service.kullanici_guncelle(claims["tenant_id"], uye_id, p.rol, p.aktif):
            raise HTTPException(404, "üye yok")
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "takim_guncelle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=uye_id,
                    ayrinti={"rol": p.rol, "aktif": p.aktif})
    return {"tamam": True}


@app.post("/v1/takim/{uye_id}/iki-adim-sifirla", tags=["Yönetim"])
def takim_iki_adim_sifirla(uye_id: str, claims=Depends(yonetici_yetkisi())):
    """v2.339 — üyenin iki adımlı doğrulamasını yönetici kapatır (kilitlenme çıkışı).
    Kendi hesabı için normal /v1/iki-adim/kapat kullanılır; bu uç BAŞKA üye içindir."""
    from pvquant.services import iki_adim_service
    if not iki_adim_service.yonetici_sifirla(claims["tenant_id"], uye_id):
        raise HTTPException(404, "üye yok")
    _denetim.kaydet("musteri", "takim_iki_adim_sifirla", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=uye_id)
    return {"tamam": True}


@app.post("/v1/parola")
def parola(p: ParolaIstek, claims=Depends(gecerli_kullanici)):
    """Kullanıcının kendi parolası — sunucu yalnız özet saklar."""
    try:
        auth_service.parola_degistir(claims["sub"], p.eski, p.yeni)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "parola_degistir", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=claims["sub"])
    return {"tamam": True}


# ---- v2.338: iki adımlı doğrulama (kullanıcının kendi hesabı) --------------
class IkiAdimKod(BaseModel):
    kod: str


@app.get("/v1/iki-adim")
def iki_adim_durum(claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    return iki_adim_service.durum(claims["sub"])


@app.post("/v1/iki-adim/baslat")
def iki_adim_baslat(claims=Depends(gecerli_kullanici)):
    """Sır + QR üretir (henüz aktif değil). E-posta claims'te yok → DB'den."""
    from pvquant.services import auth_service as au
    from pvquant.services import iki_adim_service
    try:
        return iki_adim_service.baslat(claims["sub"], au.eposta_getir(claims["sub"]))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/iki-adim/dogrula")
def iki_adim_dogrula(g: IkiAdimKod, claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    try:
        r = iki_adim_service.dogrula_ve_ac(claims["sub"], g.kod)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "iki_adim_ac", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=claims["sub"])   # v2.602 (F4-H); kod/sır yazılmaz
    return r


@app.post("/v1/iki-adim/kapat")
def iki_adim_kapat(g: IkiAdimKod, claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    try:
        iki_adim_service.kapat(claims["sub"], g.kod)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "iki_adim_kapat", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=claims["sub"])   # v2.602 (F4-H)
    return {"tamam": True}


@app.post("/v1/iki-adim/kurtarma-yenile")
def iki_adim_kurtarma(g: IkiAdimKod, claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    try:
        r = iki_adim_service.kurtarma_yenile(claims["sub"], g.kod)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "iki_adim_kurtarma_yenile", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="user", nesne_id=claims["sub"])   # v2.602; kodlar yazılmaz
    return r


@app.get("/v1/isler")
def isler(claims=Depends(gecerli_kullanici)):
    """v2.301 — gece işlerinin görünürlüğü (son 48 saat; hata ayrıntısı yalnız günlükte)."""
    from pvquant.services import isler_service
    return isler_service.ozet(claims["tenant_id"])


@app.get("/v1/kullanicilar")
def kullanici_listesi(claims=Depends(gecerli_kullanici)):
    """v2.265 — atama için kiracının kullanıcıları (id, e-posta, rol)."""
    from pvquant.services import alarm_service
    return alarm_service.kullanicilar(claims["tenant_id"])


@app.get("/v1/plants/{plant_id}/alarm-kurallari")
def alarm_kurallari(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.265 — varsayılan iki kural + santral bazında seçilmiş ek kurallar ve eşikleri."""
    from pvquant.services import alarm_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return alarm_service.kural_durumu(row)


@app.put("/v1/plants/{plant_id}/alarm-kurallari")
def alarm_kurallari_ayarla(plant_id: str, p: KuralIstek, claims=Depends(yazma_yetkisi())):
    """v2.265 — ek kural seçimi (opt-in) ve eşikler; editor/admin. Varsayılan iki kural kapatılamaz."""
    from pvquant.services import alarm_service
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        r = alarm_service.kural_ayarla(claims["tenant_id"], plant_id, p.kurallar, p.esik, alicilar=p.alicilar)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "alarm_kural_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id,   # v2.602 (F4-H)
                    ayrinti={"kurallar": list(p.kurallar or []), "esik": dict(p.esik or {}), "alici_sayisi": len(p.alicilar or [])})   # alıcı adresleri yazılmaz
    return r


@app.get("/v1/plants/{plant_id}/damga")
def damga(plant_id: str, request: Request, claims=Depends(gecerli_kullanici)):
    """v2.265 — değişim damgası: son SCADA/koşu/alarm/skill/kalibrasyon zamanları; ETag ile If-None-Match → 304.
    İstemci yalnız damga değişince veri çeker (60 s görünür / 5 dk arka plan)."""
    from fastapi.responses import JSONResponse

    from pvquant.services import damga_service
    d = damga_service.hesapla(claims["tenant_id"], plant_id)
    et = damga_service.etag_uret(d)
    if request.headers.get("if-none-match") == et:
        return Response(status_code=304, headers={"ETag": et, "Cache-Control": "no-cache"})
    return JSONResponse(d, headers={"ETag": et, "Cache-Control": "no-cache"})


class FizikIstek(BaseModel):
    ayar: dict


@app.get("/v1/plants/{plant_id}/fizik-terimleri")
def fizik_terimleri_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.274 — santralın fizik terimleri (geliş açısı, spektral, kirlenme, kar) ve seçenekleri."""
    from pvquant.services import fizik_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return fizik_service.durum(row)


@app.put("/v1/plants/{plant_id}/fizik-terimleri")
def fizik_terimleri_ayarla(plant_id: str, p: FizikIstek, claims=Depends(yazma_yetkisi())):
    """v2.274 — terimleri aç/kapa; bir sonraki koşudan itibaren geçerli (koşular güncellenmez, yenisi eklenir)."""
    from pvquant.services import fizik_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    eski = dict((row.get("params_json") or {}))
    try:
        temiz = fizik_service.dogrula(p.ayar)   # izde doğrulanmış (tür dönüşümlü) değerler karşılaştırılır; ham istek değil
        r = fizik_service.ayar_yaz(claims["tenant_id"], plant_id, p.ayar)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "fizik_terim_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id,   # v2.602 (F4-H): damga dışı (tahmin katmanı)
                    ayrinti={"degisen": {k: {"eski": eski.get(k), "yeni": v} for k, v in temiz.items() if eski.get(k) != v}})
    return r


@app.post("/v1/plants/{plant_id}/fizik-terimleri/onizle")
def fizik_terimleri_onizle(plant_id: str, p: FizikIstek, claims=Depends(gecerli_kullanici)):
    """v2.274 — 'açsam ne değişir?': arşivdeki koşu meteosuyla salt fizik, mevcut ↔ aday, 7 günlük enerji farkı."""
    from pvquant.services import fizik_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        return fizik_service.onizle(claims["tenant_id"], row, p.ayar)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/plants/{plant_id}/nowcast")
def nowcast(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.266 — kısa ufuk (0–6 s): ölçüm persistansı ile P50 harmanı. Uydu DEĞİL; SCADA tazeliği >3 s ise devre dışı ('—')."""
    from pvquant.services import nowcast_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return nowcast_service.hesapla(claims["tenant_id"], row)


@app.get("/v1/dogrulama")
def dogrulama():
    """v2.294 — kamuya açık doğrulama karnesi (kimliksiz). Yayın operatör bayrağına bağlı;
    yalnız toplulaştırılmış sayılar çıkar, santral kimliği çıkmaz. 60 sn önbellek başlığı."""
    from fastapi.responses import JSONResponse

    from pvquant.services import dogrulama_service
    return JSONResponse(dogrulama_service.ozet(), headers={"Cache-Control": "public, max-age=60"})


class BasvuruIstek(BaseModel):
    eposta: str
    santral_adi: str | None = None
    kurulu_guc_kwp: float | None = None
    web: str | None = None   # bal küpü — insanlar görmez, botlar doldurur


@app.post("/v1/vitrin/basvuru")
@limiter.limit("10/hour")
def vitrin_basvuru(request: Request, g: BasvuruIstek):
    """v2.328 — kamuya açık 'Karneni başlat' formu. Başvuru tabloya düşer,
    panelde yönetici görür; e-posta altyapısı bilerek yok (insan döner)."""
    from pvquant.services import basvuru_service
    r = basvuru_service.kaydet(g.eposta, g.santral_adi, g.kurulu_guc_kwp, g.web)
    if not r["tamam"]:
        raise HTTPException(422, r.get("neden") or "geçersiz")
    # v2.334: teyit = başvurana onay e-postası gerçekten gönderildi mi (SMTP
    # yapılandırılmamışsa False — istemci "e-posta gönderildi" DEMEZ).
    return {"tamam": True, "teyit": bool(r.get("teyit"))}


class ParolaSifirlamaIstek(BaseModel):
    eposta: str


class ParolaSifirlamaGovde(BaseModel):
    jeton: str
    parola: str


@app.post("/v1/parola-sifirla-istek")
@limiter.limit("5/hour")
def parola_sifirla_istek(request: Request, g: ParolaSifirlamaIstek):
    """v2.335 — "şifremi unuttum": kayıtlı hesaba tek kullanımlık bağlantı
    e-postalanır. Yanıt HER durumda aynı — hesap varlığı sızdırılmaz.
    v2.339: yanıta "posta_acik" eklendi — bu SUNUCUNUN mektup gönderebilme
    yeteneğidir, bu isteğin sonucu DEĞİL; dolayısıyla hesap varlığını yine
    sızdırmaz. Gerekçe: SMTP yapılandırılmamışken arayüz "bağlantı gönderildi"
    diyor ve kullanıcı asla gelmeyecek postayı bekliyordu (18 Eyl'de canlıda
    ölçüldü: jeton yazıldı, mektup çıkmadı)."""
    from pvquant.services import auth_service, posta_service
    auth_service.parola_sifirlama_istek(g.eposta)
    return {"tamam": True, "posta_acik": posta_service.yapilandirildi()}


@app.post("/v1/parola-sifirla")
@limiter.limit("10/hour")
def parola_sifirla(request: Request, g: ParolaSifirlamaGovde):
    """v2.335 — bağlantıdaki jetonla yeni parola. Jeton tek kullanımlıktır."""
    from pvquant.services import auth_service
    try:
        auth_service.parola_sifirla(g.jeton, g.parola)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"tamam": True}


# 24.10 Faz 2: /v1/vitrin/basvurular* müşteri uçları KALDIRILDI — başvurular platform yüzünde (/v1/yonetim/basvurular*).
# Faz 0'ın PVQ_PLATFORM_TENANT_ID geçici kilidi de bununla kalktı.


@app.get("/v1/hakkinda")
def hakkinda(claims=Depends(gecerli_kullanici)):
    """v2.270 — Veri kaynakları ve lisanslar (Gizlilik Anayasası v2.245 istisnası: atıf yalnız burada, rapor künyesinde, README'de)."""
    from pvquant.services import kaynak_service
    return kaynak_service.hakkinda()


@app.get("/v1/portfoy/tahmin")
def portfoy_tahmin(gun: int = 7, claims=Depends(gecerli_kullanici)):
    """v2.280 — hiyerarşik uzlaştırılmış portföy tahmini (bottom-up; ≥2 santral + artık geçmişiyle MinT)."""
    from pvquant.services import uzlastirma_service
    if not (1 <= gun <= 15):
        raise HTTPException(422, "gun 1-15")
    return uzlastirma_service.portfoy_tahmini(claims["tenant_id"], gun=gun)


@app.get("/v1/portfoy/dsg")
def portfoy_dsg(gun: int = 30, anahtar: str = "sapma", grup: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.276 — DSG/toplayıcı portföy netleştirmesi: santral başına ayrı dengesizlik ↔ portföyün netleşmiş dengesizliği.
    29.10: `anahtar` — grubun EDT'sinin üyelere dağıtımı (sapma | esit | uretim; sözleşmesel)."""
    from pvquant.ext.turkiye import dengesizlik as _d
    from pvquant.services import dengesizlik_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14-365")
    if anahtar not in _d.DAGITIM_ANAHTARLARI:
        raise HTTPException(422, "anahtar " + "|".join(_d.DAGITIM_ANAHTARLARI))
    return dengesizlik_service.dsg_ozet(claims["tenant_id"], gun=gun, dagitim_anahtari=anahtar, **({"grup": grup[:32]} if grup else {}))   # v2.539: DSG grubu seçimi


@app.get("/v1/portfoy/dsg.csv")
def portfoy_dsg_csv(gun: int = 30, anahtar: str = "sapma", grup: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.522 (P2b, IH-036) — DSG üye dağılımı belgesi: üye başına EDT tek başına / bireysel / DSG içinde, netleşme farkı, KÜPST, pay (CSV)."""
    from fastapi.responses import Response

    from pvquant.ext.turkiye import dengesizlik as _d
    from pvquant.services import dengesizlik_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14-365")
    if anahtar not in _d.DAGITIM_ANAHTARLARI:
        raise HTTPException(422, "anahtar " + "|".join(_d.DAGITIM_ANAHTARLARI))
    o = dengesizlik_service.dsg_ozet(claims["tenant_id"], gun=gun, dagitim_anahtari=anahtar, **({"grup": grup[:32]} if grup else {}))   # v2.539
    _denetim.kaydet("musteri", "dsg_belge_indir", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="tenant", nesne_id=claims["tenant_id"],
                    ayrinti={"gun": gun, "anahtar": anahtar, "uye": len(o.get("uyeler") or {})})
    return Response(dengesizlik_service.dsg_uye_csv(o), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="pvquant_dsg_uye_dagilimi_{gun}g_{anahtar}.csv"'})


@app.get("/v1/portfoy/kupst")
def portfoy_kupst(gun: int = 30, anahtar: str = "sapma", claims=Depends(gecerli_kullanici)):
    """31.10 (v2.511, 04 #14) — toplayıcı/GTŞ portföyü: dağıtıma bağlı lisanssız santrallerin KÜPST'si UEVÇB bazında (params_json.uevcb);
    `anahtar` santrallere dağılım (sapma | uretim | kurulu | esit; sözleşmesel, mevzuatta tanımsız)."""
    from pvquant.ext.turkiye import dengesizlik as _d
    from pvquant.services import dengesizlik_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14-365")
    if anahtar not in _d.PORTFOY_ANAHTARLARI:
        raise HTTPException(422, "anahtar " + "|".join(_d.PORTFOY_ANAHTARLARI))
    return dengesizlik_service.portfoy_kupst_ozet(claims["tenant_id"], gun=gun, dagitim_anahtari=anahtar)


@app.get("/v1/portfoy")
def portfoy(claims=Depends(gecerli_kullanici)):
    """v2.263 — kiracının tüm santralleri: kapasite, son ölçüm, 30g WMAPE, bugün/yarın beklenen, açık alarm; toplamlar."""
    from pvquant.services import portfoy_service
    return portfoy_service.ozet(claims["tenant_id"])


def _kgup_yaniti(tenant_id: str, plant_id: str, gun: str | None, kantil: str, fmt: str, indiren=None):
    """v2.260/v2.264 — panel ve dış API'nin ortak KGÜP gövdesi. v2.502: CSV indirme arşive yazılır (kgup_arsiv_service; aynı içerik yeni sürüm açmaz)."""
    from datetime import date, timedelta

    from pvquant.services import kgup_service, plant_service
    if kantil not in kgup_service.KANTILLER:
        raise HTTPException(422, "kantil p10|p25|p50|p75|p90")
    row = plant_service.getir(tenant_id, plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    # v2.262: 'yarın' santralin piyasa gününe göre (İstanbul), sunucunun UTC takvimine göre değil —
    # 21:00 UTC sonrası UTC 'bugün' hâlâ dünkü piyasa günüdür; canlı kontrolde KGÜP kartı bu yüzden boş kaldı.
    g = date.fromisoformat(gun) if gun else (pd.Timestamp.now(tz=PIYASA_TZ).date() + timedelta(days=1))
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j; pj = _j.loads(pj)
    r = kgup_service.uret(tenant_id, {"id": str(row["id"]), "capacity_kwp": float(row["capacity_kwp"]), "ac_limit_kw": row.get("ac_limit_kw"), "uevcb": pj.get("uevcb"),
                                      "params_json": pj},   # v2.275: EAK alanı / geçici kısıt params_json'dan
                          g, kantil)
    if "hata" in r:
        raise HTTPException(int(r.get("kod", 409)), r["hata"] + (f" (eksik saatler: {r['eksik_saatler']})" if r.get("eksik_saatler") else ""))
    if fmt == "json":
        return {k: v for k, v in r.items() if k not in ("csv", "eak_csv")}
    from pvquant.services import kgup_arsiv_service
    if fmt == "eak":   # v2.512: TPYS EAK.csv biçiminde EAK dosyası (ayrı ekran/servis); v2.513: KGÜP gibi arşivlenir (kaynak 'eak')
        from pvquant.ext.turkiye.kgup import EAK_KOLONLAR
        r_eak = {**r, "csv": r["eak_csv"], "bom": False, "dosya_adi": r["eak_dosya_adi"], "sha256": r["eak_sha256"], "kantil": "eak",
                 "toplam_mwh": None, "sablon": {"durum": "TPYS EAK.csv", "kolonlar": list(EAK_KOLONLAR)}}
        arsiv = kgup_arsiv_service.kaydet(tenant_id, str(row["id"]), r_eak, indiren=indiren, kaynak="eak")
        _denetim.kaydet("musteri", "eak_indir", aktor_id=indiren, tenant_id=tenant_id, nesne_tur="plant", nesne_id=row["id"],   # v2.516 (#7)
                        ayrinti={"gun": g.isoformat(), "surum": arsiv["surum"], "yeni_surum": bool(arsiv.get("yeni")), "kanal": "panel" if indiren else "api"})
        return Response(content=kgup_arsiv_service.baytlar(r_eak), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{r["eak_dosya_adi"]}"', "X-PVQ-Surum": str(arsiv["surum"]), "X-PVQ-SHA256": arsiv["sha256"]})
    arsiv = kgup_arsiv_service.kaydet(tenant_id, str(row["id"]), r, indiren=indiren)   # v2.502: değiştirilemez sürüm kaydı
    _denetim.kaydet("musteri", "kgup_indir", aktor_id=indiren, tenant_id=tenant_id, nesne_tur="plant", nesne_id=row["id"],   # v2.516 (#7)
                    ayrinti={"gun": g.isoformat(), "kantil": kantil, "surum": arsiv["surum"], "yeni_surum": bool(arsiv.get("yeni")), "kanal": "panel" if indiren else "api"})
    return Response(content=kgup_arsiv_service.baytlar(r), media_type="text/csv; charset=utf-8",   # baytlar tek yerde (BOM yalnız şablon isterse; SHA-256 bu baytlarla)
                    headers={"Content-Disposition": f'attachment; filename="{r["dosya_adi"]}"', "X-PVQ-Surum": str(arsiv["surum"]), "X-PVQ-SHA256": arsiv["sha256"]})


@app.get("/v1/plants/{plant_id}/kgup")
def kgup_dosyasi(plant_id: str, gun: str | None = None, kantil: str = "p50", fmt: str = "csv", claims=Depends(gecerli_kullanici)):
    """v2.260 — KGÜP saatlik program (D-1 15:30 öncesi koşudan). fmt=csv → TPYS CSV eki (arşive yazılır); fmt=json → önizleme."""
    return _kgup_yaniti(claims["tenant_id"], plant_id, gun, kantil, fmt, indiren=claims.get("sub"))


@app.get("/v1/plants/{plant_id}/kgup/surumler")
def kgup_surumler(plant_id: str, gun: str | None = None, n: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.502 (F-06) — indirilen KGÜP dosyalarının sürüm geçmişi (yeni → eski); kayıt değiştirilemez."""
    from datetime import date as _d

    from pvquant.services import kgup_arsiv_service, plant_service
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    if not (1 <= n <= 200):
        raise HTTPException(422, "n 1-200")
    try:
        g = _d.fromisoformat(gun) if gun else None
    except ValueError:
        raise HTTPException(422, "gun YYYY-MM-DD olmalı")
    return {"surumler": kgup_arsiv_service.listele(claims["tenant_id"], plant_id, g, n)}


@app.post("/v1/plants/{plant_id}/kgup/bildirilen")
def kgup_bildirilen_yukle(plant_id: str, gun: str, dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """v2.503 (F-06) — müşterinin TPYS'ye bildirdiğini beyan ettiği KGÜP dosyası: doğrulanır, 'musteri' kaynağıyla değiştirilemez kayıt;
    TPYS kabulü doğrulanmaz (beyan). Yanıt: kayıt + öneriyle kıyas."""
    from datetime import date as _d

    from pvquant.services import kgup_arsiv_service, plant_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        g = _d.fromisoformat(gun)
    except ValueError:
        raise HTTPException(422, "gun YYYY-MM-DD olmalı")
    b = dosya.file.read()
    if not b or len(b) > 2_000_000:
        raise HTTPException(422, "dosya boş ya da 2 MB'tan büyük")
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j; pj = _j.loads(pj)
    from pvquant.ext.turkiye.kgup import Sablon
    try:
        k = kgup_arsiv_service.musteri_kaydet(claims["tenant_id"], str(row["id"]), g, b, dosya.filename or "bildirilen.csv", indiren=claims.get("sub"), sablon=Sablon.params_json_dan(pj))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "kgup_bildirilen_yukle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],   # v2.516 (#7)
                    ayrinti={"gun": g.isoformat(), "surum": k.get("surum"), "dosya": (dosya.filename or "bildirilen.csv")[:80]})
    return {"kayit": k, "kiyas": kgup_arsiv_service.kiyas(claims["tenant_id"], str(row["id"]), g)}


@app.post("/v1/plants/{plant_id}/kgup/sablon")
def kgup_sablon_ogren(plant_id: str, dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """29.10 (v2.506) — müşterinin EPYS/TPYS'den indirdiği KGÜP dosyasından (CSV/Excel, ≤2 MB) dışa aktarma biçimi öğrenilir:
    kolon adları/sırası, ayraç, ondalık, tarih biçimi → params_json.kgup_sablon; sonraki CSV indirmeleri bu biçimde çıkar."""
    from datetime import datetime, timezone

    from pvquant.ext.turkiye import kgup as kg
    from pvquant.services import kgup_service, plant_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    b = dosya.file.read()
    if not b or len(b) > 2_000_000:
        raise HTTPException(422, "dosya boş ya da 2 MB'tan büyük")
    try:
        r = kg.sablon_ogren(b, dosya.filename or "sablon")
    except ValueError as e:
        raise HTTPException(422, str(e))
    kaynak = {"dosya": dosya.filename or "sablon", "zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "bicim": r["bicim"]}
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, kgup_sablon=r["sablon"], kgup_sablon_kaynak=kaynak)
    _denetim.kaydet("musteri", "kgup_sablon_ogren", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],   # v2.516 (#7)
                    ayrinti={"dosya": kaynak["dosya"][:80], "bicim": r["bicim"]})
    return {"sablon": kgup_service.sablon_ozeti(pj), "eslesme": r["eslesme"], "eslesmeyen": r["eslesmeyen"], "uyarilar": r["uyarilar"]}


@app.delete("/v1/plants/{plant_id}/kgup/sablon")
def kgup_sablon_sifirla(plant_id: str, claims=Depends(yazma_yetkisi())):
    """29.10 (v2.506) — öğrenilen şablonu kaldırır; varsayılan beş kolona dönülür."""
    from pvquant.services import kgup_service, plant_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, kgup_sablon=None, kgup_sablon_kaynak=None)
    _denetim.kaydet("musteri", "kgup_sablon_sifirla", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"])   # v2.516 (#7)
    return {"sablon": kgup_service.sablon_ozeti(pj)}


@app.get("/v1/plants/{plant_id}/kgup/revizyon")
def kgup_revizyon(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.507 (F-10) — bugünün programı ↔ güncel beklenti: eşik üstü sapan ve revizyon süresi geçmemiş saatler (GİP kapısı + 30 dk).
    Yol göstericidir; kayıt yazmaz, revizyon TPYS'de yapılır."""
    from pvquant.services import plant_service, revizyon_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return revizyon_service.oner(claims["tenant_id"], row)


@app.get("/v1/plants/{plant_id}/kgup/kiyas")
def kgup_kiyas(plant_id: str, gun: str, claims=Depends(gecerli_kullanici)):
    """v2.503 (F-06) — teslim günü için son PVQuant önerisi ↔ müşterinin bildirdiği KGÜP: saat saat fark."""
    from datetime import date as _d

    from pvquant.services import kgup_arsiv_service, plant_service
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        g = _d.fromisoformat(gun)
    except ValueError:
        raise HTTPException(422, "gun YYYY-MM-DD olmalı")
    return kgup_arsiv_service.kiyas(claims["tenant_id"], plant_id, g)


@app.get("/v1/plants/{plant_id}/kgup/surumler/{surum_id}")
def kgup_surum_dosyasi(plant_id: str, surum_id: str, claims=Depends(gecerli_kullanici)):
    """v2.502 (F-06) — arşivdeki dosyanın kendisi (bayt bayt; SHA-256 doğrulanır)."""
    from pvquant.services import kgup_arsiv_service, plant_service
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    r = kgup_arsiv_service.getir(claims["tenant_id"], plant_id, surum_id)
    if r is None:
        raise HTTPException(404, "sürüm yok")
    return Response(content=r["dosya"], media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{r["dosya_adi"]}"', "X-PVQ-Surum": str(r["surum"]), "X-PVQ-SHA256": r["sha256"]})


# ------------------------------------------------------------------ v2.264: Dış API (X-API-Key) --------------
def _son_kosu_kimligi(tenant_id: str, plant_id: str):
    from sqlalchemy import text as _t

    from pvquant.db import tenant_baglami as _tb
    with _tb(tenant_id) as s:
        return s.execute(_t(
            "SELECT id, run_at, mode FROM forecast_runs WHERE plant_id=:p "
            f"AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=forecast_runs.id) AND {_yayin_sql('forecast_runs')} ORDER BY run_at DESC LIMIT 1"),
            {"p": plant_id}).first()


class SayacAyarIstek(BaseModel):
    """v2.523 (P4a): sayaç türü ve lisanssız SCADA durumu; yalnız istekte geçen alanlar değişir, null temizler."""
    sayac_turu: str | None = None                   # 15dk_endeks | diger
    scada_durum: str | None = None                  # bagli | kopuk | yok (lisanssız, LÜY m.21(7))
    scada_kopukluk_baslangic: str | None = None     # YYYY-MM-DD
    scada_uyari_tarihi: str | None = None           # v2.538 (DK-656): dağıtım şirketinin yazılı SCADA onarım uyarısı tarihi (YYYY-MM-DD); (ç) sayımı buradan başlar
    uzlastirma_girdi: str | None = None             # v2.526 (P4a-2): scada | sayac — uzlaştırma yeniden hesabında gerçekleşen üretim kaynağı
    uzaktan_acma_var: bool | None = None            # uzaktan açma-kapama yeteneği envanterde
    sistem_kullanim_bedeli_tl_ay: float | None = None   # Karar 14909 bedel göstergesi girdisi (dağıtım faturasından)


@app.get("/v1/dis/santraller", tags=["Dış API"])
def dis_santraller(anahtar=Depends(api_anahtari("tahmin:oku"))):
    """Anahtarın kiracısındaki santraller: kimlik, ad, kurulu güç, saat dilimi + v2.599 (F4-E) tarihli künye alanları
    (bugün geçerli sürüm; künyesiz santralda null)."""
    from pvquant.services import api_anahtar_service
    from pvquant.services import santral_kunye_service as _sk
    out = []
    for p in plant_service.listele(anahtar["tenant_id"]):
        if not api_anahtar_service.santral_izinli(anahtar, p["id"]):   # v2.603 (F4-I): anahtarın santral kapsamı
            continue
        k = _sk.guncel(anahtar["tenant_id"], p["id"]) or {}
        out.append({"id": str(p["id"]), "ad": p["name"], "kapasite_kwp": float(p["capacity_kwp"]), "tz": p["tz"],
                    "dc_kwp": k.get("dc_kwp", float(p["capacity_kwp"])), "ac_kw": k.get("ac_kw", p.get("ac_limit_kw")), "eak_kw": k.get("eak_kw"),
                    "baglanti_turu": k.get("baglanti_turu"), "gerilim_kv": k.get("gerilim_kv"), "segment": k.get("segment"), "lisans_durumu": k.get("lisans_durumu"),
                    "uevcb_kod": k.get("uevcb_kod"), "eic": k.get("eic"), "epias_santral_id": k.get("epias_santral_id"), "olcum_siniri": k.get("olcum_siniri"),
                    "kunye_gecerli_bas": k.get("gecerli_bas"), "kunye_dogrulama": k.get("dogrulama")})
    return out


@app.get("/v1/dis/santral/{plant_id}/tahmin", tags=["Dış API"])
def dis_tahmin(plant_id: str, request: Request, anahtar=Depends(api_anahtari("tahmin:oku"))):
    """Son koşunun saatlik P10/P50/P90 (kW, UTC). ETag = koşu kimliği; `If-None-Match` eşleşirse 304 (gövde yok).
    Bant yoksa alan null gelir — istemci uydurmasın."""
    from pvquant.services import forecast_service
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    kosu = _son_kosu_kimligi(anahtar["tenant_id"], plant_id)
    if kosu is None:
        raise HTTPException(409, "bu santral için henüz koşu yok")
    etag = f'W/"{kosu.id}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    df = forecast_service.son_kosu(anahtar["tenant_id"], plant_id)
    def _f(v):
        return None if v is None or pd.isna(v) else round(float(v), 2)
    saatlik = [{"ts": ts.isoformat(), "p10_kw": _f(r.p10_kw), "p50_kw": _f(r.p50_kw), "p90_kw": _f(r.p90_kw)} for ts, r in df.iterrows()]
    govde = {"santral_id": str(row["id"]), "santral": row["name"], "birim": "kW",
             "kosu": {"id": str(kosu.id), "zaman": kosu.run_at.isoformat(), "mod": kosu.mode},
             "saatlik": saatlik}
    from fastapi.responses import JSONResponse
    return JSONResponse(govde, headers={"ETag": etag, "Cache-Control": "private, max-age=60"})


@app.get("/v1/dis/santral/{plant_id}/kgup", tags=["Dış API"])
def dis_kgup(plant_id: str, gun: str | None = None, kantil: str = "p50", fmt: str = "json", anahtar=Depends(api_anahtari("kgup:oku"))):
    """KGÜP saatlik program (D-1 15:30 öncesi koşudan); gün verilmezse İstanbul yarını. fmt=json yan etkisiz.
    v2.603 (F4-I): fmt=csv|eak GET ile hâlâ çalışır ama ARŞİVE YAZAR (yan etki) — `Deprecation` başlığıyla uyarılır; yeni istemciler POST /kgup kullanır."""
    _dis_santral(anahtar, plant_id)
    r = _kgup_yaniti(anahtar["tenant_id"], plant_id, gun, kantil, fmt)
    if fmt != "json" and isinstance(r, Response):
        r.headers["Deprecation"] = "true"
        r.headers["Warning"] = '299 - "GET fmt=csv/eak arsive yazar (yan etki); POST /v1/dis/santral/{id}/kgup kullanin"'
    return r


class KgupUretIstek(BaseModel):
    gun: str | None = None      # YYYY-MM-DD (İstanbul teslim günü); verilmezse yarın
    kantil: str = "p50"
    fmt: str = "csv"            # csv | eak


@app.post("/v1/dis/santral/{plant_id}/kgup", tags=["Dış API"])
def dis_kgup_uret(plant_id: str, p: KgupUretIstek, anahtar=Depends(api_anahtari("kgup:oku"))):
    """v2.603 (F4-I): KGÜP/EAK dosyasını ÜRET ve arşivle (yan etkili işlem POST'ta): TPYS CSV gövdesi, X-PVQ-Surum / X-PVQ-SHA256 başlıkları.
    Aynı içerik yeni sürüm açmaz. GET fmt=json önizleme yan etkisizdir."""
    if p.fmt not in ("csv", "eak"):
        raise _dis_hata(422, "istek_gecersiz", "fmt csv ya da eak olmalı")
    _dis_santral(anahtar, plant_id)
    return _kgup_yaniti(anahtar["tenant_id"], plant_id, p.gun, p.kantil, p.fmt)


@app.get("/v1/dis/santral/{plant_id}/kgup/surumler", tags=["Dış API"])
def dis_kgup_surumler(plant_id: str, gun: str | None = None, n: int = 30, anahtar=Depends(api_anahtari("kgup:oku"))):
    """v2.502 (F-06) — KGÜP sürüm geçmişi (indirilen dosyalar: sürüm, kaynak koşu, kesim, SHA-256)."""
    from datetime import date as _d

    from pvquant.services import kgup_arsiv_service
    _dis_santral(anahtar, plant_id)
    try:
        g = _d.fromisoformat(gun) if gun else None
    except ValueError:
        raise HTTPException(422, "gun YYYY-MM-DD olmalı")
    return {"surumler": kgup_arsiv_service.listele(anahtar["tenant_id"], plant_id, g, max(1, min(n, 200)))}


@app.get("/v1/dis/santral/{plant_id}/gerceklesen", tags=["Dış API"])
def dis_gerceklesen(plant_id: str, bas: str | None = None, bit: str | None = None, kaynak: str = "scada", anahtar=Depends(api_anahtari("gerceklesen:oku"))):
    """v2.528 (P10) — gerçekleşen üretim, saatlik kWh (UTC saat başı). kaynak=scada: geçerli SCADA ölçümü (brüt; kaynak etiketi scada_dosya /
    epias_seffaflik); kaynak=sayac: yüklü sayaç verisi (net veriş; kaynak epys/osos/mass/elle, nitelik ölçülmüş/tahmini). bas–bit Türkiye günü
    (dâhil), en çok 92 gün; verilmezse son 7 gün. Uzlaştırmaya esas UEVM değildir."""
    from datetime import date as _d
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    from pvquant.services import sayac_service
    if kaynak not in ("scada", "sayac"):
        raise HTTPException(422, "kaynak scada ya da sayac olmalı")
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    try:
        b1 = _d.fromisoformat(bit) if bit else _dt.now(sayac_service.IST).date()
        b0 = _d.fromisoformat(bas) if bas else b1 - _td(days=6)
    except ValueError:
        raise HTTPException(422, "bas/bit YYYY-MM-DD olmalı")
    if b0 > b1 or (b1 - b0).days > 91:
        raise HTTPException(422, "aralık en çok 92 gün ve bas ≤ bit olmalı")
    t0 = _dt.combine(b0, _dt.min.time(), tzinfo=sayac_service.IST); t1 = _dt.combine(b1 + _td(days=1), _dt.min.time(), tzinfo=sayac_service.IST)
    if kaynak == "scada":
        df = sayac_service.scada_oku(anahtar["tenant_id"], plant_id, t0, t1)
        saatlik = [{"ts": ts.isoformat(), "kwh": (None if pd.isna(r.kwh) else round(float(r.kwh), 3)), "kaynak": r.kaynak} for ts, r in df.iterrows()]
    else:
        df = sayac_service.sayac_oku(anahtar["tenant_id"], plant_id, t0, t1)
        saatlik = [{"ts": ts.isoformat(), "kwh": (None if pd.isna(r.veris_kwh) else round(float(r.veris_kwh), 3)), "cekis_kwh": (None if pd.isna(r.cekis_kwh) else round(float(r.cekis_kwh), 3)),
                    "kaynak": r.kaynak, "nitelik": r.nitelik} for ts, r in df.iterrows()]
    return {"santral_id": str(row["id"]), "santral": row["name"], "kaynak": kaynak, "birim": "kWh", "bas": b0.isoformat(), "bit": b1.isoformat(), "saat": len(saatlik),
            "not": ("SCADA brüt üretimdir; EPİAŞ uzlaştırmaya esas sayaç (UEVM) değildir." if kaynak == "scada" else
                    "Yüklü sayaç dosyasıdır (net veriş); uzlaştırmaya esas UEVM ile aynılığı doğrulanmaz. nitelik tahmini/doldurulmuş saatler EDAŞ kodundan."),
            "saatlik": saatlik}


@app.get("/v1/dis/santral/{plant_id}/kaynak-saatlik", tags=["Dış API"])
def dis_kaynak_saatlik(plant_id: str, bas: str | None = None, bit: str | None = None, sinir: str = "inverter_ac", anahtar=Depends(api_anahtari("gerceklesen:oku"))):
    """v2.559 (V4) — her saatin KAYNAK / ölçüm sınırı / NİTELİK (tam, kısmi, tahmini) / REVİZYON kimliğiyle gölge görünüm; üretim serisindeki saatle yan yana.
    bas–bit Türkiye günü (dâhil), en çok 31 gün; verilmezse son 7 gün. Tahmin ve doğruluk bu görünümü kullanmaz; uzlaştırmaya esas UEVM değildir."""
    from datetime import date as _d
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    from pvquant.services import kaynak_secim_service as ks
    from pvquant.services import sayac_service
    if sinir not in ks.SINIR_ETIKET:
        raise HTTPException(422, "sinir inverter_ac | plant_gross_ac | pcc_net | settlement olmalı")
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    try:
        b1 = _d.fromisoformat(bit) if bit else _dt.now(sayac_service.IST).date()
        b0 = _d.fromisoformat(bas) if bas else b1 - _td(days=6)
    except ValueError:
        raise HTTPException(422, "bas/bit YYYY-MM-DD olmalı")
    if b0 > b1 or (b1 - b0).days > 30:
        raise HTTPException(422, "aralık en çok 31 gün ve bas ≤ bit olmalı")
    t0 = _dt.combine(b0, _dt.min.time(), tzinfo=sayac_service.IST); t1 = _dt.combine(b1 + _td(days=1), _dt.min.time(), tzinfo=sayac_service.IST)
    gg = ks.golge_gorunum(anahtar["tenant_id"], row, t0, t1, sinir)
    saatler = []
    for h in gg.get("saatler") or []:
        sec = h.get("secilen") or {}; mev = h.get("mevcut") or {}
        saatler.append({"ts": h["ts_utc"], "kaynak": sec.get("kaynak"), "kaynak_etiketi": ks.KAYNAK_ETIKET.get(sec.get("kaynak") or "", sec.get("kaynak")), "cihaz_id": sec.get("cihaz_id"),
                        "sinir": sinir, "nitelik": sec.get("tamlik"), "nitelik_etiketi": sec.get("tamlik_etiketi"), "yontem": sec.get("yontem"), "revizyon": sec.get("revizyon"),
                        "kwh": (round(float(sec["energy_kwh"]), 3) if sec.get("energy_kwh") is not None else None), "alternatif_sayisi": h.get("alternatif_sayisi", 0),
                        "uretim_serisi_kwh": (round(float(mev["energy_kwh"]), 3) if mev.get("energy_kwh") is not None else None), "uretim_serisi_kaynak": mev.get("kaynak"),
                        "fark_kwh": h.get("fark_kwh"), "secim_nedeni": h.get("neden")})
    _denetim.kaydet("musteri", "rapor_donem_indir", aktor_id=None, tenant_id=anahtar["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"uc": "kaynak-saatlik", "bas": b0.isoformat(), "bit": b1.isoformat(), "sinir": sinir, "api_anahtar": anahtar["prefix"]})
    return {"santral_id": str(row["id"]), "santral": row["name"], "sinir": sinir, "sinir_etiketi": ks.SINIR_ETIKET[sinir], "bas": b0.isoformat(), "bit": b1.isoformat(), "birim": "kWh",
            "saat": len(saatler), "ozet": gg.get("ozet"), "oncelik": gg.get("oncelik"), "nitelik_ozeti": ks.nitelik_ozeti(anahtar["tenant_id"], row, t0, t1), "saatler": saatler,
            "uyari": gg.get("uyari"),
            "not": "Gölge görünüm: her saatin kaynağı, ölçüm sınırı, niteliği ve revizyonu. Kısmi ve tahmini saatler üretim serisine yazılmaz; tahmin ve doğruluk bu görünümü kullanmaz. "
                   "Uzlaştırmaya esas UEVM değildir."}


@app.post("/v1/dis/santral/{plant_id}/uretim-dosyasi", tags=["Dış API"])
def dis_uretim_dosyasi(plant_id: str, dosya: UploadFile = File(...), anahtar=Depends(api_anahtari("gerceklesen:yaz"))):
    """v2.553 (S3) — üretim dosyası İTME: SCADA / kayıt cihazı dışa aktarımı (CSV, XLSX; ≤50 MB) panelden yüklemeyle aynı alım hattından geçer (biçim/eşleme
    algılama, kayıtlı şablon, doğrulama karnesi) ve geçerli saatler üretim serisine yazılır. PVQuant üçüncü taraf gizlisi saklamaz; anahtar müşterinin.
    Cihaz bazlı dosyada tekrar politikası santral ayarından (`itme.tekrar`) gelir; yoksa 422."""
    from pvquant.services import itme_service
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    yol = _gecici_dosya(dosya)
    try:
        r = itme_service.dosya_isle(anahtar["tenant_id"], row, yol, dosya.filename or "uretim.csv", kanal="itme_http")
    finally:
        _os.unlink(yol)
    _denetim.kaydet("dis_api", "uretim_dosyasi_itme", aktor_id=anahtar.get("id"), tenant_id=anahtar["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"durum": r["durum"], "dosya": r.get("dosya"), "n_satir": r.get("n_satir"), "hata": (r.get("hata") or "")[:160] or None})
    if r["durum"] != "ok":
        raise HTTPException(422, r.get("hata") or "dosya işlenemedi")
    return r


@app.get("/v1/dis/santral/{plant_id}/alarmlar", tags=["Dış API"])
def dis_alarmlar(plant_id: str, n: int = 20, anahtar=Depends(api_anahtari("alarm:oku"))):
    """v2.528 (P10) — alarm listesi (yeni → eski; en çok 200): kural kodu + Türkçe adı, şiddet, mesaj, zaman, okunma/atama."""
    from pvquant.services import alarm_service
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    rows = alarm_service.listele(anahtar["tenant_id"], plant_id, max(1, min(int(n), 200)))
    return {"santral_id": str(row["id"]), "santral": row["name"], "alarmlar": [{**r, "kural_adi": alarm_service.KURAL_ETIKET.get(r["kural"], r["kural"])} for r in rows]}


@app.get("/v1/dis/santral/{plant_id}/rapor-donem", tags=["Dış API"])
def dis_rapor_donem(plant_id: str, donem: str | None = None, fmt: str = "json", anahtar=Depends(api_anahtari("rapor:indir"))):
    """v2.528 (P10) — dönem raporu: donem YYYY-MM | YYYY-QN | YYYY (verilmezse son tam ay); fmt json (veri) | html (indirilebilir).
    Panelin Raporlar › Dönem raporu ile aynı hesap; denetim izine düşer."""
    from pvquant.services import aylik_rapor_service
    if fmt not in ("html", "json"):
        raise HTTPException(422, "fmt html ya da json olmalı")
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    plant = {"id": str(row["id"]), "name": row["name"], "capacity_kwp": row.get("capacity_kwp"), "ac_limit_kw": row.get("ac_limit_kw"), "params_json": row.get("params_json")}
    try:
        if fmt == "json":
            v = aylik_rapor_service.veri(anahtar["tenant_id"], plant, donem); kod = v["donem"]["kod"]
        else:
            r, v = aylik_rapor_service.rapor(anahtar["tenant_id"], plant, donem); kod = v["donem"]["kod"]
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "rapor_donem_indir", aktor_id=None, tenant_id=anahtar["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"donem": kod, "fmt": fmt, "api_anahtar": anahtar["prefix"]})
    if fmt == "json":
        return v
    from pvquant.services.mutabakat_service import _sade
    ad = f"PVQuant_donem_raporu_{_sade(row['name']).replace(' ', '_')}_{kod}.html"
    return Response(aylik_rapor_service.html(r).encode("utf-8"), media_type="text/html; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@app.put("/v1/dis/santral/{plant_id}/ayarlar", tags=["Dış API"])
def dis_ayarlar(plant_id: str, p: SayacAyarIstek, anahtar=Depends(api_anahtari("santral:yaz"))):
    """v2.528 (P10) — santral ayarı yazma (sayaç ayarı alanları: sayac_turu, scada_durum, scada_kopukluk_baslangic, scada_uyari_tarihi (v2.538), uzaktan_acma_var,
    sistem_kullanim_bedeli_tl_ay, uzlastirma_girdi). Yalnız istekte geçen alanlar değişir, null temizler; panelin PUT sayac-ayar ile aynı doğrulama.
    Künye/segment/tarife bu kapsamda değildir (panelden)."""
    from pvquant.services import sayac_service
    row = _dis_santral(anahtar, plant_id)   # v2.603: 404 santral_yok / 403 santral_kapsam_disi
    try:
        an = sayac_service.ayar_dogrula(p.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, f"{e} alanı geçersiz")
    if not an:
        raise HTTPException(422, "değişecek alan yok")
    eski_pj = dict(row.get("params_json") or {})
    pj = plant_service.params_birlestir(anahtar["tenant_id"], plant_id, **an)
    _denetim.ayar_degisikligi_kaydet("sayac_ayar", aktor_id=anahtar.get("id"), tenant_id=anahtar["tenant_id"], plant_id=str(row["id"]), eski_pj=eski_pj, yeni_pj=pj,
                                     ek={"istek": dict(an), "api_anahtar": anahtar["prefix"]}, kapsam="dis_api")   # v2.602 (F4-H, M1): anahtarla yazma → dis_api kapsamı
    return {"santral_id": str(row["id"]), "degisen": an, "ayar": {k: (pj or {}).get(k) for k in ("sayac_turu", "scada_durum", "scada_kopukluk_baslangic", "scada_uyari_tarihi", "uzaktan_acma_var", "sistem_kullanim_bedeli_tl_ay", "uzlastirma_girdi")}}


# ------------------------------------------------------------------ v2.264: Yönetim (admin) -----------------
class AnahtarIstek(BaseModel):
    ad: str = ""
    kapsamlar: list[str]
    gecerlilik_gun: int | None = None
    rpm: int = 120
    plant_ids: list[str] | None = None   # v2.603 (F4-I): santral kapsamı (boş/None = tüm santraller)


class WebhookIstek(BaseModel):
    url: str
    plant_id: str | None = None
    olaylar: list[str] = ["tahmin.yeni"]


@app.get("/v1/api-anahtarlari", tags=["Yönetim"])
def anahtar_listesi(claims=Depends(yonetici_yetkisi())):
    from pvquant.services import api_anahtar_service
    return {"anahtarlar": api_anahtar_service.listele(claims["tenant_id"]), "kapsamlar": list(api_anahtar_service.CANLI_KAPSAMLAR),
            "kapsam_aciklama": dict(api_anahtar_service.KAPSAM_ACIKLAMA)}   # v2.528 (P10)


@app.post("/v1/api-anahtarlari", tags=["Yönetim"], status_code=201)
def anahtar_uret(p: AnahtarIstek, claims=Depends(yonetici_yetkisi())):
    """Düz anahtar YALNIZ bu yanıtta; sunucu sha256 dışında hiçbir şey saklamaz."""
    from pvquant.services import api_anahtar_service
    try:
        y = api_anahtar_service.uret(claims["tenant_id"], p.ad, p.kapsamlar, p.gecerlilik_gun, p.rpm, plant_ids=p.plant_ids)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "anahtar_uret", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="api_key", nesne_id=y.get("id"),
                    ayrinti={"ad": p.ad, "kapsamlar": p.kapsamlar, "rpm": p.rpm, "plant_ids": y.get("plant_ids")})   # düz anahtar YAZILMAZ
    return y


@app.delete("/v1/api-anahtarlari/{anahtar_id}", tags=["Yönetim"])
def anahtar_iptal(anahtar_id: str, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import api_anahtar_service
    if not api_anahtar_service.iptal(claims["tenant_id"], anahtar_id):
        raise HTTPException(404, "anahtar yok ya da zaten iptal")
    _denetim.kaydet("musteri", "anahtar_iptal", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="api_key", nesne_id=anahtar_id)
    return {"iptal": True}


@app.get("/v1/webhooklar", tags=["Yönetim"])
def webhook_listesi(claims=Depends(yonetici_yetkisi())):
    from pvquant.services import webhook_service
    return {"webhooklar": webhook_service.listele(claims["tenant_id"]), "olaylar": ["tahmin.yeni", "alarm.yeni"]}


@app.post("/v1/webhooklar", tags=["Yönetim"], status_code=201)
def webhook_ekle(p: WebhookIstek, claims=Depends(yonetici_yetkisi())):
    """`secret` YALNIZ bu yanıtta gösterilir; alıcı imzayı onunla doğrular."""
    from pvquant.services import webhook_service
    try:
        y = webhook_service.ekle(claims["tenant_id"], p.url, p.plant_id, p.olaylar)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "webhook_ekle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="webhook", nesne_id=y.get("id"),
                    ayrinti={"url": _denetim.maskele_url(p.url), "plant_id": p.plant_id})   # secret YAZILMAZ; v2.602: sorgu dizgisi/kullanıcı bilgisi maskelenir
    return y


@app.delete("/v1/webhooklar/{webhook_id}", tags=["Yönetim"])
def webhook_sil(webhook_id: str, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import webhook_service
    if not webhook_service.sil(claims["tenant_id"], webhook_id):
        raise HTTPException(404, "webhook yok")
    _denetim.kaydet("musteri", "webhook_sil", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="webhook", nesne_id=webhook_id)
    return {"silindi": True}


@app.post("/v1/webhooklar/{webhook_id}/dene", tags=["Yönetim"])
def webhook_dene(webhook_id: str, claims=Depends(yonetici_yetkisi())):
    """'deneme' olayı gönderir; alıcının döndürdüğü HTTP durumunu geri verir (0 = ulaşılamadı)."""
    from pvquant.services import webhook_service
    r = webhook_service.gonder(claims["tenant_id"], "deneme", {"olay": "deneme", "mesaj": "PVQuant webhook denemesi"}, webhook_id=webhook_id)
    if not r:
        raise HTTPException(404, "webhook yok ya da pasif")
    _denetim.kaydet("musteri", "webhook_dene", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="webhook", nesne_id=webhook_id,   # v2.602 (F4-H)
                    ayrinti={"http_durum": (r[0] or {}).get("durum") if isinstance(r[0], dict) else None})
    return r[0]


# ---- v2.289: kuruluşlar arası veri paylaşımı (Tablo 3.5 satır 6) ----

class PaylasimIstek(BaseModel):
    plant_id: str
    hedef_eposta: str
    izinler: list[str]
    bitis: str | None = None      # "YYYY-MM-DD" (o gün dâhil)
    takma_ad: str | None = None


@app.get("/v1/paylasimlar", tags=["Yönetim"])
def paylasim_listesi(claims=Depends(gecerli_kullanici)):
    from pvquant.services import paylasim_service
    return paylasim_service.listele(claims["tenant_id"])


@app.post("/v1/paylasimlar", tags=["Yönetim"], status_code=201)
def paylasim_ekle(p: PaylasimIstek, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import paylasim_service
    if plant_service.getir(claims["tenant_id"], p.plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        r = paylasim_service.paylas(claims["tenant_id"], claims["sub"], {"id": p.plant_id},
                                   p.hedef_eposta, p.izinler, p.bitis, p.takma_ad)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "paylasim_ekle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="paylasim", nesne_id=(r or {}).get("id") if isinstance(r, dict) else None,
                    ayrinti={"plant_id": p.plant_id, "hedef_eposta": p.hedef_eposta, "izinler": sorted(set(p.izinler or [])), "bitis": p.bitis})   # v2.602 (F4-H)
    return r


@app.delete("/v1/paylasimlar/{paylasim_id}", tags=["Yönetim"])
def paylasim_iptal(paylasim_id: str, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import paylasim_service
    if not paylasim_service.iptal(claims["tenant_id"], claims["sub"], paylasim_id):
        raise HTTPException(404, "paylaşım yok ya da zaten iptal")
    _denetim.kaydet("musteri", "paylasim_iptal", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="paylasim", nesne_id=paylasim_id)   # v2.602 (F4-H)
    return {"iptal": True}


@app.get("/v1/paylasimlar/{paylasim_id}/veri", tags=["Yönetim"])
def paylasim_veri(paylasim_id: str, tur: str, claims=Depends(gecerli_kullanici)):
    """Alınan paylaşımın verisi (tur: tahmin | karne | gerceklesen). Yalnız izin verilen kapsam."""
    from pvquant.services import paylasim_service
    f = {"tahmin": paylasim_service.paylasilan_tahmin, "karne": paylasim_service.paylasilan_karne,
         "gerceklesen": paylasim_service.paylasilan_gerceklesen}.get(tur)
    if f is None:
        raise HTTPException(422, "tur: tahmin | karne | gerceklesen")
    try:
        return f(claims["tenant_id"], paylasim_id)
    except PermissionError as e:
        raise HTTPException(403, str(e))


class SegmentIstek(BaseModel):

    segment: str
    uevcb: str | None = None
    dsg_kodu: str | None = None             # v2.539 (DK-258): DSG adı/kodu (beyan); aynı kod = aynı grup; "" temizler
    toplayici_portfoyu: bool | None = None  # v2.539 (DK-261): toplayıcı portföyünde → DSG dışı (DUY m.20(4))
    yek_g_kayitli: bool | None = None       # v2.540 (DK-612): YEK-G sisteminde kayıtlı (beyan) → Karar 14967 Ek sıra 17 eşiksiz arıza hatırlatması
    piyasa_katilimcisi: str | None = None   # v2.541 (DK-252): aynı kodlu santraller DSG hesabında tek üye; "" temizler
    lisans_yillik_uretim_mwh: float | None = None   # v2.541 (DK-804): lisansa dercedilen yıllık üretim miktarı (LDYEÜM, MWh); 0/None temizler
    gts_toplayici_adi: str | None = None    # v2.541 (DK-267): GTŞ/toplayıcı adı; UEVÇB kodu yoksa portföy KÜPST gruplaması bu ada göre; "" temizler
    # v2.543 (P9 hazırlık): depolama ünitesi beyanı — güç verilirse hepsi birlikte doğrulanır; güç None/0 → alanlar silinir
    depolama: dict | None = None


@app.put("/v1/plants/{plant_id}/segment")
def segment_ayarla(plant_id: str, p: SegmentIstek, claims=Depends(yazma_yetkisi())):
    """v2.260 — piyasa segmenti (YEKDEM / serbest / lisanssız …) ve UEVÇB kodu; params_json'a yazılır."""
    from pvquant.ext.turkiye.segment import Segment
    from pvquant.services import dengesizlik_service, plant_service
    try:
        seg = Segment(p.segment)
    except ValueError:
        raise HTTPException(422, f"segment: {[s.value for s in Segment]}")
    anahtarlar = {"segment": seg.value}
    if p.uevcb:
        anahtarlar["uevcb"] = p.uevcb.strip()[:32]
    if p.dsg_kodu is not None:   # v2.539: boş dize temizler
        anahtarlar["dsg_kodu"] = p.dsg_kodu.strip()[:32] or None
    if p.toplayici_portfoyu is not None:
        anahtarlar["toplayici_portfoyu"] = bool(p.toplayici_portfoyu)
    if p.yek_g_kayitli is not None:
        anahtarlar["yek_g_kayitli"] = bool(p.yek_g_kayitli)
    if p.piyasa_katilimcisi is not None:
        anahtarlar["piyasa_katilimcisi"] = p.piyasa_katilimcisi.strip()[:32] or None
    if p.lisans_yillik_uretim_mwh is not None:
        if p.lisans_yillik_uretim_mwh < 0:
            raise HTTPException(422, "lisans_yillik_uretim_mwh 0 ya da pozitif olmalı")
        anahtarlar["lisans_yillik_uretim_mwh"] = float(p.lisans_yillik_uretim_mwh) or None
    if p.gts_toplayici_adi is not None:
        anahtarlar["gts_toplayici_adi"] = p.gts_toplayici_adi.strip()[:64] or None
    if p.depolama is not None:   # v2.543 (P9)
        from pvquant.ext.turkiye import depolama as _dep
        try:
            anahtarlar.update(_dep.dogrula(p.depolama))
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
    eski_pj = dict((plant_service.getir(claims["tenant_id"], plant_id) or {}).get("params_json") or {})
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **anahtarlar)
    _ayar_izi("santral_segment", claims, plant_id, eski_pj, pj, ek={"istek": dict(anahtarlar)})   # v2.516 (#7); v2.602: eski/yeni + ayar damgası
    return {"params_json": {k: v for k, v in pj.items() if k in ("segment", "uevcb", "dsg_kodu", "toplayici_portfoyu", "yek_g_kayitli", "piyasa_katilimcisi", "lisans_yillik_uretim_mwh", "gts_toplayici_adi", "depolama_gucu_mw", "depolama_kapasite_mwh", "depolama_konfigurasyon", "depolama_uevcb", "depolama_kabul_tarihi", "depolama_butunlesik")}, **dengesizlik_service.segment_bilgisi(pj),
            "depolama": dengesizlik_service.segment_bilgisi(pj)["depolama"]}   # v2.543 (P9)


class KunyeTarihIstek(BaseModel):
    """v2.518 (P3a): santral künyesinin tarih alanları (params_json). Hepsi isteğe bağlı; None alanı siler. YYYY-MM-DD."""
    lisans_yururluk: str | None = None
    lisans_bitis: str | None = None
    kabul_tarihi: str | None = None
    isletmeye_giris: str | None = None
    police_bitis: str | None = None
    ced_karar_tarihi: str | None = None
    baglanti_anlasmasi: str | None = None
    cagri_mektubu_tarihi: str | None = None   # v2.541 (EK-2 DK-659): çağrı mektubuna hak kazanma tarihi (lisanssız rejim ölçütü)
    toplayici_giris: str | None = None
    toplayici_cikis: str | None = None
    yekdem_baslangic_yili: int | None = None
    tam_kabul_tarihi: str | None = None       # v2.524 (P3b): kurulu gücün tamamının kabulü (ilerleme raporu biter)
    isg_son_kontrol: str | None = None        # v2.524 (P3b): İSG periyodik kontrol (yılda bir)
    ortaklik_degisikligi: str | None = None   # v2.524 (P3b): Lisans Yön. m.57(2) 6 ay
    izin_iptali: str | None = None            # v2.524 (P3b): Lisans Yön. m.30(2) 2 ay


@app.get("/v1/plants/{plant_id}/takvim")
def takvim(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.518 (P3a) — piyasa ve mevzuat takvimi: yaklaşan son tarihler (segmente göre), aylık uzlaştırma/fatura zinciri (DUY m.132),
    günlük piyasa saatleri, künye tarihleri ve türeyenleri. Saf hesap ext/turkiye/takvim.py; EPİAŞ duyurusuyla değişebilir."""
    from pvquant.services import plant_service, takvim_service
    if not (7 <= gun <= 400):
        raise HTTPException(422, "gun 7–400 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return takvim_service.ozet({"id": str(row["id"]), "params_json": row.get("params_json"), "capacity_kwp": row.get("capacity_kwp")}, gun=gun, tenant_id=claims["tenant_id"])   # v2.524 (P3b): uyum + bakım


@app.put("/v1/plants/{plant_id}/kunye-tarihler")
def kunye_tarihler_ayarla(plant_id: str, p: KunyeTarihIstek, claims=Depends(yazma_yetkisi())):
    """v2.518 (P3a) — künye tarih alanları params_json'a yazılır (göç yok); türeyenler (lisans −6 ay, YEKDEM son yılı, poliçe) yanıtta."""
    from pvquant.services import plant_service, takvim_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        alanlar = takvim_service.kunye_dogrula(p.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, f"{e}: YYYY-MM-DD biçiminde tarih (YEKDEM başlangıç yılı 2005–2100) olmalı; bitiş yürürlükten önce olamaz")
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **alanlar)
    _denetim.kaydet("musteri", "santral_tarihler", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id,
                    ayrinti={k: v for k, v in alanlar.items()})   # v2.518 (P3a): yalnız tarih alanları, sır yok
    return {"kunye": takvim_service.ozet({"id": plant_id, "params_json": pj}, gun=7)["kunye"]}


class EakIstek(BaseModel):
    eak_kw: float | None = None                 # kalıcı EAK alanı (kW); None → AC tavanı/kurulu güç
    gecici_kw: float | None = None              # geçici kısıt (bakım/arıza), kW
    gecici_bitis: str | None = None             # YYYY-MM-DD (dâhil)
    kupst_n: float | None = None                # KÜPST katsayısı geçersiz kılma (verilmezse kural tablosu)
    kupst_tolerans: float | None = None         # KGÜP oranı (0–0,5) geçersiz kılma
    dengeleme_birimi: bool | None = None        # 29.10 (F-05): 15 dk dilimleme yalnız dengeleme birimi (DUY m.69(3))
    ariza_sayisi_ay: int | None = None          # 29.10 (v2.505, 04 #13): bu ay bildirilen arıza kaydı sayısı — KÜPST n katsayısı eşiğinde (kural tablosu) yükselir
    luy_istisna: bool | None = None             # 31.10 (v2.510, Ç3): tesis LÜY m.5(1)(ç),(d),(e) kapsamında → Karar 14907 Md.5, iletime bağlı lisanssızda KÜPST uygulanmaz
    pozisyon_kaynagi: str | None = None         # v2.517 (P2a): piyasa pozisyonu — program | uretim (üretildiği kadar satış) | sabit (baz yük MWh/saat)
    pozisyon_sabit_mwh: float | None = None     # v2.517 (P2a): pozisyon_kaynagi = sabit için saatlik MWh
    teminat_risk_katsayisi: float | None = None  # v2.522 (P2b): EPİAŞ dengesizlik teminatı risk katsayısı (değeri kaynakta yok; müşteri girer)
    kullanilabilirlik_sozlesme: float | None = None  # v2.533 (P8a): O&M sözleşmesindeki kullanılabilirlik eşiği (0,5–1); açık kWh/TL kıyas tabanı
    butce_kwh_yil: float | None = None            # v2.534 (P8b-1): finansal modeldeki yıllık bütçe (kWh); P-değeri kıyasında bütçe oranı
    pr_referans: float | None = None              # v2.542 (P8b-2): tasarım/sözleşme performans oranı (0,5–0,95); ölçülen havayla beklenen üretimin referansı
    temizlik_maliyeti_tl: float | None = None     # v2.545 (IH-090): bir modül temizliğinin maliyeti (TL); kirlenme kaybı tahminiyle karşılaştırılır
    son_temizlik_tarihi: str | None = None        # v2.546: son modül temizliği (YYYY-MM-DD); temiz referans PR bu tarihten sonraki açık günlere bağlanır
    dosya_yukleme_sikligi_gun: int | None = None  # v2.546: SCADA/sayaç dosyasını kaç günde bir yüklediğiniz (1–90); dosya tazelik eşiği iki katı


class EpiasIstek(BaseModel):
    epias_santral_id: int | None = None


@app.get("/v1/plants/{plant_id}/epias-uretim")
def epias_uretim_durum(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.278 — EPİAŞ gerçekleşen üretim akışının durumu (kimlik, santral eşlemesi, yazılan saat sayısı)."""
    from pvquant.services import epias_uretim_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return epias_uretim_service.durum(claims["tenant_id"], row)


@app.put("/v1/plants/{plant_id}/epias-uretim")
def epias_uretim_ayarla(plant_id: str, p: EpiasIstek, claims=Depends(yazma_yetkisi())):
    """v2.278 — Şeffaflık santral kimliğini (powerPlantId) eşle; null → eşlemeyi kaldır."""
    from pvquant.services import epias_uretim_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    eski = dict(row.get("params_json") or {})
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, epias_santral_id=p.epias_santral_id)
    _ayar_izi("epias_uretim_ayar", claims, plant_id, eski, pj)   # v2.602 (F4-H)
    row["params_json"] = pj
    return epias_uretim_service.durum(claims["tenant_id"], row)


@app.put("/v1/plants/{plant_id}/eak")
def eak_ayarla(plant_id: str, p: EakIstek, claims=Depends(yazma_yetkisi())):
    """v2.275 — EAK alanı (emre amade kapasite) + geçici kısıt + KÜPST katsayıları; params_json'a yazılır, KGÜP/toplayıcı çıktısı ve simülatör okur.
    v2.517 (P2a): piyasa pozisyonu ayarı (program | uretim | sabit MWh/saat) — uzlaştırma hesabının EDM tabanı."""
    from datetime import date as _d

    from pvquant.services import dengesizlik_service, kgup_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    kap = float(row["capacity_kwp"])
    an: dict = {}
    verilen = p.model_fields_set   # yalnız istekte GEÇEN alanlar değişir; null = temizle
    if "eak_kw" in verilen:
        if p.eak_kw is not None and not (0 < p.eak_kw <= kap):
            raise HTTPException(422, f"eak_kw 0–{kap:g} kW aralığında olmalı")
        an["eak_kw"] = float(p.eak_kw) if p.eak_kw is not None else None
    if "gecici_kw" in verilen or "gecici_bitis" in verilen:
        if p.gecici_kw and p.gecici_bitis:
            try:
                _d.fromisoformat(p.gecici_bitis)
            except ValueError:
                raise HTTPException(422, "gecici_bitis YYYY-MM-DD olmalı")
            if not (0 < p.gecici_kw <= kap):
                raise HTTPException(422, "gecici_kw aralık dışı")
            an["eak_gecici"] = {"kw": float(p.gecici_kw), "bitis": p.gecici_bitis}
        else:
            an["eak_gecici"] = None
    if p.kupst_n is not None:
        if not (0 <= p.kupst_n <= 0.2):
            raise HTTPException(422, "kupst_n 0–0,2")
        an["kupst_n"] = float(p.kupst_n)
    if p.kupst_tolerans is not None:
        if not (0 <= p.kupst_tolerans <= 0.5):
            raise HTTPException(422, "kupst_tolerans 0–0,5")
        an["kupst_tolerans"] = float(p.kupst_tolerans)
    if "dengeleme_birimi" in verilen:
        an["dengeleme_birimi"] = bool(p.dengeleme_birimi)
    if "luy_istisna" in verilen:
        an["luy_istisna"] = bool(p.luy_istisna)
    if "ariza_sayisi_ay" in verilen:
        if p.ariza_sayisi_ay is not None and not (0 <= p.ariza_sayisi_ay <= 999):
            raise HTTPException(422, "ariza_sayisi_ay 0–999")
        an["ariza_sayisi_ay"] = int(p.ariza_sayisi_ay) if p.ariza_sayisi_ay is not None else None
    if "pozisyon_kaynagi" in verilen:   # v2.517 (P2a)
        if p.pozisyon_kaynagi is not None and p.pozisyon_kaynagi not in ("program", "uretim", "sabit"):
            raise HTTPException(422, "pozisyon_kaynagi program, uretim ya da sabit olmalı")
        an["pozisyon_kaynagi"] = p.pozisyon_kaynagi
    if "pozisyon_sabit_mwh" in verilen:
        if p.pozisyon_sabit_mwh is not None and not (0 <= p.pozisyon_sabit_mwh <= kap / 1000.0):
            raise HTTPException(422, f"pozisyon_sabit_mwh 0–{kap / 1000.0:g} MWh/saat aralığında olmalı")
        an["pozisyon_sabit_mwh"] = float(p.pozisyon_sabit_mwh) if p.pozisyon_sabit_mwh is not None else None
    if "teminat_risk_katsayisi" in verilen:   # v2.522 (P2b)
        if p.teminat_risk_katsayisi is not None and not (0 < p.teminat_risk_katsayisi <= 10):
            raise HTTPException(422, "teminat_risk_katsayisi 0–10 aralığında olmalı")
        an["teminat_risk_katsayisi"] = float(p.teminat_risk_katsayisi) if p.teminat_risk_katsayisi is not None else None
    if "kullanilabilirlik_sozlesme" in verilen:   # v2.533 (P8a)
        if p.kullanilabilirlik_sozlesme is not None and not (0.5 <= p.kullanilabilirlik_sozlesme <= 1.0):
            raise HTTPException(422, "kullanilabilirlik_sozlesme 0,5–1,0 aralığında olmalı")
        an["kullanilabilirlik_sozlesme"] = float(p.kullanilabilirlik_sozlesme) if p.kullanilabilirlik_sozlesme is not None else None
    if "butce_kwh_yil" in verilen:   # v2.534 (P8b-1)
        if p.butce_kwh_yil is not None and not (0 < p.butce_kwh_yil <= kap * 8760):
            raise HTTPException(422, "butce_kwh_yil 0 ile kurulu güç × 8760 arasında olmalı")
        an["butce_kwh_yil"] = float(p.butce_kwh_yil) if p.butce_kwh_yil is not None else None
    if "pr_referans" in verilen:   # v2.542 (P8b-2)
        if p.pr_referans is not None and not (0.5 <= p.pr_referans <= 0.95):
            raise HTTPException(422, "pr_referans 0,5–0,95 aralığında olmalı")
        an["pr_referans"] = float(p.pr_referans) if p.pr_referans is not None else None
    if "temizlik_maliyeti_tl" in verilen:   # v2.545 (IH-090)
        if p.temizlik_maliyeti_tl is not None and not (0 <= p.temizlik_maliyeti_tl <= 1e8):
            raise HTTPException(422, "temizlik_maliyeti_tl 0 ile 100.000.000 TL arasında olmalı")
        an["temizlik_maliyeti_tl"] = float(p.temizlik_maliyeti_tl) if p.temizlik_maliyeti_tl else None
    if "son_temizlik_tarihi" in verilen:   # v2.546
        if p.son_temizlik_tarihi:
            from datetime import date as _d
            try:
                t = _d.fromisoformat(p.son_temizlik_tarihi)
            except ValueError as e:
                raise HTTPException(422, "son_temizlik_tarihi YYYY-AA-GG biçiminde olmalı") from e
            if t > _d.today():
                raise HTTPException(422, "son_temizlik_tarihi gelecekte olamaz")
            an["son_temizlik_tarihi"] = t.isoformat()
        else:
            an["son_temizlik_tarihi"] = None
    if "dosya_yukleme_sikligi_gun" in verilen:   # v2.546
        if p.dosya_yukleme_sikligi_gun is not None and not (1 <= p.dosya_yukleme_sikligi_gun <= 90):
            raise HTTPException(422, "dosya_yukleme_sikligi_gun 1–90 arasında olmalı")
        an["dosya_yukleme_sikligi_gun"] = int(p.dosya_yukleme_sikligi_gun) if p.dosya_yukleme_sikligi_gun else None
    eski_pj = dict(row.get("params_json") or {})
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **an)
    _ayar_izi("eak_ayar", claims, row["id"], eski_pj, pj, ek={"istek": dict(an)})   # v2.516 (#7); v2.602: eski/yeni + ayar damgası
    row["params_json"] = pj
    return {"eak_bugun": kgup_service.eak_etkin(row, pd.Timestamp.now(tz=PIYASA_TZ).date()),
            "eak_kw": pj.get("eak_kw"), "eak_gecici": pj.get("eak_gecici"), "kupst_n": pj.get("kupst_n"), "kupst_tolerans": pj.get("kupst_tolerans"),
            "dengeleme_birimi": bool(pj.get("dengeleme_birimi")), "ariza_sayisi_ay": int(pj.get("ariza_sayisi_ay") or 0),
            "luy_istisna": bool(pj.get("luy_istisna")),
            "pozisyon": dengesizlik_service.pozisyon_ayari(pj),   # v2.517 (P2a)
            "teminat_risk_katsayisi": pj.get("teminat_risk_katsayisi"),   # v2.522 (P2b)
            "kullanilabilirlik_sozlesme": pj.get("kullanilabilirlik_sozlesme"),   # v2.533 (P8a)
            "butce_kwh_yil": pj.get("butce_kwh_yil"),   # v2.534 (P8b-1)
            "pr_referans": pj.get("pr_referans"),   # v2.542 (P8b-2)
            "temizlik_maliyeti_tl": pj.get("temizlik_maliyeti_tl"),   # v2.545 (IH-090)
            "son_temizlik_tarihi": pj.get("son_temizlik_tarihi"), "dosya_yukleme_sikligi_gun": pj.get("dosya_yukleme_sikligi_gun")}   # v2.546


def _toplayici_yaniti(tenant_id: str, plant_id: str, gun: str | None, fmt: str, adim: int):
    from datetime import date, timedelta

    from pvquant.services import toplayici_service
    if fmt not in ("csv", "xlsx", "json") or adim not in (60, 15):
        raise HTTPException(422, "fmt csv|xlsx|json, adim 60|15")
    row = plant_service.getir(tenant_id, plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    g = date.fromisoformat(gun) if gun else (pd.Timestamp.now(tz=PIYASA_TZ).date() + timedelta(days=1))
    r = toplayici_service.uret(tenant_id, row, g, fmt, adim)
    if "hata" in r:
        raise HTTPException(409, r["hata"])
    return Response(content=r["icerik"], media_type=r["mime"], headers={"Content-Disposition": f'attachment; filename="{r["dosya_adi"]}"', "X-PVQ-Not": "toplayici sablonu"})


@app.get("/v1/plants/{plant_id}/toplayici")
def toplayici(plant_id: str, gun: str | None = None, fmt: str = "csv", adim: int = 60, claims=Depends(gecerli_kullanici)):
    """v2.275 — toplayıcı/DSG çıktısı (saatlik ya da 15 dk P10/P50/P90 MW + EAK); teslim kesimi öncesi koşudan."""
    return _toplayici_yaniti(claims["tenant_id"], plant_id, gun, fmt, adim)


@app.get("/v1/dis/santral/{plant_id}/toplayici", tags=["Dış API"])
def dis_toplayici(plant_id: str, gun: str | None = None, fmt: str = "csv", adim: int = 60, anahtar=Depends(api_anahtari("kgup:oku"))):
    """Toplayıcı/DSG program dosyası (P10/P50/P90 MW, EAK); adim=15 ile çeyrek saatlik. Gün verilmezse İstanbul yarını."""
    _dis_santral(anahtar, plant_id)
    return _toplayici_yaniti(anahtar["tenant_id"], plant_id, gun, fmt, adim)


# ---------------------------------------------------------------- v2.603 (F4-I): yeni dış uçlar -------------------------------------------------
@app.get("/v1/dis/santral/{plant_id}/tahmin-arsivi", tags=["Dış API"])
def dis_tahmin_arsivi(plant_id: str, hedef: str, yayin_oncesi: str | None = None, anahtar=Depends(api_anahtari("tahmin:oku"))):
    """v2.603 (F4-I): arşiv sorgusu — `hedef` saati için `yayin_oncesi` anında yayımlanmış son koşunun değeri ve künyesi (panel ucuyla aynı servis;
    geriye bakışlı koşular dönmez). Yoksa 404 `kosu_yok`."""
    from pvquant.services import forecast_service
    try:
        h = pd.Timestamp(hedef); y = pd.Timestamp(yayin_oncesi) if yayin_oncesi else None
    except (ValueError, TypeError):
        raise _dis_hata(422, "istek_gecersiz", "hedef / yayin_oncesi ISO 8601 zaman olmalı") from None
    if pd.isna(h) or (yayin_oncesi and pd.isna(y)):
        raise _dis_hata(422, "istek_gecersiz", "hedef / yayin_oncesi ISO 8601 zaman olmalı")
    row = _dis_santral(anahtar, plant_id)
    out = forecast_service.yayimlanmis_kosu(anahtar["tenant_id"], plant_id, h, y)
    if out is None:
        raise _dis_hata(404, "kosu_yok", "bu saat için o anda yayımlanmış koşu yok")
    return {"schema_version": DIS_API_SEMA, "santral_id": str(row["id"]), **out}


@app.get("/v1/dis/santral/{plant_id}/kalite", tags=["Dış API"])
def dis_kalite(plant_id: str, bas: str | None = None, bit: str | None = None, anahtar=Depends(api_anahtari("veri_kalitesi:oku"))):
    """v2.603 (F4-I): veri kalitesi özeti — bas–bit Türkiye günü (dâhil, en çok 92 gün; verilmezse son 7 gün): saat sayısı bayrağa ve niteliğe göre
    (kalite sözlüğü), tazelik (son geçerli ölçüm), ölçüm künyesi (kaynaklar, son geliş). Uydurma yok: olmayan saat sayılmaz."""
    from datetime import date as _d
    from datetime import datetime as _dt
    from datetime import timedelta as _td
    from zoneinfo import ZoneInfo

    from sqlalchemy import text as _text

    from pvquant.db import tenant_baglami as _tb
    from pvquant.services import kalite_sozlugu as _ks
    row = _dis_santral(anahtar, plant_id)
    tz = ZoneInfo(PIYASA_TZ)
    try:
        b1 = _d.fromisoformat(bit) if bit else _dt.now(tz).date()
        b0 = _d.fromisoformat(bas) if bas else b1 - _td(days=6)
    except ValueError:
        raise _dis_hata(422, "istek_gecersiz", "bas/bit YYYY-MM-DD olmalı") from None
    if b0 > b1 or (b1 - b0).days > 91:
        raise _dis_hata(422, "istek_gecersiz", "aralık en çok 92 gün ve bas ≤ bit olmalı")
    t0 = _dt.combine(b0, _dt.min.time(), tzinfo=tz); t1 = _dt.combine(b1 + _td(days=1), _dt.min.time(), tzinfo=tz)
    with _tb(anahtar["tenant_id"]) as s:
        # bayraksız satır «valid» SAYILMAZ (uzlaştırma süzgeci flag IN (...) ile uyumlu): ayrı anahtar, niteliği «gecersiz»
        rows = s.execute(_text("SELECT COALESCE(flag, 'bayraksiz') AS flag, count(*) AS n FROM scada_hourly WHERE plant_id = :p AND ts_utc >= :a AND ts_utc < :b GROUP BY 1"),
                         {"p": plant_id, "a": t0, "b": t1}).mappings().all()
        kw = s.execute(_text("SELECT max(alinma_zamani), array_agg(DISTINCT COALESCE(kaynak, 'bilinmiyor')) FROM scada_hourly WHERE plant_id = :p AND ts_utc >= :a AND ts_utc < :b"),
                       {"p": plant_id, "a": t0, "b": t1}).first()   # künye: pencere içi
        son = s.execute(_text(f"SELECT max(ts_utc) FROM scada_hourly WHERE plant_id = :p AND {_ks.sql_kosulu('tazelik')}"), {"p": plant_id}).scalar()   # tazelik: santralın son geçerli ölçümü
    bayrak = {r["flag"]: int(r["n"]) for r in rows}
    nitelik: dict[str, int] = {}
    for f, n in bayrak.items():
        ad = (_ks.Nitelik.GECERSIZ if f == "bayraksiz" else _ks.flag_nitelik(f)).value; nitelik[ad] = nitelik.get(ad, 0) + n   # satır var ama bayraksız → gecersiz (eksik = satır yok)
    beklenen = int((t1 - t0).total_seconds() // 3600)
    olcumlu = sum(bayrak.values())
    return {"schema_version": DIS_API_SEMA, "santral_id": str(row["id"]), "santral": row["name"], "bas": b0.isoformat(), "bit": b1.isoformat(),
            "beklenen_saat": beklenen, "olcumlu_saat": olcumlu, "eksik_saat": max(0, beklenen - olcumlu),
            "uzlastirmaya_uygun_saat": sum(n for f, n in bayrak.items() if f in _ks.gecerli_flaglar("uzlastirma")),
            "bayrak": bayrak, "nitelik": nitelik, "tazelik": _ks.tazelik_durumu(son),
            "kunye": {"son_gecerli_olcum": (son.isoformat() if son else None), "son_alinma": (kw[0].isoformat(timespec="seconds") if kw and kw[0] else None),
                      "kaynaklar": sorted(kw[1] or []) if kw else []},
            "sozluk_surumu": _ks.SOZLUK_SURUMU,
            "not": "Saatler SCADA satırlarıdır; eksik saat 0 sayılmaz. Künye (kaynaklar, son geliş) pencere içindir; tazelik ve son geçerli ölçüm santralın tamamından. "
                   "Nitelik etiketleri kalite sözlüğünden (GET /v1/sozluk/kalite)."}


@app.get("/v1/dis/portfoyler", tags=["Dış API"])
def dis_portfoyler(tarih: str | None = None, n: int = 50, sonraki: str | None = None, anahtar=Depends(api_anahtari("portfoy:oku"))):
    """v2.603 (F4-I): kiracının portföyleri (tarihte geçerli olanlar, üye sayısıyla). İmleçli sayfalama: `sonraki` bir önceki yanıttan; kimlik sıralı."""
    from datetime import date as _d

    from pvquant.services import portfoy_varlik_service as pv
    try:
        t = _d.fromisoformat(tarih) if tarih else None
    except ValueError:
        raise _dis_hata(422, "istek_gecersiz", "tarih YYYY-MM-DD olmalı") from None
    n = max(1, min(int(n), 200))
    hepsi = sorted(pv.portfoyler(anahtar["tenant_id"], tarih=t), key=lambda x: str(x["id"]))
    if sonraki:
        hepsi = [x for x in hepsi if str(x["id"]) > sonraki]
    sayfa = hepsi[:n]
    return {"schema_version": DIS_API_SEMA, "tarih": (t or pd.Timestamp.now(tz=PIYASA_TZ).date()).isoformat(),
            "portfoyler": [{"id": str(x["id"]), "ad": x["ad"], "tur": x["tur"], "kurulus_ad": x.get("kurulus_ad"), "dsg_kodu": x.get("dsg_kodu"),
                            "gecerli_bas": str(x.get("gecerli_bas") or ""), "gecerli_bit": (str(x["gecerli_bit"]) if x.get("gecerli_bit") else None),
                            "uye_sayisi": x.get("uye_sayisi")} for x in sayfa],
            "sonraki": (str(sayfa[-1]["id"]) if len(hepsi) > n else None)}


@app.get("/v1/dis/portfoy/{portfoy_id}/finansal-etki", tags=["Dış API"])
def dis_portfoy_finansal_etki(portfoy_id: str, donem: str | None = None, uretim: str | None = None, anahtar=Depends(api_anahtari("finans:oku"))):
    """v2.603 (F4-I): portföy finansal etkisi (dönem YYYY-MM-DD | YYYY-Wnn | YYYY-MM | YYYY-QN | YYYY; verilmezse son tam ay): santral satırları, toplam,
    nitelik; meta damgaları (kural sicili sha/sürümü, DSG fiyat sha, hesap durumu, çıktı sürümü). Santral sonuçları gece kaydından (≤36 sa), yoksa anında.
    Tutarlar yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir."""
    from pvquant.services import portfoy_finans_service as pfs
    ur = _fe_uretim(uretim)
    try:
        out = pfs.donem(anahtar["tenant_id"], portfoy_id, donem, ur)
    except ValueError as e:
        raise _dis_hata(422, "istek_gecersiz", str(e)) from None
    if out.get("durum") == "portfoy_yok":
        raise _dis_hata(404, "portfoy_yok", "portföy yok")
    if out.get("durum") != "ok":
        raise _dis_hata(409, "hesaplanamadi", out.get("not") or out.get("durum") or "hesaplanamadı")
    m = out.get("meta") or {}
    return {"schema_version": DIS_API_SEMA, "portfoy_id": str(portfoy_id), "portfoy": out.get("portfoy"), "donem": out.get("donem"), "uyelik_tarihi": out.get("uyelik_tarihi"),
            "santral": out.get("santral"), "santraller": out.get("santraller"), "bilesenler": out.get("bilesenler"), "toplam": out.get("toplam"), "toplam_dsg": out.get("toplam_dsg"),
            "kaynaklar": out.get("kaynaklar"), "dsg_durum": out.get("dsg_durum"),
            "meta": {"surum": m.get("surum"), "cikti_surumu": m.get("cikti_surumu"), "hesap_durumu": m.get("hesap_durumu"), "kural_sicili_sha": m.get("kural_sicili_sha"),
                     "kural_sicili_surumu": m.get("kural_sicili_surumu"), "dsg_fiyat_sha16": ((m.get("girdi") or {}).get("dsg_fiyat") or {}).get("sha16"),
                     "girdi_sha16": (m.get("girdi") or {}).get("sha16"), "uretim_girdisi": m.get("uretim_girdisi")},
            "not": "Tutarlar yürürlükteki kuralla yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir. Artı = santral lehine."}


@app.get("/v1/kurallar")
def kurallar_tablosu(tarih: str | None = None, segment: str | None = "lisansli_serbest", claims=Depends(gecerli_kullanici)):
    """29.10.2026 (F-01) — uzlaştırma kuralı ve parametre sürüm tablosu (salt okunur): tarih verilirse o günün kuralı, yoksa tüm satırlar."""
    from pvquant.ext.turkiye import kurallar as kr
    from pvquant.services import dengesizlik_service
    if tarih:
        try:
            from datetime import date as _d
            return dengesizlik_service.kural_ozeti(segment, _d.fromisoformat(tarih))
        except ValueError:
            raise HTTPException(422, "tarih YYYY-MM-DD olmalı")
    from pvquant.ext.turkiye import kural_sicili as _ks
    bugun = pd.Timestamp.now(tz=PIYASA_TZ).date()
    return {"segment": segment, "satirlar": kr.tablo(segment),
            "sicil": _ks.ozet(bugun),                                         # v2.600 (F4-F): sürüm, sha16, doğrulama dağılımı, yürürlükte / gelecek
            "bugun": dengesizlik_service.kural_ozeti(segment, bugun)}         # arayüz sabitleri buradan (k/l, V, B, AFL, KÜPST, DSG, takvim)


@app.get("/v1/kurallar/sicil")
def kurallar_sicili(claims=Depends(gecerli_kullanici)):
    """v2.600 (F4-F): mevzuat kural sicilinin tamamı (kod içi, sürümlü) + son anlık görüntüler (kural_sicili_anlik)."""
    from pvquant.ext.turkiye import kural_sicili as _ks
    from pvquant.services import kural_sicili_service as _kss
    anlik, hata = [], None
    try:
        anlik = _kss.anlik_listesi(10)
    except Exception as e:   # noqa: BLE001 — tablo yoksa/okunamazsa sicil yine döner
        hata = type(e).__name__
    return {"surum": _ks.SURUM, "sha16": _ks.sicil_sha16(), "kayitlar": _ks.tablo(), "dogrulama_durumlari": list(_ks.DOGRULAMA), "anlik": anlik, "anlik_hata": hata}


@app.get("/v1/plants/{plant_id}/dengesizlik/geri-test")
def dengesizlik_geri_test(plant_id: str, gun: int = 365, claims=Depends(gecerli_kullanici)):
    """v2.503 (F-07) — uzlaştırma kalemleri geri testi: aylık tablo, karşı-olgu sütunları (2026 kuralı tüm döneme, V = 100), mekanizma kırılımı.
    Varsayımsal yeniden hesap; EPİAŞ uzlaştırma sonucu değildir."""
    from pvquant.services import backtest_service, plant_service
    if not (30 <= gun <= 730):
        raise HTTPException(422, "gun 30-730")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return backtest_service.maliyet_geri_test(claims["tenant_id"], {"id": str(row["id"]), "params_json": row.get("params_json")}, gun=gun)


@app.get("/v1/plants/{plant_id}/dengesizlik")
def dengesizlik(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.259 — karnenin TL dili: PVQuant programı vs referans program uzlaştırma kalemleri (EDT + KÜPST, yürürlükteki kural), aylık + toplam."""
    from pvquant.services import dengesizlik_service, plant_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14–365 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return dengesizlik_service.simulasyon(claims["tenant_id"], {"id": str(row["id"]), "params_json": row.get("params_json")}, gun=gun)


@app.get("/v1/plants/{plant_id}/dengesizlik/saatlik")
def dengesizlik_saatlik(plant_id: str, gun: int = 90, fmt: str = "json", n: int = 48, uretim: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.517 (P2a, B12) — saatlik uzlaştırma dökümü: program (bildirilen/öneri), pozisyon, gerçekleşen, sapma, fiyat, yön, EDT borç/alacak,
    KÜPSM, KÜPST, kural sürümü, durum. fmt=csv (;-ayraçlı, BOM'lu) ve fmt=xlsx (Saatlik + Aylar) indirilir; fmt=json son n satırı döner.
    Yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir."""
    from fastapi.responses import Response

    from pvquant.services import dengesizlik_service, plant_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14–365 aralığında olmalı")
    if fmt not in ("json", "csv", "xlsx"):
        raise HTTPException(422, "fmt json, csv ya da xlsx olmalı")
    if uretim is not None and uretim not in ("scada", "sayac"):   # v2.526 (P4a-2): verilmezse santral ayarı
        raise HTTPException(422, "uretim scada ya da sayac olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    df, ozet = dengesizlik_service.dokum(claims["tenant_id"], {"id": str(row["id"]), "params_json": row.get("params_json")}, gun=gun, uretim=uretim)
    ad = f"pvquant_uzlastirma_saatlik_{row['name'].replace(' ', '_')}_{gun}g"
    if fmt == "csv":
        return Response(dengesizlik_service.dokum_csv(df), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{ad}.csv"'})
    if fmt == "xlsx":
        b = dengesizlik_service.dokum_xlsx(df, f"{row['name']} — saatlik uzlaştırma dökümü, son {gun} gün (yeniden hesap)", ozet.get("aylar"))
        return Response(b, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{ad}.xlsx"'})
    son = df.tail(max(1, min(int(n), 2000)))
    return {"satir": int(len(df)), "kolonlar": list(df.columns), "not": dengesizlik_service.dokum_notu(df),   # v2.520: YEKDEM'de 25 sütun
            "program": ozet.get("program"), "toplam": ozet.get("toplam"), "uretim_kaynak": ozet.get("uretim_kaynak"),   # v2.526 (P4a-2)
            "talimat_saat": ozet.get("talimat_saat", 0), "talimat_notu": ozet.get("talimat_notu"),   # v2.539 (DK-056)
            "satirlar": [{k: (None if (isinstance(v, float) and v != v) else (float(v) if hasattr(v, "item") and not isinstance(v, str) else v)) for k, v in r.items()}
                         for r in son.to_dict(orient="records")]}


class OlayIstek(BaseModel):
    """v2.521 (P1a): olay kaydı. baslangic/bitis ISO (Türkiye saati ya da saat dilimli); etkilenen_kw boş = tesisin tamamı."""
    tur: str
    baslangic: str
    bitis: str | None = None
    etkilenen_kw: float | None = None
    neden: str | None = None
    eak_gerekcesi: str | None = None
    kanit: str | None = None
    bildirim_zamani: str | None = None  # v2.541 (DK-741): acil kesmede şebeke işletmecisinin sona erme bildirimi (LÜY m.21(8))
    talimat_mw: float | None = None     # v2.541 (DK-743): YAL/YAT talimat miktarı (MW), kayıt


class OlayGuncelle(BaseModel):
    bitis: str | None = None
    etkilenen_kw: float | None = None
    neden: str | None = None
    eak_gerekcesi: str | None = None
    kanit: str | None = None
    durum: str | None = None            # iptal için
    bildirim_zamani: str | None = None  # v2.541
    talimat_mw: float | None = None     # v2.541


@app.get("/v1/plants/{plant_id}/olaylar")
def olaylar(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.521 (P1a) — olay kaydı: son N günün olayları, açık olaylar, aylık arıza sayacı (olay ∨ elle; eşik 30), bugünkü EAK etkisi,
    dâhilî bilgi 1 saat hatırlatması (Karar 14967, yürürlük belirsiz)."""
    from pvquant.services import olay_service
    if not (7 <= gun <= 400):
        raise HTTPException(422, "gun 7–400 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return olay_service.ozet(claims["tenant_id"], {"id": str(row["id"]), "name": row["name"], "capacity_kwp": row["capacity_kwp"], "ac_limit_kw": row.get("ac_limit_kw"),
                                                    "params_json": row.get("params_json")}, gun=gun)


@app.get("/v1/plants/{plant_id}/olaylar.csv")
def olaylar_csv(plant_id: str, gun: int = 365, claims=Depends(gecerli_kullanici)):
    """v2.521 (P1a) — hasar / sigorta dosyası: olay listesi CSV (; ayraç, BOM)."""
    from pvquant.services import olay_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    metin = olay_service.csv_metni(olay_service.listele(claims["tenant_id"], str(row["id"]), max(7, min(gun, 400)), iptal_dahil=True), row["name"])
    return Response(metin, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="pvquant_olay_kaydi_{row["name"].replace(" ", "_")}.csv"'})


@app.post("/v1/plants/{plant_id}/olaylar", status_code=201)
def olay_ekle(plant_id: str, p: OlayIstek, claims=Depends(yazma_yetkisi())):
    from pvquant.services import olay_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        o = olay_service.ekle(claims["tenant_id"], {"id": str(row["id"]), "capacity_kwp": row["capacity_kwp"], "ac_limit_kw": row.get("ac_limit_kw")}, p.model_dump(), olusturan=claims["sub"])
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "olay_ekle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="olay", nesne_id=o["id"],
                    ayrinti={"tur": o["tur"], "baslangic": o["baslangic"], "bitis": o["bitis"], "etkilenen_kw": o["etkilenen_kw"], "plant_id": plant_id})
    return o


@app.put("/v1/plants/{plant_id}/olaylar/{olay_id}")
def olay_guncelle(plant_id: str, olay_id: str, p: OlayGuncelle, claims=Depends(yazma_yetkisi())):
    from pvquant.services import olay_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        o = olay_service.guncelle(claims["tenant_id"], {"id": str(row["id"]), "capacity_kwp": row["capacity_kwp"], "ac_limit_kw": row.get("ac_limit_kw")}, olay_id, p.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, str(e))
    if o is None:
        raise HTTPException(404, "olay yok")
    _denetim.kaydet("musteri", "olay_guncelle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="olay", nesne_id=o["id"],
                    ayrinti={k: v for k, v in p.model_dump(exclude_unset=True).items()})
    return o


@app.get("/v1/plants/{plant_id}/mutabakat")
def mutabakat_ozet(plant_id: str, donem: str | None = None, surum: str | None = None, uretim: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.522 (P2b-1) — EPİAŞ uzlaştırma bildirimiyle kalem kalem mutabakat: yüklenmiş dönemler + seçilen dönemin bildirim ↔ PVQuant tablosu.
    Yeniden hesap EPİAŞ sonucu değildir. v2.526 (P4a-2): uretim=scada|sayac — gerçekleşen üretim kaynağı (verilmezse santral ayarı)."""
    from pvquant.services import mutabakat_service
    if surum is not None and surum not in mutabakat_service.SURUMLER:
        raise HTTPException(422, "surum on ya da nihai olmalı")
    if uretim is not None and uretim not in ("scada", "sayac"):
        raise HTTPException(422, "uretim scada ya da sayac olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        return mutabakat_service.ozet(claims["tenant_id"], {"id": str(row["id"]), "name": row["name"], "params_json": row.get("params_json")}, donem=donem, surum=surum, uretim=uretim)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/plants/{plant_id}/mutabakat", status_code=201)
def mutabakat_yukle(plant_id: str, donem: str | None = None, surum: str | None = None, dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """v2.522 (P2b-1) — EPYS «Uzlaştırma Bildirimi» dosyası (CSV/XLSX, ≤2 MB): kalemler tanınır ve dönem + sürümle saklanır (her yükleme yeni sürüm,
    silme yok). Dönem/sürüm verilmezse dosyadan okunur."""
    from pvquant.services import mutabakat_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    b = dosya.file.read()
    try:
        k = mutabakat_service.kaydet(claims["tenant_id"], {"id": str(row["id"])}, b, dosya.filename or "bildirim.csv", donem=donem, surum=surum, yukleyen=claims.get("sub"))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "mutabakat_yukle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"donem": k["donem"], "surum": k["surum"], "kalem": k["kalem_sayisi"], "dosya": (dosya.filename or "")[:80], "sha256": k["sha256"][:16]})
    return k


@app.post("/v1/plants/{plant_id}/mutabakat/saatlik", status_code=201)
def mutabakat_saatlik_yukle(plant_id: str, donem: str | None = None, dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """v2.527 (P2b-2) — EPYS saatlik detay dosyası (Uzlaştırma Dönemi Detay / Dengesizlik Uzlaştırma / KÜPST Detay; XLSX ya da CSV, ≤5 MB): saatlik PTF, SMF,
    UEVM, KUDÜP/BUDÜP, EDM/EDT, KÜPSM/KÜPST satırları dönemle saklanır (her yükleme yeni sürüm, silme yok). Dönem verilmezse dosyadan."""
    from pvquant.services import saatlik_detay_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    b = dosya.file.read()
    try:
        k = saatlik_detay_service.kaydet(claims["tenant_id"], {"id": str(row["id"])}, b, dosya.filename or "saatlik.xlsx", donem=donem, yukleyen=claims.get("sub"))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "mutabakat_saatlik_yukle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"donem": k["donem"], "saat": k["saat"], "ekran": k["kaynak_ekran"], "dosya": (dosya.filename or "")[:80], "sha256": k["sha256"][:16]})
    return k


@app.get("/v1/plants/{plant_id}/mutabakat/saatlik")
def mutabakat_saatlik(plant_id: str, donem: str | None = None, uretim: str | None = None, fmt: str = "json", claims=Depends(gecerli_kullanici)):
    """v2.527 (P2b-2) — eş kapsamlı saatlik kıyas: yüklü EPYS saatlik detayı ↔ PVQuant dökümü yalnız ortak saatlerde (fiyat, üretim, program, EDT, KÜPST;
    fark ayrıştırması; en büyük farklı saatler). fmt=csv saatlik satırları indirir. donem verilmezse son yüklenen dönem."""
    from datetime import datetime, timedelta

    from fastapi.responses import Response

    from pvquant.services import mutabakat_service, saatlik_detay_service
    if fmt not in ("json", "csv"):
        raise HTTPException(422, "fmt json ya da csv olmalı")
    if uretim is not None and uretim not in ("scada", "sayac"):
        raise HTTPException(422, "uretim scada ya da sayac olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    plant = {"id": str(row["id"]), "name": row["name"], "params_json": row.get("params_json")}
    try:
        if donem is None:
            y = saatlik_detay_service.yuklemeler(claims["tenant_id"], plant["id"], 1)
            donem = y[0]["donem"] if y else (datetime.now(mutabakat_service.IST).date().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        d = mutabakat_service._donem(donem)
        k = saatlik_detay_service.kiyas(claims["tenant_id"], plant, d, uretim)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if fmt == "csv":
        _denetim.kaydet("musteri", "mutabakat_saatlik_indir", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={"donem": k["donem"]})
        ad = f"pvquant_saatlik_kiyas_{mutabakat_service._sade(row['name']).replace(' ', '_')}_{k['donem']}.csv"
        return Response(saatlik_detay_service.kiyas_csv(k), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{ad}"'})
    k["yuklemeler_tum"] = saatlik_detay_service.yuklemeler(claims["tenant_id"], plant["id"])
    return k


def _sayac_plant(row) -> dict:
    return {"id": str(row["id"]), "name": row["name"], "capacity_kwp": row["capacity_kwp"], "ac_limit_kw": row.get("ac_limit_kw"), "params_json": row.get("params_json")}


@app.get("/v1/plants/{plant_id}/sayac")
def sayac_ozet(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.523 (P4a) — Sayaç izleme: veri geliş beklentisi (Ölçüm Sist. Yön. m.8), eksik saat, 12. gün 17:30 geri sayımı, SCADA ↔ sayaç günlük farkı,
    kaynak/nitelik etiketi, yükleme tarihçesi; lisanssızda SCADA durumu ve Karar 14909 bedel göstergesi."""
    from pvquant.services import sayac_service
    if not (7 <= gun <= 400):
        raise HTTPException(422, "gun 7–400 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return sayac_service.ozet(claims["tenant_id"], _sayac_plant(row), gun=gun)


@app.get("/v1/plants/{plant_id}/sayac.csv")
def sayac_csv(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.523 (P4a) — günlük SCADA ↔ sayaç tablosu CSV (; ayraç, BOM)."""
    from pvquant.services import sayac_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    f = sayac_service.fark(claims["tenant_id"], _sayac_plant(row), gun=max(7, min(gun, 400)))
    return Response(sayac_service.fark_csv(f, row["name"]), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="pvquant_sayac_scada_{sayac_service._sade(row["name"]).replace(" ", "_")}_{f["pencere_gun"]}g.csv"'})   # ASCII ad (Türkçe karakter başlıkta olmaz)


@app.post("/v1/plants/{plant_id}/sayac", status_code=201)
def sayac_yukle(plant_id: str, kaynak: str = "osos", dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """v2.523 (P4a) — OSOS / MASS / EPYS sayaç dışa aktarımı (CSV/XLSX, ≤8 MB): saatlik veriş kWh (dakikalık dilimler toplanır), nitelik etiketi;
    aynı saat + kaynak yeniden yüklenirse güncellenir (düzeltme), yükleme tarihçesi tutulur."""
    from pvquant.services import sayac_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    b = dosya.file.read()
    try:
        k = sayac_service.kaydet(claims["tenant_id"], {"id": str(row["id"])}, b, dosya.filename or "sayac.csv", kaynak=kaynak, yukleyen=claims.get("sub"))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "sayac_yukle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"kaynak": kaynak, "n_saat": k["n_saat"], "bas": k["bas"], "bit": k["bit"], "dosya": (dosya.filename or "")[:80], "sha256": k["sha256"][:16]})
    return k


@app.put("/v1/plants/{plant_id}/sayac-ayar")
def sayac_ayar(plant_id: str, p: SayacAyarIstek, claims=Depends(yazma_yetkisi())):
    """v2.523 (P4a) — sayaç türü (15 dk endeks / diğer), lisanssız SCADA durumu, kopukluk başlangıcı, uzaktan açma yeteneği, aylık sistem kullanım bedeli."""
    from pvquant.services import sayac_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        an = sayac_service.ayar_dogrula(p.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, f"{e} alanı geçersiz")
    if an:
        eski_pj = dict(row.get("params_json") or {})
        pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **an)
        row["params_json"] = pj
        _ayar_izi("sayac_ayar", claims, row["id"], eski_pj, pj, ek={"istek": dict(an)})   # v2.602: eski/yeni + ayar damgası
    return sayac_service.ozet(claims["tenant_id"], _sayac_plant(row), gun=30)


@app.get("/v1/plants/{plant_id}/yekdem")
def yekdem_ozet(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.520 (P5a) — YEKDEM katmanı: fiyat rejimi (Cetvel I / 7189; işletmeye giriş tarihinden ya da tarifedeki seçim), bugünün YEK fiyatı
    (Cetvel I: ¢ × günün TCMB alış kuru; 7189: ayın EPİAŞ ilanı + yerli katkı, USD band konumu), kur arşivi durumu ve YEK Yön. m.23(6) saat
    işareti (belirsiz; yalnız lisanslı YEKDEM + tarife YEKDEM). Yeniden hesaptır; EPİAŞ YEKDEM uzlaştırması değildir."""
    from pvquant.services import plant_service, yekdem_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14–365 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return yekdem_service.ozet(claims["tenant_id"], {"id": str(row["id"]), "params_json": row.get("params_json")}, gun=gun)


@app.get("/v1/piyasa/durum")
def piyasa_durum(claims=Depends(gecerli_kullanici)):
    """v2.258 — EPİAŞ entegrasyonunun durumu: kimlik var mı, son fiyat saati, senaryo değerleri."""
    from pvquant.services import piyasa_service
    return piyasa_service.durum()


@app.get("/v1/epias/uevcb-ara")
def epias_uevcb_ara(kurulus: str, claims=Depends(gecerli_kullanici)):
    """v2.513 (04 #14 kalan) — EPİAŞ Şeffaflık organization-list + uevcb-list ile UEVÇB adayları (kuruluş adı araması; yalnız okuma).
    Kimlik tanımlı değilse 503; arama en az 3 karakter."""
    from pvquant.services import piyasa_service
    if len(kurulus.strip()) < 3:
        raise HTTPException(422, "kurulus en az 3 karakter")
    try:
        r = piyasa_service.uevcb_ara(kurulus.strip())
    except Exception as e:   # noqa: BLE001 — EPİAŞ erişim hatası panele düz metin
        raise HTTPException(502, f"EPİAŞ erişilemedi: {str(e)[:120]}")
    if r["durum"] == "kimlik_yok":
        raise HTTPException(503, "EPİAŞ kimliği tanımlı değil")
    return r


@app.get("/v1/piyasa/fiyat")
def piyasa_fiyat(bas: str, bitis: str, itibariyle: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.258 — saatlik PTF/SMF/yön (UTC); eksik saatler 'senaryo' kaynaklı döner. v2.601: `itibariyle` → o andaki fiyat sürümü (M6)."""
    from pvquant.services import piyasa_service
    idx = pd.date_range(pd.Timestamp(bas, tz=PIYASA_TZ), pd.Timestamp(bitis, tz=PIYASA_TZ) + pd.Timedelta(hours=23), freq="h").tz_convert("UTC")
    if len(idx) > 24 * 400:
        raise HTTPException(422, "en fazla 400 gun")
    t = _zaman_cozumle(itibariyle) if itibariyle else None
    f = piyasa_service.fiyatlar(idx, itibariyle=t) if t else piyasa_service.fiyatlar(idx)
    return {"satirlar": [{"ts": ts.isoformat(), "ptf": _kw(r.ptf), "smf": _kw(r.smf), "yon": r.yon, "kaynak": r.kaynak} for ts, r in f.iterrows()],
            "epias_saat": int((f.kaynak == "epias").sum()), "senaryo_saat": int((f.kaynak == "senaryo").sum()),
            "sha16": piyasa_service.fiyat_sha16(f), "itibariyle": (t.isoformat(timespec="seconds") if t else None)}


@app.get("/v1/piyasa/fiyat-surumleri")
def piyasa_fiyat_surumleri(ts: str, n: int = 20, claims=Depends(gecerli_kullanici)):
    """v2.601 (F4-G): bir saatin fiyat sürümleri (en yeni önce): gün öncesi PTF → gece tam satır → düzeltmeler; alinma zamanıyla."""
    from pvquant.services import piyasa_service
    t = _zaman_cozumle(ts)
    return {"ts": t.isoformat(timespec="seconds"), "surumler": piyasa_service.surum_tarihcesi(t, max(1, min(int(n), 200)))}


@app.get("/v1/plants/{plant_id}/saglik")
def saglik(plant_id: str, gun: int = 800, claims=Depends(gecerli_kullanici)):
    """v2.256 — bozunma (%/yıl, YoY) ve performans eğilimi; POA yoksa model-normalize verimle."""
    from pvquant.services import plant_service, saglik_service
    if not (60 <= gun <= 2000):
        raise HTTPException(422, "gun 60-2000 araliginda olmali")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return saglik_service.saglik(claims["tenant_id"], {"id": str(row["id"]), "capacity_kwp": float(row["capacity_kwp"])}, gun=gun)


@app.get("/v1/plants/{plant_id}/hijyen")
def hijyen(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.254 — kırpma/kısıntı sayımı ve 'kısıtlama olmasaydı' kaybı (beklenen = son koşu fiziği)."""
    from pvquant.services import hijyen_service
    if not (7 <= gun <= 365):
        raise HTTPException(422, "gun 7-365 araliginda olmali")
    return hijyen_service.ozet(claims["tenant_id"], plant_id, gun=gun)


@app.get("/v1/plants/{plant_id}/guvenilirlik")
def guvenilirlik(plant_id: str, gun: int = 60, claims=Depends(gecerli_kullanici)):
    """v2.271 — kantil güvenilirliği (P10/P50/P90 gözlenen vs nominal), PIT histogramı, keskinlik ve aralık skoru; ham ↔ kalibre."""
    from pvquant.services import guvenilirlik_service, plant_service
    if not (14 <= gun <= 180):
        raise HTTPException(422, "gun 14-180 araliginda olmali")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return guvenilirlik_service.hesapla(claims["tenant_id"], {"id": str(row["id"]), "capacity_kwp": float(row["capacity_kwp"])}, gun=gun)


@app.get("/v1/plants/{plant_id}/backtest")
def backtest(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.253 — konformal katmanın kayan-başlangıç geriye dönük sınavı (sızıntısız)."""
    from pvquant.services import backtest_service, plant_service
    if not (30 <= gun <= 180):
        raise HTTPException(422, "gun 30-180 araliginda olmali")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    st = {"id": str(row["id"]), "capacity_kwp": float(row["capacity_kwp"])}
    r = backtest_service.konformal_backtest(claims["tenant_id"], st, gun=gun)
    r["kova_sinav"] = backtest_service.ufuk_kova_sinavi(claims["tenant_id"], st, gun=gun)   # v2.297
    return r


@app.get("/v1/plants/{plant_id}/kayma")
def kayma(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.253 — eğitim (arşiv) / servis (tahmin) meteo kayması: PSI/KS/sapma; 24 s önbellek."""
    from pvquant.services import kayma_service, plant_service
    if not (7 <= gun <= 60):
        raise HTTPException(422, "gun 7-60 araliginda olmali")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return kayma_service.kayma_denetimi({"id": str(row["id"]), "lat": row["lat"], "lon": row["lon"]}, gun=gun)


@app.get("/v1/plants/{plant_id}/konformal")
def konformal(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.252 — bant kalibrasyon ayarı (q̂ özeti). Yoksa {'aktif': False} — UI 'düzeltme yok' der."""
    from pvquant.services import konformal_service
    ayar = konformal_service.ayar_getir(claims["tenant_id"], plant_id)
    if ayar is None:
        return {"aktif": False}
    return {"aktif": True, "alpha": ayar["alpha"], "n": ayar["n"], "pencere_gun": ayar["pencere_gun"],
            "hesap_zamani": ayar["hesap_zamani"], "ort_q_kw": ayar["ort_q"],
            "kova_ort_q_kw": ayar.get("kova_ort_q"),   # v2.296: ufuk kovası başına ortalama q̂
            "q_hat": {k: v for k, v in ayar["q_hat"].items() if k != "_genel"}}


@app.get("/v1/plants/{plant_id}/pr")
def pr(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.249 — Dalga 1.4: IEC 61724-1 performans orani (olcumden). POA olcumu
    yoksa 'poa_yok' — GHI ile uydurulmaz (tire ilkesi)."""
    from pvquant.services import pr_service
    if not (7 <= gun <= 365):
        raise HTTPException(422, "gun 7-365 araliginda olmali")
    return pr_service.pr_karti(claims["tenant_id"], plant_id, gun=gun)


@app.get("/v1/plants/{plant_id}/skill")
def skill(plant_id: str, bucket: str = "0-24", gun: int = 120,
          claims=Depends(gecerli_kullanici)):
    """v2.75-A — karne kapisi. Toplulastirma Streamlit dogruluk.py'nin
    KOPYASI (iki panel ayni sayiyi soyler): kova filtresi -> mape.mean(),
    date.nunique(), skill_vs_naive.dropna().mean() (zaten yuzde saklanir).
    naif_wmape v2.95'te tablodan okunur (sartname S4: olcum, turetme degil);
    migration-oncesi eski satirlar icin v2.76 turetmesi yedek kalir. Bos
    karne 200 + bos gunluk doner — 'birikiyor' durumunu istemci anlatir.
    """
    from pvquant.services import forecast_service
    if not (1 <= gun <= 365):
        raise HTTPException(422, "gun 1-365 araliginda olmali")
    sk = forecast_service.skill_gecmisi(claims["tenant_id"], plant_id, gun=gun)
    kova = sk[sk["horizon_bucket"] == bucket] if not sk.empty else sk
    sv = kova["skill_vs_naive"].dropna() if len(kova) else []
    # v2.247 (Dalga 1.2): SFA sozlugu — kapasiteye normalize ortalamalar; kolon
    # yoksa (eski sahte df / migration oncesi) ya da tum satirlar NULL ise None.
    def _ort(kol):
        if not len(kova) or kol not in kova:
            return None
        v = kova[kol].dropna()
        return _kw(v.mean()) if len(v) else None
    def _opt(r, kol):
        v = r.get(kol) if hasattr(r, "get") else None
        return None if v is None or pd.isna(v) else _kw(v)
    # v2.248 (Dalga 1.3): bant sinavi ozeti — gun ortalamalari; hicbir gun dolu
    # degilse None (UI tire + 'birikiyor'). crps_n = crps/kapasite degil: kapasite bu
    # kapida yok, kW olarak verilir; bant_n zaten kapasiteye normalize.
    def _ol():
        d = {k: _ort(k) for k in ("pinball_p10", "pinball_p50", "pinball_p90", "crps", "picp80", "kapsama_p10", "kapsama_p90", "bant_n")}
        d["gun_sayisi"] = int(kova["picp80"].notna().sum()) if len(kova) and "picp80" in kova else 0
        return d
    return {
        "kova": bucket,
        "nmae_ort": _ort("nmae"), "nrmse_ort": _ort("nrmse"), "nmbe_ort": _ort("nmbe"),
        "cliper_wmape_ort": _ort("cliper_wmape"), "cliper_ustunluk_pct": _ort("skill_vs_cliper"),   # v2.279 (Yang 2019 referansı)
        "olasiliksal": _ol(),
        "gun_sayisi": int(kova["date"].nunique()) if len(kova) else 0,
        "wmape_ort": _kw(kova["mape"].mean()) if len(kova) else None,
        "naife_ustunluk_pct": _kw(sv.mean()) if len(sv) else None,
        "ilk_tarih": kova["date"].min().date().isoformat() if len(kova) else None,
        "son_tarih": kova["date"].max().date().isoformat() if len(kova) else None,
        "gunluk": [
            {"tarih": r["date"].date().isoformat(), "kova": r["horizon_bucket"],
             "wmape": _kw(r["mape"]),
             # v2.95: SAKLANAN naif oncelikli (sartname S4). Eski satirlar
             # icin v2.76 turetmesi yedek — ayni ozdeslik: skill=100*(1-mape/
             # naif) => naif = mape/(1-skill/100). Ikisi de yoksa null.
             "naif_wmape": _naif_wmape(r),
             "nmae": _opt(r, "nmae"), "nrmse": _opt(r, "nrmse"), "nmbe": _opt(r, "nmbe")}
            for _, r in kova.iterrows()],
    }


class TarifeIstek(BaseModel):
    tarife: dict | None = None      # None → kaldır


@app.get("/v1/plants/{plant_id}/kullanilabilirlik")
def kullanilabilirlik_uc(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.281 — kullanılabilirlik (zaman/enerji tabanlı, otomatik arıza tespiti; olay günlüğü yok)."""
    from pvquant.services import kullanilabilirlik_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return kullanilabilirlik_service.hesapla(claims["tenant_id"], row, gun=max(7, min(gun, 365)))


@app.get("/v1/plants/{plant_id}/kayip-ayrisimi")
def kayip_ayrisimi_uc(plant_id: str, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.533 (P8a; IH-087): gerçekleşen kayıp ayrışımı — nedene göre saat / kWh / TL (satış fiyatıyla), EPI; beklenen = fizik modeli."""
    from pvquant.services import kayip_ayrisimi_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return kayip_ayrisimi_service.hesapla(claims["tenant_id"], row, gun=max(7, min(gun, 365)))


@app.get("/v1/plants/{plant_id}/p-degerleri")
def p_degerleri_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.534 (P8b-1; IH-098/099): yıl yıl P50/P75/P90/P99 serisi (bozunma dâhil, biçim etiketli) ve gerçekleşen kıyası (hava düzeltmesiz)."""
    from pvquant.services import pdeger_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return pdeger_service.hesapla(claims["tenant_id"], row)


class SensorlerIstek(BaseModel):
    sensorler: list[dict]   # v2.542 (P8b-2, IH-092): tür, ölçüm, marka_model, seri_no, sinif, kalibrasyon_tarihi, kalibrasyon_periyodu_ay, not


def _sensorler_yaniti(row: dict, bugun=None) -> dict:
    from pvquant.services import performans_service as ps
    sens = ps.sensor_durumlari(ps.sensorler_oku(row.get("params_json")), bugun)
    return {"sensorler": sens, "isinim": ps.isinim_kaynagi(sens, bugun), "turler": ps.SENSOR_TURLERI, "olcumler": ps.OLCUMLER,
            "siniflar": list(ps.SINIFLAR), "varsayilan_periyot_ay": ps.KALIBRASYON_PERIYOT_AY, "yaklasan_gun": ps.KALIBRASYON_YAKLASAN_GUN, "not": ps.IEC_NOTU}


@app.get("/v1/plants/{plant_id}/sensorler")
def sensorler_oku_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.542 (P8b-2; IH-092): sensör envanteri + kalibrasyon vadesi (türetilir) + ışınım kaynağı özeti."""
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return _sensorler_yaniti(row)


@app.put("/v1/plants/{plant_id}/sensorler")
def sensorler_ayarla(plant_id: str, p: SensorlerIstek, claims=Depends(yazma_yetkisi())):
    """v2.542 (P8b-2; IH-092): envanteri bütünüyle değiştirir (en çok 20 sensör); vade saklanmaz, türetilir."""
    from pvquant.services import performans_service as ps
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if len(p.sensorler) > 20:
        raise HTTPException(422, "en çok 20 sensör")
    try:
        temiz = [ps.sensor_dogrula(s) for s in p.sensorler]
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, sensorler=temiz)
    _denetim.kaydet("musteri", "sensor_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"sensor_sayisi": len(temiz), "olcumler": sorted({s["olcum"] for s in temiz})})
    row["params_json"] = pj
    return _sensorler_yaniti(row)


@app.get("/v1/plants/{plant_id}/performans")
def performans_uc(plant_id: str, ay: int = 12, claims=Depends(gecerli_kullanici)):
    """v2.542 (P8b-2; IH-083/099/104): ölçülen düzlem-içi ışınım ve hücre sıcaklığıyla beklenen üretim, EPI, üç referans (tahmin / beklenen / P50),
    ışınım endeksi (yalnız yatay sensörde) ve hava düzeltmeli P50. Beklenen tasarım simülasyonu değildir; model çekirdeğine girmez."""
    from pvquant.services import performans_service
    if not (1 <= ay <= 36):
        raise HTTPException(422, "ay 1–36 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return performans_service.ozet(claims["tenant_id"], row, ay=ay)


@app.get("/v1/plants/{plant_id}/depolama")
def depolama_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.543 (P9 hazırlık; IH-109/111/112/113): depolama ünitesi beyanı, dengeleme birimi eşiği (DUY m.22, 30 MW), emre amadelik eşiği (DUY m.81/A,
    %85/%80; ölçüm yöntemi belirsiz), ayrı UEVÇB notu, 7189 Ek-1 (e) notu ve SMF çözünürlüğü. Hesap yok; beyan ve kural parametreleri."""
    from pvquant.ext.turkiye import depolama
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j
        pj = _j.loads(pj)
    return {**depolama.ozet(pj), "dayanaklar": list(depolama.DAYANAKLAR)}


@app.get("/v1/plants/{plant_id}/kirlenme")
def kirlenme_uc(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.544 (dalga 3 kalanı; IH-090/092): açık-gök tabanlı kirlenme göstergesi — ölçülen düzlem-içi ışınım / açık-gök modeli (açık saatler),
    günlük endeks, 30 açık gün eğimi, açık gün PR'ıyla çapraz okuma (sensör mü modül mü), son yağış. Kirlenme kaybı hesaplanmaz; göstergedir."""
    from pvquant.services import kirlenme_service
    if not (30 <= gun <= 365):
        raise HTTPException(422, "gun 30–365 aralığında olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return kirlenme_service.ozet(claims["tenant_id"], row, gun=gun)


class VeriYoluIstek(BaseModel):
    tur: str | None = None            # v2.544 (P4b hazırlık): hedef veri yolu; None → beyan silinir
    saglayici: str | None = None
    periyot_dk: int | None = None
    salt_okuma_onayi: bool | None = None
    not_: str | None = Field(default=None, alias="not")
    baglanti: dict | None = None     # v2.545: {host, port, birim} — Modbus TCP/SunSpec sınaması için
    ornekleme_acik: bool | None = None   # v2.546: sahibin «düzenli veri çekişini başlat» kararı (yalnız Modbus + bağlantı + onay ile geçerli)
    startdt_onayi: bool | None = None    # v2.548 (Aşama 0, H2): IEC 104 STARTDT yalnız sahibin «ayrı istemci yuvası tanımlandı» onayıyla
    iec104: dict | None = None           # v2.554 (S4): {ca, sinir, parametreler{k,w,t0..t3,ca_boy,ioa_boy,cot_boy}}


@app.get("/v1/plants/{plant_id}/veri-yolu")
def veri_yolu_oku(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.544 (P4b hazırlık; IH-023): etkin veri yolları (son geliş), hedef yol beyanı ve her yol için hazırlık kontrol listesi. Protokol/bulut API bağlı değildir."""
    from pvquant.services import veri_yolu_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return veri_yolu_service.ozet(claims["tenant_id"], row)


@app.put("/v1/plants/{plant_id}/veri-yolu")
def veri_yolu_ayarla(plant_id: str, p: VeriYoluIstek, claims=Depends(yazma_yetkisi())):
    """v2.544 (P4b hazırlık): hedef veri yolu beyanı (tür, sağlayıcı, periyot, salt-okuma onayı); params_json.veri_yolu."""
    from pvquant.services import veri_yolu_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj0 = row.get("params_json") or {}
    if isinstance(pj0, str):
        import json as _j
        pj0 = _j.loads(pj0)
    eski = pj0.get("veri_yolu") if isinstance(pj0.get("veri_yolu"), dict) else {}
    try:
        an = veri_yolu_service.dogrula({"tur": p.tur, "saglayici": p.saglayici, "periyot_dk": p.periyot_dk, "salt_okuma_onayi": p.salt_okuma_onayi, "not": p.not_, "baglanti": p.baglanti,
                                        "ornekleme_acik": p.ornekleme_acik, "startdt_onayi": p.startdt_onayi, "iec104": p.iec104,
                                        "nokta_tablosu": (eski.get("nokta_tablosu") if eski.get("tur") == p.tur else None)})   # v2.554: tablo ayrı uçtan; tür aynıysa korunur
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if eski.get("tur") == p.tur and eski.get("bulut_kimlik") and isinstance(an.get("veri_yolu"), dict):   # v2.556 (K1): kimlik aynası (gizli yok) tür aynıysa korunur
        an["veri_yolu"]["bulut_kimlik"] = eski["bulut_kimlik"]
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **an)
    _denetim.kaydet("musteri", "veri_yolu_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti=an)
    row["params_json"] = pj
    return veri_yolu_service.ozet(claims["tenant_id"], row)


class BulutSinamaIstek(BaseModel):
    saglayici: str                         # v2.547: fusionsolar | solaredge
    kimlik: dict = {}                      # kullanici/sistem_kodu ya da api_anahtari — SAKLANMAZ
    bolge: str | None = None               # FusionSolar bölge sunucusu


@app.post("/v1/plants/{plant_id}/veri-yolu/bulut-sinama")
def veri_yolu_bulut_sinama(plant_id: str, p: BulutSinamaIstek, claims=Depends(yazma_yetkisi())):
    """v2.547 (P4b-3): inverter bulutu bağlantı sınaması — kimlik gövdede gelir, yalnız sınama süresince tutulur, yazılmaz; sonuç (anahtarsız) beyana ve
    denetim izine düşer. Yalnız hedef «inverter_bulut_api» ve onay varken."""
    from pvquant.services import bulut_sinama_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j
        pj = _j.loads(pj)
    vy = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    if not vy or vy.get("tur") != "inverter_bulut_api":
        raise HTTPException(422, "bulut sınaması yalnız hedeflenen veri kaynağı inverter bulutu API iken yapılır")
    sonuc = bulut_sinama_service.sina(p.saglayici, p.kimlik or {}, bool(vy.get("salt_okuma_onayi")), p.bolge)
    plant_service.params_birlestir(claims["tenant_id"], plant_id, veri_yolu={**vy, "saglayici": vy.get("saglayici") or p.saglayici,
                                   "son_sinama": {"zaman": sonuc["zaman"], "durum": sonuc["durum"], "ozet": sonuc.get("ozet"), "aciklama": sonuc.get("aciklama"), "saglayici": p.saglayici}})
    _denetim.kaydet("musteri", "veri_yolu_sinama", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"durum": sonuc["durum"], "saglayici": p.saglayici, "ozet": sonuc.get("ozet")})   # kimlik bilgisi izine YAZILMAZ
    return sonuc


class BulutKimlikIstek(BaseModel):
    saglayici: str                         # v2.556 (Aşama 3, K1)
    kimlik: dict = {}                      # yalnız bu istekte düz metin; sınama geçerse zarf şifreli saklanır, hiçbir yere düz yazılmaz
    bolge: str | None = None
    onaylar: dict = {}                     # yalniz_okuma, sifreli_saklama → true
    dis_kimlik: str | None = None          # sağlayıcıdaki santral kodu (hesapta birden çok santral varsa)


class BulutKimlikAyar(BaseModel):
    cekis_acik: bool | None = None
    birim_dogrulandi: bool | None = None
    dis_kimlik: str | None = None


def _bulut_santral(claims, plant_id: str):
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j
        pj = _j.loads(pj)
    vy = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    if not vy or vy.get("tur") != "inverter_bulut_api":
        raise HTTPException(422, "bulut kimliği yalnız hedeflenen veri kaynağı inverter bulutu API iken saklanır")
    return row, vy


def _bulut_aynasi(claims, plant_id: str, vy: dict, saglayici: str | None = None) -> list[dict]:
    """params_json.veri_yolu.bulut_kimlik: gizli içermeyen ayna (aşama rozetleri ve bağlantı durumu DB'siz okur)."""
    from pvquant.services import bulut_kimlik_service as bk
    kay = bk.listele(claims["tenant_id"], plant_id)
    plant_service.params_birlestir(claims["tenant_id"], plant_id, veri_yolu={**vy, "saglayici": vy.get("saglayici") or saglayici, "bulut_kimlik": bk.params_ozeti(kay)})
    return kay


@app.get("/v1/plants/{plant_id}/bulut-kimlik")
def bulut_kimlik_durum(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.556/v2.557: kayıtlı bulut kimlikleri (maskeli etiket; gizli yok), kasa durumu, son çekiş, kota ve son ham saatler."""
    from pvquant.services import bulut_cekis_service as bc
    from pvquant.services import bulut_kimlik_service as bk
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    d = bk.durum(claims["tenant_id"], plant_id)
    d["ham_son"] = bc.ham_son(claims["tenant_id"], plant_id, None, 24)
    d["saglayici_alanlari"] = bc.saglayici_alanlari()   # v2.562: sağlayıcı → alan etiketleri, birim notu, günlük tavan
    d["alanlar"] = bc.ALANLAR; d["birim_notu"] = bc.BIRIM_NOTU; d["gunluk_tavan"] = bc.GUNLUK_TAVAN   # FusionSolar uyumluluğu
    from pvquant.services import bulut_oauth_service as bo
    d["oauth"] = {"uygulamalar": bo.uygulamalar_ozeti(), "son": bo.son(claims["tenant_id"], plant_id)}   # v2.564: sahip onayı yolu — yapılandırma durumu (gizli yok) ve son girişim
    return d


@app.post("/v1/plants/{plant_id}/bulut-kimlik")
def bulut_kimlik_kaydet(plant_id: str, p: BulutKimlikIstek, claims=Depends(yazma_yetkisi())):
    """v2.556 (K1): iki onay + sınama + santral seçimi → zarf şifreli kayıt. Yanıtta ve denetim izinde kimlik bilgisi yoktur."""
    from pvquant.services import bulut_kimlik_service as bk
    row, vy = _bulut_santral(claims, plant_id)
    onaylar = {**(p.onaylar or {}), "yalniz_okuma": bool((p.onaylar or {}).get("yalniz_okuma")) or bool(vy.get("salt_okuma_onayi"))}
    sonuc = bk.kaydet(claims["tenant_id"], row, p.saglayici, p.kimlik or {}, p.bolge, onaylar, claims["sub"], p.dis_kimlik)
    if sonuc.get("kaydedildi"):
        sn = sonuc.get("sinama") or {}; oz = {k: v for k, v in (sn.get("ozet") or {}).items() if k != "santraller"}   # kayıt sınamayla geçti → son_sinama (liste params'a yazılmaz)
        vy = {**vy, "son_sinama": {"zaman": sn.get("zaman"), "durum": "ok", "ozet": oz, "aciklama": None, "saglayici": p.saglayici}}
        _bulut_aynasi(claims, plant_id, vy, p.saglayici)
    _denetim.kaydet("musteri", "bulut_kimlik_kaydet", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"durum": sonuc["durum"], "saglayici": p.saglayici, "etiket": sonuc.get("etiket"), "dis_kimlik": sonuc.get("dis_kimlik")})   # kimlik bilgisi izine YAZILMAZ
    return sonuc


@app.patch("/v1/plants/{plant_id}/bulut-kimlik/{saglayici}")
def bulut_kimlik_ayar(plant_id: str, saglayici: str, p: BulutKimlikAyar, claims=Depends(yazma_yetkisi())):
    """v2.557 (K2): düzenli çekişi aç/kapat, birim doğrulandı işareti, sağlayıcı santral kodu. Geri alınabilir."""
    from pvquant.services import bulut_kimlik_service as bk
    row, vy = _bulut_santral(claims, plant_id)
    try:
        k = bk.ayarla(claims["tenant_id"], plant_id, saglayici, cekis_acik=p.cekis_acik, birim_dogrulandi=p.birim_dogrulandi, dis_kimlik=p.dis_kimlik)
    except bk.BirimKanitiYok as e:   # v2.565: «birim doğrulandı» kanıtsız işaretlenemez
        raise HTTPException(422, str(e)) from e
    if k is None:
        raise HTTPException(404, "bu sağlayıcı için kayıtlı kimlik yok")
    _bulut_aynasi(claims, plant_id, vy, saglayici)
    _denetim.kaydet("musteri", "bulut_kimlik_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"saglayici": saglayici, "cekis_acik": p.cekis_acik, "birim_dogrulandi": p.birim_dogrulandi, "dis_kimlik": p.dis_kimlik})
    return k


@app.post("/v1/plants/{plant_id}/bulut-kimlik/{saglayici}/birim-kiyas")
def bulut_birim_kiyas(plant_id: str, saglayici: str, dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """v2.565 (D2 adım 3): portalın saatlik dışa aktarımı (CSV: zaman, kwh) ile çekilen ham saatlerin birim/anlam kıyası; özet kayda yazılır, ham referans saklanmaz.
    «Birim doğrulandı» yalnız belge yorumu uyumlu bulununca işaretlenebilir."""
    from pvquant.services import bulut_birim_service as bb
    from pvquant.services import bulut_kimlik_service as bk
    from pvquant.services import pilot_service
    row, vy = _bulut_santral(claims, plant_id)
    kayit = next((k for k in bk.listele(claims["tenant_id"], plant_id) if k["saglayici"] == saglayici), None)
    if kayit is None:
        raise HTTPException(404, "bu sağlayıcı için kayıtlı kimlik yok")
    ham = dosya.file.read(5 * 1024 * 1024 + 1)
    if len(ham) > 5 * 1024 * 1024:
        raise HTTPException(413, "dışa aktarım dosyası en çok 5 MB")
    try:
        referans = pilot_service.referans_csv_oku(ham.decode("utf-8-sig", errors="replace"))
    except ValueError as e:
        raise HTTPException(422, f"dosya okunamadı: {e}") from e
    sonuc = bb.degerlendir(claims["tenant_id"], plant_id, saglayici, referans, aktor_id=claims["sub"], dosya=dosya.filename)
    sonuc["isaret_kaldirildi"] = bool(kayit.get("birim_dogrulandi")) and not sonuc["belge_uyumlu"] and bool(sonuc.get("kaydedildi"))   # 10.11 inceleme: çürütülen yorumla gölge yazımı sürmez
    _denetim.kaydet("musteri", "bulut_birim_kiyas", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"saglayici": saglayici, "sonuc": sonuc["sonuc"], "n_ortak": sonuc["n_ortak"], "n_uretimli": sonuc.get("n_uretimli"), "belge_uyumlu": sonuc["belge_uyumlu"],
                             "isaret_kaldirildi": sonuc["isaret_kaldirildi"], "dosya": dosya.filename})
    return sonuc


@app.delete("/v1/plants/{plant_id}/bulut-kimlik/{saglayici}")
def bulut_kimlik_sil(plant_id: str, saglayici: str, claims=Depends(yazma_yetkisi())):
    """v2.556 (K1): kimliği siler; çekiş durur. Ham saatler kalır (veri sahibinindir)."""
    from pvquant.services import bulut_kimlik_service as bk
    row, vy = _bulut_santral(claims, plant_id)
    n = bk.sil(claims["tenant_id"], plant_id, saglayici)
    if not n:
        raise HTTPException(404, "bu sağlayıcı için kayıtlı kimlik yok")
    _bulut_aynasi(claims, plant_id, vy, saglayici)
    _denetim.kaydet("musteri", "bulut_kimlik_sil", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={"saglayici": saglayici})
    return {"silindi": True, "saglayici": saglayici}


# ----------------------------------------------------------------------------- v2.564: sahip onayı (OAuth) — Sungrow iSolarCloud, SolarEdge site sahibi
class BulutOAuthBaslat(BaseModel):
    saglayici: str
    bolge: str | None = None
    onaylar: dict = {}                     # yalniz_okuma, sifreli_saklama → true


@app.post("/v1/plants/{plant_id}/bulut-kimlik/oauth/baslat")
def bulut_oauth_baslat(plant_id: str, p: BulutOAuthBaslat, claims=Depends(yazma_yetkisi())):
    """v2.564: iki onay + kasa + platform uygulaması → tek kullanımlık state ve sağlayıcının onay sayfası adresi. Yanıtta gizli yok; state denetim izine yazılmaz."""
    from pvquant.services import bulut_oauth_service as bo
    row, vy = _bulut_santral(claims, plant_id)
    onaylar = {**(p.onaylar or {}), "yalniz_okuma": bool((p.onaylar or {}).get("yalniz_okuma")) or bool(vy.get("salt_okuma_onayi"))}
    sonuc = bo.baslat(claims["tenant_id"], row, p.saglayici, p.bolge, onaylar, claims["sub"])
    _denetim.kaydet("musteri", "bulut_oauth_baslat", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"durum": sonuc["durum"], "saglayici": p.saglayici, "bolge": sonuc.get("bolge")})   # yetki adresi (state taşır) izine YAZILMAZ
    return sonuc


@app.get("/v1/bulut/oauth/{saglayici}/geri-donus")
def bulut_oauth_geri_donus(saglayici: str, request: Request):
    """v2.564: sağlayıcının yönlendirmesi — kimliksiz gelir; santral/kiracı tek kullanımlık state'ten bulunur. Kod sunucuda belirteçle değiştirilir ve
    kasaya yazılır; tarayıcı panele yalnız DURUM KODUyla döner. Kod/belirteç hiçbir yanıt, günlük ya da izde yok."""
    from fastapi.responses import RedirectResponse

    from pvquant.services import bulut_kimlik_service as bk
    from pvquant.services import bulut_oauth_service as bo
    sorgu = {k: v for k, v in request.query_params.items() if k in ("code", "state", "external_id", "site_id", "error", "error_description")}
    sonuc = bo.geri_donus(saglayici, sorgu)
    plant_id = sonuc.get("plant_id"); tenant_id = sonuc.get("tenant_id")
    if plant_id and tenant_id:
        if sonuc.get("durum") in ("tamam", "secim_bekliyor"):
            try:   # ayna: aşama rozetleri ve bağlantı durumu (kaydet ucuyla aynı yazım)
                row = plant_service.getir(tenant_id, plant_id) or {}
                vy = dict(((row.get("params_json") or {}).get("veri_yolu")) or {})
                kay = bk.listele(tenant_id, plant_id)
                vy = {**vy, "saglayici": vy.get("saglayici") or saglayici, "bulut_kimlik": bk.params_ozeti(kay),
                      "son_sinama": {"zaman": sonuc.get("zaman"), "durum": "ok", "ozet": {"santral_sayisi": len(sonuc.get("santraller") or []) or 1, "uc": "oauth"}, "aciklama": None, "saglayici": saglayici}}
                plant_service.params_birlestir(tenant_id, plant_id, veri_yolu=vy)
            except Exception:   # noqa: BLE001 — ayna yazımı dönüşü engellemez; kayıt zaten kasada
                pass
        _denetim.kaydet("musteri", "bulut_oauth_donus", aktor_id=sonuc.get("aktor_id"), tenant_id=tenant_id, nesne_tur="plant", nesne_id=plant_id,
                        ayrinti={"durum": sonuc.get("durum"), "saglayici": saglayici, "etiket": sonuc.get("etiket_hesap"), "dis_kimlik": sonuc.get("dis_kimlik")})
    r = RedirectResponse(bo.yonlendirme(plant_id, saglayici, sonuc.get("durum") or "hata"), status_code=303)
    r.headers["Cache-Control"] = "no-store"
    return r


# ----------------------------------------------------------------------------- v2.560 (Aşama 4): pilot kapıları ve referans kıyası
class PilotKapiIstek(BaseModel):
    tamam: bool
    aciklama: str | None = None


@app.get("/v1/plants/{plant_id}/pilot")
def pilot_durum(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.560: pilot kapıları (G01–G10; kod kapıları testlerle, saha kapıları sahibin tarihli beyanıyla) ve son referans kıyası özeti."""
    from pvquant.services import pilot_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return pilot_service.durum(row)


@app.put("/v1/plants/{plant_id}/pilot/kapi/{kod}")
def pilot_kapi(plant_id: str, kod: str, p: PilotKapiIstek, claims=Depends(yazma_yetkisi())):
    """v2.560: saha kapısını sahibin beyanıyla kapat/aç (tarih, aktör, not). Kod kapıları elle değişmez."""
    from pvquant.services import pilot_service
    try:
        d = pilot_service.kapi_ayarla(claims["tenant_id"], plant_id, kod, p.tamam, p.aciklama, claims["sub"])
    except LookupError:
        raise HTTPException(404, "santral yok")
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "pilot_kapi", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id, ayrinti={"kod": kod.upper(), "tamam": p.tamam, "not": p.aciklama})
    return d


@app.post("/v1/plants/{plant_id}/pilot/referans")
def pilot_referans(plant_id: str, dosya: UploadFile = File(...), sinir: str = "inverter_ac", claims=Depends(yazma_yetkisi())):
    """v2.560: referans saatlik dışa aktarımı (CSV: zaman, kWh) ile gölge görünümdeki TAM saatlerin kıyası; özet santral ayarına yazılır, ham referans saklanmaz."""
    from pvquant.services import kaynak_secim_service as ks
    from pvquant.services import pilot_service
    if sinir not in ks.SINIR_ETIKET:
        raise HTTPException(422, "sinir geçersiz")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    ham = dosya.file.read(5 * 1024 * 1024 + 1)
    if len(ham) > 5 * 1024 * 1024:
        raise HTTPException(413, "referans dosyası en çok 5 MB")
    try:
        ref = pilot_service.referans_csv_oku(ham.decode("utf-8-sig", errors="replace"))
    except ValueError as e:
        raise HTTPException(422, str(e))
    k = pilot_service.referans_degerlendir(claims["tenant_id"], row, ref, sinir, claims["sub"], dosya.filename)
    _denetim.kaydet("musteri", "pilot_referans", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"sonuc": k["sonuc"], "n_ortak": k["n_ortak"], "tolerans_orani": k["tolerans_orani"], "dosya": dosya.filename, "sinir": sinir})
    return k


# ----------------------------------------------------------------------------- v2.561 (Aşama 6): saha toplayıcısı (edge) kimliği ve idempotent alım
class EdgeToplayiciIstek(BaseModel):
    ad: str = "saha toplayıcısı"


class EdgeOrnekler(BaseModel):
    ornekler: list[dict]
    toplayici_surum: str | None = None


def toplayici_anahtari(x_toplayici_anahtar: str = _Header(..., alias="X-Toplayici-Anahtar")):
    from pvquant.services import edge_service
    try:
        return edge_service.dogrula(x_toplayici_anahtar)
    except PermissionError as e:
        raise HTTPException(401, str(e))


@app.get("/v1/plants/{plant_id}/edge/toplayici")
def edge_toplayici_listele(plant_id: str, claims=Depends(gecerli_kullanici)):
    from pvquant.services import edge_service
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    return {"toplayicilar": edge_service.toplayici_listele(claims["tenant_id"], plant_id),
            "not": "Toplayıcı anahtarı tek santrala bağlıdır ve sunucuda yalnız özeti durur; iptal edilen anahtarla gelen veri reddedilir. Sunucu toplayıcıya komut göndermez."}


@app.post("/v1/plants/{plant_id}/edge/toplayici", status_code=201)
def edge_toplayici_olustur(plant_id: str, p: EdgeToplayiciIstek, claims=Depends(yazma_yetkisi())):
    """v2.561 (E2): toplayıcı kimliği üretir; anahtar yalnız bu yanıtta görünür."""
    from pvquant.services import edge_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    r = edge_service.toplayici_olustur(claims["tenant_id"], plant_id, p.ad)
    _denetim.kaydet("musteri", "edge_toplayici_olustur", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={"ad": r["ad"], "prefix": r["prefix"]})   # anahtar izine YAZILMAZ
    return r


@app.delete("/v1/plants/{plant_id}/edge/toplayici/{toplayici_id}")
def edge_toplayici_iptal(plant_id: str, toplayici_id: str, claims=Depends(yazma_yetkisi())):
    from pvquant.services import edge_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if not edge_service.toplayici_iptal(claims["tenant_id"], plant_id, toplayici_id):
        raise HTTPException(404, "etkin toplayıcı yok")
    _denetim.kaydet("musteri", "edge_toplayici_iptal", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={"toplayici_id": toplayici_id})
    return {"iptal": True, "toplayici_id": toplayici_id}


@app.post("/v1/edge/ornekler", tags=["Saha toplayıcısı"])
def edge_ornekler(p: EdgeOrnekler, t=Depends(toplayici_anahtari)):
    """v2.561 (E1): toplayıcı örnekleri (sıra numaralı, ≤500). İdempotent: aynı sıra + aynı içerik yinelenen, farklı içerik çatışma. ack_sira kalıcı yazım sonrası döner.
    Santral anahtardan gelir (gövdede santral yok). Sunucu yanıtı veri dışında hiçbir komut taşımaz."""
    from pvquant.services import edge_service
    plant = plant_service.getir(t["tenant_id"], t["plant_id"])
    if plant is None:
        raise HTTPException(404, "toplayıcının santralı yok")
    try:
        return edge_service.al(t, plant, p.ornekler)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/plants/{plant_id}/veri-yolu/iec104-nokta-tablosu")
def veri_yolu_nokta_tablosu(plant_id: str, dosya: UploadFile = File(...), claims=Depends(yazma_yetkisi())):
    """v2.554 (S4): IEC 104 nokta tablosu (CSV: ioa, alan, carpan[, ad][, tip]) → beyana yazılır; sınama ve düzenli çekiş bu tabloyla IOA'ları PVQuant alanlarına
    eşler. Yalnız hedef iec104 iken. Üretici dışa aktarımları (Sungrow, Huawei) önce bu beş kolona indirgenir."""
    from pvquant.services import iec104_nokta_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j
        pj = _j.loads(pj)
    vy = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    if not vy or vy.get("tur") != "iec104":
        raise HTTPException(422, "nokta tablosu yalnız hedeflenen veri kaynağı IEC 60870-5-104 iken yüklenir")
    try:
        metin = dosya.file.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
        tablo = iec104_nokta_service.csv_den(metin)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    plant_service.params_birlestir(claims["tenant_id"], plant_id, veri_yolu={**vy, "nokta_tablosu": tablo, "nokta_tablosu_kaynak": {"dosya": dosya.filename, "zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n": len(tablo)}})
    _denetim.kaydet("musteri", "veri_yolu_nokta_tablosu", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={"n": len(tablo), "dosya": dosya.filename})
    return {"n": len(tablo), "alanlar": sorted({t["alan"] for t in tablo}), "tablo": tablo[:50]}


@app.post("/v1/plants/{plant_id}/veri-yolu/sinama")
def veri_yolu_sinama(plant_id: str, claims=Depends(yazma_yetkisi())):
    """v2.545 (P4b ilk bağlayıcı): Modbus TCP/SunSpec bağlantı sınaması — sahibin tetiklediği, yalnız okuma (FC3), onay şart; sonuç denetim izine yazılır.
    Düzenli veri çekişi başlatmaz."""
    from pvquant.services import canli_alim_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j
        pj = _j.loads(pj)
    vy = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    if not vy or vy.get("tur") not in ("modbus_sunspec", "iec104"):
        raise HTTPException(422, "sınama yalnız hedeflenen veri kaynağı Modbus TCP / SunSpec ya da IEC 60870-5-104 iken yapılır")
    if not vy.get("baglanti"):
        raise HTTPException(422, "bağlantı ayarı (host, port) girilmedi")
    # v2.547: IEC 104 → yalnız ulaşılabilirlik, komut yok; v2.548 (H2): varsayılan yalnız TCP, STARTDT yalnız beyandaki sahip onayıyla; v2.554 (S4): onay + nokta tablosu → genel sorgulama
    sonuc = (canli_alim_service.sina_iec104(vy["baglanti"], bool(vy.get("salt_okuma_onayi")), startdt_onayi=bool(vy.get("startdt_onayi")), nokta_tablosu=vy.get("nokta_tablosu"), iec104_ayar=vy.get("iec104")) if vy["tur"] == "iec104"
             else canli_alim_service.sina(vy["baglanti"], bool(vy.get("salt_okuma_onayi"))))
    # 08.11 inceleme (faz 4): son sınama beyana yazılır — «ayar girildi» ile «sınama başarılı» ayrı aşamalardır; sayfa yenilenince kaybolmaz
    plant_service.params_birlestir(claims["tenant_id"], plant_id, veri_yolu={**vy, "son_sinama": {"zaman": sonuc["zaman"], "durum": sonuc["durum"], "ozet": sonuc.get("ozet"), "aciklama": sonuc.get("aciklama")}})
    _denetim.kaydet("musteri", "veri_yolu_sinama", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={"durum": sonuc["durum"], "hedef": sonuc.get("hedef"), "cihaz": sonuc.get("ozet")})
    return sonuc


@app.get("/v1/plants/{plant_id}/golge-saatlik")
def golge_saatlik(plant_id: str, bas: str | None = None, bit: str | None = None, sinir: str = "inverter_ac", claims=Depends(gecerli_kullanici)):
    """v2.550 (Aşama 1, D5): GÖLGE saatlik görünüm — kaynak_saatlik'ten seçilen saat (tamlık + kaynak önceliği, son revizyon) ile üretim serisindeki saat
    yan yana; fark kWh. Yalnız okuma; tahmin/doğruluk bu görünümü kullanmaz. Pencere en çok 31 gün, varsayılan son 7 gün."""
    from datetime import datetime as _dt
    from datetime import timedelta as _td
    from datetime import timezone as _tz

    from pvquant.services import kaynak_secim_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if sinir not in kaynak_secim_service.SINIR_ETIKET:
        raise HTTPException(422, "sinir inverter_ac | plant_gross_ac | pcc_net | settlement olmalı")
    try:
        b0 = _dt.fromisoformat(bas).astimezone(_tz.utc) if bas else None
        b1 = _dt.fromisoformat(bit).astimezone(_tz.utc) if bit else None
    except ValueError as e:
        raise HTTPException(422, "bas/bit ISO 8601 olmalı") from e
    if b0 is None or b1 is None:
        v0, v1 = kaynak_secim_service.varsayilan_pencere()
        b0, b1 = b0 or v0, b1 or v1
    if b1 <= b0 or (b1 - b0) > _td(days=31):
        raise HTTPException(422, "pencere 0–31 gün arasında olmalı")
    return {"bas": b0.isoformat(), "bit": b1.isoformat(), **kaynak_secim_service.golge_gorunum(claims["tenant_id"], row, b0, b1, sinir)}


@app.get("/v1/plants/{plant_id}/olay-adaylari")
def olay_adaylari(plant_id: str, saat: int = 72, claims=Depends(gecerli_kullanici)):
    """v2.555 (Aşama 5, V2): cihaz durumundan (canlı örnekler) olay adayları — arıza/alarm koşuları ve iletişim kopuklukları. Otomatik kayıt yok; liste bilgi amaçlı."""
    from pvquant.services import cihaz_olay_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if not (1 <= saat <= 24 * 14):
        raise HTTPException(422, "saat 1–336 arasında olmalı")
    return cihaz_olay_service.listele(claims["tenant_id"], row, saat)


@app.get("/v1/plants/{plant_id}/kayip-agaci")
def kayip_agaci_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.281 — kayıp ağacı (saklı sonuç; yoksa 404)."""
    from pvquant.services.calib_service import _pj
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    r = _pj(row).get("kayip_agaci")
    if not r:
        raise HTTPException(404, "henüz hesaplanmadı")
    return r


@app.post("/v1/plants/{plant_id}/kayip-agaci/hesapla")
def kayip_agaci_hesapla(plant_id: str, claims=Depends(yazma_yetkisi())):
    """v2.281 — kayıp ağacını hesapla/yenile (tipik yıl ışınımı, ~10 s)."""
    from pvquant.services import kayip_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return kayip_service.hesapla(claims["tenant_id"], row)


@app.get("/v1/plants/{plant_id}/tarife")
def tarife_getir_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.281 — mevcut tarife yapılandırması (yoksa null)."""
    from pvquant.services import tarife_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return {"tarife": tarife_service.tarife_getir(row)}


@app.put("/v1/plants/{plant_id}/tarife")
def tarife_ayarla(plant_id: str, p: TarifeIstek, claims=Depends(yazma_yetkisi())):
    """v2.281 — tarife/gelir yapılandırması (sabit | PTF-endeksli | YEKDEM döviz endeksli); null → kaldır."""
    from pvquant.services import tarife_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        t = tarife_service.dogrula(p.tarife) if p.tarife else None
    except ValueError as e:
        raise HTTPException(422, str(e))
    eski = dict(row.get("params_json") or {})
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, tarife=t)
    _ayar_izi("tarife_ayar", claims, plant_id, eski, pj)   # v2.602 (F4-H): eski/yeni tarife + ayar damgası (etkilenen hesaplar)
    return {"tarife": pj.get("tarife")}


@app.get("/v1/plants/{plant_id}/rapor-sablon/{ad}")
def rapor_sablon_uc(plant_id: str, ad: str, ay: str | None = None, gun: int = 30, kural: str = "program", fmt: str = "html", donem: str | None = None, uretim: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.281 — şablon raporlar (HTML): kapasite-testi | fatura (ay=YYYY-MM) | kullanilabilirlik (gun) | beklenen-gerceklesen (gun). (ENV-F05-5: dördü de burada.)
    v2.576 (Faz 1 F1-E): bagimsiz-dogrulama (gun 7–365, kural program|gun_oncesi|gun_ici|ufuk, fmt html|md)."""
    from pvquant.services import sablon_rapor_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if fmt not in ("html", "md"):
        raise HTTPException(422, "fmt html|md")
    try:
        if ad == "finansal-etki":   # v2.585 (Faz 2 F2-G): dönem kodu (gün/hafta/ay/çeyrek/yıl), üretim girdisi
            p = {"donem": _fe_donem(row, donem), "uretim": _fe_uretim(uretim)}
        elif ad == "bagimsiz-dogrulama":
            from pvquant.services import bagimsiz_dogrulama_service as bd
            if kural not in bd.KURALLAR:
                raise HTTPException(422, "kural " + "|".join(bd.KURALLAR))
            if not (7 <= gun <= 365):
                raise HTTPException(422, "gun 7-365")
            p = {"gun": gun, "kural": kural}
        else:
            p = {"ay": ay} if ad == "fatura" else {"gun": gun}
        icerik, dosya = sablon_rapor_service.uret(claims["tenant_id"], row, ad, fmt=fmt, **p)
    except KeyError:
        raise HTTPException(422, f"şablon: {sablon_rapor_service.SABLONLAR}")
    except ValueError as e:
        raise HTTPException(409, str(e))
    return Response(content=icerik, media_type=("text/markdown; charset=utf-8" if fmt == "md" else "text/html; charset=utf-8"), headers={"Content-Disposition": f'attachment; filename="{dosya}"'})


class RaporGonderimIstek(BaseModel):
    """v2.525: zamanlanmış dönem raporu — aktif, ayın günü (1–28), alıcılar (boşsa alarm alıcıları)."""
    aktif: bool | None = None
    gun: int | None = None
    alicilar: list[str] | None = None


@app.get("/v1/plants/{plant_id}/rapor-donem")
def rapor_donem(plant_id: str, donem: str | None = None, fmt: str = "html", claims=Depends(gecerli_kullanici)):
    """v2.525 — dönem raporu: donem YYYY-MM (ay) | YYYY-QN (çeyrek) | YYYY (yıl); verilmezse son tam ay. fmt html (indirilebilir) | json (önizleme).
    İçerik: üretim ve gün başı beklentisi, olaylar, olay kaydına göre kullanılabilirlik, POA varsa temel PR, ay döneminde uzlaştırma kalemleri (yeniden hesap) ve EPİAŞ bildirimi."""
    from pvquant.services import aylik_rapor_service
    if fmt not in ("html", "json"):
        raise HTTPException(422, "fmt html ya da json olmalı")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    plant = {"id": str(row["id"]), "name": row["name"], "capacity_kwp": row["capacity_kwp"], "ac_limit_kw": row.get("ac_limit_kw"), "params_json": row.get("params_json")}
    try:
        if fmt == "json":
            return aylik_rapor_service.veri(claims["tenant_id"], plant, donem)
        r, v = aylik_rapor_service.rapor(claims["tenant_id"], plant, donem)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "rapor_donem_indir", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={"donem": v["donem"]["kod"]})
    from pvquant.services.mutabakat_service import _sade
    ad = f"PVQuant_donem_raporu_{_sade(row['name']).replace(' ', '_')}_{v['donem']['kod']}.html"
    return Response(aylik_rapor_service.html(r).encode("utf-8"), media_type="text/html; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@app.get("/v1/plants/{plant_id}/rapor-gonderim")
def rapor_gonderim_oku(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.525 — zamanlanmış gönderim ayarı ve son gönderim durumu."""
    from pvquant.services import alarm_service, aylik_rapor_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    g = aylik_rapor_service.gonderim_ayari(alarm_service._pj(row))
    g["varsayilan_alicilar"] = alarm_service.alicilar(row); g["posta_yapilandirildi"] = __import__("pvquant.services.posta_service", fromlist=["yapilandirildi"]).yapilandirildi()
    return g


@app.put("/v1/plants/{plant_id}/rapor-gonderim")
def rapor_gonderim_ayarla(plant_id: str, p: RaporGonderimIstek, claims=Depends(yazma_yetkisi())):
    from pvquant.services import alarm_service, aylik_rapor_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        an = aylik_rapor_service.gonderim_dogrula(p.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, f"{e} alanı geçersiz (gün 1–28; alıcı e-posta adresi, en çok 10)")
    g = aylik_rapor_service.gonderim_ayari(alarm_service._pj(row)); g.update(an)
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, rapor_gonderim={k: g[k] for k in g if k in ("aktif", "gun", "alicilar", "son_gonderim", "son_durum", "son_donem")})
    _denetim.kaydet("musteri", "rapor_gonderim_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"],
                    ayrinti={k: (len(v) if k == "alicilar" else v) for k, v in an.items()})
    row["params_json"] = pj
    out = aylik_rapor_service.gonderim_ayari(pj); out["varsayilan_alicilar"] = alarm_service.alicilar(row)
    from pvquant.services import posta_service
    out["posta_yapilandirildi"] = posta_service.yapilandirildi()
    return out


@app.post("/v1/plants/{plant_id}/rapor-gonderim/dene")
def rapor_gonderim_dene(plant_id: str, donem: str | None = None, claims=Depends(yazma_yetkisi())):
    """v2.525 — dönem raporunu şimdi alıcılara gönder (SMTP yapılandırılmamışsa dürüstçe «yapılandırılmadı»)."""
    from pvquant.services import aylik_rapor_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    plant = {"id": str(row["id"]), "name": row["name"], "capacity_kwp": row["capacity_kwp"], "ac_limit_kw": row.get("ac_limit_kw"), "params_json": row.get("params_json")}
    try:
        return aylik_rapor_service.gonder(claims["tenant_id"], plant, donem, kaynak="elle")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/plants/{plant_id}/guc-matrisi")
def guc_matrisi_uc(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.283 — modül davranışı (güç matrisi): saklı sonuç; yoksa 404."""
    from pvquant.services import guc_matrisi_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    r = guc_matrisi_service.getir(row)
    if not r:
        raise HTTPException(404, "henüz hesaplanmadı")
    return r


@app.post("/v1/plants/{plant_id}/guc-matrisi/hesapla")
def guc_matrisi_hesapla(plant_id: str, claims=Depends(yazma_yetkisi())):
    """v2.283 — güç matrisi davranışını hesapla/yenile (tipik yıl, ~10 s)."""
    from pvquant.services import guc_matrisi_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return guc_matrisi_service.hesapla(claims["tenant_id"], row)


@app.get("/v1/plants/{plant_id}/bankable")
def bankable(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.278 — bankable yıllık beklenti (P50/P90, 1 ve 10 yıl), belirsizlik bütçesi, TMY; hesaplanmadıysa 404."""
    from pvquant.services import bankable_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    r = bankable_service.getir(row)
    if not r:
        raise HTTPException(404, "henüz hesaplanmadı")
    return r


@app.post("/v1/plants/{plant_id}/bankable/hesapla")
def bankable_hesapla(plant_id: str, claims=Depends(yazma_yetkisi())):
    """v2.278 — hesapla/yenile (1–2 dk: 19 yıl × fizik koşusu); sonuç saklanır."""
    from pvquant.services import bankable_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return bankable_service.hesapla(claims["tenant_id"], row)


@app.get("/v1/plants/{plant_id}/monthly")
def monthly(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.78-B — aylik beklenti kapisi (KUTU-2 okuyan yol).

    Ham okuma, hesap yok: iklim_beklenti (P10/50/90, worker ayda bir yazar)
    + iklim_yil (20 yil serpilisi). Henuz hesaplanmadiysa durust 404 —
    'birikiyor' anlatisi istemcinin isi.
    """
    from pvquant.services import iklim_service
    b = iklim_service.iklim_oku(claims["tenant_id"], plant_id)
    if b.empty:
        raise HTTPException(404, "iklim beklentisi henuz hesaplanmadi")
    y = iklim_service.iklim_yil_oku(claims["tenant_id"], plant_id)
    # v2.317 (K2a): pencereyi VERI soyler — ust rozetteki sabit "20 yil" iddiasi
    # kendi kartlariyla celisiyordu. Kaynak iklim_yil: matrisle ayni satirlar,
    # yani cip ile matris insa geregi tutarli kalir. Bos ise durust null.
    return {
        "plant_id": plant_id,
        "hesap_zamani": b["hesap_zamani"].max().isoformat(),
        "donem": (f"{int(y['yil'].min())}\u2013{int(y['yil'].max())}"
                  if not y.empty else None),
        "yil_sayisi": int(y["yil"].nunique()) if not y.empty else None,
        "beklenti": [
            {"ay": int(r.ay), "p10": _kw(r.ghi_p10_kwh_m2),
             "p50": _kw(r.ghi_p50_kwh_m2), "p90": _kw(r.ghi_p90_kwh_m2),
             "yil_sayisi": int(r.yil_sayisi)} for r in b.itertuples()],
        "yillik": [
            {"yil": int(r.yil), "ay": int(r.ay),
             "ghi_kwh_m2": _kw(r.ghi_kwh_m2)} for r in y.itertuples()],
    }


# ---------------------------------------------------------------- 26.10 Faz 6: kuruluş
class KurulusAyar(BaseModel):
    yonetici_2fa_zorunlu: bool


@app.get("/v1/kurulus/denetim", tags=["Yönetim"])
def kurulus_denetim(limit: int = 100, once_id: int | None = None, claims=Depends(yonetici_yetkisi())):
    """Kiracı içi denetim izi (yalnız yönetici): kendi ekibinin eylemleri VE platformun bu kiracıda yaptıkları (kapsam sütunuyla).
    tenant_id jetondan — sorgudan alınmaz."""
    from pvquant.services import denetim_service
    kayitlar = denetim_service.listele(tenant_id=claims["tenant_id"], limit=limit, once_id=once_id)
    # 26.10 denetim-2: platform satırlarında personel e-postası/IP ve platforma özel alanlar (notlar) müşteriye verilmez
    for k in kayitlar:
        if k["kapsam"] == "platform":
            k["aktor_eposta"] = None; k["ip"] = None; k["aktor_id"] = None
            k["ayrinti"] = {a: v for a, v in (k.get("ayrinti") or {}).items() if "notlar" not in a}   # durum/plan değişimi kalır, not içeriği/işareti gitmez
    return {"kayitlar": kayitlar}


@app.get("/v1/kurulus/denetim/{iz_id}/etkilenen", tags=["Yönetim"])
def kurulus_denetim_etkilenen(iz_id: int, n: int = 100, claims=Depends(yonetici_yetkisi())):
    """v2.602 (F4-H): bir santral ayarı değişikliğinin (iz) öncesinde eski ayar damgasıyla hesaplanmış kayıtlı finansal sonuçlar — yeniden hesap gereğini
    gösterir, yeniden hesaplamaz. Yalnız kiracının kendi izi."""
    from pvquant.services import denetim_service
    r = denetim_service.etkilenen_sonuclar(claims["tenant_id"], iz_id, n)
    if r.get("durum") == "iz_yok":
        raise HTTPException(404, "iz yok")
    return r


@app.get("/v1/kurulus/ayarlar", tags=["Yönetim"])
def kurulus_ayarlar(claims=Depends(yonetici_yetkisi())):
    from pvquant.services import kurulus_service
    return kurulus_service.ayarlar(claims["tenant_id"])


@app.put("/v1/kurulus/ayarlar", tags=["Yönetim"])
def kurulus_ayarlar_guncelle(a: KurulusAyar, request: Request, claims=Depends(yonetici_yetkisi())):
    """«Yöneticiler için 2FA zorunlu»: açınca 2FA'sız yöneticiler bir sonraki istekte kurulum ekranına düşer (60 sn önbellek düşürülür)."""
    from pvquant.services import kurulus_service
    y = kurulus_service.ayar_guncelle(claims["tenant_id"], yonetici_2fa_zorunlu=a.yonetici_2fa_zorunlu)
    _denetim.kaydet("musteri", "kurulus_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="tenant", nesne_id=claims["tenant_id"],
                    ayrinti={"yonetici_2fa_zorunlu": a.yonetici_2fa_zorunlu}, ip=request.client.host if request.client else None)
    return y


@app.get("/v1/healthz")
def healthz():
    return {"ok": True}


@app.get("/v1/report/json-schema", tags=["Dış API"])
def rapor_json_semasi():
    """v2.350: JSON raporunun yayımlı sözleşmesi (JSON Schema, Pydantic'ten).
    Kimliksiz — sözleşme sır değildir; entegratör Postman/kod üreticiyle
    dakikalar içinde bağlanır (rakip taraması: ≥6 sağlayıcı şema yayımlıyor).
    Raporun kendisi `schema_url` ile buraya işaret eder."""
    from pvquant.reporting.schemas import ForecastReport
    return ForecastReport.model_json_schema()


# ---------------------------------------------------------------- v2.87
# SCADA yukleme kapilari — SPA'nin veri isi. Cekirdek boru hatti
# (preview_file / ingest_file / yukle_ve_kaydet) DEGISMEZ; buradaki
# uclar ince HTTP sarmasidir. API durumsuz: dosya iki uca da gonderilir
# (12 ay saatlik ~9k satir, MB mertebesi — bilinene kapsam karari).
# Manuel esleme sihirbazi kapsam disi (v2.90 adayi): esleme tutmazsa
# durust 422, Streamlit sihirbazina yonlendirme.
from fastapi import File, Form, UploadFile


def _gecici_dosya(f) -> str:
    """UploadFile -> diskte gecici kopya. Uzanti korunur: format
    algilama .xlsx/.csv ayrimini dosya adindan da okur."""
    import shutil
    import tempfile
    from pathlib import Path
    ek = Path(f.filename or "veri.csv").suffix or ".csv"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ek)
    shutil.copyfileobj(f.file, tmp)
    tmp.close()
    return tmp.name


def _ornek_satirlar(df):
    """Ham onizleme JSON-guvenli: NaN -> null, her deger metin.
    Onay ekrani ham gorunumu GOSTERIR, yorumlamaz (icat yok)."""
    return {"columns": [str(c) for c in df.columns],
            "rows": [[None if pd.isna(v) else str(v) for v in r]
                     for r in df.head(10).itertuples(index=False, name=None)]}


@app.get("/v1/plants/{plant_id}/scada/disa")
def scada_disa(plant_id: str, baslangic: str | None = None, bitis: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.298 — yüklenen ham serinin CSV dökümü ("veriniz sizindir" sözünün karşılığı; her role açık)."""
    from fastapi.responses import Response

    from pvquant.services import ingest_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    csv = ingest_service.scada_disa_csv(claims["tenant_id"], plant_id, baslangic, bitis)
    ad = f"pvquant_scada_{row['name'].replace(' ', '_')}.csv"
    return Response(csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@app.delete("/v1/plants/{plant_id}/scada")
def scada_sil(plant_id: str, baslangic: str, bitis: str, claims=Depends(yonetici_yetkisi())):
    """v2.298 — ham SCADA aralığını siler (yalnız yönetici; bitiş günü dâhil). Karne arşivi korunur —
    geçmiş sınav sonuçları yeniden yazılmaz; kalibrasyon sonraki koşuda kalan veriyle öğrenir."""
    from pvquant.services import ingest_service
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        n = ingest_service.scada_sil(claims["tenant_id"], plant_id, baslangic, bitis)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "scada_sil", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id,
                    ayrinti={"baslangic": baslangic, "bitis": bitis, "silinen": n})
    return {"silinen_satir": n}


@app.post("/v1/plants/{plant_id}/scada/preview")
def scada_preview(plant_id: str, dosya: UploadFile = File(...),
                  claims=Depends(gecerli_kullanici)):
    """v2.87 Faz 1: algila + esle — KAYDETME YOK. Onay ekranini besler."""
    from pvquant.io.ingestion.pipeline import MappingFailedError, preview_file
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    yol = _gecici_dosya(dosya)
    try:
        pv = preview_file(yol)
    except ValueError as e:
        # v2.369 (bulgu 20): tablo olmayan dosya (JSON vb.) sihirbaza değil
        # insan diliyle redde gider — boş kolonlu çıkışsız sihirbaz bitti.
        raise HTTPException(422, str(e))
    except MappingFailedError as e:
        # v2.91: duz metin degil YAPILANDIRILMIS red — SPA sihirbazi bu
        # govdeyle kurulur (hata zaten kolonlari + ornekleri tasiyor).
        raise HTTPException(422, {
            "tur": "esleme",
            "columns": e.columns,
            "sample_rows": _ornek_satirlar(e.sample_rows),
            "file_format": e.file_format.to_dict(),
        })
    finally:
        _os.unlink(yol)
    return {"file_format": pv.file_format.to_dict(),
            "mapping": pv.mapping.to_dict(),
            "unmapped_columns": pv.unmapped_columns,
            "sample_rows": _ornek_satirlar(pv.sample_rows),
            "matched_template": pv.matched_template,
            "notes": pv.notes,
            "onerilen_tz": row["tz"]}


@app.post("/v1/plants/{plant_id}/scada")
def scada_yukle(plant_id: str, dosya: UploadFile = File(...),
                source_timezone: str | None = Form(None),
                map_timestamp: str | None = Form(None),
                map_power: str | None = Form(None),
                map_energy: str | None = Form(None),
                map_poa_irradiance: str | None = Form(None),
                map_temp_ambient: str | None = Form(None),
                map_temp_module: str | None = Form(None),
                map_wind_speed: str | None = Form(None),
                map_ghi: str | None = Form(None),
                duplicate_policy: str | None = Form(None),   # v2.363: sum|mean
                damga_tipi: str | None = Form(None),         # v2.599 (F4-D): aralik_basi (varsayılan) | aralik_sonu | anlik
                claims=Depends(yazma_yetkisi())):
    """v2.87 Faz 2: onayli kararla dogrula + kalicilastir. Kapasite/konum
    santral KAYDINDAN okunur (kunye tek gercek, formda tekrar yok).
    Karne (QualityReport) cevapta doner — SPA yorumsuz gosterir."""
    from pvquant.io.ingestion.pipeline import MappingFailedError, ingest_file
    from pvquant.io.ingestion.transform import DuplicateTimestampsError
    from pvquant.services import ingest_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    # v2.363: cihaz/invertör bazlı dosyada panel "Topla/Ortala" seçimini bu
    # alanla yollar; çöp değer sessizce 'error'a düşmez, açıkça reddedilir.
    if duplicate_policy is not None and duplicate_policy not in ("sum", "mean"):
        raise HTTPException(422, "duplicate_policy yalnız 'sum' ya da 'mean' olabilir")
    tekrar = duplicate_policy or "error"
    from pvquant.zaman import DAMGA_TIPLERI as _DT
    if damga_tipi is not None and damga_tipi not in _DT:
        raise HTTPException(422, "damga_tipi yalnız aralik_basi, aralik_sonu ya da anlik olabilir")
    damga = damga_tipi or "aralik_basi"
    tz = source_timezone or row["tz"]   # v2.91: bos ise santral kaydi konusur
    esleme = None
    if map_timestamp:
        # v2.91: sihirbaz kararlari. ONEMLI: yalniz mapping vermek otomatik
        # dala dusurur (pipeline kurali); file_format da birlikte gerekli.
        # Algilama 1. asamada zaten basariliydi — ayni tespiti uretiriz.
        from pvquant.io.ingestion.contracts import ColumnMapping
        esleme = ColumnMapping(
            timestamp=map_timestamp, power=map_power, energy=map_energy,
            poa_irradiance=map_poa_irradiance, temp_ambient=map_temp_ambient,
            temp_module=map_temp_module, wind_speed=map_wind_speed,
            ghi=map_ghi)
    yol = _gecici_dosya(dosya)
    try:
        if esleme is not None:
            from pvquant.io.ingestion.detection import detect_file_format
            res = ingest_file(yol, capacity_kwp=float(row["capacity_kwp"]),
                              latitude=row["lat"], longitude=row["lon"],
                              source_timezone=tz,
                              file_format=detect_file_format(yol),
                              mapping=esleme, duplicate_policy=tekrar, damga_tipi=damga,
                              ac_limit_kw=row.get("ac_limit_kw"))   # v2.376
        else:
            res = ingest_file(yol, capacity_kwp=float(row["capacity_kwp"]),
                              latitude=row["lat"], longitude=row["lon"],
                              source_timezone=tz, duplicate_policy=tekrar, damga_tipi=damga,
                              ac_limit_kw=row.get("ac_limit_kw"))   # v2.376
        out = ingest_service.yukle_ve_kaydet(
            claims["tenant_id"], plant_id, dosya.filename or yol,
            capacity_kwp=float(row["capacity_kwp"]),
            latitude=row["lat"], longitude=row["lon"],
            source_timezone=tz, hazir_sonuc=res)
    except MappingFailedError as e:
        raise HTTPException(422, "otomatik esleme kurulamadi: "
                            f"{e} — simdilik Streamlit sihirbazini kullanin")
    except DuplicateTimestampsError as e:
        # v2.363: fren mesajı 500'ün içinde kaybolmaz — panel bu yapıyla
        # "Santral toplamı / Ortalama" seçimi sunup aynı dosyayı yeniden yollar.
        # v2.373 (E6): kopya mükerrerde önerilen 'mean' — panel rozeti buna göre
        raise HTTPException(422, {
            "tur": "cihaz_bazli", "satir": e.rows, "damga": e.timestamps,
            "oran": e.ratio, "oneri": "mean" if e.identical else "sum",
            "mesaj": ((f"Mükerrer satırlar birebir KOPYA görünüyor (damga başına "
                       f"{e.ratio:.1f} satır). 'Ortalama' doğru seçimdir; "
                       "'Santral toplamı' değerleri katlar.")
                      if e.identical else
                      (f"Bu dosya cihaz/invertör bazlı görünüyor: zaman damgası "
                       f"başına ortalama {e.ratio:.1f} satır ({e.rows} satır, "
                       f"{e.timestamps} damga). Satırlar sessizce birleştirilmez — "
                       "nasıl birleştirileceğini siz seçin."))})
    except ValueError as e:
        # v2.363: hattın diğer doğrulama hataları da müşteriye 500 değil
        # insan diliyle 422 döner.
        raise HTTPException(422, str(e))
    finally:
        _os.unlink(yol)
    _denetim.kaydet("musteri", "scada_yukle", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id,   # v2.602 (F4-H): dosya içeriği yazılmaz
                    ayrinti={"dosya": dosya.filename, "damga_tipi": damga_tipi, "duplicate_policy": duplicate_policy,
                             **{k: v for k, v in (out or {}).items() if isinstance(v, (int, str)) and k in ("batch_id", "parti_id", "satir", "yazilan", "ilk", "son", "rows_written", "n_satir")}})
    return {**out, "report": res.report.to_dict(),
            "transform": res.transform.to_dict()}


# ---------------------------------------------------------------- v2.93
# Hizli tahmin — Streamlit'teki tek satirin HTTP hali:
# forecast_service.uret_ve_kaydet. Kalibre santralda aktif modla kosar
# (vaat edilenden iyisi); kalibrasyonsuz santralda fizik (Mod A).
# Es zamanli doner (10-20 sn) — panel icin kabul edilir, serh dusuldu.

@app.post("/v1/plants/{plant_id}/forecast/run")
def tahmin_kos(plant_id: str, claims=Depends(yazma_yetkisi())):
    """v2.93: taze tahmin kosusu tetikle; run_id doner."""
    from pvquant.services.forecast_service import uret_ve_kaydet
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    import time as _time
    t0 = _time.perf_counter()
    run_id = uret_ve_kaydet(claims["tenant_id"], row, etiket="elle")   # v2.572: elle koşu ana karne kovalarına girmez (karne_kurali)
    sure_sn = round(_time.perf_counter() - t0, 2)   # v2.606 (F4-L): eş zamanlı koşu YALNIZ ölçülür (arka plana alınması ayrı karar); süre izde ve yanıtta
    _denetim.kaydet("musteri", "elle_kosu", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id, ayrinti={"run_id": str(run_id), "etiket": "elle", "sure_sn": sure_sn})   # v2.602
    return {"run_id": str(run_id), "sure_sn": sure_sn}


# ---------------------------------------------------------------- v2.94
# Raporlar — tek uretim kapisi (report_service.uret) HTTP'ye acilir.
# reporting paketi TEK SATIR degismez (Parca 3 §4 sozlesmesi surer).

_RAPOR_MIME = {
    "pdf": "application/pdf",
    "pdf16": "application/pdf",   # v2.104: 16 sayfalik musteri raporu
    "xlsx": ("application/vnd.openxmlformats-officedocument"
             ".spreadsheetml.sheet"),
    "json": "application/json",
}


@app.get("/v1/plants/{plant_id}/runs")
def kosu_listesi(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.94: gecmis kosular — SPA'daki sabit ornegin yerine gercek tablo."""
    from pvquant.services.forecast_service import kosu_gecmisi
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return [{"run_at": r.run_at.isoformat(), "mode": r.mode, "model": r.model, "bant": getattr(r, "bant", None),   # v2.273
             "sapma": getattr(r, "sapma", None), "etiket": getattr(r, "etiket", None),   # v2.274 / v2.276
             "nwp_kosu_zamani": (r.nwp_kosu_zamani.isoformat() if getattr(r, "nwp_kosu_zamani", None) else None), "nwp_bilesenler": getattr(r, "nwp_bilesenler", None)}   # v2.605
            for r in kosu_gecmisi(claims["tenant_id"], plant_id, n=10)]


@app.get("/v1/plants/{plant_id}/dogrulama/bagimsiz")
def bagimsiz_dogrulama(plant_id: str, gun: int = 30, kural: str = "program", taze: int = 0, claims=Depends(gecerli_kullanici)):
    """v2.574 (Faz 1 F1-C): bağımsız doğrulama — yayımlandığı andaki tahmin × uygun ölçüm × referanslar (fizik, persistans, CLIPER).
    Varsayılan: gece işinin son kayıtlı sonucu (≤36 sa); yoksa ya da taze=1 ise anında hesap (kaydedilmez)."""
    from pvquant.services import bagimsiz_dogrulama_service as bd
    if kural not in bd.KURALLAR:
        raise HTTPException(422, "kural " + "|".join(bd.KURALLAR))
    if not (7 <= gun <= 365):
        raise HTTPException(422, "gun 7-365")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if not taze:
        s = bd.son(claims["tenant_id"], plant_id, kural, gun)
        if s:
            return s
    s = bd.hesapla(claims["tenant_id"], row, gun=gun, kural=kural)
    s["kayitli"] = False
    return s


@app.get("/v1/portfoy/dogrulama/bagimsiz")
def portfoy_bagimsiz_dogrulama(gun: int = 30, kural: str = "program", claims=Depends(gecerli_kullanici)):
    """v2.574 (Faz 1 F1-C): kiracının tüm santralleri tek havuzda (saatlik havuzlanmış); anında hesap, kaydedilmez."""
    from pvquant.services import bagimsiz_dogrulama_service as bd
    if kural not in bd.KURALLAR:
        raise HTTPException(422, "kural " + "|".join(bd.KURALLAR))
    if not (7 <= gun <= 365):
        raise HTTPException(422, "gun 7-365")
    from sqlalchemy import text as _text

    from pvquant.db import tenant_baglami as _tb
    with _tb(claims["tenant_id"]) as s:
        plants = [dict(r._mapping) for r in s.execute(_text("SELECT id, name, capacity_kwp, tz, lat, lon, params_json FROM plants WHERE NOT archived ORDER BY name"))]
    return bd.portfoy(claims["tenant_id"], plants, gun=gun, kural=kural)


def _fe_donem_dict(row: dict, donem: str | None) -> dict:
    from pvquant.ext.platform import finans as fn
    try:
        return fn.donem_cozumle(donem, tz=row.get("tz") or fn.IST_AD)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


def _fe_donem(row: dict, donem: str | None) -> str:
    return _fe_donem_dict(row, donem)["kod"]


def _fe_uretim(uretim: str | None) -> str | None:
    if uretim in (None, ""):
        return None
    if uretim not in ("scada", "sayac"):
        raise HTTPException(422, "uretim scada|sayac")
    return uretim


@app.get("/v1/plants/{plant_id}/finansal-etki")
def finansal_etki(plant_id: str, donem: str | None = None, uretim: str | None = None, taze: int = 0, itibariyle: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.583 (Faz 2 F2-E): Finansal Etki Merkezi — dönem (YYYY-MM-DD | YYYY-Wnn | YYYY-MM | YYYY-QN | YYYY; verilmezse son tam ay) için üretim özeti,
    satış geliri, uzlaştırma bileşenleri, resmî eşleme, göstergeler, üretim düşüklüğü, ileri maruziyet ve birleşik toplam. Varsayılan: gece işinin son
    kayıtlı sonucu (≤36 sa); yoksa ya da taze=1 ise anında hesap (kaydedilmez). Tutarlar yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir."""
    from pvquant.services import finansal_etki_service as fe
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    d = _fe_donem_dict(row, donem); kod = d["kod"]; ur = _fe_uretim(uretim)
    if itibariyle:   # v2.601 (F4-G, M6): fiyat o andaki sürümle — kayıtlı sonucun yeniden kurulması (kaydedilmez)
        return fe.ozet(claims["tenant_id"], row, kod, ur, itibariyle=_zaman_cozumle(itibariyle))
    if not taze:
        s = fe.son(claims["tenant_id"], plant_id, kod, ur, donem_bit=d["bit"], plant=row)   # v2.587: dönem sonu ve santral ayarındaki girdiyle eşleşen kayıt
        if s:
            return s
    return fe.ozet(claims["tenant_id"], row, kod, ur)


def _zaman_cozumle(metin: str):
    """ISO zaman → UTC datetime; saat dilimi yoksa piyasa dilimi varsayılır. Geçersizse 422."""
    try:
        t = pd.Timestamp(metin)
    except (ValueError, TypeError):
        raise HTTPException(422, "itibariyle ISO zaman olmalı (ör. 2026-11-12T03:55:00+03:00)") from None
    if pd.isna(t):
        raise HTTPException(422, "itibariyle ISO zaman olmalı")
    t = t.tz_localize(PIYASA_TZ) if t.tzinfo is None else t
    return t.tz_convert("UTC").to_pydatetime()


@app.get("/v1/plants/{plant_id}/finansal-etki/gecmis")
def finansal_etki_gecmis(plant_id: str, donem: str | None = None, n: int = 20, claims=Depends(gecerli_kullanici)):
    """v2.583 (Faz 2 F2-E, Stage 6): dönemin kayıtlı sürümleri ve her birinin varsayımları (kural sürümü, fiyat kaynağı, program, tarife, bildirim)."""
    from pvquant.services import finansal_etki_service as fe
    if not (1 <= n <= 100):
        raise HTTPException(422, "n 1-100")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    kod = _fe_donem(row, donem)
    return {"donem_kodu": kod, "surumler": fe.gecmis(claims["tenant_id"], plant_id, kod, n)}


@app.get("/v1/plants/{plant_id}/finansal-etki/senaryo")
def finansal_etki_senaryo(plant_id: str, donem: str | None = None, pozisyon: str = "program", sabit_mwh: float | None = None, uretim: str | None = None,
                          claims=Depends(gecerli_kullanici)):
    """v2.583 (Faz 2 F2-E, Stage 6): pozisyon senaryosu (program | uretim | sabit MWh/saat) — kaydedilmez, «senaryo» damgalı; resmî değerlerin yerine geçmez."""
    from pvquant.services import finansal_etki_service as fe
    if pozisyon not in fe.POZISYON_SECENEKLERI:
        raise HTTPException(422, "pozisyon " + "|".join(fe.POZISYON_SECENEKLERI))
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    if pozisyon == "sabit":
        kap = float(row.get("capacity_kwp") or 0.0) / 1000.0
        if sabit_mwh is None or not (0.0 <= float(sabit_mwh) <= (kap if kap > 0 else float("inf"))):
            raise HTTPException(422, "sabit_mwh 0–kurulu güç (MWh/saat)")
    kod = _fe_donem(row, donem); ur = _fe_uretim(uretim)
    return fe.senaryo(claims["tenant_id"], row, kod, pozisyon, sabit_mwh, ur)


@app.get("/v1/portfoy/finansal-etki")
def portfoy_finansal_etki(donem: str | None = None, uretim: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.583 (Faz 2 F2-E): kiracının santralleri — santral başına özet ve toplam (segment kapısıyla; eksik nitelikli santral toplama girmez); anında hesap, kaydedilmez."""
    from sqlalchemy import text as _text

    from pvquant.db import tenant_baglami as _tb
    from pvquant.services import finansal_etki_service as fe
    ur = _fe_uretim(uretim)
    with _tb(claims["tenant_id"]) as s:
        plants = [dict(r._mapping) for r in s.execute(_text("SELECT id, name, capacity_kwp, tz, lat, lon, params_json, archived FROM plants WHERE NOT archived ORDER BY name"))]
    kod = _fe_donem(plants[0] if plants else {}, donem)
    return fe.portfoy(claims["tenant_id"], plants, kod, ur)


@app.get("/v1/plants/{plant_id}/report")
def rapor_uret(plant_id: str, fmt: str, claims=Depends(gecerli_kullanici)):
    """v2.94: uret() -> bytes; dosya adi basliga yazilir, tarayici indirir."""
    from fastapi.responses import Response

    from pvquant.services import report_service
    from pvquant.services.report_html_service import RaporDenetimHatasi
    if fmt not in _RAPOR_MIME:
        raise HTTPException(422, f"bilinmeyen format: {fmt}")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        veri, ad, _ts = report_service.uret(claims["tenant_id"], row, fmt)
    except ValueError as e:
        raise HTTPException(409, str(e))   # "once tahmin uretin" durustce doner
    except RaporDenetimHatasi as e:
        # v2.147 (Adim 4): kapinin bulgulari artik logda degil KULLANICIDA —
        # 422 + yapilandirilmis govde; SPA gosterir. Uretim kusurlari 500 kalir.
        raise HTTPException(422, detail={
            "mesaj": "Rapor üretilmedi: tutarlılık denetimi geçemedi. "
                     "Aşağıdaki bulgular giderilmeden rapor yayımlanmaz.",
            "bulgular": e.bulgular})
    return Response(content=veri, media_type=_RAPOR_MIME[fmt],
                    headers={"Content-Disposition":
                             f'attachment; filename="{ad}"'})


# ======================================================================================================================
# v2.593 (Faz 3 F3-F) — PORTFÖY VARLIKLARI ve PORTFÖY HESAP UÇLARI
# Yetki: okuma gecerli_kullanici (viewer dâhil); kuruluş/portföy/üyelik yazma editor/admin (yazma_yetkisi); sözleşme okuma editor/admin, yazma yalnız admin.
# Doğrulama hataları (PortfoyHatasi) 422, «bulunamadı» 404. Her yazma denetim izine düşer (servis). Hesap uçları anında hesaplar; kayıt yalnız gece işinden.
# ======================================================================================================================
class KurulusIstek(BaseModel):
    ad: str
    tur: str
    epias_kodu: str | None = None
    notlar: str | None = None


class KurulusGuncelle(BaseModel):
    ad: str | None = None
    tur: str | None = None
    epias_kodu: str | None = None
    notlar: str | None = None
    aktif: bool | None = None


class PortfoyIstek(BaseModel):
    ad: str
    tur: str
    gecerli_bas: str
    gecerli_bit: str | None = None
    kurulus_id: str | None = None
    notlar: str | None = None
    dsg: dict | None = None          # {"dsg_kodu", "yonetici_kurulus_id"?, "netlesme"?}
    toplayici: dict | None = None    # {"kurulus_id"?, "sorumluluk"?}


class PortfoyGuncelle(BaseModel):
    ad: str | None = None
    gecerli_bit: str | None = None
    notlar: str | None = None
    kurulus_id: str | None = None
    dsg_kodu: str | None = None
    yonetici_kurulus_id: str | None = None
    netlesme: dict | None = None
    sorumluluk: dict | None = None


class UyelikIstek(BaseModel):
    plant_id: str
    gecerli_bas: str
    gecerli_bit: str | None = None
    kaynak: str = "beyan"
    dogrulama: str = "beyan"
    belge_adi: str | None = None
    belge_sha256: str | None = None
    notlar: str | None = None


class UyelikGuncelle(BaseModel):
    gecerli_bit: str | None = None
    dogrulama: str | None = None
    belge_adi: str | None = None
    belge_sha256: str | None = None
    notlar: str | None = None
    kaynak: str | None = None


class SozlesmeIstek(BaseModel):
    tur: str
    gecerli_bas: str
    gecerli_bit: str | None = None
    portfoy_id: str | None = None
    plant_id: str | None = None
    taraf_a_kurulus_id: str | None = None
    taraf_b_kurulus_id: str | None = None
    satis_modeli: str | None = None
    uzlastirma_modeli: str | None = None
    dengesizlik_sorumlusu: str | None = None
    dagitim_yontemi: str | None = None
    parametreler: dict | None = None
    belge_adi: str | None = None
    belge_sha256: str | None = None
    dogrulama: str = "beyan"
    notlar: str | None = None


class SozlesmeGuncelle(BaseModel):
    gecerli_bit: str | None = None
    satis_modeli: str | None = None
    uzlastirma_modeli: str | None = None
    dengesizlik_sorumlusu: str | None = None
    dagitim_yontemi: str | None = None
    parametreler: dict | None = None
    belge_adi: str | None = None
    belge_sha256: str | None = None
    dogrulama: str | None = None
    notlar: str | None = None


def _pv():
    from pvquant.services import portfoy_varlik_service as pv
    return pv


def _pv_aktor(claims) -> dict:
    return {"sub": claims.get("sub"), "email": claims.get("email")}


def _pv_hata(e: Exception) -> HTTPException:
    m = str(e)
    return HTTPException(404 if "bulunamadı" in m else 422, m)


def _pv_tarih(tarih: str | None, ad: str = "tarih"):
    if tarih in (None, ""):
        return None
    try:
        return _pv()._tarih(tarih, ad)
    except ValueError as e:
        raise _pv_hata(e)


def _pv_gun(bugun: str | None):
    """Test ve yeniden üretim için isteğe bağlı «bugün» (YYYY-AA-GG); verilmezse gerçek gün."""
    return _pv_tarih(bugun, "bugun")


@app.get("/v1/kuruluslar")
def kuruluslar(aktif: int = 1, claims=Depends(gecerli_kullanici)):
    return {"kuruluslar": _pv().kuruluslar(claims["tenant_id"], True if aktif else None)}


@app.post("/v1/kuruluslar")
def kurulus_ekle(p: KurulusIstek, claims=Depends(yazma_yetkisi())):
    try:
        return {"id": _pv().kurulus_ekle(claims["tenant_id"], p.ad, p.tur, p.epias_kodu, p.notlar, aktor=_pv_aktor(claims))}
    except ValueError as e:
        raise _pv_hata(e)


@app.put("/v1/kuruluslar/{kurulus_id}")
def kurulus_guncelle(kurulus_id: str, p: KurulusGuncelle, claims=Depends(yazma_yetkisi())):
    try:
        return _pv().kurulus_guncelle(claims["tenant_id"], kurulus_id, aktor=_pv_aktor(claims), **p.model_dump(exclude_none=True))
    except ValueError as e:
        raise _pv_hata(e)


@app.get("/v1/portfoyler")
def portfoyler(tarih: str | None = None, tur: str | None = None, claims=Depends(gecerli_kullanici)):
    try:
        return {"portfoyler": _pv().portfoyler(claims["tenant_id"], _pv_tarih(tarih), tur)}
    except ValueError as e:
        raise _pv_hata(e)


@app.post("/v1/portfoyler")
def portfoy_ekle(p: PortfoyIstek, claims=Depends(yazma_yetkisi())):
    try:
        return {"id": _pv().portfoy_ekle(claims["tenant_id"], p.ad, p.tur, p.gecerli_bas, p.gecerli_bit, p.kurulus_id, p.notlar, p.dsg, p.toplayici, aktor=_pv_aktor(claims))}
    except ValueError as e:
        raise _pv_hata(e)


@app.get("/v1/portfoyler/{portfoy_id}")
def portfoy_getir(portfoy_id: str, tarih: str | None = None, claims=Depends(gecerli_kullanici)):
    try:
        return _pv().portfoy(claims["tenant_id"], portfoy_id, _pv_tarih(tarih))
    except ValueError as e:
        raise _pv_hata(e)


@app.put("/v1/portfoyler/{portfoy_id}")
def portfoy_guncelle(portfoy_id: str, p: PortfoyGuncelle, claims=Depends(yazma_yetkisi())):
    try:
        return _pv().portfoy_guncelle(claims["tenant_id"], portfoy_id, aktor=_pv_aktor(claims), **p.model_dump(exclude_none=True))
    except ValueError as e:
        raise _pv_hata(e)


@app.get("/v1/portfoyler/{portfoy_id}/uyeler")
def portfoy_uyeler(portfoy_id: str, tarih: str | None = None, tum: int = 0, claims=Depends(gecerli_kullanici)):
    """tarih verilirse o tarihte geçerli üyeler; tum=1 bütün üyelik geçmişi; ikisi de yoksa bugün."""
    pv = _pv()
    try:
        pv.portfoy(claims["tenant_id"], portfoy_id)   # 404 kapısı
        t = None if tum else (_pv_tarih(tarih) or __import__("datetime").date.today())
        return {"uyeler": pv.uyeler(claims["tenant_id"], portfoy_id, t)}
    except ValueError as e:
        raise _pv_hata(e)


@app.post("/v1/portfoyler/{portfoy_id}/uyeler")
def portfoy_uyelik_ekle(portfoy_id: str, p: UyelikIstek, claims=Depends(yazma_yetkisi())):
    try:
        return {"id": _pv().uyelik_ekle(claims["tenant_id"], portfoy_id, p.plant_id, p.gecerli_bas, p.gecerli_bit, p.kaynak, p.dogrulama, p.belge_adi, p.belge_sha256, p.notlar,
                                        aktor=_pv_aktor(claims))}
    except ValueError as e:
        raise _pv_hata(e)


@app.put("/v1/portfoyler/{portfoy_id}/uyeler/{uyelik_id}")
def portfoy_uyelik_guncelle(portfoy_id: str, uyelik_id: str, p: UyelikGuncelle, claims=Depends(yazma_yetkisi())):
    try:
        return _pv().uyelik_guncelle(claims["tenant_id"], uyelik_id, aktor=_pv_aktor(claims), **p.model_dump(exclude_none=True))
    except ValueError as e:
        raise _pv_hata(e)


@app.get("/v1/sozlesmeler")
def sozlesmeler(portfoy_id: str | None = None, plant_id: str | None = None, tarih: str | None = None, claims=Depends(yazma_yetkisi())):
    """Sözleşme kayıtları editor/admin'e açıktır (hassas ticari veri); viewer yalnız portföy görünümündeki dağılım etiketini görür."""
    try:
        return {"sozlesmeler": _pv().sozlesmeler(claims["tenant_id"], portfoy_id, plant_id, _pv_tarih(tarih))}
    except ValueError as e:
        raise _pv_hata(e)


@app.post("/v1/sozlesmeler")
def sozlesme_ekle(p: SozlesmeIstek, claims=Depends(yonetici_yetkisi())):
    try:
        d = p.model_dump()
        return {"id": _pv().sozlesme_ekle(claims["tenant_id"], d.pop("tur"), d.pop("gecerli_bas"), d.pop("gecerli_bit"), aktor=_pv_aktor(claims), **d)}
    except ValueError as e:
        raise _pv_hata(e)


@app.put("/v1/sozlesmeler/{sozlesme_id}")
def sozlesme_guncelle(sozlesme_id: str, p: SozlesmeGuncelle, claims=Depends(yonetici_yetkisi())):
    try:
        return _pv().sozlesme_guncelle(claims["tenant_id"], sozlesme_id, aktor=_pv_aktor(claims), **p.model_dump(exclude_none=True))
    except ValueError as e:
        raise _pv_hata(e)


def _pf_kapi(claims, portfoy_id: str) -> dict:
    try:
        return _pv().portfoy(claims["tenant_id"], portfoy_id)
    except ValueError as e:
        raise _pv_hata(e)


@app.get("/v1/portfoyler/{portfoy_id}/tahmin")
def portfoyler_tahmin(portfoy_id: str, gun: int = 2, kural: str = "son", bugun: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.589 (F3-B): portföy saatlik tahmini — ortak saat kümesi, bant (santral yarı genişlikleri × büzülmüş korelasyon; naif/bağımsız sınırlar), günlük beklenti, tazelik."""
    from pvquant.services import portfoy_tahmin_service as pt
    if kural not in pt.KURALLAR:
        raise HTTPException(422, "kural " + "|".join(pt.KURALLAR))
    if not (1 <= gun <= 15):
        raise HTTPException(422, "gun 1-15")
    _pf_kapi(claims, portfoy_id); b = _pv_gun(bugun)
    return pt.gunler(claims["tenant_id"], portfoy_id, gun, kural, b)


@app.get("/v1/portfoyler/{portfoy_id}/kapsama")
def portfoy_kapsama(portfoy_id: str, gun: int = 30, taze: int = 0, bugun: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.589 (F3-B): portföy bandının geçmiş sınavı (PICP80, Winkler; naif ve bağımsız karşılaştırma). Varsayılan: gece işinin son kaydı (≤36 sa); yoksa ya da taze=1 anında."""
    from pvquant.services import portfoy_tahmin_service as pt
    if not (7 <= gun <= 120):
        raise HTTPException(422, "gun 7-120")
    _pf_kapi(claims, portfoy_id)
    if not taze and not bugun:
        s = pt.son_kapsama(claims["tenant_id"], portfoy_id)
        if s:
            return s
    return pt.kapsama(claims["tenant_id"], portfoy_id, gun, _pv_gun(bugun))


@app.get("/v1/portfoyler/{portfoy_id}/sapma")
def portfoy_sapma(portfoy_id: str, donem: str | None = None, uretim: str | None = None, bugun: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.590 (F3-C): dönem için program sapması / tahmin hatası / fizik sapması ayrı; santral katkıları, fiziksel ofset, maruziyet saatleri (gösterge), kapsama."""
    from pvquant.services import portfoy_sapma_service as sp
    _pf_kapi(claims, portfoy_id); ur = _fe_uretim(uretim)
    try:
        return sp.donem(claims["tenant_id"], portfoy_id, donem, ur, _pv_gun(bugun))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/portfoyler/{portfoy_id}/risk")
def portfoy_risk(portfoy_id: str, gun: int = 2, kural: str = "son", bugun: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.590 (F3-C): ileriye dönük risk — portföy bandı ↔ ileri program (bildirilen KGÜP › program kesimi öncesi tahmin); riskli saatler ve etiket."""
    from pvquant.services import portfoy_sapma_service as sp
    from pvquant.services import portfoy_tahmin_service as pt
    if kural not in pt.KURALLAR:
        raise HTTPException(422, "kural " + "|".join(pt.KURALLAR))
    if not (1 <= gun <= 7):
        raise HTTPException(422, "gun 1-7")
    _pf_kapi(claims, portfoy_id)
    return sp.gelecek(claims["tenant_id"], portfoy_id, gun, kural, _pv_gun(bugun))


@app.get("/v1/portfoyler/{portfoy_id}/dsg")
def portfoy_dsg_perspektif(portfoy_id: str, donem: str | None = None, uretim: str | None = None, anahtar: str | None = None, bugun: str | None = None,
                           claims=Depends(gecerli_kullanici)):
    """v2.591 (F3-D): DSG üç perspektif (bağımsız / DSG içi / sözleşmesel dağılım) zamanlı üyelik ve sözleşmeyle; DSG olmayan portföyde durum «dsg_degil»."""
    from pvquant.ext.platform import dagitim as dg
    from pvquant.services import portfoy_dsg_service as sd
    if anahtar is not None and anahtar not in dg.YONTEMLER:
        raise HTTPException(422, "anahtar " + "|".join(dg.YONTEMLER))
    _pf_kapi(claims, portfoy_id); ur = _fe_uretim(uretim)
    try:
        return sd.donem(claims["tenant_id"], portfoy_id, donem, ur, _pv_gun(bugun), anahtar=anahtar)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/portfoyler/{portfoy_id}/revizyon")
def portfoy_revizyon(portfoy_id: str, hedef: str = "yarin", simdi: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.592 (F3-E): revizyon karar desteği — dayanaklı Türkçe öneriler, etiketli (doğrulanmış / tahmini / eksik bilgi / fırsat geçti). Otomatik bildirim yok."""
    from pvquant.services import portfoy_revizyon_service as rv
    if hedef not in rv.HEDEFLER:
        raise HTTPException(422, "hedef " + "|".join(rv.HEDEFLER))
    _pf_kapi(claims, portfoy_id)
    t = None
    if simdi:
        try:
            t = pd.Timestamp(simdi)
        except (ValueError, TypeError):
            raise HTTPException(422, "simdi ISO zaman")
    return rv.oneriler(claims["tenant_id"], portfoy_id, hedef, t)


@app.get("/v1/portfoyler/{portfoy_id}/finansal-etki")
def portfoyler_finansal_etki(portfoy_id: str, donem: str | None = None, uretim: str | None = None, taze: int = 0, bugun: str | None = None, claims=Depends(gecerli_kullanici)):
    """v2.594 (F3-G): portföy finansal etkisi — santral başına Faz 2 FEM sonucu (gece kaydı ≤36 sa, yoksa anında), portföy bileşenleri (çift sayım bekçisi),
    DSG portföyünde bağımsız / DSG içi / sözleşmesel dağılım satırları ve DSG içi toplam (yerine koyma), gerçekleşen ↔ hesaplanan ↔ varsayımsal sınıfları."""
    from pvquant.services import portfoy_finans_service as pfs
    _pf_kapi(claims, portfoy_id); ur = _fe_uretim(uretim)
    try:
        return pfs.donem(claims["tenant_id"], portfoy_id, donem, ur, _pv_gun(bugun), taze=bool(taze))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/portfoyler/{portfoy_id}/gecmis")
def portfoy_gecmis(portfoy_id: str, tur: str | None = None, donem: str | None = None, n: int = 20, claims=Depends(gecerli_kullanici)):
    """v2.593 (F3-F): gece işinin kayıtlı portföy sonuçları (yalnız ekleme; üyelik/sözleşme anlık görüntüsü meta'da) — yeniden üretilebilirlik."""
    pv = _pv()
    if tur is not None and tur not in pv.SONUC_TURLERI:
        raise HTTPException(422, "tur " + "|".join(pv.SONUC_TURLERI))
    if not (1 <= n <= 100):
        raise HTTPException(422, "n 1-100")
    _pf_kapi(claims, portfoy_id)
    return {"kayitlar": pv.sonuc_gecmisi(claims["tenant_id"], portfoy_id, tur, donem, n)}


@app.get("/v1/portfoyler/{portfoy_id}/gecmis/{kayit_id}")
def portfoy_gecmis_kayit(portfoy_id: str, kayit_id: str, claims=Depends(gecerli_kullanici)):
    from sqlalchemy import text as _text

    from pvquant.db import tenant_baglami as _tb
    _pf_kapi(claims, portfoy_id)
    with _tb(claims["tenant_id"]) as s:
        r = s.execute(_text("SELECT id, hesap_zamani, tur, donem_kodu, donem_bas, donem_bit, sonuc_json, meta_json FROM portfoy_sonuc WHERE id = CAST(:i AS uuid) AND portfoy_id = CAST(:p AS uuid)"),
                      {"i": kayit_id, "p": portfoy_id}).mappings().first()
    if r is None:
        raise HTTPException(404, "kayıt yok")
    return {"id": str(r["id"]), "hesap_zamani": r["hesap_zamani"].isoformat(), "tur": r["tur"], "donem_kodu": r["donem_kodu"], "donem_bas": r["donem_bas"].isoformat(),
            "donem_bit": r["donem_bit"].isoformat(), "sonuc": r["sonuc_json"], "meta": r["meta_json"], "kayitli": True}
