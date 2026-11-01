"""v2.520 (P5a) — TCMB gösterge döviz alış kuru arşivi (doviz_kuru).

Cetvel I YEKDEM fiyatı ABD senti/kWh × enerjinin sisteme verildiği günün TCMB döviz alış kuru (5346 sayılı Kanun m.3(1)(16); YEK Yön.
m.3(1)(dd)); kur elle girilmez, her gün çekilir. Kaynak: https://www.tcmb.gov.tr/kurlar/today.xml (son bülten) ve
/kurlar/YYYYMM/DDMMYYYY.xml (arşiv). TCMB bülteni iş günlerinde 15:30'da yayımlar; hafta sonu ve resmî tatilde dosya yoktur (404) ve
today.xml son iş gününün bültenini döner. Tatil günü için hangi kurun uygulandığı EPİAŞ kaynağında BULUNAMADI → kur_serisi önceki iş
gününün kurunu taşır ve satırı «onceki_gun» ile işaretler (panel «önceki iş günü kuru» yazar; kesinlik iddia etmez). Yalnız döviz alış
(ForexBuying) kullanılır; efektif/satış değil. Kamuya açık veri, kiracısız tablo, sır yok. Worker: gece_kur 13:05 UTC (16:05 TSİ).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

IST = ZoneInfo("Europe/Istanbul")
TCMB_BUGUN = "https://www.tcmb.gov.tr/kurlar/today.xml"
TCMB_ARSIV = "https://www.tcmb.gov.tr/kurlar/{ym}/{dmy}.xml"
PARALAR = ("USD", "EUR")
AZAMI_GUN = 400          # geri doldurma tek istekte en çok
ILK_DOLDURMA_GUN = 399   # arşiv kısaysa worker ilk koşuda bu kadar geriye tamamlar (7189 band kontrolü önceki ayı, döküm 12 ayı ister)
TCMB_SAYFA = "https://www.tcmb.gov.tr/kurlar/kurlar_tr.html"
GERI_TASIMA_GUN = 15     # kur_serisi: bülteni olmayan gün için en çok bu kadar geri bakılır (uzun tatil + hafta sonu)
KAYNAK_ETIKET = {"tcmb": "günün TCMB alış kuru", "tcmb_onceki_gun": "önceki iş gününün TCMB alış kuru (tatil/hafta sonu; EPİAŞ uygulaması doğrulanmadı)",
                 "elle": "elle girilen kur (TCMB kuru yok)", "kur_yok": "kur yok"}


def xml_coz(metin: str) -> dict | None:
    """TCMB bülten XML'i → {gun, usd_alis, eur_alis, bulten}; USD alış kuru yoksa ya da XML bozuksa None."""
    try:
        kok = ET.fromstring(metin)
    except ET.ParseError:
        return None
    try:
        g = datetime.strptime((kok.get("Tarih") or "").strip(), "%d.%m.%Y").date()
    except ValueError:
        return None
    out: dict = {"gun": g, "usd_alis": None, "eur_alis": None, "bulten": kok.get("Bulten_No")}
    for c in kok.findall("Currency"):
        kod = c.get("Kod") or c.get("CurrencyCode")
        if kod not in PARALAR:
            continue
        v = (c.findtext("ForexBuying") or "").strip()
        try:
            deger = float(v) if v else None
            birim = float((c.findtext("Unit") or "1").strip() or 1)
        except ValueError:
            deger, birim = None, 1.0
        out[f"{kod.lower()}_alis"] = (deger / birim) if (deger is not None and birim) else deger
    return out if out["usd_alis"] else None


def _getir(url: str, istemci=None) -> tuple[int, str]:
    if istemci is not None:   # test: url → (durum, metin)
        return istemci(url)
    import httpx
    r = httpx.get(url, timeout=20.0, follow_redirects=True, headers={"User-Agent": "PVQuant/1.0 (yekdem kur)"})
    return r.status_code, r.text


def indir(gun: date | None = None, istemci=None) -> dict | None:
    """gun None → son bülten (today.xml; hafta sonu son iş gününü döner). gun verilirse o günün arşiv dosyası; 404 → None (iş günü
    değil ya da henüz yayımlanmadı). Ağ hatası ve 5xx yükseltilir; dosya adıyla içerik günü uyuşmazsa yazılmaz (None)."""
    url = TCMB_BUGUN if gun is None else TCMB_ARSIV.format(ym=gun.strftime("%Y%m"), dmy=gun.strftime("%d%m%Y"))
    kod, metin = _getir(url, istemci)
    if kod == 404:
        return None
    if kod != 200:
        raise RuntimeError(f"TCMB {kod}: {url}")
    k = xml_coz(metin)
    if k is None:
        raise RuntimeError(f"TCMB bülteni çözülemedi: {url}")
    if gun is not None and k["gun"] != gun:
        return None
    return k


