"""MODEL SEÇİMİ DOĞRULAMASI — zaman sıralı, mevsim-bloklu, sızıntısız (26.11.2026; MODEL_BC_KIYAS bulgusu).

Sorun: Mod C kapısı eğitim penceresinin SON %20'si (çoğunlukla Eki–Ara) üzerinde karar veriyordu → mevsim yanlı; 4 santralin 2'sinde
bir sonraki yılın sonucunu yanlış öngördü. Çözüm: pencere `n_blok` ardışık dilime bölünür; her dilimin SONUNDAKİ `blok_pay`'lık kesit
holdout bloğudur, eğitim yalnız bloktan ÖNCEKİ veridir (genişleyen pencere; gelecek verisi asla eğitime girmez). Bloklar yılın farklı
mevsimlerine düşer; metrikler bloklar üzerinde HAVUZLANIR (saat ağırlıklı). Kapı eşikleri DEĞİŞMEZ (gate_min_improvement_pct,
gate_wmape_ceiling); yalnız eşiklerin uygulandığı holdout kümesi değişir. Modeller/kalibrasyon formülleri değişmez: Mod B =
calibrate_from_scada → forecast_7day, Mod C = run_hybrid_training → hybrid_forecast_hourly (üretim sargıları). Değerlendiriciler
enjekte edilebilir (test). Yetersiz eğitim/holdout saatinde blok «atlandı» (sayı uydurulmaz); tüm bloklar atlanırsa sonuç None →
çağıran eski yola (son %20) döner. Hibrit bir blokta eğitilemezse (ör. ilk blokta <500 temiz gündüz saati) o blok B–C kıyasından
düşer; kıyas kalan ORTAK bloklarda (≥2 blok, ≥2 mevsim) yapılır, aksi hâlde C None (kanıt yetersiz) — hata gizlenmez. Varsayılan ayar `secim_dogrulama = "son20"` → üretim davranışı değişmez; "mevsim_bloklu" opt-in.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

N_BLOK = 4                 # dört mevsim
BLOK_PAY = 0.05            # pencerenin %5'i ≈ 18 gün (365 g); toplam holdout ≈ %20 (eski tek blokla aynı oran)
ASGARI_EGITIM_SAAT = 24 * 45   # bloktan önce en az 45 gün eğitim verisi
ASGARI_BLOK_SAAT = 24          # blokta en az 24 geçerli gündüz saati
ASGARI_ORTAK_BLOK = 2          # B–C kıyası için C'nin hesaplanabildiği en az ortak blok (≥2 farklı mevsim)
MEVSIM = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}


@dataclass
class Blok:
    sira: int
    egitim_bit: pd.Timestamp     # eğitim [t0, egitim_bit)
    test_bas: pd.Timestamp       # holdout [test_bas, test_bit]
    test_bit: pd.Timestamp
    mevsim: str
    durum: str = "aday"          # aday | atlandi:<neden> | ok
    not_: str = ""
    saat: int = 0
    metrik: dict = field(default_factory=dict)


def bloklar(index: pd.DatetimeIndex, n_blok: int = N_BLOK, blok_pay: float = BLOK_PAY, asgari_egitim_saat: int = ASGARI_EGITIM_SAAT) -> list[Blok]:
    """SAF. Zaman sıralı mevsim blokları. Her blok için egitim_bit == test_bas (kesin sınır, çakışma yok); eğitim süresi
    asgari_egitim_saat'ten kısaysa blok «atlandi:egitim_kisa». Boş/tek noktalı indeks → []."""
    idx = pd.DatetimeIndex(index).sort_values()
    if len(idx) < 2:
        return []
    t0, t1 = idx.min(), idx.max()
    sure = t1 - t0
    out = []
    for i in range(1, n_blok + 1):
        bit = t0 + sure * (i / n_blok)
        bas = bit - sure * blok_pay
        if bas <= t0:
            bas = t0
        orta = bas + (bit - bas) / 2
        b = Blok(sira=i, egitim_bit=bas, test_bas=bas, test_bit=bit, mevsim=MEVSIM[int(orta.month)])
        if (bas - t0) < pd.Timedelta(hours=asgari_egitim_saat):
            b.durum = f"atlandi:egitim_kisa({int((bas - t0).total_seconds() // 3600)} sa < {asgari_egitim_saat})"
        out.append(b)
    return out


def _wmape(p: pd.Series, a: pd.Series) -> float | None:
    k = p.notna() & a.notna()
    return float((p[k] - a[k]).abs().sum() / a[k].sum() * 100.0) if k.any() and a[k].sum() > 0 else None


