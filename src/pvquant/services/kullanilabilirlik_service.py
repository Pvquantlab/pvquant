"""v2.281 — Tablo 3.3 satır 6: kullanılabilirlik (IEC 61724-3 kalıbı) — olay günlüğü olmadan OTOMATİK tespit.

Üretim mümkün saat: 0–24 s öncülü fizik beklentisi > %2 kapasite. Veri erişilebilirliği = geçerli ölçüm satırı / mümkün saat.
Arıza (otomatik): ölçüm satırı var, gücü < %0,5 kapasite ama beklenti > %10 kapasite → 'sıfır üretim' saati. Şebeke kesintisi /
kısıntı ayrımı olay günlüğü olmadan yapılamaz — 'kisinti' bayraklı saatler hariç tutulur, kalanı arıza sayılır; dürüstçe
"otomatik tespit" etiketiyle sunulur. Enerji tabanlı: kayıp = beklenti − ölçüm (arıza saatleri). Özet PR kartına ve alarm
kuralına (kullanilabilirlik_dustu, opt-in) beslenir.
"""
from __future__ import annotations

import pandas as pd
from pvquant.services.karne_kurali import yayin_kosu_sql as _yayin_sql   # v2.597 (F4-B): yayımlanmış koşu süzgeci
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten

MIN_MUMKUN_SAAT = 40


def mtbf_ozeti(olaylar: list[dict], bas: pd.Timestamp, bit: pd.Timestamp) -> dict:
    """SAF. Olay kaydındaki 'ariza' olaylarından ext.standart.kullanilabilirlik.mtbf_mttr (IEC 61724-3 tanımı): MTBF = (dönem − toplam onarım) /
    arıza sayısı, MTTR = ortalama onarım süresi. Açık arıza (bitiş yok) dönem sonuna kadar sayılır. Arıza yoksa saatler None."""
    from pvquant.ext.standart import kullanilabilirlik as kl
    ol = []
    for o in olaylar:
        if o.get("tur") != "ariza" or not o.get("baslangic"):
            continue
        b0 = max(pd.Timestamp(o["baslangic"]).tz_convert("UTC") if pd.Timestamp(o["baslangic"]).tzinfo else pd.Timestamp(o["baslangic"], tz="UTC"), bas)
        b1 = pd.Timestamp(o["bitis"]) if o.get("bitis") else bit
        b1 = b1.tz_convert("UTC") if b1.tzinfo else b1.tz_localize("UTC")
        b1 = min(b1, bit)
        if b1 > b0:
            ol.append(kl.Olay(b0, b1, "ariza"))
    r = kl.mtbf_mttr(ol, bas, bit)
    tam = lambda v: (round(float(v), 1) if v == v else None)   # noqa: E731 — NaN → None
    return {"ariza_olay_sayisi": int(r["ariza_sayisi"]), "mtbf_saat": tam(r["MTBF_saat"]), "mttr_saat": tam(r["MTTR_saat"])}


def ariza_istatistigi(tenant_id, plant_id, df: pd.DataFrame) -> dict:
    """Pencere = df'nin saat aralığı; olay kaydı yoksa ya da hata olursa sıfır/None (hesabı düşürmez)."""
    bos = {"ariza_olay_sayisi": 0, "mtbf_saat": None, "mttr_saat": None}
    if df is None or df.empty:
        return bos
    try:
        from pvquant.services import olay_service
        ts = pd.to_datetime(df["ts_utc"], utc=True)
        bas, bit = ts.min(), ts.max() + pd.Timedelta(hours=1)
        olaylar = olay_service.aralik(tenant_id, plant_id, bas.to_pydatetime(), bit.to_pydatetime(), turler=("ariza",))
        return mtbf_ozeti(olaylar, bas, bit)
    except Exception:   # noqa: BLE001
        return bos


def hesapla_df(df: pd.DataFrame, capacity_kwp: float) -> dict:
    """SAF. df: ts_utc, beklenen_kw (fizik, 0–24 s), power_kw (NaN = satır yok), flag."""
    if df is None or df.empty:
        return {"durum": "veri_yok"}
    x = df.copy()
    mumkun = x["beklenen_kw"].astype(float) > 0.02 * capacity_kwp
    x = x[mumkun]
    if len(x) < MIN_MUMKUN_SAAT:
        return {"durum": "yetersiz", "mumkun_saat": int(len(x))}
    var = x["power_kw"].notna()
    haric = x.get("flag", pd.Series("", index=x.index)).astype(str).eq("kisinti")
    ariza = var & ~haric & (x["power_kw"].astype(float) < 0.005 * capacity_kwp) & (x["beklenen_kw"].astype(float) > 0.10 * capacity_kwp)
    payda = int((var & ~haric).sum())
    A_t = 1 - int(ariza.sum()) / payda if payda else None
    kayip = (x["beklenen_kw"].astype(float) - x["power_kw"].astype(float)).clip(lower=0).where(ariza, 0.0).sum()
    E = float(x.loc[var & ~haric, "power_kw"].astype(float).sum())
    A_e = E / (E + float(kayip)) if (E + float(kayip)) > 0 else None
    return {"durum": "ok", "mumkun_saat": int(len(x)), "veri_orani": round(float(var.mean()), 3), "haric_saat": int(haric.sum()),
            "beklenen_kwh": round(float(x.loc[var & ~haric, "beklenen_kw"].astype(float).sum()), 1),   # v2.533: sözleşme açığı tabanı
            "ariza_saat": int(ariza.sum()), "A_t": (round(float(A_t), 4) if A_t is not None else None),
            "A_e": (round(float(A_e), 4) if A_e is not None else None), "kayip_kwh": round(float(kayip), 1),
            "not": "arıza saatleri otomatik tespit (beklenti >%10 iken üretim ≈0); olay günlüğü yok — şebeke kesintisi ayrılamaz"}


