"""Ortak veri sözleşmesi ve yardımcılar.

Her kaynak modülü aynı çerçeveyi döndürür ki harman, nowcast ve entegrasyon
katmanı kaynağı umursamasın. Işınım ayrıştırma (GHI → DNI/DHI) yalnız kaynağın
kendisi vermediğinde uygulanır; UI'da yöntem adı geçmez (Gizlilik Anayasası).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pvlib

KOLONLAR = ["ghi", "dni", "dhi", "temp_air", "wind_speed_10m", "cloud_cover"]


@dataclass(frozen=True)
class KaynakBilgisi:
    """Bir veri kaynağının kimliği ve lisansı — atıf modülü bunu okur."""

    ad: str            # ör. "ECMWF Open Data (IFS)"
    kurum: str         # ör. "ECMWF"
    lisans: str        # ör. "CC BY 4.0"
    lisans_url: str
    veri_url: str
    ticari_kullanim: bool
    not_: str = ""


@dataclass
class MeteoCerceve:
    """Saatlik UTC meteoroloji çerçevesi.

    Attributes:
        df: index = saatlik UTC DatetimeIndex; kolonlar KOLONLAR alt kümesi.
        latitude/longitude: sorgulanan nokta.
        kaynak: kaynak kimliği (lisans/atıf için).
        kosu_zamani: NWP koşusunun başlangıcı (UTC) ya da None (arşiv/uydu).
        uyeler: ensemble üyeleri varsa {üye_no: df} — yalnız ghi kolonu şart.
    """

    df: pd.DataFrame
    latitude: float
    longitude: float
    kaynak: KaynakBilgisi
    kosu_zamani: pd.Timestamp | None = None
    uyeler: dict[int, pd.DataFrame] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.df.index.tz is None:
            self.df.index = self.df.index.tz_localize("UTC")
        else:
            self.df.index = self.df.index.tz_convert("UTC")
        eksik = [k for k in ("ghi", "temp_air", "wind_speed_10m") if k not in self.df.columns]
        if eksik:
            raise ValueError(f"MeteoCerceve zorunlu kolonlar eksik: {eksik}")
        if "dni" not in self.df.columns or "dhi" not in self.df.columns:
            self.df = ayristir(self.df, self.latitude, self.longitude)
        self.df = self.df.sort_index()

    def kes(self, baslangic: pd.Timestamp | None = None, bitis: pd.Timestamp | None = None) -> "MeteoCerceve":
        return MeteoCerceve(self.df.loc[baslangic:bitis].copy(), self.latitude, self.longitude,
                            self.kaynak, self.kosu_zamani, self.uyeler)


def saatlik_utc_index(baslangic: pd.Timestamp, saat: int) -> pd.DatetimeIndex:
    b = pd.Timestamp(baslangic)
    b = b.tz_localize("UTC") if b.tz is None else b.tz_convert("UTC")
    return pd.date_range(b.floor("h"), periods=saat, freq="h", tz="UTC")


def gunes_konumu(index: pd.DatetimeIndex, lat: float, lon: float) -> pd.DataFrame:
    """Saat ortası için zenit/azimut (saatlik ortalama ışınıma uygun)."""
    orta = index + pd.Timedelta(minutes=30)
    return pvlib.solarposition.get_solarposition(orta, lat, lon)


def acik_gok_ghi(index: pd.DatetimeIndex, lat: float, lon: float, yukseklik: float = 0.0) -> pd.Series:
    """Açık gök GHI (saatlik). Nowcast ve harman için 'gök açıklığı endeksi' paydası."""
    konum = pvlib.location.Location(lat, lon, altitude=yukseklik, tz="UTC")
    orta = index + pd.Timedelta(minutes=30)
    cs = konum.get_clearsky(orta, model="ineichen")
    cs.index = index
    return cs["ghi"].clip(lower=0.0)


def ayristir(df: pd.DataFrame, lat: float, lon: float) -> pd.DataFrame:
    """GHI'dan DNI/DHI türet (kaynak vermediğinde). Gece sıfır."""
    df = df.copy()
    konum = gunes_konumu(df.index, lat, lon)
    zenit = konum["apparent_zenith"].values
    doy = df.index.dayofyear.values
    ghi = df["ghi"].clip(lower=0.0).values
    out = pvlib.irradiance.erbs(ghi, zenit, doy)
    dni = np.asarray(out["dni"]); dhi = np.asarray(out["dhi"])
    gece = zenit >= 90
    dni[gece] = 0.0; dhi[gece] = 0.0
    df["dni"] = dni; df["dhi"] = dhi
    return df


def gok_acikligi(ghi: pd.Series, lat: float, lon: float) -> pd.Series:
    """kt = GHI / GHI_açık; açık gök < 20 W/m² olan saatlerde NaN (gece/alacakaranlık)."""
    cs = acik_gok_ghi(ghi.index, lat, lon)
    kt = ghi / cs.where(cs >= 20.0)
    return kt.clip(lower=0.0, upper=1.3)


