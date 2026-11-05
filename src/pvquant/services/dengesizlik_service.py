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
# v2.535 dayanak künyeleri [DUY, KARAR_14968, KARAR_14907, TUE] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    "Karar 14968: EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711; "
    'Karar 14907: EPDK Kurul Kararı 14907 (KÜPST, 1.11.2026 çıkarım), RG 19.10.2026-33405; '
    'Teminat U&E: Teminat Usul ve Esasları, Karar 6282-3, RG 28.05.2016-29725; son değişiklik Karar 14954, RG 21.10.2026-33407'
)

IST = "Europe/Istanbul"


def _pj(v) -> dict:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v or {}


URETIM_SECENEKLERI = {"scada": "SCADA ölçümü", "sayac": "sayaç verisi (yüklü saatlerde; kalan saatler SCADA)"}   # v2.526 (P4a-2)


def uretim_secimi(pj) -> str:
    """v2.526 (P4a-2): uzlaştırma yeniden hesabında gerçekleşen üretim kaynağı — params_json.uzlastirma_girdi (scada | sayac); varsayılan scada."""
    v = (_pj(pj) if not isinstance(pj, dict) else pj).get("uzlastirma_girdi")
    return v if v in URETIM_SECENEKLERI else "scada"


def program_df(tenant_id, plant_id, gun: int = 90, uretim: str = "scada") -> pd.DataFrame:
    """DB: ts_utc, gercek_kw, kgup_kw (D-1 15:30 IST öncesi son koşu), naif_kw (dün-aynı-saat), uretim_kaynak (scada | sayac_olculmus | sayac_tahmini).
    v2.526 (P4a-2): uretim='sayac' → sayaç satırı olan saatlerde gercek_kw sayacın veriş kWh'si (1 saat = kW); sayaç olmayan saatlerde SCADA kalır.
    v2.532 (DK-180/DK-195): sayaç satırında çekiş varsa cekis_kw sütunu (UEÇM; 1.11.2026'dan net sapmada düşülür), yoksa NaN.
    SCADA'da olmayan saat sayaçla eklenmez (program ve fiyat o saat için SCADA satırından kurulur; sonraya)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "WITH g AS (SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
            "  AND ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day')) "
            "SELECT g.ts_utc, g.power_kw AS gercek_kw, "
            " (SELECT f.p50_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "   WHERE f.plant_id=:p AND f.ts_utc=g.ts_utc "
            "   AND r.run_at <= ((date_trunc('day', g.ts_utc AT TIME ZONE 'Europe/Istanbul') - INTERVAL '1 day' "
            "     + (CASE WHEN CAST(g.ts_utc AT TIME ZONE 'Europe/Istanbul' AS date) < DATE '2025-01-01' THEN INTERVAL '16 hours' ELSE INTERVAL '15 hours 30 minutes' END)) "   # 03.11: 2024 ve öncesi teslim günü kesimi 16:00 (DK-154); ::date yazımı text() bağlı parametresiyle karışır
            "     AT TIME ZONE 'Europe/Istanbul') "
            "   ORDER BY r.run_at DESC LIMIT 1) AS kgup_kw, "
            " (SELECT s2.power_kw FROM scada_hourly s2 WHERE s2.plant_id=:p AND s2.flag='valid' AND s2.ts_utc = g.ts_utc - INTERVAL '24 hour') AS naif_kw "
            "FROM g ORDER BY g.ts_utc"),
            s.connection(), params={"p": plant_id, "g": gun}, parse_dates=["ts_utc"])
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    df["uretim_kaynak"] = "scada"; df["cekis_kw"] = np.nan
    if uretim == "sayac" and not df.empty:
        from pvquant.services import sayac_service
        sy = sayac_service.sayac_oku(tenant_id, plant_id, df["ts_utc"].min().to_pydatetime(), (df["ts_utc"].max() + pd.Timedelta(hours=1)).to_pydatetime())
        if not sy.empty:
            es = df["ts_utc"].map(sy["veris_kwh"]); var = es.notna()
            nit = df["ts_utc"].map(sy["nitelik"])
            df.loc[var, "gercek_kw"] = pd.to_numeric(es[var], errors="coerce").astype(float)
            df.loc[var, "uretim_kaynak"] = np.where(nit[var].isin(["tahmini", "doldurulmus", "yok"]), "sayac_tahmini", "sayac_olculmus")
            if "cekis_kwh" in sy.columns:   # v2.532: çekiş → UEÇM (yalnız sayaç satırı olan saatlerde)
                df.loc[var, "cekis_kw"] = pd.to_numeric(df["ts_utc"].map(sy["cekis_kwh"])[var], errors="coerce").astype(float).values
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


def pozisyon_ayari(params_json) -> dict:
    """v2.517 (P2a): piyasa pozisyonu (EDM = gerçekleşen − pozisyon) nereden alınır? 'program' (varsayılan: bildirilen/önerilen KGÜP;
    satış programa eşit varsayımı), 'uretim' (üretildiği kadar satış, pay-as-produced ikili anlaşma: dengesizlik alıcıda, yalnız KÜPST kalır),
    'sabit' (her saat sabit MWh baz yük satışı). params_json.pozisyon_kaynagi / pozisyon_sabit_mwh."""
    pj = _pj(params_json); k = pj.get("pozisyon_kaynagi") or "program"
    if k not in ("program", "uretim", "sabit"):
        k = "program"
    sabit = pj.get("pozisyon_sabit_mwh")
    try:
        sabit = float(sabit) if sabit is not None else None
    except (TypeError, ValueError):
        sabit = None
    if k == "sabit" and sabit is None:
        k = "program"
    sabit_tr = f"{sabit:g}".replace(".", ",") if sabit is not None else ""   # dil: ondalık virgül
    etiket = {"program": "pozisyon = program (satış programa eşit varsayımı)", "uretim": "pozisyon = gerçekleşen üretim (üretildiği kadar satış; dengesizlik alıcıda)",
              "sabit": f"pozisyon = sabit {sabit_tr} MWh/saat (baz yük satışı)" if sabit is not None else ""}[k]
    return {"kaynak": k, "sabit_mwh": sabit, "etiket": etiket}


def bildirilen_serisi(tenant_id, plant_id, params_json=None, gun: int = 90) -> pd.Series:
    """v2.517 (P2a): müşterinin TPYS'ye bildirdiğini beyan ettiği KGÜP dosyaları (kgup_surum kaynak='musteri', teslim günü başına son sürüm)
    → saatlik MWh serisi (UTC index; İstanbul günü 00:00'dan 24 saat). Dosya yoksa boş seri: o saatlerde program PVQuant önerisine düşer.
    TPYS kabulü doğrulanmaz (beyan); hesaba giren program «bildirilen» etiketiyle taşınır."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import kgup_arsiv_service as ka
    from pvquant.ext.turkiye.kgup import Sablon
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT DISTINCT ON (teslim_gunu) teslim_gunu, dosya FROM kgup_surum WHERE plant_id=:p AND kaynak='musteri' "
            "AND teslim_gunu >= (CURRENT_DATE - (:g * INTERVAL '1 day')) ORDER BY teslim_gunu, surum DESC"), {"p": plant_id, "g": int(gun)}).fetchall()
    sab = Sablon.params_json_dan(_pj(params_json))
    parcalar = []
    for r in rows:
        try:
            t = ka.csv_oku(bytes(r.dosya), sab)
        except Exception:  # noqa: BLE001 — şablon sonradan değiştiyse sezgisel okuma
            try:
                t = ka.csv_oku(bytes(r.dosya))
            except Exception:  # noqa: BLE001 — okunamayan dosya hesaba girmez
                continue
        idx = pd.date_range(pd.Timestamp(r.teslim_gunu).tz_localize(IST), periods=24, freq="h").tz_convert("UTC")
        parcalar.append(pd.Series(t["kgup_mwh"].values[:len(idx)].astype(float), index=idx))
    return pd.concat(parcalar).sort_index() if parcalar else pd.Series(dtype=float)