def hesapla(tenant_id, plant: dict, gun: int = 30) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.physics_kw AS beklenen_kw, s.power_kw, s.flag FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "LEFT JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc "
            "WHERE f.plant_id=:p AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            f"AND {_yayin_sql('r')} "
            f"AND f.ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('kayip')}) - (:g * INTERVAL '1 day') "
            f"AND f.ts_utc <= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('kayip')})"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc"])
    if not df.empty:
        df = df.sort_values("ts_utc").drop_duplicates("ts_utc", keep="last")
        # v2.521 (P1a): olay kaydındaki istisna türleri (planlı bakım, talimat, acil kesme, şebeke kesintisi) arıza sayılmaz — 'kisinti' gibi dışarıda
        from pvquant.services import olay_service
        ts = pd.to_datetime(df["ts_utc"], utc=True)
        istisna = olay_service.istisna_saatleri(tenant_id, plant["id"], ts.min().to_pydatetime(), (ts.max() + pd.Timedelta(hours=1)).to_pydatetime())
        if istisna:
            maske = ts.isin(list(istisna)).values
            df["flag"] = df.get("flag", pd.Series("", index=df.index)).astype(str).where(~maske, "kisinti")
            olay_saat = int(maske.sum())
        else:
            olay_saat = 0
    else:
        olay_saat = 0
    out = hesapla_df(df, float(plant["capacity_kwp"]))
    out["pencere_gun"] = gun
    out["olay_istisna_saat"] = olay_saat
    out.update(ariza_istatistigi(tenant_id, plant["id"], df))   # 04.11 v2.531 (ENV-F10): olay kaydındaki arızalardan MTBF/MTTR
    if olay_saat and out.get("not"):
        out["not"] = out["not"].replace("olay günlüğü yok — şebeke kesintisi ayrılamaz", f"olay kaydındaki {olay_saat} istisna saati (planlı bakım, talimat, kesinti) dışarıda")
    out["sozlesme"] = sozlesme_acigi(plant, out)   # 04.11 v2.533 (P8a, K-07): sözleşme eşiği girildiyse açık (kWh, TL)
    return out


def sozlesme_acigi(plant: dict, out: dict) -> dict | None:
    """v2.533 (P8a): params_json.kullanilabilirlik_sozlesme (0,5–1) girildiyse ext.standart.kullanilabilirlik.sozlesme — eşik altı kalan pay ×
    penceredeki beklenen enerji × birim satış fiyatı (tarife ortalaması; yoksa PTF ortalaması). O&M sözleşmesindeki tanım, istisna listesi ve
    tazmin formülü farklı olabilir: bu değer kıyas tabanıdır, alacak değildir. Eşik yoksa None."""
    import json
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    esik = pj.get("kullanilabilirlik_sozlesme")
    if esik in (None, "") or out.get("durum") != "ok" or out.get("A_t") is None:
        return None
    from pvquant.ext.standart import kullanilabilirlik as kl
    fiyat, kaynak = _birim_fiyat(plant)
    r = kl.sozlesme(float(out["A_t"]), float(esik), float(out.get("beklenen_kwh") or 0.0), (fiyat / 1000.0) if fiyat else 0.0)
    return {"esik": float(esik), "A_gercek": round(r["A_gercek"], 4), "acik_puan": round(r["acik_puan"], 4), "acik_kwh": round(r["acik_kwh"], 1),
            "acik_tl": (round(r["acik_tl"], 0) if fiyat else None), "fiyat_tl_mwh": (round(fiyat, 1) if fiyat else None), "fiyat_kaynak": kaynak,
            "not": "teknik kullanılabilirlik (otomatik tespit, olay kaydı istisnaları) ile sözleşme eşiğinin farkı; O&M sözleşmenizdeki tanım, istisna listesi ve tazmin formülü farklı olabilir — kıyas tabanıdır, alacak değildir"}


def _birim_fiyat(plant: dict) -> tuple[float | None, str]:
    """Birim satış fiyatı (TL/MWh): tarife ortalaması (sabit / YEKDEM gün fiyatı / PTF endeksli), yoksa son 30 gün PTF ortalaması; alınamazsa None."""
    try:
        from pvquant.services import piyasa_service, tarife_service
        idx = pd.date_range(pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(days=30), periods=24 * 30, freq="h")
        f = piyasa_service.fiyatlar(idx); ptf_ort = float(f["ptf"].astype(float).mean()) if len(f) else None
        t = tarife_service.tarife_getir(plant)
        if t and t.get("tip"):
            v = tarife_service.ortalama_fiyat_tl_mwh(t, ptf_ort=ptf_ort, plant=plant)
            if v:
                return float(v), f"tarife ({t['tip']})"
        if ptf_ort:
            return ptf_ort, "PTF 30 gün ortalaması" + (" (senaryo fiyat)" if (f["kaynak"].astype(str) != "epias").any() else "")
    except Exception:   # noqa: BLE001 — DB/fiyat yoksa TL verilmez
        pass
    return None, "fiyat yok"