def kaydet(k: dict) -> int:
    """Gün bazında üzerine yazar (aynı gün ikinci çekimde değer değişmez)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO doviz_kuru(gun, usd_alis, eur_alis, bulten, kaynak, guncelleme) VALUES (:g, :u, :e, :b, 'tcmb', now()) "
                       "ON CONFLICT (gun) DO UPDATE SET usd_alis = EXCLUDED.usd_alis, eur_alis = EXCLUDED.eur_alis, bulten = EXCLUDED.bulten, guncelleme = now()"),
                  {"g": k["gun"], "u": float(k["usd_alis"]), "e": (float(k["eur_alis"]) if k.get("eur_alis") is not None else None), "b": k.get("bulten")})
    return 1


def oku(bas: date, bit: date) -> pd.DataFrame:
    """Arşivden gün aralığı (gün indeksli; usd_alis, eur_alis, bulten)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        df = pd.read_sql(text("SELECT gun, usd_alis, eur_alis, bulten FROM doviz_kuru WHERE gun >= :a AND gun <= :b ORDER BY gun"),
                         s.connection(), params={"a": bas, "b": bit})
    if df.empty:
        return pd.DataFrame(columns=["usd_alis", "eur_alis", "bulten"], index=pd.DatetimeIndex([], name="gun"))
    df["gun"] = pd.to_datetime(df["gun"])
    return df.set_index("gun")


def mevcut_gunler(bas: date, bit: date) -> set[date]:
    return {pd.Timestamp(d).date() for d in oku(bas, bit).index}


def kur_serisi(bas: date, bit: date, para: str = "usd", arsiv: pd.DataFrame | None = None) -> pd.DataFrame:
    """Her takvim günü için uygulanacak kur: o günün bülteni varsa o; yoksa önceki iş gününün (onceki_gun=True; en çok GERI_TASIMA_GUN
    geri). Kolonlar: kur, kur_gunu (kullanılan bültenin günü), onceki_gun, kaynak ('tcmb' | 'tcmb_onceki_gun' | 'kur_yok')."""
    kol = f"{para}_alis"
    if arsiv is None:
        arsiv = oku(bas - timedelta(days=GERI_TASIMA_GUN), bit)
    tum = pd.date_range(pd.Timestamp(bas - timedelta(days=GERI_TASIMA_GUN)), pd.Timestamp(bit), freq="D")
    s = (arsiv[kol].astype(float) if (arsiv is not None and not arsiv.empty and kol in arsiv) else pd.Series(dtype=float)).reindex(tum)
    kg = pd.Series(tum, index=tum).where(s.notna()).ffill()
    out = pd.DataFrame({"kur": s.ffill(), "kur_gunu": kg}).loc[pd.Timestamp(bas):pd.Timestamp(bit)]
    out["onceki_gun"] = out["kur_gunu"].notna() & (out["kur_gunu"] != out.index)
    out["kaynak"] = np.where(out["kur"].notna(), np.where(out["onceki_gun"], "tcmb_onceki_gun", "tcmb"), "kur_yok")
    return out


