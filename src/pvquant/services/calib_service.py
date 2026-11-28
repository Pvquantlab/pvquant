"""Kalibrasyon: DB'den oku -> mevcut motoru cagir -> DB'ye yaz.
Zeyilname v1.6: quality_json 4 alanli sozlesme (mape_pct/mape_before_pct/
deviation_pct/deviation_before_pct + warnings)."""
from __future__ import annotations
import json, pickle, pathlib
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.services.ingest_service import scada_oku
from pvquant.io.scada import SCADAData
from pvquant.io.meteo import OpenMeteoClient
from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.services.plant_spec_service import params_json, plant_spec_kur
from pvquant.pipeline.forecast import PlantSpec
from pvquant.pipeline.hybrid_ui import run_hybrid_training, session_ozeti
from pvquant.services.plant_spec_service import egim_azimut

ARTIFACT_DIR = pathlib.Path("var/artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)



def _kalibrasyon_izgarasi(df: pd.DataFrame, plant: dict) -> pd.DataFrame:
    """scada_oku ciktisini kalibrasyon motorunun istedigi kesintisiz
    saatlik izgaraya oturtur. Mantik frontend/veri_yukleme.py
    _kopru_scadadata_ve_gec'ten TASINDI (Faz 1 saha-kanitli) —
    yeniden yazilmadi. UI kopyasi Anayasa Adim 3'te silinecek."""
    if not isinstance(df.index, pd.DatetimeIndex) or len(df) <= 1:
        return df
    full_range = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="1h",
        tz=df.index.tz,
    )
    df = df.reindex(full_range)
    df.index.name = "timestamp"
    # Gece saatlerinde NaN power_kw -> 0 doldur (gercekte uretim yok)
    # Gunduz NaN'lari NaN kalir (backend duser). Boylece index tam kalir
    # ama gunduzun tam satirlari kesintisiz olur -> %90+ tutarlilik.
    try:
        import pvlib
        solpos = pvlib.solarposition.get_solarposition(
            df.index, plant["lat"], plant["lon"],
        )
        is_night = solpos["apparent_elevation"] < -3.0
        night_nan_mask = is_night.values & df["power_kw"].isna().values
        df.loc[night_nan_mask, "power_kw"] = 0.0
    except Exception:
        # pvlib yoksa fallback: tum NaN'lari 0 yap (daha az temiz ama calisir)
        df["power_kw"] = df["power_kw"].fillna(0.0)
    return df


#: G2-C1 (C2-1, 24.11.2026): kalibrasyon penceresi, kendi NWP arşivinin başladığı kesimden (`acik_nwp.ARSIV_KESIM_UTC`) önceye
#: uzanmaz. Eskiden `scada_oku` tarih süzgeçsizdi: Karapınar'ın 31.12.2024'ten gelen 15.120 satırı meteo kapsamasını %4,5'e
#: düşürüyor, kalibrasyon hiç geçmiyordu. Ölçüm silinmez; yalnız bu uydurmanın penceresi kesilir (karne/uzlaştırma dokunulmaz).
MOD_B_ASGARI_SAAT = 100          # G2-C1 (C2-8): temizlenmiş GÜNDÜZ saat sayısı (motorun 100 saat eşiğiyle aynı; gece 0'ları saymaz)
MOD_B_SAPMA_TAVAN_PCT = 30.0     # G2-C1 (C2-8): uydurma sonrası |toplam sapma| bunu aşarsa «kör B» — kayıt yazılmaz