def degerlendir(index: pd.DatetimeIndex, gercek: pd.Series, mod_b, mod_c=None, *, esik_kw: float = 0.0, n_blok: int = N_BLOK,
                blok_pay: float = BLOK_PAY, asgari_egitim_saat: int = ASGARI_EGITIM_SAAT, asgari_blok_saat: int = ASGARI_BLOK_SAAT) -> dict | None:
    """Blokları üretir; her blokta mod_b(egitim_bit, test_bas, test_bit) → tahmin Series ve (varsa) mod_c(...) → tahmin Series çağırır.
    Değerlendirici istisna atarsa o blok ilgili mod için «hata» kaydedilir (diğer mod devam eder). Geçerli saat: gercek > esik_kw ve
    her iki (varsa) tahmin tanımlı — B ve C AYNI saatlerde ölçülür. Döner: {bloklar[], mevsimler, saat, B{wmape}, C{wmape}|None,
    iyilesme_pct|None, sizinti_ok} ya da hiç geçerli blok yoksa None."""
    bl = bloklar(index, n_blok=n_blok, blok_pay=blok_pay, asgari_egitim_saat=asgari_egitim_saat)
    if not bl:
        return None
    p_b_all, a_all = [], []
    ortak, ortak_seri = [], []   # C'nin de hesaplandığı bloklar (B ile aynı saatler)
    c_var = mod_c is not None
    c_hata = 0
    for b in bl:
        if b.durum != "aday":
            continue
        assert b.egitim_bit <= b.test_bas, "sızıntı: eğitim bitişi test başlangıcını geçiyor"
        maske = (gercek.index >= b.test_bas) & (gercek.index <= b.test_bit)
        a = gercek[maske]
        try:
            p_b = pd.Series(mod_b(b.egitim_bit, b.test_bas, b.test_bit)).reindex(a.index)
        except Exception as e:  # blok düşer, diğerleri sürer
            b.durum = f"atlandi:modB_hata({type(e).__name__})"
            continue
        p_c = None
        if c_var:
            try:
                p_c = pd.Series(mod_c(b.egitim_bit, b.test_bas, b.test_bit)).reindex(a.index)
            except Exception as e:
                b.not_ = f"mod_c hata: {type(e).__name__}"
                c_hata += 1
        k = a.notna() & (a > esik_kw) & p_b.notna()
        if p_c is not None:
            k = k & p_c.notna()
        if int(k.sum()) < asgari_blok_saat:
            b.durum = f"atlandi:gecerli_saat_az({int(k.sum())} < {asgari_blok_saat})"
            continue
        b.durum = "ok"
        b.saat = int(k.sum())
        b.metrik = {"B_wmape": round(_wmape(p_b[k], a[k]), 1), "C_wmape": (round(_wmape(p_c[k], a[k]), 1) if p_c is not None else None)}
        p_b_all.append(p_b[k])
        a_all.append(a[k])
        if p_c is not None:
            ortak.append(b)
            ortak_seri.append((p_b[k], p_c[k], a[k]))
    ok = [b for b in bl if b.durum == "ok"]
    if not ok:
        return None
    a_h = pd.concat(a_all)
    p_b_h = pd.concat(p_b_all)
    out = {"yontem": "mevsim_bloklu_zaman_sirali", "n_blok": n_blok, "blok_pay": blok_pay,
           "bloklar": [{"sira": b.sira, "mevsim": b.mevsim, "egitim_bit": b.egitim_bit.isoformat(), "test_bas": b.test_bas.isoformat(),
                        "test_bit": b.test_bit.isoformat(), "durum": b.durum, "saat": b.saat, **b.metrik, "not": b.not_} for b in bl],
           "mevsimler": sorted({b.mevsim for b in ok}), "saat": len(a_h), "sizinti_ok": True,
           "B": {"wmape": round(_wmape(p_b_h, a_h), 1)}}
    # C: B ile AYNI saatlerde, yalnız C'nin de hesaplanabildiği ORTAK bloklarda karşılaştırılır (ör. ilk blokta hibrit asgari saat
    # kuralı düşerse o blok dışlanır); en az ASGARI_ORTAK_BLOK ortak blok ve ≥2 farklı mevsim yoksa C None (kanıt yetersiz).
    if c_var and ortak:
        mevsim_ortak = sorted({b.mevsim for b in ortak})
        if len(ortak) >= ASGARI_ORTAK_BLOK and len(mevsim_ortak) >= 2:
            a_o = pd.concat([x[2] for x in ortak_seri])
            p_b_o = pd.concat([x[0] for x in ortak_seri])
            p_c_o = pd.concat([x[1] for x in ortak_seri])
            out["C"] = {"wmape": round(_wmape(p_c_o, a_o), 1), "ortak_blok": len(ortak), "ortak_mevsimler": mevsim_ortak, "ortak_saat": len(a_o),
                        "B_ayni_saatler_wmape": round(_wmape(p_b_o, a_o), 1)}
            bw, cw = out["C"]["B_ayni_saatler_wmape"], out["C"]["wmape"]
            out["iyilesme_pct"] = round((bw - cw) / bw * 100.0, 1) if bw and bw > 0 else None
            if c_hata:
                out["C_not"] = f"{c_hata} blokta hibrit hatası; karşılaştırma {len(ortak)} ortak blokta"
        else:
            out["C"] = None
            out["iyilesme_pct"] = None
            out["C_not"] = f"ortak blok yetersiz ({len(ortak)} blok, mevsim {mevsim_ortak}); {c_hata} blokta hibrit hatası"
    else:
        out["C"] = None
        out["iyilesme_pct"] = None
        out["C_not"] = (f"{c_hata} blokta hibrit hatası, ortak blok yok" if c_var else "hibrit istenmedi")
    return out


