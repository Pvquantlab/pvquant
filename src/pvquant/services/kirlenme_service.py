"""08.11.2026 v2.544 (dalga 3 kalanı; IH-090 kirlenme ve temizlik kararı, IH-092 sensör kirliliği) — açık-gök tabanlı kirlenme göstergesi.

Uydu ışınım akışı ve kirlenme sensörü yok; gösterge ölçülen düzlem-içi ışınımın AÇIK-GÖK MODELİNE oranından kurulur:
- Açık-gök düzlem-içi ışınım: pvlib Ineichen (Linke bulanıklığı pvlib aylık iklim tablosundan), güneş konumu saat ortası, Hay-Davies düzlem
  dönüşümü santralın eğim/azimutuna (iklim_service.poa_serisi). Eğim/azimut yoksa hesap yok.
- Açık saat: açık-gök POA ≥ 200 W/m², oran 0,5–1,35 arasında ve komşu saatlerle fark ≤ 0,08 (bulut geçişi dışlanır). Günde ≥ 3 açık saat → o gün
  «açık gün»; günün açık-gök endeksi (AGE) açık saatlerdeki oranların medyanı.
- Çapraz okuma: aynı açık saatlerde PR_açık = ΣE_ac / (P0 × ΣPOA/1000). AGE düşer, PR_açık yükselirse → ışınım SENSÖRÜ kirleniyor olabilir
  (sensör düşük okuyunca PR yapay yükselir); AGE sabit, PR_açık düşerse → MODÜLLER kirleniyor olabilir; ikisi birlikte düşerse → sensör modüllerle
  aynı düzlemde birlikte kirleniyor ya da atmosfer bulanıklığı artıyor; ayrım yapılamaz. Yağış (meteo arşivi, ≥ 1 mm/gün) sonrası sıçrama
  kirlenme okumasını destekler.
Dürüstlük: göstergedir; kirlenme oranı/kaybı (kWh, TL) HESAPLANMAZ — yerel kirlenme oranı yok (04-19), kirlenme sensörü yok (SolarPower Europe
O&M v6.0 öneri, 04-05); temizlik kararı eğilim + yağış sonrası sıçrama + saha gözlemiyle verilir. Model çekirdeğine girmez.
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten

ACIK_GOK_MIN_WM2 = 200.0
ORAN_ARALIK = (0.5, 1.35)
KOMSU_FARK = 0.08
ACIK_SAAT_MIN = 3
YAGIS_ESIK_MM = 1.0
EGIM_PENCERE_GUN = 30
EGIM_MIN_ACIK_GUN = 8
EGIM_ESIK_PCT_AY = 2.0      # |eğim| bunun altındaysa «kararlı»

VERI_BAYAT_GUN = 7          # son ölçüm bundan eskiyse «güncel değil» uyarısı
TEMIZ_REFERANS_KANTIL = 0.9  # pencere içindeki açık gün PR'larının bu kantili «temiz durum» referansı
KAYIP_NOTU = ("Tahmindir: temiz durum referansı pencere içindeki açık gün PR'larının %90 kantili; günlük oran açık günlerden ara günlere zamanla "
              "enterpolasyon; kayıp = üretim × (1/oran − 1); pencereler son ölçüm gününe göre sayılır. Yalnız yorum «modüller kirleniyor olabilir» ya da "
              "«birlikte» ise karar tahminidir ve temizlik maliyetiyle karşılaştırılır; eğilim yok/kararlı/atmosfer yorumunda yalnız şartlı senaryo olarak "
              "gösterilir, temizlik karşılaştırması yapılmaz. Işınım sensörü kirleniyor olabilir yorumunda açık gün PR'ı yanlı ölçüldüğünden tahmin askıya "
              "alınır. TL karşılığı satış fiyatıyla gelir tahminidir, uzlaştırma kalemi değildir. Kirlenme sensörü ve uydu referansı yok.")
# 08.11 inceleme (brif, faz 1): kayıp tahmininin güvenilirlik sınıfı yorum koduna bağlıdır — sayı gösterimi ve temizlik karşılaştırması buna göre kısıtlanır.
KAYIP_GECERLILIK = {"modul": "anlamli", "ikisi": "anlamli", "atmosfer": "zayif", "kararli": "zayif", "toparlanma": "zayif", "sensor": "yanli", "yetersiz": "belirsiz"}
KAYIP_GECERLILIK_METIN = {
    "anlamli": "Yorum modül kirlenmesiyle uyumlu; tahmin temizlik kararında kullanılabilir.",
    "zayif": "Açık gün performans oranında belirgin düşüş yok; bu sayı şartlı bir senaryodur, temizlik kararı için kullanılmaz.",
    "belirsiz": "Eğilim için açık gün yetersiz; bu sayı şartlı bir senaryodur, temizlik kararı için kullanılmaz.",
    "yanli": "Işınım sensörü kirleniyor olabilir: açık gün performans oranı şişkin ölçülür, temiz referans ve kayıp bu veriyle hesaplanamaz. Önce sensörü temizleyin; birkaç açık gün sonra tahmin yeniden kurulur.",
}

# Yorum matrisi (ön tanı; kanıt değil). tur: olcum = ölçüm sapması (üretim kaybı değil), uretim = üretim kaybı olası, bilgi = eylem yok.
YORUM = {
    "sensor": {"baslik": "Işınım sensörü kirleniyor olabilir", "tur": "olcum", "uretim_kaybi": "yok",
               "metin": "Açık-gök endeksi düşerken açık gün performans oranı yükseliyor: sensör düşük okudukça PR yapay yükselir. Bu bir ölçüm sapmasıdır, üretim kaybı değildir; PR ve beklenen üretim şişkin okunur. Sensörü temizleyip birkaç açık gün sonra yeniden bakın."},
    "modul": {"baslik": "Modüller kirleniyor olabilir", "tur": "uretim", "uretim_kaybi": "olasi",
              "metin": "Işınım ölçümü kararlı, açık gün performans oranı düşüyor: üretim verimi düşmüş görünüyor; kirlenme, gölgelenme ya da arıza olabilir. Yağış sonrası PR sıçrarsa kirlenme güçlenir; temizlik kararı saha gözlemiyle."},
    "atmosfer": {"baslik": "Işınım azalmış görünüyor; kirlenme kanıtı yok", "tur": "olcum", "uretim_kaybi": "belirsiz",
                 "metin": "Açık-gök endeksi düşüyor ama performans oranı değişmiyor: ölçülen ışınım ve üretim birlikte azalmış. Atmosfer bulanıklığı (aerosol, nem) ya da açık-gök modelinin mevsimsel sapması olabilir; sensör veya modül kirlenmesine işaret etmez."},
    "ikisi": {"baslik": "Sensör ve modüller birlikte düşüyor olabilir", "tur": "uretim", "uretim_kaybi": "olasi",
              "metin": "Hem açık-gök endeksi hem performans oranı düşüyor: sensör modüllerle aynı düzlemde birlikte kirleniyor olabilir. Önce sensörü temizleyin; PR düşüşü sürerse modül kirlenmesi ya da başka bir üretim kaybı vardır."},
    "toparlanma": {"baslik": "Toparlanma", "tur": "bilgi", "uretim_kaybi": "yok",
                   "metin": "Açık-gök endeksi yükseliyor: yağış ya da temizlik sonrası toparlanma. Eylem gerekmez; birkaç açık gün sonra kararlılığı doğrulayın."},
    "kararli": {"baslik": "Kararlı", "tur": "bilgi", "uretim_kaybi": "yok",
                "metin": "Son 30 günde açık-gök endeksi ve açık gün performans oranı belirgin eğilim göstermiyor. Eylem gerekmez."},
    "yetersiz": {"baslik": "Eğilim için açık gün yetersiz", "tur": "bilgi", "uretim_kaybi": "belirsiz",
                 "metin": f"Son {EGIM_PENCERE_GUN} günde en az {EGIM_MIN_ACIK_GUN} açık gün gerekir; bulutlu dönemlerde gösterge bekler, yanlış sonuç vermez."},
}
NOT = ("Ön tanı göstergesidir: ölçülen düzlem-içi ışınımın açık-gök modeline oranı (pvlib Ineichen, Linke bulanıklığı aylık iklim tablosu; Hay-Davies düzlem "
       "dönüşümü), yalnız açık saatlerde. Kirlenme sensörü ve uydu referansı yok; kirlenme oranı doğrudan ölçülmez, kayıp açık-gök PR'dan ayrı etiketli bir "
       "TAHMİN olarak verilir. Yağış hava TAHMİNİ arşivinden (ölçülen yağış değil). Temizlik kararı eğilim, yağış sonrası sıçrama, tahmini kayıp–temizlik "
       "maliyeti karşılaştırması ve saha gözlemiyle verilir.")
def _tr(x) -> str:
    """08.11 inceleme: görünür metinde Türkçe ondalık (0,5 — 0.5 değil)."""
    return f"{x:g}".replace(".", ",")


YONTEM = [
    "Açık-gök düzlem-içi ışınım: pvlib Ineichen açık-gök modeli (Linke bulanıklığı aylık iklim tablosundan), güneş konumu saat ortasında, Hay-Davies düzlem dönüşümü santralın eğim/azimutuna.",
    f"Açık saat: açık-gök ışınımı ≥ {_tr(ACIK_GOK_MIN_WM2)} W/m², ölçülen/açık-gök oranı {_tr(ORAN_ARALIK[0])}–{_tr(ORAN_ARALIK[1])} arasında ve komşu saatlerle fark ≤ {_tr(KOMSU_FARK)} (bulut geçişleri elenir). Günde ≥ {ACIK_SAAT_MIN} açık saat → açık gün.",
    "Açık-gök endeksi (AGE): açık saat oranlarının günlük medyanı. Açık gün PR: aynı saatlerde ΣE_ac / (P0 × ΣPOA/1000).",
    f"Eğilim: son ölçümden geriye {EGIM_PENCERE_GUN} takvim günündeki açık günlerde (≥ {EGIM_MIN_ACIK_GUN}) doğrusal eğim, aylık göreli yüzde (pencere ortalamasına göre; puan değil); |eğim| < %{_tr(EGIM_ESIK_PCT_AY)}/ay «kararlı».",
    "Yorum: AGE↓ PR↑ → sensör (ölçüm sapması); AGE sabit PR↓ → modül (üretim kaybı olası); AGE↓ PR sabit → atmosfer/model (kirlenme kanıtı yok); AGE↓ PR↓ → ikisi; AGE↑ → toparlanma.",
    f"Yağış: hava tahmini arşivinden günlük toplam ≥ {_tr(YAGIS_ESIK_MM)} mm (ölçülen yağış değil); «gün önce» son ölçüm gününe göredir; yalnız bağlam.",
]


# ----------------------------------------------------------------------------- saf
def acik_gok_poa(idx: pd.DatetimeIndex, lat: float, lon: float, egim: float, azimut: float) -> pd.Series:
    """Saat başı UTC damgalı indeks için açık-gök düzlem-içi ışınım (W/m²)."""
    from pvquant.ext.tahmin.fizik_terimler import acik_gok
    from pvquant.services.iklim_service import poa_serisi
    cs = acik_gok(idx, lat, lon)
    return poa_serisi(cs[["ghi", "dni", "dhi"]], lat, lon, float(egim), float(azimut))


def gunluk_endeks(df: pd.DataFrame, cs_poa: pd.Series, capacity_kwp: float, tz: str = PIYASA_TZ) -> pd.DataFrame:
    """SAF. df: ts_utc, power_kw, poa_wm2. cs_poa: aynı damgalarda açık-gök POA. Döner gün satırları: gun, acik_saat, age, pr_acik."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["gun", "acik_saat", "age", "pr_acik"])
    d = df.copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d.set_index("ts_utc").sort_index()
    cs = cs_poa.reindex(d.index)
    poa = pd.to_numeric(d["poa_wm2"], errors="coerce")
    oran = (poa / cs).where(cs >= ACIK_GOK_MIN_WM2)
    aday = oran.between(*ORAN_ARALIK)
    once = (oran - oran.shift(1)).abs(); sonra = (oran - oran.shift(-1)).abs()
    kararli = ((once <= KOMSU_FARK) | once.isna()) & ((sonra <= KOMSU_FARK) | sonra.isna())
    acik = aday & kararli & oran.notna()
    x = pd.DataFrame({"oran": oran, "poa": poa, "guc": pd.to_numeric(d["power_kw"], errors="coerce"), "acik": acik})
    x["gun"] = x.index.tz_convert(tz).date
    out = []
    for g, b in x.groupby("gun", sort=True):
        a = b[b["acik"]]
        if len(a) < ACIK_SAAT_MIN:
            continue
        poa_top = float(a["poa"].sum())
        pr = float(a["guc"].fillna(0).sum()) / (float(capacity_kwp) * poa_top / 1000.0) if (capacity_kwp and poa_top > 0) else np.nan
        out.append({"gun": g, "acik_saat": int(len(a)), "age": round(float(a["oran"].median()), 4), "pr_acik": (round(pr, 4) if pr == pr else None)})
    return pd.DataFrame(out, columns=["gun", "acik_saat", "age", "pr_acik"])


