"""v2.260 — Dalga 4.13: KGÜP bildirim dosyası (saatlik program) — teslim edilebilir koşudan.

Program günü D için kaynak koşu: D-1 15:30 (İstanbul) öncesinde verilmiş son koşu (dengesizlik simülatörüyle aynı
kural); bugün için henüz 15:30 geçmediyse en son koşu. Kantil seçimi p50 (varsayılan) | p10 | p90 (temkinli/iddialı).
Dosya: pvquant.ext.turkiye.kgup (KGÜP ≤ EAK ≤ kurulu güç, ≥200 MWh sıçramada 15 dk dilimleme, TPYS CSV — kolonlar
parametrik; resmi şablon teyit edilemedi). Tire ilkesi: koşu yoksa 409, 24 saatin tamamı yoksa eksik saatler 0 + uyarı.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

from pvquant.ext.turkiye import kgup as kg

IST = "Europe/Istanbul"


def kaynak_kosu_df(tenant_id, plant_id, gun: date, kantil: str = "p50") -> tuple[pd.DataFrame, dict | None]:
    """DB: D-1 15:30 IST öncesi son koşunun D günü saatleri (UTC). Döner (df[ts_utc, kw], koşu bilgisi)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    kol = {"p50": "p50_kw", "p10": "p10_kw", "p90": "p90_kw"}[kantil]
    d0 = pd.Timestamp(gun, tz=IST); d1 = d0 + pd.Timedelta(days=1)
    kesim = d0 - pd.Timedelta(hours=8, minutes=30)   # D-1 15:30 IST
    simdi = pd.Timestamp.now(tz=IST)
    if kesim > simdi:
        kesim = simdi
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT id, run_at, mode FROM forecast_runs WHERE plant_id=:p AND run_at <= :k "
                           "AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=forecast_runs.id AND v.ts_utc >= :a AND v.ts_utc < :b) "
                           "ORDER BY run_at DESC LIMIT 1"),
                      {"p": plant_id, "k": kesim.to_pydatetime(), "a": d0.tz_convert("UTC").to_pydatetime(), "b": d1.tz_convert("UTC").to_pydatetime()}).first()
        if r is None:
            return pd.DataFrame(columns=["ts_utc", "kw"]), None
        df = pd.read_sql(text(f"SELECT ts_utc, {kol} AS kw FROM forecast_values WHERE run_id=:r AND plant_id=:p AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"r": r.id, "p": plant_id, "a": d0.tz_convert("UTC").to_pydatetime(), "b": d1.tz_convert("UTC").to_pydatetime()}, parse_dates=["ts_utc"])
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df, {"run_id": str(r.id), "run_at": r.run_at.isoformat(), "mode": r.mode, "kesim": kesim.isoformat()}


def uret(tenant_id, plant: dict, gun: date, kantil: str = "p50", uevcb: str | None = None) -> dict:
    """Program tablosu + doğrulama + TPYS CSV metni. Koşu yoksa {'hata': ...}."""
    df, kosu = kaynak_kosu_df(tenant_id, plant["id"], gun, kantil)
    if kosu is None:
        return {"hata": "bu gün için teslim penceresi öncesinde verilmiş koşu yok", "gun": gun.isoformat()}
    seri = pd.Series(df["kw"].values, index=pd.DatetimeIndex(df["ts_utc"])) / 1000.0   # kW → MW
    kap = float(plant["capacity_kwp"]) / 1000.0
    eak = (float(plant["ac_limit_kw"]) / 1000.0) if plant.get("ac_limit_kw") else kap
    son = kg.program_uret(seri, gun.isoformat(), uevcb or plant.get("uevcb") or str(plant["id"])[:8].upper(), kap, eak_mw=eak, kantil=None)
    hatalar = kg.dogrula(son, kap)
    tablo = kg.ceyrek_dilimle(son) if son.sicrama_saatleri else son.tablo
    buf = io.StringIO()
    sab = kg.Sablon()
    csv_df = pd.DataFrame({sab.tarih: pd.to_datetime(tablo["tarih"]).dt.strftime(sab.tarih_bicim), sab.saat: tablo["saat"].astype(int),
                           sab.uevcb: tablo["uevcb"], sab.kgup: tablo["kgup_mwh"], sab.eak: tablo["eak_mwh"]})
    if "ceyrek" in tablo and tablo["ceyrek"].notna().any():
        csv_df[sab.ceyrek] = tablo["ceyrek"].astype("Int64")
    csv_df.to_csv(buf, sep=sab.ayrac, decimal=sab.ondalik, index=False)
    return {"gun": gun.isoformat(), "kantil": kantil, "kosu": kosu, "uyarilar": son.uyarilar + hatalar, "sicrama_saatleri": son.sicrama_saatleri,
            "toplam_mwh": round(float(son.tablo["kgup_mwh"].sum()), 3),
            "satirlar": [{"saat": int(r.saat), "kgup_mwh": float(r.kgup_mwh), "eak_mwh": float(r.eak_mwh)} for r in son.tablo.itertuples()],
            "csv": buf.getvalue(), "dosya_adi": f"KGUP_{(uevcb or 'UEVCB')}_{gun.isoformat()}_{kantil}.csv",
            "teslim": kg.teslim_durumu()}