def saatlik_hesap(df: pd.DataFrame, fiyat: pd.DataFrame, kat: d.Katsayilar | None = None, segment: str | None = None,
                  ariza_sayisi: int = 0, luy_istisna: bool = False, bildirilen_mwh: pd.Series | None = None,
                  pozisyon: dict | None = None):
    """SAF çekirdek (v2.517): program = bildirilen KGÜP (varsa) yoksa PVQuant önerisi; pozisyon ayara göre. Dönüş (pv, fiyat_ozeti, x, ay_naif)
    ya da hepsi None (boş). v2.532 (DK-180/DK-195, Karar 14907): df'te cekis_kw varsa o saatlerde UEÇM = çekiş MWh, motor 1.11.2026'dan net sapmada
    düşer; yoksa UEÇM 0 (net sapma brüt sapmaya eşit) — pv'ye uecm sütunu."""
    kat = kat or d.Katsayilar()
    if df is None or df.empty:
        return None, None, None, None
    x = df.dropna(subset=["gercek_kw", "kgup_kw"]).copy().set_index("ts_utc")
    if x.empty:
        return None, None, None, None
    f = fiyat.reindex(x.index)
    yon, fiyat_ozeti = _yon_ve_kaynak(f)
    ger = x["gercek_kw"].astype(float) / 1000.0; oneri = x["kgup_kw"].astype(float) / 1000.0
    if bildirilen_mwh is not None and len(bildirilen_mwh):
        b = bildirilen_mwh.reindex(x.index).astype(float)
        prog = b.where(b.notna(), oneri); kaynak = np.where(b.notna(), "bildirilen", "oneri")
    else:
        prog = oneri; kaynak = np.full(len(x), "oneri", dtype=object)
    poz = pozisyon or {"kaynak": "program", "sabit_mwh": None}
    poz_s = (ger if poz["kaynak"] == "uretim" else pd.Series(float(poz["sabit_mwh"]), index=x.index) if poz["kaynak"] == "sabit" else None)
    ptf = f["ptf"].astype(float); smf = f["smf"].astype(float)
    uecm = (pd.to_numeric(x["cekis_kw"], errors="coerce").astype(float) / 1000.0) if "cekis_kw" in x.columns else pd.Series(np.nan, index=x.index)
    pv = d.saatlik(prog, ger, ptf, smf, kat, yon=yon, segment=segment, ariza_sayisi=ariza_sayisi, luy_istisna=luy_istisna,
                   pozisyon_mwh=poz_s, budup_mwh=prog, uecm_mwh=uecm.fillna(0.0))
    pv["program_kaynak"] = kaynak; pv["oneri"] = oneri.values; pv["uecm"] = uecm.values
    naif_var = x["naif_kw"].notna(); ay_naif = None
    if naif_var.sum() >= 24:
        xn = x[naif_var]
        nv = d.saatlik(xn["naif_kw"].astype(float) / 1000.0, ger.loc[xn.index], ptf.loc[xn.index], smf.loc[xn.index], kat,
                       yon=yon.loc[xn.index], segment=segment, ariza_sayisi=ariza_sayisi)
        ay_naif = d.aylik_karne(nv)
    return pv, fiyat_ozeti, x, ay_naif


def teminat_gostergesi(pv: pd.DataFrame, risk_katsayisi: float | None = None) -> dict:
    """v2.522 (P2b, IH-033/K-05): EPİAŞ dengesizlik teminatı tanımıyla gösterge — geçmiş 3 ayın aylık en yüksek negatif enerji dengesizlik
    miktarının mutlak değeri (MWh) × geçmiş 12 aylık dönemin aylık ortalama SMF'lerinin aritmetik ortalaması × risk katsayısı (02-08; EPİAŞ teminat
    sayfası). Risk katsayısı değeri BULUNAMADI → Santral ayarlarından girilir; girilmemişse tutar yok. Teminat Hesaplama Yöntemi m.7'deki «aylık
    ağırlıklı ortalama SMF» piyasa geneli dengesizlik miktarıyla ağırlıklıdır (03.11.2026 doğrulama arşivi DK-537); o veri burada yok → saatlik SMF'nin
    aylık düz ortalaması alınır ve «yaklaşık» diye etiketlenir. Kalem 'doğrulanmamış' etiketiyle sunulur; EPYS/Takasbank esastır."""
    bos = {"edm_neg_max_mwh": None, "edm_ay": None, "smf_ort_tl_mwh": None, "smf_ay_sayisi": 0, "risk_katsayisi": risk_katsayisi, "tutar_tl": None,
           "dogrulanmis": False, "formul": "3 ayın en yüksek aylık negatif EDM (MWh) × 12 aylık ortalama SMF (TL/MWh) × risk katsayısı",
           "smf_agirlik": "düz aylık ortalama (yaklaşık; Yöntem m.7 piyasa geneli dengesizlik ağırlıklı ortalama ister)",
           "not": ("EPİAŞ dengesizlik teminatı tanımı (Teminat Hesaplama Yöntemi; risk katsayısının başlangıç değeri 1,5 — Teminat Usul ve Esasları Geçici m.1; "
                   "güncel değer piyasa işletmecisinin katılımcı portalında ilan edilir, kamuya açık kaynakta bulunamadı → Santral ayarlarından girilir; "
                   "SMF ortalaması ağırlıksız, yaklaşık). Gösterge; EPYS ve Takasbank tutarları esastır.")}
    if pv is None or pv.empty:
        return bos
    x = pv.copy(); x.index = x.index.tz_convert(IST)
    edm_neg = (-x["sapma"]).clip(lower=0).resample("ME").sum()
    ay_basi = pd.Timestamp.now(tz=IST).normalize().replace(day=1)
    tam = edm_neg[edm_neg.index < ay_basi]   # yalnız kapanmış aylar
    son3 = (tam if len(tam) else edm_neg).tail(3)
    smf_ay = x["smf"].astype(float).resample("ME").mean().dropna().tail(12)
    if son3.empty or smf_ay.empty:
        return bos
    en = son3.idxmax()
    out = {**bos, "edm_neg_max_mwh": round(float(son3.max()), 1), "edm_ay": en.strftime("%Y-%m"), "ay_sayisi": int(len(son3)),
           "smf_ort_tl_mwh": round(float(smf_ay.mean()), 2), "smf_ay_sayisi": int(len(smf_ay))}
    if risk_katsayisi is not None and risk_katsayisi > 0:
        out["tutar_tl"] = round(float(son3.max()) * float(smf_ay.mean()) * float(risk_katsayisi), 0)
    return out


