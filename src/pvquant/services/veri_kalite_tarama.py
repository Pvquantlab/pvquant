"""VERİ KALİTESİ TARAMASI — ölçüm serilerinde üç UYARI imzası (26.11.2026; bağımsız 2026 koşusu bulguları). SAF; DB/ağ yok.

Yalnız UYARI üretir: hiçbir veriyi kaydırmaz, kırpmaz, düzeltmez; tahmin ve kalibrasyon yolları çağırmaz (model/eşik değişmez).
«Doğrulanmış arıza» hükmü verilmez — kaynak teyidi (EPİAŞ/işletmeci/sayaç) gerekir; döngü sözlüğü: sinif ∈ {temiz, uyari}.
1) zaman_kaymasi: güç–ışınım aylık en iyi gecikme (±1 sa); ardışık ≥`min_ay` ayda lag ≠ 0 → uyarı (Ra Mardin Şub 2025→: −1 sa).
2) ac_asimi: güç > AC sınırı × (1 + tolerans) olan saatler ve ayları (Büyükalan-1 Şub 2026: 21 sa, +%3,7).
3) kis_uretim_kaybi: günlük GHI ≥ `ghi_min_kwh` iken özgül verim < `verim_esik` olan günler (kar örtüsü / soğuk kesinti imzası;
   Solentegre Oca–Şub 2026: 11 gün, T_min −10 °C); varsa günün en düşük sıcaklığı eklenir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAG_ADAYLARI = (-1, 0, 1)
MIN_AY = 2
AC_TOLERANS = 0.01
GHI_MIN_KWH = 2.0
VERIM_ESIK = 0.30


def _utc(s: pd.Series) -> pd.Series:
    if not isinstance(s.index, pd.DatetimeIndex):
        s = s.copy()
        s.index = pd.to_datetime(s.index, utc=True)
    return s if s.index.tz is not None else s.tz_localize("UTC")


def zaman_kaymasi(power_kw: pd.Series, ghi: pd.Series, *, min_ay: int = MIN_AY, min_saat: int = 200) -> dict:
    """Aylık en iyi gecikme (ghi.shift(lag) ile korelasyon). Ardışık ≥min_ay ayda lag ≠ 0 → uyari; başlangıç ayı raporlanır."""
    p, g = _utc(power_kw.astype(float)), _utc(ghi.astype(float))
    j = pd.concat([p.rename("p"), g.rename("g")], axis=1, join="inner").dropna()
    aylik: dict[str, int | None] = {}
    for ay, d in j.groupby(j.index.tz_convert(None).to_period("M")):   # tz bilgisi ay etiketinde gerekmez (UTC)
        if len(d) < min_saat or d["p"].std() == 0 or d["g"].std() == 0:
            aylik[str(ay)] = None
            continue
        kor = {L: float(d["p"].corr(d["g"].shift(L))) for L in LAG_ADAYLARI}
        aylik[str(ay)] = max(kor, key=lambda k: (kor[k] if kor[k] == kor[k] else -9.0))
    seri, en_uzun, baslangic, cur, cur_bas = [], 0, None, 0, None
    for ay, lag in aylik.items():
        if lag is not None and lag != 0:
            cur += 1
            cur_bas = cur_bas or ay
            if cur > en_uzun:
                en_uzun, baslangic = cur, cur_bas
                seri = [ay for ay, lg in aylik.items() if lg is not None and lg != 0]
        else:
            cur, cur_bas = 0, None
    uyari = en_uzun >= min_ay
    return {"sinif": "uyari" if uyari else "temiz", "aylik_en_iyi_lag": aylik, "ardisik_kayma_ay": en_uzun, "kayma_baslangic": baslangic if uyari else None,
            "kayma_aylari": seri if uyari else [], "mesaj": (f"güç serisi ışınıma göre {en_uzun} ardışık ay kaymış görünüyor (başlangıç {baslangic}); kaynak zaman damgası "
                                                             "teyidi gerekir — veri KAYDIRILMADI" if uyari else "aylık gecikme 0; kayma imzası yok")}


def ac_asimi(power_kw: pd.Series, ac_limit_kw: float | None, *, tolerans: float = AC_TOLERANS) -> dict:
    """AC sınırı × (1+tolerans) üstü saatler. Sınır yoksa «uygulanamaz». Değer kırpılmaz."""
    if not ac_limit_kw or ac_limit_kw <= 0:
        return {"sinif": "uygulanamaz", "saat": 0, "mesaj": "AC sınırı bilinmiyor"}
    p = _utc(power_kw.astype(float)).dropna()
    ust = p[p > float(ac_limit_kw) * (1.0 + tolerans)]
    aylar = {str(k): int(v) for k, v in ust.groupby(ust.index.tz_convert(None).to_period("M")).size().items()} if len(ust) else {}
    return {"sinif": "uyari" if len(ust) else "temiz", "saat": len(ust), "maks_kw": (round(float(ust.max()), 1) if len(ust) else None),
            "maks_oran": (round(float(ust.max() / ac_limit_kw), 3) if len(ust) else None), "aylar": aylar, "ac_limit_kw": float(ac_limit_kw),
            "mesaj": (f"{len(ust)} saat AC sınırı %{tolerans * 100:.0f} toleransının üstünde (maks ×{ust.max() / ac_limit_kw:.3f}); AC sınırı/ölçüm kapsamı teyidi gerekir — "
                      "değer KIRPILMADI" if len(ust) else "AC sınırı aşımı yok")}


def kis_uretim_kaybi(power_kw: pd.Series, ghi: pd.Series, kwp: float, *, t_air: pd.Series | None = None, ghi_min_kwh: float = GHI_MIN_KWH,
                     verim_esik: float = VERIM_ESIK, aylar=(11, 12, 1, 2, 3)) -> dict:
    """Günlük: GHI toplamı ≥ ghi_min_kwh/m² iken özgül verim (kWh/kWp ÷ kWh/m²) < verim_esik → «güneş var üretim yok» günü.
    Yalnız imza: kar örtüsü, kesinti, kısıntı ayrıştırılamaz (işletme kaydı gerekir). Üretim DÜZELTİLMEZ."""
    p, g = _utc(power_kw.astype(float)), _utc(ghi.astype(float))
    j = pd.concat([p.rename("p"), g.rename("g")], axis=1, join="inner")
    j = j[j.index.month.isin(list(aylar))]
    if j.empty or not kwp:
        return {"sinif": "uygulanamaz", "gun": 0, "mesaj": "kış dönemi verisi yok"}
    gun = pd.DataFrame({"uretim_kwh": j["p"].groupby(j.index.date).sum(), "ghi_kwh_m2": j["g"].groupby(j.index.date).sum() / 1000.0})
    gun["verim"] = (gun["uretim_kwh"] / float(kwp)) / gun["ghi_kwh_m2"].replace(0, np.nan)
    if t_air is not None:
        t = _utc(t_air.astype(float))
        gun["t_min"] = t.groupby(t.index.date).min().reindex(gun.index)
    kayip = gun[(gun["ghi_kwh_m2"] >= ghi_min_kwh) & (gun["verim"] < verim_esik)]
    normal = gun[(gun["ghi_kwh_m2"] >= ghi_min_kwh) & (gun["verim"] >= verim_esik)]
    out = {"sinif": "uyari" if len(kayip) else "temiz", "gun": len(kayip), "incelenen_gun": int((gun["ghi_kwh_m2"] >= ghi_min_kwh).sum()),
           "gunler": [str(d) for d in kayip.index], "normal_verim_medyan": (round(float(normal["verim"].median()), 3) if len(normal) else None),
           "kayip_uretim_kwh_tahmini": None}
    if len(kayip) and len(normal):
        out["kayip_uretim_kwh_tahmini"] = round(float(((normal["verim"].median() * kayip["ghi_kwh_m2"] * float(kwp)) - kayip["uretim_kwh"]).sum()), 0)
    if t_air is not None and len(kayip):
        out["t_min_ort"] = round(float(kayip["t_min"].mean()), 1)
    out["mesaj"] = (f"{len(kayip)} günde güneş var üretim yok/çok düşük (verim < {verim_esik}); kar örtüsü/kesinti/kısıntı imzası — işletme kaydı teyidi gerekir, "
                    "üretim DÜZELTİLMEDİ" if len(kayip) else "kış üretim kaybı imzası yok")
    return out


def tara(power_kw: pd.Series, ghi: pd.Series, *, kwp: float, ac_limit_kw: float | None = None, t_air: pd.Series | None = None) -> dict:
    """Üç taramayı birlikte çalıştırır; genel sinif = herhangi biri uyari ise uyari. Yalnız rapor."""
    z, a, k = zaman_kaymasi(power_kw, ghi), ac_asimi(power_kw, ac_limit_kw), kis_uretim_kaybi(power_kw, ghi, kwp, t_air=t_air)
    return {"sinif": "uyari" if "uyari" in (z["sinif"], a["sinif"], k["sinif"]) else "temiz", "zaman_kaymasi": z, "ac_asimi": a, "kis_uretim_kaybi": k,
            "not": "uyarılar doğrulanmış arıza değildir; veri kaydırılmadı/kırpılmadı/düzeltilmedi"}