def egim_pct_ay(gunler: pd.DataFrame, alan: str, bitis: date, pencere_gun: int = EGIM_PENCERE_GUN) -> tuple[float | None, int]:
    """SAF. Son `pencere_gun` takvim günündeki açık günlerde doğrusal eğim, aylık yüzde (ortalamaya göre). Döner (eğim %/ay | None, açık gün sayısı)."""
    if gunler is None or gunler.empty or alan not in gunler:
        return None, 0
    g = gunler[(pd.to_datetime(gunler["gun"]).dt.date > bitis - timedelta(days=pencere_gun)) & gunler[alan].notna()]
    n = int(len(g))
    if n < EGIM_MIN_ACIK_GUN:
        return None, n
    t = np.array([(d - bitis).days for d in pd.to_datetime(g["gun"]).dt.date], dtype=float)
    y = g[alan].astype(float).values
    if np.ptp(t) == 0 or np.mean(y) <= 0:
        return None, n
    egim = np.polyfit(t, y, 1)[0]
    return round(float(egim * 30.0 / np.mean(y) * 100.0), 2), n


def yorumla(age_egim: float | None, pr_egim: float | None) -> dict:
    """SAF. Eğilim çiftinden ön tanı kodu (bkz. YORUM)."""
    if age_egim is None or pr_egim is None:
        kod = "yetersiz"
    else:
        e = EGIM_ESIK_PCT_AY
        age_d, age_y = age_egim <= -e, age_egim >= e
        pr_d, pr_y = pr_egim <= -e, pr_egim >= e
        if age_d and pr_y:
            kod = "sensor"
        elif age_d and pr_d:
            kod = "ikisi"
        elif age_d:
            kod = "atmosfer"
        elif pr_d:
            kod = "modul"
        elif age_y:
            kod = "toparlanma"
        else:
            kod = "kararli"
    return {"kod": kod, **YORUM[kod]}