def hesapla_df(df: pd.DataFrame, fiyat: pd.DataFrame, kat: d.Katsayilar | None = None, segment: str | None = None,
               ariza_sayisi: int = 0, luy_istisna: bool = False, bildirilen_mwh: pd.Series | None = None,
               pozisyon: dict | None = None, risk_katsayisi: float | None = None) -> dict:
    """SAF. df: ts_utc, gercek_kw, kgup_kw (PVQuant önerisi), naif_kw (kW ≈ kWh/saat → MWh = /1000). fiyat: aynı ts index'li ptf/smf/yon/kaynak.
    v2.517 (P2a): bildirilen_mwh verilirse o saatlerde program = müşterinin bildirdiği KGÜP (BUDÜP), kalanında öneri; pozisyon ayara göre.
    Çıktı: aylar[] ve toplam — EDT (edt_neg/edt_poz/edta/edtb), kayıp (dengesizlik_tl), KÜPST (kupst_tl) AYRI; tolerans dışı saat ve KÜPSM MWh;
    pvquant_tl = kayıp + KÜPST («uzlaştırma kalemleri toplamı»; KÜPST hesaplanamıyorsa None); program: kaynak sayımı ve pozisyon ayarı."""
    kat = kat or d.Katsayilar()
    poz = pozisyon or {"kaynak": "program", "sabit_mwh": None, "etiket": "pozisyon = program (satış programa eşit varsayımı)"}
    bos = {"gun_sayisi": 0, "aylar": [], "toplam": None, "hesaplanamayan_saat": 0, "kural_surumu": None,
           "fiyat": {"epias_saat": 0, "senaryo_saat": 0, "yon_varsayilan_saat": 0, "yon_eksik_saat": 0},
           "program": {"bildirilen_saat": 0, "oneri_saat": 0, "bildirilen_gun": 0, "pozisyon": poz}}
    pv, fiyat_ozeti, x, ay_naif = saatlik_hesap(df, fiyat, kat, segment, ariza_sayisi, luy_istisna, bildirilen_mwh, poz)
    if pv is None:
        return bos
    ay_pv = d.aylik_karne(pv)
    pvl = pv.copy(); pvl.index = pvl.index.tz_convert(IST)
    ek = pvl.assign(tol=(pvl["kupsm"] > 1e-9).astype(int), bil=(pvl["program_kaynak"] == "bildirilen").astype(int)).resample("ME").agg(
        {"tol": "sum", "kupsm": "sum", "bil": "sum"})
    out_ay = []
    for ay, r in ay_pv.iterrows():
        kn = (float(ay_naif.loc[ay, "toplam_maliyet"]) if ay_naif is not None and ay in ay_naif.index else None)
        top = _r0(r["toplam_maliyet"])
        e = ek.loc[ay] if ay in ek.index else None
        out_ay.append({"ay": ay.strftime("%Y-%m"), "uretim_mwh": round(float(r["gerceklesen"]), 1), "sapma_mwh": round(float(r["sapma"]), 1),
                       "kupst_tl": _r0(r["kupst"]), "dengesizlik_tl": _r0(r["dengesizlik_maliyeti"]),   # v2.275; kayıp (programa göre)
                       "edt_neg_tl": _r0(r["edt_neg"]), "edt_poz_tl": _r0(r["edt_poz"]), "edta_tl": _r0(r["edta"]), "edtb_tl": _r0(r["edtb"]),
                       "referans_gelir_tl": round(float(r["referans_gelir"]), 0), "pvquant_tl": top,
                       "naif_tl": _r0(kn), "kurtarilan_tl": (_r0(kn - float(r["toplam_maliyet"])) if kn is not None and top is not None else None),
                       "gelir_oran_pct": round(float(r["maliyet_gelir_orani"]) * 100, 2) if pd.notna(r["maliyet_gelir_orani"]) else None,
                       "tl_per_mwh": round(float(r["tl_per_mwh"]), 1) if pd.notna(r["tl_per_mwh"]) else None,
                       "hesaplanamayan_saat": int(r["hesaplanamayan_saat"]), "kural_surumu": str(r["kural_surumu"]),
                       # v2.517 (P2a): tolerans dışı saat (KÜPSM > 0) ve KÜPSM toplamı; bildirilen programla hesaplanan saat
                       "tolerans_disi_saat": int(e["tol"]) if e is not None else 0, "kupsm_mwh": round(float(e["kupsm"]), 3) if e is not None else 0.0,
                       "bildirilen_saat": int(e["bil"]) if e is not None else 0})
    top_pv = float(pv["toplam_maliyet"].sum(min_count=1)) if pv["toplam_maliyet"].notna().any() else float("nan")
    top_ref = float(pv["referans_gelir"].sum())
    teminat = teminat_gostergesi(pv, risk_katsayisi)   # v2.522 (P2b): mevzuat formülü (3 ay en yüksek negatif EDM × 12 ay SMF ort. × risk katsayısı); doğrulanmadı
    teminat_tl = teminat["tutar_tl"]
    top_naif = float(ay_naif["toplam_maliyet"].sum(min_count=1)) if ay_naif is not None and ay_naif["toplam_maliyet"].notna().any() else None
    kupst_top = float(pv["kupst"].sum(min_count=1)) if pv["kupst"].notna().any() and not pv["kupst"].isna().any() else None
    bil = int((pv["program_kaynak"] == "bildirilen").sum())
    uecm_saat = int(pv["uecm"].notna().sum()) if "uecm" in pv else 0   # v2.532: çekişi bilinen saat (sayaç satırı)
    net_saat = int(pv["net_sapma"].astype(bool).sum()) if "net_sapma" in pv else 0
    return {"gun_sayisi": int(pd.Series(x.index.tz_convert(IST).date).nunique()), "aylar": out_ay,
            "toplam": {"pvquant_tl": _r0(top_pv), "kupst_tl": _r0(kupst_top),   # v2.275
                       "dengesizlik_tl": round(float(pv["dengesizlik_maliyeti"].sum()), 0),
                       "edt_neg_tl": round(float(pv["edt_neg"].fillna(0).sum()), 0), "edt_poz_tl": round(float(pv["edt_poz"].fillna(0).sum()), 0),
                       "edta_tl": round(float(ay_pv["edta"].sum()), 0), "edtb_tl": round(float(ay_pv["edtb"].sum()), 0),
                       "teminat_tl": teminat_tl,   # v2.287 → v2.522 mevzuat formülü (katsayı yoksa None)
                       "teminat": teminat,   # v2.522 (P2b)
                       "naif_tl": _r0(top_naif),
                       "kurtarilan_tl": (_r0(top_naif - top_pv) if top_naif is not None and not np.isnan(top_pv) else None),
                       "gelir_oran_pct": round(top_pv / top_ref * 100, 2) if top_ref and not np.isnan(top_pv) else None, "referans_gelir_tl": round(top_ref, 0),
                       "tolerans_disi_saat": int((pv["kupsm"] > 1e-9).sum()), "kupsm_mwh": round(float(pv["kupsm"].sum()), 3)},   # v2.517
            "program": {"bildirilen_saat": bil, "oneri_saat": int(len(pv) - bil),
                        "bildirilen_gun": int(pd.Series(pv.index[pv["program_kaynak"] == "bildirilen"].tz_convert(IST).date).nunique()) if bil else 0,
                        "pozisyon": poz,
                        "uecm_saat": uecm_saat, "net_sapma_saat": net_saat,   # v2.532 (DK-180/195): UEÇM sayaç çekişinden; kalan saatlerde 0
                        "uecm_etiketi": (f"UEÇM {uecm_saat} saatte sayaç çekişinden, kalan {len(pv) - uecm_saat} saatte 0 varsayıldı" if uecm_saat
                                         else "UEÇM (uzlaştırmaya esas çekiş miktarı) verisi yok, 0 varsayıldı: net sapma brüt sapmaya eşit")
                        if net_saat else None},   # v2.517 (P2a)
            "fiyat": fiyat_ozeti, "hesaplanamayan_saat": int((pv["durum"] != "ok").sum()),
            "kural_surumu": " | ".join(sorted(set(pv["kural_surumu"]))),
            "katsayilar": {"k": 0.03, "l": 0.03, "k_yon": {"acik": 0.06, "fazla": 0.03, "dengede": 0.03} if (pv["rejim"] == "2026").any() else {"acik": 0.03, "fazla": 0.03, "dengede": 0.03},
                           "l_yon": {"acik": 0.03, "fazla": 0.06, "dengede": 0.03} if (pv["rejim"] == "2026").any() else {"acik": 0.03, "fazla": 0.03, "dengede": 0.03},
                           "kupst_n": (float(pv["kupst_n"].iloc[-1]) if pd.notna(pv["kupst_n"].iloc[-1]) else None),
                           "kupst_tolerans": (float(pv["kupst_m"].iloc[-1]) if pd.notna(pv["kupst_m"].iloc[-1]) else None),
                           # v2.535 (resmî/senaryo ayrımı): KÜPST n/tolerans santral ayarından geçersiz kılındıysa açıkça işaretlenir;
                           # k/l, V, B, AFL ve DSG eşiği her durumda kural tablosundandır (ayarlardan değişmez)
                           "kupst_gecersiz_kilma": bool(kat.kupst_n is not None or kat.kupst_tolerans is not None),
                           "kupst_kaynak": ("santral ayarı (geçersiz kılma)" if (kat.kupst_n is not None or kat.kupst_tolerans is not None)
                                            else "kural tablosu")}}


DOKUM_KOLONLAR = ["zaman", "program_mwh", "program_kaynak", "pozisyon_mwh", "gerceklesen_mwh", "sapma_mwh", "ptf_tl_mwh", "smf_tl_mwh", "yon",
                  "k", "l", "fiyat_eksik_tl_mwh", "fiyat_fazla_tl_mwh", "edt_borc_tl", "edt_alacak_tl", "edt_net_tl", "kupsm_mwh", "kupst_tl",
                  "toplam_tl", "kural_surumu", "durum"]
