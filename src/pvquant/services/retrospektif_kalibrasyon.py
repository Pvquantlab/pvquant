"""G4-P1 (26.11.2026) — RETROSPEKTİF kalibrasyon deneyi: DB yok, ağ yok, yazma yok; üretim kalibrasyon yolu (`calib_service.kalibre_et`)
DEĞİŞMEZ ve çağrılmaz.

Faz 1 G4 kapısı (Mod B: n_valid ≥ 100 gündüz saati, holdout WMAPE, |toplam sapma| ≤ %30) geçmiş dış veriyle — PVDAQ Golden 33 2018
(ext/kaynak/pvdaq) + analiz/uydu meteosu (PVGIS ERA5 / CAMS) — denenir. Üretim yolundaki `kalibrasyon_penceresi` (02.10.2026 NWP arşiv
kesimi) burada UYGULANMAZ, çünkü kesim «kendi arşivimizin ışınımı kaymış» bulgusu içindir; dış meteo bu kusuru taşımaz. Bu bilerek ve
açıkça etiketlenir: sonuç «retrospektif model deneyi»dir, operasyonel iddia DEĞİLDİR, `calibrations` tablosuna yazılmaz, canlıya
taşınmaz. Aynı motor fonksiyonları kullanılır: `calibrate_from_scada`, `_kronolojik_holdout`, `mod_b_kapisi`, `plant_spec_kur`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.services.plant_spec_service import egim_azimut

ETIKET = "retrospektif_model_deneyi"
GEREKLI = ("power_kw",)
GUNDUZ_ORAN = 0.02       # geçerli saat eşiği = kWp × 0,02 (karne_kurali.GUNDUZ_ORAN ile aynı); motorun mutlak 1 kW varsayılanı küçük santralde (2,4 kWp)
                         # yalnız parlak saatleri sayıyordu (Golden 33 2018: 1036 saat) → metrikler iyimser olurdu


OLCUM_SENSORLERI = ("poa_wm2", "t_module", "t_air", "wind_ms")


def sensorsuz(df: pd.DataFrame) -> pd.DataFrame:
    """G4-P3: ölçüm çerçevesinden saha sensörlerini (POA ışınımı, modül/ortam sıcaklığı, rüzgar) düşürür → motor ve hibrit yalnız
    meteo (NWP/reanaliz) girdisiyle çalışır; «ölçülmüş POA yolu» ile «meteo yolu» ayrı raporlanır. Güç/enerji/kapsama kalır."""
    return df.drop(columns=[c for c in OLCUM_SENSORLERI if c in df.columns])


def scada_cercevesi(df: pd.DataFrame, plant: dict):
    """Saatlik ölçüm çerçevesi (ts_utc index; power_kw, energy_kwh?, poa_wm2?, t_air?, t_module?) → SCADAData (kesintisiz saatlik ızgara).
    `kalibrasyon_penceresi` uygulanmaz (bkz. modül notu)."""
    from pvquant.io.scada import SCADAData
    from pvquant.services.calib_service import _kalibrasyon_izgarasi
    for k in GEREKLI:
        if k not in df.columns:
            raise ValueError(f"ölçüm çerçevesinde {k} yok")
    d = df.copy()
    if not isinstance(d.index, pd.DatetimeIndex):
        d.index = pd.to_datetime(d.index, utc=True)
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    d = d.sort_index()
    d = _kalibrasyon_izgarasi(d, plant)

    def _o(k):
        return d[k] if k in d.columns and d[k].notna().any() else None
    return SCADAData(power_kw=d["power_kw"], energy_kwh=_o("energy_kwh"), poa_irradiance=_o("poa_wm2"), temp_ambient=_o("t_air"),
                     temp_module=_o("t_module"), wind_speed=_o("wind_ms"), plant_name=str(plant.get("name") or "retrospektif"),
                     timestep_minutes=60)


def meteo_cercevesi(df: pd.DataFrame, lat: float, lon: float, kaynak: str = "analiz") -> object:
    """Saatlik meteo çerçevesi (ts_utc index; ghi, temp_air, wind_speed_10m?) → MeteoData (UTC). Eksik rüzgar → 1 m/s sabit (not düşülür)."""
    from pvquant.io.meteo import MeteoData
    d = df.copy()
    if not isinstance(d.index, pd.DatetimeIndex):
        d.index = pd.to_datetime(d.index, utc=True)
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    d = d.sort_index()
    if "ghi" not in d.columns or "temp_air" not in d.columns:
        raise ValueError("meteo çerçevesinde ghi ve temp_air gerekir")
    ruzgar = d["wind_speed_10m"] if "wind_speed_10m" in d.columns else pd.Series(1.0, index=d.index)
    return MeteoData(ghi=d["ghi"].astype(float).clip(lower=0.0), temp_air=d["temp_air"].astype(float), wind_speed_10m=ruzgar.astype(float),
                     relative_humidity=None, cloud_cover=None, latitude=float(lat), longitude=float(lon), timezone="UTC",
                     kaynak=kaynak, nwp_model=kaynak)


def kalibre_et_retrospektif(scada_df: pd.DataFrame, meteo, plant: dict, *, meteo_kaynak: str = "analiz", hibrit: bool = False) -> dict:
    """Mod B retrospektif kalibrasyon + kronolojik holdout + G2-C1 Mod B kapısı. Döner (yazmaz): etiket, mode (B | atlandi), kapi,
    eta_bos, bg, n_valid_hours, wmape_pct, sapma_pct, holdout{…}, pencere{…}, uyarilar, meteo_kaynak, not."""
    from pvquant.pipeline.calibration import calibrate_from_scada
    from pvquant.services.calib_service import _kronolojik_holdout, mod_b_kapisi
    from pvquant.services.plant_spec_service import plant_spec_kur
    scada = scada_cercevesi(scada_df, plant)
    spec = plant_spec_kur(plant)
    idx = scada.power_kw.index
    pencere = {"bas": idx.min().isoformat(), "bit": idx.max().isoformat(), "saat": len(idx), "gecerli_saat": int(scada.power_kw.notna().sum())}
    esik_kw = max(float(plant.get("capacity_kwp") or 0.0) * GUNDUZ_ORAN, 0.001)
    try:
        cr = calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=spec, fit_bg=True, fit_eta_bos=True, clean_outliers=True,
                                  threshold_kw=esik_kw)
    except ValueError as e:   # motorun asgari veri kuralı (ör. <100 saat) — deney düşmez, «atlandı» olarak raporlanır
        return {"etiket": ETIKET, "mode": "atlandi", "kapi": f"motor: {e}", "eta_bos": None, "bg": None, "n_valid_hours": 0,
                "wmape_pct": None, "wmape_once_pct": None, "sapma_pct": None, "holdout": {}, "uyarilar": [], "pencere": pencere,
                "santral": {"ad": plant.get("name"), "kwp": plant.get("capacity_kwp"), "panel_tech": plant.get("panel_tech"), "bifacial_factor": spec.bifacial_factor},
                "meteo_kaynak": meteo_kaynak, "not": "retrospektif model deneyi: motor asgari veri kuralı; yazılmaz"}
    try:
        holdout = _kronolojik_holdout(scada, meteo, spec, threshold_kw=esik_kw)
    except Exception as e:   # ölçüm yardımcı; deney düşmez
        holdout = {"wmape_holdout_pct": None, "mape_holdout_pct": None, "holdout_saat": None, "holdout_not": f"hesaplanamadı: {type(e).__name__}"}
    sapma = getattr(cr.validation_after, "total_deviation_pct", None)
    kapi_ok, kapi_neden = mod_b_kapisi(cr.n_valid_hours, holdout.get("wmape_holdout_pct"), sapma)
    hib = hibrit_kapisi(scada, meteo, plant) if (hibrit and kapi_ok) else None
    mode = "atlandi" if not kapi_ok else ("C" if (hib and hib.get("gecti")) else "B")
    return {"etiket": ETIKET, "mode": mode, "kapi": kapi_neden, "hibrit": hib,
            "eta_bos": float(cr.eta_bos), "bg": float(cr.bg), "n_valid_hours": int(cr.n_valid_hours),
            "wmape_pct": getattr(cr.validation_after, "wmape_pct", None), "wmape_once_pct": getattr(cr.validation_before, "wmape_pct", None),
            "sapma_pct": sapma, "holdout": holdout, "uyarilar": list(cr.warnings or []) + list(cr.notes or []),
            "pencere": pencere,
            "santral": {"ad": plant.get("name"), "kwp": plant.get("capacity_kwp"), "panel_tech": plant.get("panel_tech"), "bifacial_factor": spec.bifacial_factor},
            "meteo_kaynak": meteo_kaynak, "esik_kw": esik_kw, "poa_olcumu_kullanildi": scada.poa_irradiance is not None,
            "sensorler": [k for k, v in (("poa", scada.poa_irradiance), ("t_module", scada.temp_module), ("t_air", scada.temp_ambient),
                                          ("wind", scada.wind_speed)) if v is not None],
            "not": "retrospektif model deneyi: kalibrasyon_penceresi uygulanmadı; calibrations tablosuna YAZILMAZ; operasyonel iddia değildir; "
                   "POA ölçümü varsa motor doğrulamayı ölçülmüş POA ile yapar (meteo ışınımı hesaba girmez — NWP/ERA5 hatası dâhil değil)"}


def hibrit_kapisi(scada, meteo, plant: dict) -> dict:
    """Mod C retrospektif: `hybrid_ui.run_hybrid_training` (kronolojik %80/%20 holdout; rastgele bölme yok) + üretimle AYNI kapı kuralı
    (`kalibre_et`): göreli iyileşme ≥ gate_min_improvement_pct VE holdout WMAPE ≤ gate_wmape_ceiling. Artefakt kaydedilmez."""
    from pvquant.config import get_settings
    from pvquant.pipeline.hybrid_ui import run_hybrid_training
    from pvquant.services.calib_service import panel_teknolojisi
    cfg = get_settings()
    ctx = {"capacity_kwp": plant["capacity_kwp"], "latitude": plant["lat"], "longitude": plant["lon"], "timezone": plant.get("tz") or "UTC",
           "tilt": egim_azimut(plant)[0], "azimuth": egim_azimut(plant)[1], "panel_technology": panel_teknolojisi(plant.get("panel_tech")),
           "ac_limit_kw": plant.get("ac_limit_kw")}
    try:
        res = run_hybrid_training(scada=scada, historical_meteo=meteo, plant_ctx=ctx, plant_name=str(plant.get("name") or "retrospektif"))
    except Exception as e:   # deney düşmez
        return {"denendi": True, "gecti": False, "sebep": f"hibrit eğitimi hata: {type(e).__name__}: {e}"[:200]}
    w = getattr(res, "holdout_wmape_pct", None)
    pw = getattr(res, "physics_wmape_pct", None)
    iyi = float((pw - w) / pw * 100.0) if (w is not None and pw is not None and pw > 0) else None
    taban_ok = (w is not None and w <= cfg.gate_wmape_ceiling)
    gecti = bool(res.ok and iyi is not None and iyi >= cfg.gate_min_improvement_pct and taban_ok)
    sebep = None if gecti else (res.error or (f"holdout WMAPE {w} > tavan {cfg.gate_wmape_ceiling}" if not taban_ok
                                             else f"iyileşme {iyi} < {cfg.gate_min_improvement_pct}"))
    return {"denendi": True, "gecti": gecti, "sebep": sebep, "holdout_wmape": w, "fizik_wmape": pw, "wmape_iyilesme_pct": iyi,
            "holdout_mape": getattr(res, "holdout_mape_pct", None), "fizik_mape": getattr(res, "physics_mape_pct", None),
            "holdout_saat": getattr(res, "holdout_hours", None), "esik": {"iyilesme_pct": cfg.gate_min_improvement_pct, "wmape_tavan": cfg.gate_wmape_ceiling},
            "not": "kronolojik holdout (ilk %80 eğitim, son %20 doğrulama); artefakt kaydedilmedi"}


# --- G4-P4 (26.11.2026): HATA AYRIŞTIRMA — yüksek WMAPE hangi bileşenden? (SAF; DB/ağ/yazma yok; motor parametrelerine dokunmaz)
KT_KUSAKLARI = ((0.0, 0.3, "bulutlu"), (0.3, 0.6, "parcali"), (0.6, 0.85, "az_bulutlu"), (0.85, 1.6, "berrak"))
PR_COKME = 0.5            # ölçülmüş POA > 300 W/m² iken PR < 0,5 → kar/gölge/kesinti saati (santral tarafı, meteo değil)


def _poa_motor_yolu(ghi: pd.Series, lat: float, lon: float, tilt: float, az: float, orta_dk: int = 30):
    """Motorla AYNI ışınım yolu (forecast_7day §1–3): güneş konumu aralık ortası, Erbs ayrıştırma, Perez transpozisyon, albedo 0,25."""
    from pvquant.models import irradiance as irr
    t = ghi.index
    sp = irr.solar_position(t + pd.Timedelta(minutes=orta_dk), lat, lon)
    sp.index = t
    dec = irr.decompose_ghi_erbs(ghi=ghi, solar_zenith=sp["apparent_zenith"], times=t)
    de, am = irr.extra_radiation_and_airmass(t, sp["apparent_zenith"])
    poa = irr.transpose_perez(tilt, az, sp["apparent_zenith"], sp["azimuth"], dec["dni"], dec["ghi"], dec["dhi"], de, am, albedo=0.25)
    return poa.global_.fillna(0.0).clip(lower=0.0), sp["apparent_elevation"]


def _wmape(p: pd.Series, a: pd.Series) -> float | None:
    k = p.notna() & a.notna()
    return round(float((p[k] - a[k]).abs().sum() / a[k].sum() * 100.0), 1) if k.any() and a[k].sum() > 0 else None


def _bias(p: pd.Series, a: pd.Series) -> float | None:
    k = p.notna() & a.notna()
    return round(float((p[k].sum() / a[k].sum() - 1.0) * 100.0), 1) if k.any() and a[k].sum() > 0 else None


def hata_ayristir(scada_df: pd.DataFrame, meteo_df: pd.DataFrame, plant: dict, *, holdout_pay: float = 0.2, eta_sabit: float | None = None) -> dict:
    """Ölçüm (power_kw, poa_wm2 ZORUNLU, t_air?) + meteo (ghi, temp_air) → hata bileşenleri. Ölçülmüş POA YALNIZ tanı referansıdır
    (tahmin anında yok); meteo yolu metriklerine girmez. Döner: isinim{wmape, bias, berraklik{…}, zaman_varyantlari}, santral{pr…,
    pr_cokme_saat, kis_hata_payi}, mevsim{aylik{era5, poa_olcum}, holdout{…}}, hukum (metin, eşik değiştirmez)."""
    lat, lon = float(plant["lat"]), float(plant["lon"])
    tilt, az, kwp = float(plant.get("tilt") or 20.0), float(plant.get("azimuth") or 180.0), float(plant["capacity_kwp"])
    m = scada_df.copy()
    e = meteo_df.copy()
    for d in (m, e):
        if not isinstance(d.index, pd.DatetimeIndex):
            d.index = pd.to_datetime(d.index, utc=True)
        if d.index.tz is None:
            d.index = d.index.tz_localize("UTC")
    if "poa_wm2" not in m or m["poa_wm2"].notna().sum() < 100:
        raise ValueError("hata ayrıştırma için ölçülmüş POA (poa_wm2) gerekir — tanı referansı")
    df = m.join(e[["ghi", "temp_air"]], how="inner").sort_index()
    if len(df) < 200:
        raise ValueError(f"ortak saat yetersiz ({len(df)})")
    poa_m, elev = _poa_motor_yolu(df["ghi"].astype(float).clip(lower=0), lat, lon, tilt, az)
    df["poa_model"] = poa_m
    gun = (elev > 5) & df["poa_wm2"].notna() & (df["poa_wm2"] > 20)
    out: dict = {"n_saat": len(df), "n_gunduz": int(gun.sum())}
    # 1) IŞINIM — motor yolu (reanaliz/NWP GHI → POA) vs ölçülmüş POA
    isinim = {"wmape_pct": _wmape(poa_m[gun], df["poa_wm2"][gun]), "bias_pct": _bias(poa_m[gun], df["poa_wm2"][gun]),
              "corr": round(float(poa_m[gun].corr(df["poa_wm2"][gun])), 3)}
    zv = {}
    for dk in (0, 30, 60):
        pm, _ = _poa_motor_yolu(df["ghi"].astype(float).clip(lower=0), lat, lon, tilt, az, orta_dk=dk)
        zv[f"gunes_konumu_+{dk}dk"] = _wmape(pm[gun], df["poa_wm2"][gun])
    for lag in (-1, 1):
        pm, _ = _poa_motor_yolu(df["ghi"].astype(float).shift(lag).fillna(0).clip(lower=0), lat, lon, tilt, az)
        zv[f"ghi_kaydir_{lag:+d}sa"] = _wmape(pm[gun], df["poa_wm2"][gun])
    isinim["zaman_varyantlari"] = zv
    import pvlib
    loc = pvlib.location.Location(lat, lon)
    cs = loc.get_clearsky(df.index + pd.Timedelta(minutes=30), model="ineichen")
    cs.index = df.index
    poa_cs, _ = _poa_motor_yolu(cs["ghi"], lat, lon, tilt, az)
    kt_olc = (df["poa_wm2"] / poa_cs.replace(0, np.nan)).clip(0, 1.6)
    ber = {}
    for lo_, hi_, ad in KT_KUSAKLARI:
        k = gun & (kt_olc > lo_) & (kt_olc <= hi_)
        ber[ad] = {"n": int(k.sum()), "wmape_pct": _wmape(poa_m[k], df["poa_wm2"][k]), "bias_pct": _bias(poa_m[k], df["poa_wm2"][k])}
    isinim["berraklik_olculen"] = ber
    isinim["aylik"] = {int(ay): {"wmape_pct": _wmape(g["poa_model"], g["poa_wm2"]), "bias_pct": _bias(g["poa_model"], g["poa_wm2"])}
                       for ay, g in df[gun].groupby(df[gun].index.month)}
    out["isinim"] = isinim
    # 2) SANTRAL / FİZİK — ölçülmüş POA ile performans oranı; PR çökmesi (kar/gölge/kesinti) saatleri
    parlak = df["poa_wm2"] > 300
    pr = (df["power_kw"] / (kwp * df["poa_wm2"] / 1000.0)).where(parlak)
    t_air = df["t_air"] if "t_air" in df and df["t_air"].notna().any() else df["temp_air"]
    tc = t_air + 25.0 * df["poa_wm2"].fillna(0) / 1000.0
    pr_t = pr / (1.0 - 0.004 * (tc - 25.0))
    eta = float(eta_sabit) if eta_sabit is not None else float(pr_t.median())
    cok = parlak & (pr < PR_COKME)
    out["santral"] = {"pr_medyan": round(float(pr.median()), 3), "pr_sicaklik_duzeltmeli_medyan": round(float(pr_t.median()), 3),
                      "pr_aylik_medyan": {int(k): round(float(v), 3) for k, v in pr.groupby(pr.index.month).median().items()},
                      "pr_cokme_saat_aylik": {int(k): int(v) for k, v in cok.groupby(cok.index.month).sum().items() if v > 0},
                      "pr_cokme_saat": int(cok.sum()), "ac_maks_kw": round(float(df["power_kw"].max()), 3),
                      "meteo_tair_bias_C": round(float((df["temp_air"] - df["t_air"]).mean()), 2) if "t_air" in df else None, "eta_kullanilan": round(eta, 3)}
    # 3) MEVSİM / HOLDOUT — aynı sabit-η basit model: meteo yolu vs ölçülmüş-POA yolu (motor değil; bileşen ayrımı için)
    def p_of(poa):
        tcell = df["temp_air"] + 25.0 * poa / 1000.0
        return (kwp * poa / 1000.0 * eta * (1.0 - 0.004 * (tcell - 25.0))).clip(lower=0.0)
    pe, pp = p_of(poa_m), p_of(df["poa_wm2"].fillna(0.0))
    act = df["power_kw"]
    g2 = act.notna() & (act > kwp * GUNDUZ_ORAN)
    ay = {int(k): {"meteo_yolu": _wmape(pe[idx], act[idx]), "olculmus_poa": _wmape(pp[idx], act[idx])} for k, idx in act[g2].groupby(act[g2].index.month).groups.items()}
    pw = act[g2].sort_index()
    kes = pw.index[int(len(pw) * (1.0 - holdout_pay))]
    h, tr = g2 & (df.index >= kes), g2 & (df.index < kes)
    hk = h & cok
    pay = round(float((pe[hk] - act[hk]).abs().sum() / (pe[h] - act[h]).abs().sum() * 100.0), 1) if h.any() and (pe[h] - act[h]).abs().sum() > 0 else None
    kis = g2 & df.index.month.isin([11, 12, 1, 2])
    kis_cok = kis & cok
    out["mevsim"] = {"aylik_wmape": ay, "holdout": {"bas": kes.isoformat(), "n": int(h.sum()), "meteo_yolu": _wmape(pe[h], act[h]), "olculmus_poa": _wmape(pp[h], act[h]),
                                                    "pr_cokme_saat": int(hk.sum()), "pr_cokme_hata_payi_pct": pay},
                     "egitim": {"n": int(tr.sum()), "meteo_yolu": _wmape(pe[tr], act[tr]), "olculmus_poa": _wmape(pp[tr], act[tr])},
                     "kis_olculmus_poa": {"wmape_pct": _wmape(pp[kis], act[kis]), "pr_cokme_saat": int(kis_cok.sum()),
                                          "pr_cokme_disi_wmape_pct": _wmape(pp[kis & ~cok], act[kis & ~cok]),
                                          "pr_cokme_hata_payi_pct": round(float((pp[kis_cok] - act[kis_cok]).abs().sum() / (pp[kis] - act[kis]).abs().sum() * 100.0), 1) if kis.any() else None}}
    # 4) HÜKÜM (metin; eşik değiştirmez): baskın bileşen
    berrak = ber.get("berrak", {}).get("wmape_pct")
    bulut = ber.get("bulutlu", {}).get("bias_pct")
    zaman_ok = zv.get("gunes_konumu_+30dk") is not None and all(zv["gunes_konumu_+30dk"] <= v for v in zv.values() if v is not None)
    out["hukum"] = {"zaman_hizasi_motor_dogru": bool(zaman_ok),
                    "baskin_bilesen": ("meteo_isinim" if (isinim["wmape_pct"] or 0) > 15 and (berrak or 99) < 10 else "belirsiz"),
                    "aciklama": (f"meteo→POA WMAPE %{isinim['wmape_pct']} (berrak saatte %{berrak}, bulutlu saatte sapma %{bulut}); ölçülmüş POA ile aynı santral modeli "
                                 f"holdout %{out['mevsim']['holdout']['olculmus_poa']} → fark ≈ meteo ışınım hatası; kış hatasının %{out['mevsim']['kis_olculmus_poa']['pr_cokme_hata_payi_pct']}'i "
                                 f"PR çökmesi saatleri (kar/gölge/kesinti, meteo değil)")}
    return out