TEMIZLIK_SONRASI_MIN_ACIK_GUN = 3   # v2.546: temizlik sonrası en az bu kadar açık gün varsa referans o döneme bağlanır


def kayip_tahmini(gunler: pd.DataFrame, uretim_gunluk: pd.Series, fiyat_gunluk: pd.Series | None, bitis: date,
                  temizlik_maliyeti_tl: float | None = None, yorum_kodu: str | None = None, temizlik_tarihi: date | None = None) -> dict:
    """SAF. gunler: aylik açık gün satırları (gun, pr_acik); uretim_gunluk: yerel gün → kWh (tüm günler); fiyat_gunluk: gün → TL/MWh.
    Temiz referans = açık gün PR'larının %90 kantili; r_d = PR_d/ref (≤ 1) açık günlerden ara günlere zamanla enterpolasyon; kayıp_d = E_d × (1/r_d − 1)."""
    gecerlilik = KAYIP_GECERLILIK.get(yorum_kodu or "yetersiz", "belirsiz")
    if gecerlilik == "yanli":   # sensör şüphesi: PR yanlı → referans ve kayıp hesaplanmaz (sayı gösterilmez)
        return {"durum": "askida", "neden": "sensor", "gecerlilik": "yanli", "gecerlilik_metin": KAYIP_GECERLILIK_METIN["yanli"], "not": KAYIP_NOTU,
                "temizlik": None, "temizlik_neden": "sensör şüphesi giderilmeden temizlik karşılaştırması yapılmaz",
                "aciklama": KAYIP_GECERLILIK_METIN["yanli"]}
    if gunler is None or gunler.empty or uretim_gunluk is None or uretim_gunluk.empty:
        return {"durum": "yetersiz", "not": KAYIP_NOTU, "aciklama": "Kayıp tahmini için açık gün PR'ı ve günlük üretim gerekir."}
    pr = gunler.dropna(subset=["pr_acik"])
    if len(pr) < EGIM_MIN_ACIK_GUN:
        return {"durum": "yetersiz", "not": KAYIP_NOTU, "aciklama": f"Kayıp tahmini için en az {EGIM_MIN_ACIK_GUN} açık gün gerekir ({len(pr)} var)."}
    s = pd.Series(pr["pr_acik"].astype(float).values, index=pd.to_datetime(pr["gun"]))
    ref_kaynak = f"açık gün PR'larının %{int(TEMIZ_REFERANS_KANTIL * 100)} kantili (pencere)"
    ref = float(s.quantile(TEMIZ_REFERANS_KANTIL))
    if temizlik_tarihi is not None:   # v2.546: son temizlikten sonraki açık günler temiz durumu daha iyi temsil eder
        st = s[s.index > pd.Timestamp(temizlik_tarihi)]
        if len(st) >= TEMIZLIK_SONRASI_MIN_ACIK_GUN:
            ref = float(st.quantile(TEMIZ_REFERANS_KANTIL))
            ref_kaynak = f"son temizlik ({temizlik_tarihi.isoformat()}) sonrası {len(st)} açık günün PR %{int(TEMIZ_REFERANS_KANTIL * 100)} kantili"
        else:
            ref_kaynak += f"; son temizlik ({temizlik_tarihi.isoformat()}) sonrası açık gün yetersiz ({len(st)} < {TEMIZLIK_SONRASI_MIN_ACIK_GUN})"
    if ref <= 0:
        return {"durum": "yetersiz", "not": KAYIP_NOTU, "aciklama": "Referans PR hesaplanamadı."}
    e = uretim_gunluk.copy(); e.index = pd.to_datetime(e.index)
    birlesik = s.index.union(e.index)
    r = (s / ref).clip(upper=1.0).reindex(birlesik).interpolate(method="time").ffill().bfill().reindex(e.index)
    kayip = (e * (1.0 / r - 1.0)).clip(lower=0.0)
    f = None
    if fiyat_gunluk is not None and not fiyat_gunluk.empty:
        f = fiyat_gunluk.copy(); f.index = pd.to_datetime(f.index); f = f.reindex(e.index).ffill().bfill()
    tl = (kayip / 1000.0 * f) if f is not None else None
    son30 = (e.index > pd.Timestamp(bitis - timedelta(days=30))) & (e.index <= pd.Timestamp(bitis))   # son ölçüm gününe kadar 30 takvim günü
    son7 = (e.index > pd.Timestamp(bitis - timedelta(days=7))) & (e.index <= pd.Timestamp(bitis))
    gun_ort_pct = float((1.0 - r[son7]).mean() * 100.0) if son7.any() else None
    k30 = float(kayip[son30].sum()); t30 = float(tl[son30].sum()) if tl is not None else None
    gunluk_tl = (t30 / max(int(son30.sum()), 1)) if t30 is not None else None
    temizlik, temizlik_neden = None, None
    if temizlik_maliyeti_tl is not None and temizlik_maliyeti_tl > 0:
        if gecerlilik == "anlamli":
            temizlik = {"maliyet_tl": float(temizlik_maliyeti_tl), "son30_karsilar": (t30 is not None and t30 >= temizlik_maliyeti_tl),
                        "geri_odeme_gun": (round(float(temizlik_maliyeti_tl) / gunluk_tl, 0) if gunluk_tl and gunluk_tl > 0 else None)}
            if t30 is None:
                temizlik_neden = "satış fiyatı yok; TL karşılaştırması yapılamadı"
        else:
            temizlik_neden = "yorum modül kirlenmesini desteklemiyor; temizlik karşılaştırması yapılmadı"
    return {"durum": "ok", "nitelik": ("tahmin" if gecerlilik == "anlamli" else "senaryo"), "gecerlilik": gecerlilik, "gecerlilik_metin": KAYIP_GECERLILIK_METIN[gecerlilik],
            "bitis": bitis.isoformat(), "referans_pr": round(ref, 4), "referans_kaynak": ref_kaynak,
            "son7_gunluk_kayip_pct": (round(gun_ort_pct, 2) if gun_ort_pct is not None else None),
            "son30_kayip_kwh": round(k30, 1), "son30_kayip_tl": (round(t30, 0) if t30 is not None else None), "son30_gun": int(son30.sum()),
            "pencere_kayip_kwh": round(float(kayip.sum()), 1), "temizlik": temizlik, "temizlik_neden": temizlik_neden, "not": KAYIP_NOTU}