YEKDEM_KOLONLAR = ["yek_fiyat_tl_mwh", "m23_6", "yekdem_disi_mwh", "yekdem_disi_tl"]   # v2.520 (P5a): yalnız lisanslı YEKDEM + tarife yekdem


def dokum_df(pv: pd.DataFrame, ek: pd.DataFrame | None = None) -> pd.DataFrame:
    """v2.517 (P2a): saatlik uzlaştırma dökümü (İstanbul saati). Her satır: program ve kaynağı, pozisyon, gerçekleşen, sapma, fiyatlar, yön,
    yöne bağlı k/l, EDT borç/alacak/net, KÜPSM (tolerans üstü sapma MWh), KÜPST, toplam, kural sürümü, durum (ok / yon_eksik / kupst_hesaplanamaz)."""
    if pv is None or pv.empty:
        return pd.DataFrame(columns=DOKUM_KOLONLAR)
    z = pv.index.tz_convert(IST)
    out = pd.DataFrame({"zaman": [t.strftime("%Y-%m-%d %H:%M") for t in z],
                        "program_mwh": pv["kgup"].round(3).values, "program_kaynak": pv["program_kaynak"].values,
                        "pozisyon_mwh": pv["pozisyon"].round(3).values, "gerceklesen_mwh": pv["gerceklesen"].round(3).values,
                        "sapma_mwh": pv["sapma"].round(3).values, "ptf_tl_mwh": pv["ptf"].round(2).values, "smf_tl_mwh": pv["smf"].round(2).values,
                        "yon": pv["yon"].values, "k": pv["k"].values, "l": pv["l"].values,
                        "fiyat_eksik_tl_mwh": pv["p_neg"].round(2).values, "fiyat_fazla_tl_mwh": pv["p_poz"].round(2).values,
                        "edt_borc_tl": pv["edt_neg"].round(2).values, "edt_alacak_tl": pv["edt_poz"].round(2).values, "edt_net_tl": pv["edt_net"].round(2).values,
                        "kupsm_mwh": pv["kupsm"].round(3).values, "kupst_tl": pv["kupst"].round(2).values, "toplam_tl": pv["toplam_maliyet"].round(2).values,
                        "kural_surumu": pv["kural_surumu"].values, "durum": pv["durum"].values})
    out = out[DOKUM_KOLONLAR]
    if ek is not None and not ek.empty:   # v2.520 (P5a): YEKDEM sütunları (yekdem_service.dokum_ek)
        e = ek.reindex(pv.index)
        out["yek_fiyat_tl_mwh"] = e["yek_fiyat_tl_mwh"].astype(float).round(2).values; out["m23_6"] = e["m23_6"].values
        out["yekdem_disi_mwh"] = e["yekdem_disi_mwh"].astype(float).round(3).values; out["yekdem_disi_tl"] = e["yekdem_disi_tl"].astype(float).round(2).values
    return out


DOKUM_NOTU_SAYAC = (" uretim_kaynak: sayac_olculmus = o saatin gerçekleşeni yüklü sayaç dosyasındaki ölçülmüş veriş kWh (EPYS > OSOS > MASS > elle), "
                    "sayac_tahmini = sayaç satırı tahmini/doldurulmuş/veri yok nitelikli, scada = sayaç satırı yok, SCADA ölçümü. Sayaç verisi uzlaştırmaya esas "
                    "UEVM ile aynı olup olmadığı PVQuant'tan doğrulanmaz. 1.11.2026'dan net sapmada (Karar 14907) sayaç satırındaki çekiş UEÇM olarak düşülür; "
                    "çekiş sütunu olmayan saatlerde UEÇM 0 varsayılır.")
DOKUM_NOTU = ("Yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir. program_kaynak: bildirilen = TPYS'ye bildirildiği beyan edilerek yüklenen KGÜP "
              "(TPYS kabulü doğrulanmaz); oneri = PVQuant'ın bir gün önce 15:30'dan önceki son tahmininin P50'si. sapma = gerçekleşen − pozisyon (EDM). "
              "edt_borc = eksik üretim tutarı (öder), edt_alacak = fazla üretim tutarı (alır; düşük fiyat saatinde negatif olabilir). "
              "kupsm = tolerans (m × program) üstündeki sapma MWh; kupst = kupsm × max(taban; PTF; SMF) × n. Saatler Türkiye saatidir (Europe/Istanbul). "
              "DUY m.71(3): teklifin gerçek zamandan yarım saat öncesine kadar talimatlandırılması ya da UEVÇB'nin kısıt listesine alınması hâlinde KGÜP o saatte "
              "kesinleşmiş program sayılır; PVQuant kısıt listesini ve T−30 talimatlarını veri olarak almaz, bu saatler dökümde ayrıca işaretlenmez (program sapması olduğu gibi görünür).")
DOKUM_NOTU_TALIMAT = (" talimat: Olay kaydındaki yük atma (yat), yük alma (yal) ve acil durum kesmesi (acil) saatleri. Bu saatlerde program sapması talimattan kaynaklanır; "
                      "talimat miktarı veri olarak alınmadığından o saatin sapma tutarı güvenilir değildir — talimat uzlaştırması EPİAŞ'ta ayrıca yapılır (DUY m.75–78; "
                      "lisanssızda tutar m.75(3) ile yansıtılır). Sapma hesaba olduğu gibi girer, işaret bilgi amaçlıdır.")   # v2.539 (EK-3 DK-056, kanıt A)
TALIMAT_TURLERI = {"talimat_yat": "yat", "talimat_yal": "yal", "acil_kesme": "acil"}


def talimat_isareti(olaylar: list[dict], idx: pd.DatetimeIndex) -> pd.Series:
    """v2.539 (DK-056) — SAF: saat dilimi [t, t+1 sa) olay aralığıyla kesişiyorsa tür kodu (yat | yal | acil), yoksa boş. Bitişi olmayan olay
    dizinin sonuna kadar sürer; aynı saatte birden çok olay varsa ilk başlayan yazılır."""
    s = pd.Series("", index=idx, dtype=object)
    if olaylar is None or len(idx) == 0:
        return s
    son = idx[-1] + pd.Timedelta(hours=1)
    for o in sorted(olaylar, key=lambda o: o["baslangic"]):
        kod = TALIMAT_TURLERI.get(o.get("tur"))
        if not kod:
            continue
        bas = pd.Timestamp(o["baslangic"]); bit = pd.Timestamp(o["bitis"]) if o.get("bitis") else son
        if bas.tzinfo is None:
            bas = bas.tz_localize(IST)
        if bit.tzinfo is None:
            bit = bit.tz_localize(IST)
        m = ((idx + pd.Timedelta(hours=1)) > bas) & (idx < bit) & (s == "")
        s[m] = kod
    return s


def _talimat_olaylari(tenant_id, plant: dict, idx: pd.DatetimeIndex) -> list[dict]:
    """Olay kaydından döküm aralığındaki talimat/acil kesme olayları; olay tablosu yoksa boş."""
    try:
        from pvquant.services import olay_service
        return olay_service.aralik(tenant_id, plant["id"], idx[0].to_pydatetime(), (idx[-1] + pd.Timedelta(hours=1)).to_pydatetime(), turler=list(TALIMAT_TURLERI))
    except Exception:   # noqa: BLE001
        return []
DOKUM_NOTU_YEKDEM = (" YEKDEM sütunları (lisanslı YEKDEM, tarife YEKDEM): yek_fiyat = o saatin YEK fiyatı (+ yerli katkı; Cetvel I günün TCMB alış kuruyla, 7189 "
                     "ayın EPİAŞ ilanı); m23_6 = YEK Yön. m.23(6) işareti (evet: PTF ya da SMF < V ve sistem fazlası saatinde program üstü üretim ve PTF < YEK "
                     "fiyatı → YEKDEM dışı; ptf_yek_ustu: şartlar var, PTF ≥ YEK fiyatı; kapsam_disi: 19.10.2026 öncesi; EPİAŞ uygulaması belirsiz, talimat "
                     "saatleri dâhil değil); yekdem_disi_mwh = program üstü MWh; yekdem_disi_tl = MWh × (YEK fiyatı − 0,98 × PTF).")


