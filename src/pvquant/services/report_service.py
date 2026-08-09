"""Rapor baglami: forecast_values + calibrations -> ReportContext.
reporting paketi TEK SATIR degismez (Parca 3 §4).
Fable 5 v1.7 kurali: JSONB dict olarak geldigi icin isinstance kontrolu."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.reporting import ReportContext, build_pdf, build_excel, build_json
from pvquant.services.forecast_service import son_kosu


def rapor_baglami(tenant_id, plant: dict) -> ReportContext | None:
    h = son_kosu(tenant_id, plant["id"])
    if h is None:
        return None
    h = h.rename(columns={"physics_kw": "p_dc_kw"})  # gecici: dc yoksa fizik
    h["energy_kwh"] = h["p50_kw"]
    h["poa"] = 0.0
    h["temp_cell"] = 25.0
    yerel = h.tz_convert(plant["tz"])
    daily = h["energy_kwh"].groupby(h.index.tz_convert("UTC").date).sum()
    import pandas as pd
    daily.index = pd.to_datetime(daily.index)
    with tenant_baglami(tenant_id) as s:
        # v2.94: rapor kimligi KOSUDAN gelir, kalibrasyondan degil.
        # Onceki hal: artifact-yok gerilemesiyle Mod B kosan kosu raporda
        # "Mod C" etiketi tasiyordu; run_at da rapor ani yaziliyordu.
        kosu = s.execute(text(
            "SELECT run_at, mode, model FROM forecast_runs "
            "WHERE plant_id=:p ORDER BY run_at DESC LIMIT 1"),
            {"p": plant["id"]}).first()
        cal = s.execute(text(
            "SELECT mode,params_json,quality_json,gate_json,n_valid_hours,"
            " created_at FROM calibrations WHERE plant_id=:p AND active"),
            {"p": plant["id"]}).first()
    ctx = ReportContext(
        plant_name=plant["name"],
        capacity_kwp=plant["capacity_kwp"],
        latitude=plant["lat"],
        longitude=plant["lon"],
        tilt_deg=plant.get("tilt") or 20,
        azimuth_deg=plant.get("azimuth") or 180,
        plant_tz=plant["tz"],
        run_at_utc=(kosu.run_at if kosu else datetime.now(timezone.utc)),
        mode=(kosu.mode if kosu else (cal.mode if cal else "A")),
        model_name=(kosu.model if kosu else "barhdadi_bennis"),
        meteo_source="open-meteo",
        hourly=h,
        daily_kwh=daily,
    )
    # v2.96 durusma dersi (Mod C rozet + '—' bant celiskisi): son_kosu
    # p10/p90'i ZATEN tasiyor, baglanmiyordu. Varsa gunluk banda cevir.
    if "p10_kw" in h.columns and h["p10_kw"].notna().any():
        gr = h.index.tz_convert("UTC").date
        ctx.daily_p10 = h["p10_kw"].groupby(gr).sum()
        ctx.daily_p90 = h["p90_kw"].groupby(gr).sum()
        ctx.daily_p10.index = pd.to_datetime(ctx.daily_p10.index)
        ctx.daily_p90.index = pd.to_datetime(ctx.daily_p90.index)
    if cal:
        # Fable 5 v1.7: JSONB psycopg-den dict olarak gelir, str degil
        pa = cal.params_json if isinstance(cal.params_json, dict) else json.loads(cal.params_json)
        q_raw = cal.quality_json
        q = q_raw if isinstance(q_raw, dict) else (json.loads(q_raw) if q_raw else {})
        ctx.eta_bos = pa.get("eta_bos")
        ctx.bg = pa.get("bg")
        ctx.mape_pct = q.get("mape_pct")
        ctx.warnings = q.get("warnings", [])
        ctx.n_valid_hours = cal.n_valid_hours
        ctx.calibrated_at = cal.created_at
        g_raw = cal.gate_json
        g = g_raw if isinstance(g_raw, dict) else (json.loads(g_raw) if g_raw else {})
        if cal.mode == "C" and g.get("gecti"):
            ctx.holdout_mape_pct = g.get("holdout_mape")
            ctx.holdout_physics_mape_pct = g.get("fizik_mape")
            ctx.holdout_improvement_pct = g.get("iyilesme_pct")
            ctx.kapsama_p10_p90 = g.get("kapsama_p10_p90")
            ctx.bant_pct = g.get("bant_pct")
    # v2.96 (sartname S4): dogruluk karnesi — skill_daily fotografi.
    # Rapor yalniz OKUR (hesap worker'da); karne yoksa ctx.karne None
    # kalir, S4 sayfasi durust 'veri eksik' isareti basar.
    from pvquant.services.forecast_service import skill_gecmisi
    # gun=120: dogruluk.py ve API /skill ile AYNI pencere (uc yuzey ayni
    # sayiyi soyler). Kapsanan tarihler S4 basliginda acikca yazilir
    # (karne_donem_metni — v2.71-E dersi), genis pencere yaniltmaz.
    kr = skill_gecmisi(tenant_id, plant["id"], gun=120)
    if kr is not None and len(kr) > 0:
        ctx.karne = kr
    # v2.96 tam sartname kaynaklari — hepsi ham okuma, hesap yok; bos
    # gelen her sey None kalir, ilgili sayfa durust isaret basar.
    from pvquant.services.iklim_service import iklim_oku
    ik = iklim_oku(tenant_id, plant["id"])
    if ik is not None and len(ik) > 0:
        ctx.iklim = ik
    with tenant_baglami(tenant_id) as s:
        # S6: son 12 ayin gerceklesen uretimi (saatlik kW ~ kWh/saat)
        ctx.son12 = pd.read_sql(text(
            "SELECT date_trunc('month', ts_utc) AS ay,"
            " SUM(power_kw)/1000.0 AS actual_mwh "
            "FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
            "AND ts_utc >= date_trunc('month', now()) - INTERVAL '12 months' "
            "GROUP BY 1 ORDER BY 1"),
            s.connection(), params={"p": plant["id"]}, parse_dates=["ay"])
        if len(ctx.son12) == 0:
            ctx.son12 = None
        # S5: veri kalitesi karnesi — flag dagilimi + kapsama
        fl = s.execute(text(
            "SELECT flag, COUNT(*) AS n FROM scada_hourly "
            "WHERE plant_id=:p GROUP BY flag"), {"p": plant["id"]}).fetchall()
        if fl:
            ctx.flag_dagilimi = {r.flag: int(r.n) for r in fl}
            toplam = sum(ctx.flag_dagilimi.values())
            if toplam:
                ctx.coverage_pct = 100.0 * ctx.flag_dagilimi.get(
                    "valid", 0) / toplam
        sc = s.execute(text(
            "SELECT MIN(ts_utc) AS ilk, MAX(ts_utc) AS son "
            "FROM scada_hourly WHERE plant_id=:p"),
            {"p": plant["id"]}).first()
        if sc and sc.son:
            ctx.son_scada_ts = sc.son
            ctx.ilk_scada_ts = sc.ilk  # v2.103: künye aralığı sabit kalmasın
        # S8: hedef gun (kosu penceresinin ilk tam gunu = yarin) icin son
        # kosularda P50 evrimi. <2 kosu ise sayfa 'veri eksik' der.
        if kosu:
            hedef = (kosu.run_at.date() + _dt.timedelta(days=1))
            ev = pd.read_sql(text(
                "SELECT r.run_at, SUM(f.p50_kw)/1000.0 AS p50_mwh, "
                "SUM(f.p90_kw - f.p10_kw)/2000.0 AS half_mwh "  # v2.103: evrim bandı
                "FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
                "WHERE f.plant_id=:p AND f.ts_utc >= :g0 AND f.ts_utc < :g1 "
                "GROUP BY r.run_at ORDER BY r.run_at DESC LIMIT 8"),
                s.connection(), params={
                    "p": plant["id"],
                    "g0": _dt.datetime.combine(hedef, _dt.time.min,
                                               tzinfo=timezone.utc),
                    "g1": _dt.datetime.combine(
                        hedef + _dt.timedelta(days=1), _dt.time.min,
                        tzinfo=timezone.utc)},
                parse_dates=["run_at"]).sort_values("run_at")
            if len(ev) > 0:
                ctx.kosu_evrim = ev
                ctx.evrim_gunu = hedef
        # v2.103 (E.3-a, B1+B5): worker fotograflari — report_stats'tan HAM
        # okuma, hesap yok. Gecis bekcisi: migration oncesi tablo yoksa
        # alanlar None kalir, taslak _zorunlu() isim isim ValueError verir
        # (sessiz Konya varsayilani YOK — E.2 ilkesi).
        if s.execute(text(
                "SELECT to_regclass('report_stats') IS NOT NULL")).scalar():
            for r in s.execute(text(
                    "SELECT key, value_json FROM report_stats "
                    "WHERE plant_id=:p"), {"p": plant["id"]}).fetchall():
                v = (r.value_json if isinstance(r.value_json, dict)
                     else json.loads(r.value_json))   # Fable 5 v1.7 kurali
                if r.key == "uninterrupted_days":
                    ctx.uninterrupted_days = v.get("value")
                elif r.key == "error_dist":
                    ctx.error_dist = v
        # v2.103 (B2, karar 9 Agu): aylik kalite kirilimi — son 6 ay, yuzde.
        # Siniflama: gecerli=valid; hatali={yanlis_yil*,gece_uretim,
        # kapasite_ustu,okunamayan}; diger=kalan (donmus + yeni bayraklar).
        # diger = 100-g-h: yuvarlama sonrasi toplam 100 garanti.
        ql = pd.read_sql(text(
            "SELECT date_trunc('month', ts_utc) AS ay, COUNT(*) AS n, "
            " COUNT(*) FILTER (WHERE flag='valid') AS g, "
            " COUNT(*) FILTER (WHERE flag IN ('gece_uretim','kapasite_ustu',"
            "'okunamayan') OR flag LIKE 'yanlis%') AS h "
            "FROM scada_hourly WHERE plant_id=:p "
            "AND ts_utc >= date_trunc('month', now()) - INTERVAL '5 months' "
            "GROUP BY 1 ORDER BY 1"), s.connection(),
            params={"p": plant["id"]}, parse_dates=["ay"])
        if len(ql) > 0:
            _ayl = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            gy = [round(100 * r.g / r.n) for r in ql.itertuples()]
            hy = [round(100 * r.h / r.n) for r in ql.itertuples()]
            ctx.quality_monthly = {
                "aylar": [_ayl[r.ay.month - 1] for r in ql.itertuples()],
                "gecerli": gy, "hatali": hy,
                "diger": [max(0, 100 - a - b) for a, b in zip(gy, hy)]}
    return ctx

# --------------------------------------------------------------- Adim 6
import datetime as _dt
from pvquant.reporting import build_pdf, build_excel, build_json


def uret(tenant_id, plant: dict, fmt: str):
    """Tek uretim kapisi (KURAL 2 — sayfada build_* cagrisi olmaz).
    Donus: (bytes, dosya_adi, uretim_ts). ctx None ise ValueError —
    sayfa bos-durum bekcileri bunu zaten engeller."""
    ctx = rapor_baglami(tenant_id, plant)
    if ctx is None:
        raise ValueError("rapor baglami kurulamadi — once tahmin uretin")
    ad_kok = plant["name"].replace(" ", "_")
    gun = _dt.date.today().strftime("%Y%m%d")
    if fmt == "pdf":
        veri, uzanti = build_pdf(ctx), "pdf"
    elif fmt == "xlsx":
        veri, uzanti = build_excel(ctx), "xlsx"
    elif fmt == "json":
        j = build_json(ctx)
        veri = j.encode("utf-8") if isinstance(j, str) else j
        uzanti = "json"
    else:
        raise ValueError(f"bilinmeyen format: {fmt}")
    return veri, f"PVQuant_{ad_kok}_{gun}.{uzanti}", _dt.datetime.now()


def rapor_id_uret(tenant_id, plant: dict, mode: str) -> str:
    """v2.103 (B6, karar 9 Agu): PVQ-<tarih>-<mod>-<sira>.
    Sira report_log BIGSERIAL'den — gunluk sayac degil: sifirlanmaz ve
    'hangi rapor ne zaman uretildi' denetim izini bedavaya verir."""
    with tenant_baglami(tenant_id) as s:
        rid = s.execute(text(
            "INSERT INTO report_log(tenant_id,plant_id,mode) "
            "VALUES(:t,:p,:m) RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "m": mode}).scalar()
    return "PVQ-%s-%s-%04d" % (_dt.date.today().isoformat(), mode, rid % 10000)