def kalibrasyon_penceresi(df: pd.DataFrame, kesim: pd.Timestamp | None = None) -> pd.DataFrame:
    """SAF (G2-C1). Ölçüm çerçevesini `kesim`'den (varsayılan: NWP arşiv başlangıcı) itibaren keser; kesim öncesi satır yoksa
    aynen döner. Index tz'siz ise UTC varsayılır."""
    if df is None or len(df) == 0 or not isinstance(df.index, pd.DatetimeIndex):
        return df
    if kesim is None:
        from pvquant.io.acik_nwp import ARSIV_KESIM_UTC
        kesim = ARSIV_KESIM_UTC
    kesim = pd.Timestamp(kesim)
    kesim = kesim.tz_localize("UTC") if kesim.tzinfo is None else kesim.tz_convert("UTC")
    idx = df.index if df.index.tz is not None else df.index.tz_localize("UTC")
    return df.loc[idx >= kesim]


def mod_b_kapisi(n_valid_hours, holdout_wmape_pct, deviation_pct) -> tuple[bool, str]:
    """SAF (G2-C1, C2-8). Mod B kalite kapısı: (1) temizlenmiş gündüz saati ≥ MOD_B_ASGARI_SAAT, (2) örneklem dışı holdout metriği
    hesaplanabilmiş (yoksa iddia kanıtsız), (3) uydurma sonrası |toplam sapma| ≤ MOD_B_SAPMA_TAVAN_PCT. Format Lab vakası (8 saat,
    sapma −%98,6 ile Mod B yazıldı) üçünde de düşer. Döner (geçti, neden)."""
    try:
        n = int(n_valid_hours or 0)
    except (TypeError, ValueError):
        n = 0
    if n < MOD_B_ASGARI_SAAT:
        return False, f"temiz gündüz saati {n} < {MOD_B_ASGARI_SAAT}"
    if holdout_wmape_pct is None or holdout_wmape_pct != holdout_wmape_pct:
        return False, "örneklem dışı holdout metriği hesaplanamadı"
    try:
        sap = abs(float(deviation_pct))
    except (TypeError, ValueError):
        return False, "uydurma sonrası sapma hesaplanamadı"
    if sap > MOD_B_SAPMA_TAVAN_PCT:
        return False, f"uydurma sonrası sapma %{sap:.1f} > %{MOD_B_SAPMA_TAVAN_PCT:.0f}"
    return True, "kapı geçti"


_PANEL_TEKNOLOJISI = {"monofacial": "mono", "mono": "mono", "bifacial": "bifacial", "thin_film": "thin_film", "thinfilm": "thin_film"}


def panel_teknolojisi_bilgi(panel_tech) -> tuple[str, bool]:
    """SAF (G4-P0, 26.11.2026). (teknoloji, beyan_edildi). Beyansız/bilinmeyen panel → **mono** (bifacial kazancı YOK): eski varsayılan
    `bifacial`, beyanı olmayan santrala sessizce BF 0,7 kazancı yüklüyordu (araştırma havuzu PANEL_SOZLUGU_NOTU §2: pvlib/CEC/Sandia/
    PVGIS sözlükleri bilinmeyeni bifacial saymaz; Golden 33 «Unknown», CdTe ince film). Bilinmeyen = kazanç iddiası yok."""
    anahtar = str(panel_tech or "").strip().lower()
    if anahtar in _PANEL_TEKNOLOJISI:
        return _PANEL_TEKNOLOJISI[anahtar], True
    return "mono", False


def panel_teknolojisi(panel_tech) -> str:
    """SAF (G2-C1, C2-2; G4-P0). `plants.panel_tech` sözlüğü (`monofacial`/`bifacial`) → `PanelSpec.technology` Literal (`mono`/…).
    Bilinmeyen/boş → `mono` (G4-P0: beyansız santrala bifacial kazancı yüklenmez). Eskiden `monofacial` doğrudan geçiyor, Pydantic
    ValidationError hibrit eğitimi sessizce düşürüyordu (Golden 33, Format Lab, Kıvanç)."""
    return panel_teknolojisi_bilgi(panel_tech)[0]