def dokum_notu(df: pd.DataFrame) -> str:
    """v2.520: YEKDEM sütunları varsa not ekiyle."""
    return DOKUM_NOTU + (DOKUM_NOTU_YEKDEM if "m23_6" in df.columns else "") + (DOKUM_NOTU_SAYAC if "uretim_kaynak" in df.columns else "") + (DOKUM_NOTU_TALIMAT if "talimat" in df.columns else "")


def dokum_csv(df: pd.DataFrame) -> str:
    """UTF-8 BOM'lu, noktalı virgül ayraçlı, ondalık virgüllü CSV (Türkçe Excel doğrudan açar); ilk satır not."""
    import io
    buf = io.StringIO()
    buf.write("# " + dokum_notu(df) + "\n")
    df.to_csv(buf, sep=";", decimal=",", index=False, lineterminator="\n")
    return "\ufeff" + buf.getvalue()


def dokum_xlsx(df: pd.DataFrame, baslik: str, aylar: list[dict] | None = None) -> bytes:
    """İki sayfa: Saatlik (döküm) ve Aylar (özet) + Not."""
    import io
    import xlsxwriter
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    kalin = wb.add_format({"bold": True}); sayi3 = wb.add_format({"num_format": "#,##0.000"}); para = wb.add_format({"num_format": "#,##0.00"})
    ws = wb.add_worksheet("Saatlik")
    kol = list(df.columns)   # v2.520: YEKDEM sütunları varsa 25
    ws.write(0, 0, baslik, kalin); ws.write(1, 0, dokum_notu(df))
    for j, c in enumerate(kol):
        ws.write(3, j, c, kalin)
    for i, row in enumerate(df.itertuples(index=False), start=4):
        for j, v in enumerate(row):
            if isinstance(v, (float, np.floating)):
                if np.isnan(v):
                    continue
                ws.write_number(i, j, float(v), sayi3 if kol[j].endswith("_mwh") else para)
            elif isinstance(v, (int, np.integer)):
                ws.write_number(i, j, int(v))
            else:
                ws.write(i, j, "" if v is None else str(v))
    ws.set_column(0, 0, 17); ws.set_column(1, len(kol) - 1, 13)
    if aylar:
        wa = wb.add_worksheet("Aylar")
        kol = ["ay", "uretim_mwh", "sapma_mwh", "edt_neg_tl", "edt_poz_tl", "edta_tl", "edtb_tl", "dengesizlik_tl", "kupst_tl", "pvquant_tl",
               "tolerans_disi_saat", "kupsm_mwh", "bildirilen_saat", "hesaplanamayan_saat", "kural_surumu"]
        for j, c in enumerate(kol):
            wa.write(0, j, c, kalin)
        for i, a in enumerate(aylar, start=1):
            for j, c in enumerate(kol):
                v = a.get(c)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    wa.write_number(i, j, float(v))
                else:
                    wa.write(i, j, "" if v is None else str(v))
        wa.set_column(0, len(kol) - 1, 14)
    wb.close()
    return buf.getvalue()


def _girdiler(tenant_id, plant: dict, gun: int, uretim: str | None = None) -> dict:
    """v2.520: simülasyon, döküm ve YEKDEM özeti aynı girdilerden (program, fiyat, katsayılar, segment, bildirilen seri, pozisyon).
    v2.526: uretim (scada | sayac) verilmezse santral ayarı (uzlastirma_girdi)."""
    from pvquant.services import piyasa_service
    uretim = uretim if uretim in URETIM_SECENEKLERI else uretim_secimi(plant.get("params_json"))
    df = program_df(tenant_id, plant["id"], gun, uretim)
    idx = pd.DatetimeIndex(df["ts_utc"]) if not df.empty else pd.DatetimeIndex([], tz="UTC")
    fiyat = piyasa_service.fiyatlar(idx)
    pj = _pj(plant.get("params_json")); seg = segment_bilgisi(plant.get("params_json")); kat = katsayilar(plant.get("params_json"))
    return {"df": df, "fiyat": fiyat, "kat": kat, "segment": seg["segment"], "ariza_sayisi": _ariza(tenant_id, plant),
            "luy_istisna": bool(pj.get("luy_istisna")), "bildirilen_mwh": bildirilen_serisi(tenant_id, plant["id"], pj, gun), "pozisyon": pozisyon_ayari(pj), "pj": pj, "uretim": uretim}


def saatlik_pv(tenant_id, plant: dict, gun: int = 90) -> pd.DataFrame | None:
    """v2.520 (P5a): saatlik hesap çıktısı (pv) — YEKDEM m.23(6) işareti için; boşsa None."""
    g = _girdiler(tenant_id, plant, gun)
    pv, _, _, _ = saatlik_hesap(g["df"], g["fiyat"], g["kat"], g["segment"], g["ariza_sayisi"], g["luy_istisna"], g["bildirilen_mwh"], g["pozisyon"])
    return pv


def yekdem_eki(pj: dict, segment: str | None, pv: pd.DataFrame | None) -> pd.DataFrame | None:
    """v2.520 (P5a): lisanslı YEKDEM + tarife yekdem ise döküme YEKDEM sütunları; fiyat verisi/DB yoksa None (döküm 21 sütun kalır)."""
    if pv is None or pv.empty or segment != "lisansli_yekdem" or (pj.get("tarife") or {}).get("tip") != "yekdem":
        return None
    try:
        from pvquant.services import yekdem_service
        return yekdem_service.dokum_ek(pj, pv)
    except Exception:   # noqa: BLE001 — kur/ilan tablosu yoksa döküm YEKDEM'siz iner
        return None


def dokum(tenant_id, plant: dict, gun: int = 90, uretim: str | None = None) -> tuple[pd.DataFrame, dict]:
    """v2.517 (P2a): simülasyonla aynı girdilerden saatlik döküm + ay özeti (dışa aktarım için). v2.520: lisanslı YEKDEM'de YEKDEM sütunları.
    v2.526 (P4a-2): uretim='sayac' (ya da santral ayarı) → sayaç satırı olan saatlerde gerçekleşen sayaçtan; döküme «uretim_kaynak» sütunu ve özete sayım."""
    g = _girdiler(tenant_id, plant, gun, uretim)
    pv, _, _, _ = saatlik_hesap(g["df"], g["fiyat"], g["kat"], g["segment"], g["ariza_sayisi"], g["luy_istisna"], g["bildirilen_mwh"], g["pozisyon"])
    ozet = hesapla_df(g["df"], g["fiyat"], g["kat"], segment=g["segment"], ariza_sayisi=g["ariza_sayisi"], luy_istisna=g["luy_istisna"],
                      bildirilen_mwh=g["bildirilen_mwh"], pozisyon=g["pozisyon"])
    df = dokum_df(pv, yekdem_eki(g["pj"], g["segment"], pv))
    if pv is not None and not pv.empty and "kaynak" in g["fiyat"]:   # v2.522 (P2b): mutabakat için saat bazında fiyat kaynağı (epias / senaryo); dışa aktarıma girmez
        ozet["saat_fiyat_kaynak"] = [str(k) for k in g["fiyat"]["kaynak"].reindex(pv.index).fillna("yok").values]
    uk = {"secim": g["uretim"], "etiket": URETIM_SECENEKLERI[g["uretim"]], "sayac_olculmus_saat": 0, "sayac_tahmini_saat": 0, "scada_saat": 0}
    if pv is not None and not pv.empty and "uretim_kaynak" in g["df"].columns:
        kaynak = g["df"].set_index("ts_utc")["uretim_kaynak"].reindex(pv.index).fillna("scada")
        uk["sayac_olculmus_saat"] = int((kaynak == "sayac_olculmus").sum()); uk["sayac_tahmini_saat"] = int((kaynak == "sayac_tahmini").sum()); uk["scada_saat"] = int((kaynak == "scada").sum())
        ozet["saat_uretim_kaynak"] = [str(k) for k in kaynak.values]
        if g["uretim"] == "sayac":
            df["uretim_kaynak"] = kaynak.values   # dışa aktarımda hangi saatin sayaç, hangisinin SCADA olduğu görünür
    ozet["uretim_kaynak"] = uk
    ozet["talimat_saat"] = 0   # v2.539 (DK-056): talimat/acil kesme saatleri işaretlenir, hesap değişmez
    if pv is not None and not pv.empty:
        t = talimat_isareti(_talimat_olaylari(tenant_id, plant, pv.index), pv.index)
        if (t != "").any():
            df["talimat"] = t.values
            ozet["talimat_saat"] = int((t != "").sum()); ozet["talimat_notu"] = DOKUM_NOTU_TALIMAT.strip()
            ozet["saat_talimat"] = [str(v) for v in t.values]
    return df, ozet

