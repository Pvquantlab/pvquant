"""F-10 (v2.507, 30.10.2026) — gün içi revize program önerisi.

Bugünün bildirilmiş programı (öncelik: müşterinin yüklediği «bildirilen» dosya → indirilen son PVQuant önerisi → 15:30 kesimi öncesi
tahminin P50'si) ile GÜNCEL beklenti (önümüzdeki 6 saat için ölçüm persistansıyla düzeltilmiş tahmin, ötesi son koşunun P50'si)
saat saat kıyaslanır. DUY m.69(1): KGÜP, teslimat saatinin GİP kapı kapanışı (teslimat − 1 s) + 30 dk'ya kadar revize edilebilir;
dolayısıyla her saatin revizyon son anı = teslimat − 30 dk. Sapması eşiği (varsayılan programın %10'u, taban kurulu gücün %2'si ×
1 saat) aşan ve revizyon süresi geçmemiş saatler «öneri» olarak işaretlenir. Bu bir yol göstericidir; kayıt yazmaz, TPYS'de
revizyon müşterinin kendi işlemidir. Hesap ve veri kaynakları yanıtta açıkça söylenir.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

IST = "Europe/Istanbul"
ESIK_ORAN_VARSAYILAN = 0.10     # programın %10'u
TABAN_ORAN_KURULU = 0.02        # kurulu gücün %2'si (MW × 1 s = MWh) — küçük programlarda gürültüyü eler


def oner_df(program_mwh: pd.Series, beklenen_mwh: pd.Series, simdi: pd.Timestamp, *, esik_oran: float = ESIK_ORAN_VARSAYILAN,
            kurulu_guc_mw: float | None = None) -> dict:
    """SAF. program_mwh / beklenen_mwh: saat başı index (tz'li), MWh. simdi: tz'li. Dönüş: saat satırları + özet."""
    from pvquant.ext.turkiye import kgup as kg
    t = pd.Timestamp(simdi); t = t.tz_convert(IST) if t.tz is not None else t.tz_localize(IST)
    p = program_mwh.copy(); p.index = p.index.tz_convert(IST) if p.index.tz is not None else p.index.tz_localize("UTC").tz_convert(IST)
    b = beklenen_mwh.copy(); b.index = b.index.tz_convert(IST) if b.index.tz is not None else b.index.tz_localize("UTC").tz_convert(IST)
    gun_sonu = t.normalize() + pd.Timedelta(days=1)
    idx = p.index[(p.index > t - pd.Timedelta(hours=1)) & (p.index < gun_sonu)]   # içinde bulunulan saat dâhil, gün sonuna kadar
    taban = (TABAN_ORAN_KURULU * kurulu_guc_mw) if kurulu_guc_mw else 0.0
    satirlar = []
    for ts in idx:
        prog = float(p.loc[ts]); bek = b.get(ts, np.nan); bek = None if (bek is None or pd.isna(bek)) else float(bek)
        pen = kg.gun_ici_revizyon_penceresi(ts)
        son = pen["kgup_revizyon_son"]; mumkun = bool(son > t)
        fark = (bek - prog) if bek is not None else None
        esik = max(esik_oran * abs(prog), taban)
        oneri = bool(mumkun and fark is not None and abs(fark) > esik and esik > 0)
        satirlar.append({"saat": int(ts.hour), "ts": ts.isoformat(), "program_mwh": round(prog, 3), "beklenen_mwh": (round(bek, 3) if bek is not None else None),
                         "fark_mwh": (round(fark, 3) if fark is not None else None), "fark_oran": (round(fark / prog, 3) if (fark is not None and prog > 0) else None),
                         "esik_mwh": round(esik, 3), "revizyon_son": son.isoformat(), "revize_mumkun": mumkun, "oneri": oneri})
    oneriler = [s for s in satirlar if s["oneri"]]
    return {"saatler": satirlar, "oneri_saatleri": [s["saat"] for s in oneriler],
            "toplam_fark_mwh": round(float(sum(s["fark_mwh"] for s in satirlar if s["fark_mwh"] is not None)), 3),
            "ilk_revizyon_son": (min(s["revizyon_son"] for s in oneriler) if oneriler else None),
            "esik_oran": esik_oran, "taban_mwh": round(taban, 3), "simdi": t.isoformat()}


def _program_bugun(tenant_id, plant: dict, gun: date) -> tuple[pd.Series | None, str | None]:
    """Bugünün programı ve kaynağı: bildirilen dosya → indirilen öneri → 15:30 öncesi tahmin (P50)."""
    from pvquant.ext.turkiye.kgup import Sablon
    from pvquant.services import kgup_arsiv_service, kgup_service
    pid = str(plant["id"]); pj = plant.get("params_json") or {}
    try:
        kayitlar = kgup_arsiv_service.listele(tenant_id, pid, gun=gun, n=20)
    except Exception:   # noqa: BLE001 — arşiv yoksa tahmine düş
        kayitlar = []
    for kaynak, etiket in (("musteri", "bildirilen dosya"), ("pvquant", "indirilen öneri")):
        k = next((r for r in kayitlar if r["kaynak"] == kaynak), None)   # listele yeni→eski; ilk eşleşen en son sürüm
        if k:
            try:
                d = kgup_arsiv_service.getir(tenant_id, pid, k["id"])
                df = kgup_arsiv_service.csv_oku(d["dosya"], Sablon.params_json_dan(pj if isinstance(pj, dict) else {}))
                idx = pd.date_range(pd.Timestamp(gun, tz=IST), periods=24, freq="h")
                s = pd.Series(df.set_index("saat")["kgup_mwh"].reindex(range(24)).values, index=idx, dtype=float)
                return s, f"{etiket} (sürüm {k['surum']})"
            except Exception:   # noqa: BLE001
                continue
    try:
        df, kosu = kgup_service.kaynak_kosu_df(tenant_id, pid, gun)
    except Exception:   # noqa: BLE001
        return None, None
    if df is None or df.empty or kosu is None:
        return None, None
    s = pd.Series(df["kw"].astype(float).values / 1000.0, index=pd.DatetimeIndex(df["ts_utc"]).tz_convert(IST) if pd.DatetimeIndex(df["ts_utc"]).tz is not None else pd.DatetimeIndex(df["ts_utc"]).tz_localize("UTC").tz_convert(IST))
    return s, "15:30 öncesi tahmin (P50)"


def _beklenen(tenant_id, plant: dict, simdi: pd.Timestamp) -> tuple[pd.Series | None, str]:
    """Güncel beklenti: nowcast ufku (varsa) + son koşu P50 (MWh)."""
    from pvquant.services import forecast_service, nowcast_service
    pid = str(plant["id"])
    df = forecast_service.son_kosu(tenant_id, pid)
    if df is None or df.empty:
        return None, "tahmin yok"
    idx = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    s = pd.Series(df["p50_kw"].astype(float).values / 1000.0, index=idx)
    kaynak = "son koşu P50"
    try:
        nc = nowcast_service.hesapla(tenant_id, plant, simdi)
        if nc.get("durum") == "ok" and nc.get("ufuk"):
            for u in nc["ufuk"]:
                ts = pd.Timestamp(u["ts"]).tz_convert("UTC")
                s.loc[ts] = float(u["nowcast_kw"]) / 1000.0
            s = s.sort_index(); kaynak = f"ilk {len(nc['ufuk'])} saat ölçümle düzeltilmiş, ötesi son koşu P50"
    except Exception:   # noqa: BLE001 — nowcast süsleme
        pass
    return s, kaynak


def oner(tenant_id, plant: dict, simdi: pd.Timestamp | None = None) -> dict:
    """DB: bugün için öneri. Dönüş oner_df + {durum, program_kaynagi, beklenen_kaynagi, gun, not}."""
    t = pd.Timestamp(simdi or pd.Timestamp.now(tz="UTC")); t = t.tz_convert(IST) if t.tz is not None else t.tz_localize("UTC").tz_convert(IST)
    gun = t.date()
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        import json as _j; pj = _j.loads(pj)
    esik = float(((pj.get("alarm_esik") or {}).get("revizyon_esik")) or ESIK_ORAN_VARSAYILAN)
    ortak = {"gun": gun.isoformat(), "simdi": t.isoformat(), "esik_oran": esik,
             "not": "Yol göstericidir, kayıt yazmaz: her saatin revizyon son anı GİP kapı kapanışı + 30 dakikadır (teslimat − 30 dk, DUY m.69(1)); revizyon TPYS'de yapılır."}
    if t.hour >= 23:
        return {**ortak, "durum": "gun_bitti", "program_kaynagi": None, "beklenen_kaynagi": None, "saatler": [], "oneri_saatleri": []}
    prog, kaynak = _program_bugun(tenant_id, plant, gun)
    if prog is None:
        return {**ortak, "durum": "program_yok", "program_kaynagi": None, "beklenen_kaynagi": None, "saatler": [], "oneri_saatleri": []}
    bek, bkaynak = _beklenen(tenant_id, plant, t)
    if bek is None:
        return {**ortak, "durum": "tahmin_yok", "program_kaynagi": kaynak, "beklenen_kaynagi": None, "saatler": [], "oneri_saatleri": []}
    r = oner_df(prog, bek, t, esik_oran=esik, kurulu_guc_mw=(float(plant.get("capacity_kwp") or 0) / 1000.0) or None)
    return {**ortak, **r, "durum": "ok", "program_kaynagi": kaynak, "beklenen_kaynagi": bkaynak}
