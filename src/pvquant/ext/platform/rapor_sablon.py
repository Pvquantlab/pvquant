"""Şablon raporlar — kapasite testi (ASTM E2848), beklenen-gerçekleşen, fatura, kullanılabilirlik.

Her şablon: veri → yapılandırılmış sonuç (dict/DataFrame) → `markdown()` / `html()` (çatı-bağımsız, jinja yok).
Mevcut 16 sayfalık PDF'e ek sayfalar ya da ayrı kısa raporlar olarak kullanılır. Yöntem adları (E2848 regresyonu vb.)
rapor gövdesinde geçmez; yalnız 'kapasite testi' gibi ürün dili (Gizlilik Anayasası).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Rapor:
    baslik: str; donem: str; santral: str; bolumler: list[tuple[str, pd.DataFrame | str]]; kunye: str = ""

    def markdown(self) -> str:
        p = [f"# {self.baslik}", f"**Santral:** {self.santral}  ·  **Dönem:** {self.donem}", ""]
        for ad, govde in self.bolumler:
            p.append(f"## {ad}")
            p.append(govde.to_markdown(floatfmt=".2f") if isinstance(govde, pd.DataFrame) else str(govde)); p.append("")
        if self.kunye:
            p += ["---", self.kunye]
        return "\n".join(p)

    def html(self) -> str:
        p = [f"<h1>{self.baslik}</h1><p><b>Santral:</b> {self.santral} · <b>Dönem:</b> {self.donem}</p>"]
        for ad, govde in self.bolumler:
            p.append(f"<h2>{ad}</h2>")
            p.append(govde.to_html(float_format=lambda x: f"{x:,.2f}", border=0) if isinstance(govde, pd.DataFrame) else f"<p>{govde}</p>")
        if self.kunye:
            p.append(f"<hr><small>{self.kunye}</small>")
        return "\n".join(p)


def kapasite_testi(guc_ac_kw: pd.Series, poa: pd.Series, temp_air: pd.Series, wind: pd.Series, p_hedef_kw: float | None = None,
                   poa_min: float = 400.0, rtc: dict | None = None, santral: str = "", donem: str = "", beklenen_fn=None) -> tuple[Rapor, dict]:
    """ASTM E2848: P = E·(a1 + a2·E + a3·T_a + a4·v) regresyonu; raporlama koşulunda (RC) ölçülen kapasite vs BEKLENEN.
    Hedef anma gücü DEĞİL, aynı RC'deki beklenen güçtür: `beklenen_fn(rc) -> kW` (kalibre model/veri sayfası) ya da doğrudan p_hedef_kw.
    rtc: raporlama koşulları {'E':..,'T':..,'v':..}; verilmezse test verisinin ışınım-ağırlıklı ortalaması."""
    idx = guc_ac_kw.dropna().index.intersection(poa.dropna().index).intersection(temp_air.index).intersection(wind.index)
    m = poa.loc[idx] >= poa_min
    E, T, V, P = poa.loc[idx][m].values, temp_air.loc[idx][m].values, wind.loc[idx][m].values, guc_ac_kw.loc[idx][m].values
    if len(E) < 50:
        raise ValueError("kapasite testi için ≥50 uygun saat gerekir")
    X = np.c_[E, E * E, E * T, E * V]
    kat, *_ = np.linalg.lstsq(X, P, rcond=None)
    rtc = rtc or {"E": float(np.average(E, weights=E)), "T": float(np.average(T, weights=E)), "v": float(np.average(V, weights=E))}
    p_rc = float(rtc["E"] * (kat[0] + kat[1] * rtc["E"] + kat[2] * rtc["T"] + kat[3] * rtc["v"]))
    if beklenen_fn is not None:
        p_hedef_kw = float(beklenen_fn(rtc))
    if p_hedef_kw is None:
        raise ValueError("p_hedef_kw ya da beklenen_fn gerekir")
    tahmin = X @ kat; r2 = 1 - np.sum((P - tahmin) ** 2) / np.sum((P - P.mean()) ** 2)
    oran = p_rc / p_hedef_kw
    sonuc = {"olculen_kapasite_kw": p_rc, "hedef_kw": p_hedef_kw, "oran": oran, "r2": float(r2), "n": int(len(E)), "rc": rtc, "gecti": bool(oran >= 0.95)}
    tablo = pd.DataFrame([{"Ölçülen kapasite (kW)": p_rc, "Hedef (kW)": p_hedef_kw, "Oran": oran, "Uyum (R²)": r2, "Saat sayısı": len(E)}])
    rc = pd.DataFrame([{"Işınım (W/m²)": rtc["E"], "Sıcaklık (°C)": rtc["T"], "Rüzgar (m/s)": rtc["v"]}])
    karar = "GEÇTİ (≥ %95)" if sonuc["gecti"] else "KALDI (< %95)"
    return Rapor("Kapasite testi", donem, santral, [("Sonuç", tablo), ("Raporlama koşulları", rc), ("Karar", karar)]), sonuc


def beklenen_gerceklesen(beklenen_kwh: pd.Series, gercek_kwh: pd.Series, santral: str = "", donem: str = "", tz: str = "Europe/Istanbul") -> tuple[Rapor, pd.DataFrame]:
    idx = beklenen_kwh.index.intersection(gercek_kwh.index)
    b = beklenen_kwh.loc[idx].tz_convert(tz); g = gercek_kwh.loc[idx].tz_convert(tz)
    ay = pd.DataFrame({"Beklenen (kWh)": b.resample("ME").sum(), "Gerçekleşen (kWh)": g.resample("ME").sum()})
    ay["Fark (kWh)"] = ay["Gerçekleşen (kWh)"] - ay["Beklenen (kWh)"]; ay["Fark (%)"] = ay["Fark (kWh)"] / ay["Beklenen (kWh)"].replace(0, np.nan) * 100
    ay.index = ay.index.strftime("%Y-%m")
    toplam = ay[["Beklenen (kWh)", "Gerçekleşen (kWh)", "Fark (kWh)"]].sum(); toplam["Fark (%)"] = toplam["Fark (kWh)"] / toplam["Beklenen (kWh)"] * 100
    ay.loc["Toplam"] = toplam
    en_kotu = ay.drop("Toplam").sort_values("Fark (%)").head(3).index.tolist()
    return Rapor("Beklenen – gerçekleşen", donem, santral, [("Aylık", ay), ("Not", f"En zayıf aylar: {', '.join(en_kotu)}")]), ay


def fatura(uretim_mwh: pd.Series, gelir_tl: pd.Series, dengesizlik_tl: pd.Series | None = None, kdv: float = 0.20,
           santral: str = "", donem: str = "", ek_kalemler: dict[str, float] | None = None) -> tuple[Rapor, pd.DataFrame]:
    kalem = [{"Kalem": "Enerji satışı", "Miktar (MWh)": float(uretim_mwh.sum()), "Tutar (TL)": float(gelir_tl.sum())}]
    if dengesizlik_tl is not None:
        kalem.append({"Kalem": "Dengesizlik (−)", "Miktar (MWh)": np.nan, "Tutar (TL)": -float(dengesizlik_tl.sum())})
    for ad, tutar in (ek_kalemler or {}).items():
        kalem.append({"Kalem": ad, "Miktar (MWh)": np.nan, "Tutar (TL)": float(tutar)})
    df = pd.DataFrame(kalem); ara = df["Tutar (TL)"].sum()
    df = pd.concat([df, pd.DataFrame([{"Kalem": "Ara toplam", "Tutar (TL)": ara}, {"Kalem": f"KDV (%{kdv*100:.0f})", "Tutar (TL)": ara * kdv},
                                      {"Kalem": "Genel toplam", "Tutar (TL)": ara * (1 + kdv)}])], ignore_index=True)
    return Rapor("Fatura özeti", donem, santral, [("Kalemler", df), ("Not", "e-Fatura (UBL-TR) için muhasebe entegrasyonu ayrı; bu özet bilgilendirme amaçlıdır.")]), df


def kullanilabilirlik_raporu(zaman: dict, enerji: dict, birim: pd.DataFrame | None, sozlesme: dict | None, santral: str = "", donem: str = "") -> Rapor:
    ozet = pd.DataFrame([{"Zaman tabanlı (%)": zaman.get("A_t", np.nan) * 100, "Enerji tabanlı (%)": enerji.get("A_e", np.nan) * 100,
                          "Arıza saati": zaman.get("saat_ariza"), "Hariç saat": zaman.get("saat_haric"), "Arıza kaybı (kWh)": enerji.get("E_kayip_ariza_kwh")}])
    bol = [("Özet", ozet)]
    if birim is not None:
        bol.append(("Birim bazında", birim[["birim", "kapasite", "A_t"]].assign(A_t=lambda d: d["A_t"] * 100).rename(columns={"A_t": "A_t (%)"})))
    if sozlesme:
        bol.append(("Sözleşme", pd.DataFrame([sozlesme])))
    return Rapor("Kullanılabilirlik", donem, santral, bol)
