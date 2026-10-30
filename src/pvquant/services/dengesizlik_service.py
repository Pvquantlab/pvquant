"""v2.259 — Dalga 4.12: uzlaştırma kalemleri simülatörü (EDT + KÜPST) — karnenin TL dili. 29.10.2026 (F-01/F-02/F-03):
kural TARİHE göre (ext.turkiye.kurallar), yöne bağlı k/l, V/B/AFL dalları, 750 TL tabanı, 14907 net sapma.

Program (KGÜP) = D-1 günü 15:30 (İstanbul) öncesinde verilmiş SON koşunun D günü P50'si — yani gerçekten
teslim edilebilecek program (sonraki koşular sayılmaz). Referans program = dün-aynı-saat gerçekleşen (basit
referans). Gerçekleşen = SCADA (flag 'valid'). Fiyat = piyasa_service.fiyatlar (EPİAŞ ya da senaryo — kaynak
ve sistem yönü satır satır taşınır). Formül: pvquant.ext.turkiye.dengesizlik. Segment: plants.params_json.segment →
dengesizliği santral mı taşıyor, KÜPST katsayıları (ext.turkiye.segment + kurallar). Dürüstlük: eşleşen gün yoksa boş;
senaryo fiyatı kullanıldıysa yanıt bunu sayıyla söyler; senaryo saatinde sistem yönü yoktur → k = l = 0,03 («dengede»)
VARSAYIMI ve sayısı yanıtta; EPİAŞ saatinde yön eksikse o saat hesaplanmaz («yon_eksik»); KÜPST hesaplanamıyorsa
(segment seçilmedi / katsayı doğrulanamadı) 0 değil None döner. 'kurtarilan_tl' alan adı sözleşmedir; anlamı
«referans programa göre fark»; vaat değil, varsayımsal kıyastır.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from pvquant.ext.turkiye import dengesizlik as d, kurallar as kr, segment as sg

IST = "Europe/Istanbul"


def _pj(v) -> dict:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v or {}


def program_df(tenant_id, plant_id, gun: int = 90) -> pd.DataFrame:
    """DB: ts_utc, gercek_kw, kgup_kw (D-1 15:30 IST öncesi son koşu), naif_kw (dün-aynı-saat)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "WITH g AS (SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
            "  AND ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day')) "
            "SELECT g.ts_utc, g.power_kw AS gercek_kw, "
            " (SELECT f.p50_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "   WHERE f.plant_id=:p AND f.ts_utc=g.ts_utc "
            "   AND r.run_at <= ((date_trunc('day', g.ts_utc AT TIME ZONE 'Europe/Istanbul') - INTERVAL '1 day' + INTERVAL '15 hours 30 minutes') AT TIME ZONE 'Europe/Istanbul') "
            "   ORDER BY r.run_at DESC LIMIT 1) AS kgup_kw, "
            " (SELECT s2.power_kw FROM scada_hourly s2 WHERE s2.plant_id=:p AND s2.flag='valid' AND s2.ts_utc = g.ts_utc - INTERVAL '24 hour') AS naif_kw "
            "FROM g ORDER BY g.ts_utc"),
            s.connection(), params={"p": plant_id, "g": gun}, parse_dates=["ts_utc"])
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df


