"""05.11.2026 v2.542 (P8b-2; IH-083, IH-092, IH-099 hava düzeltmeli, IH-104 kısmen) — ölçülen havayla beklenen üretim, EPI ve sensör envanteri.

Üç referans (IH-083): (1) tahmin — hava tahmini girdili fizik modeli (kayip_ayrisimi_service, 0–24 saat öncülü), (2) BEKLENEN — ölçülen düzlem-içi
ışınım ve hücre sıcaklığıyla (bu modül), (3) bütçe/P50 — bankable yıllık beklenti ve finansal bütçe (pdeger_service). EPI = Σgerçekleşen / Σbeklenen.

Beklenen (saatlik, kWh): P0 × (POA/1000) × PR_ref × (1 + γ·(T_c − 25)); AC sınırı (EAK) varsa üstten kesilir. Model çekirdeğine dokunmaz; IEC 61724-1
büyüklükleriyle (Y_r, PR) tutarlı basit bir beklentidir, tasarım simülasyonu değildir. PR_ref kaynağı: Santral ayarlarındaki tasarım/sözleşme PR'ı
girildiyse o; girilmediyse santralın kendi son 12 ay ölçülen PR'ı (etiketli — bu durumda EPI «kendi geçmişine göre» okunur). T_c kaynağı: modül
sıcaklık sensörü (≥%90 kapsam); yoksa hava sıcaklığı + rüzgârdan Faiman (IEC 61853-2; rüzgâr yoksa 1 m/s varsayımı, etiketli); o da yoksa sıcaklık
terimi yok (etiketli). Tire ilkesi: ayda POA kapsamı gündüz saatlerinin %95'inden azsa o ayın beklentisi YAZILMAZ (GHI ile uydurulmaz).

Işınım kıyası (IH-104 sigorta koşulu, IH-099 hava düzeltmesi): ölçülen aylık ışınım toplamı (kWh/m²) iklim P50 yatay ışınımıyla kıyaslanır; endeks =
ölçülen / P50. Yalnız yatay (GHI) ölçen sensör beyan edildiyse yapılır — düzlem-içi ölçüm yatay P50 ile aynı düzlemde değildir, aylık toplamlar
üzerinden dönüştürülmez (dürüstlük; saatlik dönüşüm sonraya). Endeks varsa P50 aylık üretim hava düzeltmeli olarak da verilir (P50 × endeks).

Sensör envanteri (IH-092): params_json.sensorler — tür, ölçüm, marka/model, seri no, IEC 61724-1:2021 sınıfı (A/B; 2017 baskısındaki C sınıfı
kaldırıldı), kalibrasyon tarihi ve periyodu (varsayılan 24 ay; standart metni doğrulanmadı, etiketli). Vade türetilir: geçti / yaklaşıyor (≤60 gün) /
uygun / tarih yok. PR kartına ışınım kaynağı etiketi; «Sensör kalibrasyonu vadesi geçti» alarmı alarm_service'te.
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from pvquant.ext.standart import iec61724
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.services.karne_kurali import yayin_kosu_sql as _yayin_sql   # v2.597 (F4-B): yayımlanmış koşu süzgeci

GAMMA_VARSAYILAN = -0.0035               # 1/°C (kristal silisyum tipik; PR kartıyla aynı)
PR_REFERANS_ARALIK = (0.5, 0.95)
T_MODUL_MIN_KAPSAM = 0.9
POA_MIN_KAPSAM = 0.95                    # pr_service ile aynı tire eşiği (ay bazında)
RUZGAR_VARSAYILAN_MS = 1.0
KALIBRASYON_PERIYOT_AY = 24
KALIBRASYON_YAKLASAN_GUN = 60
AC_KAYNAK_ETIKET = {"eak_alani": "EAK alanı", "gecici": "geçici kısıt", "ac_tavani": "AC sınırı"}   # kgup_service.eak_etkin kaynakları; kurulu_guc (DC) kesim değildir

SENSOR_TURLERI = {"piranometre": "Piranometre (termopil)", "referans_hucre": "Referans hücre (fotovoltaik)",
                  "uydu": "Uydu türevli ışınım (saha sensörü değil)", "modul_sicaklik": "Modül sıcaklık sensörü",
                  "meteo_istasyonu": "Meteoroloji istasyonu (hava sıcaklığı, rüzgâr)"}
OLCUMLER = {"poa": "düzlem-içi ışınım (POA)", "ghi": "yatay ışınım (GHI)", "t_module": "modül sıcaklığı",
            "t_air": "hava sıcaklığı", "wind": "rüzgâr hızı"}
SINIFLAR = ("A", "B")
IEC_NOTU = ("IEC 61724-1:2021 izleme sınıfları A ve B (2017 baskısındaki C sınıfı kaldırıldı). Kalibrasyon periyodu üreticinin ya da "
            "izleme sınıfının şartına göre girilir; PVQuant varsayılanı 24 ay — standart metninden doğrulanmadı, beyandır.")
BEKLENEN_NOTU = ("Beklenen üretim ölçülen düzlem-içi ışınım ve hücre sıcaklığından, referans performans oranıyla hesaplanır (P0 × POA/1000 × PR_ref × "
                 "sıcaklık terimi; EAK girildiyse üstten kesilir). Tasarım simülasyonu değildir; model çekirdeğine girmez. EPI = gerçekleşen / beklenen. "
                 "Ayda düzlem-içi ışınım ölçümü gündüz saatlerinin %95'inden azsa o ayın beklentisi yazılmaz.")
ISINIM_NOTU = {"ok": "Işınım endeksi = ölçülen ışınım / iklim P50 (aynı düzlemde: yatay sensörde yatay, düzlem-içi sensörde santralın eğim/azimutuna "
                     "dönüştürülmüş düzlem-içi beklenti), aylık toplam. Sigorta «maddi hasara bağlı olmayan üretim kaybı» kıyasının girdisidir; "
                     "poliçe şartları PVQuant'ta yok.",
               "poa_p50_yok": "Sensör düzlem-içi (POA) ölçüyor; iklim düzlem-içi P50 beklentisi henüz yok (santralın eğim/azimutu girilmemiş ya da aylık iklim "
                              "işi henüz dönüştürmedi). Aylık toplam üzerinden yatay P50 ile kıyas yapılmaz — ışınım endeksi ve hava düzeltmeli P50 verilmez.",
               "sensor_yok": "Işınım sensörü beyan edilmedi (Santral ayarları › Sensörler); ışınım kıyası yapılmadı.",
               "iklim_yok": "İklim beklentisi (P50 ışınım) henüz hesaplanmadı; ışınım kıyası yapılmadı.",
               "olcum_yok": "Ölçülen ışınım birikmedi; ışınım kıyası yapılmadı."}


# ----------------------------------------------------------------------------- sensör envanteri ---------------------
def sensor_dogrula(s: dict) -> dict:
    """SAF. Bir sensör beyanını doğrular ve normalleştirir; hata → ValueError (Türkçe)."""
    if not isinstance(s, dict):
        raise ValueError("sensör kaydı sözlük olmalı")
    tur = str(s.get("tur") or "").strip()
    if tur not in SENSOR_TURLERI:
        raise ValueError(f"tur {', '.join(SENSOR_TURLERI)} arasından olmalı")
    olcum = str(s.get("olcum") or "").strip()
    if olcum not in OLCUMLER:
        raise ValueError(f"olcum {', '.join(OLCUMLER)} arasından olmalı")
    if tur in ("piranometre", "referans_hucre", "uydu") and olcum not in ("poa", "ghi"):
        raise ValueError("ışınım sensörü poa ya da ghi ölçer")
    if tur == "modul_sicaklik" and olcum != "t_module":
        raise ValueError("modül sıcaklık sensörünün ölçümü t_module olmalı")
    if tur == "meteo_istasyonu" and olcum not in ("t_air", "wind"):
        raise ValueError("meteoroloji istasyonu t_air ya da wind ölçer")
    sinif = s.get("sinif")
    sinif = (str(sinif).strip().upper() or None) if sinif not in (None, "") else None
    if sinif is not None and sinif not in SINIFLAR:
        raise ValueError("sinif A ya da B olmalı (IEC 61724-1:2021)")
    kt = s.get("kalibrasyon_tarihi")
    if kt not in (None, ""):
        try:
            kt = date.fromisoformat(str(kt)[:10]).isoformat()
        except ValueError as e:
            raise ValueError("kalibrasyon_tarihi YYYY-AA-GG olmalı") from e
    else:
        kt = None
    per = s.get("kalibrasyon_periyodu_ay")
    per = KALIBRASYON_PERIYOT_AY if per in (None, "") else int(per)
    if not (1 <= per <= 120):
        raise ValueError("kalibrasyon_periyodu_ay 1–120 arasında olmalı")

    def _metin(ad, en):
        v = s.get(ad)
        v = "" if v is None else str(v).strip()
        if len(v) > en:
            raise ValueError(f"{ad} en çok {en} karakter")
        return v or None
    return {"tur": tur, "olcum": olcum, "marka_model": _metin("marka_model", 80), "seri_no": _metin("seri_no", 40),
            "sinif": sinif, "kalibrasyon_tarihi": kt, "kalibrasyon_periyodu_ay": per, "not": _metin("not", 200)}


def _ay_ekle(d: date, ay: int) -> date:
    y, m = divmod(d.month - 1 + ay, 12)
    yil = d.year + y; m += 1
    son = [31, 29 if (yil % 4 == 0 and (yil % 100 != 0 or yil % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(yil, m, min(d.day, son))


def sensor_durumlari(sensorler: list[dict] | None, bugun: date | None = None) -> list[dict]:
    """SAF. Her sensöre kalibrasyon vadesi ve durumu ekler: gecti / yaklasiyor / uygun / tarih_yok."""
    bugun = bugun or datetime.now(timezone.utc).date()
    out = []
    for s in sensorler or []:
        kt = s.get("kalibrasyon_tarihi")
        if kt:
            vade = _ay_ekle(date.fromisoformat(str(kt)[:10]), int(s.get("kalibrasyon_periyodu_ay") or KALIBRASYON_PERIYOT_AY))
            kalan = (vade - bugun).days
            durum = "gecti" if kalan < 0 else ("yaklasiyor" if kalan <= KALIBRASYON_YAKLASAN_GUN else "uygun")
            out.append({**s, "vade": vade.isoformat(), "kalan_gun": kalan, "durum": durum})
        else:
            out.append({**s, "vade": None, "kalan_gun": None, "durum": "tarih_yok"})
    return out


def isinim_kaynagi(sensorler: list[dict] | None, bugun: date | None = None) -> dict:
    """SAF. PR kartı ve ışınım kıyası için ışınım sensörü özeti: düzlem (poa/ghi/None), etiket, sınıf, kalibrasyon durumu."""
    durumlar = sensor_durumlari(sensorler, bugun)
    isinim = [s for s in durumlar if s["olcum"] in ("poa", "ghi")]
    if not isinim:
        return {"duzlem": None, "etiket": "ışınım sensörü beyan edilmedi", "sinif": None, "kalibrasyon": None, "tur": None}
    # düzlem-içi varsa o esas (PR IEC düzlem-içi ister); yoksa yatay
    s = next((x for x in isinim if x["olcum"] == "poa"), isinim[0])
    etiket = f"{SENSOR_TURLERI[s['tur']]} — {OLCUMLER[s['olcum']]}" + (f", sınıf {s['sinif']}" if s.get("sinif") else ", sınıf beyan edilmedi")
    return {"duzlem": s["olcum"], "etiket": etiket, "sinif": s.get("sinif"), "kalibrasyon": s["durum"], "tur": s["tur"],
            "vade": s.get("vade")}


def sensorler_oku(pj: dict | str | None) -> list[dict]:
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    v = (pj or {}).get("sensorler")
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


# ----------------------------------------------------------------------------- beklenen seri ---------------------
def hucre_sicakligi(df: pd.DataFrame) -> tuple[pd.Series | None, str]:
    """SAF. T_c kaynağı: t_module (≥%90) → 'modul'; t_air (+wind) → 'faiman'; yoksa (None, 'yok')."""
    if "t_module" in df and df["t_module"].notna().mean() >= T_MODUL_MIN_KAPSAM:
        return df["t_module"].astype(float), "modul"
    if "t_air" in df and df["t_air"].notna().mean() >= T_MODUL_MIN_KAPSAM:
        ruzgar = df["wind_ms"].astype(float) if "wind_ms" in df else pd.Series(np.nan, index=df.index)
        varsayim = bool(ruzgar.isna().mean() > 0.5)
        tc = iec61724.hucre_sicakligi_faiman(df["poa_wm2"].astype(float).clip(lower=0), df["t_air"].astype(float),
                                             ruzgar.fillna(RUZGAR_VARSAYILAN_MS))
        return tc, ("faiman_ruzgarsiz" if varsayim else "faiman")
    return None, "yok"


T_C_ETIKET = {"modul": "modül sıcaklık sensörü", "faiman": "hava sıcaklığı ve rüzgârdan (Faiman, IEC 61853-2)",
              "faiman_ruzgarsiz": "hava sıcaklığından (Faiman; rüzgâr ölçümü yok, 1 m/s varsayımı)",
              "yok": "sıcaklık ölçümü yok — sıcaklık terimi uygulanmadı"}


def beklenen_olculen(df: pd.DataFrame, capacity_kwp: float, pr_ref: float, gamma: float = GAMMA_VARSAYILAN,
                     ac_sinir_kw: float | None = None) -> tuple[pd.DataFrame, str]:
    """SAF. df: ts_utc, power_kw, poa_wm2, t_module/t_air/wind_ms (NaN olabilir), flag, kirpma. Döner (df + beklenen_kw, t_c kaynağı)."""
    d = df.copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d.set_index("ts_utc").sort_index()
    poa = pd.to_numeric(d["poa_wm2"], errors="coerce").clip(lower=0)
    tc, kaynak = hucre_sicakligi(d)
    terim = (1.0 + gamma * (tc - 25.0)) if tc is not None else pd.Series(1.0, index=d.index)
    bek = float(capacity_kwp) * poa / 1000.0 * float(pr_ref) * terim.fillna(1.0)
    if ac_sinir_kw:
        bek = bek.clip(upper=float(ac_sinir_kw))
    d["beklenen_kw"] = bek.where(poa.notna())
    d["t_c"] = tc
    return d.reset_index(), kaynak


def aylik_tablo(d: pd.DataFrame, capacity_kwp: float, tz: str = PIYASA_TZ) -> list[dict]:
    """SAF. beklenen_olculen çıktısından ay satırları (santral saat dilimi). Tire: ay POA kapsamı < %95 → beklenen/EPI None."""
    if d is None or d.empty:
        return []
    x = d.copy()
    x["ts"] = pd.to_datetime(x["ts_utc"], utc=True).dt.tz_convert(tz)
    x["ay"] = x["ts"].dt.strftime("%Y-%m")
    guc = pd.to_numeric(x["power_kw"], errors="coerce")
    poa = pd.to_numeric(x["poa_wm2"], errors="coerce")
    x["gunduz"] = guc > 0.02 * float(capacity_kwp)
    x["poa_var"] = poa.notna() & (poa > 0)
    x["kirp"] = x["kirpma"].fillna(False).astype(bool) if "kirpma" in x else False
    x["kisinti"] = (x["flag"] == "kisinti") if "flag" in x else False
    out = []
    for ay, g in x.groupby("ay", sort=True):
        gd = g[g["gunduz"]]
        kapsam = float(gd["poa_var"].mean()) if len(gd) else 0.0
        uretim = float(pd.to_numeric(g["power_kw"], errors="coerce").fillna(0).sum())
        satir = {"ay": ay, "uretim_kwh": round(uretim, 1), "saat": int(g["power_kw"].notna().sum()), "poa_kapsam": round(kapsam, 3),
                 "kirpma_saat": int(g["kirp"].sum()), "kisinti_saat": int(g["kisinti"].sum()),
                 "isinim_kwh_m2": (round(float(poa.loc[g.index].fillna(0).sum()) / 1000.0, 1) if g["poa_var"].any() else None),
                 "beklenen_kwh": None, "epi": None, "epi_temiz": None, "durum": "ok"}
        if kapsam < POA_MIN_KAPSAM or not len(gd):
            satir["durum"] = "poa_yok"
        else:
            bv = g["beklenen_kw"].notna()
            bek = float(g.loc[bv, "beklenen_kw"].sum()); ger = float(pd.to_numeric(g.loc[bv, "power_kw"], errors="coerce").fillna(0).sum())
            satir["beklenen_kwh"] = round(bek, 1)
            satir["epi"] = round(ger / bek, 4) if bek > 0 else None
            temiz = bv & ~g["kirp"] & ~g["kisinti"]
            bek2 = float(g.loc[temiz, "beklenen_kw"].sum()); ger2 = float(pd.to_numeric(g.loc[temiz, "power_kw"], errors="coerce").fillna(0).sum())
            satir["epi_temiz"] = round(ger2 / bek2, 4) if bek2 > 0 else None
        out.append(satir)
    return out


def referans_pr(pj: dict | None, pr_olcum: dict | None) -> dict | None:
    """SAF. PR_ref: tasarım/sözleşme değeri girildiyse o; yoksa son 12 ay ölçülen PR (sıcaklık düzeltmeli > kırpma dışı > ham)."""
    v = (pj or {}).get("pr_referans")
    if v not in (None, ""):
        return {"deger": float(v), "kaynak": "tasarim", "etiket": "tasarım/sözleşme PR (Santral ayarlarından)"}
    if pr_olcum and pr_olcum.get("durum") == "ok":
        for alan, ad in (("PR_sicaklik", "sıcaklık düzeltmeli"), ("PR_kirpma_disi", "kırpma dışı"), ("PR", "ham")):
            if pr_olcum.get(alan) is not None:
                return {"deger": float(pr_olcum[alan]), "kaynak": "olcum",
                        "etiket": f"santralın kendi son {int(pr_olcum.get('pencere_gun') or 365)} gün ölçülen PR'ı ({ad}); EPI kendi geçmişine göre okunur"}
    return None


def isinim_endeksi(aylar: list[dict], iklim: dict | None, duzlem: str | None) -> dict:
    """SAF. aylar: aylik_tablo satırları (isinim_kwh_m2). iklim: {"ghi": {ay_no: kWh/m²}, "poa": {ay_no: kWh/m²}} — sensörün düzlemiyle aynı
    düzlem kullanılır; düzlem-içi sensörde POA beklentisi yoksa `poa_p50_yok` (yatayla kıyas YAPILMAZ)."""
    if duzlem is None:
        return {"durum": "sensor_yok", "aylar": {}, "yil": None}
    if not iklim or not iklim.get("ghi"):
        return {"durum": "iklim_yok", "aylar": {}, "yil": None}
    p50 = iklim.get(duzlem) or {}
    if duzlem == "poa" and not p50:
        return {"durum": "poa_p50_yok", "aylar": {}, "yil": None}
    endeks = {}; top_o = top_p = 0.0
    for s in aylar:
        o = s.get("isinim_kwh_m2"); p = p50.get(int(s["ay"][5:7]))
        if o is None or not p or s.get("durum") != "ok":
            continue
        endeks[s["ay"]] = {"olculen_kwh_m2": o, "p50_kwh_m2": round(float(p), 1), "endeks": round(float(o) / float(p), 3)}
        top_o += float(o); top_p += float(p)
    if not endeks:
        return {"durum": "olcum_yok", "aylar": {}, "yil": None}
    return {"durum": "ok", "aylar": endeks, "yil": round(top_o / top_p, 3) if top_p > 0 else None}


# ----------------------------------------------------------------------------- DB ---------------------
def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def ozet(tenant_id, plant: dict, ay: int = 12, bugun: date | None = None) -> dict:
    """Son `ay` ay + cari ay: ölçülen havayla beklenen, EPI, üç referans, ışınım endeksi, sensör özeti."""
    bugun = bugun or datetime.now(timezone.utc).date()
    return _hesapla(tenant_id, plant, _ay_ekle(bugun.replace(day=1), -int(ay)), None, bugun, ay=int(ay))


def donem(tenant_id, plant: dict, bas: date, bit: date, bugun: date | None = None) -> dict:
    """v2.542 (aylık rapor): kapalı dönem [bas, bit] (yerel günler, bit dâhil) için aynı hesap."""
    bugun = bugun or datetime.now(timezone.utc).date()
    return _hesapla(tenant_id, plant, bas, bit + timedelta(days=1), bugun, ay=0)


def _hesapla(tenant_id, plant: dict, bas_yerel: date, bit_yerel: date | None, bugun: date, ay: int) -> dict:
    from zoneinfo import ZoneInfo
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import pr_service, iklim_service
    tz = plant.get("tz") or PIYASA_TZ
    pj = _pj(plant)
    cap = float(plant.get("capacity_kwp") or 0.0)
    bas_utc = pd.Timestamp(bas_yerel, tz=ZoneInfo(tz)).tz_convert("UTC")
    bit_utc = pd.Timestamp(bit_yerel, tz=ZoneInfo(tz)).tz_convert("UTC") if bit_yerel else pd.Timestamp("2100-01-01", tz="UTC")
    sens = sensor_durumlari(sensorler_oku(pj), bugun)
    kaynak = isinim_kaynagi(sens, bugun)
    bos = {"ay": int(ay), "bugun": bugun.isoformat(), "bas": bas_yerel.isoformat(), "bit": (bit_yerel - timedelta(days=1)).isoformat() if bit_yerel else None,
           "sensorler": kaynak, "sensor_sayisi": len(sens), "not": BEKLENEN_NOTU}
    if cap <= 0:
        return {"durum": "veri_yok", **bos}
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, poa_wm2, t_air, t_module, wind_ms, flag, kirpma FROM scada_hourly "
            f"WHERE plant_id=:p AND {_ks.sql_kosulu('kayip')} AND ts_utc >= :bas AND ts_utc < :bit ORDER BY ts_utc"),
            s.connection(), params={"p": plant["id"], "bas": bas_utc.to_pydatetime(), "bit": bit_utc.to_pydatetime()}, parse_dates=["ts_utc"])
        tahmin = pd.read_sql(text(
            "SELECT DISTINCT ON (f.ts_utc) f.ts_utc, f.physics_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "WHERE f.plant_id=:p AND f.ts_utc >= :bas AND f.ts_utc < :bit AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            f"AND {_yayin_sql('r')} "
            "ORDER BY f.ts_utc, r.run_at DESC"),
            s.connection(), params={"p": plant["id"], "bas": bas_utc.to_pydatetime(), "bit": bit_utc.to_pydatetime()}, parse_dates=["ts_utc"])
    if df.empty:
        return {"durum": "veri_yok", **bos}
    pr12 = pr_service.pr_karti(tenant_id, plant["id"], gun=365)
    ref = referans_pr(pj, pr12)
    if ref is None:
        return {"durum": "referans_yok", **bos, "pr_olcum": {k: pr12.get(k) for k in ("durum", "poa_orani", "gun")},
                "not": "Referans performans oranı yok: Santral ayarlarına tasarım/sözleşme PR'ı girin ya da düzlem-içi ışınım ölçümü biriksin (son 12 ayda PR hesaplanamadı)."}
    # kesim: EAK alanı / geçici kısıt / AC sınırı (kgup_service öncelik sırası); yalnız kurulu güç (DC) kalıyorsa kesim yok
    ac_sinir_kw = None; ac_kaynak = None
    try:
        from pvquant.services import kgup_service
        e = kgup_service.eak_etkin(plant, bugun)
        if e.get("kaynak") in AC_KAYNAK_ETIKET:
            ac_sinir_kw = float(e["eak_mw"]) * 1000.0; ac_kaynak = AC_KAYNAK_ETIKET[e["kaynak"]]
    except Exception:   # noqa: BLE001
        ac_sinir_kw = float(pj["eak_kw"]) if pj.get("eak_kw") else None; ac_kaynak = "EAK alanı" if ac_sinir_kw else None
    d, tc_kaynak = beklenen_olculen(df, cap, ref["deger"], GAMMA_VARSAYILAN, ac_sinir_kw)
    aylar = aylik_tablo(d, cap, tz)
    # tahmin referansı (hava tahmini girdili fizik modeli): ölçümün olduğu saatlerde aylık toplam
    if not tahmin.empty:
        t = tahmin.copy(); t["ts_utc"] = pd.to_datetime(t["ts_utc"], utc=True)
        olc = pd.to_datetime(df["ts_utc"], utc=True)
        t = t[t["ts_utc"].isin(set(olc))]
        t["ay"] = t["ts_utc"].dt.tz_convert(tz).dt.strftime("%Y-%m")
        tah = t.groupby("ay")["physics_kw"].sum().to_dict()
        for sat in aylar:
            v = tah.get(sat["ay"]); sat["tahmin_kwh"] = round(float(v), 1) if v is not None else None
    else:
        for sat in aylar:
            sat["tahmin_kwh"] = None
    # P50 aylık (bankable × iklim payı) ve ışınım endeksi
    p50_ay: dict[int, float] = {}; iklim_p50: dict[int, float] = {}; poa_p50: dict[int, float] = {}
    try:
        b = iklim_service.iklim_oku(tenant_id, plant["id"])
        if b is not None and not b.empty and len(b) == 12:
            iklim_p50 = {int(r["ay"]): float(r["ghi_p50_kwh_m2"]) for _, r in b.iterrows() if r["ghi_p50_kwh_m2"] == r["ghi_p50_kwh_m2"]}
            if "poa_p50_kwh_m2" in b:   # v2.542: düzlem-içi beklenti (aylık iklim işi santralın eğim/azimutuyla)
                poa_p50 = {int(r["ay"]): float(r["poa_p50_kwh_m2"]) for _, r in b.iterrows() if r["poa_p50_kwh_m2"] is not None and r["poa_p50_kwh_m2"] == r["poa_p50_kwh_m2"]}
    except Exception:   # noqa: BLE001
        iklim_p50 = {}
    try:
        from pvquant.services import bankable_service
        bk = bankable_service.getir(plant)
        if bk and bk.get("durum") == "ok" and iklim_p50 and len(iklim_p50) == 12:
            top = sum(iklim_p50.values())
            p50_ay = {k: float(bk["p50_kwh"]) * v / top for k, v in iklim_p50.items()}
    except Exception:   # noqa: BLE001
        p50_ay = {}
    end = isinim_endeksi(aylar, {"ghi": iklim_p50, "poa": poa_p50} if iklim_p50 else None, kaynak["duzlem"])
    duzlem_p50 = poa_p50 if kaynak["duzlem"] == "poa" else iklim_p50
    for sat in aylar:
        no = int(sat["ay"][5:7])
        sat["p50_kwh"] = round(p50_ay[no], 1) if no in p50_ay else None
        e = end["aylar"].get(sat["ay"])
        sat["isinim_p50_kwh_m2"] = e["p50_kwh_m2"] if e else (round(duzlem_p50[no], 1) if (no in duzlem_p50 and end["durum"] == "ok") else None)
        sat["isinim_endeksi"] = e["endeks"] if e else None
        sat["p50_hava_duzeltmeli_kwh"] = round(p50_ay[no] * e["endeks"], 1) if (e and no in p50_ay) else None
    ok = [a for a in aylar if a["durum"] == "ok"]
    tb = sum(a["beklenen_kwh"] for a in ok); tg = sum(a["uretim_kwh"] for a in ok)
    toplam = {"ay_ok": len(ok), "ay": len(aylar), "uretim_kwh": round(tg, 1), "beklenen_kwh": round(tb, 1),
              "epi": (round(tg / tb, 4) if tb > 0 else None),
              "tahmin_kwh": (round(sum(a["tahmin_kwh"] for a in ok if a.get("tahmin_kwh") is not None), 1) if any(a.get("tahmin_kwh") is not None for a in ok) else None),
              "p50_kwh": (round(sum(a["p50_kwh"] for a in ok if a.get("p50_kwh") is not None), 1) if any(a.get("p50_kwh") is not None for a in ok) else None)}
    return {"durum": "ok" if ok else "poa_yok", **bos, "referans": ref, "sicaklik": {"kaynak": tc_kaynak, "etiket": T_C_ETIKET[tc_kaynak]},
            "gamma": GAMMA_VARSAYILAN, "ac_sinir_kw": ac_sinir_kw, "ac_sinir_kaynak": ac_kaynak, "aylar": aylar, "toplam": toplam,
            "isinim": {"durum": end["durum"], "yil": end["yil"], "not": ISINIM_NOTU[end["durum"]], "duzlem": kaynak["duzlem"]},
            "pr_olcum": {k: pr12.get(k) for k in ("durum", "PR", "PR_sicaklik", "PR_kirpma_disi", "poa_orani", "gun")}}
