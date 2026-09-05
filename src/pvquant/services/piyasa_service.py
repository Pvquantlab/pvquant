"""v2.258 — Dalga 4.14: EPİAŞ Şeffaflık fiyat entegrasyonu (PTF / SMF / sistem yönü).

Kimlik: Settings.epias_kullanici / epias_sifre (env PVQUANT_EPIAS_*). Varsa gece işi son günleri çeker ve
piyasa_fiyat tablosuna yazar (kaynak='epias'). Yoksa hiçbir şey uydurulmaz: simülatör 'senaryo' fiyatıyla
çalışır (EPDK 2025 yıllık ağırlıklı ortalamaları — PTF 2.651,81 / SMF 2.524,09 TL/MWh) ve UI bunu söyler.
İstemci: pvquant.ext.turkiye.epias (TGT önbellekli, CAS limitleri, İstanbul→UTC).
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

SENARYO_PTF = 2651.81   # EPDK 2025 yıllık ağırlıklı ortalama, TL/MWh
SENARYO_SMF = 2524.09
SENARYO_AD = "senaryo (EPDK 2025 ortalaması)"


def kimlik_var() -> bool:
    from pvquant.config import get_settings
    s = get_settings()
    return bool(s.epias_kullanici and s.epias_sifre)


def _istemci():
    from pvquant.config import get_settings
    from pvquant.ext.turkiye.epias import Istemci
    s = get_settings()
    return Istemci(s.epias_kullanici, s.epias_sifre)


def senaryo_fiyat(index: pd.DatetimeIndex) -> pd.DataFrame:
    """SAF. Sabit senaryo fiyatları (kaynak açıkça 'senaryo')."""
    return pd.DataFrame({"ptf": SENARYO_PTF, "smf": SENARYO_SMF, "yon": None, "kaynak": "senaryo"}, index=index)


def fiyat_cek(bas: str, bitis: str, istemci=None) -> pd.DataFrame:
    """EPİAŞ'tan PTF/SMF/yön (UTC saatlik). Kimlik yoksa RuntimeError."""
    c = istemci or _istemci()
    p = c.fiyat_paketi(bas, bitis)
    p = p.rename(columns={"yon": "yon"}); p["kaynak"] = "epias"
    return p.dropna(subset=["ptf"], how="all")


def kaydet(df: pd.DataFrame) -> int:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    if df is None or df.empty:
        return 0
    satirlar = [{"ts": ts.to_pydatetime(), "ptf": (None if pd.isna(r.ptf) else float(r.ptf)),
                 "smf": (None if pd.isna(r.get("smf", float("nan"))) else float(r.smf)),
                 "yon": (None if r.get("yon") is None or (isinstance(r.get("yon"), float) and pd.isna(r.get("yon"))) else str(r.yon)),
                 "k": r.get("kaynak", "epias")} for ts, r in df.iterrows()]
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO piyasa_fiyat(ts_utc, ptf, smf, yon, kaynak, guncelleme) VALUES(:ts,:ptf,:smf,:yon,:k,now()) "
                       "ON CONFLICT (ts_utc) DO UPDATE SET ptf=EXCLUDED.ptf, smf=EXCLUDED.smf, yon=EXCLUDED.yon, kaynak=EXCLUDED.kaynak, guncelleme=now()"), satirlar)
    return len(satirlar)


def gece_piyasa(gun: int = 3) -> dict:
    """Worker: son `gun` günün fiyatlarını çek/yaz. Kimlik yoksa atlar (hata değil)."""
    if not kimlik_var():
        return {"durum": "kimlik_yok", "yazilan": 0}
    bitis = date.today(); bas = bitis - timedelta(days=gun)
    n = kaydet(fiyat_cek(bas.isoformat(), bitis.isoformat()))
    return {"durum": "ok", "yazilan": n}


def fiyatlar(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Verilen saatler için fiyat: tabloda varsa EPİAŞ, eksik saatler senaryo (kaynak kolonu söyler)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    if len(index) == 0:
        return senaryo_fiyat(index)
    with sistem_baglami() as s:
        df = pd.read_sql(text("SELECT ts_utc, ptf, smf, yon, kaynak FROM piyasa_fiyat WHERE ts_utc >= :a AND ts_utc <= :b"),
                         s.connection(), params={"a": index.min().to_pydatetime(), "b": index.max().to_pydatetime()}, parse_dates=["ts_utc"])
    out = senaryo_fiyat(index)
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True); df = df.set_index("ts_utc")
        ortak = out.index.intersection(df.index)
        for k in ("ptf", "smf", "yon", "kaynak"):
            out.loc[ortak, k] = df.loc[ortak, k]
    return out


def durum() -> dict:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT max(ts_utc), count(*) FROM piyasa_fiyat WHERE kaynak='epias'")).first()
    return {"kimlik": kimlik_var(), "son_fiyat": r[0].isoformat() if r and r[0] else None, "saat": int(r[1] or 0) if r else 0,
            "senaryo": {"ptf": SENARYO_PTF, "smf": SENARYO_SMF, "ad": SENARYO_AD}}
