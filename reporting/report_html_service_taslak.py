# -*- coding: utf-8 -*-
"""report_html_service.py TASLAĞI (Dalga E.2, Adım 3a) — henüz DB'ye karşı TEST EDİLMEDİ.

Yerleşim: src/pvquant/services/report_html_service.py  (eski pvquant.reporting paketine
SIFIR dokunuş — 'reporting paketi TEK SATIR değişmez' kuralı korunur.)

Akış:  rapor_baglami(ctx)  →  ctx_to_json()  →  reporting/kopru.json_ile_uret()
İlke:  eksik alan SESSİZCE Konya varsayılanına düşmez; isim isim ValueError.

DOLDURULABİLENLER (ctx'te bugün var):
  plant.* ← plant dict + ctx.capacity/lat/lon/tilt/azimuth/tz
  run.mode/prepared ← ctx.mode, ctx.run_at_utc
  daily[] ← ctx.daily_kwh (+ daily_p10/p90 varsa)  [kWh→MWh]
  totals.p50/p10/p90 ← daily toplamları; capacity_factor ← toplam/(kWp·saat)
  accuracy.wmape_0_24, skill ← ctx.karne (0-24 kovası ortalaması, 120 g penceresi)
  climate.monthly_history ← ctx.iklim (iklim_oku)
  scada.coverage_pct ← ctx.coverage_pct
  calibration.physics_mape/holdout_mape ← ctx.holdout_physics_mape_pct / holdout_mape_pct
  history.evolution ← ctx.kosu_evrim
  hourly_typical.base_kw ← ctx.hourly p50'nin tipik-gün profili (medyan gün)
  accuracy.report_card[] ← ctx.karne satırları (0-24 + 24-72 kovaları)

BOŞLUKLAR (DB/worker'da bugün YOK — yarın kapatılacak, şimdilik ValueError):
  B1 accuracy.uninterrupted_days  → karneden ardışık gün sayımı türetilebilir (karar: türet?)
  B2 scada.quality_monthly        → flag_dagilimi TOPLAM; aylık kırılım SQL'i gerekli (s10)
  B3 scada.quality_flags aksiyon metinleri → bayrak adı→aksiyon sabit tablosu (aşağıda kısmen)
  B4 calibration.steps ara adımları → gate yalnız BAS/BIT verir; sistem verimi/bifacial/ML
     kırılımı worker'a yazdırılmalı (ya da 2 adımlık dürüst şelale basılmalı — karar)
  B5 error_dist (mu/sd/ndays, mae eğrileri, prof) → günlük sapma fotoğrafı worker'da yok
  B6 report.id üretim kuralı      → PVQ-<tarih>-<mod>-<sıra> üretici
  B7 sources.weather.model/version → forecast_runs.meteo_ozet_json'a model adı yazılmalı
"""
from __future__ import annotations
import datetime as _dt
import json
import os
import tempfile

AY_UZUN = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
           "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# B3 — bayrak adı → rapor aksiyon cümlesi (s10 çizelgesi)
BAYRAK_AKSIYON = {
    "yanlis_yil": ("Hatalı yıl bloğu",
                   "Kaynak dosyadaki bozuk yıl etiketi düzeltilip veri yeniden yüklenmeli."),
    "gece_uretim": ("Gece üretimi",
                    "Sayaç ofseti kontrol edilmeli; gece sıfırdan büyük üretim fiziksel değildir."),
    "donmus": ("Donmuş veri",
               "Telemetri kesintisi; aynı değerin tekrarlandığı bloklar düşürüldü."),
    "kapasite_ustu": ("Kapasite üstü kayıt",
                      "Ölçek hatası olasılığı; kurulu güç künyesiyle çapraz doğrulanmalı."),
    "okunamayan": ("Okunamayan satır",
                   "Ayrıştırılamayan kayıtlar; örnekleri veri ekinde listelenir."),
}


def _mwh(kwh):
    return round(float(kwh) / 1000.0, 1)