def _scada_data(tenant_id, plant) -> SCADAData:
    df = kalibrasyon_penceresi(scada_oku(tenant_id, plant["id"]))   # G2-C1: pencere arşiv kesiminden başlar
    # v2.254 (Dalga 3.9): AC tavanında kırpılmış saatler kalibrasyona GİRMEZ — tavanlı güç DC fiziğini
    # yansıtmaz, eta_bos/BG uydurmasını aşağı çeker. Ölçüm silinmez; yalnız bu uydurmada NaN (gündüz NaN
    # → motor düşer). Karne bu saatleri saymaya devam eder (tahmin de tavanı modellemeli).
    if "kirpma" in df.columns:
        df.loc[df["kirpma"].fillna(False).astype(bool), "power_kw"] = float("nan")
    df = _kalibrasyon_izgarasi(df, plant)
    def _o(k):
        return df[k] if k in df.columns and df[k].notna().any() else None
    return SCADAData(
        power_kw=df["power_kw"], energy_kwh=_o("energy_kwh"),
        poa_irradiance=_o("poa_wm2"), temp_ambient=_o("t_air"),
        temp_module=_o("t_module"), wind_speed=_o("wind_ms"),
        plant_name=plant["name"], timestep_minutes=60,
    )


def _meteo(plant, df_index):
    start = df_index.min().strftime("%Y-%m-%d")
    end = df_index.max().strftime("%Y-%m-%d")
    return OpenMeteoClient().get_historical(
        latitude=plant["lat"], longitude=plant["lon"],
        start_date=start, end_date=end,
    )


def _plant_spec(plant) -> PlantSpec:
    """Geriye uyumlu ad (v2.597): tek kaynak `plant_spec_service.plant_spec_kur`; kalibrasyonsuz spec."""
    return plant_spec_kur(plant)


def _pj(plant) -> dict:
    """Geriye uyumlu ad (v2.597): `plant_spec_service.params_json`."""
    return params_json(plant)