def _risk_katsayisi(pj: dict) -> float | None:
    """v2.522 (P2b): params_json.teminat_risk_katsayisi (0–10); yoksa None → teminat tutarı verilmez."""
    try:
        v = float(pj.get("teminat_risk_katsayisi")) if pj.get("teminat_risk_katsayisi") not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return v if v is not None and 0 < v <= 10 else None


def program_bildirilenle(tenant_id, plant_id: str, pj: dict, df: pd.DataFrame, gun: int) -> tuple[pd.DataFrame, dict]:
    """v2.522 (P2b; v2.517 sınırı kapandı): DSG ve UEVÇB KÜPST hesaplarında program = müşterinin bildirdiği KGÜP (varsa; kgup_surum kaynak
    'musteri'), kalan saatlerde PVQuant önerisi. program_df çıktısının kgup_kw sütunu bildirilen MWh × 1000 ile değiştirilir; kaynak sayımı döner."""
    if df is None or df.empty:
        return df, {"bildirilen_saat": 0, "oneri_saat": 0}
    try:
        bil = bildirilen_serisi(tenant_id, plant_id, pj, gun)
    except Exception:   # noqa: BLE001 — arşiv tablosu yoksa öneriyle
        bil = pd.Series(dtype=float)
    if bil is None or not len(bil):
        return df, {"bildirilen_saat": 0, "oneri_saat": int(len(df))}
    x = df.copy(); ts = pd.DatetimeIndex(x["ts_utc"])
    b = bil.reindex(ts).astype(float)
    m = b.notna().values
    x.loc[m, "kgup_kw"] = (b[m] * 1000.0).values
    return x, {"bildirilen_saat": int(m.sum()), "oneri_saat": int(len(x) - m.sum())}


def _pozisyon_serisi(pj: dict, df: pd.DataFrame) -> pd.Series | None:
    """v2.522 (P2b): DSG hesabında üyenin piyasa pozisyonu ayara göre (program | uretim | sabit); 'program' ise None (K kullanılır)."""
    poz = pozisyon_ayari(pj)
    if df is None or df.empty or poz["kaynak"] == "program":
        return None
    x = df.dropna(subset=["gercek_kw", "kgup_kw"]).set_index("ts_utc")
    if poz["kaynak"] == "uretim":
        return x["gercek_kw"].astype(float) / 1000.0
    return pd.Series(float(poz["sabit_mwh"] or 0.0), index=x.index)


def _ariza(tenant_id, plant: dict) -> int:
    """v2.521 (P1a): aylık arıza sayısı = olay kaydındaki arıza olayları ile Santral ayarlarındaki elle girilen sayının büyüğü (olay_service)."""
    try:
        from pvquant.services import olay_service
        return int(olay_service.ariza_sayisi_etkin(tenant_id, {"id": plant["id"], "params_json": plant.get("params_json")})["sayi"])
    except Exception:   # noqa: BLE001 — olay tablosu yoksa elle giriş
        return int(_pj(plant.get("params_json")).get("ariza_sayisi_ay") or 0)


