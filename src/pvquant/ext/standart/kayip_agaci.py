"""PVsyst tarzı kayıp ağacı — GHI'dan şebekeye adım adım enerji ve kayıp yüzdesi.

Adımlar (PVsyst 'loss diagram' sırası):
  GHI → [transpozisyon] → POA_global → [gölge (yakın/ufuk)] → [IAM] → [soiling] → [spektral]
  → etkin ışınım → [STC dönüşüm: nominal DC] → [ışınım seviyesi] → [sıcaklık] → [modül kalitesi/LID]
  → [uyumsuzluk (mismatch)] → [DC kablo] → DC → [inverter verimi] → [kırpma/clipping] → [AC kablo/trafo]
  → [kullanılabilirlik] → [kısıntı/curtailment] → şebeke.
Her adım ya ölçülmüş/simüle enerji (kWh) ya da kayıp oranıyla verilir; eksik adım 'uygulanmadı' sayılır.
Çıktı: tablo (adım, giren, çıkan, kayıp kWh, kayıp %) + şelale verisi (panelin 'selale' grafiği için).
Işınım adımları kWh/m² × alan × STC verimiyle enerjiye çevrilir (PVsyst'in yaptığı gibi 'nominal DC').
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib

SIRA = ["transpozisyon", "golge", "iam", "soiling", "spektral", "isinim_seviyesi", "sicaklik", "modul_kalitesi",
        "uyumsuzluk", "dc_kablo", "inverter", "kirpma", "ac_kablo", "kullanilabilirlik", "kisinti"]
ETIKET = {"transpozisyon": "Düzleme aktarma kazancı/kaybı", "golge": "Gölge", "iam": "Geliş açısı (IAM)", "soiling": "Kirlenme",
          "spektral": "Spektral", "isinim_seviyesi": "Düşük ışınım verimi", "sicaklik": "Sıcaklık", "modul_kalitesi": "Modül kalitesi / LID",
          "uyumsuzluk": "Uyumsuzluk", "dc_kablo": "DC kablo", "inverter": "Evirici verimi", "kirpma": "Kırpma", "ac_kablo": "AC kablo / trafo",
          "kullanilabilirlik": "Kullanılabilirlik", "kisinti": "Şebeke kısıntısı"}


@dataclass
class AgacSonucu:
    tablo: pd.DataFrame
    selale: list[dict]
    ghi_kwh_m2: float; poa_kwh_m2: float; nominal_dc_kwh: float; sebeke_kwh: float

    def pr(self) -> float:
        return self.sebeke_kwh / self.nominal_dc_kwh * (self.nominal_dc_kwh / max(self.nominal_dc_kwh, 1e-9)) if self.nominal_dc_kwh else np.nan


def transpozisyon(ghi: pd.Series, dni: pd.Series, dhi: pd.Series, lat: float, lon: float, tilt: float, azimuth: float,
                  albedo: float = 0.2) -> pd.Series:
    """Saatlik POA global (Perez). azimuth: 180 = güney."""
    orta = ghi.index + pd.Timedelta(minutes=30)
    sp = pvlib.solarposition.get_solarposition(orta, lat, lon)
    dni_extra = pvlib.irradiance.get_extra_radiation(orta)
    am = pvlib.atmosphere.get_relative_airmass(sp["apparent_zenith"].values)
    poa = pvlib.irradiance.get_total_irradiance(tilt, azimuth, sp["apparent_zenith"].values, sp["azimuth"].values,
                                                dni.values, ghi.values, dhi.values, dni_extra=dni_extra.values, airmass=am,
                                                albedo=albedo, model="perez")
    return pd.Series(np.nan_to_num(np.asarray(poa["poa_global"], float)), index=ghi.index).clip(lower=0)


def sicaklik_kaybi(poa: pd.Series, temp_air: pd.Series, wind: pd.Series, gamma: float = -0.0035, u0: float = 25.0, u1: float = 6.84) -> float:
    """Işınım-ağırlıklı sıcaklık kayıp oranı: 1 − Σ G(1+γ(Tc−25)) / Σ G."""
    tc = temp_air + poa / (u0 + u1 * wind)
    w = poa.clip(lower=0)
    return float(1 - (w * (1 + gamma * (tc - 25))).sum() / max(w.sum(), 1e-9))


def isinim_seviyesi_kaybi(poa: pd.Series, k: float = 0.02) -> float:
    """Düşük ışınımda verim düşüşü: η(G)/η_STC ≈ 1 + k·ln(G/1000) (basit PVsyst benzeri), ağırlıklı."""
    w = poa.clip(lower=1.0)
    eta = 1 + k * np.log(w / 1000.0)
    return float(1 - (w * eta.clip(0.5, 1.05)).sum() / w.sum())


def agac(ghi_kwh_m2: float, poa_kwh_m2: float, alan_m2: float, eta_stc: float, oranlar: dict[str, float],
         sebeke_kwh: float | None = None) -> AgacSonucu:
    """oranlar: adım → kayıp oranı (pozitif kayıp; transpozisyon için kazanç negatif verilebilir; verilmeyen adım 0).
    sebeke_kwh verilirse son adıma 'açıklanamayan' kalıntı eklenir (ölçülen ile zincir farkı)."""
    nominal = poa_kwh_m2 * alan_m2 * eta_stc
    satir = [{"adim": "GHI (yatay)", "etiket": "Yatay ışınım", "giren": ghi_kwh_m2 * alan_m2 * eta_stc, "cikan": ghi_kwh_m2 * alan_m2 * eta_stc, "kayip_kwh": 0.0, "kayip_pct": 0.0}]
    e = ghi_kwh_m2 * alan_m2 * eta_stc
    # transpozisyon: POA/GHI oranından
    tr = 1 - poa_kwh_m2 / ghi_kwh_m2 if ghi_kwh_m2 > 0 else 0.0
    oranlar = dict(oranlar); oranlar.setdefault("transpozisyon", tr)
    for ad in SIRA:
        o = float(oranlar.get(ad, 0.0))
        cik = e * (1 - o)
        satir.append({"adim": ad, "etiket": ETIKET[ad], "giren": e, "cikan": cik, "kayip_kwh": e - cik, "kayip_pct": o * 100})
        e = cik
    if sebeke_kwh is not None and e > 0:
        o = 1 - sebeke_kwh / e
        satir.append({"adim": "aciklanamayan", "etiket": "Açıklanamayan kalıntı", "giren": e, "cikan": sebeke_kwh, "kayip_kwh": e - sebeke_kwh, "kayip_pct": o * 100})
        e = sebeke_kwh
    tablo = pd.DataFrame(satir)
    selale = [{"ad": r["etiket"], "deger": -r["kayip_kwh"], "tip": "kayip" if r["kayip_kwh"] > 0 else "kazanc"} for _, r in tablo.iloc[1:].iterrows()]
    selale.insert(0, {"ad": "Nominal (yatay)", "deger": float(tablo.iloc[0]["cikan"]), "tip": "baslangic"})
    selale.append({"ad": "Şebekeye", "deger": float(e), "tip": "sonuc"})
    return AgacSonucu(tablo, selale, ghi_kwh_m2, poa_kwh_m2, nominal, float(e))


def oranlari_saatlikten(ghi: pd.Series, dni: pd.Series, dhi: pd.Series, temp_air: pd.Series, wind: pd.Series, lat: float, lon: float,
                        tilt: float, azimuth: float, gamma: float = -0.0035, iam_b: float = 0.05, soiling: float = 0.02,
                        spektral: float = 0.01, golge: float = 0.01, modul_kalitesi: float = 0.01, uyumsuzluk: float = 0.01,
                        dc_kablo: float = 0.01, inverter: float = 0.02, kirpma: float = 0.0, ac_kablo: float = 0.01,
                        kullanilabilirlik: float = 0.01, kisinti: float = 0.0) -> tuple[dict[str, float], float, float]:
    """Saatlik meteo'dan hesaplanan adımlar (transpozisyon, IAM, ışınım seviyesi, sıcaklık) + verilen sabit oranlar.
    Döner: (oranlar, GHI kWh/m², POA kWh/m²)."""
    poa = transpozisyon(ghi, dni, dhi, lat, lon, tilt, azimuth)
    orta = ghi.index + pd.Timedelta(minutes=30)
    sp = pvlib.solarposition.get_solarposition(orta, lat, lon)
    aoi = pvlib.irradiance.aoi(tilt, azimuth, sp["apparent_zenith"].values, sp["azimuth"].values)
    iam = np.nan_to_num(pvlib.iam.ashrae(aoi, b=iam_b), nan=0.0)
    beam_poa = np.clip(dni.values * np.cos(np.radians(aoi)), 0, None)
    iam_kayip = float(1 - ((beam_poa * iam).sum() + (poa.values - beam_poa).sum()) / max(poa.values.sum(), 1e-9))
    oranlar = {"iam": max(iam_kayip, 0.0), "golge": golge, "soiling": soiling, "spektral": spektral,
               "isinim_seviyesi": isinim_seviyesi_kaybi(poa), "sicaklik": sicaklik_kaybi(poa, temp_air, wind, gamma),
               "modul_kalitesi": modul_kalitesi, "uyumsuzluk": uyumsuzluk, "dc_kablo": dc_kablo, "inverter": inverter,
               "kirpma": kirpma, "ac_kablo": ac_kablo, "kullanilabilirlik": kullanilabilirlik, "kisinti": kisinti}
    return oranlar, float(ghi.clip(lower=0).sum() / 1000), float(poa.sum() / 1000)
