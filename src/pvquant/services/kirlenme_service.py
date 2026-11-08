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

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

ACIK_GOK_MIN_WM2 = 200.0
ORAN_ARALIK = (0.5, 1.35)
KOMSU_FARK = 0.08
ACIK_SAAT_MIN = 3
YAGIS_ESIK_MM = 1.0
EGIM_PENCERE_GUN = 30
EGIM_MIN_ACIK_GUN = 8
EGIM_ESIK_PCT_AY = 2.0      # |eğim| bunun altındaysa «kararlı»

VERI_BAYAT_GUN = 7          # son ölçüm bundan eskiyse «güncel değil» uyarısı

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
       "dönüşümü), yalnız açık saatlerde. Kirlenme sensörü ve uydu referansı yok; kirlenme oranı ya da kaybı (kWh, TL) hesaplanmaz. Yağış hava TAHMİNİ "
       "arşivinden (ölçülen yağış değil). Temizlik kararı eğilim, yağış sonrası sıçrama ve saha gözlemiyle verilir.")
YONTEM = [
    "Açık-gök düzlem-içi ışınım: pvlib Ineichen açık-gök modeli (Linke bulanıklığı aylık iklim tablosundan), güneş konumu saat ortasında, Hay-Davies düzlem dönüşümü santralın eğim/azimutuna.",
    f"Açık saat: açık-gök ışınımı ≥ {ACIK_GOK_MIN_WM2:g} W/m², ölçülen/açık-gök oranı {ORAN_ARALIK[0]:g}–{ORAN_ARALIK[1]:g} arasında ve komşu saatlerle fark ≤ {KOMSU_FARK:g} (bulut geçişleri elenir). Günde ≥ {ACIK_SAAT_MIN} açık saat → açık gün.",
    "Açık-gök endeksi (AGE): açık saat oranlarının günlük medyanı. Açık gün PR: aynı saatlerde ΣE_ac / (P0 × ΣPOA/1000).",
    f"Eğilim: son {EGIM_PENCERE_GUN} takvim günündeki açık günlerde (≥ {EGIM_MIN_ACIK_GUN}) doğrusal eğim, aylık yüzde; |eğim| < %{EGIM_ESIK_PCT_AY:g}/ay «kararlı».",
    "Yorum: AGE↓ PR↑ → sensör (ölçüm sapması); AGE sabit PR↓ → modül (üretim kaybı olası); AGE↓ PR sabit → atmosfer/model (kirlenme kanıtı yok); AGE↓ PR↓ → ikisi; AGE↑ → toparlanma.",
    f"Yağış: hava tahmini arşivinden günlük toplam ≥ {YAGIS_ESIK_MM:g} mm (ölçülen yağış değil); yalnız bağlam.",
]


# ----------------------------------------------------------------------------- saf
def acik_gok_poa(idx: pd.DatetimeIndex, lat: float, lon: float, egim: float, azimut: float) -> pd.Series:
    """Saat başı UTC damgalı indeks için açık-gök düzlem-içi ışınım (W/m²)."""
    from pvquant.ext.tahmin.fizik_terimler import acik_gok
    from pvquant.services.iklim_service import poa_serisi
    cs = acik_gok(idx, lat, lon)
    return poa_serisi(cs[["ghi", "dni", "dhi"]], lat, lon, float(egim), float(azimut))


def gunluk_endeks(df: pd.DataFrame, cs_poa: pd.Series, capacity_kwp: float, tz: str = "Europe/Istanbul") -> pd.DataFrame:
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


def gunluk_yagis(df_meteo: pd.DataFrame, tz: str = "Europe/Istanbul") -> pd.Series:
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
    tz = plant.get("tz") or "Europe/Istanbul"
    pj = _pj(plant)
    kaynak = ps.isinim_kaynagi(ps.sensor_durumlari(ps.sensorler_oku(pj), bugun), bugun)
    bos = {"pencere_gun": gun, "sensor": kaynak, "not": NOT}
    if plant.get("tilt") is None or plant.get("azimuth") is None:
        return {"durum": "egim_yok", **bos, "aciklama": "Santralın eğim/azimutu kayıtlı değil; açık-gök düzlem-içi ışınımı hesaplanamaz."}
    cap = float(plant.get("capacity_kwp") or 0.0)
    with tenant_baglami(tenant_id) as s:
        son = s.execute(text("SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid'"), {"p": plant["id"]}).scalar()
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, poa_wm2 FROM scada_hourly WHERE plant_id=:p AND flag='valid' AND poa_wm2 IS NOT NULL "
            "AND ts_utc >= :son - (:g * INTERVAL '1 day') AND ts_utc <= :son ORDER BY ts_utc"),
            s.connection(), params={"p": plant["id"], "g": gun, "son": son}, parse_dates=["ts_utc"]) if son is not None else pd.DataFrame()
    if df.empty:
        return {"durum": "poa_yok", **bos, "aciklama": "Düzlem-içi ışınım ölçümü yok; gösterge ölçülen ışınım ister."}
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
        son_yagis = ({"tarih": max(yagisli.index).isoformat(), "mm": round(float(yagisli[max(yagisli.index)]), 1), "gun_once": (bitis - max(yagisli.index)).days, "kaynak": "hava tahmini arşivi (ölçülen yağış değil)"}
                     if len(yagisli) else {"tarih": None, "mm": None, "gun_once": None, "kaynak": "hava tahmini arşivi", "not": f"pencerede ≥ {YAGIS_ESIK_MM:g} mm/gün yağış yok (hava tahmini arşivi)"})
    except Exception as e:   # noqa: BLE001 — meteo arşivi yoksa gösterge düşmez
        son_yagis = {"tarih": None, "mm": None, "gun_once": None, "kaynak": "hava tahmini arşivi", "not": f"hava tahmini arşivi okunamadı ({type(e).__name__}); yağış bağlamı yok"}
    return {"durum": "ok", **bos, "son_olcum": bitis.isoformat(), "tazelik": tazelik, "pencere": {"bas": (bitis - timedelta(days=gun)).isoformat(), "bit": bitis.isoformat()},
            "yontem": YONTEM, "acik_gun": int(len(gunler)), "acik_gun_30": n_age,
            "age_7g": round(float(son7["age"].median()), 3), "pr_acik_7g": (round(float(son7["pr_acik"].dropna().median()), 3) if son7["pr_acik"].notna().any() else None),
            "age_egim_pct_ay": age_egim, "pr_egim_pct_ay": pr_egim, "yorum": yorumla(age_egim, pr_egim), "son_yagis": son_yagis,
            "gunler": [{"gun": str(r["gun"]), "acik_saat": int(r["acik_saat"]), "age": float(r["age"]), "pr_acik": (None if r["pr_acik"] is None or r["pr_acik"] != r["pr_acik"] else float(r["pr_acik"]))}
                       for _, r in gunler.tail(10).iterrows()],
            "esikler": {"acik_gok_min_wm2": ACIK_GOK_MIN_WM2, "oran_aralik": list(ORAN_ARALIK), "komsu_fark": KOMSU_FARK, "acik_saat_min": ACIK_SAAT_MIN,
                        "egim_pencere_gun": EGIM_PENCERE_GUN, "egim_esik_pct_ay": EGIM_ESIK_PCT_AY, "yagis_esik_mm": YAGIS_ESIK_MM}}
