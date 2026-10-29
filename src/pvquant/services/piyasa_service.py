"""v2.258 — Dalga 4.14: EPİAŞ Şeffaflık fiyat entegrasyonu (PTF / SMF / sistem yönü).

Kimlik: Settings.epias_kullanici / epias_sifre (env PVQUANT_EPIAS_*). Varsa gece işi son günleri çeker ve
piyasa_fiyat tablosuna yazar (kaynak='epias', yon='acik'|'fazla'|'dengede'). Yoksa hiçbir şey uydurulmaz: simülatör
'senaryo' fiyatıyla çalışır (EPDK 2025 yıllık ağırlıklı ortalamaları — PTF 2.651,81 / SMF 2.524,09 TL/MWh; sistem yönü YOK)
ve UI her TL alanında bunu söyler (senaryo rozeti). Geçmişi toplu doldurma: geri_doldur() (F-04; zamanlayıcıya bağlanmadı).
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
        # 29.10 (v2.505): eksik alan mevcut değeri SİLMEZ — gün öncesi PTF (smf/yön henüz yok) ya da yön ucu boş dönen parça, dolu satırı boşaltmasın
        s.execute(text("INSERT INTO piyasa_fiyat(ts_utc, ptf, smf, yon, kaynak, guncelleme) VALUES(:ts,:ptf,:smf,:yon,:k,now()) "
                       "ON CONFLICT (ts_utc) DO UPDATE SET ptf=COALESCE(EXCLUDED.ptf, piyasa_fiyat.ptf), smf=COALESCE(EXCLUDED.smf, piyasa_fiyat.smf), "
                       "yon=COALESCE(EXCLUDED.yon, piyasa_fiyat.yon), kaynak=EXCLUDED.kaynak, guncelleme=now()"), satirlar)
    return len(satirlar)


def gece_piyasa(gun: int = 3) -> dict:
    """Worker: son `gun` günün fiyatlarını çek/yaz. Kimlik yoksa atlar (hata değil).

    v2.378 (bulgu 29, ilk gerçek koşu): bitiş DÜNDÜR. EPİAŞ, günün MCP'sini
    öğleden önce sorgulatmıyor (SEF1124: "...saat 14 öncesinde mevcut değil")
    — bitis=bugün olunca gece 02:00 koşusu 400 yiyip hiç fiyat yazamıyordu.
    Dengesizlik/karne geçmişe bakar; dünün sonu yeterli ve her saatte geçerli."""
    if not kimlik_var():
        return {"durum": "kimlik_yok", "yazilan": 0}
    bitis = date.today() - timedelta(days=1); bas = bitis - timedelta(days=gun)
    n = kaydet(fiyat_cek(bas.isoformat(), bitis.isoformat()))
    return {"durum": "ok", "yazilan": n}


def geri_doldur(bas: str, bitis: str, parca_gun: int = 7, istemci=None, bugun: date | None = None) -> dict:
    """F-04: geçmiş fiyat/yön doldurma (gün gün, parça parça). Kimlik yoksa atlar. Zamanlayıcıya bağlı değil; elle/CLI.
    29.10 (v2.505, canlı ders): bitiş en çok DÜN — bugünün saatleri SMF/yön ucunda henüz yok, 400 dönüyor ve koşu son parçada
    düşüyordu. Parça hatası koşuyu durdurmaz: hatalı parçalar `hatali` listesinde döner (durum 'kismi'), diğerleri yazılır."""
    if istemci is None and not kimlik_var():
        return {"durum": "kimlik_yok", "yazilan": 0}
    dun = (bugun or date.today()) - timedelta(days=1)
    b = date.fromisoformat(bas); e = min(date.fromisoformat(bitis), dun); yazilan = 0; parcalar = 0; hatali: list[dict] = []
    while b <= e:
        p_bitis = min(b + timedelta(days=parca_gun - 1), e)
        try:
            yazilan += kaydet(fiyat_cek(b.isoformat(), p_bitis.isoformat(), istemci))
        except Exception as x:   # noqa: BLE001 — bir parça (EPİAŞ 400/zaman aşımı) tüm doldurmayı düşürmesin
            hatali.append({"bas": b.isoformat(), "bitis": p_bitis.isoformat(), "hata": f"{type(x).__name__}: {str(x)[:160]}"})
        parcalar += 1
        b = p_bitis + timedelta(days=1)
    return {"durum": "kismi" if hatali else "ok", "yazilan": yazilan, "parca": parcalar, "hatali": hatali, "bitis": e.isoformat()}


def gun_oncesi_ptf(istemci=None, bugun: date | None = None) -> dict:
    """29.10 (v2.505): gün öncesi piyasası sonuçlandıktan sonra (TSİ ~14:00) BUGÜN ve YARIN için yalnız PTF çekilir; SMF/yön bu saatler
    için henüz yoktur, satır kaynak='epias_gop' ile yazılır (uzlaştırma/yön sayımlarına 'epias' olarak girmez). Gece işi aynı saatleri
    tam satırla (PTF/SMF/yön, kaynak='epias') üzerine yazar. Yarın henüz yayımlanmamışsa 'henuz_yok' döner, hata değildir."""
    if istemci is None and not kimlik_var():
        return {"durum": "kimlik_yok", "yazilan": 0}
    c = istemci or _istemci()
    g = bugun or date.today(); yarin = g + timedelta(days=1)
    try:
        ptf = c.ptf(g.isoformat(), yarin.isoformat())
    except Exception as x:   # noqa: BLE001 — EPİAŞ 400 (henüz yayımlanmadı) ya da ağ
        return {"durum": "henuz_yok", "yazilan": 0, "hata": f"{type(x).__name__}: {str(x)[:160]}"}
    if ptf is None or len(ptf) == 0:
        return {"durum": "henuz_yok", "yazilan": 0}
    df = pd.DataFrame({"ptf": ptf.astype(float)}); df["smf"] = float("nan"); df["yon"] = None; df["kaynak"] = "epias_gop"
    yarin_saat = int((df.index.tz_convert("Europe/Istanbul").date == yarin).sum())
    return {"durum": "ok", "yazilan": kaydet(df), "yarin_saat": yarin_saat}


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
        r = s.execute(text("SELECT max(ts_utc), count(*), count(yon) FROM piyasa_fiyat WHERE kaynak='epias'")).first()
    return {"kimlik": kimlik_var(), "son_fiyat": r[0].isoformat() if r and r[0] else None, "saat": int(r[1] or 0) if r else 0,
            "yon_saat": int(r[2] or 0) if r else 0,
            "senaryo": {"ptf": SENARYO_PTF, "smf": SENARYO_SMF, "ad": SENARYO_AD}}
