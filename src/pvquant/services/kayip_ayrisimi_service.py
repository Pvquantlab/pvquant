"""04.11.2026 v2.533 (P8a; IH-087, IH-083 kısmen) — gerçekleşen kayıp ayrışımı: son N ölçüm gününde beklenen (fizik modeli, 0–24 saat öncülü)
ile gerçekleşen arasındaki açığı nedene göre saat, kWh ve TL olarak ayırır; EPI (enerji performans indeksi) = Σgerçek / Σbeklenen.

Neden ataması saat başına ve öncelik sırasıyla: olay kaydı (talimat YAT/YAL → «talimat», planlı bakım, şebeke kesintisi / acil kesme → «şebeke»,
arıza / hasar → «arıza (olay kaydı)»), hijyen bayrağı «kisinti» (şebeke kısıtı, otomatik tespit), AC sınırında kırpma (kWh HESAPLANMAZ: beklenti
AC sınırını içerir, DC potansiyeli ölçülmez), otomatik arıza (beklenti > %10 kapasite iken üretim < %0,5), kalanı «açıklanmayan sapma» (hava
tahmini belirsizliği dâhil; kayıp sayılmaz, bilgi). Kayıp kWh = max(beklenen − gerçek, 0). TL = kWh × o saatin satış fiyatı: Santral ayarlarındaki
tarife (sabit / çok zamanlı / PTF endeksli / YEKDEM gün fiyatı); tarife yoksa piyasa takas fiyatı (PTF; piyasa kimliği yoksa senaryo, işaretli).
Dürüstlük: beklenen seri ölçülen hava verisiyle değil hava tahmini girdili fizik modeliyle üretilir (saha ışınım sensörü akışı yok); «kaybın TL
karşılığı» gelir kaybı tahminidir, uzlaştırma ya da fatura kalemi değildir; her satır KPI'dan (kalibrasyon ve kullanılabilirlik) dışlanıp
dışlanmadığını söyler (olay_service.TUR_KURAL istisna bayrağı).
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

from datetime import timedelta, timezone

import numpy as np
import pandas as pd
from pvquant.services.karne_kurali import yayin_kosu_sql as _yayin_sql   # v2.597 (F4-B): yayımlanmış koşu süzgeci
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten

NEDENLER = (
    ("talimat", "Sistem işletmecisi talimatı (YAT/YAL)", "olay kaydı", True),
    ("planli_bakim", "Planlı bakım", "olay kaydı", True),
    ("sebeke", "Şebeke kesintisi / acil kesme", "olay kaydı", True),
    ("ariza_kaydi", "Arıza / hasar (olay kaydı)", "olay kaydı", False),
    ("kisinti", "Şebeke kısıtı (otomatik tespit)", "veri temizliği", True),
    ("kirpma", "AC sınırında kırpma", "veri temizliği", True),
    ("ariza_otomatik", "Arıza (otomatik tespit)", "otomatik", False),
    ("veri_yok", "Ölçüm satırı yok", "ölçüm", None),
    ("aciklanmayan", "Açıklanmayan sapma (tahmin belirsizliği dâhil)", "model farkı", False),
)
NEDEN_ETIKET = {k: e for k, e, _, _ in NEDENLER}
TUR_NEDEN = {"talimat_yat": "talimat", "talimat_yal": "talimat", "planli_bakim": "planli_bakim", "sebeke_kesintisi": "sebeke", "acil_kesme": "sebeke",
             "ariza": "ariza_kaydi", "hasar": "ariza_kaydi", "uzaktan_acma": "sebeke"}
MIN_SAAT = 24


def olay_saat_haritasi(olaylar: list[dict], bas, bit) -> dict:
    """SAF. Olay listesi → {UTC saat başı: neden}; aynı saatte birden çok olay varsa NEDENLER sırası (talimat > bakım > şebeke > arıza) kazanır."""
    oncelik = {k: i for i, (k, *_r) in enumerate(NEDENLER)}
    out: dict = {}
    for o in olaylar:
        neden = TUR_NEDEN.get(o.get("tur") or "")
        if not neden or not o.get("baslangic"):
            continue
        t = pd.Timestamp(o["baslangic"]).tz_convert("UTC") if pd.Timestamp(o["baslangic"]).tzinfo else pd.Timestamp(o["baslangic"]).tz_localize("UTC")
        t = t.floor("h")
        son = pd.Timestamp(o["bitis"]).tz_convert("UTC") if o.get("bitis") and pd.Timestamp(o["bitis"]).tzinfo else (pd.Timestamp(o["bitis"]).tz_localize("UTC") if o.get("bitis") else pd.Timestamp(bit))
        while t < son and t < pd.Timestamp(bit):
            if t >= pd.Timestamp(bas) and (t not in out or oncelik[neden] < oncelik[out[t]]):
                out[t] = neden
            t += pd.Timedelta(hours=1)
    return out


def hesapla_df(df: pd.DataFrame, capacity_kwp: float, olay_neden: dict | None = None, fiyat_tl_mwh: pd.Series | None = None) -> dict:
    """SAF. df: ts_utc (UTC), power_kw (NaN = satır yok), beklenen_kw, flag ('valid' | 'kisinti'), kirpma (bool). olay_neden: {ts → neden}.
    fiyat_tl_mwh: ts indeksli saatlik satış fiyatı (NaN → TL yok)."""
    if df is None or df.empty:
        return {"durum": "veri_yok"}
    x = df.copy()
    x["ts_utc"] = pd.to_datetime(x["ts_utc"], utc=True)
    x = x.sort_values("ts_utc").drop_duplicates("ts_utc").set_index("ts_utc")
    x = x[x["beklenen_kw"].astype(float) > 0.02 * capacity_kwp]            # üretim mümkün saatler
    if len(x) < MIN_SAAT:
        return {"durum": "yetersiz", "mumkun_saat": int(len(x))}
    b = x["beklenen_kw"].astype(float); g = pd.to_numeric(x["power_kw"], errors="coerce")
    var = g.notna()
    flag = x["flag"].astype(str) if "flag" in x else pd.Series("", index=x.index)
    kirp = x["kirpma"].fillna(False).astype(bool) if "kirpma" in x else pd.Series(False, index=x.index)
    neden = pd.Series("", index=x.index, dtype=object)
    if olay_neden:
        for ts, n in olay_neden.items():
            if ts in neden.index:
                neden[ts] = n
    bos = neden == ""
    neden[bos & ~var] = "veri_yok"; bos = neden == ""
    neden[bos & flag.eq("kisinti")] = "kisinti"; bos = neden == ""
    neden[bos & kirp] = "kirpma"; bos = neden == ""
    neden[bos & (g < 0.005 * capacity_kwp) & (b > 0.10 * capacity_kwp)] = "ariza_otomatik"; bos = neden == ""
    neden[bos] = "aciklanmayan"
    kayip = (b - g).clip(lower=0.0)
    fiyat = fiyat_tl_mwh.reindex(x.index).astype(float) if fiyat_tl_mwh is not None else pd.Series(np.nan, index=x.index)
    satirlar = []; toplam_kwh = 0.0; toplam_tl = 0.0; tl_eksik = 0
    for kod, etiket, kaynak, kpi_disi in NEDENLER:
        m = neden == kod
        saat = int(m.sum())
        if saat == 0:
            continue
        if kod in ("veri_yok", "kirpma"):
            kwh = None; tl = None
        else:
            kwh = float(kayip[m].sum())
            f = fiyat[m]
            if kod == "aciklanmayan":
                tl = None                                            # kayıp sayılmaz → TL karşılığı yazılmaz (yanıltmasın)
            else:
                tl = float((kayip[m][f.notna()] / 1000.0 * f[f.notna()]).sum()) if f.notna().any() else None
                tl_eksik += int((m & fiyat.isna()).sum())
                toplam_kwh += kwh; toplam_tl += (tl or 0.0)
        satirlar.append({"neden": kod, "etiket": etiket, "kaynak": kaynak, "kpi_disi": kpi_disi, "saat": saat,
                         "kayip_kwh": (round(kwh, 1) if kwh is not None else None), "kayip_tl": (round(tl, 0) if tl is not None else None),
                         "not": ("kWh hesaplanmaz: beklenti AC sınırını içerir, DC potansiyeli ölçülmez" if kod == "kirpma" else
                                 "ölçüm satırı yok; kayıp bilinmiyor" if kod == "veri_yok" else
                                 "kayıp sayılmaz; hava tahmini belirsizliği ve model farkı" if kod == "aciklanmayan" else "")})
    epi_m = var & ~neden.isin(["veri_yok"])
    epi = float(g[epi_m].sum() / b[epi_m].sum()) if b[epi_m].sum() > 0 else None
    return {"durum": "ok", "mumkun_saat": int(len(x)), "veri_saat": int(var.sum()), "uretim_kwh": round(float(g[var].sum()), 1),
            "beklenen_kwh": round(float(b[var].sum()), 1), "epi": (round(epi, 4) if epi is not None else None),
            "satirlar": satirlar, "toplam_kayip_kwh": round(toplam_kwh, 1), "toplam_kayip_tl": round(toplam_tl, 0),
            "fiyatsiz_saat": tl_eksik}


def _fiyat_serisi(plant: dict, idx: pd.DatetimeIndex) -> tuple[pd.Series, dict]:
    """Saatlik satış fiyatı (TL/MWh): tarife tanımlıysa tarife yapısı (PTF endeksliyse piyasa fiyatıyla), yoksa PTF."""
    from pvquant.services import piyasa_service, tarife_service
    f = piyasa_service.fiyatlar(idx)
    ptf = f["ptf"].astype(float).reindex(idx)
    senaryo = int((f["kaynak"].astype(str) != "epias").sum())
    t = tarife_service.tarife_getir(plant)
    if t and t.get("tip"):
        try:
            ist = idx.tz_convert(PIYASA_TZ)
            y = tarife_service.yapi(t, plant=plant, bas=ist.min().date(), bit=ist.max().date())
            fiyat = y.fiyat(idx, ptf=ptf)
            return fiyat, {"kaynak": "tarife", "tip": t["tip"], "senaryo_saat": (senaryo if t["tip"] == "ptf" else 0),
                           "etiket": {"sabit": "sabit tarife", "cok_zamanli": "çok zamanlı tarife", "ptf": "PTF endeksli tarife", "yekdem": "YEK fiyatı (gün bazlı)"}.get(t["tip"], t["tip"])}
        except Exception as e:   # noqa: BLE001 — tarife eksik/bozuksa PTF'ye düş, nedeni söyle
            return ptf, {"kaynak": "ptf", "tip": None, "senaryo_saat": senaryo, "etiket": f"piyasa takas fiyatı (tarife uygulanamadı: {e})"}
    return ptf, {"kaynak": "ptf", "tip": None, "senaryo_saat": senaryo, "etiket": "piyasa takas fiyatı (satış tarifesi tanımlı değil)"}


def hesapla(tenant_id, plant: dict, gun: int = 30) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import olay_service
    with tenant_baglami(tenant_id) as s:
        son = s.execute(text(f"SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('kayip')}"), {"p": plant["id"]}).scalar()
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.physics_kw AS beklenen_kw, s.power_kw, s.flag, s.kirpma FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            f"LEFT JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND {_ks.sql_kosulu('kayip', 's')} "
            "WHERE f.plant_id=:p AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            f"AND {_yayin_sql('r')} "
            "AND f.ts_utc >= :son - (:g * INTERVAL '1 day') AND f.ts_utc <= :son ORDER BY f.ts_utc, r.run_at DESC"),
            s.connection(), params={"p": plant["id"], "g": gun, "son": son}, parse_dates=["ts_utc"]) if son is not None else pd.DataFrame()
    bos = {"pencere_gun": gun, "son_olcum": son.date().isoformat() if son is not None else None}
    if df.empty:
        return {"durum": "veri_yok", **bos}
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    df = df.drop_duplicates("ts_utc", keep="first")
    bas = df["ts_utc"].min().to_pydatetime(); bit = (df["ts_utc"].max() + pd.Timedelta(hours=1)).to_pydatetime()
    try:
        olaylar = olay_service.aralik(tenant_id, plant["id"], bas, bit, list(TUR_NEDEN))
    except Exception:   # noqa: BLE001 — olay tablosu yoksa
        olaylar = []
    neden = olay_saat_haritasi(olaylar, bas, bit)
    idx = pd.DatetimeIndex(df["ts_utc"])
    try:
        fiyat, fiyat_bilgi = _fiyat_serisi(plant, idx)
    except Exception as e:   # noqa: BLE001
        fiyat, fiyat_bilgi = None, {"kaynak": "yok", "tip": None, "senaryo_saat": 0, "etiket": f"fiyat alınamadı: {e}"}
    out = hesapla_df(df, float(plant["capacity_kwp"]), neden, fiyat)
    out.update(bos); out["fiyat"] = fiyat_bilgi; out["olay_saat"] = len(neden)
    out["not"] = ("Beklenen üretim hava tahmini girdili fizik modelidir (0–24 saat öncülü); saha ışınım sensörü akışı yok. TL karşılığı o saatin "
                  "satış fiyatıyla gelir kaybı tahminidir, uzlaştırma ya da fatura kalemi değildir. «KPI'dan dışlanır» = kalibrasyon ve teknik "
                  "kullanılabilirlik bu saatleri saymaz.")
    return out
