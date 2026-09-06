"""Tahmin uret ve ARSIVLE. Ekranlar yalniz bu tablolardan okur."""
from __future__ import annotations
import json, pickle
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import text
from pvquant.config import get_settings
from pvquant.db import tenant_baglami
from pvquant.io.meteo import OpenMeteoClient
from pvquant.pipeline.forecast import forecast_7day
from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly
from pvquant.services.calib_service import _plant_spec


def _model_yukle(yol: str):
    """v2.80 — artifact'i yukler; diskte yoksa None (kosu olmez, mod duser).
    Yalniz yasanan vaka yakalanir (FileNotFoundError); baska hatalar
    maskelenmez — bozuk pickle vb. hala gurultuyle patlar."""
    try:
        with open(yol, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"UYARI: model artifact'i diskte yok ({yol}) — mod C->B dusuluyor")
        return None


def kosu_cercevesi_denetle(h) -> None:
    """v2.176 (backtest kök sebebi): run yazan HER yol önce bunu çağırır.
    İlke: BAŞSIZ RUN BIRAKILMAZ — values taşımayacak bir koşu için run
    satırı hiç açılmaz (15 Nis vakasının yapısal kapanışı; v2.164 son_kosu
    ve v2.171 kosu_gecmisi süzgeçleri belirtiyi gizler, bu kaynağı kapatır).
    Boş çerçeve ya da p50 tamamı NaN → ValueError, run YAZILMADAN."""
    if h is None or len(h) == 0:
        raise ValueError("koşu yazılmadı: saatlik çerçeve boş — "
                         "başsız run bırakılmaz (meteo kaynağı bu aralık "
                         "için veri döndürmemiş olabilir)")
    if "p50_kw" not in h.columns or h["p50_kw"].isna().all():
        raise ValueError("koşu yazılmadı: p50_kw yok ya da tamamı NaN — "
                         "değersiz koşu için run açılmaz")


