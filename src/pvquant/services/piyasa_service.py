"""v2.258 — Dalga 4.14: EPİAŞ Şeffaflık fiyat entegrasyonu (PTF / SMF / sistem yönü).

Kimlik: Settings.epias_kullanici / epias_sifre (env PVQUANT_EPIAS_*). Varsa gece işi son günleri çeker ve
piyasa_fiyat tablosuna yazar (kaynak='epias', yon='acik'|'fazla'|'dengede'). Yoksa hiçbir şey uydurulmaz: simülatör
'senaryo' fiyatıyla çalışır (EPDK Aralık 2025 Sektör Raporu 2025 yıllık ortalamaları — PTF 2.651,81 ağırlıklı / SMF 2.524,09 aritmetik TL/MWh; sistem yönü YOK, V/B dalı çalışmaz, k = l = 0,03)
ve UI her TL alanında bunu söyler (senaryo rozeti). Geçmişi toplu doldurma: geri_doldur() (F-04; zamanlayıcıya bağlanmadı).
İstemci: pvquant.ext.turkiye.epias (TGT önbellekli, CAS limitleri, İstanbul→UTC).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from pvquant.zaman import PIYASA_TZ

# v2.535 dayanak künyeleri [DUY, KARAR_14968] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    "Karar 14968: EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711"
)

from pvquant.ext.turkiye import (
    kural_sicili as _ks,  # v2.600 (F4-F): senaryo fiyatı kural sicilinden
)

_SENARYO = _ks.guncel("piyasa.senaryo").deger   # en son yürürlük (ekleme sırası değil)
SENARYO_PTF = float(_SENARYO["ptf"])   # EPDK 2025 yıllık ağırlıklı ortalama PTF (Aralık 2025 Sektör Raporu), TL/MWh
SENARYO_SMF = float(_SENARYO["smf"])   # 2025 yıllık ARİTMETİK ortalama SMF (Aralık 2025 Sektör Raporu)
SENARYO_AD = str(_SENARYO["ad"])


def piyasa_gunu(simdi=None) -> date:
    """v2.604 (F4-J): EPİAŞ tarih aralıkları PİYASA gününe göre (Europe/Istanbul) — sunucu UTC takvimine göre değil. 21:00 UTC sonrası UTC «bugün»
    hâlâ dünkü piyasa günüdür; gece işi (03:15 TSİ) UTC'de henüz bir önceki gündeyken «dün» bir gün geri kayardı. Tek tanım `pvquant.zaman.piyasa_gunu`."""
    from pvquant.zaman import piyasa_gunu as _pg
    return _pg(simdi if simdi is not None else pd.Timestamp.now(tz="UTC"))


def kimlik_var() -> bool:
    from pvquant.config import get_settings
    s = get_settings()
    return bool(s.epias_kullanici and s.epias_sifre)


# v2.513 (04 #14 kalan): UEVÇB kodunu EPİAŞ Şeffaflık'tan kuruluş adıyla bulma — organization-list (692 kuruluş, 6 saat önbellek) içinde
# ad araması, eşleşen her kuruluş için uevcb-list {organizationId, startDate} (31.10 canlı sınama: 200). Yalnız okuma; sonuç panelde seçilir.
_ORG_ONBELLEK: dict = {"zaman": None, "liste": []}
ORG_ONBELLEK_SAAT = 6


def _sade(s) -> str:
    return str(s or "").strip().lower().translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))


def kuruluslar(simdi: pd.Timestamp | None = None) -> list[dict]:
    """EPİAŞ kuruluş listesi (organizationId, organizationName); 6 saat bellek önbelleği."""
    simdi = simdi or pd.Timestamp.now(tz="UTC")
    z = _ORG_ONBELLEK["zaman"]
    if z is not None and (simdi - z) < pd.Timedelta(hours=ORG_ONBELLEK_SAAT) and _ORG_ONBELLEK["liste"]:
        return _ORG_ONBELLEK["liste"]
    g = simdi.tz_convert(PIYASA_TZ).strftime("%Y-%m-%d")
    liste = _istemci().organizasyon_listesi(g, g) or []
    _ORG_ONBELLEK.update({"zaman": simdi, "liste": liste})
    return liste


def uevcb_ara(metin: str, en_cok: int = 5) -> dict:
    """Kuruluş adında `metin` geçen en çok `en_cok` kuruluş ve her birinin UEVÇB'leri. Kimlik yoksa durum 'kimlik_yok'."""
    if not kimlik_var():
        return {"durum": "kimlik_yok", "kuruluslar": [], "toplam_kurulus": 0}
    m = _sade(metin)
    liste = kuruluslar()
    esl = [o for o in liste if m and m in _sade(o.get("organizationName") or o.get("name"))][:en_cok]
    g = pd.Timestamp.now(tz=PIYASA_TZ).strftime("%Y-%m-%d")
    c = _istemci(); out = []
    for o in esl:
        oid = o.get("organizationId") or o.get("id"); ad = o.get("organizationName") or o.get("name")
        try:
            uev = c.uevcb_listesi(int(oid), g) or []; hata = None
        except Exception as e:   # noqa: BLE001 — bir kuruluşun UEVÇB listesi düşerse ötekiler gelir
            uev, hata = [], str(e)[:120]
        out.append({"kurulus": ad, "kurulus_id": oid, "hata": hata,
                    "uevcbler": [{"id": u.get("id"), "eic": u.get("eic"), "name": u.get("name")} for u in uev]})
    return {"durum": "ok", "kuruluslar": out, "toplam_kurulus": len(liste)}


