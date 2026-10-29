"""Alt-saatlik (15 dk) tahmin — saatlikten indirgeme ve 15 dk fiyat kavramı yardımcıları.

Saatlik P50'yi 15 dakikaya indirirken gök açıklığı endeksi saat içinde sabit tutulur ve
açık gök 15 dk profiliyle çarpılır (enerji korunur, doğuş/batış eğriliği doğru). İsteğe bağlı
kt değişkenliği (bulutlu saatlerde) log-normal gürültüyle eklenir; kantiller aynı yolla indirilir.
Ters yönde `saatlige_topla`.

15 dk uzlaştırma (F-17 kavram düzeltmesi): yürürlükteki DUY m.110(2)'de EDM SAATLİK kalır; 15 dk DGP uzlaştırması
(m.91(2), Geçici 40) başlayınca yalnız FİYAT saat içi çeyreklerin en kötüsüne bağlanır: SMF_N = max(SMF_ç), SMF_P = min(SMF_ç).
15 dk başlamadıysa SMF_N = SMF_P = saatlik SMF. Başlangıç en erken 1.1.2027 (Geçici 40); fiilî tarih EPİAŞ/TEİAŞ duyurusuna bağlı.
`uzlastirma_15dk` bu tanıma göre yeniden yazıldı: 15 dk sapmayı 15 dk fiyatla uzlaştırmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def acik_gok_15dk(index_15: pd.DatetimeIndex, lat: float, lon: float, yukseklik: float = 0.0) -> pd.Series:
    konum = pvlib.location.Location(lat, lon, altitude=yukseklik, tz="UTC")
    orta = index_15 + pd.Timedelta(minutes=7, seconds=30)
    cs = konum.get_clearsky(orta, model="ineichen")
    cs.index = index_15
    return cs["ghi"].clip(lower=0.0)


def saatlikten_15dk(saatlik: pd.Series, lat: float, lon: float, degiskenlik: float = 0.0, seed: int = 0) -> pd.Series:
    """saatlik: GHI ya da güç (kt oranıyla ölçeklenir). degiskenlik: kt'ye eklenen log-normal σ (0 = düz)."""
    s = saatlik.dropna()
    idx15 = pd.date_range(s.index[0], s.index[-1] + pd.Timedelta(minutes=45), freq="15min", tz="UTC")
    cs15 = acik_gok_15dk(idx15, lat, lon)
    cs_saat = cs15.resample("h").mean()
    kt = (s / cs_saat.reindex(s.index).where(lambda x: x > 20)).clip(0, 1.3)
    kt15 = kt.reindex(idx15, method="ffill")
    if degiskenlik > 0:
        rng = np.random.default_rng(seed)
        g = np.exp(rng.normal(0, degiskenlik, len(idx15)))
        # bulutlu saatlerde (kt<0,8) uygula, enerji koruyacak şekilde saat içinde normalize
        g = pd.Series(g, index=idx15).where(kt15 < 0.8, 1.0)
        g = g / g.groupby(g.index.floor("h")).transform("mean")
        kt15 = (kt15 * g).clip(0, 1.3)
    out = (kt15 * cs15).clip(lower=0.0)
    # enerji koruma: saat toplamı saatlik değere eşitlensin (cs eğriliği sonrası küçük sapma)
    olcek = s / out.resample("h").mean().reindex(s.index).replace(0, np.nan)
    return (out * olcek.reindex(idx15, method="ffill").fillna(1.0)).fillna(0.0)


def saatlige_topla(seri_15: pd.Series, enerji: bool = False) -> pd.Series:
    r = seri_15.resample("h")
    return r.sum() if enerji else r.mean()


def smf_n_p(smf_ceyrek: pd.Series) -> pd.DataFrame:
    """Çeyrek SMF serisi (15 dk index) → saatlik SMF_N = max, SMF_P = min (DUY m.110(2))."""
    s = smf_ceyrek.dropna().astype(float)
    g = s.groupby(s.index.floor("h"))
    return pd.DataFrame({"smf_n": g.max(), "smf_p": g.min()})


def uzlastirma_15dk(uretim_mwh_saat: pd.Series, program_mwh_saat: pd.Series, ptf: pd.Series, smf_ceyrek: pd.Series,
                    yon=None, segment: str | None = None) -> pd.DataFrame:
    """15 dk DGP uzlaştırması BAŞLADIĞINDA: EDM saatlik (üretim − program), fiyat çeyreklerin en kötüsü (SMF_N/SMF_P).
    smf_ceyrek saatlik verilirse SMF_N = SMF_P = SMF (15 dk başlamamış hâl; F-02 ile aynı sonuç)."""
    from pvquant.ext.turkiye import dengesizlik as d
    np_ = smf_n_p(smf_ceyrek)
    idx = uretim_mwh_saat.index.intersection(program_mwh_saat.index)
    smf_saat = np_["smf_p"].reindex(idx).fillna(np_["smf_n"].reindex(idx))
    return d.saatlik(program_mwh_saat.loc[idx], uretim_mwh_saat.loc[idx], ptf.reindex(idx), smf_saat,
                     yon=yon, segment=segment, smf_n=np_["smf_n"].reindex(idx), smf_p=np_["smf_p"].reindex(idx))