# --- Üretim sargılarıyla değerlendiriciler (motor/kalibrasyon formülü DEĞİŞMEZ) ---
def _scada_dilim(scada, bit):
    from pvquant.io.scada import SCADAData

    def d(s):
        return None if s is None else s[s.index < bit]
    return SCADAData(power_kw=d(scada.power_kw), energy_kwh=d(scada.energy_kwh), poa_irradiance=d(scada.poa_irradiance),
                     temp_ambient=d(scada.temp_ambient), temp_module=d(scada.temp_module), wind_speed=d(scada.wind_speed),
                     plant_name=scada.plant_name, timestep_minutes=scada.timestep_minutes)


def _meteo_dilim(meteo, bas, bit):
    import dataclasses

    def d(s):
        return None if s is None else s[(s.index >= bas) & (s.index <= bit)]
    return dataclasses.replace(meteo, ghi=d(meteo.ghi), temp_air=d(meteo.temp_air), wind_speed_10m=d(meteo.wind_speed_10m),
                               relative_humidity=d(meteo.relative_humidity), cloud_cover=d(meteo.cloud_cover),
                               precipitation=d(meteo.precipitation), snowfall=d(meteo.snowfall))


def uretim_degerlendiriciler(scada, meteo, plant_spec, plant_ctx: dict, plant_name: str, *, threshold_kw: float):
    """(mod_b, mod_c) kapanışları: her blok için eğitim dilimiyle uydur/eğit, test dilimini tahmin et. Mod C eğitimi bloğun eğitim
    dilimindeki meteo ile (hybrid_ui.run_hybrid_training; iç %80/20'si bu dilim içinde kalır)."""
    from pvquant.pipeline.calibration import calibrate_from_scada
    from pvquant.pipeline.forecast import forecast_7day
    from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly, run_hybrid_training

    def mod_b(egitim_bit, test_bas, test_bit):
        cr = calibrate_from_scada(scada=_scada_dilim(scada, egitim_bit), historical_meteo=_meteo_dilim(meteo, meteo.ghi.index.min(), egitim_bit),
                                  plant=plant_spec, fit_bg=True, fit_eta_bos=True, clean_outliers=True, threshold_kw=threshold_kw)
        return forecast_7day(_meteo_dilim(meteo, test_bas, test_bit), cr.plant, measured_poa=scada.poa_irradiance).hourly["p_ac_kw"]

    def mod_c(egitim_bit, test_bas, test_bit):
        res = run_hybrid_training(scada=_scada_dilim(scada, egitim_bit), historical_meteo=_meteo_dilim(meteo, meteo.ghi.index.min(), egitim_bit),
                                  plant_ctx=plant_ctx, plant_name=plant_name)
        if not res.ok:
            raise RuntimeError(res.error or "hibrit eğitimi başarısız")
        h = hybrid_forecast_hourly(res.model, _meteo_dilim(meteo, test_bas, test_bit))
        if h is None:
            raise RuntimeError("hybrid_forecast_hourly None")
        return h["p50_kw"]
    return mod_b, mod_c