def segment_bilgisi(params_json) -> dict:
    pj = _pj(params_json); ad = pj.get("segment")
    try:
        seg = sg.Segment(ad) if ad else None
    except ValueError:
        seg = None
    uevcb = (pj.get("uevcb") or None)   # v2.513 (04 #14): UEVÇB kodu panelde görünür/düzenlenir
    if seg is None:
        return {"segment": None, "kgup_yukumlu": None, "dengesizlik_sahibi": None, "santral_tasir": None, "uevcb": uevcb,
                "dsg_kodu": (str(pj.get("dsg_kodu")).strip() or None) if pj.get("dsg_kodu") else None, "toplayici_portfoyu": bool(pj.get("toplayici_portfoyu"))}
    k = sg.KURALLAR.loc[seg]
    st = sg.Santral("x", seg, 1.0)
    return {"segment": seg.value, "kgup_yukumlu": bool(k["kgup_yukumlu"]), "dengesizlik_sahibi": str(k["dengesizlik_sahibi"]), "santral_tasir": st.dengesizlik_tasir_mi(),
            "uevcb": uevcb, "dsg_kodu": (str(pj.get("dsg_kodu")).strip() or None) if pj.get("dsg_kodu") else None,   # v2.539 (DK-258): DSG adı/kodu (beyan)
            "toplayici_portfoyu": bool(pj.get("toplayici_portfoyu"))}   # v2.539 (DK-261): toplayıcı portföyünde → DSG dışı (DUY m.20(4))


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
    ariza = _ariza(tenant_id, plant); luy = bool(pj.get("luy_istisna"))   # 31.10 (v2.510, Ç3): LÜY; v2.521: olay kaydı ∨ elle m.5(1)(ç),(d),(e) istisnası
    bil = bildirilen_serisi(tenant_id, plant["id"], pj, gun); poz = pozisyon_ayari(pj)   # v2.517 (P2a): fiilî bildirim ve pozisyon ayarı
    out = hesapla_df(df, fiyat, kat, segment=seg["segment"], ariza_sayisi=ariza, luy_istisna=luy, bildirilen_mwh=bil, pozisyon=poz,
                     risk_katsayisi=_risk_katsayisi(pj))   # v2.522 (P2b): teminat risk katsayısı Santral ayarlarından
    out["oneri"] = oneri_kantili(fiyat, kat)   # v2.287
    out["pencere_gun"] = gun
    out["segment"] = seg; out["luy_istisna"] = luy
    out["kural"] = kural_ozeti(seg["segment"], luy_istisna=luy)
    k = out["kural"]
    kupst_not = ("KÜPST: segment seçilmedi, hesaplanmadı; " if not seg["segment"]
                 else f"KÜPST: {k['kupst_dayanak']}; " if k["kupst_n"] is not None or seg["segment"] == "lisanssiz_dagitim"
                 else "KÜPST: katsayı doğrulanamadı, hesaplanmadı; ")
    if (out.get("katsayilar") or {}).get("kupst_gecersiz_kilma"):   # v2.535: senaryo parametresi resmî tabloyla karıştırılmaz
        kupst_not += (f"KÜPST tolerans/n santral ayarından geçersiz kılındı (uygulanan: %{(out['katsayilar']['kupst_tolerans'] or 0) * 100:.0f} / "
                      f"{out['katsayilar']['kupst_n']}; resmî tablo: %{(k['kupst_m'] or 0) * 100:.0f} / {k['kupst_n']}); ")
    pr = out["program"]
    program_not = (f"Program: {pr['bildirilen_gun']} günde bildirilen KGÜP ({pr['bildirilen_saat']} saat; TPYS'ye bildirildiği beyan edilen dosya, kabulü doğrulanmaz), "
                   f"kalan {pr['oneri_saat']} saatte PVQuant önerisi (bir gün önce 15:30'dan önceki son tahminin P50'si)" if pr["bildirilen_saat"]
                   else "Program: PVQuant önerisi (bir gün önce 15:30'dan önceki son tahminin P50'si); bildirilen KGÜP dosyası yüklenirse hesap ona göre yapılır")
    out["not"] = (program_not + f"; {pr['pozisyon']['etiket']}; referans: dün aynı saat. "
                  f"Kural: {k['edt_dayanak']}; " + kupst_not
                  + ("fiyat: EPİAŞ (gerçek saatlik)" if out["fiyat"]["senaryo_saat"] == 0 and out["fiyat"]["epias_saat"] > 0
                     else f"fiyat: {piyasa_service.SENARYO_AD} (EPİAŞ kimliği yok); senaryo saatinde sistem yönü yok → k = l = 0,03 varsayımı")
                  + ("; 1.1.2027 m.110 metni hukuken belirsiz (varsayılan: 2026 rejimi sürer — hukuki dayanağı olmayan varsayım)" if k["belirsiz_2027"] else "")
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
                   dagitim_anahtari: str = "sapma", luy_istisnalar: dict[str, bool] | None = None,
                   pozisyonlar: dict[str, pd.Series] | None = None) -> dict:
    """SAF (v2.502, F-08). programlar[santral] = program_df çıktısı (ts_utc, gercek_kw, kgup_kw). Yürürlükteki DSG kuralı:
    üye eşiği (%10 / %5 — 2026+ payın %5 alınması yorum / 2027 varsayım) PH = max(A, F) ile; aşan kısım bireysel EDT olarak DST'ye yansıtılır; KÜPST üye bazında toplanır, netleşmez;
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
    poz = {a: v.reindex(idx) for a, v in (pozisyonlar or {}).items() if v is not None and a in K}   # v2.522: üye pozisyon ayarı (uretim/sabit)
    r = d.dsg_saatlik({a: K[a].loc[idx] for a in K}, {a: G[a].loc[idx] for a in G}, ptf, smf, yon=yon, segmentler=segmentler, ariza_sayilari=ariza_sayilari, luy_istisnalar=luy_istisnalar,
                      dagitim_anahtari=dagitim_anahtari, pozisyonlar=poz or None)
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
            "esik": (float(sa["esik"].iloc[-1]) if pd.notna(sa["esik"].iloc[-1]) else None), "esik_kaynak": r["esik_kaynak"],   # None → eşik yok (1.1.2025 öncesi) "kural_surumu": " | ".join(sorted(set(sa["kural_surumu"]))),
            "gecici_m39": kr.gecici_m39_notu(pd.Timestamp(idx[-1]).tz_convert(IST).date()),   # v2.513: dağıtım/GTŞ DSG'lerinde %100 (1.1.2027'ye kadar)
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
    programlar = {}; program_kaynak = {}
    for p in uyeler:   # v2.522 (P2b): program = bildirilen KGÜP (varsa), kalan öneri
        programlar[p["name"]], program_kaynak[p["name"]] = program_bildirilenle(tenant_id, str(p["id"]), _pj(p.get("params_json")), program_df(tenant_id, str(p["id"]), gun), gun)
    K: dict[str, pd.Series] = {}; G: dict[str, pd.Series] = {}
    for ad, df in programlar.items():
        if df is None or df.empty:
            continue
        x = df.dropna(subset=["gercek_kw", "kgup_kw"]).set_index("ts_utc")
        if x.empty:
            continue
        K[ad] = x["kgup_kw"].astype(float) / 1000.0; G[ad] = x["gercek_kw"].astype(float) / 1000.0
    bos["program"] = {"bildirilen_saat": sum(v["bildirilen_saat"] for v in program_kaynak.values()), "oneri_saat": sum(v["oneri_saat"] for v in program_kaynak.values()),
                      "santral": program_kaynak}
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


def _esik_cumlesi(esik) -> str:
    """DSG kartı ilk cümlesi; eşik None → 1.1.2025 öncesi kural (üye eşiği yok, tam netleşme) — 03.11.2026 doğrulama DK-249."""
    if esik is None:
        return "Bu dönemde üye eşiği yoktur (1.1.2025 öncesi, DUY m.111(3)-(5) henüz yok): santrallerin sapmaları DSG içinde tamamen netleşir. "
    return f"Her santralin sapmasının eşik oranı kadarı, %{esik * 100:.0f} × PH, DSG içinde netleşir; aşan kısmın tutarı mevzuat gereği DST'ye ayrıca yansıtılır; üyeye aktarımı sözleşmeye bağlıdır. "


DSG_DISI_NEDEN = {"toplayici": "toplayıcı portföyünde (beyan): toplayıcı DSG'de yer alamaz (DUY m.20(4)), portföye geçen üye DSG'den çıkar",
                  "lisanssiz_iletim": "iletime bağlı lisanssız: enerji dengesizlik tutarı GTŞ/toplayıcı portföyünde, DSG üyeliği doğrulanmadı",
                  "lisanssiz_dagitim": "dağıtıma bağlı lisanssız: dengesizlik GTŞ/toplayıcı UEVÇB'sinde, santral taşımaz",
                  "oz_tuketim_saatlik": "öz tüketim (saatlik mahsup): dengesizlik yok",
                  "kodsuz": "DSG kodu girilmedi: başka santrallerde kod varken kodsuz santral hangi gruba girdiği bilinmediğinden hesap dışı (Santralim › Santral ayarları › DSG kodu)"}
DSG_KATILIMCI_NOTU = ("Üye eşiği piyasa katılımcısı düzeyinde uygulanır (DUY m.111); aynı katılımcının birden çok santrali varsa PH ve eşik katılımcı toplamında hesaplanır. "
                      "PVQuant her santrali ayrı üye sayar (katılımcı alanı yok); çok santralli katılımcıda bireysel EDT fazla görünebilir (çıkarım).")   # EK-3 DK-252


def dsg_gruplari(santraller: list[dict]) -> dict:
    """v2.539 (EK-3 DK-258/DK-261, kanıt A) — SAF: santral kayıtlarından DSG grupları. Dışarıda: toplayıcı portföyündeki (beyan), iletime/dağıtıma bağlı
    lisanssız ve öz tüketim segmentleri. Kalanlar params_json.dsg_kodu ile gruplanır; hiçbir santralde kod yoksa hepsi tek grup («varsayim»);
    kod girilmiş santral varsa kodsuz santral hesap dışı («kodsuz»). Dönüş: {"gruplar": {kod|None: [ad…]}, "disi_nedenleri": {ad: neden}, "grup_kaynagi": beyan|varsayim}."""
    disi: dict[str, str] = {}; aday: list[tuple[str, str]] = []
    for p in santraller:
        ad = p["name"]; b = segment_bilgisi(p.get("params_json"))
        if b["toplayici_portfoyu"]:
            disi[ad] = DSG_DISI_NEDEN["toplayici"]
        elif b["segment"] in ("lisanssiz_iletim", "lisanssiz_dagitim", "oz_tuketim_saatlik"):
            disi[ad] = DSG_DISI_NEDEN[b["segment"]]
        else:
            aday.append((ad, b["dsg_kodu"] or ""))
    kodlu = [a for a in aday if a[1]]
    if not kodlu:
        return {"gruplar": {None: [a for a, _ in aday]} if aday else {}, "disi_nedenleri": disi, "grup_kaynagi": "varsayim"}
    gruplar: dict = {}
    for ad, kod in aday:
        if not kod:
            disi[ad] = DSG_DISI_NEDEN["kodsuz"]; continue
        gruplar.setdefault(kod, []).append(ad)
    return {"gruplar": gruplar, "disi_nedenleri": disi, "grup_kaynagi": "beyan"}


def dsg_ozet(tenant_id, gun: int = 30, dagitim_anahtari: str = "sapma", grup: str | None = None) -> dict:
    """Kiracının santralleri: DSG netleşmesi (yürürlükteki kural, F-08). Dengesizlik taşımayan segmentler portföy dışı; segment seçilmemiş
    santral lisanslı güneş kabul edilir ve KÜPST hesaplanamaz olarak işaretlenir.
    v2.539 (DK-258/261): gruplar santral kaydındaki DSG koduna göre (dsg_gruplari); toplayıcı portföyündeki ve lisanssız santraller dışarıda.
    `grup` ile seçilen grup, verilmezse en kalabalık grup üst düzeyde döner; bütün grupların özeti `gruplar`, dışarıda kalanlar `disi_nedenleri`."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import piyasa_service
    with tenant_baglami(tenant_id) as s:
        santraller = [dict(r._mapping) for r in s.execute(text("SELECT id, name, params_json FROM plants WHERE NOT archived ORDER BY name"))]
    programlar = {}; program_kaynak = {}; pozisyonlar = {}
    for p in santraller:   # v2.522 (P2b; v2.517 sınırı): program = bildirilen KGÜP (varsa) + pozisyon ayarı
        pj_p = _pj(p.get("params_json"))
        programlar[p["name"]], program_kaynak[p["name"]] = program_bildirilenle(tenant_id, str(p["id"]), pj_p, program_df(tenant_id, str(p["id"]), gun), gun)
        pozisyonlar[p["name"]] = _pozisyon_serisi(pj_p, programlar[p["name"]])
    segmentler = {p["name"]: segment_bilgisi(p.get("params_json"))["segment"] for p in santraller}
    ariza = {p["name"]: _ariza(tenant_id, p) for p in santraller}   # v2.521 (P1a): olay kaydındaki arıza sayısı ∨ elle giriş
    luy = {p["name"]: bool(_pj(p.get("params_json")).get("luy_istisna")) for p in santraller}   # 31.10 (v2.510, Ç3)
    idx = pd.DatetimeIndex([], tz="UTC")
    for df in programlar.values():
        if df is not None and not df.empty:
            idx = idx.union(pd.DatetimeIndex(df["ts_utc"]))
    fiyat = piyasa_service.fiyatlar(idx) if len(idx) else pd.DataFrame(columns=["ptf", "smf", "yon", "kaynak"])
    gr = dsg_gruplari(santraller)   # v2.539 (DK-258/261)
    sonuclar = {kod: dsg_hesapla_df({a: programlar[a] for a in adlar}, fiyat, segmentler=segmentler, ariza_sayilari=ariza, dagitim_anahtari=dagitim_anahtari,
                                    luy_istisnalar=luy, pozisyonlar=pozisyonlar) for kod, adlar in gr["gruplar"].items()}
    if not sonuclar:   # bütün santraller dışarıda
        sonuclar = {None: dsg_hesapla_df({}, fiyat)}
        sonuclar[None]["not"] = "portföyde dengesizlik taşıyan üye yok"
    if grup is not None and grup in sonuclar:
        secili = grup
    else:
        secili = max(sonuclar, key=lambda k: (len(gr["gruplar"].get(k, [])), str(k)))
    out = dict(sonuclar[secili])
    out["grup"] = secili; out["grup_kaynagi"] = gr["grup_kaynagi"]; out["disi_nedenleri"] = gr["disi_nedenleri"]
    out["disi"] = sorted(set(out.get("disi") or []) | set(gr["disi_nedenleri"]))
    out["gruplar"] = [{"kod": k, "santral": len(gr["gruplar"].get(k, [])), "uyeler": gr["gruplar"].get(k, []), "n_saat": v.get("n_saat"), "ayri_tl": v.get("ayri_tl"),
                       "net_tl": v.get("net_tl"), "kazanc_tl": v.get("kazanc_tl"), "not": v.get("not"), "secili": k == secili} for k, v in sonuclar.items()]
    out["katilimci_notu"] = DSG_KATILIMCI_NOTU
    out["pencere_gun"] = gun
    out["program"] = {"bildirilen_saat": sum(v["bildirilen_saat"] for v in program_kaynak.values()), "oneri_saat": sum(v["oneri_saat"] for v in program_kaynak.values()),
                      "santral": program_kaynak, "pozisyon_ayarli": [a for a, v in pozisyonlar.items() if v is not None]}   # v2.522 (P2b)
    out.setdefault("fiyat", {"epias_saat": int((fiyat["kaynak"] == "epias").sum()) if len(fiyat) else 0, "senaryo_saat": int((fiyat["kaynak"] == "senaryo").sum()) if len(fiyat) else 0})
    out["segment_yok"] = [p["name"] for p in santraller if not segmentler[p["name"]]]
    # 29.10 dil turu: müşteri dili — kural kısa, varsayım açık, dayanak sonda
    grup_notu = (" DSG kodu girilmedi: dengesizliğini kendisi taşıyan bütün santraller tek DSG varsayıldı; Santralim › Santral ayarları'ndan DSG kodu girince gruplar ayrılır." if gr["grup_kaynagi"] == "varsayim" and out["santral"] > 1
                 else (f" {len(sonuclar)} DSG grubu beyan edildi; gösterilen: «{secili}»." if gr["grup_kaynagi"] == "beyan" and len(sonuclar) > 1 else ""))
    out["not"] = ("Dengeden Sorumlu Grup içinde tek santral var; karşılıklı netleşecek sapma bulunmadığından fark sıfırdır. İkinci santral bağlandığında burada görünür." if out["santral"] <= 1
                  else _esik_cumlesi(out.get("esik"))
                       + "KÜPST santral başına ödenir ve DSG içinde netleşmez. Dayanak: DUY m.111. Bu rakamlar yürürlükteki kuralla yapılmış varsayımsal bir yeniden hesaptır; "
                       + ("program bildirilen KGÜP'tür (yüklü saatlerde), kalan saatlerde PVQuant önerisi; " if out["program"]["bildirilen_saat"] else "bildirilen KGÜP yüklü değil, program PVQuant önerisidir; ")
                       + ("satış Santral ayarlarındaki pozisyon ayarına göre alınmıştır. " if out["program"]["pozisyon_ayarli"] else "satış programa eşit varsayılmıştır. ")
                       + "EPİAŞ uzlaştırma sonucu değildir."
                       + (f" Senaryo fiyatlı {out['fiyat']['senaryo_saat']} saatte sistem yönü dengede varsayılmıştır (senaryo SMF ≠ PTF ile tutarsız; maliyet alt sınır niteliğinde)." if out["fiyat"].get("senaryo_saat") else "")
                       + (f" Üyelere dağıtım: {out['dagitim_etiket']}; anahtar DSG sözleşmesinde belirlenir." if out.get("dagitim_etiket") else "")
                       + grup_notu)
    if out.get("gecici_m39") and out["santral"] > 1:   # v2.513 rötuş: dağıtım/GTŞ DSG'lerinde 1.1.2027'ye kadar %100 (DUY Geçici m.39) — dsg_ozet dipnotu
        out["not"] += " " + kr.GECICI_M39_DIPNOT
    return out