def _istemci():
    from pvquant.config import get_settings
    from pvquant.ext.turkiye.epias import Istemci
    s = get_settings()
    return Istemci(s.epias_kullanici, s.epias_sifre, onbellek_dizin=(s.epias_onbellek_dizin or None))   # v2.604 (F4-J): gün önbelleği üretimde açık (var/epias)


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
        # v2.601 (F4-G, bulgu M6): yazımdan sonra güncel satır son sürümden FARKLIYSA tarihçeye yeni sürüm eklenir (yalnız ekleme; aynı değer tekrar yazılmaz)
        s.execute(text(SURUM_EKLE_SQL), {"ts": [r["ts"] for r in satirlar]})
    return len(satirlar)


SURUM_EKLE_SQL = (
    "INSERT INTO piyasa_fiyat_surum(ts_utc, ptf, smf, yon, kaynak, alinma) "
    "SELECT f.ts_utc, f.ptf, f.smf, f.yon, f.kaynak, now() FROM piyasa_fiyat f "
    "LEFT JOIN LATERAL (SELECT v.ptf, v.smf, v.yon, v.kaynak FROM piyasa_fiyat_surum v WHERE v.ts_utc = f.ts_utc ORDER BY v.alinma DESC, v.id DESC LIMIT 1) son ON TRUE "
    "WHERE f.ts_utc = ANY(:ts) AND (son.kaynak IS NULL OR son.ptf IS DISTINCT FROM f.ptf OR son.smf IS DISTINCT FROM f.smf "
    "      OR son.yon IS DISTINCT FROM f.yon OR son.kaynak IS DISTINCT FROM f.kaynak)")


def gece_piyasa(gun: int = 3) -> dict:
    """Worker: son `gun` günün fiyatlarını çek/yaz. Kimlik yoksa atlar (hata değil).

    v2.378 (bulgu 29, ilk gerçek koşu): bitiş DÜNDÜR. EPİAŞ, günün MCP'sini
    öğleden önce sorgulatmıyor (SEF1124: "...saat 14 öncesinde mevcut değil")
    — bitis=bugün olunca gece 02:00 koşusu 400 yiyip hiç fiyat yazamıyordu.
    Dengesizlik/karne geçmişe bakar; dünün sonu yeterli ve her saatte geçerli."""
    if not kimlik_var():
        return {"durum": "kimlik_yok", "yazilan": 0}
    bitis = piyasa_gunu() - timedelta(days=1); bas = bitis - timedelta(days=gun)   # v2.604: piyasa günü (İstanbul)
    n = kaydet(fiyat_cek(bas.isoformat(), bitis.isoformat()))
    return {"durum": "ok", "yazilan": n}


def geri_doldur(bas: str, bitis: str, parca_gun: int = 7, istemci=None, bugun: date | None = None) -> dict:
    """F-04: geçmiş fiyat/yön doldurma (gün gün, parça parça). Kimlik yoksa atlar. Zamanlayıcıya bağlı değil; elle/CLI.
    29.10 (v2.505, canlı ders): bitiş en çok DÜN — bugünün saatleri SMF/yön ucunda henüz yok, 400 dönüyor ve koşu son parçada
    düşüyordu. Parça hatası koşuyu durdurmaz: hatalı parçalar `hatali` listesinde döner (durum 'kismi'), diğerleri yazılır."""
    if istemci is None and not kimlik_var():
        return {"durum": "kimlik_yok", "yazilan": 0}
    dun = (bugun or piyasa_gunu()) - timedelta(days=1)   # v2.604: piyasa günü
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
    g = bugun or piyasa_gunu(); yarin = g + timedelta(days=1)   # v2.604: piyasa günü
    try:
        ptf = c.ptf(g.isoformat(), yarin.isoformat())
    except Exception as x:   # noqa: BLE001 — EPİAŞ 400 (henüz yayımlanmadı) ya da ağ
        return {"durum": "henuz_yok", "yazilan": 0, "hata": f"{type(x).__name__}: {str(x)[:160]}"}
    if ptf is None or len(ptf) == 0:
        return {"durum": "henuz_yok", "yazilan": 0}
    df = pd.DataFrame({"ptf": ptf.astype(float)}); df["smf"] = float("nan"); df["yon"] = None; df["kaynak"] = "epias_gop"
    yarin_saat = int((df.index.tz_convert(PIYASA_TZ).date == yarin).sum())
    return {"durum": "ok", "yazilan": kaydet(df), "yarin_saat": yarin_saat}


