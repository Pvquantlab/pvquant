"""v2.590 (Faz 3 F3-C) — PORTFÖY SAPMA VE RİSK (saf; DB yok; TL hesabı yok).

Üç kavram ayrı tutulur, karıştırılmaz:
- program sapması  = gerçekleşen − program (bildirilen KGÜP › öneri); EDM işareti (artı = fazla üretim) — uzlaştırmanın fiziksel tabanı;
- tahmin hatası    = gün öncesi tahmin (P50) − gerçekleşen (artı = fazla tahmin) — tahmin motorunun performansı;
- fizik sapması    = gerçekleşen − hava girdili fizik beklentisi (artı = beklenenden fazla) — santral tarafı (kısıntı, arıza, kirlenme) göstergesi.
Her sapma yalnız iki tarafı da olan saatlerde hesaplanır; eksik/geçersiz ölçüm 0 sayılmaz, saat «hesap dışı» kalır ve sayılır.
Portföy saatlik toplamı santral toplamıdır; santral katkıları toplamı = portföy sapması (test). Karşıt sapmalar: Σ|santral| − |Σ santral| = fiziksel
netleşme (MWh); bu FİZİKSEL bir ofsettir, finansal netleşme değildir (DSG üyeliği ve sözleşme yoksa uzlaştırma santral santral yürür — F3-D).
Maruziyet saatleri: |program sapması| × PTF yalnız SIRALAMA göstergesidir (TL tutarı değildir; fiyat senaryo ise etiketlenir).
Kapsama: beklenen saat, bütün üyeleri ölçülü/programlı saat, sapma hesaplanan saat; güvenilirlik «tam / kısmi / yetersiz».
Gelecek risk: portföy tahmin bandı (F3-B) ile ileri program farkı; bant doğrulanmamışsa etiket taşınır."""
from __future__ import annotations

import numpy as np
import pandas as pd

SURUM = "2026-11-11"
GUVENILIRLIK_ESIK = {"tam": 0.95, "kismi": 0.5}
BANT_TOLERANS_MWH = 1e-6
DENGEDE_PCT = 0.5   # |sapma| / program bu yüzdenin altındaysa santral «dengede» (FEM ile aynı eşik; yalnız etiket)
GUVENILIRLIK_AD = {"tam": "Tam", "kismi": "Kısmi", "yetersiz": "Yetersiz", "yok": "Veri yok"}
RISK_ETIKET = {"dogrulanmis": "Doğrulanmış risk", "tahmini": "Tahmini risk", "eksik": "Eksik bilgi"}
KOLONLAR = ("program_mwh", "gercek_mwh", "tahmin_mwh", "fizik_mwh")


def _hizala(girdiler: dict[str, pd.DataFrame]) -> tuple[pd.DatetimeIndex, list[str]]:
    adlar = [a for a, d in girdiler.items() if d is not None]
    idx = None
    for a in adlar:
        i = pd.DatetimeIndex(girdiler[a].index); i = i.tz_localize("UTC") if i.tz is None else i.tz_convert("UTC")
        idx = i if idx is None else idx.union(i)
    return (idx.sort_values() if idx is not None else pd.DatetimeIndex([], tz="UTC")), adlar


def _kol(d: pd.DataFrame, ad: str, idx: pd.DatetimeIndex) -> pd.Series:
    if ad not in d.columns:
        return pd.Series(np.nan, index=idx)
    s = pd.to_numeric(d[ad], errors="coerce"); i = pd.DatetimeIndex(s.index); s.index = i.tz_localize("UTC") if i.tz is None else i.tz_convert("UTC")
    return s[~s.index.duplicated(keep="last")].reindex(idx).astype(float)