def dsg_uye_csv(ozet: dict) -> str:
    """v2.522 (P2b, IH-036): üyelere dağıtım belgesi — DSG özetinden üye satırları (; ayraç, ondalık virgül, BOM; ilk satır not). Dağıtım anahtarı
    sözleşmeseldir; tutarlar yeniden hesaptır, EPİAŞ sonucu değildir."""
    import io as _io
    kol = ["santral", "edt_tek_basina_tl", "edt_bireysel_tl", "edt_dsg_tl", "netlesme_farki_tl", "kupst_tl", "pay_pct", "sapma_mwh", "grup_payi_mwh"]
    satirlar = [{"santral": ad, "edt_tek_basina_tl": v.get("edt_tek_tl"), "edt_bireysel_tl": v.get("edt_bireysel_tl"), "edt_dsg_tl": v.get("edt_dsg_tl"),
                 "netlesme_farki_tl": v.get("netlesme_farki_tl"), "kupst_tl": v.get("kupst_tl"), "pay_pct": v.get("pay_pct"), "sapma_mwh": v.get("sapma_mwh"),
                 "grup_payi_mwh": v.get("grup_payi_mwh")} for ad, v in (ozet.get("uyeler") or {}).items()]
    buf = _io.StringIO()
    buf.write(f"# PVQuant DSG üye dağılımı; DSG grubu: {ozet.get('grup') or 'tek grup varsayımı'}; son {ozet.get('pencere_gun')} gün; dağıtım anahtarı: {ozet.get('dagitim_etiket')}; üye eşiği {ozet.get('esik') if ozet.get('esik') is not None else 'yok (1.1.2025 öncesi)'}; "
              f"kural {ozet.get('kural_surumu')}; yeniden hesap, EPİAŞ uzlaştırma sonucu değildir; eksi EDT = üye öder\n")
    pd.DataFrame(satirlar, columns=kol).to_csv(buf, sep=";", decimal=",", index=False, lineterminator="\n")
    return "\ufeff" + buf.getvalue()
