"""Uzlaştırma kalemleri simülatörü — EDT (DUY m.110(1)-(2)) ve KÜPST (m.110(3)-(6)); kural TARİHE göre (kurallar.py, F-01).

Saatlik (uzlaştırma dönemi u; 15 dk başlayana kadar saat):
  EDM = gerçekleşen − piyasa pozisyonu (pozisyon verilmezse KGÜP; MWh).
  2025 rejimi (≤31.12.2025): P(−) = max(PTF, SMF)·(1+k); P(+) = min(PTF, SMF)·(1−l); k = l = 0,03.
  2026 rejimi (≥1.1.2026): P(−) = max(V, PTF, SMF_N)·(1+k_yön); max(PTF, SMF_N) = AFL ise P(−) = AFL·1,05·(1+k_yön) [AFL dalı].
                           P(+) = min(PTF, SMF_P)·(1−l_yön); min(PTF, SMF_P) < V ise P(+) = −B·(1+l_yön) [B dalı: fazla üretim BORÇ].
                           k/l sistem yönüne göre (Karar 14030); yön verisi yoksa hesap «yon_eksik» durumuyla DURUR — yön SMF>PTF'den çıkarılmaz.
  EDT(−) = |EDM⁻|·P(−) (katılımcı öder, pozitif yazılır); EDT(+) = EDM⁺·P(+) (katılımcı alır; negatifse öder).
  Programa göre kayıp (karne dili, C §2.2) = eksikte |EDM|·(P(−) − PTF), fazlada EDM·(PTF − P(+)) → «dengesizlik_maliyeti».
  Referans (kusursuz program) geliri = gerçekleşen·PTF; gerçekleşen gelir = pozisyon·PTF + EDT(+) − EDT(−).
KÜPST: UDÜPS = |UEVM − BUDÜP| (≤31.10.2026) ya da |(UEVM − UEÇM) − BUDÜP| (1.11.2026'dan, Karar 14907); KÜPSM = max(0, UDÜPS − m·BUDÜP);
  KÜPST = KÜPSM·max(taban 750; PTF; SMF)·n. m/n segment, tarih ve aylık arıza sayısına göre (kurallar.py). BUDÜP verilmezse KGÜP.
  m/n doğrulanamıyorsa (segment seçilmemiş, 2025 iletime bağlı lisanssız) KÜPST NaN + durum «kupst_hesaplanamaz» — 0 YAZILMAZ.
Aylık (m.110(1)): 2025 tek net EDT; 1.1–18.10.2026 EDTA = max(ΣEDT(+);0), EDTB = ΣEDT(−) − min(ΣEDT(+);0);
  19.10.2026'dan dönem bazında (B borcu alacakla netleşmez): EDTA = Σ max(EDT(+);0), EDTB = ΣEDT(−) − Σ min(EDT(+);0).
EDT ve KÜPST hiçbir yerde tek sayı olarak sunulmaz; toplam yalnız «uzlaştırma kalemleri toplamı» (toplam_maliyet = kayıp + KÜPST).
DSG: portföy sapmaları saatlik toplanır (dsg_netlestir) — %5 üye eşiği ve KÜPST ayrımı F-08 (sonraki paket), bu görünüm GÖSTERGEDİR.
Teminat: son 3 ayın en yüksek aylık EDT(−) × risk katsayısı — sadeleştirilmiş gösterge, Teminat U&E ile doğrulanmadı.
Kıyas: iki program (ör. referans vs PVQuant) → aylık kalem farkı (kolon adı 'kurtarilan_tl' API sözleşmesidir; ekranda «referansa göre fark»).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from pvquant.ext.turkiye import kurallar as kr


@dataclass
class Katsayilar:
    """Santral bazında KÜPST GEÇERSİZ KILMA (params_json.kupst_n / kupst_tolerans). None → kural tablosu (kurallar.py).
    k/l artık burada değil: sistem yönüne ve tarihe göre kural tablosundan gelir."""
    kupst_n: float | None = None
    kupst_tolerans: float | None = None
    kupst_kgup_yukumlu: bool = True


def _hizala(*seriler: pd.Series) -> pd.DatetimeIndex:
    idx = seriler[0].dropna().index
    for s in seriler[1:]:
        idx = idx.intersection(s.dropna().index)
    return idx


def _yon_serisi(yon, idx: pd.DatetimeIndex) -> pd.Series:
    if yon is None:
        return pd.Series([None] * len(idx), index=idx, dtype=object)
    if isinstance(yon, str):
        return pd.Series([kr.yon_normalize(yon)] * len(idx), index=idx, dtype=object)
    return pd.Series([kr.yon_normalize(v) for v in yon.reindex(idx)], index=idx, dtype=object)


def birim_fiyatlar(ptf: pd.Series, smf: pd.Series, yon, *, smf_n: pd.Series | None = None, smf_p: pd.Series | None = None,
                   segment: str | None = None, karsi_olgu: str | None = None) -> pd.DataFrame:
    """SAF. Saat başına P(−), P(+), dal etiketleri, k/l ve kural sürümü. yon: Series|str|None ('acik'|'fazla'|'dengede')."""
    idx = pd.DatetimeIndex(ptf.index)
    P = ptf.astype(float); S = smf.astype(float).reindex(idx)
    SN = (smf_n.astype(float).reindex(idx) if smf_n is not None else S).fillna(S)
    SP = (smf_p.astype(float).reindex(idx) if smf_p is not None else S).fillna(S)
    prm = kr.parametre_cercevesi(idx, segment, karsi_olgu=karsi_olgu)
    y = _yon_serisi(yon, idx)
    eski = prm["rejim"].eq("2025").values
    # k/l: 2025 sabit 0,03; 2026 yöne göre; yön yoksa NaN
    k = np.where(eski, 0.03, np.nan).astype(float); l = k.copy()
    for yn in kr.YONLER:
        m = (~eski) & (y.values == yn)
        k[m] = prm.loc[m, f"k_{yn}"].values; l[m] = prm.loc[m, f"l_{yn}"].values
    V = prm["V"].values.astype(float); B = prm["B"].values.astype(float); AFL = prm["AFL"].values.astype(float)
    mx = np.maximum(P.values, SN.values); mn = np.minimum(P.values, SP.values)
    # P(−)
    p_neg = np.where(eski, mx * (1 + k), np.maximum(V, mx) * (1 + k))
    afl_dal = (~eski) & np.isfinite(AFL) & (mx >= AFL)
    p_neg = np.where(afl_dal, AFL * 1.05 * (1 + k), p_neg)
    dal_neg = np.where(eski, "2025", np.where(afl_dal, "AFL", np.where(mx < V, "V", "normal")))
    # P(+)
    b_dal = (~eski) & (mn < V)
    p_poz = np.where(eski, mn * (1 - l), np.where(b_dal, -B * (1 + l), mn * (1 - l)))
    dal_poz = np.where(eski, "2025", np.where(b_dal, "B", "normal"))
    yon_eksik = (~eski) & pd.isna(y.values)
    p_neg = np.where(yon_eksik, np.nan, p_neg); p_poz = np.where(yon_eksik, np.nan, p_poz)
    return pd.DataFrame({"ptf": P, "smf": S, "smf_n": SN, "smf_p": SP, "yon": y.values, "k": k, "l": l,
                         "p_neg": p_neg, "p_poz": p_poz, "dal_neg": dal_neg, "dal_poz": dal_poz,
                         "rejim": prm["rejim"].values, "kural_surumu": prm["surum"].values, "V": V, "B": B, "AFL": AFL,
                         "yon_eksik": yon_eksik, "belirsiz_2027": prm["belirsiz_2027"].values}, index=idx)


def saatlik(kgup_mwh: pd.Series, gerceklesen_mwh: pd.Series, ptf: pd.Series, smf: pd.Series, kat: Katsayilar | None = None, *,
            yon=None, segment: str | None = None, ariza_sayisi: int = 0, smf_n: pd.Series | None = None, smf_p: pd.Series | None = None,
            pozisyon_mwh: pd.Series | None = None, budup_mwh: pd.Series | None = None, uecm_mwh: pd.Series | None = None,
            portfoy: bool = False, karsi_olgu: str | None = None) -> pd.DataFrame:
    """Saatlik uzlaştırma kalemleri. Girdiler MWh; index saat dilimli (UTC önerilir) — kural teslim gününe (İstanbul) göre seçilir.
    yon: sistem yönü (Series/str; 'acik'|'fazla'|'dengede' ya da EPİAŞ metni). 2026 saatlerinde yön yoksa EDT NaN ve durum 'yon_eksik'."""
    kat = kat or Katsayilar()
    idx = _hizala(kgup_mwh, gerceklesen_mwh, ptf, smf)
    K, G, P, S = (x.loc[idx].astype(float) for x in (kgup_mwh, gerceklesen_mwh, ptf, smf))
    poz_ser = pozisyon_mwh.reindex(idx).astype(float).fillna(K) if pozisyon_mwh is not None else K
    f = birim_fiyatlar(P, S, yon, smf_n=smf_n, smf_p=smf_p, segment=segment, karsi_olgu=karsi_olgu)
    edm = G - poz_ser
    poz, neg = edm.clip(lower=0), (-edm).clip(lower=0)
    edt_poz = poz * f["p_poz"]            # katılımcı alır (negatifse öder)
    edt_neg = neg * f["p_neg"]            # katılımcı öder
    program_gelir = poz_ser * P
    gerceklesen_gelir = program_gelir + edt_poz - edt_neg
    referans_gelir = G * P
    kayip = referans_gelir - gerceklesen_gelir      # = poz·(PTF − P(+)) + neg·(P(−) − PTF)
    # --- KÜPST ---
    prm = kr.parametre_cercevesi(idx, segment, ariza_sayisi, portfoy, karsi_olgu=karsi_olgu)
    m = prm["m"].values.astype(float); n = prm["n"].values.astype(float)
    if kat.kupst_tolerans is not None:
        m = np.full(len(idx), float(kat.kupst_tolerans))
    if kat.kupst_n is not None:
        n = np.full(len(idx), float(kat.kupst_n))
    budup = budup_mwh.reindex(idx).astype(float).fillna(K) if budup_mwh is not None else K
    uecm = uecm_mwh.reindex(idx).astype(float).fillna(0.0) if uecm_mwh is not None else pd.Series(0.0, index=idx)
    net = prm["net_sapma"].values
    udups = np.where(net, np.abs((G.values - uecm.values) - budup.values), np.abs(G.values - budup.values))
    kupsm = np.clip(udups - m * budup.values, 0.0, None)
    kupst = kupsm * np.maximum.reduce([prm["taban"].values.astype(float), P.values, S.values]) * n
    if not kat.kupst_kgup_yukumlu:
        kupst = np.zeros(len(idx)); n = np.zeros(len(idx))
    kupst_yok = np.isnan(n) | np.isnan(m)
    durum = np.where(f["yon_eksik"].values, "yon_eksik", np.where(kupst_yok, "kupst_hesaplanamaz", "ok"))
    kupst_s = pd.Series(kupst, index=idx)
    toplam = kayip + kupst_s
    return pd.DataFrame({"kgup": K, "gerceklesen": G, "pozisyon": poz_ser, "sapma": edm, "ptf": P, "smf": S,
                         "yon": f["yon"], "k": f["k"], "l": f["l"], "p_neg": f["p_neg"], "p_poz": f["p_poz"],
                         "dal": np.where(edm.values < 0, f["dal_neg"].values, np.where(edm.values > 0, f["dal_poz"].values, "")),
                         "edt_neg": edt_neg, "edt_poz": edt_poz, "edt_net": edt_poz - edt_neg,
                         "pozitif_gelir": edt_poz, "negatif_gider": edt_neg,          # eski kolon adları (API/rapor uyumu)
                         "referans_gelir": referans_gelir, "gerceklesen_gelir": gerceklesen_gelir,
                         "dengesizlik_maliyeti": kayip, "kupsm": kupsm, "kupst_m": m, "kupst_n": n, "kupst": kupst_s,
                         "toplam_maliyet": toplam, "kural_surumu": f["kural_surumu"], "rejim": f["rejim"], "durum": durum,
                         "belirsiz_2027": f["belirsiz_2027"]})


def _toplama(grup: pd.DataFrame) -> tuple[float, float]:
    """m.110(1) aylık toplama; saat satırının toplama kuralına göre (ay içinde iki kural karışabilir: Ekim 2026)."""
    edta = edtb = 0.0
    for kural_adi, g in grup.groupby("toplama_kurali", sort=False):
        poz, neg = g["edt_poz"].fillna(0.0), g["edt_neg"].fillna(0.0)
        if kural_adi == "edta_ayrik":
            edta += float(poz.clip(lower=0).sum()); edtb += float(neg.sum() - poz.clip(upper=0).sum())
        elif kural_adi == "edta_net":
            edta += float(max(poz.sum(), 0.0)); edtb += float(neg.sum() - min(poz.sum(), 0.0))
        else:   # 2025: tek net EDT_f
            netto = float(poz.sum() - neg.sum()); edta += max(netto, 0.0); edtb += max(-netto, 0.0)
    return edta, edtb


def aylik_karne(saatlik_df: pd.DataFrame, tz: str = "Europe/Istanbul") -> pd.DataFrame:
    """Piyasa ayı İstanbul saatiyle: UTC index önce yerel saate çevrilir (1 Temmuz 00:00 IST = 30 Haziran 21:00 UTC).
    EDTA/EDTB (m.110(1)) ayrı; kayıp (dengesizlik_maliyeti) ve KÜPST ayrı; toplam_maliyet = kayıp + KÜPST."""
    df = saatlik_df.copy(); df.index = df.index.tz_convert(tz)
    if "toplama_kurali" not in df:
        yerel_gun = pd.Series(df.index.date, index=df.index)
        df["toplama_kurali"] = [kr.edt_kurali(g).toplama for g in yerel_gun]
    a = df.resample("ME").agg({"gerceklesen": "sum", "sapma": lambda x: x.abs().sum(), "referans_gelir": "sum",
                               "dengesizlik_maliyeti": "sum", "kupst": "sum", "toplam_maliyet": "sum",
                               "edt_neg": "sum", "edt_poz": "sum"})
    top = df.groupby(pd.Grouper(freq="ME")).apply(_toplama) if len(df) else pd.Series(dtype=object)
    a["edta"] = [t[0] for t in top.reindex(a.index)] if len(a) else []
    a["edtb"] = [t[1] for t in top.reindex(a.index)] if len(a) else []
    sayim = df.groupby(pd.Grouper(freq="ME"))["durum"] if "durum" in df else None
    a["hesaplanamayan_saat"] = sayim.apply(lambda s: int((s != "ok").sum())).reindex(a.index).fillna(0).astype(int) if sayim is not None else 0
    a["kural_surumu"] = df.groupby(pd.Grouper(freq="ME"))["kural_surumu"].agg(lambda s: " | ".join(sorted(set(s)))).reindex(a.index) if "kural_surumu" in df else ""
    a["sapma_orani"] = a["sapma"] / a["gerceklesen"].replace(0, np.nan)
    a["maliyet_gelir_orani"] = a["toplam_maliyet"] / a["referans_gelir"].replace(0, np.nan)
    a["tl_per_mwh"] = a["toplam_maliyet"] / a["gerceklesen"].replace(0, np.nan)
    return a


def kiyas(kgup_a: pd.Series, kgup_b: pd.Series, gerceklesen: pd.Series, ptf: pd.Series, smf: pd.Series,
          kat: Katsayilar | None = None, ad_a: str = "referans", ad_b: str = "pvquant", **ek) -> pd.DataFrame:
    """İki program (ör. referans «dün aynı saat» vs PVQuant P50) → aylık kalem toplamı ve FARK ('kurtarilan_tl' sütun adı sözleşmedir;
    anlamı «a programına göre b programının farkı»; vaat değil, varsayımsal kıyastır)."""
    A = aylik_karne(saatlik(kgup_a, gerceklesen, ptf, smf, kat, **ek)); B = aylik_karne(saatlik(kgup_b, gerceklesen, ptf, smf, kat, **ek))
    out = pd.DataFrame({f"{ad_a}_tl": A["toplam_maliyet"], f"{ad_b}_tl": B["toplam_maliyet"]})
    out["kurtarilan_tl"] = out[f"{ad_a}_tl"] - out[f"{ad_b}_tl"]
    out["kurtarilan_oran"] = out["kurtarilan_tl"] / out[f"{ad_a}_tl"].replace(0, np.nan)
    return out


def dsg_netlestir(programlar: dict[str, pd.Series], gerceklesenler: dict[str, pd.Series]) -> tuple[pd.Series, pd.Series]:
    """Eski gösterge: saatlik KGÜP ve gerçekleşen toplamları (eşiksiz). Yürürlükteki hesap için dsg_saatlik() kullanılır."""
    K = pd.concat(programlar.values(), axis=1).sum(axis=1); G = pd.concat(gerceklesenler.values(), axis=1).sum(axis=1)
    return K, G


def dsg_saatlik(programlar: dict[str, pd.Series], gerceklesenler: dict[str, pd.Series], ptf: pd.Series, smf: pd.Series, *,
                yon=None, segmentler: dict[str, str | None] | None = None, pozisyonlar: dict[str, pd.Series] | None = None,
                esik_oran: float | None = None, ariza_sayilari: dict[str, int] | None = None) -> dict:
    """F-08 (v2.502) — DSG netleşmesi, DUY m.111(3)-(5) + Karar 13869: her üye için PH = max(UEVM, satış) (saf satıcı GES: max(A, F));
    üyenin |EDM|'sinin esik × PH kadarı grupta netleşir, aşan kısım üyenin kendi P(−)/P(+)'sıyla bireysel kalır; grubun net EDM'si
    grup fiyatıyla (aynı saatlik birim fiyat). Eşik tarihe göre kural tablosundan (%10 → %5, 2027 varsayım) ya da esik_oran.
    KÜPST üye UEVÇB'si bazında (segment/tarih/arıza) hesaplanır ve TOPLANIR, netleşmez (m.110(6)). Dengesizlik taşımayan
    segmentteki üye (dağıtım lisanssız, öz tüketim) portföye GİRMEZ, 'disi' listesinde döner. Toplayıcı DSG'de yer alamaz (m.20(4)).
    Dönüş: {"saatlik": DataFrame (edt_tek, edt_dsg, edt_grup, edt_bireysel, netlesme_farki, kayip_tek, kayip_dsg, kupst_uye, esik, kural_surumu, durum),
            "uyeler": {ad: DataFrame}, "disi": [ad…], "esik_kaynak": str}."""
    segmentler = segmentler or {}
    disi = [ad for ad in programlar if segmentler.get(ad) in ("lisanssiz_dagitim", "oz_tuketim_saatlik")]
    uyeler = [ad for ad in programlar if ad not in disi]
    idx = None
    for ad in uyeler:
        i = _hizala(programlar[ad], gerceklesenler[ad], ptf, smf)
        idx = i if idx is None else idx.intersection(i)
    if idx is None or len(idx) == 0:
        return {"saatlik": pd.DataFrame(), "uyeler": {}, "disi": disi, "esik_kaynak": ""}
    P = ptf.loc[idx].astype(float); S = smf.loc[idx].astype(float)
    f = birim_fiyatlar(P, S, yon)
    prm = kr.parametre_cercevesi(idx)
    esik = pd.Series(esik_oran, index=idx, dtype=float) if esik_oran is not None else prm["dsg_esik"].astype(float)
    esik_kaynak = "parametre" if esik_oran is not None else kr.kural(idx[0]).dsg_dayanak
    grup_edm = pd.Series(0.0, index=idx); birey_edt = pd.Series(0.0, index=idx); tek_edt = pd.Series(0.0, index=idx)
    kayip_tek = pd.Series(0.0, index=idx); kayip_birey = pd.Series(0.0, index=idx); kupst_top = pd.Series(0.0, index=idx)
    kupst_eksik = pd.Series(False, index=idx); detay = {}
    for ad in uyeler:
        F = (pozisyonlar or {}).get(ad, programlar[ad]).reindex(idx).astype(float).fillna(programlar[ad].reindex(idx).astype(float))
        A = gerceklesenler[ad].loc[idx].astype(float); edm = A - F
        ph = pd.concat([A, F], axis=1).max(axis=1)
        grup = edm.clip(lower=-esik * ph, upper=esik * ph); birey = edm - grup
        # tek başına (netleşme olmasaydı) ve bireysel kalan kısım — aynı saatlik birim fiyatlarla
        tek = edm.clip(lower=0) * f["p_poz"] - (-edm).clip(lower=0) * f["p_neg"]
        br = birey.clip(lower=0) * f["p_poz"] - (-birey).clip(lower=0) * f["p_neg"]
        k_tek = edm.clip(lower=0) * (P - f["p_poz"]) + (-edm).clip(lower=0) * (f["p_neg"] - P)
        k_br = birey.clip(lower=0) * (P - f["p_poz"]) + (-birey).clip(lower=0) * (f["p_neg"] - P)
        uye = saatlik(programlar[ad].loc[idx], A, P, S, yon=yon, segment=segmentler.get(ad), ariza_sayisi=(ariza_sayilari or {}).get(ad, 0))
        detay[ad] = pd.DataFrame({"edm": edm, "ph": ph, "grup_payi": grup, "bireysel": birey, "edt_tek": tek, "edt_bireysel": br, "kupst": uye["kupst"]})
        grup_edm += grup; birey_edt += br; tek_edt += tek; kayip_tek += k_tek; kayip_birey += k_br
        kupst_top += uye["kupst"].fillna(0.0); kupst_eksik |= uye["kupst"].isna()
    grup_edt = grup_edm.clip(lower=0) * f["p_poz"] - (-grup_edm).clip(lower=0) * f["p_neg"]
    kayip_grup = grup_edm.clip(lower=0) * (P - f["p_poz"]) + (-grup_edm).clip(lower=0) * (f["p_neg"] - P)
    out = pd.DataFrame({"ptf": P, "smf": S, "yon": f["yon"], "p_neg": f["p_neg"], "p_poz": f["p_poz"], "esik": esik,
                        "grup_edm": grup_edm, "edt_grup": grup_edt, "edt_bireysel": birey_edt, "edt_dsg": grup_edt + birey_edt,
                        "edt_tek": tek_edt, "netlesme_farki": (grup_edt + birey_edt) - tek_edt,
                        "kayip_tek": kayip_tek, "kayip_dsg": kayip_grup + kayip_birey,
                        "kupst_uye": kupst_top.where(~kupst_eksik, np.nan), "kural_surumu": f["kural_surumu"],
                        "durum": np.where(f["yon_eksik"].values, "yon_eksik", np.where(kupst_eksik.values, "kupst_hesaplanamaz", "ok"))})
    return {"saatlik": out, "uyeler": detay, "disi": disi, "esik_kaynak": esik_kaynak}


def teminat(saatlik_df: pd.DataFrame, risk_katsayisi: float = 1.0, ay: int = 3) -> float:
    """Son `ay` ayın en yüksek aylık EDT(−) × risk katsayısı — SADELEŞTİRİLMİŞ GÖSTERGE (Teminat U&E ile doğrulanmadı)."""
    a = saatlik_df["edt_neg"].resample("ME").sum().tail(ay)
    return float(a.max() * risk_katsayisi) if len(a) else 0.0


def senaryo_spread(ptf: pd.Series, spread_oran: float = 0.2, yon_olasilik: float = 0.5, seed: int = 0) -> pd.Series:
    """SMF senaryosu: PTF·(1 ± spread) — sistem yönü rastgele (enerji açığı ↑, fazlası ↓). Gerçek SMF yoksa."""
    rng = np.random.default_rng(seed)
    yon = np.where(rng.uniform(size=len(ptf)) < yon_olasilik, 1.0, -1.0)
    return (ptf * (1 + yon * spread_oran)).clip(lower=0)


def optimal_teklif_kantili(ptf: float, smf_beklenen_acik: float, smf_beklenen_fazla: float, kat: Katsayilar | None = None,
                           tarih: date | None = None) -> float:
    """Gazeteci-çocuk (newsvendor) kuralı: KGÜP için en iyi kantil τ* = c_fazla / (c_eksik + c_fazla).
    c_eksik = eksik üretimin birim maliyeti (açık yönde P(−) − PTF), c_fazla = fazla üretimin birim maliyeti (fazla yönde PTF − P(+));
    birim fiyatlar o günün kuralıyla (kurallar.py; tarih verilmezse bugün)."""
    t = tarih or pd.Timestamp.now(tz=kr.IST).date()
    r = kr.edt_kurali(t)
    if r.rejim == "2025":
        c_eksik = max(ptf, smf_beklenen_acik) * 1.03 - ptf
        c_fazla = ptf - min(ptf, smf_beklenen_fazla) * 0.97
    else:
        mx = max(r.V or 0.0, ptf, smf_beklenen_acik)
        p_neg = (r.AFL * 1.05 if r.AFL and max(ptf, smf_beklenen_acik) >= r.AFL else mx) * (1 + r.k["acik"])
        mn = min(ptf, smf_beklenen_fazla)
        p_poz = (-(r.B or 0.0) * (1 + r.l["fazla"])) if mn < (r.V or 0.0) else mn * (1 - r.l["fazla"])
        c_eksik = p_neg - ptf; c_fazla = ptf - p_poz
    if c_eksik + c_fazla <= 0:
        return 0.5
    return float(np.clip(c_fazla / (c_eksik + c_fazla), 0.05, 0.95))
