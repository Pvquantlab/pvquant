"""v2.590 (Faz 3 F3-C) — PORTFÖY SAPMA VE RİSK SERVİSİ: dönem için üyelerin program / gerçekleşen / tahmin / fizik serileri aynı saat kümesinde
(FEM girdileri: bildirilen KGÜP › öneri, SCADA/sayaç, ölçüm uygunluğu; gün öncesi tahmin ve fizik beklentisi tahmin arşivinden karne kuralıyla),
saf `ext/platform/portfoy_sapma` ile ayrıştırma; ileriye dönük risk F3-B bandıyla. TL hesabı yok (F3-D/G). Formül yok."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.ext.platform import portfoy_sapma as ps
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe
from pvquant.services import portfoy_tahmin_service as pt
from pvquant.services import portfoy_varlik_service as pv

SURUM = ps.SURUM
RISKLI_GUN = 5


def _r(v, n=3):
    try:
        return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), n)
    except (TypeError, ValueError):
        return None


def _tahmin_fizik(tenant_id, plant: dict, dn: dict) -> tuple[pd.Series, pd.Series]:
    """Gün öncesi seçimli P50 ve fizik beklentisi (MWh), dönem ızgarasında; yoksa NaN."""
    izgara = dn["izgara"]
    try:
        df, _ = bd.tahmin_oku(tenant_id, plant["id"], dn["bas_utc"], dn["bit_utc"])
        sec = bd.kosu_sec(df, "gun_oncesi", plant.get("tz") or fn.IST_AD) if df is not None and not df.empty else None
    except Exception:   # noqa: BLE001 — tahmin arşivi okunamazsa tahmin/fizik eksik kalır (uydurulmaz)
        sec = None
    if sec is None or sec.empty:
        return pd.Series(np.nan, index=izgara), pd.Series(np.nan, index=izgara)
    sec = sec.drop_duplicates("ts_utc").set_index(pd.to_datetime(sec["ts_utc"], utc=True))
    t = pd.to_numeric(sec["p50_kw"], errors="coerce").reindex(izgara) / 1000.0
    f = pd.to_numeric(sec["physics_kw"], errors="coerce").reindex(izgara) / 1000.0 if "physics_kw" in sec.columns else pd.Series(np.nan, index=izgara)
    return t, f


def girdiler(tenant_id, plants: list[dict], dn: dict, uretim: str | None = None) -> tuple[dict[str, pd.DataFrame], dict, pd.DataFrame | None]:
    """Santral → (program_mwh, gercek_mwh, tahmin_mwh, fizik_mwh) ve santral başına kaynak/kapsama bilgisi; dönem fiyatı (ilk santralden; ızgara aynı)."""
    from pvquant.services import olcum_uygunluk_service as ou
    out, bilgi, fiyat = {}, {}, None
    izgara = fn.saat_kumesi(dn); dn = {**dn, "izgara": izgara}
    for p in plants:
        try:
            g = fe.girdiler(tenant_id, p, dn, uretim)
        except Exception as ex:   # noqa: BLE001 — bir santralin girdisi okunamazsa o santral eksik etiketiyle listelenir, portföy düşmez
            bilgi[p["name"]] = {"hata": f"{type(ex).__name__}: {ex}"}; out[p["name"]] = None; continue
        prog, kaynak = fe.program_serisi(g["df"], g["bildirilen"], izgara)
        ger = pd.to_numeric(g["df"]["gercek_kw"], errors="coerce").reindex(izgara).astype(float) / 1000.0 if "gercek_kw" in g["df"].columns else pd.Series(np.nan, index=izgara)
        tah, fiz = _tahmin_fizik(tenant_id, p, dn)
        out[p["name"]] = pd.DataFrame({"program_mwh": prog, "gercek_mwh": ger, "tahmin_mwh": tah, "fizik_mwh": fiz}, index=izgara)
        tamamlanan = int(g["df"]["program_tamamlanan"].reindex(izgara).fillna(False).astype(bool).sum()) if "program_tamamlanan" in g["df"].columns else 0
        try:
            _, dok = ou.saat_durumlari(tenant_id, p, dn["bas_utc"], dn["bit_utc"], "sayac" if g["uretim"] == "sayac" else "scada")
        except Exception:   # noqa: BLE001
            dok = None
        bilgi[p["name"]] = {"program": {"bildirilen_saat": int((kaynak == "bildirilen").sum()), "oneri_saat": int((kaynak == "oneri").sum()),
                                        "yok_saat": int(kaynak.isna().sum()), "tamamlanan_saat": tamamlanan},
                            "uretim": g["uretim"], "olcum_saat": int(ger.notna().sum()), "tahmin_saat": int(tah.notna().sum()), "fizik_saat": int(fiz.notna().sum()),
                            "kapsama": dok, "segment": g["segment"]}
        if fiyat is None:
            fiyat = g["fiyat"]
    return out, bilgi, fiyat


def donem(tenant_id, portfoy_id, kod: str | None = None, uretim: str | None = None, bugun: date | None = None, tarih: date | None = None) -> dict:
    """Dönem (gün / hafta / ay / çeyrek / yıl kodu; yoksa dün) için portföy sapma ve risk görünümü. Üyelik: dönemin son günü ya da bugün (hangisi önceyse);
    `tarih` verilirse o."""
    bugun = bugun or pd.Timestamp.now(tz=fn.IST_AD).date()
    dn = fn.donem_cozumle(kod, bugun, tz=fn.IST_AD)
    uyelik_tarihi = tarih or min(dn["bit"] - timedelta(days=1), bugun)
    plants = pt.santraller(tenant_id, portfoy_id, uyelik_tarihi)
    if not plants:
        return {"durum": "uye_yok", "santral": 0, "donem": _donem_sozluk(dn), "not": "Bu tarihte portföyün geçerli üyesi yok."}
    tz = pt._portfoy_tz(plants)
    if tz != fn.IST_AD:
        dn = fn.donem_cozumle(kod, bugun, tz=tz)
    girdi, bilgi, fiyat = girdiler(tenant_id, plants, dn, uretim)
    p, st = ps.saatlik({a: d for a, d in girdi.items() if d is not None})
    kaps = {pl["name"]: pl["capacity_kwp"] for pl in plants if girdi.get(pl["name"]) is not None}
    o = ps.ozet(p, st, kaps)
    kat = ps.katkilar(p, st, kaps)
    kat_t = ps.katkilar(p, st, kaps, "tahmin_hata"); kat_f = ps.katkilar(p, st, kaps, "fizik_sapma")
    ko = ps.korelasyon_sapma(st)
    mar = ps.maruziyet_saatleri(p, st, fiyat)
    kp = ps.kapsama(p)
    # riskli günler (geçmiş): günlük portföy program sapması, |sapma| en büyük 5 gün
    riskli = []
    if len(p) and p["program_sapma_mwh"].notna().any():
        yerel = pd.DatetimeIndex(p.index).tz_convert(tz).date
        g = p.assign(_g=yerel).groupby("_g").agg(sapma=("program_sapma_mwh", lambda s: s.sum(min_count=1)), program=("program_mwh", lambda s: s.sum(min_count=1)),
                                                 tam=("sapma_tam", "sum"), saat=("program_sapma_n", lambda s: int((s > 0).sum())))
        g = g.dropna(subset=["sapma"])
        for gun, r in g.reindex(g["sapma"].abs().sort_values(ascending=False).index).head(RISKLI_GUN).iterrows():
            riskli.append({"gun": str(gun), "sapma_mwh": _r(r["sapma"]), "program_mwh": _r(r["program"]), "pct": _r(100 * r["sapma"] / r["program"], 1) if r["program"] and r["program"] > 1e-9 else None,
                           "tam_saat": int(r["tam"]), "saat": int(r["saat"])})
    saatlik = [{"ts": ts.isoformat(timespec="minutes"), "program_mwh": _r(r.program_mwh), "gercek_mwh": _r(r.gercek_mwh), "tahmin_mwh": _r(r.tahmin_mwh), "fizik_mwh": _r(r.fizik_mwh),
                "program_sapma_mwh": _r(r.program_sapma_mwh), "tahmin_hata_mwh": _r(r.tahmin_hata_mwh), "fizik_sapma_mwh": _r(r.fizik_sapma_mwh),
                "olcum_n": int(r.gercek_n), "program_n": int(r.program_n), "sapma_n": int(r.program_sapma_n), "tam": bool(r.sapma_tam)} for ts, r in p.iterrows()]
    eksik = [pl["name"] for pl in plants if girdi.get(pl["name"]) is None]
    return {"durum": "ok", "portfoy_id": str(portfoy_id), "donem": _donem_sozluk(dn), "tz": tz, "santral": len(plants), "hesaba_giren": len(kaps), "eksik_santral": eksik,
            "kapasite_kwp": float(sum(kaps.values())), "ozet": o, "katkilar": kat, "katkilar_tahmin": kat_t, "katkilar_fizik": kat_f, "korelasyon": ko,
            "maruziyet_saatleri": mar, "kapsama": kp, "riskli_gunler": riskli, "saatlik": saatlik, "santral_bilgi": bilgi,
            "fiyat": {"epias_saat": int((fiyat["kaynak"] == "epias").sum()) if fiyat is not None and "kaynak" in fiyat.columns else 0,
                      "senaryo_saat": int((fiyat["kaynak"] != "epias").sum()) if fiyat is not None and "kaynak" in fiyat.columns else 0},
            "meta": {"surum": SURUM, "uretim_girdisi": uretim or "santral ayarı", "uyelik_tarihi": uyelik_tarihi.isoformat(), "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, uyelik_tarihi),
                     "tahmin_secimi": "gün öncesi (yerel gün başlamadan önceki son yayın); fizik beklentisi aynı yayından", "program": "bildirilen KGÜP › PVQuant önerisi (15:30 kesimi)",
                     "isaret": {"program_sapma": "gerçekleşen − program (artı = fazla üretim)", "tahmin_hata": "tahmin − gerçekleşen", "fizik_sapma": "gerçekleşen − fizik beklentisi"},
                     "netlesme": "fiziksel ofset; finansal netleşme DSG üyeliği ve sözleşmeye bağlıdır (F3-D)"}}


def _donem_sozluk(dn: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dn.items() if k != "izgara"}


def gelecek(tenant_id, portfoy_id, gun: int = 2, kural: str = "son", bugun: date | None = None, bas_gun: date | None = None, simdi: pd.Timestamp | None = None) -> dict:
    """Bugün ve sonraki günler: portföy tahmini (F3-B, bant) ↔ ileri program (bildirilen KGÜP › program kesimi öncesi tahmin). Riskli saatler ve etiket.
    v2.592 (F3-E): `bas_gun` pencereyi o günden başlatır (üyelik o gün itibarıyla); `simdi` verilirse geçmiş saatler (şu anki saat öncesi) pencereden düşer."""
    bugun = bugun or pd.Timestamp.now(tz=fn.IST_AD).date()
    bas_gun = bas_gun or bugun
    plants = pt.santraller(tenant_id, portfoy_id, bas_gun)
    if not plants:
        return {"durum": "uye_yok", "santral": 0}
    tz = pt._portfoy_tz(plants)
    bas, bit = pt._utc(bas_gun, tz), pt._utc(bas_gun + timedelta(days=gun), tz)
    if simdi is not None:
        kesim = pd.Timestamp(simdi).tz_convert("UTC").floor("h").to_pydatetime()
        bas = max(bas, kesim)
    if bit <= bas:
        return {"durum": "saat_yok", "santral": len(plants), "not": "Pencerede kalan saat yok."}
    o = pt.saatlik(tenant_id, portfoy_id, bas, bit, kural, bugun, tarih=bas_gun, simdi=simdi)
    if o.get("durum") != "ok":
        return o
    izgara = pd.date_range(bas, bit, freq="h", inclusive="left", tz="UTC")
    progs, kaynaklar = {}, {}
    for p in plants:
        pj = ds._pj(p.get("params_json"))
        try:
            bil = ds.bildirilen_serisi(tenant_id, p["id"], pj, gun + 1).reindex(izgara).astype(float)
        except Exception:   # noqa: BLE001
            bil = pd.Series(np.nan, index=izgara)
        t, _ = pt.tahmin_sec(tenant_id, p, bas, bit, "program")
        on = (t["p50"].reindex(izgara) / 1000.0) if t is not None else pd.Series(np.nan, index=izgara)
        progs[p["name"]] = bil.where(bil.notna(), on)
        kaynaklar[p["name"]] = pd.Series(np.where(bil.notna(), "bildirilen", np.where(on.notna(), "oneri", None)), index=izgara, dtype=object)
    P = pd.DataFrame(progs); K = pd.DataFrame(kaynaklar)
    tam = P.notna().all(axis=1)
    program = P.sum(axis=1, min_count=1).where(tam)   # bir santralin programı yoksa o saat portföy programı eksik (0 sayılmaz)
    kay = pd.Series(np.where(~tam, None, np.where((K == "bildirilen").all(axis=1), "bildirilen", "oneri")), index=izgara, dtype=object)
    t = pd.DataFrame([{"ts": r["ts"], "p50": r["p50_kw"], "p10": r["p10_kw"], "p90": r["p90_kw"]} for r in o["saatlik"]])
    t = t.set_index(pd.to_datetime(t["ts"], utc=True)).drop(columns=["ts"]) if len(t) else pd.DataFrame()
    r = ps.gelecek_risk(t, program, o["belirsizlik"]["durum"], kay, o["kapasite_kwp"])
    sayim = {k: int((kay == k).sum()) for k in ("bildirilen", "oneri")}; sayim["yok"] = int(kay.isna().sum())
    return {"durum": "ok", "portfoy_id": str(portfoy_id), "bugun": bugun.isoformat(), "gun": gun, "tz": tz, "kural": kural, "kural_ad": o["kural_ad"], "santral": len(plants),
            "tahmin_yok": o["tahmin_yok"], "tazelik": o["tazelik"], "belirsizlik": o["belirsizlik"], "program_kaynak": sayim,
            "santral_program": {a: {"mwh": _r(P[a].sum(min_count=1)), "bildirilen_saat": int((K[a] == "bildirilen").sum()), "oneri_saat": int((K[a] == "oneri").sum()), "yok_saat": int(K[a].isna().sum())} for a in P.columns},
            "santral_tahmin": {a: k.get("p50_mwh") for a, k in (o.get("katkilar") or {}).items()}, "pencere": o["pencere"], "kapasite_kwp": o["kapasite_kwp"],
            "risk": r, "gunluk": o["gunluk"], "meta": {"surum": SURUM, "program": "bildirilen KGÜP › program kesimi öncesi tahmin (15:30 kuralı)", "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, bugun)}}