def uret_ve_kaydet(tenant_id, plant: dict) -> str:
    meteo = OpenMeteoClient().get_forecast(
        latitude=plant["lat"], longitude=plant["lon"],
        days=get_settings().forecast_horizon_days)  # v2.69: 7g -> 16g
    with tenant_baglami(tenant_id) as s:
        cal = s.execute(text(
            "SELECT mode, params_json FROM calibrations "
            "WHERE plant_id=:p AND active "
            "ORDER BY created_at DESC LIMIT 1"), {"p": plant["id"]}).first()
        ml = s.execute(text(
            "SELECT artifact_path FROM ml_models "
            "WHERE plant_id=:p AND active "
            "ORDER BY created_at DESC LIMIT 1"), {"p": plant["id"]}).first()
    mode = cal.mode if cal else "A"
    spec = _plant_spec(plant)
    if cal:
        pr = json.loads(cal.params_json) if isinstance(cal.params_json, str) else cal.params_json
        # kalibre katsayilar spec'e islenir — PlantSpec alan adlarini dogrula
        if pr.get("eta_bos"): spec.eta_bos = pr["eta_bos"]
        # v2.133: params_json.bg GEOMETRIK BG'dir (calibration.py BG fit'i
        # bifacial_gain_geometric icin kosar); BF (bifaciality, 0.7) _plant_spec
        # kurar. Eski satir bg'yi BF yuvasina yaziyordu -> canli tahmin neti
        # 0.347(varsayilan BG) x bg x albedo ile kuruyordu (yanlis carpim).
        if pr.get("bg") is not None: spec.bifacial_gain_geometric = pr["bg"]
    fr = forecast_7day(meteo, spec)
    h = fr.hourly.rename(columns={"p_ac_kw": "p50_kw"})
    h["physics_kw"] = h["p50_kw"]; h["ml_kw"] = None
    h["p10_kw"] = None; h["p90_kw"] = None
    h["p25_kw"] = None; h["p75_kw"] = None   # v2.204: ic bant — A/B'de yok
    if mode == "C" and ml:
        model = _model_yukle(ml.artifact_path)
        if model is None:
            # v2.80: DB 'aktif model var' der, disk 'yok' derse kosu OLMEZ —
            # kalibre-fizik (B) moduna dusulur; etiket kayda durustce gider
            # (20:25 vakasi: acilis yarisinda artifact henuz diskte yoktu).
            mode = "B"
        hh = hybrid_forecast_hourly(model, meteo) if model is not None else None
        if hh is not None:
            h["p50_kw"] = hh["p50_kw"].reindex(h.index)
            h["ml_kw"] = h["p50_kw"] - h["physics_kw"]
            for k in ("p10_kw", "p25_kw", "p75_kw", "p90_kw"):  # v2.204: +ic bant
                if k in hh.columns: h[k] = hh[k].reindex(h.index)
    # v2.273 (Dalga 2, ★ onaylı): ensemble bandı — taze GEFS üyeleri varsa üye başına fizik koşusundan ampirik kantiller
    # HAM bandı verir (P50 hibrit kalır); üye yoksa yukarıdaki model bandı. Konformal bunun üstüne uygulanır.
    from pvquant.services import ensemble_service as _es
    _q, _bant = _es.bant_uret(plant, spec, meteo, h, get_settings().forecast_horizon_days)
    if _q is not None:
        for k in ("p10", "p25", "p75", "p90"):
            # üye ufku dışındaki saatler (GEFS koşu+3 s öncesi ve +240 s sonrası) model bandında kalır — NaN bant yazılmaz
            _yeni = _q[k].reindex(h.index)
            h[f"{k}_kw"] = _yeni.where(_yeni.notna(), h[f"{k}_kw"]) if h[f"{k}_kw"].notna().any() else _yeni
    # v2.274 (Dalga 2, ★ onaylı): trend/sapma katmanı — son 7 günün saat-bazlı ölçüm/tahmin oranı; yalnız taze SCADA ve
    # anlamlı sapma varsa (aksi hâlde dokunmaz). Konformal bundan SONRA gelir.
    from pvquant.services import sapma_service as _sp
    _sapma = _sp.ayar_getir(tenant_id, plant)
    h = _sp.uygula_df(h, _sapma, plant.get("tz") or "UTC")
    # v2.252 (Dalga 2.7, ★ onaylı): konformal bant kalibrasyonu — ham kantiller saklanır,
    # servis edilen bant q̂ ile düzeltilir; ayar yoksa ham = servis. Çekirdek dokunulmadı.
    from pvquant.services import konformal_service as _kf
    _ayar = _kf.ayar_getir(tenant_id, plant["id"]) if mode == "C" else None
    h = _kf.uygula_df(h, _ayar, plant.get("ac_limit_kw") or plant.get("capacity_kwp"))
    kosu_cercevesi_denetle(h)   # v2.176: run açılmadan önce
    with tenant_baglami(tenant_id) as s:
        _kaynak = meteo.kaynak   # v2.189: tek değer — özet + INSERT aynı; v2.268: veriden ('acik-nwp' | 'open-meteo')
        meteo_ozet = json.dumps({
            "kaynak": _kaynak,
            "nwp_model": meteo.nwp_model,   # v2.268
            "bant": _bant,                   # v2.273: {'kaynak': 'gefs', 'uye': n} | {'kaynak': 'model'}
            "sapma": {k: v for k, v in _sapma.items() if k != "oran_saat"},   # v2.274: aktif/neden/oran_genel
            "cekim_utc": datetime.now(timezone.utc).isoformat(),
            "gunler": [
                {"tarih": str(g), "t_max": round(t, 1),
                 "ghi_kwh_m2": round(ghi_g / 1000.0, 1)}
                for g, t, ghi_g in list(_gun_ozetleri(meteo, plant["tz"]))[:3]
            ],
        }, default=str)
        run_id = s.execute(text(
            "INSERT INTO forecast_runs(tenant_id,plant_id,mode,model,"
            " meteo_source,meteo_ozet_json)"
            " VALUES(:t,:p,:m,:mo,:ms,:oz) RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "m": mode,
             "mo": "hybrid_residual" if mode == "C" else "barhdadi_bennis",
             "ms": _kaynak,
             "oz": meteo_ozet}).scalar()
        satirlar = [{"t": tenant_id, "r": run_id, "p": plant["id"], "ts": ts,
                     "p50": _f(v["p50_kw"]), "p10": _f(v["p10_kw"]),
                     "p90": _f(v["p90_kw"]),
                     "p25": _f(v["p25_kw"]), "p75": _f(v["p75_kw"]),  # v2.204
                     "p10h": _f(v["p10_ham_kw"]), "p90h": _f(v["p90_ham_kw"]),  # v2.252
                     "ph": _f(v["physics_kw"]),
                     "ml": _f(v["ml_kw"])} for ts, v in h.iterrows()]
        s.execute(text(
            "INSERT INTO forecast_values(tenant_id,run_id,plant_id,ts_utc,"
            " p50_kw,p10_kw,p90_kw,p25_kw,p75_kw,physics_kw,ml_kw,p10_ham_kw,p90_ham_kw) "
            "VALUES(:t,:r,:p,:ts,:p50,:p10,:p90,:p25,:p75,:ph,:ml,:p10h,:p90h)"), satirlar)
        # v2.176 son-bekçi: commit'ten önce, aynı işlemde sayım. Tutmazsa
        # raise → tenant_baglami rollback → run da values da gitmez. Bu,
        # mekanizma-bağımsız garanti: hangi yoldan gelirse gelsin (sessiz
        # no-op, kısmi yazım) başsız/eksik run COMMIT EDİLEMEZ.
        _n = s.execute(text(
            "SELECT count(*) FROM forecast_values WHERE run_id=:r"),
            {"r": run_id}).scalar()
        if _n != len(satirlar):
            raise RuntimeError(
                "koşu geri alındı: values %s/%s yazıldı — eksik koşu "
                "commit edilmez" % (_n, len(satirlar)))
    return str(run_id)


