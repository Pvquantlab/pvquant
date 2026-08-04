"""ReportContext — üç rapor formatının tek veri sözleşmesi.

from_results(), UI'daki mevcut nesnelerden (ForecastResult +
CalibrationResult) bağlamı kurar: entegrasyonun tek yapıştırıcısı budur.
Mod B'de P10/P90 YOKTUR — bağlam bunu dürüstçe taşır (has_band=False),
raporlar aralık uydurmaz.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

# Sema surumu: alan EKLEME minor, kaldirma/yeniden adlandirma major (pratikte
# yapilmaz — alan 'deprecated' isaretlenir). Tur 6: quality.hybrid blogu -> 1.1.0
SCHEMA_VERSION = "1.1.0"


@dataclass
class ReportContext:
    # kimlik
    plant_name: str
    capacity_kwp: float
    latitude: float
    longitude: float
    tilt_deg: float
    azimuth_deg: float
    plant_tz: str
    # koşu
    run_at_utc: datetime
    mode: str                 # "A" | "B" | "C"
    model_name: str
    meteo_source: str
    model_version: str = "faz2-ui"
    # veri (hourly UTC index; kolonlar: p50_kw, poa, temp_cell, p_dc_kw,
    #        p_ac_kw, energy_kwh; varsa p10_kw, p90_kw)
    hourly: pd.DataFrame = None
    daily_kwh: pd.Series = None          # yerel gün -> kWh (P50)
    daily_p10: Optional[pd.Series] = None
    daily_p90: Optional[pd.Series] = None
    # kalibrasyon / güven
    eta_bos: Optional[float] = None
    bg: Optional[float] = None
    mape_pct: Optional[float] = None
    deviation_pct: Optional[float] = None
    calibrated_at: Optional[datetime] = None
    n_valid_hours: Optional[int] = None          # kalibrasyondaki geçerli saat
    holdout_mape_pct: Optional[float] = None     # kronolojik son %20 sınavı
    holdout_rmse_kw: Optional[float] = None
    holdout_physics_mape_pct: Optional[float] = None
    holdout_improvement_pct: Optional[float] = None
    holdout_hours: Optional[int] = None
    # dogruluk karnesi (v2.96, sartname S4 — skill_daily fotografi; kolonlar:
    # date, horizon_bucket, mape (=gunluk WMAPE %), naive_wmape,
    # skill_vs_naive). Worker gece yazar, rapor yalniz OKUR (tek uretici o).
    karne: Optional[pd.DataFrame] = None
    # v2.96 tam sartname (S2/S5/S6/S8) veri alanlari — hepsi opsiyonel,
    # yoksa ilgili sayfa durust '—' / 'veri eksik' basar:
    iklim: Optional[pd.DataFrame] = None        # ay, ghi_p10/p50/p90_kwh_m2
    son12: Optional[pd.DataFrame] = None        # ay(ts), actual_mwh
    flag_dagilimi: Optional[dict] = None        # flag -> satir sayisi
    coverage_pct: Optional[float] = None        # gecerli saat / toplam saat
    son_scada_ts: Optional[datetime] = None
    kosu_evrim: Optional[pd.DataFrame] = None   # run_at, p50_mwh (hedef gun)
    evrim_gunu: Optional[object] = None         # S8 hedef gunu (date)
    kapsama_p10_p90: Optional[float] = None     # gate_json'dan (Mod C)
    bant_pct: Optional[float] = None            # bant genisligi / p50 (%)
    warnings: list[str] = None
    schema_version: str = SCHEMA_VERSION

    # ---- türetilmiş KPI'lar (tek yerde yaşar; üç format aynı sayıyı basar) ----
    @property
    def total_kwh(self) -> float:
        return float(self.daily_kwh.sum())

    @property
    def total_mwh(self) -> float:
        return self.total_kwh / 1000.0

    @property
    def has_band(self) -> bool:
        return self.daily_p10 is not None and self.daily_p90 is not None

    @property
    def band_mwh(self) -> Optional[tuple[float, float]]:
        if not self.has_band:
            return None
        return (float(self.daily_p90.sum()) / 1000.0,
                float(self.daily_p10.sum()) / 1000.0)

    @property
    def capacity_factor_pct(self) -> float:
        """IEC 61724-1: E / (P_nom × saat)."""
        saat = len(self.hourly)
        return 100.0 * self.total_kwh / (self.capacity_kwp * saat)

    @property
    def specific_yield(self) -> float:
        """kWh/kWp — dönem özgül verimi (IEC 61724-1)."""
        return self.total_kwh / self.capacity_kwp

    @property
    def period_str(self) -> str:
        from .styles import donem_tr
        h = self.hourly.tz_convert(self.plant_tz)
        return donem_tr(h.index[0], h.index[-1])

    # ---- karne KPI'lari (S4; toplulastirma dogruluk.py/API /skill'in
    #      KOPYASI — uc yuzey ayni sayiyi soyler) ----
    @property
    def karne_var(self) -> bool:
        return self.karne is not None and len(self.karne) > 0

    def karne_ozet(self, kova: str) -> Optional[dict]:
        """Kova bazli donem ozeti: mape.mean(), date.nunique(),
        skill_vs_naive.dropna().mean(). Veri yoksa None — sifir uydurulmaz."""
        if not self.karne_var:
            return None
        k = self.karne[self.karne["horizon_bucket"] == kova]
        if len(k) == 0:
            return None
        sv = k["skill_vs_naive"].dropna()
        nf = (k["naive_wmape"].dropna()
              if "naive_wmape" in k.columns else pd.Series(dtype=float))
        return {"gun": int(k["date"].nunique()),
                "wmape_ort": float(k["mape"].mean()),
                "naif_ort": float(nf.mean()) if len(nf) else None,
                "skill_ort": float(sv.mean()) if len(sv) else None,
                "ilk": min(k["date"]), "son": max(k["date"])}

    @property
    def karne_kesintisiz_gun(self) -> Optional[int]:
        """Son karne gununden geriye ARDISIK 0-24 kovali gun sayisi.
        Olculmeyen gun zinciri KIRAR (sartname: '—', hesaba katilmaz)."""
        if not self.karne_var:
            return None
        g = self.karne[self.karne["horizon_bucket"] == "0-24"]
        if len(g) == 0:
            return 0
        gunler = sorted({d.date() if hasattr(d, "date") else d
                         for d in g["date"]})
        n = 1
        for i in range(len(gunler) - 1, 0, -1):
            if (gunler[i] - gunler[i - 1]).days == 1:
                n += 1
            else:
                break
        return n

    @property
    def karne_donem(self) -> Optional[tuple]:
        """Karnenin kapsadigi TUM tarihler (kova ayrimsiz) — v2.96 PDF
        durusmasi dersi: yalniz 0-24'ten hesaplamak donemi kisa gosteriyordu
        (baslik 15-16 Nis derken grafik 18 Nis'e uzaniyordu)."""
        if not self.karne_var:
            return None
        return (min(self.karne["date"]), max(self.karne["date"]))

    def karne_ufuk_kiyasi(self) -> Optional[dict]:
        """ADIL ufuk kiyasi: yalniz iki kovanin da olculdugu ORTAK gunlerde
        0-24 vs 24-72 ortalama farki. v2.96 durusmasi dersi: donem ortalamasi
        kiyasi farkli gun kumelerini karsilastiriyordu (0-24: 15-16 Nis,
        24-72: 16-18 Nis) — elma/armut. Ortak gun yoksa None (kiyas yapilmaz,
        uydurulmaz)."""
        if not self.karne_var:
            return None
        k = self.karne
        a = k[k["horizon_bucket"] == "0-24"].set_index("date")["mape"]
        b = k[k["horizon_bucket"] == "24-72"].set_index("date")["mape"]
        ortak = a.index.intersection(b.index)
        if len(ortak) == 0:
            return None
        return {"gun": int(len(ortak)),
                "fark": float(b.loc[ortak].mean() - a.loc[ortak].mean())}


def from_results(
    forecast_result,
    calibration_result=None,
    plant_name: str | None = None,
    plant_tz: str = "Europe/Istanbul",
    mode: str = "B",
    plant_context: dict | None = None,
) -> ReportContext:
    """pvquant.pipeline.forecast.ForecastResult (+ CalibrationResult) →
    ReportContext. UI entegrasyonunun çağırdığı tek fonksiyon.

    Santral adı çözüm sırası (ilk dolu olan kazanır):
      1. plant_name argümanı (çağıran açıkça verdiyse)
      2. plant_context dict'inde "plant_name" veya "name" anahtarı
      3. "Santral" (son çare — ama artık nadiren görünür)
    plant_context, UI'daki st.session_state.plant_context'tir; anahtar
    farkını (name/plant_name) burada soğuran tek nokta budur.
    """
    if plant_name is None:
        pc = plant_context or {}
        ham = pc.get("plant_name") or pc.get("name") or "Santral"
        plant_name = normalize_plant_name(ham)
    fr = forecast_result
    # v2.69: kosu artik 16 gun (384s) tasiyabilir; RAPOR sozlesmesi 7 gundur
    # (yedi_gun_yedi_bar, "8. gun DOGMAZ" testi). PDF/Excel ilk 168 saati basar.
    h = fr.hourly.copy().iloc[:168]
    if h.index.tz is None:                       # güvence: UTC'ye sabitle
        h.index = h.index.tz_localize("UTC")
    h = h.rename(columns={"p_ac_kw": "p50_kw"})
    # Günlük gruplama UTC gün sınırına göre yapılır: forecast penceresi UTC
    # 00:00'da başlar; yerele çevirip gün saymak son günü taşırıp fazladan
    # (sıfıra yakın) 8. gün üretiyordu. Grafik/tablo günleri UTC tabanlı,
    # saatlik profil ise görselde yerele çevrilir (charts.py) — tutarlı.
    daily = h["energy_kwh"].groupby(h.index.tz_convert("UTC").date).sum()
    daily.index = pd.to_datetime(daily.index)

    cr = calibration_result
    # CalibrationResult.validation_after.mape_pct alan adları repoya göre:
    mape = None
    dev = None
    if cr is not None:
        va = getattr(cr, "validation_after", None)
        mape = getattr(va, "mape_pct", None) if va is not None else None
        dev = getattr(va, "deviation_pct", None) if va is not None else None

    return ReportContext(
        plant_name=plant_name,
        capacity_kwp=fr.plant.p_nom_kwp,
        latitude=fr.plant.latitude,
        longitude=fr.plant.longitude,
        tilt_deg=fr.plant.tilt,
        azimuth_deg=fr.plant.azimuth,
        plant_tz=plant_tz,
        run_at_utc=datetime.now(timezone.utc),
        mode=mode,
        model_name=fr.meta.get("power_model", "barhdadi_bennis"),
        meteo_source=fr.meta.get("meteo_source", "open-meteo"),
        hourly=h,
        daily_kwh=daily,
        eta_bos=getattr(cr, "eta_bos", None) if cr else None,
        bg=getattr(cr, "bg", None) if cr else None,
        mape_pct=mape,
        deviation_pct=dev,
        n_valid_hours=getattr(cr, "n_valid_hours", None) if cr else None,
        holdout_mape_pct=getattr(cr, "holdout_mape_pct", None) if cr else None,
        calibrated_at=getattr(cr, "calibrated_at", None) if cr else None,
        warnings=list(getattr(cr, "warnings", []) or []) if cr else [],
    )


def apply_hybrid_session(ctx: "ReportContext", session) -> "ReportContext":
    """raporlar.py'nin tek satırlık hibrit bağlantısı.

    session: st.session_state (veya testte düz dict). Sözleşme:
      hybrid_active (bool)  -> ctx.mode = "C" (rozet + KPI dili)
      hybrid_report (dict)  -> holdout_mape_pct / holdout_rmse_kw
    Hibrit yoksa ctx'e DOKUNULMAZ — fizik akışı aynen kalır.
    """
    getter = session.get if hasattr(session, "get") else lambda k, d=None: d
    if getter("hybrid_active"):
        ctx.mode = "C"
    hr = getter("hybrid_report") or {}
    _esle = (("holdout_mape_pct", "holdout_mape_pct", float),
             ("holdout_rmse_kw", "holdout_rmse_kw", float),
             ("physics_mape_pct", "holdout_physics_mape_pct", float),
             ("improvement_pct", "holdout_improvement_pct", float),
             ("holdout_hours", "holdout_hours", int))
    for kaynak, hedef, tip in _esle:
        if hr.get(kaynak) is not None:
            setattr(ctx, hedef, tip(hr[kaynak]))
    return ctx


import re as _re

_AD_KIRP = _re.compile(
    r"(?i)[_\s-]*(scada|yillik|yıllık|full|data|export|rapor|report"
    r"|20\d{2}|19\d{2})[_\s-]*")


def normalize_plant_name(ham: str) -> str:
    """Dosya adından türeyen santral adını insanileştirir.
    'SANTRAL_GES_yillik_SCADA' -> 'SANTRAL GES'
    Kural: bilinen ekler (scada/yillik/full/data/export/yıl) kırpılır,
    alt çizgiler boşluğa döner, çoklu boşluk teklenir. Büyük harf
    kısaltmalar (GES gibi) korunur."""
    ad = _AD_KIRP.sub(" ", ham or "")
    ad = ad.replace("_", " ").replace("-", " ")
    ad = " ".join(ad.split()).strip()
    return ad or "Santral"
