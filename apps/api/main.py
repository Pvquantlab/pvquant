"""PVQuant API — ince katman: HTTP -> services -> HTTP."""
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from apps.api.deps import gecerli_kullanici, yazma_yetkisi
from pvquant.services import auth_service, plant_service

import os as _os
try:
    import sentry_sdk
    if _os.environ.get("PVQ_SENTRY_DSN"):
        sentry_sdk.init(dsn=_os.environ["PVQ_SENTRY_DSN"],
                        traces_sample_rate=0)
except ImportError:
    pass  # sentry-sdk kurulu değilse sessiz geç (dev ortamı)

app = FastAPI(title="PVQuant API", version="0.1")

# v2.73-B: dev SPA (vite, :5173) tarayici kapisi. Prod'da SPA ayni alan
# adindan (Caddy /v1) sunulur — oraya CORS gerekmez; liste env ile dar tutulur.
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_os.environ.get(
        "PVQ_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"], allow_headers=["Authorization",
                                                  "Content-Type"],
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
    from pvquant.services import forecast_service
    if not (1 <= hours <= 384):
        raise HTTPException(422, "hours 1-384 araliginda olmali")
    df = forecast_service.son_kosu(claims["tenant_id"], plant_id)
    if df is None:
        raise HTTPException(404, "tahmin kosusu yok")
    kosu = forecast_service.kosu_gecmisi(claims["tenant_id"], plant_id, n=1)
    df = df.iloc[:hours]
    return {
        "plant_id": plant_id,
        "run_at": kosu[0].run_at.isoformat() if kosu else None,
        "mode": kosu[0].mode if kosu else None,
        "hours": int(len(df)),
        "series": [
            {"ts_utc": ts.isoformat(), "p10_kw": _kw(r.p10_kw),
             "p50_kw": _kw(r.p50_kw), "p90_kw": _kw(r.p90_kw)}
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
    from pvquant.services import plant_service, ozet_service, ingest_service
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
    aylik = [] if ay.empty else [
        {"ay": r["ay"], "mwh": _kw(r["uretim_mwh"]),
         # aylik_ozet kolonu 'saat' (v2.68) — 'saglam_saat' degil (canli ders #2)
         "saglam_saat": int(r["saat"]) if "saat" in r else None,
         "kapsam_pct": _kw(r["kapsam_pct"]) if "kapsam_pct" in r else None}
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
    return {
        "kova": bucket,
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
             "naif_wmape": _naif_wmape(r)}
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
    return [{"run_at": r.run_at.isoformat(), "mode": r.mode, "model": r.model}
            for r in kosu_gecmisi(claims["tenant_id"], plant_id, n=10)]


@app.get("/v1/plants/{plant_id}/report")
def rapor_uret(plant_id: str, fmt: str, claims=Depends(gecerli_kullanici)):
    """v2.94: uret() -> bytes; dosya adi basliga yazilir, tarayici indirir."""
    from fastapi.responses import Response
    from pvquant.services import report_service
    if fmt not in _RAPOR_MIME:
        raise HTTPException(422, f"bilinmeyen format: {fmt}")
    row = plant_service.getir(claims["tenant_id"], plant_id)
    if row is None:
        raise HTTPException(404, "santral yok")
    try:
        veri, ad, _ts = report_service.uret(claims["tenant_id"], row, fmt)
    except ValueError as e:
        raise HTTPException(409, str(e))   # "once tahmin uretin" durustce doner
    return Response(content=veri, media_type=_RAPOR_MIME[fmt],
                    headers={"Content-Disposition":
                             f'attachment; filename="{ad}"'})