def ctx_to_json(ctx, plant: dict) -> dict:
    eksik = []

    def iste(kosul, ad):
        if not kosul:
            eksik.append(ad)
        return kosul

    J = {"schema_version": "2.1"}

    # kimlik / künye
    J["report"] = {"customer": plant.get("customer") or eksik.append("report.customer"),
                   "id": None, "contact": None}      # B6 + iletişim ayarı
    J["plant"] = {"name": ctx.plant_name, "display": _saha_display(ctx, plant)}
    J["run"] = {"mode": _mod_rozet(ctx.mode), "pages": 16,
                "prepared": ctx.run_at_utc.strftime("%Y-%m-%dT%H:%M")}

    # günlük seri + toplamlar
    iste(ctx.daily_kwh is not None and len(ctx.daily_kwh) == 16, "daily[16]")
    gunler = list(ctx.daily_kwh.index)
    J["forecast"] = {"start": str(gunler[0].date()), "end": str(gunler[-1].date())}
    bant = getattr(ctx, "daily_p10", None) is not None
    iste(bant, "daily[].p10/p90 (Mod C bandı)")
    J["daily"] = [{"date": str(g.date()),
                   "p50_mwh": _mwh(ctx.daily_kwh[g]),
                   "half_mwh": (_mwh((ctx.daily_p90[g] - ctx.daily_p10[g]) / 2) if bant else None),
                   "flag": None}                      # cephe bayrağı: meteo'dan (E.3)
                  for g in gunler]
    top50 = round(sum(d["p50_mwh"] for d in J["daily"]), 1)
    J["totals"] = {"p50_mwh": top50,
                   "p10_mwh": (round(_mwh(ctx.daily_p10.sum())) if bant else None),
                   "p90_mwh": (round(_mwh(ctx.daily_p90.sum())) if bant else None),
                   "capacity_factor": round(100 * top50 * 1000
                                            / (ctx.capacity_kwp * 24 * len(gunler)), 1)}

    # doğruluk (120 g penceresi — report_service.skill_gecmisi(gun=120) ile aynı)
    iste(getattr(ctx, "karne", None) is not None, "accuracy.karne (skill_daily)")
    if getattr(ctx, "karne", None) is not None:
        k = ctx.karne
        g24 = k[k.horizon_bucket == "0-24"]
        J["accuracy"] = {
            "skill_basis": "akilli-sureklilik (EPRI naif referans)",
            "wmape_0_24": round(float(g24.mape.mean()), 1),
            "skill": int(round(100 * float(g24.skill_vs_naive.mean()))),
            "uninterrupted_days": _ardisik_gun(g24),          # B1 — karar bekliyor
            "report_card": _karne_satirlari(k),
        }

    # iklim arşivi
    iste(getattr(ctx, "iklim", None) is not None, "climate.monthly_history (iklim_oku)")
    if getattr(ctx, "iklim", None) is not None:
        J["climate"] = {"monthly_history": _iklim_sozluk(ctx.iklim)}

    # SCADA kalite
    J["scada"] = {"coverage_pct": iste(getattr(ctx, "coverage_pct", None), "scada.coverage_pct")
                  and round(ctx.coverage_pct)}
    eksik.append("scada.quality_monthly (B2 — aylık SQL)")     # bilinçli açık
    eksik.append("error_dist.* (B5 — worker fotoğrafı)")
    eksik.append("calibration.steps (B4)")
    eksik.append("hourly_typical.base_kw (medyan gün türetimi — yazılacak)")

    # kalibrasyon uçları
    if getattr(ctx, "holdout_mape_pct", None) is not None:
        J["calibration"] = {"physics_mape": ctx.holdout_physics_mape_pct,
                            "holdout_mape": ctx.holdout_mape_pct, "steps": None}
    else:
        eksik.append("calibration.holdout (gate)")

    # evrim
    if getattr(ctx, "kosu_evrim", None) is not None:
        J["history"] = {"evolution": [
            {"date": r.run_at.strftime("%d ") + AY_UZUN[r.run_at.month - 1][:3],
             "p50": round(float(r.p50_mwh), 1), "half": None}   # bant: koşu p10/p90 (E.3)
            for r in ctx.kosu_evrim.itertuples()]}

    if eksik:
        raise ValueError("JSON v2.1 için eksik alanlar:\n  - " + "\n  - ".join(map(str, eksik)))
    return J


def uret_html_pdf(tenant_id, plant: dict):
    """Tek üretim kapısı (report_service.uret'e 'pdf16' formatı olarak bağlanır)."""
    from pvquant.services.report_service import rapor_baglami
    from reporting.kopru import json_ile_uret                   # depo kökü sys.path'te
    ctx = rapor_baglami(tenant_id, plant)
    if ctx is None:
        raise ValueError("rapor bağlamı kurulamadı — önce tahmin üretin")
    J = ctx_to_json(ctx, plant)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False)
        yol = f.name
    try:
        # Konya-dışı santralde taban denetimi anlamsız → denetim=False (E.3: taban türetimi)
        return json_ile_uret(yol, denetim=(plant.get("name") == "Konya GES"))
    finally:
        os.unlink(yol)


# ---- yardımcılar (iskelet; yarın DB karşısında doldurulup test edilecek) ----
def _mod_rozet(m):
    return {"A": "MOD A · HAM FİZİK", "B": "MOD B · KALİBRE",
            "C": "MOD C · HİBRİT"}.get(m, "MOD %s" % m)


def _saha_display(ctx, plant):
    return [("Koordinat", "%.4f°K · %.4f°D" % (ctx.latitude, ctx.longitude)),
            ("Kurulu güç", "%.1f MWp" % (ctx.capacity_kwp / 1000)),
            ("Panel eğimi / azimut", "%d° / %d°" % (ctx.tilt_deg, ctx.azimuth_deg)),
            ("Saat dilimi", ctx.plant_tz)]


def _ardisik_gun(g24):
    """B1: karnede bugünden geriye kesintisiz gün sayısı."""
    ...


def _karne_satirlari(k):
    ...


def _iklim_sozluk(ik):
    ...
