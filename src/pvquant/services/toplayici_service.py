"""v2.275 — Dalga 4 tamamlayıcısı: toplayıcı / DSG çıktı biçimi (smartPulse, Volue vb.) ve 15 dakikalık hazırlık.

Toplayıcılar üye santralden saatlik (2027'den itibaren 15 dk) MW program ve bant ister. Resmî smartPulse/Volue şablonları
kamuya açık değil (teyit edilemedi); bu çıktı genel bir şablondur: Tarih;Saat;[Ceyrek];UEVCB;P10_MW;P50_MW;P90_MW;EAK_MW.
Kolon adları params_json.toplayici_sablon ile eşlenebilir (ör. {"P50_MW": "Forecast"}). 15 dk: saatlik seri açık gök
profiliyle enerji korunarak bölünür (pvquant.ext.tahmin.alt_saatlik) — 15 dk uzlaştırma (1.1.2027) için hazırlık.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

IST = "Europe/Istanbul"
KOLONLAR = ["Tarih", "Saat", "Ceyrek", "UEVCB", "P10_MW", "P50_MW", "P90_MW", "EAK_MW"]


def tablo_uret(df: pd.DataFrame, gun: date, uevcb: str, eak_mw: float, lat: float, lon: float, adim: int = 60) -> pd.DataFrame:
    """SAF. df: ts_utc index (UTC), p50_kw/p10_kw/p90_kw. Piyasa günü İstanbul 00–24; adim 60 → 24 satır, 15 → 96 satır."""
    from pvquant.ext.tahmin.alt_saatlik import saatlikten_15dk
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    d0 = pd.Timestamp(gun).tz_localize(IST); d1 = d0 + pd.Timedelta(days=1)
    x = df.copy(); x.index = idx
    x = x[(x.index >= d0) & (x.index < d1)]
    if len(x) < 20:
        raise ValueError("bu gün için saatlik seri eksik")
    def mw(kol):
        s = x[kol].astype(float) / 1000.0 if kol in x and x[kol].notna().any() else None
        return s
    p50, p10, p90 = mw("p50_kw"), mw("p10_kw"), mw("p90_kw")
    if adim == 15:
        def bol(s):
            """Açık gök profiliyle böl; açık gökün ~0 olduğu ama tahminin >0 olduğu saatlerde (gün doğumu kenarı) düz böl — enerji kaybolmasın."""
            q = saatlikten_15dk(s, lat, lon)
            saat_ort = q.resample("h").mean().reindex(s.index).fillna(0.0)
            eksik = s.index[(s > 0) & (saat_ort <= 0)]
            for t in eksik:
                q.loc[(q.index >= t) & (q.index < t + pd.Timedelta(hours=1))] = float(s[t])
            return q
        p50 = bol(p50)
        p10 = bol(p10) if p10 is not None else None
        p90 = bol(p90) if p90 is not None else None
        p50 = p50[(p50.index >= d0) & (p50.index < d1)]
    yerel = p50.index.tz_convert(IST)
    out = pd.DataFrame({"Tarih": yerel.strftime("%d.%m.%Y"), "Saat": yerel.hour, "Ceyrek": yerel.minute, "UEVCB": uevcb,
                        "P10_MW": (p10.reindex(p50.index).clip(upper=eak_mw).round(3).values if p10 is not None else None),
                        "P50_MW": p50.clip(upper=eak_mw).round(3).values,
                        "P90_MW": (p90.reindex(p50.index).clip(upper=eak_mw).round(3).values if p90 is not None else None),
                        "EAK_MW": round(float(eak_mw), 3)})
    if adim == 60:
        out = out.drop(columns=["Ceyrek"])
    return out.reset_index(drop=True)


def eslesme_uygula(tablo: pd.DataFrame, sablon: dict | None) -> pd.DataFrame:
    if not sablon:
        return tablo
    return tablo.rename(columns={k: str(v) for k, v in sablon.items() if k in tablo.columns and v})


def dosya(tablo: pd.DataFrame, fmt: str) -> tuple[bytes, str, str]:
    """(içerik, MIME, uzantı). csv: ';' ayraç ve ',' ondalık (TR); xlsx: openpyxl; json: kayıt listesi."""
    if fmt == "xlsx":
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine="openpyxl") as w:
            tablo.to_excel(w, index=False, sheet_name="Program")
        return b.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    if fmt == "json":
        return tablo.to_json(orient="records", force_ascii=False).encode("utf-8"), "application/json", "json"
    buf = io.StringIO(); tablo.to_csv(buf, sep=";", decimal=",", index=False)
    return buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "csv"


def uret(tenant_id, plant: dict, gun: date, fmt: str = "csv", adim: int = 60) -> dict:
    """Teslim kesimi öncesi koşu (KGÜP kuralıyla aynı kaynak); yoksa {'hata':…}."""
    from pvquant.services import kgup_service
    from pvquant.services.kgup_service import eak_etkin
    df, kosu = kgup_service.kaynak_kosu_df(tenant_id, plant["id"], gun, "p50", tum_kantiller=True)
    if kosu is None:
        return {"hata": "bu gün için teslim penceresi öncesinde verilmiş koşu yok", "gun": gun.isoformat()}
    pj = plant.get("params_json") or {}
    eak = eak_etkin(plant, gun)
    tablo = tablo_uret(df.set_index("ts_utc"), gun, pj.get("uevcb") or str(plant["id"])[:8].upper(), eak["eak_mw"], float(plant["lat"]), float(plant["lon"]), adim)
    tablo = eslesme_uygula(tablo, pj.get("toplayici_sablon"))
    icerik, mime, uz = dosya(tablo, fmt)
    return {"gun": gun.isoformat(), "adim": adim, "satir": int(len(tablo)), "kosu": kosu, "eak": eak, "icerik": icerik, "mime": mime,
            "dosya_adi": f"TOPLAYICI_{pj.get('uevcb') or 'UEVCB'}_{gun.isoformat()}_{adim}dk.{uz}",
            "not": "smartPulse/Volue resmî şablonu teyit edilemedi; kolon adları params_json.toplayici_sablon ile eşlenir"}
