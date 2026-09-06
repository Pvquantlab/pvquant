"""v2.281 — Tablo 3.5 satır 4: şablon raporlar — kapasite testi, fatura/uzlaştırma özeti, kullanılabilirlik (HTML).

pvquant.ext.platform.rapor_sablon üzerinden; 16 sayfalık ana rapora ek, kısa ve tek amaçlı belgeler. Kapasite testi
ölçülen düzlem ışınımı (POA) ister — yoksa dürüstçe 409 (uydurma ışınımla test yapılmaz). Fatura: aylık SCADA üretimi ×
tarife (params_json.tarife; PTF tipi için EPİAŞ/senaryo fiyatı) − dengesizlik (simülatör). Künye satırı kaynak_service'ten.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from pvquant.ext.platform import rapor_sablon as rs

SABLONLAR = ("kapasite-testi", "fatura", "kullanilabilirlik")


def _kunye() -> str:
    try:
        from pvquant.services.kaynak_service import rapor_kunye_satiri
        return rapor_kunye_satiri()
    except Exception:   # noqa: BLE001
        return "Veriler PVQuant tarafından işlenmiştir."


def kapasite_testi(tenant_id, plant: dict, gun: int = 30) -> rs.Rapor:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services.calib_service import _plant_spec
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, poa_wm2, t_air, wind_ms FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
            "AND ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day') ORDER BY ts_utc"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc"], index_col="ts_utc")
    if df.empty or df["poa_wm2"].notna().sum() < 50:
        raise ValueError("kapasite testi için ölçülen düzlem ışınımı (POA) gerekir — bu santralda yok/yetersiz")
    if df["t_air"].isna().all() or df["wind_ms"].isna().all():
        raise ValueError("kapasite testi için sıcaklık ve rüzgar ölçümü gerekir")
    spec = _plant_spec(plant)
    kap = float(plant.get("ac_limit_kw") or plant["capacity_kwp"])
    def beklenen(rc):
        # aynı raporlama koşulunda beklenen güç: kalibre sistem katsayısı ve sıcaklık katsayısıyla (anma gücü değil)
        eta = float(getattr(spec, "eta_bos", 0.9) or 0.9); gamma = float(getattr(spec, "effective_gamma", None) or -0.0035)
        tc = rc["T"] + rc["E"] / (25.0 + 6.84 * rc["v"])
        return min(kap, float(plant["capacity_kwp"]) * rc["E"] / 1000.0 * eta * (1 + gamma * (tc - 25.0)))
    rapor, _ = rs.kapasite_testi(df["power_kw"], df["poa_wm2"], df["t_air"].ffill().bfill(), df["wind_ms"].ffill().bfill(),
                                 santral=plant["name"], donem=f"son {gun} gün", beklenen_fn=beklenen)
    rapor.kunye = _kunye()
    return rapor


def fatura(tenant_id, plant: dict, ay: str | None = None) -> rs.Rapor:
    """ay: 'YYYY-MM' (İstanbul); verilmezse son tam ay."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import tarife_service, piyasa_service, dengesizlik_service
    tz = plant.get("tz") or "Europe/Istanbul"
    if ay is None:
        bugun = pd.Timestamp.now(tz=tz); ilk = (bugun.replace(day=1) - pd.Timedelta(days=1)).replace(day=1); ay = ilk.strftime("%Y-%m")
    a0 = pd.Timestamp(ay + "-01", tz=tz); a1 = a0 + pd.offsets.MonthBegin(1)
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text("SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND flag='valid' AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"p": plant["id"], "a": a0, "b": a1}, parse_dates=["ts_utc"], index_col="ts_utc")
    if df.empty:
        raise ValueError(f"{ay} için ölçüm yok")
    t = tarife_service.tarife_getir(plant)
    if not t:
        raise ValueError("tarife tanımlı değil — Santralim › künye › Tarife")
    idx = pd.DatetimeIndex(df.index); idx = idx.tz_localize("UTC") if idx.tz is None else idx
    ptf = piyasa_service.fiyatlar(idx)["ptf"] if t["tip"] == "ptf" else None
    g = tarife_service.gelir_df(pd.Series(df["power_kw"].values, index=idx), t, ptf=ptf)
    deng = None
    try:
        sim = dengesizlik_service.simulasyon(tenant_id, plant, gun=45)
        satir = next((x for x in sim.get("aylar", []) if x["ay"] == ay), None)
        if satir:
            deng = pd.Series([float(satir["pvquant_tl"])])
    except Exception:   # noqa: BLE001
        deng = None
    rapor, _ = rs.fatura(g["uretim_mwh"], g["gelir_tl"].fillna(0.0), deng, santral=plant["name"], donem=ay,
                         ek_kalemler=None)
    rapor.bolumler.append(("Tarife", f"{t['tip']} · ortalama {g['fiyat_tl_mwh'].mean():,.0f} TL/MWh" + (" (PTF: senaryo/EPİAŞ karışık olabilir)" if t["tip"] == "ptf" else "")))
    rapor.kunye = _kunye()
    return rapor


def kullanilabilirlik(tenant_id, plant: dict, gun: int = 30) -> rs.Rapor:
    from pvquant.services import kullanilabilirlik_service
    k = kullanilabilirlik_service.hesapla(tenant_id, plant, gun)
    if k.get("durum") != "ok":
        raise ValueError(f"kullanılabilirlik hesaplanamadı: {k.get('durum')}")
    zaman = {"A_t": k["A_t"], "saat_ariza": k["ariza_saat"], "saat_haric": k["haric_saat"]}
    enerji = {"A_e": k["A_e"], "E_kayip_ariza_kwh": k["kayip_kwh"]}
    rapor = rs.kullanilabilirlik_raporu(zaman, enerji, None, None, santral=plant["name"], donem=f"son {gun} gün")
    rapor.bolumler.append(("Not", k["not"] + f"; veri erişilebilirliği %{k['veri_orani']*100:.0f}"))
    rapor.kunye = _kunye()
    return rapor


def uret(tenant_id, plant: dict, ad: str, **p) -> tuple[bytes, str]:
    if ad not in SABLONLAR:
        raise KeyError(ad)
    r = {"kapasite-testi": kapasite_testi, "fatura": fatura, "kullanilabilirlik": kullanilabilirlik}[ad](tenant_id, plant, **p)
    html = ("<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>" + r.baslik + "</title>"
            "<style>body{font-family:'IBM Plex Sans',system-ui,sans-serif;max-width:860px;margin:32px auto;color:#101D30}"
            "table{border-collapse:collapse;font-size:13px}td,th{padding:6px 10px;border-bottom:1px solid #DDE3EA;text-align:right}"
            "th:first-child,td:first-child{text-align:left}h1{font-size:22px}h2{font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:#45586F}"
            "small{color:#45586F}</style></head><body>" + r.html() + "</body></html>")
    return html.encode("utf-8"), f"{ad}_{plant['name'].replace(' ', '_')}_{date.today().isoformat()}.html"