def fizik_terimleri(tenant_id, plant_id) -> dict:
    """v2.255 — UI sözlüğü: IAM/spektral (santral) + kt referansı (ayar)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.config import get_settings
    with tenant_baglami(tenant_id) as s:
        pj = s.execute(text("SELECT params_json FROM plants WHERE id=:p"), {"p": plant_id}).scalar()
    pj = _pj({"params_json": pj})
    return {"iam": pj.get("iam_model") or "none", "spektral": pj.get("spectral_model") or "none",
            "kirlenme": pj.get("soiling_model") or "none", "kar": pj.get("kar_model") or "none",
            "kt_referans": get_settings().kt_referans}


def _pencere_gun(index) -> int | None:
    """v2.175: kalibrasyon penceresi (takvim günü) — kalibrasyonun GERÇEKTEN
    kullandığı ızgaranın ucundan uca aralığı. Gömülü 120 değil, iddia değil,
    ÖLÇÜM: rapor kontratındaki calibration.window_days bunu taşır; s09
    altyazısının ', N gün' iddiası ve D5'in tavan denetimi (saat ≤ gün×14)
    bu ölçüme dayanır. Boş/tekil indekste None — uydurma pencere yok
    (dürüst-eksiklik: iddia yoksa kart pencereyi söylemez, D5 uyarır)."""
    try:
        if index is None or len(index) < 2:
            return None
        return int((index.max() - index.min()).days) + 1
    except (TypeError, AttributeError, ValueError):
        return None


#: v2.380 (bulgu 31): AYLIK (cron) kalibrasyonun tazelik eşiği — son ölçüm
#: bundan eskiyse yeniden kalibrasyon koşmaz, MEVCUT ayar korunur. 1 Eki
#: canlı: 639 gündür veri gelmeyen kobay ay-başı cron'uyla Mod B'ye geçip
#: %98,6 sapmalı karne üretti. Sapma katmanının 3 günlük tazelik bekçisi
#: vardı (v2.274), kalibrasyonun HİÇ yoktu. Panelden ELLE kalibrasyon bu
#: eşiğe takılmaz — kullanıcı elindeki veriyle bilinçli kalibre edebilir.
KALIBRASYON_TAZELIK_GUN = 60


def kalibrasyon_bayat_mi(son_ts, simdi=None) -> tuple[bool, str]:
    """SAF: cron kalibrasyonu için tazelik hükmü. (bayat_mi, neden) döner."""
    if son_ts is None:
        return True, "hiç ölçüm yok"
    simdi = simdi or pd.Timestamp.now(tz="UTC")
    son = pd.Timestamp(son_ts)
    if son.tzinfo is None:
        son = son.tz_localize("UTC")
    yas = (simdi - son).days
    if yas > KALIBRASYON_TAZELIK_GUN:
        return True, f"son ölçüm {yas} gün önce (>{KALIBRASYON_TAZELIK_GUN})"
    return False, f"son ölçüm {yas} gün önce"


HOLDOUT_PAY = 0.2            # Faz 0 P0-04 (karar C4-1, 21.11): zaman sırasıyla son %20 holdout
HOLDOUT_ASGARI_SAAT = 72     # holdout diliminde bundan az geçerli saat varsa metrik yazılmaz (sayı uydurulmaz)


def _kronolojik_holdout(scada, meteo, plant_spec, *, threshold_kw: float = 1.0, pay: float = HOLDOUT_PAY, asgari_saat: int = HOLDOUT_ASGARI_SAAT,
                        temizle: bool = True) -> dict:
    """Faz 0 P0-04 (karar C4-1, 21.11.2026). ÜRETİM PARAMETRELERİNE DOKUNMAZ: pencere zaman sırasıyla (1−pay)/pay bölünür, ilk dilimle
    İKİNCİ (atılacak) bir uydurma yapılır, son dilimde `validate` koşulur. Dönen MAPE/WMAPE örneklem dışıdır; `kalibre_et`'in tüm
    pencereyle uydurduğu η_BoS/BG değişmez (bu fonksiyon girdilerini değiştirmez, çıktısı yalnız quality_json'a yazılır).
    Yetersiz veri / hata → metrik None + `holdout_not` (kalibrasyon düşmez)."""
    import time
    from pvquant.io.scada import SCADAData
    from pvquant.pipeline.forecast import forecast_7day
    from pvquant.validation.metrics import validate
    t0 = time.perf_counter()
    bos = {"mape_holdout_pct": None, "wmape_holdout_pct": None, "holdout_saat": None, "holdout_egitim_saat": None,
           "holdout_bas": None, "holdout_bit": None, "holdout_pay": pay, "holdout_sure_sn": None}
    pw = scada.power_kw.dropna().sort_index()
    if len(pw) < 2 * asgari_saat:
        return {**bos, "holdout_not": f"holdout için yetersiz ölçüm ({len(pw)} saat < {2 * asgari_saat})"}
    kesim = pw.index[int(len(pw) * (1.0 - pay))]
    def _dilim(s, egitim: bool):
        if s is None:
            return None
        return s[s.index < kesim] if egitim else s[s.index >= kesim]
    # QA C4-6: eğitim ızgarası NaN'lı ORİJİNAL seriden kesilir (dropna ızgarayı deler, zaman adımı denetimi düşer); pw yalnız kesim/holdout gerçeği için
    scada_e = SCADAData(power_kw=_dilim(scada.power_kw, True), energy_kwh=_dilim(scada.energy_kwh, True), poa_irradiance=_dilim(scada.poa_irradiance, True),
                        temp_ambient=_dilim(scada.temp_ambient, True), temp_module=_dilim(scada.temp_module, True), wind_speed=_dilim(scada.wind_speed, True),
                        plant_name=scada.plant_name, timestep_minutes=scada.timestep_minutes)
    try:
        cr_e = calibrate_from_scada(scada=scada_e, historical_meteo=meteo, plant=plant_spec, fit_bg=True, fit_eta_bos=True, clean_outliers=temizle,   # üretimle aynı bayraklar
                                    threshold_kw=threshold_kw)
    except ValueError as e:   # «Yetersiz veri» gibi beklenen durumlar
        return {**bos, "holdout_not": f"eğitim dilimi uydurulamadı: {e}"}
    pred = forecast_7day(meteo, cr_e.plant, measured_poa=scada.poa_irradiance).hourly["p_ac_kw"]
    gercek = _dilim(pw, False)
    ortak = pred.index.intersection(gercek.index)
    if len(ortak) < asgari_saat:
        return {**bos, "holdout_not": f"holdout diliminde ortak saat yetersiz ({len(ortak)} < {asgari_saat})"}
    rep = validate(pred.loc[ortak], gercek.loc[ortak], threshold=threshold_kw)
    if int(rep.n_samples) < asgari_saat:   # eşik üstü (gündüz) geçerli saat sayısı; gece saatleri metrik tabanına girmez
        return {**bos, "holdout_not": f"holdout diliminde geçerli saat yetersiz ({int(rep.n_samples)} < {asgari_saat})"}
    wm = getattr(rep, "wmape_pct", None)
    wm = None if wm is None or wm != wm else float(wm)   # NaN → None
    return {"mape_holdout_pct": float(rep.mape_pct), "wmape_holdout_pct": wm, "holdout_saat": int(rep.n_samples), "holdout_egitim_saat": int(cr_e.n_valid_hours),
            "holdout_bas": kesim.isoformat(), "holdout_bit": gercek.index.max().isoformat(), "holdout_pay": pay,
            "holdout_sure_sn": round(time.perf_counter() - t0, 2), "holdout_not": None}


def kalibre_et(tenant_id, plant: dict, hibrit: bool = False) -> dict:
    import time as _time
    scada = _scada_data(tenant_id, plant)
    pencere_gun = _pencere_gun(scada.power_kw.index)   # v2.175: ölçülü pencere
    meteo = _meteo(plant, scada.power_kw.index)
    _t0 = _time.perf_counter()
    cr = calibrate_from_scada(
        scada=scada, historical_meteo=meteo, plant=_plant_spec(plant),
        fit_bg=True, fit_eta_bos=True, clean_outliers=True,
    )
    _uretim_sure = round(_time.perf_counter() - _t0, 2)
    try:   # Faz 0 P0-04 (C4-1): örneklem dışı ölçüm — üretim uydurması (cr) yukarıda tamamlandı, buradan etkilenmez
        holdout = _kronolojik_holdout(scada, meteo, _plant_spec(plant))
    except Exception as e:   # ölçüm yardımcı; kalibrasyonu düşürmez
        holdout = {"mape_holdout_pct": None, "wmape_holdout_pct": None, "holdout_saat": None, "holdout_egitim_saat": None, "holdout_bas": None,
                   "holdout_bit": None, "holdout_pay": HOLDOUT_PAY, "holdout_sure_sn": None, "holdout_not": f"hesaplanamadı: {type(e).__name__}"}
    sonuc = {
        "mode": "B", "eta_bos": cr.eta_bos, "bg": cr.bg,
        "warnings": list(cr.warnings or []),
        "n_valid_hours": cr.n_valid_hours,
    }
    gate = None
    hyb = None
    if hibrit:
        res = run_hybrid_training(
            scada=scada, historical_meteo=meteo,
            plant_ctx={
                "capacity_kwp": plant["capacity_kwp"],
                "latitude": plant["lat"], "longitude": plant["lon"],
                "timezone": plant["tz"],
                "tilt": egim_azimut(plant)[0],
                "azimuth": egim_azimut(plant)[1],
                "panel_technology": panel_teknolojisi(plant.get("panel_tech")),   # G2-C1 (C2-2): monofacial → mono
                # B-1 v2.27: AC tavanı kaynağı → PlantProfile ailesi
                "ac_limit_kw": plant.get("ac_limit_kw"),
            },
            plant_name=plant["name"],
        )
      # v2.40: kapi cift kosullu — GORELI iyilesme YETMEZ, MUTLAK taban sart.
        # %35 ustu holdout MAPE "kullanilabilir model" degildir; kapi kapali
        # kalir, sistem Mod B'de durur ve sebep karneye yazilir.
        from pvquant.config import get_settings as _gs
        _cfg = _gs()
        HIBRIT_MUTLAK_TAVAN = _cfg.gate_mape_ceiling          # v2.53: ayardan
        HIBRIT_MUTLAK_TAVAN_WMAPE = _cfg.gate_wmape_ceiling   # v2.53: ayardan
        _w = getattr(res, "holdout_wmape_pct", None)
        _wtxt = f"{_w:.1f}" if _w is not None else "yok"
        _taban_ok = ((_w <= HIBRIT_MUTLAK_TAVAN_WMAPE) if _w is not None
                     else (res.holdout_mape_pct is not None
                           and res.holdout_mape_pct <= HIBRIT_MUTLAK_TAVAN))
        # v2.51-C: goreli esik de WMAPE diline tasinir. Ayrisma vakasi #1
        # kaniti: ayni holdout'ta MAPE-iyilesmesi %-43 derken WMAPE
        # hibriti 0,23p onde gormustu — kapi karari yanlis dilden geliyordu.
        _pw = getattr(res, "physics_wmape_pct", None)
        _w_iyi = (float((_pw - _w) / _pw * 100.0)
                  if (_w is not None and _pw is not None and _pw > 0) else None)
        _iyi_etkin = _w_iyi if _w_iyi is not None else res.improvement_pct
        _iyi_dil = "WMAPE" if _w_iyi is not None else "MAPE (yedek yol)"
        if (res.ok and _iyi_etkin is not None
                and _iyi_etkin >= _cfg.gate_min_improvement_pct
                and _taban_ok):
            sonuc["mode"] = "C"
            hyb = res
            gate = {
                "denendi": True, "gecti": True, "hata": False,   # 26.11: hata=True yalnız hibrit eğitimi İSTİSNA ile düşünce (kapı reddi değil)
                "iyilesme_pct": res.improvement_pct,
                "wmape_iyilesme_pct": _w_iyi,
                "holdout_mape": res.holdout_mape_pct,
                "fizik_mape": res.physics_mape_pct,
                "holdout_wmape": _w,
                "fizik_wmape": getattr(res, "physics_wmape_pct", None),
                "kapsama_p10_p90": getattr(res, "coverage_p10_p90_pct", None),
                "bant_ort_kw": getattr(res, "band_width_mean_kw", None),
                "bant_pct": getattr(res, "band_width_pct_of_p50", None),
            }
        else:
            gate = {
                "denendi": True, "gecti": False,
                # 26.11 (MODEL_BC_MEVCUT_DURUM §0): run_hybrid_training istisnayı yutup ok=False döndüğünde bu, kapı reddi DEĞİL
                # altyapı/veri hatasıdır (ör. PanelSpec ValidationError 01.10'da Mod C'yi 2 ay sessizce engelledi). Ayrı bayrak +
                # sebep öneki ile görünür kılınır; model davranışı aynı (Mod B'de kalınır), kayıt dürüst.
                "hata": (not res.ok),
                "iyilesme_pct": res.improvement_pct,
                "wmape_iyilesme_pct": _w_iyi,
                "holdout_mape": res.holdout_mape_pct,
                "fizik_mape": res.physics_mape_pct,
                "holdout_wmape": _w,
                "fizik_wmape": getattr(res, "physics_wmape_pct", None),
                "kapsama_p10_p90": getattr(res, "coverage_p10_p90_pct", None),
                "bant_ort_kw": getattr(res, "band_width_mean_kw", None),
                "bant_pct": getattr(res, "band_width_pct_of_p50", None),
                "sebep": ((f"hibrit DENENEMEDİ (altyapı/veri hatası, kapı reddi değil): {res.error}" if res.error else None)
                          or (f"holdout WMAPE %{_wtxt} > "
                              f"%{HIBRIT_MUTLAK_TAVAN_WMAPE:.0f} tavanı (WMAPE)"
                              if not _taban_ok
                              else (f"iyilesme %{_iyi_etkin:.1f} < "
                                    f"{_cfg.gate_min_improvement_pct:g} ({_iyi_dil})"
                                    if _iyi_etkin is not None
                                    else "iyilesme hesaplanamadi"))),            }
    if hibrit and gate is not None and gate.get("hata"):
        sonuc["hibrit_hata"] = res.error   # 26.11: çağıran (aylık iş) günlüğe/sonuc_json'a yazar; sessiz düşüş yok
    # G2-C1 (C2-8): Mod B kalite kapısı — düşerse HİÇBİR kayıt yazılmaz (mevcut aktif kalibrasyon korunur), sebep döner/günlüğe.
    kapi_ok, kapi_neden = mod_b_kapisi(cr.n_valid_hours, holdout.get("wmape_holdout_pct"), getattr(cr.validation_after, "total_deviation_pct", None))
    if not kapi_ok:
        return {"mode": "atlandi", "kapi": kapi_neden, "calibration_id": None, "gate": gate, "eta_bos": cr.eta_bos, "bg": cr.bg,
                "n_valid_hours": cr.n_valid_hours, "warnings": list(cr.warnings or []), "holdout": holdout,
                "hibrit_hata": sonuc.get("hibrit_hata")}
    from pvquant.surum import yazilim_surumu as _ys   # Faz 0 P0-04 (20.11): kalite kaydına sürüm ve değerlendirme sınıfı damgası
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "UPDATE calibrations SET active=false WHERE plant_id=:p"),
            {"p": plant["id"]})
        cal_id = s.execute(text(
            "INSERT INTO calibrations(tenant_id,plant_id,mode,params_json,"
            " quality_json,gate_json,n_valid_hours,active) "
            "VALUES(:t,:p,:m,:pa,:q,:g,:n,true) RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "m": sonuc["mode"],
             "pa": json.dumps({"eta_bos": cr.eta_bos, "bg": cr.bg}),
             "q": json.dumps({
                 "meteo_kaynak":        getattr(meteo, "kaynak", "open-meteo"),   # v2.269: künye gerçek kullanımı okur
                 "degerlendirme":       ("orneklem_ici+holdout" if holdout.get("mape_holdout_pct") is not None else "orneklem_ici"),   # Faz 0 P0-04: mape/wmape uydurma dönemiyle AYNI saatlerde; *_holdout_* son %20 örneklem dışı (C4-1)
                 "yazilim_surumu":      _ys(),
                 "kalibrasyon_sure_sn": _uretim_sure,
                 **holdout,
                 "mape_pct":            getattr(cr.validation_after,  "mape_pct", None),
                 "mape_before_pct":     getattr(cr.validation_before, "mape_pct", None),
                 "wmape_pct":           getattr(cr.validation_after,  "wmape_pct", None),
                 "wmape_before_pct":    getattr(cr.validation_before, "wmape_pct", None),
                 "deviation_pct":       getattr(cr.validation_after,  "total_deviation_pct", None),
                 "deviation_before_pct":getattr(cr.validation_before, "total_deviation_pct", None),
                 "warnings": sonuc["warnings"],
                 # v2.175: kök iş kapanışı — report_service:127 bu alanı
                 # okuyordu, pipeline yazmıyordu; artık ölçümden yazılıyor.
                 "window_days": pencere_gun,
             }, default=str),
             "g": json.dumps(gate) if gate else None,
             "n": cr.n_valid_hours}).scalar()
        if hyb is not None:
            yol = ARTIFACT_DIR / f"hyb_{plant['id']}_{cal_id}.pkl"
            with open(yol, "wb") as f:
                pickle.dump(hyb.model, f)
            s.execute(text(
                "UPDATE ml_models SET active=false WHERE plant_id=:p"),
                {"p": plant["id"]})
            s.execute(text(
                "INSERT INTO ml_models(tenant_id,plant_id,artifact_path,"
                " training_report_json,active) VALUES(:t,:p,:y,:r,true)"),
                {"t": tenant_id, "p": plant["id"], "y": str(yol),
                 "r": json.dumps(session_ozeti(hyb), default=str)})
    sonuc["calibration_id"] = str(cal_id)
    sonuc["gate"] = gate
    # Faz 1 Mod C bekçisi (27.11.2026): ml_models(active=true) «en son artefakt» demektir, MÜŞTERİ aktivasyonu DEĞİL —
    # servis kararı forecast_service.girdileri_topla'da ayar + sha onayı ile (mod_c_bekcisi). Günlüğe açık yazılır.
    from pvquant.services.mod_c_bekcisi import mod_c_aktivasyon
    _akt = mod_c_aktivasyon()
    sonuc["musteri_aktivasyon"] = {"mod_c_musteri": ("acik" if _akt["etkin"] else "kapali"), "onayli_artefakt_sayisi": len(_akt["onayli"]),
                                   "not": "aylık kalibrasyon müşteri aktivasyonu vermez; C servis için ayar + artefakt sha onayı gerekir"}
    return sonuc


def aktif_kalibrasyon(tenant_id, plant_id):
    """UI'nin tek kalibrasyon okuması. Yoksa None."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "SELECT id, mode, params_json, quality_json, gate_json,"
            " n_valid_hours, created_at FROM calibrations "
            "WHERE plant_id=:p AND active "
            "ORDER BY created_at DESC LIMIT 1"),
            {"p": plant_id}).first()

