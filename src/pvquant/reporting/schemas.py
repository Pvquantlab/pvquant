"""JSON çıktı — Pydantic v2 şeması (Tur 3'te derinleşecek çekirdek)."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
# v2.535 dayanak künyeleri [KARAR_14968] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    "Karar 14968: EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711"
)


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


class IndependentValidationReference(BaseModel):
    hours: int
    wmape_pct: float | None = None
    model_wmape_pct: float | None = Field(default=None, description="PVQuant WMAPE, aynı saat kümesinde")
    skill_pct: float | None = Field(default=None, description="1 − WMAPE/WMAPE_ref, puan; pozitif = PVQuant daha iyi")
    verdict: str | None = None
    note: str | None = None


class IndependentValidation(BaseModel):
    """v2.576 (Faz 1 F1-E): bağımsız doğrulama — yayımlandığı andaki tahmin × uygun ölçüm × referanslar; bagimsiz_dogrulama_service sözlüğü.
    Gece karnesinden (accuracy) ayrı hesaptır: saat başına tek tahmin, havuzlanmış WMAPE, nedenli dışlama, yeniden üretim kimliği."""
    status: str = Field(description="DOĞRULANMIŞ ÖLÇÜM | EKSİK DEĞERLENDİRME | GERİYE DÖNÜK SİMÜLASYON")
    dictionary_version: str
    rule: str = Field(description="program | gun_oncesi | gun_ici | ufuk")
    source: str = Field(description="scada (tesis brüt AC) | sayac (bağlantı noktası net)")
    period_start: str
    period_end: str
    timezone: str | None = None
    hours_evaluated: int
    days_evaluated: int
    wmape_pct: float | None = None
    wmape_daily_mean_pct: float | None = None
    mae_kw: float | None = None
    rmse_kw: float | None = None
    nmae_pct: float | None = None
    nrmse_pct: float | None = None
    mbe_kw: float | None = Field(default=None, description="tahmin − gerçek; pozitif = fazla tahmin")
    nmbe_pct: float | None = None
    energy_bias_kwh_per_day: float | None = None
    picp80_pct: float | None = None
    below_p10_pct: float | None = None
    above_p90_pct: float | None = None
    interval_width_pct: float | None = Field(default=None, description="ortalama (P90 − P10) / kurulu güç")
    winkler_kw: float | None = None
    measurement_coverage_pct: float | None = None
    evaluated_daytime_pct: float | None = None
    excluded_daytime_hours: dict[str, int] = {}
    clipping_hours: int = 0
    references: dict[str, IndependentValidationReference] = {}
    worst_days: list[dict] = []
    run_count: int = 0
    run_set_sha: str
    hour_set_sha: str
    computed_at: str
    software_version: str | None = None
    record_id: str | None = None


def _independent_validation(ctx) -> "IndependentValidation | None":
    s = getattr(ctx, "bagimsiz", None)
    if not s:
        return None
    from pvquant.services.sablon_rapor_service import dogrulama_durumu
    m = s.get("metrik") or {}; b = s.get("butunluk") or {}; meta = s.get("meta") or {}; o = b.get("olcum") or {}
    durum, _ = dogrulama_durumu(s)
    refs = {k: IndependentValidationReference(hours=int(v.get("n_saat") or 0), wmape_pct=v.get("wmape"), model_wmape_pct=v.get("model_wmape_ayni_saatler"),
                                              skill_pct=v.get("beceri_pct"), verdict=v.get("sonuc"), note=v.get("tanim")) for k, v in (s.get("referans") or {}).items()}
    return IndependentValidation(
        status=durum, dictionary_version=str(meta.get("sozluk_surumu")), rule=str(meta.get("kural")), source=str(meta.get("kaynak", "scada")),
        period_start=str(meta.get("donem", {}).get("bas")), period_end=str(meta.get("donem", {}).get("bit")), timezone=meta.get("donem", {}).get("tz"),
        hours_evaluated=int(m.get("n_saat") or 0), days_evaluated=int(m.get("n_gun") or 0), wmape_pct=m.get("wmape"), wmape_daily_mean_pct=m.get("wmape_gunluk_ort"),
        mae_kw=m.get("mae_kw"), rmse_kw=m.get("rmse_kw"), nmae_pct=m.get("nmae"), nrmse_pct=m.get("nrmse"), mbe_kw=m.get("mbe_kw"), nmbe_pct=m.get("nmbe"),
        energy_bias_kwh_per_day=m.get("enerji_sapma_kwh_gun"), picp80_pct=m.get("picp80"), below_p10_pct=m.get("p10_alti"), above_p90_pct=m.get("p90_ustu"),
        interval_width_pct=m.get("bant_genisligi_oran"), winkler_kw=m.get("winkler_kw"), measurement_coverage_pct=o.get("kapsama_pct"),
        evaluated_daytime_pct=b.get("degerlendirilen_pct"), excluded_daytime_hours={str(k): int(v) for k, v in (b.get("gunduz_dislanan") or {}).items()},
        clipping_hours=int(b.get("kirpma_saat_degerlendirilen") or 0), references=refs,
        worst_days=[{"date": g.get("kesit"), "wmape_pct": g.get("wmape"), "hours": g.get("n_saat"), "energy_bias_kwh": g.get("enerji_sapma_kwh_gun")} for g in (s.get("kesit") or {}).get("en_zayif_gunler", [])],
        run_count=int(meta.get("kosu_sayisi") or 0), run_set_sha=str(meta.get("kosu_kumesi_sha")), hour_set_sha=str(meta.get("saat_kumesi_sha")),
        computed_at=str(s.get("hesap_zamani") or meta.get("hesap_zamani")), software_version=meta.get("yazilim_surumu"), record_id=s.get("id"))


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


class FinancialImpactComponent(BaseModel):
    """v2.585 (Faz 2 F2-G): finansal sonuç satırı; işaret artı = santral lehine (alacak), eksi = aleyhine (borç)."""
    code: str
    name: str
    net_tl: float | None = None
    credit_tl: float | None = None
    debit_tl: float | None = None
    quality: str = Field(description="resmi | hesaplanan | sozlesme_tahmini | senaryo | eksik")
    included_in_total: bool = True
    coverage_hours: int | None = None
    expected_hours: int | None = None
    source: str | None = None
    rule_version: str | None = None
    notes: list[str] = []


class FinancialImpactRecommendation(BaseModel):
    code: str
    kind: str = Field(description="bilgi | oneri | eylem")
    text: str
    page: str | None = None


class FinancialImpact(BaseModel):
    """v2.585 (Faz 2 F2-G): Finansal Etki Merkezi bloğu — arayüzle aynı hesap sürümü ve kapsam (finansal_etki_service.ozet/son).
    Tutarlar PVQuant'ın yeniden hesabıdır; resmî uzlaştırma sonucu değildir (status ve quality alanları bunu taşır)."""
    status: str = Field(description="RESMÎ KARŞILAŞTIRMALI | TAHMİNİ HESAP | SENARYO HESABI | EKSİK HESAP")
    dictionary_version: str
    sign_convention: str
    is_scenario: bool = False
    period_type: str
    period_code: str
    period_start: str
    period_end: str
    timezone: str | None = None
    period_hours: int | None = None
    production_input: str | None = None
    planned_mwh: float | None = None
    actual_mwh: float | None = None
    forecast_mwh: float | None = None
    deviation_mwh: float | None = None
    deviation_pct: float | None = None
    deviation_direction: str | None = None
    measured_hours: int | None = None
    expected_hours: int | None = None
    measurement_boundary: str | None = None
    program_source: str | None = None
    components: list[FinancialImpactComponent] = []
    total_net_tl: float | None = None
    total_credit_tl: float | None = None
    total_debit_tl: float | None = None
    total_quality: str | None = None
    total_included: list[str] = []
    total_missing: list[str] = []
    official_available: bool = False
    official_differences_tl: dict[str, float] = {}
    official_statuses: dict[str, str] = {}
    price_epias_hours: int | None = None
    price_scenario_hours: int | None = None
    tariff_type: str | None = None
    tariff_sha: str | None = None
    market_position: str | None = None
    rule_version: str | None = None
    recommendations: list[FinancialImpactRecommendation] = []
    computed_at: str | None = None
    software_version: str | None = None
    record_id: str | None = None