def aylik_ortalama(ay: date, para: str = "usd") -> dict | None:
    """Ayın yayımlanmış bültenlerinin (iş günleri) alış kuru ortalaması — 7189 sayılı CK Ek-2 band kontrolü «bir önceki ayın günlük ABD
    Doları alış kurları ortalaması». Bülten yoksa None."""
    a0 = ay.replace(day=1)
    a1 = (a0 + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    df = oku(a0, a1)
    if df.empty:
        return None
    v = df[f"{para}_alis"].astype(float).dropna()
    if v.empty:
        return None
    beklenen = [g for g in (a0 + timedelta(days=i) for i in range((a1 - a0).days + 1)) if bulten_gunu(g)]
    var = {pd.Timestamp(d).date() for d in v.index}
    eksik = [g.isoformat() for g in beklenen if g not in var]   # 01.11 ikinci inceleme: eksik bültenli ayın ortalaması «tam» gibi görünmesin
    return {"ay": a0.isoformat()[:7], "ortalama": round(float(v.mean()), 4), "gun": int(len(v)), "beklenen": len(beklenen), "eksik_gun": eksik}


def bulten_gunu(d: date) -> bool:
    """TCMB o gün bülten yayımlar mı: iş günü olmalı ve yarım gün (28 Ekim, dinî bayram arefesi) olmamalı — TCMB yarım gün tatillerde kur
    belirlemez (01.11 incelemesi: 28.10.2026 «eksik iş günü» görünüyordu). Takvim modülü yarım günleri iş günü sayar; burada ayrıca elenir."""
    from pvquant.ext.turkiye import takvim as tk
    if not tk.is_gunu(d):
        return False
    if (d.month, d.day) == (10, 28):
        return False
    bayram = tk.DINI_BAYRAM.get(d.year, ())
    return not ((d + timedelta(days=1)) in bayram and d not in bayram)   # ertesi gün bayramın ilk günüyse arefe


def eksik_is_gunleri(bas: date, bit: date) -> list[date]:
    """Aralıkta bülteni olmayan bülten günleri (hafta sonu, resmî tatil ve yarım günler beklenmez)."""
    if bit < bas:
        return []
    var = mevcut_gunler(bas, bit)
    return [g for g in (bas + timedelta(days=i) for i in range((bit - bas).days + 1)) if bulten_gunu(g) and g not in var]


def geri_doldur(bas: date, bit: date, istemci=None) -> dict:
    """Aralıktaki eksik iş günlerini TCMB arşivinden çeker (tek istekte en çok AZAMI_GUN gün). TCMB'de dosya olmayan iş günü (arefe
    yarım gün, olağanüstü tatil) «bulunamayan» listesine düşer; hata değildir."""
    if bit < bas:
        raise ValueError("bitiş başlangıçtan önce olamaz")
    if (bit - bas).days > AZAMI_GUN:
        raise ValueError(f"tek seferde en çok {AZAMI_GUN} gün")
    yazilan, bulunamayan = 0, []
    for g in eksik_is_gunleri(bas, bit):
        k = indir(g, istemci)
        if k is None:
            bulunamayan.append(g.isoformat())
            continue
        yazilan += kaydet(k)
    return {"yazilan": yazilan, "bulunamayan": bulunamayan, "bas": bas.isoformat(), "bit": bit.isoformat()}


def ilk_gun() -> date | None:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT min(gun) FROM doviz_kuru")).scalar()
    return r


def ilk_doldurma(bugun: date | None = None, istemci=None) -> dict | None:
    """Arşiv ILK_DOLDURMA_GUN günden kısaysa (ilk dağıtım ya da uzun kesinti) eksik bülten günlerini bir kerede tamamlar; yeterince
    geriye gidiyorsa None (01.11 incelemesi: arşiv yalnız elle doldurulan Eylül'den başlıyordu, Ağustos–Eylül ilanlarının USD karşılığı
    «kur yok» kalıyordu)."""
    b = bugun or datetime.now(IST).date()
    hedef = b - timedelta(days=ILK_DOLDURMA_GUN)
    ilk = ilk_gun()
    if ilk is not None and ilk <= hedef + timedelta(days=7):
        return None
    return geri_doldur(hedef, b - timedelta(days=1), istemci)


def gunluk(bugun: date | None = None, geri_gun: int = 10, istemci=None) -> str:
    """Worker işi (16:05 TSİ): son bülteni çeker, son geri_gun günün eksik iş günlerini tamamlar. Hafta sonu/tatilde bülten önceki iş
    gününündür (zaten yazılıysa 0 yeni satır) — hata değil. Dönüş jobs_log ayrıntısı."""
    b = bugun or datetime.now(IST).date()
    yeni = 0
    k = indir(None, istemci)
    if k is not None and k["gun"] not in mevcut_gunler(k["gun"], k["gun"]):
        yeni += kaydet(k)
    ilk = ilk_doldurma(b, istemci)
    r = geri_doldur(b - timedelta(days=geri_gun), b - timedelta(days=1), istemci)
    yeni += r["yazilan"] + (ilk["yazilan"] if ilk else 0)
    bulunamayan = sorted(set(r["bulunamayan"]) | set(ilk["bulunamayan"] if ilk else []))
    return (f"yeni {yeni} bülten" + (f" (ilk doldurma {ilk['bas']}–{ilk['bit']}: {ilk['yazilan']})" if ilk else "")
            + (f"; son bülten {k['gun'].isoformat()} USD {k['usd_alis']:.4f}" if k else "; bülten alınamadı")
            + (f"; bulunamayan iş günü {', '.join(bulunamayan)}" if bulunamayan else ""))


def durum(bugun: date | None = None) -> dict:
    """Yönetim kartı: son bülten günü ve kuru, satır sayısı, son 30 günde eksik iş günleri."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    b = bugun or datetime.now(IST).date()
    with sistem_baglami() as s:
        r = s.execute(text("SELECT max(gun), count(*), min(gun) FROM doviz_kuru")).first()
    son = r[0] if r else None
    son_usd = son_eur = None
    if son:
        df = oku(son, son)
        if not df.empty:
            son_usd = float(df["usd_alis"].iloc[0]); e = df["eur_alis"].iloc[0]; son_eur = None if pd.isna(e) else float(e)
    eksik = eksik_is_gunleri(b - timedelta(days=30), b - timedelta(days=1)) if (r and r[1]) else []
    return {"son_gun": son.isoformat() if son else None, "son_usd_alis": son_usd, "son_eur_alis": son_eur, "gun_sayisi": int(r[1] or 0) if r else 0,
            "ilk_gun": r[2].isoformat() if (r and r[2]) else None, "eksik_is_gunu_30": [d.isoformat() for d in eksik],
            "kaynak": "TCMB gösterge döviz alış kuru (today.xml ve günlük arşiv); iş günü 15:30 bülteni, yarım günlerde bülten yok", "kaynak_url": TCMB_SAYFA}