def biriktirilmisten_saatlik(deger_J: pd.Series, adim_saat: pd.Series | int) -> pd.Series:
    """Biriktirilmiş enerji (J/m², koşu başından) → aralık ortalaması W/m².

    ECMWF ssrd ve GFS DSWRF (bazı adımlarda) biriktirilmiş gelir; ardışık farkı
    adım süresine bölerek ortalama güç elde edilir.
    """
    fark = deger_J.diff()
    fark.iloc[0] = deger_J.iloc[0]
    if isinstance(adim_saat, int):
        sn = adim_saat * 3600.0
        return (fark / sn).clip(lower=0.0)
    return (fark / (adim_saat * 3600.0)).clip(lower=0.0)


def sifirlamali_ortalamadan_aralik(ort: pd.Series, kosu: pd.Timestamp, pencere_saat: int = 6) -> pd.Series:
    """v2.382 — GFS/GEFS DSWRF: değer, son `pencere_saat`'lik sıfırlamadan bu yana ortalamadır
    (GRIB stepRange 0-4, 0-5, 0-6, 6-7, 6-8 …; NOMADS gfs.pgrb2.0p25 ve gefs pgrb2s, 01.10.2026'da okundu).
    Ardışık adımlardan (önceki, t] aralık ortalamasına çevrilir; sonuç ARALIK SONU damgalıdır
    (kaba_adimi_saatlige_indir'in beklediği biçim). Eski yol değeri doğrudan (önceki, t] ortalaması sayıyordu:
    pencerenin ikinci yarısında sabah/akşam rampası düzleşiyordu."""
    ort = ort.dropna().sort_index()
    if ort.empty:
        return ort
    adim = np.asarray((ort.index - kosu) / pd.Timedelta(hours=1), dtype=float)
    deg = ort.to_numpy(dtype=float)
    out = np.empty_like(deg)
    for i, (s, v) in enumerate(zip(adim, deg)):
        bas = pencere_saat * np.floor((s - 1e-9) / pencere_saat)          # bu adımın sıfırlama başlangıcı
        onceki = adim[i - 1] if i > 0 else bas
        if i == 0 or onceki <= bas + 1e-9:                                  # pencerenin ilk adımı: (bas, s]
            out[i] = v
        else:                                                               # aynı pencere: farktan aralık
            out[i] = (v * (s - bas) - deg[i - 1] * (onceki - bas)) / (s - onceki)
    return pd.Series(np.clip(out, 0.0, None), index=ort.index)


def kaba_adimi_saatlige_indir(seri: pd.Series, lat: float, lon: float, hedef_index: pd.DatetimeIndex) -> pd.Series:
    """3–6 saatlik ortalama GHI'yı saatliğe indirir: gök açıklığı endeksini sabit tutup
    açık gök profiliyle çarpar (sabah/akşam eğriliği korunur, enerji korunur).

    v2.382: `seri` ARALIK SONU damgalıdır (NWP birikimi: t_i değeri (t_{i-1}, t_i] ortalaması);
    `hedef_index` sözleşme gereği SAAT BAŞI damgalıdır ([h, h+1) ortalaması). (t_{i-1}, t_i]
    aralığının saatleri h ∈ [t_{i-1}, t_i) olur. Eski maske (t_{i-1} < h ≤ t_i) aralığı bir
    saat ileri atıyordu: ECMWF/ICON/GFS GHI'si bir saat gecikmeliydi (sabah eksik, akşam fazla)."""
    seri = seri.dropna()
    if seri.empty:
        return pd.Series(np.nan, index=hedef_index)
    cs_h = acik_gok_ghi(hedef_index, lat, lon)
    # her kaba aralığın (t_i-1, t_i] saatleri
    kt_saat = pd.Series(np.nan, index=hedef_index)
    onceki = None
    for t, v in seri.items():
        if onceki is None:
            onceki = t - (seri.index[1] - seri.index[0] if len(seri) > 1 else pd.Timedelta(hours=1))
        maske = (hedef_index >= onceki) & (hedef_index < t)
        cs_ort = cs_h[maske].mean()
        kt = (v / cs_ort) if cs_ort and cs_ort > 20 else 0.0
        kt_saat[maske] = min(max(kt, 0.0), 1.3)
        onceki = t
    return (kt_saat.ffill() * cs_h).clip(lower=0.0)


def ruzgar_hizi(u: pd.Series, v: pd.Series) -> pd.Series:
    return np.sqrt(u.astype(float) ** 2 + v.astype(float) ** 2)


def en_yakin_grid(lat: float, lon: float, adim: float) -> tuple[float, float]:
    return round(lat / adim) * adim, round(lon / adim) * adim