def _financial_impact(ctx) -> "FinancialImpact | None":
    s = getattr(ctx, "finansal", None)
    if not s:
        return None
    from pvquant.services.sablon_rapor_service import finansal_durum
    d = s.get("donem") or {}; u = s.get("uretim") or {}; top = s.get("toplam") or {}; meta = s.get("meta") or {}; uz = s.get("uzlastirma") or {}; r = uz.get("resmi") or {}
    g = u.get("gerceklesen") or {}; sap = u.get("sapma") or {}; pl = u.get("planlanan") or {}
    durum, _ = finansal_durum(s)
    return FinancialImpact(
        status=durum, dictionary_version=str(meta.get("sozluk_surumu")), sign_convention=str(meta.get("isaret") or ""), is_scenario=bool(meta.get("senaryo")),
        period_type=str(d.get("tur")), period_code=str(d.get("kod")), period_start=str(d.get("bas")), period_end=str(d.get("bit")), timezone=d.get("tz"), period_hours=d.get("saat"),
        production_input=meta.get("uretim_girdisi"), planned_mwh=pl.get("mwh"), actual_mwh=g.get("mwh"), forecast_mwh=(u.get("tahmin") or {}).get("mwh"), deviation_mwh=sap.get("mwh"),
        deviation_pct=sap.get("pct"), deviation_direction=sap.get("yon"), measured_hours=g.get("saat"), expected_hours=g.get("beklenen_saat"), measurement_boundary=g.get("sinir"),
        program_source=pl.get("kaynak"),
        components=[FinancialImpactComponent(code=b["kod"], name=b["ad"], net_tl=b.get("tutar_tl"), credit_tl=b.get("alacak_tl"), debit_tl=b.get("borc_tl"), quality=str(b.get("nitelik")),
                                             included_in_total=bool(b.get("toplanir")), coverage_hours=b.get("kapsam_saat"), expected_hours=b.get("beklenen_saat"), source=b.get("kaynak"),
                                             rule_version=b.get("kural_surumu"), notes=list(b.get("notlar") or [])) for b in (s.get("bilesenler") or [])],
        total_net_tl=top.get("tutar_tl"), total_credit_tl=top.get("alacak_tl"), total_debit_tl=top.get("borc_tl"), total_quality=top.get("nitelik"),
        total_included=list(top.get("giren") or []), total_missing=list(top.get("eksik") or []),
        official_available=bool(r.get("bilesenler")), official_differences_tl={k: float(v) for k, v in (r.get("fark") or {}).items() if v is not None},
        official_statuses={k: str(v) for k, v in (r.get("durum") or {}).items() if v is not None},
        price_epias_hours=(uz.get("fiyat") or {}).get("epias_saat"), price_scenario_hours=(uz.get("fiyat") or {}).get("senaryo_saat"),
        tariff_type=(meta.get("tarife") or {}).get("tip"), tariff_sha=(meta.get("tarife") or {}).get("sha"), market_position=(meta.get("pozisyon") or {}).get("kaynak"),
        rule_version=meta.get("kural_surumu"),
        recommendations=[FinancialImpactRecommendation(code=x["kod"], kind=x["tur"], text=x["metin"], page=x.get("sayfa")) for x in (s.get("oneriler") or [])],
        computed_at=str(s.get("hesap_zamani") or meta.get("hesap_zamani")), software_version=meta.get("yazilim_surumu"), record_id=s.get("id"))


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
    independent_validation: IndependentValidation | None = Field(default=None, description="v2.576: bağımsız doğrulama; hesaplanmadıysa anahtar HİÇ yazılmaz")
    financial_impact: FinancialImpact | None = Field(default=None, description="v2.585: Finansal Etki Merkezi; hesaplanmadıysa anahtar HİÇ yazılmaz")


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
        independent_validation=_independent_validation(ctx),
        financial_impact=_financial_impact(ctx),   # v2.585 (Faz 2 F2-G)
    )
    d = rapor.model_dump(mode="json")
    if d["quality"].get("hybrid") is None:      # yok = YOK (null değil)
        d["quality"].pop("hybrid", None)
    if d.get("independent_validation") is None:   # v2.576: yok = YOK
        d.pop("independent_validation", None)
    if d.get("financial_impact") is None:   # v2.585: yok = YOK
        d.pop("financial_impact", None)
    return _json.dumps(d, indent=2, ensure_ascii=False)