def _yon_ve_kaynak(f: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Fiyat çerçevesinden sistem yönü serisi: EPİAŞ satırında yön metni normalize edilir (yoksa None → o saat hesaplanmaz);
    senaryo satırında yön yoktur → 'dengede' (k = l = 0,03) VARSAYIMI, sayısı döner."""
    kaynak = f["kaynak"] if "kaynak" in f else pd.Series("epias", index=f.index)
    yon = pd.Series([kr.yon_normalize(v) for v in (f["yon"].values if "yon" in f else [None] * len(f))], index=f.index, dtype=object)
    sen = (kaynak == "senaryo").values
    varsayilan = sen & yon.isna().values
    yon[varsayilan] = "dengede"
    return yon, {"epias_saat": int((kaynak == "epias").sum()), "senaryo_saat": int(sen.sum()),
                 "yon_varsayilan_saat": int(varsayilan.sum()), "yon_eksik_saat": int(((~sen) & yon.isna().values).sum())}


def _r0(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 0)


def hesapla_df(df: pd.DataFrame, fiyat: pd.DataFrame, kat: d.Katsayilar | None = None, segment: str | None = None,
               ariza_sayisi: int = 0, luy_istisna: bool = False) -> dict:
    """SAF. df: ts_utc, gercek_kw, kgup_kw, naif_kw (kW ≈ kWh/saat → MWh = /1000). fiyat: aynı ts index'li ptf/smf/yon/kaynak.
    Çıktı: aylar[] ve toplam — EDT (edt_neg/edt_poz/edta/edtb), kayıp (dengesizlik_tl), KÜPST (kupst_tl) AYRI;
    pvquant_tl = kayıp + KÜPST («uzlaştırma kalemleri toplamı»; KÜPST hesaplanamıyorsa None)."""
    kat = kat or d.Katsayilar()
    bos = {"gun_sayisi": 0, "aylar": [], "toplam": None, "hesaplanamayan_saat": 0, "kural_surumu": None,
           "fiyat": {"epias_saat": 0, "senaryo_saat": 0, "yon_varsayilan_saat": 0, "yon_eksik_saat": 0}}
    if df is None or df.empty:
        return bos
    x = df.dropna(subset=["gercek_kw", "kgup_kw"]).copy().set_index("ts_utc")
    if x.empty:
        return bos
    f = fiyat.reindex(x.index)
    yon, fiyat_ozeti = _yon_ve_kaynak(f)
    ger = x["gercek_kw"].astype(float) / 1000.0; kg = x["kgup_kw"].astype(float) / 1000.0
    ptf = f["ptf"].astype(float); smf = f["smf"].astype(float)
    pv = d.saatlik(kg, ger, ptf, smf, kat, yon=yon, segment=segment, ariza_sayisi=ariza_sayisi, luy_istisna=luy_istisna)
    ay_pv = d.aylik_karne(pv)
    naif_var = x["naif_kw"].notna(); ay_naif = None
    if naif_var.sum() >= 24:
        xn = x[naif_var]
        nv = d.saatlik(xn["naif_kw"].astype(float) / 1000.0, ger.loc[xn.index], ptf.loc[xn.index], smf.loc[xn.index], kat,
                       yon=yon.loc[xn.index], segment=segment, ariza_sayisi=ariza_sayisi)
        ay_naif = d.aylik_karne(nv)
    out_ay = []
    for ay, r in ay_pv.iterrows():
        kn = (float(ay_naif.loc[ay, "toplam_maliyet"]) if ay_naif is not None and ay in ay_naif.index else None)
        top = _r0(r["toplam_maliyet"])
        out_ay.append({"ay": ay.strftime("%Y-%m"), "uretim_mwh": round(float(r["gerceklesen"]), 1), "sapma_mwh": round(float(r["sapma"]), 1),
                       "kupst_tl": _r0(r["kupst"]), "dengesizlik_tl": _r0(r["dengesizlik_maliyeti"]),   # v2.275; kayıp (programa göre)
                       "edt_neg_tl": _r0(r["edt_neg"]), "edt_poz_tl": _r0(r["edt_poz"]), "edta_tl": _r0(r["edta"]), "edtb_tl": _r0(r["edtb"]),
                       "referans_gelir_tl": round(float(r["referans_gelir"]), 0), "pvquant_tl": top,
                       "naif_tl": _r0(kn), "kurtarilan_tl": (_r0(kn - float(r["toplam_maliyet"])) if kn is not None and top is not None else None),
                       "gelir_oran_pct": round(float(r["maliyet_gelir_orani"]) * 100, 2) if pd.notna(r["maliyet_gelir_orani"]) else None,
                       "tl_per_mwh": round(float(r["tl_per_mwh"]), 1) if pd.notna(r["tl_per_mwh"]) else None,
                       "hesaplanamayan_saat": int(r["hesaplanamayan_saat"]), "kural_surumu": str(r["kural_surumu"])})
    top_pv = float(pv["toplam_maliyet"].sum(min_count=1)) if pv["toplam_maliyet"].notna().any() else float("nan")
    top_ref = float(pv["referans_gelir"].sum())
    teminat_tl = round(d.teminat(pv), 0)   # v2.287: sadeleştirilmiş gösterge (Teminat U&E ile doğrulanmadı)
    top_naif = float(ay_naif["toplam_maliyet"].sum(min_count=1)) if ay_naif is not None and ay_naif["toplam_maliyet"].notna().any() else None
    kupst_top = float(pv["kupst"].sum(min_count=1)) if pv["kupst"].notna().any() and not pv["kupst"].isna().any() else None
    return {"gun_sayisi": int(pd.Series(x.index.tz_convert(IST).date).nunique()), "aylar": out_ay,
            "toplam": {"pvquant_tl": _r0(top_pv), "kupst_tl": _r0(kupst_top),   # v2.275
                       "dengesizlik_tl": round(float(pv["dengesizlik_maliyeti"].sum()), 0),
                       "edt_neg_tl": round(float(pv["edt_neg"].fillna(0).sum()), 0), "edt_poz_tl": round(float(pv["edt_poz"].fillna(0).sum()), 0),
                       "edta_tl": round(float(ay_pv["edta"].sum()), 0), "edtb_tl": round(float(ay_pv["edtb"].sum()), 0),
                       "teminat_tl": teminat_tl,   # v2.287
                       "naif_tl": _r0(top_naif),
                       "kurtarilan_tl": (_r0(top_naif - top_pv) if top_naif is not None and not np.isnan(top_pv) else None),
                       "gelir_oran_pct": round(top_pv / top_ref * 100, 2) if top_ref and not np.isnan(top_pv) else None, "referans_gelir_tl": round(top_ref, 0)},
            "fiyat": fiyat_ozeti, "hesaplanamayan_saat": int((pv["durum"] != "ok").sum()),
            "kural_surumu": " | ".join(sorted(set(pv["kural_surumu"]))),
            "katsayilar": {"k": 0.03, "l": 0.03, "k_yon": {"acik": 0.06, "fazla": 0.03, "dengede": 0.03} if (pv["rejim"] == "2026").any() else {"acik": 0.03, "fazla": 0.03, "dengede": 0.03},
                           "l_yon": {"acik": 0.03, "fazla": 0.06, "dengede": 0.03} if (pv["rejim"] == "2026").any() else {"acik": 0.03, "fazla": 0.03, "dengede": 0.03},
                           "kupst_n": (float(pv["kupst_n"].iloc[-1]) if pd.notna(pv["kupst_n"].iloc[-1]) else None),
                           "kupst_tolerans": (float(pv["kupst_m"].iloc[-1]) if pd.notna(pv["kupst_m"].iloc[-1]) else None)}}


def segment_bilgisi(params_json) -> dict:
    pj = _pj(params_json); ad = pj.get("segment")
    try:
        seg = sg.Segment(ad) if ad else None
    except ValueError:
        seg = None
    if seg is None:
        return {"segment": None, "kgup_yukumlu": None, "dengesizlik_sahibi": None, "santral_tasir": None}
    k = sg.KURALLAR.loc[seg]
    st = sg.Santral("x", seg, 1.0)
    return {"segment": seg.value, "kgup_yukumlu": bool(k["kgup_yukumlu"]), "dengesizlik_sahibi": str(k["dengesizlik_sahibi"]), "santral_tasir": st.dengesizlik_tasir_mi()}


def katsayilar(params_json) -> d.Katsayilar:
    """Santral bazında KÜPST geçersiz kılma (params_json.kupst_n / kupst_tolerans); verilmezse kural tablosu (kurallar.py)
    tarihe ve segmente göre seçer. KÜPST yalnız KGÜP yükümlü segmentlerde (KURALLAR.kupst)."""
    pj = _pj(params_json)
    seg = segment_bilgisi(params_json)
    kupst_var = False
    if seg["segment"]:
        try:
            kupst_var = bool(sg.KURALLAR.loc[sg.Segment(seg["segment"]), "kupst"])
        except (KeyError, ValueError):
            kupst_var = False
    n = pj.get("kupst_n"); tol = pj.get("kupst_tolerans")
    return d.Katsayilar(kupst_n=(float(n) if n is not None and kupst_var else None),
                        kupst_tolerans=(float(tol) if tol is not None and kupst_var else None),
                        kupst_kgup_yukumlu=bool(seg["kgup_yukumlu"]) if seg["kgup_yukumlu"] is not None else True)


def kural_ozeti(segment: str | None, tarih=None, luy_istisna: bool = False) -> dict:
    """Ekran etiketi için yürürlükteki kural (tarih verilmezse bugün, İstanbul)."""
    r = kr.kural(tarih or pd.Timestamp.now(tz=IST).date(), segment, luy_istisna=luy_istisna)
    return {"tarih": r.tarih.isoformat(), "kural_surumu": r.surum, "rejim": r.edt.rejim, "edt_dayanak": r.edt.dayanak,
            "k": r.edt.k, "l": r.edt.l, "V": r.edt.V, "B": r.edt.B, "AFL": r.edt.AFL, "aylik_toplama": r.edt.toplama,
            "kupst_m": r.kupst.m, "kupst_n": r.kupst.n, "kupst_n_ariza": r.kupst.n_ariza, "kupst_ariza_esigi": r.kupst.ariza_esigi,
            "kupst_taban": r.kupst.taban, "kupst_net_sapma": r.kupst.net_sapma, "kupst_birim": r.kupst.birim, "kupst_dayanak": r.kupst.dayanak,
            "dsg_esik": r.dsg_esik, "dsg_dayanak": r.dsg_dayanak, "belirsiz_2027": r.belirsiz_2027,
            "belirsiz_2027_gerekce": kr.BELIRSIZ_2027_GEREKCE if r.belirsiz_2027 else None}


def simulasyon(tenant_id, plant: dict, gun: int = 90) -> dict:
    from pvquant.services import piyasa_service
    df = program_df(tenant_id, plant["id"], gun)
    idx = pd.DatetimeIndex(df["ts_utc"]) if not df.empty else pd.DatetimeIndex([], tz="UTC")
    fiyat = piyasa_service.fiyatlar(idx)
    pj = _pj(plant.get("params_json"))
    seg = segment_bilgisi(plant.get("params_json"))
    kat = katsayilar(plant.get("params_json"))
    ariza = int(pj.get("ariza_sayisi_ay") or 0); luy = bool(pj.get("luy_istisna"))   # 31.10 (v2.510, Ç3): LÜY m.5(1)(ç),(d),(e) istisnası
    out = hesapla_df(df, fiyat, kat, segment=seg["segment"], ariza_sayisi=ariza, luy_istisna=luy)
    out["oneri"] = oneri_kantili(fiyat, kat)   # v2.287
    out["pencere_gun"] = gun
    out["segment"] = seg; out["luy_istisna"] = luy
    out["kural"] = kural_ozeti(seg["segment"], luy_istisna=luy)
    k = out["kural"]
    kupst_not = ("KÜPST: segment seçilmedi, hesaplanmadı; " if not seg["segment"]
                 else f"KÜPST: {k['kupst_dayanak']}; " if k["kupst_n"] is not None or seg["segment"] == "lisanssiz_dagitim"
                 else "KÜPST: katsayı doğrulanamadı, hesaplanmadı; ")
    out["not"] = ("Program: bir gün önce 15:30'dan önce verilmiş son tahminin P50'si; referans: dün aynı saat. "
                  f"Kural: {k['edt_dayanak']}; " + kupst_not
                  + ("fiyat: EPİAŞ (gerçek saatlik)" if out["fiyat"]["senaryo_saat"] == 0 and out["fiyat"]["epias_saat"] > 0
                     else f"fiyat: {piyasa_service.SENARYO_AD} (EPİAŞ kimliği yok); senaryo saatinde sistem yönü yok → k = l = 0,03 varsayımı")
                  + ("; 1.1.2027 m.110 metni hukuken belirsiz (varsayılan: 2026 rejimi sürer)" if k["belirsiz_2027"] else "")
                  + ". Bu bir yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir.")
    return out


# ----------------------------------------------------------------------------- v2.276: DSG portföy netleştirmesi ----
KANTIL_SECENEK = {"p10": 0.10, "p25": 0.25, "p50": 0.50, "p75": 0.75, "p90": 0.90}


def oneri_kantili(fiyat: pd.DataFrame, kat: d.Katsayilar | None = None) -> dict:
    """v2.287 — SAF: hangi kantili bildirmeli? Gazeteci-çocuk kuralı (ext.optimal_teklif_kantili, kural tarihli):
    τ* = c_fazla / (c_eksik + c_fazla); eksik üretimin birim maliyeti ağırsa düşük kantil. Yön istatistiği EPİAŞ sistem
    yönü sütunundan (SMF > PTF'den ÇIKARILMAZ); yön yoksa öneri verilmez. Senaryo fiyatta yön dağılımı temsili değildir → dürüst tire."""
    if fiyat is None or fiyat.empty or not {"ptf", "smf"} <= set(fiyat.columns):
        return {"durum": "veri_yok", "kantil": None}
    f = fiyat.dropna(subset=["ptf", "smf"])
    if f.empty:
        return {"durum": "veri_yok", "kantil": None}
    if "kaynak" in f and (f["kaynak"] == "senaryo").all():
        return {"durum": "senaryo", "kantil": None,
                "not": "Senaryo fiyatta sistem yönü dağılımı temsili değildir; öneri gerçek fiyat akışıyla (piyasa kimliği) anlamlanır."}
    yon = pd.Series([kr.yon_normalize(v) for v in (f["yon"].values if "yon" in f else [None] * len(f))], index=f.index, dtype=object)
    f = f[yon.notna().values]; yon = yon.dropna()
    if f.empty:
        return {"durum": "yon_eksik", "kantil": None, "not": "EPİAŞ sistem yönü verisi yok; yön fiyattan çıkarılmaz, öneri verilmez."}
    ptf = float(f["ptf"].mean())
    acik = f.loc[(yon == "acik").values, "smf"]; fazla = f.loc[(yon == "fazla").values, "smf"]
    smf_acik = float(acik.mean()) if len(acik) else ptf
    smf_fazla = float(fazla.mean()) if len(fazla) else ptf
    tau = d.optimal_teklif_kantili(ptf, smf_acik, smf_fazla, kat)
    kantil = min(KANTIL_SECENEK, key=lambda k2: abs(KANTIL_SECENEK[k2] - tau))
    return {"durum": "ok", "tau": round(tau, 3), "kantil": kantil, "n_saat": int(len(f)),
            "acik_saat_orani": round(float(len(acik)) / len(f), 3),
            "not": f"Eksik üretimin birim maliyeti ile fazla üretimin birim maliyetinin dengesi; son {len(f)} saatin fiyat ve sistem yönünden."}


def _para_payi(pay: pd.Series, edt_grup: pd.Series) -> float:
    """29.10 — üyenin grubun EDT'sindeki payı: saatlik payların |grup EDT|'siyle ağırlıklı ortalaması (para payı). Grup EDT'si
    her saatte 0 ise (netleşecek bir şey yok) düz ortalama."""
    w = edt_grup.abs()
    return float((pay * w).sum() / w.sum()) if float(w.sum()) > 0 else float(pay.mean())


def dsg_hesapla_df(programlar: dict[str, pd.DataFrame], fiyat: pd.DataFrame, kat: d.Katsayilar | None = None,
                   segmentler: dict[str, str | None] | None = None, ariza_sayilari: dict[str, int] | None = None,
                   dagitim_anahtari: str = "sapma", luy_istisnalar: dict[str, bool] | None = None) -> dict:
    """SAF (v2.502, F-08). programlar[santral] = program_df çıktısı (ts_utc, gercek_kw, kgup_kw). Yürürlükteki DSG kuralı:
    üye eşiği (%10 / %5 / 2027 varsayım) PH = max(A, F) ile; aşan kısım bireysel; KÜPST üye bazında toplanır, netleşmez;
    dengesizlik taşımayan segment portföy dışı. Alan adları sözleşme: ayri_tl = tek başına kayıp, net_tl = DSG kaybı,
    kazanc_tl = fark (ayri − net; «netleşme farkı», vaat değil). Ek: edt_tek_tl, edt_dsg_tl, netlesme_farki_tl, kupst_uye_tl, esik.
    29.10: `dagitim_anahtari` (sapma | esit | uretim; sözleşmesel) ile üye başına edt_dsg_tl / netlesme_farki_tl / pay_pct; Σ üye = grup."""
    K: dict[str, pd.Series] = {}; G: dict[str, pd.Series] = {}
    for ad, df in programlar.items():
        if df is None or df.empty:
            continue
        x = df.dropna(subset=["gercek_kw", "kgup_kw"]).set_index("ts_utc")
        if x.empty:
            continue
        K[ad] = x["kgup_kw"].astype(float) / 1000.0; G[ad] = x["gercek_kw"].astype(float) / 1000.0
    bos = {"santral": 0, "n_saat": 0, "ayri_tl": None, "net_tl": None, "kazanc_tl": None, "gosterge": False}
    if not K:
        return bos
    idx = None
    for ad in K:
        idx = K[ad].index if idx is None else idx.intersection(K[ad].index)
    if idx is None or len(idx) < 24:
        return {**bos, "santral": len(K), "n_saat": int(len(idx) if idx is not None else 0), "not": "ortak saat yetersiz"}
    f = fiyat.reindex(idx); ptf = f["ptf"].astype(float); smf = f["smf"].astype(float)
    yon, fiyat_ozeti = _yon_ve_kaynak(f)
    r = d.dsg_saatlik({a: K[a].loc[idx] for a in K}, {a: G[a].loc[idx] for a in G}, ptf, smf, yon=yon, segmentler=segmentler, ariza_sayilari=ariza_sayilari, luy_istisnalar=luy_istisnalar,
                      dagitim_anahtari=dagitim_anahtari)
    sa = r["saatlik"]
    if sa.empty:
        return {**bos, "santral": len(K), "disi": r["disi"], "not": "portföyde dengesizlik taşıyan üye yok"}
    ayri = float(sa["kayip_tek"].sum()); net = float(sa["kayip_dsg"].sum())
    kupst = float(sa["kupst_uye"].sum(min_count=1)) if sa["kupst_uye"].notna().all() else None
    uye = {a: {"kayip_tl": round(float((v["edm"].clip(lower=0) * (sa["ptf"] - sa["p_poz"]) + (-v["edm"]).clip(lower=0) * (sa["p_neg"] - sa["ptf"])).sum()), 0),
               "edt_tek_tl": round(float(v["edt_tek"].sum()), 0), "edt_bireysel_tl": round(float(v["edt_bireysel"].sum()), 0),
               "kupst_tl": (round(float(v["kupst"].sum()), 0) if v["kupst"].notna().all() else None),
               "sapma_mwh": round(float(v["edm"].abs().sum()), 1), "grup_payi_mwh": round(float(v["grup_payi"].abs().sum()), 1),
               "edt_dsg_tl": round(float(v["edt_dsg"].sum()), 0), "netlesme_farki_tl": round(float(v["netlesme_farki"].sum()), 0),
               "pay_pct": round(100 * _para_payi(v["pay"], sa["edt_grup"]), 1)} for a, v in r["uyeler"].items()}
    return {"santral": len(r["uyeler"]), "n_saat": int(len(idx)), "ayri_tl": round(ayri, 0), "net_tl": round(net, 0),
            "kazanc_tl": round(ayri - net, 0), "kazanc_pct": (round(100 * (ayri - net) / ayri, 1) if ayri > 0 else None),
            "edt_tek_tl": round(float(sa["edt_tek"].sum()), 0), "edt_dsg_tl": round(float(sa["edt_dsg"].sum()), 0),
            "edt_grup_tl": round(float(sa["edt_grup"].sum()), 0), "edt_bireysel_tl": round(float(sa["edt_bireysel"].sum()), 0),
            "netlesme_farki_tl": round(float(sa["netlesme_farki"].sum()), 0), "kupst_uye_tl": (round(kupst, 0) if kupst is not None else None),
            "esik": float(sa["esik"].iloc[-1]), "esik_kaynak": r["esik_kaynak"], "kural_surumu": " | ".join(sorted(set(sa["kural_surumu"]))),
            "dagitim_anahtari": r["dagitim_anahtari"], "dagitim_etiket": d.DAGITIM_ETIKET[r["dagitim_anahtari"]],
            "hesaplanamayan_saat": int((sa["durum"] != "ok").sum()), "disi": r["disi"], "gosterge": False,
            "santral_tl": {a: v["kayip_tl"] for a, v in uye.items()}, "uyeler": uye,
            "uretim_mwh": round(float(sum(G[a].loc[idx].sum() for a in r["uyeler"])), 1),
            "sapma_net_mwh": round(float(sa["grup_edm"].abs().sum()), 1),
            "sapma_ayri_mwh": round(float(sum((G[a].loc[idx] - K[a].loc[idx]).abs().sum() for a in r["uyeler"])), 1),
            "fiyat": fiyat_ozeti}


def portfoy_kupst_ozet(tenant_id, gun: int = 30, dagitim_anahtari: str = "sapma") -> dict:
    """04 #14 (v2.511): dağıtıma bağlı lisanssız santrallerin KÜPST'si GTŞ/toplayıcı UEVÇB'si bazında (params_json.uevcb ile gruplanır;
    boş kod → tek birim varsayımı etiketiyle). Santrallere dağılım anahtarı sözleşmeseldir; mevzuatta tanımsız."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import piyasa_service
    if dagitim_anahtari not in d.PORTFOY_ANAHTARLARI:
        raise ValueError("anahtar " + "|".join(d.PORTFOY_ANAHTARLARI))
    with tenant_baglami(tenant_id) as s:
        santraller = [dict(r._mapping) for r in s.execute(text("SELECT id, name, capacity_kwp, params_json FROM plants WHERE NOT archived ORDER BY name"))]
    uyeler = [p for p in santraller if segment_bilgisi(p.get("params_json"))["segment"] == "lisanssiz_dagitim"]
    bos = {"santral": 0, "uevcbler": [], "kupst_toplam_tl": None, "dagitim_anahtari": dagitim_anahtari,
           "dagitim_etiket": d.PORTFOY_ANAHTAR_ETIKET[dagitim_anahtari], "etiket": d.PORTFOY_ETIKET, "pencere_gun": gun,
           "fiyat": {"epias_saat": 0, "senaryo_saat": 0}}
    if not uyeler:
        return {**bos, "not": "portföyde dağıtıma bağlı lisanssız santral yok"}
    programlar = {p["name"]: program_df(tenant_id, str(p["id"]), gun) for p in uyeler}
    K: dict[str, pd.Series] = {}; G: dict[str, pd.Series] = {}
    for ad, df in programlar.items():
        if df is None or df.empty:
            continue
        x = df.dropna(subset=["gercek_kw", "kgup_kw"]).set_index("ts_utc")
        if x.empty:
            continue
        K[ad] = x["kgup_kw"].astype(float) / 1000.0; G[ad] = x["gercek_kw"].astype(float) / 1000.0
    if not K:
        return {**bos, "santral": len(uyeler), "not": "ortak saat yetersiz"}
    idx = pd.DatetimeIndex([], tz="UTC")
    for k in K.values():
        idx = idx.union(k.index)
    fiyat = piyasa_service.fiyatlar(idx)
    f = fiyat.reindex(idx); ptf = f["ptf"].astype(float); smf = f["smf"].astype(float)
    _, fiyat_ozeti = _yon_ve_kaynak(f)
    uevcb = {p["name"]: (_pj(p.get("params_json")).get("uevcb") or "") for p in uyeler}
    kurulu = {p["name"]: float(p.get("capacity_kwp") or 0) / 1000.0 for p in uyeler}
    r = d.portfoy_kupst_saatlik(K, G, ptf, smf, uevcb=uevcb, kurulu_guc=kurulu, dagitim_anahtari=dagitim_anahtari)
    cikti = []; toplam = 0.0; toplam_var = False
    for kod, g in r["uevcbler"].items():
        sa = g["saatlik"]
        if sa.empty or len(sa) < 24:
            cikti.append({"kod": kod, "kod_tanimsiz": kod == d.UEVCB_TANIMSIZ, "santraller": list(g["uyeler"].keys()) or [a for a in K if (uevcb.get(a) or "") == ("" if kod == d.UEVCB_TANIMSIZ else kod)],
                          "n_saat": int(len(sa)), "kupst_tl": None, "not": "ortak saat yetersiz"})
            continue
        ok = sa["durum"].eq("ok")
        kupst = float(sa.loc[ok, "kupst"].sum()) if ok.any() else None
        if kupst is not None:
            toplam += kupst; toplam_var = True
        uye = {}
        for ad, v in g["uyeler"].items():
            k_ad = float(v.loc[ok, "kupst"].sum()) if ok.any() else None
            uye[ad] = {"kupst_tl": (round(k_ad, 0) if k_ad is not None else None),
                       "pay_pct": (round(100 * k_ad / kupst, 1) if (k_ad is not None and kupst) else round(100 * float(v["pay"].mean()), 1)),
                       "sapma_mwh": round(float(v["sapma"].abs().sum()), 1), "uretim_mwh": round(float(v["gerceklesen"].sum()), 1),
                       "kurulu_mw": round(kurulu.get(ad, 0.0), 3)}
        cikti.append({"kod": kod, "kod_tanimsiz": kod == d.UEVCB_TANIMSIZ, "santraller": list(g["uyeler"].keys()), "n_saat": int(len(sa)),
                      "kupst_tl": (round(kupst, 0) if kupst is not None else None), "udups_mwh": round(float(sa.loc[ok, "udups"].sum()), 1),
                      "kupsm_mwh": round(float(sa.loc[ok, "kupsm"].sum()), 1), "uretim_mwh": round(float(sa["gerceklesen"].sum()), 1),
                      "hesaplanamayan_saat": int((~ok).sum()), "kural_dayanak": g["kural_dayanak"],
                      "kural_surumu": " | ".join(sorted(set(sa["kural_surumu"]))), "uyeler": uye})
    return {**bos, "santral": len(uyeler), "uevcbler": cikti, "kupst_toplam_tl": (round(toplam, 0) if toplam_var else None),
            "etiket": r["etiket"], "fiyat": fiyat_ozeti,
            "not": ("KGÜP sapma tutarı santralde değil, görevli tedarik şirketi ya da toplayıcı UEVÇB'sinde hesaplanır; sapma UEVÇB toplamında "
                    "brüt alınır. Katsayılar 1.11.2026'dan Karar 14907 (tolerans 0,25; fiyat katsayısı 0,01); öncesi belirsiz, o saatler hesaplanmadı. "
                    "Bu bir yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir.")}


def dsg_ozet(tenant_id, gun: int = 30, dagitim_anahtari: str = "sapma") -> dict:
    """Kiracının santralleri: DSG netleşmesi (yürürlükteki kural, F-08). Dengesizlik taşımayan segmentler portföy dışı; segment seçilmemiş
    santral lisanslı güneş kabul edilir ve KÜPST hesaplanamaz olarak işaretlenir."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import piyasa_service
    with tenant_baglami(tenant_id) as s:
        santraller = [dict(r._mapping) for r in s.execute(text("SELECT id, name, params_json FROM plants WHERE NOT archived ORDER BY name"))]
    programlar = {p["name"]: program_df(tenant_id, str(p["id"]), gun) for p in santraller}
    segmentler = {p["name"]: segment_bilgisi(p.get("params_json"))["segment"] for p in santraller}
    ariza = {p["name"]: int(_pj(p.get("params_json")).get("ariza_sayisi_ay") or 0) for p in santraller}
    luy = {p["name"]: bool(_pj(p.get("params_json")).get("luy_istisna")) for p in santraller}   # 31.10 (v2.510, Ç3)
    idx = pd.DatetimeIndex([], tz="UTC")
    for df in programlar.values():
        if df is not None and not df.empty:
            idx = idx.union(pd.DatetimeIndex(df["ts_utc"]))
    fiyat = piyasa_service.fiyatlar(idx) if len(idx) else pd.DataFrame(columns=["ptf", "smf", "yon", "kaynak"])
    out = dsg_hesapla_df(programlar, fiyat, segmentler=segmentler, ariza_sayilari=ariza, dagitim_anahtari=dagitim_anahtari, luy_istisnalar=luy)
    out["pencere_gun"] = gun
    out.setdefault("fiyat", {"epias_saat": int((fiyat["kaynak"] == "epias").sum()) if len(fiyat) else 0, "senaryo_saat": int((fiyat["kaynak"] == "senaryo").sum()) if len(fiyat) else 0})
    out["segment_yok"] = [p["name"] for p in santraller if not segmentler[p["name"]]]
    # 29.10 dil turu: müşteri dili — kural kısa, varsayım açık, dayanak sonda
    out["not"] = ("Dengeden Sorumlu Grup içinde tek santral var; karşılıklı netleşecek sapma bulunmadığından fark sıfırdır. İkinci santral bağlandığında burada görünür." if out["santral"] <= 1
                  else f"Her santralin sapmasının eşik oranı kadarı, %{out.get('esik', 0.05) * 100:.0f} × PH, DSG içinde netleşir; aşan kısım santralin kendisinde kalır. "
                       "KÜPST santral başına ödenir ve DSG içinde netleşmez. Dayanak: DUY m.111. Bu rakamlar yürürlükteki kuralla yapılmış varsayımsal bir yeniden hesaptır; "
                       "santralin satışı KGÜP'e eşit varsayılmıştır. EPİAŞ uzlaştırma sonucu değildir."
                       + (f" Senaryo fiyatlı {out['fiyat']['senaryo_saat']} saatte sistem yönü dengede varsayılmıştır." if out["fiyat"].get("senaryo_saat") else "")
                       + (f" Üyelere dağıtım: {out['dagitim_etiket']}; anahtar DSG sözleşmesinde belirlenir." if out.get("dagitim_etiket") else ""))
    return out