def fiyatlar(index: pd.DatetimeIndex, itibariyle: datetime | None = None) -> pd.DataFrame:
    """Verilen saatler için fiyat: tabloda varsa EPİAŞ, eksik saatler senaryo (kaynak kolonu söyler).
    v2.601 (F4-G, M6): `itibariyle` verilirse o ANDA geçerli olan sürüm okunur (piyasa_fiyat_surum; sonradan gelen düzeltme/gece tam satırı görülmez) —
    kayıtlı bir finansal sonuç `meta.fiyat.itibariyle` ile aynı fiyatlarla yeniden kurulur. None → güncel görünüm (piyasa_fiyat)."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami
    if len(index) == 0:
        return senaryo_fiyat(index)
    prm = {"a": index.min().to_pydatetime(), "b": index.max().to_pydatetime()}
    if itibariyle is None:
        sql = "SELECT ts_utc, ptf, smf, yon, kaynak FROM piyasa_fiyat WHERE ts_utc >= :a AND ts_utc <= :b"
    else:
        sql = ("SELECT DISTINCT ON (ts_utc) ts_utc, ptf, smf, yon, kaynak FROM piyasa_fiyat_surum WHERE ts_utc >= :a AND ts_utc <= :b AND alinma <= :t "
               "ORDER BY ts_utc, alinma DESC, id DESC")
        prm["t"] = itibariyle
    with sistem_baglami() as s:
        df = pd.read_sql(text(sql), s.connection(), params=prm, parse_dates=["ts_utc"])
    out = senaryo_fiyat(index)
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True); df = df.set_index("ts_utc")
        for k in ("ptf", "smf"):   # v2.601: tümü NULL sütun (gün öncesi PTF satırı: smf yok) object gelir; float sütuna yazılamaz → sayıya çevir
            df[k] = pd.to_numeric(df[k], errors="coerce")
        ortak = out.index.intersection(df.index)
        for k in ("ptf", "smf", "yon", "kaynak"):
            out.loc[ortak, k] = df.loc[ortak, k]
    return out


def fiyat_sha16(f: pd.DataFrame) -> str:
    """v2.601 (F4-G, M6): fiyat çerçevesinin içerik damgası (saat, ptf, smf, yön, kaynak; 1e-6 yuvarlama) — sonuç meta'sı `fiyat.sha16`.
    Aynı saatler aynı fiyatla → aynı damga; EPİAŞ düzeltmesi ya da senaryo→gerçek geçişi damgayı değiştirir."""
    import hashlib
    if f is None or len(f) == 0:
        return hashlib.sha256(b"[]").hexdigest()[:16]
    g = f.sort_index()
    idx = pd.DatetimeIndex(g.index)
    idx = idx.tz_convert("UTC") if idx.tz is not None else idx
    def _say(k):
        v = pd.to_numeric(g[k], errors="coerce").round(6) if k in g.columns else pd.Series(float("nan"), index=g.index)
        return [None if pd.isna(x) else float(x) for x in v]
    yon = [None if y is None or (isinstance(y, float) and pd.isna(y)) else str(y) for y in (g["yon"] if "yon" in g.columns else [None] * len(g))]
    kaynak = [str(x) for x in (g["kaynak"] if "kaynak" in g.columns else ["senaryo"] * len(g))]
    satirlar = list(zip([t.isoformat() for t in idx], _say("ptf"), _say("smf"), yon, kaynak, strict=True))
    return hashlib.sha256(repr(satirlar).encode("utf-8")).hexdigest()[:16]


def surum_tarihcesi(ts_utc: datetime, n: int = 20) -> list[dict]:
    """v2.601: bir saatin fiyat sürümleri (en yeni önce) — API /v1/piyasa/fiyat-surumleri."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT ptf, smf, yon, kaynak, alinma FROM piyasa_fiyat_surum WHERE ts_utc = :ts ORDER BY alinma DESC, id DESC LIMIT :n"),
                         {"ts": ts_utc, "n": int(n)}).mappings().all()
    return [{"ptf": r["ptf"], "smf": r["smf"], "yon": r["yon"], "kaynak": r["kaynak"], "alinma": r["alinma"].isoformat()} for r in rows]


def durum() -> dict:
    from sqlalchemy import text

    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT max(ts_utc), count(*), count(yon) FROM piyasa_fiyat WHERE kaynak='epias'")).first()
    return {"kimlik": kimlik_var(), "son_fiyat": r[0].isoformat() if r and r[0] else None, "saat": int(r[1] or 0) if r else 0,
            "yon_saat": int(r[2] or 0) if r else 0,
            "senaryo": {"ptf": SENARYO_PTF, "smf": SENARYO_SMF, "ad": SENARYO_AD}}
