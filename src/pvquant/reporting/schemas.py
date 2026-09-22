"""JSON çıktı — Pydantic v2 şeması (Tur 3'te derinleşecek çekirdek)."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class PlantInfo(BaseModel):
    name: str
    capacity_kwp: float
    latitude: float
    longitude: float
    timezone: str


class RunInfo(BaseModel):
    model: str
    model_version: str
    mode: str
    meteo_source: str
    run_at: datetime


class HourlyPoint(BaseModel):
    ts: datetime = Field(description="Aralığın BAŞI, UTC (conventions.timestamp)")
    p50_kw: float
    # v2.350 (şema 1.2.0): olasılık bandı — üründe vardı, JSON'a düşmüyordu
    # (rakip taraması: ≥8 sağlayıcı bant veriyor). Bantsız koşuda null.
    p10_kw: float | None = None
    p90_kw: float | None = None
    energy_kwh: float = Field(description="Saatlik aralıkta p50_kw ile sayısal özdeş")


class DailyPoint(BaseModel):
    date: str
    p50_kwh: float
    p10_kwh: float | None = None
    p90_kwh: float | None = None


class Totals(BaseModel):
    p50_mwh: float
    p10_mwh: float | None = None
    p90_mwh: float | None = None
    capacity_factor_pct: float
    specific_yield_kwh_kwp: float = Field(
        description="IEC 61724-1 dönem özgül verimi")


class Conventions(BaseModel):
    """v2.350: makine-okunur sözleşme — entegratörün en sık hata kaynağı
    damga anlamı ve eksik değerdi (rakip taraması: PV_Live/Solcast açıkça yazar)."""
    timestamp: str = Field(default="interval_start",
                           description="hourly.ts aralığın başını gösterir")
    period: str = Field(default="PT1H", description="ISO 8601 süre — saatlik")
    timezone: str = "UTC"
    missing: str = Field(default="null",
                         description="Hesaplanamayan/ölçülmeyen değer null'dur; "
                                     "uydurulmaz, sıfırla doldurulmaz")


class AccuracyDay(BaseModel):
    date: str
    measured: bool = Field(description="False ise satır dürüst boştur (ölçüm yok)")
    wmape_0_24: float | None = None
    wmape_24_72: float | None = None
    naive_wmape: float | None = None
    skill: float | None = Field(default=None, description="1 − wmape/naif, 0–1 kesir")
    coverage_pct: int | None = None


class Accuracy(BaseModel):
    """v2.350: gece karnesi JSON'da — rakip taramasında API gövdesinde
    eşdeğeri bulunmayan alan (PVQuant'ın ayırt edici farkı, artık makine-okunur)."""
    window_days: int
    last_measured_date: str
    wmape_pct: float | None = None
    nmae_pct: float | None = Field(default=None, description="Kurulu güce normalize MAE")
    naive_wmape_pct: float | None = None
    skill_vs_naive_pct: float | None = None
    band_coverage_pct: float | None = None
    band_target_pct: float = 80.0
    daily: list[AccuracyDay] = []


class HybridQuality(BaseModel):
    """Mod C holdout sınavı — kronolojik son %20 (yalnız hibrit aktifken)."""
    holdout_mape_pct: float
    holdout_rmse_kw: float | None = None
    physics_mape_pct: float | None = None
    improvement_pct: float | None = None
    holdout_hours: int | None = None
    note: str | None = None      # marjinal iyileşme uyarısı (< kapı eşiği %3)


class Quality(BaseModel):
    mape_pct: float | None = None
    deviation_pct: float | None = None
    eta_bos: float | None = None
    bg: float | None = None
    hybrid: HybridQuality | None = None
    warnings: list[str] = []


UNITS: dict[str, str] = {
    "p50_kw": "kW", "p10_kw": "kW", "p90_kw": "kW", "energy_kwh": "kWh",
    "p50_kwh": "kWh", "p10_kwh": "kWh", "p90_kwh": "kWh",
    "p50_mwh": "MWh", "p10_mwh": "MWh", "p90_mwh": "MWh",
    "capacity_factor_pct": "%", "specific_yield_kwh_kwp": "kWh/kWp",
    "capacity_kwp": "kWp", "mape_pct": "%", "deviation_pct": "%",
    "wmape_pct": "%", "nmae_pct": "%", "naive_wmape_pct": "%",
    "skill_vs_naive_pct": "%", "band_coverage_pct": "%", "coverage_pct": "%",
}

SCHEMA_URL = "/v1/report/json-schema"   # apps.api: ForecastReport.model_json_schema()


class ForecastReport(BaseModel):
    schema_version: str = "1.0.0"   # build_json ctx'ten geçirir (SCHEMA_VERSION)
    # v2.350 (1.2.0): yayımlı sözleşme + izlenebilirlik + birim bloğu.
    # Hepsi EKLEMEdir — 1.1.0 tüketicileri aynen çalışır; yalnız quality
    # sayıları yuvarlandı (14 haneli ham float → anlamlı hane).
    schema_url: str = SCHEMA_URL
    report_id: str | None = Field(default=None, description="PVQ-<tarih>-<mod>-<sıra>; report_log izi")
    generated_at: datetime
    conventions: Conventions = Conventions()
    units: dict[str, str] = UNITS
    plant: PlantInfo
    run: RunInfo
    totals: Totals
    daily: list[DailyPoint]
    hourly: list[HourlyPoint]
    accuracy: Accuracy | None = Field(default=None, description="Ölçüm yoksa null")
    quality: Quality


def _hybrid_quality(ctx) -> "HybridQuality | None":
    """Sözleşme koruması: mode!='C' ya da holdout yoksa blok HİÇ üretilmez
    (null değil, YOK) — Mod B tüketicileri geriye dönük aynen çalışır."""
    if ctx.mode != "C" or ctx.holdout_mape_pct is None:
        return None
    imp = ctx.holdout_improvement_pct
    not_metni = None
    if imp is not None and imp < 3.0:   # terfi kapısıyla AYNI eşik (config)
        not_metni = ("marjinal iyileşme — kapı eşiği %3'ün altında; "
                     "fizikten istatistiksel ayrışma zayıf olabilir")
    return HybridQuality(
        holdout_mape_pct=round(ctx.holdout_mape_pct, 2),
        holdout_rmse_kw=round(ctx.holdout_rmse_kw, 1)
            if ctx.holdout_rmse_kw is not None else None,
        physics_mape_pct=round(ctx.holdout_physics_mape_pct, 2)
            if ctx.holdout_physics_mape_pct is not None else None,
        improvement_pct=round(imp, 1) if imp is not None else None,
        holdout_hours=ctx.holdout_hours,
        note=not_metni,
    )


def _accuracy(ctx) -> "Accuracy | None":
    """v2.350: özet report_service'in iliştirdiği ctx.dogrulama'dan (vitrin/Excel
    ile AYNI hesap — 'üç yüzey aynı sayıyı söyler'); günlük satırlar s07 ile
    aynı üreticiden (_karne_satirlari, bos_kabul — ölçülmeyen gün measured=False
    ve null ile DURUR, silinmez). Özet yoksa blok null."""
    dg = getattr(ctx, "dogrulama", None)
    if not dg:
        return None
    gunluk: list[AccuracyDay] = []
    if getattr(ctx, "karne", None) is not None:
        from pvquant.services.report_html_service import _karne_satirlari
        for d in _karne_satirlari(ctx.karne, getattr(ctx, "karne_kapsama", None),
                                  bos_kabul=True):
            gunluk.append(AccuracyDay(
                date=d["date"], measured=bool(d["olculdu"]),
                wmape_0_24=d.get("wmape_0_24"), wmape_24_72=d.get("wmape_24_72"),
                naive_wmape=d.get("naif_wmape"), skill=d.get("skill"),
                coverage_pct=d.get("kapsama_pct")))
    return Accuracy(
        window_days=dg["gun"], last_measured_date=dg["son_gun"],
        wmape_pct=dg.get("wmape_pct"), nmae_pct=dg.get("nmae_pct"),
        naive_wmape_pct=dg.get("naif_wmape_pct"),
        skill_vs_naive_pct=dg.get("beceri_naif_pct"),
        band_coverage_pct=dg.get("bant_kapsama_pct"),
        band_target_pct=float(dg.get("bant_hedef_pct") or 80.0),
        daily=gunluk)


def _r(x, n):
    return None if x is None else round(float(x), n)


def build_json(ctx) -> str:
    import json as _json
    h = ctx.hourly
    # bant: saatlikte son_kosu p10/p90 kolonları (v2.96), günlükte daily_p10/p90;
    # ikisi de yoksa null — bantsızlık eksiklik değil, dürüst yokluktur (v2.141)
    hb = "p10_kw" in h.columns and "p90_kw" in h.columns
    db = ctx.has_band

    def _hv(r, k):
        v = r[k] if hb else None
        return None if v is None or v != v else round(float(v), 2)

    rapor = ForecastReport(
        schema_version=ctx.schema_version,
        report_id=getattr(ctx, "report_id", None),
        generated_at=ctx.run_at_utc,
        plant=PlantInfo(name=ctx.plant_name, capacity_kwp=ctx.capacity_kwp,
                        latitude=ctx.latitude, longitude=ctx.longitude,
                        timezone=ctx.plant_tz),
        run=RunInfo(model=ctx.model_name, model_version=ctx.model_version,
                    mode=ctx.mode, meteo_source=ctx.meteo_source,
                    run_at=ctx.run_at_utc),
        totals=Totals(p50_mwh=round(ctx.total_mwh, 2),
                      p10_mwh=_r(ctx.daily_p10.sum() / 1000.0, 2) if db else None,
                      p90_mwh=_r(ctx.daily_p90.sum() / 1000.0, 2) if db else None,
                      capacity_factor_pct=round(ctx.capacity_factor_pct, 2),
                      specific_yield_kwh_kwp=round(ctx.specific_yield, 2)),
        daily=[DailyPoint(date=f"{g:%Y-%m-%d}", p50_kwh=round(float(v), 1),
                          p10_kwh=_r(ctx.daily_p10.get(g), 1) if db else None,
                          p90_kwh=_r(ctx.daily_p90.get(g), 1) if db else None)
               for g, v in ctx.daily_kwh.items()],
        hourly=[HourlyPoint(ts=ts.to_pydatetime(),
                            p50_kw=round(float(r["p50_kw"]), 2),
                            p10_kw=_hv(r, "p10_kw"), p90_kw=_hv(r, "p90_kw"),
                            energy_kwh=round(float(r["energy_kwh"]), 2))
                for ts, r in h.iterrows()],
        accuracy=_accuracy(ctx),
        # v2.350: yuvarlama disiplini — 25.902187499941466 gibi ham float
        # entegratöre anlam taşımaz (hybrid bloğu zaten 2 haneydi, hizalandı)
        quality=Quality(mape_pct=_r(ctx.mape_pct, 2),
                        deviation_pct=_r(ctx.deviation_pct, 2),
                        eta_bos=_r(ctx.eta_bos, 3), bg=_r(ctx.bg, 3),
                        hybrid=_hybrid_quality(ctx),
                        warnings=ctx.warnings or []),
    )
    d = rapor.model_dump(mode="json")
    if d["quality"].get("hybrid") is None:      # yok = YOK (null değil)
        d["quality"].pop("hybrid", None)
    return _json.dumps(d, indent=2, ensure_ascii=False)