def gunluk_yagis(df_meteo: pd.DataFrame, tz: str = PIYASA_TZ) -> pd.Series:
    """SAF. meteo arşivi saatlik precipitation (mm) → yerel günlük toplam."""
    if df_meteo is None or df_meteo.empty or "precipitation" not in df_meteo:
        return pd.Series(dtype=float)
    s = pd.to_numeric(df_meteo["precipitation"], errors="coerce").fillna(0.0)
    idx = pd.to_datetime(df_meteo.index, utc=True).tz_convert(tz)
    return s.groupby(idx.date).sum()


# ----------------------------------------------------------------------------- DB
def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def _meteo_yagis(lat: float, lon: float, bas, bit) -> pd.DataFrame:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    from pvquant.io.acik_nwp import KAYNAK, _nokta_anahtar
    la, lo = _nokta_anahtar(lat, lon)
    with sistem_baglami() as s:
        return pd.read_sql(text(
            "SELECT DISTINCT ON (ts_utc) ts_utc, precipitation FROM meteo_arsiv WHERE kaynak=:k AND lat=:la AND lon=:lo AND ts_utc >= :a AND ts_utc < :b "
            "AND ts_utc - kosu_zamani BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' ORDER BY ts_utc, kosu_zamani DESC"),
            s.connection(), params={"k": KAYNAK, "la": la, "lo": lo, "a": bas, "b": bit}, index_col="ts_utc", parse_dates=["ts_utc"])