def kalibrasyon_ozeti(tenant_id, plant_id):
    """v2.122 — aktif kaydin UI sozlesmesi (JSON-donusur sozluk).
    UYDURMA YOK: kayit ne tasiyorsa o; uyarilar dahil. Yoksa None."""
    r = aktif_kalibrasyon(tenant_id, plant_id)
    if r is None:
        return None
    q = r.quality_json or {}
    pj = r.params_json or {}
    return {
        "mode": r.mode,
        "fizik_terimleri": fizik_terimleri(tenant_id, plant_id),   # v2.255
        "eta_bos": pj.get("eta_bos"), "bg": pj.get("bg"),
        "gecerli_saat": r.n_valid_hours,
        "tarih": r.created_at.isoformat() if r.created_at else None,
        "mape_once": q.get("mape_before_pct"), "mape_sonra": q.get("mape_pct"),
        "wmape_once": q.get("wmape_before_pct"), "wmape_sonra": q.get("wmape_pct"),
        "sapma_once": q.get("deviation_before_pct"), "sapma_sonra": q.get("deviation_pct"),
        # Faz 0 P0-04 (C4-1): örneklem dışı ölçüm (eski kayıtlarda yok → None; UI «—» ve not)
        "degerlendirme": q.get("degerlendirme"), "mape_holdout": q.get("mape_holdout_pct"), "wmape_holdout": q.get("wmape_holdout_pct"),
        "holdout_saat": q.get("holdout_saat"), "holdout_bas": q.get("holdout_bas"), "holdout_bit": q.get("holdout_bit"), "holdout_not": q.get("holdout_not"),
        "uyarilar": q.get("warnings") or [],
    }


def kalibrasyon_gecmisi(tenant_id, plant_id):
    """Mod gecmisi icin tum kayitlar (eski->yeni)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "SELECT created_at, mode, gate_json FROM calibrations "
            "WHERE plant_id=:p ORDER BY created_at"),
            {"p": plant_id}).fetchall()
