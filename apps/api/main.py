"""PVQuant API — ince katman: HTTP -> services -> HTTP."""
import pandas as pd
from fastapi import FastAPI, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response   # v2.261: /kgup CSV eki modül düzeyinde kullanır
from pydantic import BaseModel
from apps.api.deps import gecerli_kullanici, yazma_yetkisi, yonetici_yetkisi, api_anahtari
from pvquant.services import auth_service, plant_service

# v2.364: İTHALAT ISINDIRMASI — FastAPI'nin sync uçları iş parçacığı havuzunda
# koşar; ağır pipeline zinciri taze işçide İKİ istek tarafından aynı anda İLK
# KEZ tembel-import edilince Python "partially initialized module" /
# KeyError('pvquant.pipeline') yarışı doğuyordu (25 Eyl canlı: dağıtım sonrası
# /forecast ve /fizik-terimleri aralıklı 500 — panel "gelip gidiyor"). Zincir
# burada, açılışta tek iş parçacığıyla bir kez yüklenir; istekler hazır bulur.
import pvquant.pipeline.calibration  # noqa: F401,E402  (forecast+utils+validation zincirini kökten yükler)

import os as _os
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
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_os.environ.get(
        "PVQ_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],   # v2.264: PUT (segment) + DELETE (anahtar/webhook)
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    # v2.94: rapor dosya adi — tarayici bu basligi ancak expose ile gorur
    expose_headers=["Content-Disposition"])

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from apps.api.hiz import limiter, paylasimli_sinir   # 24.10 Faz 1: yonetim yönlendiricisiyle paylaşılır

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 24.10 Faz 1: platform yönetimi (/v1/yonetim/*) — ayrı kapsam, ayrı yönlendirici
from apps.api.yonetim import yonetim as _yonetim   # noqa: E402
from pvquant.services import denetim_service as _denetim   # noqa: E402
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
    tz: str = "Europe/Istanbul"
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
        return {"id": plant_service.olustur(claims["tenant_id"], **p.model_dump())}
    except ValueError as e:   # v2.302: yinelenen ad insan diliyle döner (500 değil)
        raise HTTPException(422, str(e))


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
    from pvquant.services import (plant_service, ozet_service, ingest_service,
                                  forecast_service)
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
                   "anomali": o.anomali_sayisi},
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
    from pvquant.services import iki_adim_service, auth_service as au
    try:
        return iki_adim_service.baslat(claims["sub"], au.eposta_getir(claims["sub"]))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/iki-adim/dogrula")
def iki_adim_dogrula(g: IkiAdimKod, claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    try:
        return iki_adim_service.dogrula_ve_ac(claims["sub"], g.kod)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/iki-adim/kapat")
def iki_adim_kapat(g: IkiAdimKod, claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    try:
        iki_adim_service.kapat(claims["sub"], g.kod)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"tamam": True}


@app.post("/v1/iki-adim/kurtarma-yenile")
def iki_adim_kurtarma(g: IkiAdimKod, claims=Depends(gecerli_kullanici)):
    from pvquant.services import iki_adim_service
    try:
        return iki_adim_service.kurtarma_yenile(claims["sub"], g.kod)
    except ValueError as e:
        raise HTTPException(422, str(e))


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
        return alarm_service.kural_ayarla(claims["tenant_id"], plant_id, p.kurallar, p.esik, alicilar=p.alicilar)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/plants/{plant_id}/damga")
def damga(plant_id: str, request: Request, claims=Depends(gecerli_kullanici)):
    """v2.265 — değişim damgası: son SCADA/koşu/alarm/skill/kalibrasyon zamanları; ETag ile If-None-Match → 304.
    İstemci yalnız damga değişince veri çeker (60 s görünür / 5 dk arka plan)."""
    from pvquant.services import damga_service
    from fastapi.responses import JSONResponse
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
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        return fizik_service.ayar_yaz(claims["tenant_id"], plant_id, p.ayar)
    except ValueError as e:
        raise HTTPException(422, str(e))


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
def portfoy_dsg(gun: int = 30, anahtar: str = "sapma", claims=Depends(gecerli_kullanici)):
    """v2.276 — DSG/toplayıcı portföy netleştirmesi: santral başına ayrı dengesizlik ↔ portföyün netleşmiş dengesizliği.
    29.10: `anahtar` — grubun EDT'sinin üyelere dağıtımı (sapma | esit | uretim; sözleşmesel)."""
    from pvquant.ext.turkiye import dengesizlik as _d
    from pvquant.services import dengesizlik_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14-365")
    if anahtar not in _d.DAGITIM_ANAHTARLARI:
        raise HTTPException(422, "anahtar " + "|".join(_d.DAGITIM_ANAHTARLARI))
    return dengesizlik_service.dsg_ozet(claims["tenant_id"], gun=gun, dagitim_anahtari=anahtar)


@app.get("/v1/portfoy/dsg.csv")
def portfoy_dsg_csv(gun: int = 30, anahtar: str = "sapma", claims=Depends(gecerli_kullanici)):
    """v2.522 (P2b, IH-036) — DSG üye dağılımı belgesi: üye başına EDT tek başına / bireysel / DSG içinde, netleşme farkı, KÜPST, pay (CSV)."""
    from fastapi.responses import Response
    from pvquant.ext.turkiye import dengesizlik as _d
    from pvquant.services import dengesizlik_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14-365")
    if anahtar not in _d.DAGITIM_ANAHTARLARI:
        raise HTTPException(422, "anahtar " + "|".join(_d.DAGITIM_ANAHTARLARI))
    o = dengesizlik_service.dsg_ozet(claims["tenant_id"], gun=gun, dagitim_anahtari=anahtar)
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
    g = date.fromisoformat(gun) if gun else (pd.Timestamp.now(tz="Europe/Istanbul").date() + timedelta(days=1))
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
            "AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=forecast_runs.id) ORDER BY run_at DESC LIMIT 1"),
            {"p": plant_id}).first()


class SayacAyarIstek(BaseModel):
    """v2.523 (P4a): sayaç türü ve lisanssız SCADA durumu; yalnız istekte geçen alanlar değişir, null temizler."""
    sayac_turu: str | None = None                   # 15dk_endeks | diger
    scada_durum: str | None = None                  # bagli | kopuk | yok (lisanssız, LÜY m.21(7))
    scada_kopukluk_baslangic: str | None = None     # YYYY-MM-DD
    uzlastirma_girdi: str | None = None             # v2.526 (P4a-2): scada | sayac — uzlaştırma yeniden hesabında gerçekleşen üretim kaynağı
    uzaktan_acma_var: bool | None = None            # uzaktan açma-kapama yeteneği envanterde
    sistem_kullanim_bedeli_tl_ay: float | None = None   # Karar 14909 bedel göstergesi girdisi (dağıtım faturasından)


@app.get("/v1/dis/santraller", tags=["Dış API"])
def dis_santraller(anahtar=Depends(api_anahtari("tahmin:oku"))):
    """Anahtarın kiracısındaki santraller (kimlik, ad, kurulu güç, saat dilimi)."""
    return [{"id": str(p["id"]), "ad": p["name"], "kapasite_kwp": float(p["capacity_kwp"]), "tz": p["tz"]}
            for p in plant_service.listele(anahtar["tenant_id"])]


@app.get("/v1/dis/santral/{plant_id}/tahmin", tags=["Dış API"])
def dis_tahmin(plant_id: str, request: Request, anahtar=Depends(api_anahtari("tahmin:oku"))):
    """Son koşunun saatlik P10/P50/P90 (kW, UTC). ETag = koşu kimliği; `If-None-Match` eşleşirse 304 (gövde yok).
    Bant yoksa alan null gelir — istemci uydurmasın."""
    from pvquant.services import forecast_service
    row = plant_service.getir(anahtar["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
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
    """KGÜP saatlik program (D-1 15:30 öncesi koşudan); gün verilmezse İstanbul yarını. fmt=csv → TPYS CSV (arşive yazılır)."""
    return _kgup_yaniti(anahtar["tenant_id"], plant_id, gun, kantil, fmt)


@app.get("/v1/dis/santral/{plant_id}/kgup/surumler", tags=["Dış API"])
def dis_kgup_surumler(plant_id: str, gun: str | None = None, n: int = 30, anahtar=Depends(api_anahtari("kgup:oku"))):
    """v2.502 (F-06) — KGÜP sürüm geçmişi (indirilen dosyalar: sürüm, kaynak koşu, kesim, SHA-256)."""
    from datetime import date as _d
    from pvquant.services import kgup_arsiv_service
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
    from datetime import date as _d, datetime as _dt, timedelta as _td
    from pvquant.services import sayac_service
    if kaynak not in ("scada", "sayac"):
        raise HTTPException(422, "kaynak scada ya da sayac olmalı")
    row = plant_service.getir(anahtar["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
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


@app.get("/v1/dis/santral/{plant_id}/alarmlar", tags=["Dış API"])
def dis_alarmlar(plant_id: str, n: int = 20, anahtar=Depends(api_anahtari("alarm:oku"))):
    """v2.528 (P10) — alarm listesi (yeni → eski; en çok 200): kural kodu + Türkçe adı, şiddet, mesaj, zaman, okunma/atama."""
    from pvquant.services import alarm_service
    row = plant_service.getir(anahtar["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    rows = alarm_service.listele(anahtar["tenant_id"], plant_id, max(1, min(int(n), 200)))
    return {"santral_id": str(row["id"]), "santral": row["name"], "alarmlar": [{**r, "kural_adi": alarm_service.KURAL_ETIKET.get(r["kural"], r["kural"])} for r in rows]}


@app.get("/v1/dis/santral/{plant_id}/rapor-donem", tags=["Dış API"])
def dis_rapor_donem(plant_id: str, donem: str | None = None, fmt: str = "json", anahtar=Depends(api_anahtari("rapor:indir"))):
    """v2.528 (P10) — dönem raporu: donem YYYY-MM | YYYY-QN | YYYY (verilmezse son tam ay); fmt json (veri) | html (indirilebilir).
    Panelin Raporlar › Dönem raporu ile aynı hesap; denetim izine düşer."""
    from pvquant.services import aylik_rapor_service
    if fmt not in ("html", "json"):
        raise HTTPException(422, "fmt html ya da json olmalı")
    row = plant_service.getir(anahtar["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
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
    """v2.528 (P10) — santral ayarı yazma (sayaç ayarı alanları: sayac_turu, scada_durum, scada_kopukluk_baslangic, uzaktan_acma_var,
    sistem_kullanim_bedeli_tl_ay, uzlastirma_girdi). Yalnız istekte geçen alanlar değişir, null temizler; panelin PUT sayac-ayar ile aynı doğrulama.
    Künye/segment/tarife bu kapsamda değildir (panelden)."""
    from pvquant.services import sayac_service
    row = plant_service.getir(anahtar["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        an = sayac_service.ayar_dogrula(p.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, f"{e} alanı geçersiz")
    if not an:
        raise HTTPException(422, "değişecek alan yok")
    pj = plant_service.params_birlestir(anahtar["tenant_id"], plant_id, **an)
    _denetim.kaydet("musteri", "sayac_ayar", aktor_id=None, tenant_id=anahtar["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti={**an, "api_anahtar": anahtar["prefix"]})
    return {"santral_id": str(row["id"]), "degisen": an, "ayar": {k: (pj or {}).get(k) for k in ("sayac_turu", "scada_durum", "scada_kopukluk_baslangic", "uzaktan_acma_var", "sistem_kullanim_bedeli_tl_ay", "uzlastirma_girdi")}}


# ------------------------------------------------------------------ v2.264: Yönetim (admin) -----------------
class AnahtarIstek(BaseModel):
    ad: str = ""
    kapsamlar: list[str]
    gecerlilik_gun: int | None = None
    rpm: int = 120


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
        y = api_anahtar_service.uret(claims["tenant_id"], p.ad, p.kapsamlar, p.gecerlilik_gun, p.rpm)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _denetim.kaydet("musteri", "anahtar_uret", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="api_key", nesne_id=y.get("id"),
                    ayrinti={"ad": p.ad, "kapsamlar": p.kapsamlar, "rpm": p.rpm})   # düz anahtar YAZILMAZ
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
                    ayrinti={"url": p.url, "plant_id": p.plant_id})   # secret YAZILMAZ
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
        return paylasim_service.paylas(claims["tenant_id"], claims["sub"], {"id": p.plant_id},
                                       p.hedef_eposta, p.izinler, p.bitis, p.takma_ad)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.delete("/v1/paylasimlar/{paylasim_id}", tags=["Yönetim"])
def paylasim_iptal(paylasim_id: str, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import paylasim_service
    if not paylasim_service.iptal(claims["tenant_id"], claims["sub"], paylasim_id):
        raise HTTPException(404, "paylaşım yok ya da zaten iptal")
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


@app.put("/v1/plants/{plant_id}/segment")
def segment_ayarla(plant_id: str, p: SegmentIstek, claims=Depends(yazma_yetkisi())):
    """v2.260 — piyasa segmenti (YEKDEM / serbest / lisanssız …) ve UEVÇB kodu; params_json'a yazılır."""
    from pvquant.ext.turkiye.segment import Segment
    from pvquant.services import plant_service, dengesizlik_service
    try:
        seg = Segment(p.segment)
    except ValueError:
        raise HTTPException(422, f"segment: {[s.value for s in Segment]}")
    anahtarlar = {"segment": seg.value}
    if p.uevcb:
        anahtarlar["uevcb"] = p.uevcb.strip()[:32]
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **anahtarlar)
    _denetim.kaydet("musteri", "santral_segment", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=plant_id,   # v2.516 (#7)
                    ayrinti=dict(anahtarlar))
    return {"params_json": {k: v for k, v in pj.items() if k in ("segment", "uevcb")}, **dengesizlik_service.segment_bilgisi(pj)}


class KunyeTarihIstek(BaseModel):
    """v2.518 (P3a): santral künyesinin tarih alanları (params_json). Hepsi isteğe bağlı; None alanı siler. YYYY-MM-DD."""
    lisans_yururluk: str | None = None
    lisans_bitis: str | None = None
    kabul_tarihi: str | None = None
    isletmeye_giris: str | None = None
    police_bitis: str | None = None
    ced_karar_tarihi: str | None = None
    baglanti_anlasmasi: str | None = None
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
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, epias_santral_id=p.epias_santral_id)
    row["params_json"] = pj
    return epias_uretim_service.durum(claims["tenant_id"], row)


@app.put("/v1/plants/{plant_id}/eak")
def eak_ayarla(plant_id: str, p: EakIstek, claims=Depends(yazma_yetkisi())):
    """v2.275 — EAK alanı (emre amade kapasite) + geçici kısıt + KÜPST katsayıları; params_json'a yazılır, KGÜP/toplayıcı çıktısı ve simülatör okur.
    v2.517 (P2a): piyasa pozisyonu ayarı (program | uretim | sabit MWh/saat) — uzlaştırma hesabının EDM tabanı."""
    from datetime import date as _d
    from pvquant.services import kgup_service, dengesizlik_service
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
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **an)
    _denetim.kaydet("musteri", "eak_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti=dict(an))   # v2.516 (#7)
    row["params_json"] = pj
    return {"eak_bugun": kgup_service.eak_etkin(row, pd.Timestamp.now(tz="Europe/Istanbul").date()),
            "eak_kw": pj.get("eak_kw"), "eak_gecici": pj.get("eak_gecici"), "kupst_n": pj.get("kupst_n"), "kupst_tolerans": pj.get("kupst_tolerans"),
            "dengeleme_birimi": bool(pj.get("dengeleme_birimi")), "ariza_sayisi_ay": int(pj.get("ariza_sayisi_ay") or 0),
            "luy_istisna": bool(pj.get("luy_istisna")),
            "pozisyon": dengesizlik_service.pozisyon_ayari(pj),   # v2.517 (P2a)
            "teminat_risk_katsayisi": pj.get("teminat_risk_katsayisi"),   # v2.522 (P2b)
            "kullanilabilirlik_sozlesme": pj.get("kullanilabilirlik_sozlesme"),   # v2.533 (P8a)
            "butce_kwh_yil": pj.get("butce_kwh_yil")}   # v2.534 (P8b-1)


def _toplayici_yaniti(tenant_id: str, plant_id: str, gun: str | None, fmt: str, adim: int):
    from datetime import date, timedelta
    from pvquant.services import toplayici_service
    if fmt not in ("csv", "xlsx", "json") or adim not in (60, 15):
        raise HTTPException(422, "fmt csv|xlsx|json, adim 60|15")
    row = plant_service.getir(tenant_id, plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    g = date.fromisoformat(gun) if gun else (pd.Timestamp.now(tz="Europe/Istanbul").date() + timedelta(days=1))
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
    return _toplayici_yaniti(anahtar["tenant_id"], plant_id, gun, fmt, adim)


@app.get("/v1/kurallar")
def kurallar_tablosu(tarih: str | None = None, segment: str | None = "lisansli_serbest", claims=Depends(gecerli_kullanici)):
    """29.10.2026 (F-01) — uzlaştırma kuralı ve parametre sürüm tablosu (salt okunur): tarih verilirse o günün kuralı, yoksa tüm satırlar."""
    from pvquant.services import dengesizlik_service
    from pvquant.ext.turkiye import kurallar as kr
    if tarih:
        try:
            from datetime import date as _d
            return dengesizlik_service.kural_ozeti(segment, _d.fromisoformat(tarih))
        except ValueError:
            raise HTTPException(422, "tarih YYYY-MM-DD olmalı")
    return {"segment": segment, "satirlar": kr.tablo(segment)}


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


class OlayGuncelle(BaseModel):
    bitis: str | None = None
    etkilenen_kw: float | None = None
    neden: str | None = None
    eak_gerekcesi: str | None = None
    kanit: str | None = None
    durum: str | None = None            # iptal için


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
    from pvquant.services import saatlik_detay_service, mutabakat_service
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
        pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, **an)
        row["params_json"] = pj
        _denetim.kaydet("musteri", "sayac_ayar", aktor_id=claims["sub"], tenant_id=claims["tenant_id"], nesne_tur="plant", nesne_id=row["id"], ayrinti=an)
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
def piyasa_fiyat(bas: str, bitis: str, claims=Depends(gecerli_kullanici)):
    """v2.258 — saatlik PTF/SMF/yön (UTC); eksik saatler 'senaryo' kaynaklı döner."""
    from pvquant.services import piyasa_service
    idx = pd.date_range(pd.Timestamp(bas, tz="Europe/Istanbul"), pd.Timestamp(bitis, tz="Europe/Istanbul") + pd.Timedelta(hours=23), freq="h").tz_convert("UTC")
    if len(idx) > 24 * 400:
        raise HTTPException(422, "en fazla 400 gun")
    f = piyasa_service.fiyatlar(idx)
    return {"satirlar": [{"ts": ts.isoformat(), "ptf": _kw(r.ptf), "smf": _kw(r.smf), "yon": r.yon, "kaynak": r.kaynak} for ts, r in f.iterrows()],
            "epias_saat": int((f.kaynak == "epias").sum()), "senaryo_saat": int((f.kaynak == "senaryo").sum())}


@app.get("/v1/plants/{plant_id}/saglik")
def saglik(plant_id: str, gun: int = 800, claims=Depends(gecerli_kullanici)):
    """v2.256 — bozunma (%/yıl, YoY) ve performans eğilimi; POA yoksa model-normalize verimle."""
    from pvquant.services import saglik_service, plant_service
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
    if plant_service.getir(claims["tenant_id"], plant_id) is None:
        raise HTTPException(404, "santral yok")
    try:
        t = tarife_service.dogrula(p.tarife) if p.tarife else None
    except ValueError as e:
        raise HTTPException(422, str(e))
    pj = plant_service.params_birlestir(claims["tenant_id"], plant_id, tarife=t)
    return {"tarife": pj.get("tarife")}


@app.get("/v1/plants/{plant_id}/rapor-sablon/{ad}")
def rapor_sablon_uc(plant_id: str, ad: str, ay: str | None = None, gun: int = 30, claims=Depends(gecerli_kullanici)):
    """v2.281 — şablon raporlar (HTML): kapasite-testi | fatura (ay=YYYY-MM) | kullanilabilirlik (gun) | beklenen-gerceklesen (gun). (ENV-F05-5: dördü de burada.)"""
    from pvquant.services import sablon_rapor_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        p = {"ay": ay} if ad == "fatura" else {"gun": gun}
        icerik, dosya = sablon_rapor_service.uret(claims["tenant_id"], row, ad, **p)
    except KeyError:
        raise HTTPException(422, f"şablon: {sablon_rapor_service.SABLONLAR}")
    except ValueError as e:
        raise HTTPException(409, str(e))
    return Response(content=icerik, media_type="text/html; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{dosya}"'})


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
    from pvquant.services import aylik_rapor_service, alarm_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    g = aylik_rapor_service.gonderim_ayari(alarm_service._pj(row))
    g["varsayilan_alicilar"] = alarm_service.alicilar(row); g["posta_yapilandirildi"] = __import__("pvquant.services.posta_service", fromlist=["yapilandirildi"]).yapilandirildi()
    return g


@app.put("/v1/plants/{plant_id}/rapor-gonderim")
def rapor_gonderim_ayarla(plant_id: str, p: RaporGonderimIstek, claims=Depends(yazma_yetkisi())):
    from pvquant.services import aylik_rapor_service, alarm_service
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
    import shutil, tempfile
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
                              mapping=esleme, duplicate_policy=tekrar,
                              ac_limit_kw=row.get("ac_limit_kw"))   # v2.376
        else:
            res = ingest_file(yol, capacity_kwp=float(row["capacity_kwp"]),
                              latitude=row["lat"], longitude=row["lon"],
                              source_timezone=tz, duplicate_policy=tekrar,
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
    run_id = uret_ve_kaydet(claims["tenant_id"], row)
    return {"run_id": str(run_id)}


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
             "sapma": getattr(r, "sapma", None), "etiket": getattr(r, "etiket", None)}   # v2.274 / v2.276
            for r in kosu_gecmisi(claims["tenant_id"], plant_id, n=10)]


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