def saatlik(girdiler: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """girdiler: ad → DataFrame (indeks ts_utc; kolonlar program_mwh, gercek_mwh, tahmin_mwh, fizik_mwh; eksik NaN). Saat birliği (union) üzerinde
    portföy çerçevesi ve santral çerçeveleri (sapmalar yalnız iki taraflı saatlerde)."""
    idx, adlar = _hizala(girdiler)
    n = len(adlar)
    santral: dict[str, pd.DataFrame] = {}
    for a in adlar:
        d = girdiler[a]
        f = pd.DataFrame({k: _kol(d, k, idx) for k in KOLONLAR}, index=idx)
        f["program_sapma_mwh"] = (f["gercek_mwh"] - f["program_mwh"]).where(f["gercek_mwh"].notna() & f["program_mwh"].notna())
        f["tahmin_hata_mwh"] = (f["tahmin_mwh"] - f["gercek_mwh"]).where(f["gercek_mwh"].notna() & f["tahmin_mwh"].notna())
        f["fizik_sapma_mwh"] = (f["gercek_mwh"] - f["fizik_mwh"]).where(f["gercek_mwh"].notna() & f["fizik_mwh"].notna())
        santral[a] = f
    p = pd.DataFrame(index=idx)
    for k in KOLONLAR + ("program_sapma_mwh", "tahmin_hata_mwh", "fizik_sapma_mwh"):
        M = pd.DataFrame({a: santral[a][k] for a in adlar}) if adlar else pd.DataFrame(index=idx)
        p[k] = M.sum(axis=1, min_count=1) if adlar else np.nan
        p[k.replace("_mwh", "_n")] = M.notna().sum(axis=1) if adlar else 0
    p["santral_n"] = n
    p["olcum_tam"] = p["gercek_n"] == n; p["program_tam"] = p["program_n"] == n; p["sapma_tam"] = p["program_sapma_n"] == n
    p["hesap_disi_n"] = n - p["program_sapma_n"]
    return p, santral


def _tr(v: float, n: int = 1) -> str:
    """Türkçe ondalık (virgül)."""
    return f"{v:.{n}f}".replace(".", ",")


def _mwh(s: pd.Series) -> float | None:
    v = pd.to_numeric(s, errors="coerce")
    return None if v.notna().sum() == 0 else round(float(v.sum()), 3)


def ozet(p: pd.DataFrame, santral: dict[str, pd.DataFrame], kapasiteler: dict[str, float] | None = None) -> dict:
    """Dönem toplamları (yalnız tam saatler değil: her kavram kendi iki taraflı saatlerinde; «tam» sayımlar ayrıca). Sapma yüzdesi programa göre."""
    n_saat = int(len(p))
    out = {"saat": n_saat, "santral": int(p["santral_n"].iloc[0]) if n_saat else 0, "kapasite_kwp": float(sum((kapasiteler or {}).values())) if kapasiteler else None,
           "program": {"mwh": _mwh(p["program_mwh"]), "saat": int((p["program_n"] > 0).sum()), "tam_saat": int(p["program_tam"].sum())},
           "gerceklesen": {"mwh": _mwh(p["gercek_mwh"]), "saat": int((p["gercek_n"] > 0).sum()), "tam_saat": int(p["olcum_tam"].sum()), "eksik_saat": int((p["gercek_n"] < p["santral_n"]).sum())},
           "tahmin": {"mwh": _mwh(p["tahmin_mwh"]), "saat": int((p["tahmin_n"] > 0).sum())},
           "fizik": {"mwh": _mwh(p["fizik_mwh"]), "saat": int((p["fizik_n"] > 0).sum())}}
    for kod, ad in (("program_sapma", "gerçekleşen − program (artı = fazla üretim)"), ("tahmin_hata", "tahmin − gerçekleşen (artı = fazla tahmin)"),
                    ("fizik_sapma", "gerçekleşen − fizik beklentisi (artı = beklenenden fazla)")):
        s = p[f"{kod}_mwh"]; m = s.notna()
        taban_kol = {"program_sapma": "program_mwh", "tahmin_hata": "gercek_mwh", "fizik_sapma": "fizik_mwh"}[kod]
        t = float(sum(f[taban_kol][f[f"{kod}_mwh"].notna()].sum() for f in santral.values()))   # payda yalnız sapması hesaplanan santral-saatler
        out[kod] = {"mwh": _mwh(s), "pct": round(100.0 * float(s[m].sum()) / t, 2) if m.any() and t > 1e-9 else None, "saat": int(m.sum()),
                    "tam_saat": int((p[f"{kod}_n"] == p["santral_n"]).sum()), "etiket": ad,
                    "mutlak_mwh": round(float(s[m].abs().sum()), 3) if m.any() else None}
    return out


def katkilar(p: pd.DataFrame, santral: dict[str, pd.DataFrame], kapasiteler: dict[str, float] | None = None, kavram: str = "program_sapma") -> dict:
    """Santral katkıları (Σ = portföy) ve karşıt sapma ofseti: fiziksel netleşme = Σ|santral| − |Σ santral| (MWh, finansal değildir)."""
    k = f"{kavram}_mwh"
    satirlar = []
    toplam = float(p[k].sum()) if p[k].notna().any() else 0.0
    mutlak_toplam = sum(float(santral[a][k].abs().sum()) for a in santral)
    for a, f in santral.items():
        s = f[k]; m = s.notna()
        v = float(s[m].sum()) if m.any() else None
        taban = float(f["program_mwh"][m].sum()) if m.any() else 0.0
        yon = None if v is None else ("dengede" if (taban > 1e-9 and abs(v) / taban * 100 < DENGEDE_PCT) or abs(v) < 1e-9 else "fazla" if v > 0 else "eksik")
        satirlar.append({"santral": a, "kapasite_kwp": (kapasiteler or {}).get(a), "mwh": None if v is None else round(v, 3),
                         "pay_pct": None if v is None or abs(toplam) < 1e-9 else round(100.0 * v / toplam, 1),
                         "mutlak_pay_pct": None if v is None or mutlak_toplam < 1e-9 else round(100.0 * abs(v) / mutlak_toplam, 1),
                         "yon": yon, "pct": None if v is None or taban < 1e-9 else round(100.0 * v / taban, 2), "saat": int(m.sum()),
                         "program_mwh": _mwh(f["program_mwh"]), "gercek_mwh": _mwh(f["gercek_mwh"])})
    satirlar.sort(key=lambda r: -abs(r["mwh"] or 0.0))
    netlesen = max(0.0, mutlak_toplam - abs(toplam))
    fazla = [r["santral"] for r in satirlar if r["yon"] == "fazla"]; eksik = [r["santral"] for r in satirlar if r["yon"] == "eksik"]
    not_ = None
    if fazla and eksik and netlesen > 1e-6:
        not_ = (f"{len(fazla) + len(eksik)} santralin sapmaları portföy toplamında birbirini kısmen dengeliyor: toplam |sapma| {_tr(mutlak_toplam)} MWh, "
                f"portföy net sapması {_tr(abs(toplam))} MWh ({_tr(netlesen)} MWh fiziksel olarak netleşti). Bu fiziksel bir ofsettir; mali karşılığı "
                "DSG üyeliği ve sözleşmeye bağlıdır.")
    return {"kavram": kavram, "satirlar": satirlar, "toplam_mwh": round(toplam, 3), "mutlak_toplam_mwh": round(mutlak_toplam, 3), "netlesen_mwh": round(netlesen, 3),
            "netlesme_orani_pct": round(100.0 * netlesen / mutlak_toplam, 1) if mutlak_toplam > 1e-9 else None, "fazla": fazla, "eksik": eksik, "not": not_}


def korelasyon_sapma(santral: dict[str, pd.DataFrame], kavram: str = "program_sapma") -> dict:
    """Santraller arası sapma korelasyonu (saatlik, iki taraflı saatler), F3-B büzülmüş korelasyonuyla."""
    from pvquant.ext.tahmin.portfoy_belirsizlik import korelasyon
    M = pd.DataFrame({a: f[f"{kavram}_mwh"] for a, f in santral.items()})
    ko = korelasyon(M if not M.empty else None)
    return {"durum": ko["durum"], "n_gun": ko["n_gun"], "n_saat": ko["n_saat"], "rho": ko["rho"].round(3).to_dict() if ko.get("rho") is not None else None, "yontem": ko["yontem"]}


def maruziyet_saatleri(p: pd.DataFrame, santral: dict[str, pd.DataFrame], fiyat: pd.DataFrame | None, n: int = 10) -> dict:
    """En yüksek maruziyet saatleri: |program sapması| × PTF SIRALAMA göstergesi (TL tutarı değil). Fiyat yoksa yalnız |sapma| ile sıralanır."""
    s = p["program_sapma_mwh"]
    m = s.notna()
    if not m.any():
        return {"saatler": [], "olcut": "yok", "not": "Sapma hesaplanan saat yok."}
    if fiyat is not None and "ptf" in fiyat.columns and len(fiyat):
        f = fiyat.copy(); i = pd.DatetimeIndex(f.index); f.index = i.tz_localize("UTC") if i.tz is None else i.tz_convert("UTC")
        ptf = pd.to_numeric(f["ptf"], errors="coerce").reindex(p.index)
        kay = f["kaynak"].reindex(p.index) if "kaynak" in f.columns else pd.Series(None, index=p.index, dtype=object)
        skor = (s.abs() * ptf).where(m & ptf.notna()); olcut = "|program sapması| × PTF (gösterge)"
    else:
        ptf = pd.Series(np.nan, index=p.index); kay = pd.Series(None, index=p.index, dtype=object); skor = s.abs().where(m); olcut = "|program sapması|"
    sira = skor.dropna().sort_values(ascending=False).head(n)
    out = []
    for ts, v in sira.items():
        kat = {a: f.loc[ts, "program_sapma_mwh"] for a, f in santral.items() if pd.notna(f.loc[ts, "program_sapma_mwh"])}
        bask = max(kat, key=lambda a: abs(kat[a])) if kat else None
        out.append({"ts": ts.isoformat(timespec="minutes"), "sapma_mwh": round(float(s[ts]), 3), "ptf": None if pd.isna(ptf[ts]) else round(float(ptf[ts]), 2),
                    "fiyat_kaynak": None if kay[ts] is None or (isinstance(kay[ts], float) and np.isnan(kay[ts])) else str(kay[ts]),
                    "gosterge": round(float(v), 1), "baskin_santral": bask, "baskin_mwh": None if bask is None else round(float(kat[bask]), 3), "tam": bool(p.loc[ts, "sapma_tam"])})
    return {"saatler": out, "olcut": olcut, "not": "Sıralama göstergesidir; uzlaştırma tutarı değildir (sistem yönü ve kural saatlik hesapta uygulanır)."}


def kapsama(p: pd.DataFrame) -> dict:
    n = int(len(p))
    if n == 0:
        return {"beklenen_saat": 0, "olcum_tam_saat": 0, "program_tam_saat": 0, "sapma_tam_saat": 0, "sapma_saat": 0, "oran_pct": None, "guvenilirlik": "yok", "guvenilirlik_ad": GUVENILIRLIK_AD["yok"]}
    tam = int(p["sapma_tam"].sum()); oran = tam / n
    g = "tam" if oran >= GUVENILIRLIK_ESIK["tam"] else "kismi" if oran >= GUVENILIRLIK_ESIK["kismi"] else "yetersiz"
    return {"beklenen_saat": n, "olcum_tam_saat": int(p["olcum_tam"].sum()), "program_tam_saat": int(p["program_tam"].sum()), "sapma_tam_saat": tam,
            "sapma_saat": int((p["program_sapma_n"] > 0).sum()), "hesap_disi_santral_saat": int(p["hesap_disi_n"].sum()), "oran_pct": round(100.0 * oran, 1),
            "guvenilirlik": g, "guvenilirlik_ad": GUVENILIRLIK_AD[g],
            "aciklama": {"tam": "Dönemin neredeyse tüm saatlerinde bütün santrallerin ölçümü ve programı var.",
                         "kismi": "Bazı saatlerde en az bir santralin ölçümü ya da programı yok; o saatler toplamlara girmedi.",
                         "yetersiz": "Saatlerin yarısından azında bütün santrallerin verisi var; portföy sapması eksik görünümdür."}[g]}


def gelecek_risk(tahmin: pd.DataFrame, program: pd.Series, belirsizlik_durumu: str, program_kaynak: pd.Series | None = None, kapasite: float | None = None) -> dict:
    """tahmin: F3-B saatlik (p50, p10, p90 kW; indeks ts_utc). program: ileri program (MWh). Beklenen sapma = tahmin − program; riskli saat = program bandın dışında.
    Etiket: program bildirilen ve bant doğrulanmış → doğrulanmış risk; aksi tahmini risk; program yoksa eksik bilgi."""
    if tahmin is None or tahmin.empty:
        return {"etiket": "eksik", "etiket_ad": RISK_ETIKET["eksik"], "not": "Portföy tahmini yok.", "saatler": []}
    t = tahmin.copy(); i = pd.DatetimeIndex(t.index); t.index = i.tz_localize("UTC") if i.tz is None else i.tz_convert("UTC")
    pr = pd.to_numeric(program, errors="coerce") if program is not None else pd.Series(dtype=float)
    if len(pr):
        j = pd.DatetimeIndex(pr.index); pr.index = j.tz_localize("UTC") if j.tz is None else j.tz_convert("UTC")
    pr = pr.reindex(t.index)
    p50, p10, p90 = t["p50"] / 1000.0, t["p10"] / 1000.0, t["p90"] / 1000.0
    m = pr.notna() & p50.notna()
    if not m.any():
        return {"etiket": "eksik", "etiket_ad": RISK_ETIKET["eksik"], "not": "Gelecek saatler için program yok; sapma hesaplanamadı.", "saatler": [],
                "tahmin_mwh": _mwh(p50), "program_mwh": None}
    fark = (p50 - pr).where(m)
    riskli = m & ((pr < p10 - BANT_TOLERANS_MWH) | (pr > p90 + BANT_TOLERANS_MWH))   # 1 Wh tolerans: 0 = 0 saatlerde kayan nokta «dışarıda» demesin
    kay = program_kaynak.reindex(t.index) if program_kaynak is not None else pd.Series(None, index=t.index, dtype=object)
    bildirilen_hepsi = bool(len(kay.dropna()) and (kay[m] == "bildirilen").all())
    et = "dogrulanmis" if belirsizlik_durumu == "dogrulandi" and bildirilen_hepsi else "tahmini"
    top_p, top_pr = float(p50[m].sum()), float(pr[m].sum())
    saatler = [{"ts": ts.isoformat(timespec="minutes"), "program_mwh": round(float(pr[ts]), 3), "tahmin_mwh": round(float(p50[ts]), 3), "p10_mwh": round(float(p10[ts]), 3) if pd.notna(p10[ts]) else None,
                "p90_mwh": round(float(p90[ts]), 3) if pd.notna(p90[ts]) else None, "fark_mwh": round(float(fark[ts]), 3), "yon": "program bandın üstünde" if pr[ts] > p90[ts] else "program bandın altında"}
               for ts in t.index[riskli]]
    saatler.sort(key=lambda r: -abs(r["fark_mwh"]))
    return {"etiket": et, "etiket_ad": RISK_ETIKET[et], "belirsizlik_durumu": belirsizlik_durumu, "program_bildirilen": bildirilen_hepsi,
            "saat": int(m.sum()), "program_mwh": round(top_pr, 3), "tahmin_mwh": round(top_p, 3), "beklenen_sapma_mwh": round(top_p - top_pr, 3),
            "beklenen_sapma_pct": round(100.0 * (top_p - top_pr) / top_pr, 2) if top_pr > 1e-9 else None,
            "aralik_mwh": {"p10": round(float((p10[m] - pr[m]).sum()), 3), "p90": round(float((p90[m] - pr[m]).sum()), 3)},
            "riskli_saat": int(riskli.sum()), "saatler": saatler[:24], "kapasite_kwp": kapasite,
            "not": ("Program ile tahmin arasındaki fark bant içindeyse sapma olağan belirsizlik sınırında kabul edilir; bandın dışındaki saatler listelendi. "
                    + ("Bant doğrulanmış, program bildirilmiş: doğrulanmış risk." if et == "dogrulanmis" else "Bant doğrulanmamış ya da program öneri: tahmini risk."))}
