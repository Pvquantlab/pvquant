"""10.11.2026 v2.568 (Faz 0 onay paketi 1: TK-05/06/12) — KARNE KURALI, tek yer.

Doğruluk karnesi (skill_daily), rapor hata dağılımı ve Doğruluk sayfası hesapları aynı eşleşmeyi aynı kuralla seçer:

1. Geriye bakışlı koşular karneye girmez: `forecast_runs.model='backtest'` ya da `meteo_source='open-meteo-arsiv'` (analiz
   meteosuyla geçmiş tarihli koşu; scripts/dev_skill_backtest.py). Yayımlandığı anda saklanmamış tahmin sınav sayılmaz.
2. Gün içi revizyon koşuları (`meteo_ozet_json.etiket='gun_ici'`, 09:30 ve 15:30 UTC) ana ufuk kovalarına (0-24 / 24-72 /
   72-168 / 168+) girmez; ayrı «gun_ici» kovasında sayılır (saat başına en son revizyon). Önceden ana kovaya karışıyor ve
   aynı saat birden çok satır sayıldığı için WMAPE iyimserleşiyordu (saf yeniden üretim: %20 → %11).
3. Ana kovalarda her (saat, kova) için EN ERKEN yayımlanan koşu (en uzun ufuk) tutulur: yöntem metni «gün başlamadan
   üretilir, sonradan düzeltme yapılmaz» der; en erken koşu bu cümleyi karşılar.
4. «program» kovası: teslim günü D için D-1 KGÜP kesimi (1.1.2025'ten 15:30, öncesinde 16:00, İstanbul) öncesi son
   koşunun D saatleri — uzlaştırma maliyetini belirleyen program doğruluğu (kgup_service.kaynak_kosu_df ile aynı kural).
5. Gündüz = gerçekleşen > GUNDUZ_ORAN × kurulu güç; tek sabit.

Hepsi SAF; DB yok. Çekirdek tahmin matematiğine dokunmaz; yalnız hangi tahminin sınava girdiğini seçer.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

GUNDUZ_ORAN = 0.02
KOVA_SINIRLARI = [0, 24, 72, 168, 999]
KOVA_ETIKETLERI = ["0-24", "24-72", "72-168", "168+"]
ANA_KOVALAR = tuple(KOVA_ETIKETLERI)
KOVA_GUN_ICI = "gun_ici"
KOVA_PROGRAM = "program"
GERIYE_BAKISLI_MODEL = frozenset({"backtest"})
GERIYE_BAKISLI_METEO = frozenset({"open-meteo-arsiv"})
ETIKET_GUN_ICI = "gun_ici"
PIYASA_TZ = "Europe/Istanbul"
KURAL_SURUMU = "2026-11-10"


def kova_etiketle(ufuk_s: pd.Series) -> pd.Series:
    """Ufuk saatini ana kovaya eşler: (0,24] / (24,72] / (72,168] / (168,999]. Metin döner (yeni kovalar eklenebilsin)."""
    return pd.cut(ufuk_s, KOVA_SINIRLARI, labels=KOVA_ETIKETLERI).astype(object)


def gunduz_maskesi(power_kw: pd.Series, capacity_kwp: float) -> pd.Series:
    return power_kw > GUNDUZ_ORAN * float(capacity_kwp)


def geriye_bakisli(df: pd.DataFrame) -> pd.Series:
    """Karneye girmeyecek koşular (model / meteo_source sütunu yoksa hiçbiri)."""
    m = pd.Series(False, index=df.index)
    if "model" in df:
        m |= df["model"].isin(GERIYE_BAKISLI_MODEL)
    if "meteo_source" in df:
        m |= df["meteo_source"].isin(GERIYE_BAKISLI_METEO)
    return m


def karne_secimi(df: pd.DataFrame) -> pd.DataFrame:
    """Eşleşmiş satırlardan (ts_utc, run_at|ufuk_s, [model, meteo_source, etiket]) karne satırlarını seçer.
    Döner: aynı sütunlar + `ufuk_s`, `kova`; ana kovalarda (ts_utc, kova) başına tek satır (en erken koşu);
    gün içi koşular `kova='gun_ici'` ile saat başına tek satır (en son revizyon). Boş df boş döner."""
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()
    d = df.copy()
    d = d[~geriye_bakisli(d)]
    if "ufuk_s" not in d:
        d["ufuk_s"] = (pd.to_datetime(d["ts_utc"], utc=True) - pd.to_datetime(d["run_at"], utc=True)).dt.total_seconds() / 3600
    d = d[d["ufuk_s"] >= 0]
    if d.empty:
        d["kova"] = pd.Series(dtype=object)
        return d
    gun_ici = d["etiket"].eq(ETIKET_GUN_ICI) if "etiket" in d else pd.Series(False, index=d.index)
    ana = d[~gun_ici].copy()
    ana["kova"] = kova_etiketle(ana["ufuk_s"])
    ana = ana.dropna(subset=["kova"])
    ana = ana.sort_values("ufuk_s", ascending=False).drop_duplicates(["ts_utc", "kova"], keep="first")   # en erken koşu
    rev = d[gun_ici].copy()
    if not rev.empty:
        rev["kova"] = KOVA_GUN_ICI
        rev = rev.sort_values("ufuk_s", ascending=True).drop_duplicates("ts_utc", keep="first")        # en son revizyon
    out = pd.concat([ana, rev], ignore_index=True) if not rev.empty else ana.reset_index(drop=True)
    return out.sort_values(["ts_utc", "kova"]).reset_index(drop=True)


def ana_kovalar(df: pd.DataFrame) -> pd.DataFrame:
    """Yalnız ana ufuk kovaları (gün içi ve program hariç)."""
    if df is None or df.empty or "kova" not in df:
        return df
    return df[df["kova"].isin(ANA_KOVALAR)]


def program_kesimi(gun: date) -> pd.Timestamp:
    """Teslim günü D için D-1 KGÜP kesim anı (İstanbul)."""
    from pvquant.ext.turkiye import kurallar as kr
    (kh, km), _ = kr.kgup_kesim(gun)
    return pd.Timestamp(gun, tz=PIYASA_TZ) - pd.Timedelta(days=1) + pd.Timedelta(hours=kh, minutes=km)


def program_kovasi(df: pd.DataFrame) -> pd.DataFrame:
    """Eşleşmiş satırlardan (ts_utc, run_at, …; geriye bakışlı ve gün içi dâhil olabilir) `kova='program'` satırları:
    her teslim günü (İstanbul) için kesim öncesi SON koşu, o günün saatleri. Gün içi 09:30 UTC koşusu kesimden önce
    bittiği için programa kaynak olabilir (kgup_service ile aynı). Kesim öncesi koşu yoksa o gün satırı yok (sayı uydurulmaz)."""
    if df is None or df.empty or "run_at" not in df:
        return pd.DataFrame(columns=list(df.columns) + ["ufuk_s", "kova"]) if df is not None else pd.DataFrame()
    d = df[~geriye_bakisli(df)].copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d["run_at"] = pd.to_datetime(d["run_at"], utc=True)
    d["_gun"] = d["ts_utc"].dt.tz_convert(PIYASA_TZ).dt.date
    parcalar = []
    for gun, g in d.groupby("_gun"):
        kesim = program_kesimi(gun)
        uygun = g[g["run_at"] <= kesim]
        if uygun.empty:
            continue
        son = uygun["run_at"].max()
        secim = uygun[uygun["run_at"] == son].copy()
        secim["ufuk_s"] = (secim["ts_utc"] - secim["run_at"]).dt.total_seconds() / 3600
        secim["kova"] = KOVA_PROGRAM
        parcalar.append(secim.drop_duplicates("ts_utc"))
    if not parcalar:
        return pd.DataFrame(columns=list(d.drop(columns=["_gun"]).columns) + ["ufuk_s", "kova"])
    return pd.concat(parcalar, ignore_index=True).drop(columns=["_gun"])


def karne_satirlari(df: pd.DataFrame) -> pd.DataFrame:
    """Karnenin tamamı: ana kovalar + gün içi + program (aynı saat farklı kovalarda bir kez)."""
    sec = karne_secimi(df)
    prog = program_kovasi(df)
    if prog is None or prog.empty:
        return sec
    return pd.concat([sec, prog[sec.columns.intersection(prog.columns)]], ignore_index=True)