def _f(v):
    return None if v is None or pd.isna(v) else float(v)


def _gun_ozetleri(meteo, tz: str):
    """Meteo serilerini yerel gune grupla; her gun icin (tarih, t_max, ghi_toplam_wh_m2).
    Fable 5 v1.8: hava_3gun icin en fazla 3 gun kullanilir."""
    ta = meteo.temp_air.tz_convert(tz)
    gh = meteo.ghi.tz_convert(tz)
    ta_gun = ta.groupby(ta.index.date).max()
    gh_gun = gh.groupby(gh.index.date).sum()
    for gun in sorted(set(ta_gun.index) | set(gh_gun.index)):
        yield gun, float(ta_gun.get(gun, 0.0)), float(gh_gun.get(gun, 0.0))


def son_kosu(tenant_id, plant_id) -> pd.DataFrame | None:
    with tenant_baglami(tenant_id) as s:
        run = s.execute(text(
            "SELECT id FROM forecast_runs WHERE plant_id=:p "
            "AND EXISTS (SELECT 1 FROM forecast_values v "
            "  WHERE v.run_id = forecast_runs.id) "
            "ORDER BY run_at DESC LIMIT 1"), {"p": plant_id}).first()
        if not run: return None
        return pd.read_sql(text(
            "SELECT ts_utc,p50_kw,p10_kw,p90_kw,p25_kw,p75_kw,"  # v2.204
            "physics_kw,ml_kw "
            "FROM forecast_values WHERE run_id=:r ORDER BY ts_utc"),
            s.connection(), params={"r": run.id},
            index_col="ts_utc", parse_dates=["ts_utc"])

def aylik_beklenti(tenant_id, plant_id) -> dict:
    """v2.205 — forecast_daily'den ay bazli beklenti toplami.
    Doner: {"YYYY-MM": {"mwh": float, "gun_sayisi": int}}. Sunum kurali
    cagiranin: ay TAM kapsanmadan (gun_sayisi < ayin gunu) beklenti
    gosterilmez — kismi toplam yaniltir."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT to_char(gun,'YYYY-MM') AS ay,"
            " SUM(p50_kwh)/1000.0 AS mwh, COUNT(*) AS gun_sayisi "
            "FROM forecast_daily WHERE plant_id=:p "
            "GROUP BY 1 ORDER BY 1"), {"p": plant_id}).fetchall()
    return {r.ay: {"mwh": float(r.mwh), "gun_sayisi": int(r.gun_sayisi)}
            for r in rows}


def skill_gecmisi(tenant_id, plant_id, gun: int = 30):
    """skill_daily'den son N gunun karnesi. SUNUM icin ham okuma;
    hesap yok (gece skill hesabini worker yapar — tek uretici o)."""
    import pandas as pd
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return pd.read_sql(text(
            "SELECT date, horizon_bucket, mape, naive_wmape, skill_vs_naive, "
            "nmae, nrmse, nmbe, pinball_p10, pinball_p50, pinball_p90, crps, picp80, "
            "kapsama_p10, kapsama_p90, bant_n "
            "FROM skill_daily WHERE plant_id=:p "
            "AND date >= current_date - (:g * INTERVAL '1 day') "
            "ORDER BY date"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["date"])

def kosu_gecmisi(tenant_id, plant_id, n: int = 10):
    """Gecmis kosular tablosu icin hafif okuma (yeni->eski)."""
    from sqlalchemy import text as _text
    from pvquant.db import tenant_baglami as _tb
    with _tb(tenant_id) as s:
        # v2.171: bos kosu (values yazilmamis) GIZLIDIR — kullanici karari
        # 20 Agu; son_kosu ile ayni EXISTS kalibi (v2.164). Silme gecmisi
        # temizler, suzgec gelecegi: yarim kalan kosular listeye sizmasin.
        return s.execute(_text(
            "SELECT run_at, mode, model, meteo_ozet_json->'bant' AS bant, meteo_ozet_json->'sapma' AS sapma FROM forecast_runs "
            "WHERE plant_id=:p "
            "AND EXISTS (SELECT 1 FROM forecast_values v "
            "  WHERE v.run_id = forecast_runs.id) "
            "ORDER BY run_at DESC LIMIT :n"),
            {"p": plant_id, "n": n}).fetchall()