def ozet(tenant_id, plant: dict, gun: int = 90, bugun: date | None = None) -> dict:
    """Son `gun` ölçüm günü: açık gün serisi, AGE/PR_açık 7 gün medyanları, 30 açık gün eğimleri, yorum, son yağış."""
    from zoneinfo import ZoneInfo
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import performans_service as ps
    tz = plant.get("tz") or PIYASA_TZ
    pj = _pj(plant)
    kaynak = ps.isinim_kaynagi(ps.sensor_durumlari(ps.sensorler_oku(pj), bugun), bugun)
    bos = {"pencere_gun": gun, "sensor": kaynak, "not": NOT}
    if plant.get("tilt") is None or plant.get("azimuth") is None:
        return {"durum": "egim_yok", **bos, "aciklama": "Santralın eğim/azimutu kayıtlı değil; açık-gök düzlem-içi ışınımı hesaplanamaz."}
    cap = float(plant.get("capacity_kwp") or 0.0)
    with tenant_baglami(tenant_id) as s:
        son = s.execute(text(f"SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('kalibrasyon')}"), {"p": plant["id"]}).scalar()
        df = pd.read_sql(text(
            f"SELECT ts_utc, power_kw, poa_wm2 FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('kalibrasyon')} AND poa_wm2 IS NOT NULL "
            "AND ts_utc >= :son - (:g * INTERVAL '1 day') AND ts_utc <= :son ORDER BY ts_utc"),
            s.connection(), params={"p": plant["id"], "g": gun, "son": son}, parse_dates=["ts_utc"]) if son is not None else pd.DataFrame()
    if df.empty:
        return {"durum": "poa_yok", **bos, "aciklama": "Düzlem-içi ışınım ölçümü yok; gösterge ölçülen ışınım ister."}
    with tenant_baglami(tenant_id) as s:   # günlük üretim (tüm geçerli saatler; POA'sız saatler dâhil) — kayıp tahmini tabanı
        ur = pd.read_sql(text(f"SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('kalibrasyon')} AND ts_utc >= :son - (:g * INTERVAL '1 day') AND ts_utc <= :son"),
                         s.connection(), params={"p": plant["id"], "g": gun, "son": son}, parse_dates=["ts_utc"])
    idx = pd.DatetimeIndex(pd.to_datetime(df["ts_utc"], utc=True))
    cs = acik_gok_poa(idx, float(plant["lat"]), float(plant["lon"]), float(plant["tilt"]), float(plant["azimuth"]))
    gunler = gunluk_endeks(df, cs, cap, tz)
    bitis = pd.Timestamp(son).tz_convert(ZoneInfo(tz)).date() if son is not None else (bugun or datetime.now(timezone.utc).date())
    bugun = bugun or datetime.now(timezone.utc).date()
    veri_yasi = (bugun - bitis).days
    tazelik = {"son_olcum": bitis.isoformat(), "veri_yasi_gun": veri_yasi, "bayat": veri_yasi > VERI_BAYAT_GUN,
               "not": (f"Son ölçüm {veri_yasi} gün önce; gösterge o tarihe kadar olan ölçümlerle hesaplandı, bugünkü durumu göstermez." if veri_yasi > VERI_BAYAT_GUN else None)}
    if gunler.empty:
        return {"durum": "acik_gun_yok", **bos, "son_olcum": bitis.isoformat(), "tazelik": tazelik, "aciklama": "Pencerede açık gün yok (günde ≥ 3 kararlı açık saat gerekir); bulutlu dönemde gösterge bekler."}
    age_egim, n_age = egim_pct_ay(gunler, "age", bitis)
    pr_egim, _ = egim_pct_ay(gunler, "pr_acik", bitis)
    son7 = gunler.tail(7)
    try:
        bas_utc = pd.Timestamp(bitis - timedelta(days=gun), tz=ZoneInfo(tz)).tz_convert("UTC").to_pydatetime()
        bit_utc = pd.Timestamp(bitis + timedelta(days=1), tz=ZoneInfo(tz)).tz_convert("UTC").to_pydatetime()
        yg = gunluk_yagis(_meteo_yagis(float(plant["lat"]), float(plant["lon"]), bas_utc, bit_utc), tz)
        yagisli = yg[yg >= YAGIS_ESIK_MM]
        son_yagis = ({"tarih": max(yagisli.index).isoformat(), "mm": round(float(yagisli[max(yagisli.index)]), 1), "gun_once": (bitis - max(yagisli.index)).days, "referans": "son ölçüm günü", "kaynak": "hava tahmini arşivi (ölçülen yağış değil)"}
                     if len(yagisli) else {"tarih": None, "mm": None, "gun_once": None, "kaynak": "hava tahmini arşivi", "not": f"pencerede ≥ {YAGIS_ESIK_MM:g} mm/gün yağış yok (hava tahmini arşivi)"})
    except Exception as e:   # noqa: BLE001 — meteo arşivi yoksa gösterge düşmez
        son_yagis = {"tarih": None, "mm": None, "gun_once": None, "kaynak": "hava tahmini arşivi", "not": f"hava tahmini arşivi okunamadı ({type(e).__name__}); yağış bağlamı yok"}
    yorum = yorumla(age_egim, pr_egim)
    try:
        uix = pd.to_datetime(ur["ts_utc"], utc=True).dt.tz_convert(tz)
        uretim_g = pd.to_numeric(ur["power_kw"], errors="coerce").fillna(0).groupby(uix.dt.date).sum()
        fiyat_g = None
        try:
            from pvquant.services.kayip_ayrisimi_service import _fiyat_serisi
            hidx = pd.DatetimeIndex(pd.to_datetime(ur["ts_utc"], utc=True)).unique().sort_values()
            fs, _ = _fiyat_serisi(plant, hidx)
            fiyat_g = fs.groupby(hidx.tz_convert(tz).date).mean()
        except Exception:   # noqa: BLE001 — fiyat yoksa TL verilmez
            fiyat_g = None
        tt = pj.get("son_temizlik_tarihi")
        try:
            tt = date.fromisoformat(tt) if tt else None
        except ValueError:
            tt = None
        kayip = kayip_tahmini(gunler, uretim_g, fiyat_g, bitis, pj.get("temizlik_maliyeti_tl"), yorum["kod"], tt)
    except Exception as e:   # noqa: BLE001
        kayip = {"durum": "yetersiz", "not": KAYIP_NOTU, "aciklama": f"kayıp tahmini alınamadı ({type(e).__name__})"}
    tt = pj.get("son_temizlik_tarihi")
    try:
        son_temizlik = ({"tarih": tt, "gun_once": (bitis - date.fromisoformat(tt)).days, "referans": "son ölçüm günü"} if tt else None)
    except ValueError:
        son_temizlik = None
    return {"durum": "ok", **bos, "son_olcum": bitis.isoformat(), "tazelik": tazelik, "pencere": {"bas": (bitis - timedelta(days=gun)).isoformat(), "bit": bitis.isoformat()},
            "hesaplama_zamani": datetime.now(timezone.utc).isoformat(timespec="minutes"),   # 08.11 inceleme II: sonuçların ne zaman değerlendirildiği
            "kayip": kayip, "son_temizlik": son_temizlik,
            "yontem": YONTEM, "acik_gun": int(len(gunler)), "acik_gun_30": n_age,
            "age_7g": round(float(son7["age"].median()), 3), "pr_acik_7g": (round(float(son7["pr_acik"].dropna().median()), 3) if son7["pr_acik"].notna().any() else None),
            "age_egim_pct_ay": age_egim, "pr_egim_pct_ay": pr_egim, "yorum": yorum, "son_yagis": son_yagis,
            "gunler": [{"gun": str(r["gun"]), "acik_saat": int(r["acik_saat"]), "age": float(r["age"]), "pr_acik": (None if r["pr_acik"] is None or r["pr_acik"] != r["pr_acik"] else float(r["pr_acik"]))}
                       for _, r in gunler.tail(10).iterrows()],
            "esikler": {"acik_gok_min_wm2": ACIK_GOK_MIN_WM2, "oran_aralik": list(ORAN_ARALIK), "komsu_fark": KOMSU_FARK, "acik_saat_min": ACIK_SAAT_MIN,
                        "egim_pencere_gun": EGIM_PENCERE_GUN, "egim_esik_pct_ay": EGIM_ESIK_PCT_AY, "yagis_esik_mm": YAGIS_ESIK_MM}}
