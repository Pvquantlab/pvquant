"""PVQuant API — ince katman: HTTP -> services -> HTTP."""
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import Response   # v2.261: /kgup CSV eki modül düzeyinde kullanır
from pydantic import BaseModel
from apps.api.deps import gecerli_kullanici, yazma_yetkisi, yonetici_yetkisi, api_anahtari
from pvquant.services import auth_service, plant_service

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

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class GirisIstek(BaseModel):
    email: str
    sifre: str


@app.post("/v1/auth/login")
@limiter.limit("5/minute")
def login(request: Request, g: GirisIstek):
    r = auth_service.giris(g.email, g.sifre)
    if r is None:
        raise HTTPException(401, "hatali")
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


@app.post("/v1/plants")
def plant_ekle(p: PlantIstek, claims=Depends(yazma_yetkisi())):
    return {"id": plant_service.olustur(claims["tenant_id"], **p.model_dump())}


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


@app.get("/v1/plants/{plant_id}/hata-matrisi")
def hata_matrisi_uc(plant_id: str, gun: int = 30, kova: str = "0-24",
                    claims=Depends(gecerli_kullanici)):
    """v2.111 — saat x gun isaretli hata matrisi (p50 - gercek, kW).
    Hesap accuracy_service'te; kurallar gece_skill ile ozdes (flag='valid',
    gunduz > %2 kapasite, yerel gun penceresi). Bos matris 200 + bos listeler
    doner — 'birikiyor' durumunu istemci anlatir."""
    from pvquant.services import accuracy_service
    if not (1 <= gun <= 120):
        raise HTTPException(422, "gun 1-120 araliginda olmali")
    try:
        return accuracy_service.hata_matrisi(
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
        return alarm_service.kural_ayarla(claims["tenant_id"], plant_id, p.kurallar, p.esik)
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


@app.get("/v1/plants/{plant_id}/nowcast")
def nowcast(plant_id: str, claims=Depends(gecerli_kullanici)):
    """v2.266 — kısa ufuk (0–6 s): ölçüm persistansı ile P50 harmanı. Uydu DEĞİL; SCADA tazeliği >3 s ise devre dışı ('—')."""
    from pvquant.services import nowcast_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return nowcast_service.hesapla(claims["tenant_id"], row)


@app.get("/v1/hakkinda")
def hakkinda(claims=Depends(gecerli_kullanici)):
    """v2.270 — Veri kaynakları ve lisanslar (Gizlilik Anayasası v2.245 istisnası: atıf yalnız burada, rapor künyesinde, README'de)."""
    from pvquant.services import kaynak_service
    return kaynak_service.hakkinda()


@app.get("/v1/portfoy")
def portfoy(claims=Depends(gecerli_kullanici)):
    """v2.263 — kiracının tüm santralleri: kapasite, son ölçüm, 30g WMAPE, bugün/yarın beklenen, açık alarm; toplamlar."""
    from pvquant.services import portfoy_service
    return portfoy_service.ozet(claims["tenant_id"])


def _kgup_yaniti(tenant_id: str, plant_id: str, gun: str | None, kantil: str, fmt: str):
    """v2.260/v2.264 — panel ve dış API'nin ortak KGÜP gövdesi."""
    from datetime import date, timedelta
    from pvquant.services import kgup_service, plant_service
    if kantil not in ("p10", "p50", "p90"):
        raise HTTPException(422, "kantil p10|p50|p90")
    row = plant_service.getir(tenant_id, plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    # v2.262: 'yarın' santralin piyasa gününe göre (İstanbul), sunucunun UTC takvimine göre değil —
    # 21:00 UTC sonrası UTC 'bugün' hâlâ dünkü piyasa günüdür; canlı kontrolde KGÜP kartı bu yüzden boş kaldı.
    g = date.fromisoformat(gun) if gun else (pd.Timestamp.now(tz="Europe/Istanbul").date() + timedelta(days=1))
    pj = row.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j; pj = _j.loads(pj)
    r = kgup_service.uret(tenant_id, {"id": str(row["id"]), "capacity_kwp": float(row["capacity_kwp"]), "ac_limit_kw": row.get("ac_limit_kw"), "uevcb": pj.get("uevcb")}, g, kantil)
    if "hata" in r:
        raise HTTPException(409, r["hata"])
    if fmt == "json":
        return {k: v for k, v in r.items() if k != "csv"}
    return Response(content=r["csv"].encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{r["dosya_adi"]}"'})


@app.get("/v1/plants/{plant_id}/kgup")
def kgup_dosyasi(plant_id: str, gun: str | None = None, kantil: str = "p50", fmt: str = "csv", claims=Depends(gecerli_kullanici)):
    """v2.260 — KGÜP saatlik program (D-1 15:30 öncesi koşudan). fmt=csv → TPYS CSV eki; fmt=json → önizleme."""
    return _kgup_yaniti(claims["tenant_id"], plant_id, gun, kantil, fmt)


# ------------------------------------------------------------------ v2.264: Dış API (X-API-Key) --------------
def _son_kosu_kimligi(tenant_id: str, plant_id: str):
    from sqlalchemy import text as _t
    from pvquant.db import tenant_baglami as _tb
    with _tb(tenant_id) as s:
        return s.execute(_t(
            "SELECT id, run_at, mode FROM forecast_runs WHERE plant_id=:p "
            "AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=forecast_runs.id) ORDER BY run_at DESC LIMIT 1"),
            {"p": plant_id}).first()


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
    """KGÜP saatlik program (D-1 15:30 öncesi koşudan); gün verilmezse İstanbul yarını. fmt=csv → TPYS CSV."""
    return _kgup_yaniti(anahtar["tenant_id"], plant_id, gun, kantil, fmt)


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
    return {"anahtarlar": api_anahtar_service.listele(claims["tenant_id"]), "kapsamlar": list(api_anahtar_service.CANLI_KAPSAMLAR)}


@app.post("/v1/api-anahtarlari", tags=["Yönetim"], status_code=201)
def anahtar_uret(p: AnahtarIstek, claims=Depends(yonetici_yetkisi())):
    """Düz anahtar YALNIZ bu yanıtta; sunucu sha256 dışında hiçbir şey saklamaz."""
    from pvquant.services import api_anahtar_service
    try:
        return api_anahtar_service.uret(claims["tenant_id"], p.ad, p.kapsamlar, p.gecerlilik_gun, p.rpm)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.delete("/v1/api-anahtarlari/{anahtar_id}", tags=["Yönetim"])
def anahtar_iptal(anahtar_id: str, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import api_anahtar_service
    if not api_anahtar_service.iptal(claims["tenant_id"], anahtar_id):
        raise HTTPException(404, "anahtar yok ya da zaten iptal")
    return {"iptal": True}


@app.get("/v1/webhooklar", tags=["Yönetim"])
def webhook_listesi(claims=Depends(yonetici_yetkisi())):
    from pvquant.services import webhook_service
    return {"webhooklar": webhook_service.listele(claims["tenant_id"]), "olaylar": ["tahmin.yeni"]}


@app.post("/v1/webhooklar", tags=["Yönetim"], status_code=201)
def webhook_ekle(p: WebhookIstek, claims=Depends(yonetici_yetkisi())):
    """`secret` YALNIZ bu yanıtta gösterilir; alıcı imzayı onunla doğrular."""
    from pvquant.services import webhook_service
    try:
        return webhook_service.ekle(claims["tenant_id"], p.url, p.plant_id, p.olaylar)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.delete("/v1/webhooklar/{webhook_id}", tags=["Yönetim"])
def webhook_sil(webhook_id: str, claims=Depends(yonetici_yetkisi())):
    from pvquant.services import webhook_service
    if not webhook_service.sil(claims["tenant_id"], webhook_id):
        raise HTTPException(404, "webhook yok")
    return {"silindi": True}


@app.post("/v1/webhooklar/{webhook_id}/dene", tags=["Yönetim"])
def webhook_dene(webhook_id: str, claims=Depends(yonetici_yetkisi())):
    """'deneme' olayı gönderir; alıcının döndürdüğü HTTP durumunu geri verir (0 = ulaşılamadı)."""
    from pvquant.services import webhook_service
    r = webhook_service.gonder(claims["tenant_id"], "deneme", {"olay": "deneme", "mesaj": "PVQuant webhook denemesi"}, webhook_id=webhook_id)
    if not r:
        raise HTTPException(404, "webhook yok ya da pasif")
    return r[0]


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
    return {"params_json": {k: v for k, v in pj.items() if k in ("segment", "uevcb")}, **dengesizlik_service.segment_bilgisi(pj)}


@app.get("/v1/plants/{plant_id}/dengesizlik")
def dengesizlik(plant_id: str, gun: int = 90, claims=Depends(gecerli_kullanici)):
    """v2.259 — karnenin TL dili: PVQuant programı vs naif program dengesizlik maliyeti (DUY), aylık + toplam."""
    from pvquant.services import dengesizlik_service, plant_service
    if not (14 <= gun <= 365):
        raise HTTPException(422, "gun 14-365 araliginda olmali")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    return dengesizlik_service.simulasyon(claims["tenant_id"], {"id": str(row["id"]), "params_json": row.get("params_json")}, gun=gun)


@app.get("/v1/piyasa/durum")
def piyasa_durum(claims=Depends(gecerli_kullanici)):
    """v2.258 — EPİAŞ entegrasyonunun durumu: kimlik var mı, son fiyat saati, senaryo değerleri."""
    from pvquant.services import piyasa_service
    return piyasa_service.durum()


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
    return backtest_service.konformal_backtest(claims["tenant_id"], {"id": str(row["id"]), "capacity_kwp": float(row["capacity_kwp"])}, gun=gun)


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
    return {
        "plant_id": plant_id,
        "hesap_zamani": b["hesap_zamani"].max().isoformat(),
        "beklenti": [
            {"ay": int(r.ay), "p10": _kw(r.ghi_p10_kwh_m2),
             "p50": _kw(r.ghi_p50_kwh_m2), "p90": _kw(r.ghi_p90_kwh_m2),
             "yil_sayisi": int(r.yil_sayisi)} for r in b.itertuples()],
        "yillik": [
            {"yil": int(r.yil), "ay": int(r.ay),
             "ghi_kwh_m2": _kw(r.ghi_kwh_m2)} for r in y.itertuples()],
    }


@app.get("/v1/healthz")
def healthz():
    return {"ok": True}


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
                claims=Depends(yazma_yetkisi())):
    """v2.87 Faz 2: onayli kararla dogrula + kalicilastir. Kapasite/konum
    santral KAYDINDAN okunur (kunye tek gercek, formda tekrar yok).
    Karne (QualityReport) cevapta doner — SPA yorumsuz gosterir."""
    from pvquant.io.ingestion.pipeline import MappingFailedError, ingest_file
    from pvquant.services import ingest_service
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
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
                              mapping=esleme)
        else:
            res = ingest_file(yol, capacity_kwp=float(row["capacity_kwp"]),
                              latitude=row["lat"], longitude=row["lon"],
                              source_timezone=tz)
        out = ingest_service.yukle_ve_kaydet(
            claims["tenant_id"], plant_id, dosya.filename or yol,
            capacity_kwp=float(row["capacity_kwp"]),
            latitude=row["lat"], longitude=row["lon"],
            source_timezone=tz, hazir_sonuc=res)
    except MappingFailedError as e:
        raise HTTPException(422, "otomatik esleme kurulamadi: "
                            f"{e} — simdilik Streamlit sihirbazini kullanin")
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
             "sapma": getattr(r, "sapma", None)}   # v2.274
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
