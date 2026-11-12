"""v2.589 (Faz 3 F3-B) — PORTFÖY TAHMİN SERVİSİ: zamanlı üyelikten santral kümesi, tutarlı koşu seçimi, hizalama, belirsizlik, günlük beklenti,
portföy kapsama sınavı ve yalnız-ekleme kaydı (dogrulama_sonuc, plant_id NULL = portföy; kural «portfoy_gun_oncesi»).

Hesap `ext/tahmin/portfoy_belirsizlik` (saf) ile yapılır; santral tahminleri, kalibrasyon ve MinT DOKUNULMAZ. Eski `/v1/portfoy/tahmin`
(uzlastirma_service) değişmez (B11: naif bant notu ayrı karar).
Koşu seçimi `kural`: «son» = santralın en yeni (geriye bakışlı ve elle olmayan) koşusu; «gun_oncesi» / «program» / «gun_ici» =
bagimsiz_dogrulama_service.kosu_sec (karne kuralı: saat başına tek koşu, aynı yayın kuralı her santralde). Tazelik: santral başına yayın zamanı,
en eski–en yeni farkı saat olarak; eksik tahmini olan santral listelenir, 0 sayılmaz.
Artık geçmişi: son `gecmis_gun` gün, «gun_oncesi» kuralıyla seçilen P50 − ölçüm (SCADA flag='valid'; gündüz), bütün üyeler aynı UTC saatte.
Kapsama sınavı: son `gun` günde her gün için gün öncesi seçimli santral bantları → portföy bandı (ρ aynı pencereden, örneklem içi; meta söyler) →
PICP80 / P(y<P10) / P(y>P90) / Winkler; naif toplam da yanında raporlanır. Sonuç kaydı yalnız ekleme; üyelik anlık görüntüsü meta'da."""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.ext.tahmin import portfoy_belirsizlik as pb
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import karne_kurali as kk
from pvquant.services import portfoy_varlik_service as pv

KURALLAR = ("son", "gun_oncesi", "program", "gun_ici")
KURAL_AD = {"son": "En yeni tahmin", "gun_oncesi": "Gün öncesi tahmin", "program": "Program kesimi öncesi tahmin", "gun_ici": "Gün içi güncelleme"}
GECMIS_GUN = 60
KAPSAMA_GUN = 30
KAPSAMA_KURALI = "portfoy_gun_oncesi"
SOZLUK_SURUMU = pb.YONTEM_SURUMU
TAZELIK_UYARI_SAAT = 6.0


def _r(v, n=1):
    try:
        return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), n)
    except (TypeError, ValueError):
        return None


def _tarih(bugun: date | None, tz: str) -> date:
    return bugun or pd.Timestamp.now(tz=tz).date()


def _utc(gun: date, tz: str) -> datetime:
    return pd.Timestamp(gun, tz=tz).tz_convert("UTC").to_pydatetime()


# ---------------------------------------------------------------- santraller (zamanlı üyelik)
def santraller(tenant_id, portfoy_id, tarih: date) -> list[dict]:
    """O tarihte geçerli üyeler → plant sözlükleri (id, name, capacity_kwp, tz, lat, lon, segment, uyelik)."""
    out = []
    for u in pv.uyeler(tenant_id, portfoy_id, tarih):
        if u.get("archived"):
            continue
        out.append({"id": u["plant_id"], "name": u["santral"], "capacity_kwp": float(u["capacity_kwp"] or 0.0), "tz": u.get("tz") or PIYASA_TZ,
                    "lat": u.get("lat"), "lon": u.get("lon"), "segment": u.get("segment"), "params_json": u.get("params_json") or {},
                    "uyelik": {"kaynak": u["kaynak"], "dogrulama": u["dogrulama"], "gecerli_bas": u["gecerli_bas"], "gecerli_bit": u["gecerli_bit"]}})
    return out


def _portfoy_tz(plants: list[dict]) -> str:
    tzs = [p.get("tz") or PIYASA_TZ for p in plants]
    return max(set(tzs), key=tzs.count) if tzs else PIYASA_TZ


# ---------------------------------------------------------------- koşu seçimi
def tahmin_sec(tenant_id, plant: dict, bas: datetime, bit: datetime, kural: str = "son") -> tuple[pd.DataFrame | None, dict]:
    """[bas, bit) için seçilen tahmin (indeks ts_utc; p50, p10, p90 kW) ve künye {run_at, run_id, n_saat, kural}. Tahmin yoksa (None, künye)."""
    if kural not in KURALLAR:
        raise ValueError("kural " + "|".join(KURALLAR))
    df, _ = bd.tahmin_oku(tenant_id, plant["id"], bas, bit)
    if df is None or df.empty:
        return None, {"run_at": None, "run_id": None, "n_saat": 0, "kural": kural}
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True); df["run_at"] = pd.to_datetime(df["run_at"], utc=True)
    if kural == "son":
        d = df[~kk.geriye_bakisli(df)]
        d = d[d["etiket"].fillna("") != kk.ETIKET_ELLE]
        if d.empty:
            return None, {"run_at": None, "run_id": None, "n_saat": 0, "kural": kural}
        son_run = d.loc[d["run_at"].idxmax(), "run_id"]
        sec = d[d["run_id"] == son_run]
    else:
        sec = bd.kosu_sec(df, kural, plant.get("tz") or PIYASA_TZ)
        if sec is None or sec.empty:
            return None, {"run_at": None, "run_id": None, "n_saat": 0, "kural": kural}
    sec = sec.drop_duplicates("ts_utc").set_index("ts_utc").sort_index()
    out = pd.DataFrame({"p50": pd.to_numeric(sec["p50_kw"], errors="coerce"), "p10": pd.to_numeric(sec["p10_kw"], errors="coerce"),
                        "p90": pd.to_numeric(sec["p90_kw"], errors="coerce")})
    ra = pd.to_datetime(sec["run_at"]).max()
    return out, {"run_at": ra.isoformat(timespec="minutes"), "run_id": str(sec["run_id"].iloc[-1]), "n_saat": int(len(out)), "kural": kural,
                 "yayin_sayisi": int(sec["run_id"].nunique())}


# ---------------------------------------------------------------- artık geçmişi
def artik_gecmisi(tenant_id, plants: list[dict], bas: datetime, bit: datetime, kural: str = "gun_oncesi") -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Santral adı → (y, p50, p10, p90) ve artık tablosu (ts × ad; tahmin − ölçüm, gündüz; eksik NaN)."""
    art, gecmis = {}, {}
    for p in plants:
        t, _ = tahmin_sec(tenant_id, p, bas, bit, kural)
        y = bd.gecmis_olcum_oku(tenant_id, p["id"], bas, bit, geriye_gun=0)
        if t is None or t.empty or y.empty:   # tahmini ya da ölçümü olmayan santral artık tablosuna GİRMEZ (NaN sütunu bütün ortak saatleri düşürürdü)
            gecmis[p["name"]] = pd.DataFrame(columns=["y", "p50", "p10", "p90"]); continue
        y.index = pd.DatetimeIndex(y.index); y.index = y.index.tz_localize("UTC") if y.index.tz is None else y.index.tz_convert("UTC")
        d = t.join(y.rename("y"), how="inner")
        kap = float(p["capacity_kwp"] or 0.0)
        gunduz = (d["y"] > pb.GUNDUZ_ORAN * kap) | (d["p50"] > pb.GUNDUZ_ORAN * kap)
        art[p["name"]] = (d["p50"] - d["y"]).where(gunduz)
        gecmis[p["name"]] = d[["y", "p50", "p10", "p90"]]
    A = pd.DataFrame(art) if art else pd.DataFrame()
    return A, gecmis


# ---------------------------------------------------------------- saatlik / günlük portföy tahmini
def saatlik(tenant_id, portfoy_id, bas: datetime | None = None, bit: datetime | None = None, kural: str = "son", bugun: date | None = None,
            tarih: date | None = None, gecmis_gun: int = GECMIS_GUN, kapsama_sonucu: dict | None = None, simdi: pd.Timestamp | None = None) -> dict:
    """Portföyün saatlik tahmini: üyeler (tarih; varsayılan bugün), her santral aynı `kural` ile seçilir, ortak UTC saat kümesi; ρ son `gecmis_gun`
    günün gün öncesi artıklarından. Varsayılan pencere: bugün 00:00 yerel → +2 gün (bugün ve yarın)."""
    tz0 = PIYASA_TZ   # v2.599
    bugun = _tarih(bugun, tz0); tarih = tarih or bugun
    plants = santraller(tenant_id, portfoy_id, tarih)
    if not plants:
        return {"durum": "uye_yok", "santral": 0, "tarih": tarih.isoformat(), "not": "Bu tarihte portföyün geçerli üyesi yok."}
    tz = _portfoy_tz(plants)
    bas = bas or _utc(bugun, tz); bit = bit or _utc(bugun + timedelta(days=2), tz)
    tahminler, kunye = {}, {}
    for p in plants:
        t, k = tahmin_sec(tenant_id, p, bas, bit, kural)
        tahminler[p["name"]] = t; kunye[p["name"]] = k
    g_bas, g_bit = _utc(bugun - timedelta(days=gecmis_gun), tz), _utc(bugun, tz)
    A, _ = artik_gecmisi(tenant_id, plants, g_bas, g_bit, "gun_oncesi")
    kaps = {p["name"]: p["capacity_kwp"] for p in plants}
    koord = {p["name"]: (float(p["lat"]), float(p["lon"])) for p in plants if p.get("lat") is not None and p.get("lon") is not None}
    ks = kapsama_sonucu if kapsama_sonucu is not None else son_kapsama(tenant_id, portfoy_id)
    o = pb.portfoy_tahmini(tahminler, kaps, A if not A.empty else None, tz, koord, (ks or {}).get("metrik"))
    s = o["saatlik"]
    # tazelik
    yayinlar = {ad: k["run_at"] for ad, k in kunye.items() if k.get("run_at")}
    taz = None
    if yayinlar:
        ts = [pd.Timestamp(v) for v in yayinlar.values()]
        simdi = pd.Timestamp(simdi).tz_convert("UTC") if simdi is not None else pd.Timestamp.now(tz="UTC")
        taz = {"en_yeni": max(ts).isoformat(timespec="minutes"), "en_eski": min(ts).isoformat(timespec="minutes"),
               "fark_saat": _r((max(ts) - min(ts)).total_seconds() / 3600, 1), "en_eski_yas_saat": _r((simdi - min(ts)).total_seconds() / 3600, 1),
               "farkli_yayin": bool((max(ts) - min(ts)).total_seconds() / 3600 > TAZELIK_UYARI_SAAT)}
    katki = {}
    for ad in o["hizalama"]["santral"]:
        c = s[f"{ad}__p50"]
        katki[ad] = {"p50_mwh": _r(c.sum(skipna=False) / 1000.0, 2), "pay_pct": _r(c.sum() / s["p50"].sum() * 100, 1) if s["p50"].sum() > 0 else None,
                     "kapasite_kwp": kaps[ad], "yayin": kunye[ad].get("run_at"), "uyelik": next(p["uyelik"] for p in plants if p["name"] == ad)}
    kayit = [{"ts": t.isoformat(timespec="minutes"), "p50_kw": _r(r.p50), "p10_kw": _r(r.p10), "p90_kw": _r(r.p90), "p10_naif_kw": _r(r.p10_naif), "p90_naif_kw": _r(r.p90_naif),
              "p10_bagimsiz_kw": _r(r.p10_bagimsiz), "p90_bagimsiz_kw": _r(r.p90_bagimsiz), "eksik": bool(r.eksik)} for t, r in s.iterrows()]
    gun = [{"gun": str(g), "p50_mwh": _r(r.p50_mwh, 2), "p10_mwh": _r(r.p10_mwh, 2), "p90_mwh": _r(r.p90_mwh, 2), "p10_naif_mwh": _r(r.p10_naif_mwh, 2),
            "p90_naif_mwh": _r(r.p90_naif_mwh, 2), "saat": int(r.saat)} for g, r in o["gunluk"].iterrows()]
    ko = o["korelasyon"]
    rho = ko["rho"].round(3).to_dict() if ko.get("rho") is not None else None
    return {"durum": "ok", "portfoy_id": str(portfoy_id), "tarih": tarih.isoformat(), "bugun": bugun.isoformat(), "tz": tz, "kural": kural, "kural_ad": KURAL_AD[kural],
            "pencere": {"bas": bas.isoformat(timespec="minutes"), "bit": bit.isoformat(timespec="minutes"), "n_saat": o["hizalama"]["n_saat"]},
            "santral": len(plants), "kapasite_kwp": o["kapasite_kwp"], "katkilar": katki, "tahmin_yok": o["hizalama"]["tahmin_yok"], "eksik_saat": o["hizalama"]["eksik_saat"],
            "tazelik": taz, "saatlik": kayit, "gunluk": gun, "gunluk_meta": o["gunluk_meta"],
            "korelasyon": {"durum": ko["durum"], "n_gun": ko["n_gun"], "n_saat": ko["n_saat"], "yontem": ko["yontem"], "rho": rho, "gecmis_gun": gecmis_gun},
            "bolge": o["bolge"], "belirsizlik": {**o["belirsizlik"], "kapsama": (ks or {}).get("metrik"), "kapsama_hesap_zamani": (ks or {}).get("hesap_zamani")},
            "yontem": o["yontem"], "sozluk_surumu": SOZLUK_SURUMU}


def gunler(tenant_id, portfoy_id, gun: int = 7, kural: str = "son", bugun: date | None = None, gecmis_gun: int = GECMIS_GUN) -> dict:
    """Önümüzdeki `gun` günün günlük beklentisi + hafta/ay dönem bantları (gün bloğu bootstrap)."""
    tz0 = PIYASA_TZ; bugun = _tarih(bugun, tz0)
    plants = santraller(tenant_id, portfoy_id, bugun)
    if not plants:
        return {"durum": "uye_yok", "santral": 0}
    tz = _portfoy_tz(plants)
    o = saatlik(tenant_id, portfoy_id, _utc(bugun, tz), _utc(bugun + timedelta(days=gun), tz), kural, bugun, gecmis_gun=gecmis_gun)
    if o.get("durum") != "ok":
        return o
    A, _ = artik_gecmisi(tenant_id, plants, _utc(bugun - timedelta(days=gecmis_gun), tz), _utc(bugun, tz), "gun_oncesi")
    ga = pb.gunluk_artiklar(A, tz) if not A.empty else pd.Series(dtype=float)
    donem = {}
    for ad, n in (("hafta", 7), ("ay", 30)):
        b = pb.donem_bandi(ga, n)
        donem[ad] = {**b, "q10_mwh": _r(b["q10_kwh"] / 1000.0, 2), "q90_mwh": _r(b["q90_kwh"] / 1000.0, 2)} if b else None
    o["donem_bantlari"] = donem
    o["donem_notu"] = ("Hafta ve ay aralıkları günlük sapmaların gün bloğu bootstrap'ıyla; P10 = toplam − q90, P90 = toplam − q10." if any(donem.values())
                       else "Hafta ve ay aralığı için yeterli ortak gün yok; yalnız merkez beklenti verildi.")
    return o


# ---------------------------------------------------------------- kapsama sınavı (portföy toplamı)
def kapsama(tenant_id, portfoy_id, gun: int = KAPSAMA_GUN, bugun: date | None = None, tarih: date | None = None) -> dict:
    """Son `gun` tam yerel gün: her santral gün öncesi seçimli bant, portföy bandı ρ ile (aynı pencere, örneklem içi), ölçüm Σ y; PICP sınavı.
    Üyelik `tarih` (varsayılan bugün) itibarıyla; pencere içinde üyelik değiştiyse meta uyarır."""
    tz0 = PIYASA_TZ; bugun = _tarih(bugun, tz0); tarih = tarih or bugun
    plants = santraller(tenant_id, portfoy_id, tarih)
    if not plants:
        return {"durum": "uye_yok", "santral": 0, "metrik": pb.kapsama_sinavi(pd.DataFrame(), 1.0)}
    tz = _portfoy_tz(plants)
    bas, bit = _utc(bugun - timedelta(days=gun), tz), _utc(bugun, tz)
    A, gecmis = artik_gecmisi(tenant_id, plants, bas, bit, "gun_oncesi")
    ko = pb.korelasyon(A if not A.empty else None)
    tah = {ad: (g[["p50", "p10", "p90"]] if not g.empty else None) for ad, g in gecmis.items()}
    h = pb.hizala(tah)
    kaps = {p["name"]: p["capacity_kwp"] for p in plants}
    s = pb.saatlik_bant(h, ko["rho"], kaps)
    kap = float(sum(kaps[a] for a in h["santral"]))
    if h["santral"]:
        Y = pd.DataFrame({ad: gecmis[ad]["y"].reindex(h["idx"]) for ad in h["santral"]})
        e = pd.DataFrame({"y": Y.sum(axis=1, skipna=False), "p50": s["p50"], "p10": s["p10"], "p90": s["p90"]})
        e_naif = e.assign(p10=s["p10_naif"], p90=s["p90_naif"]); e_bag = e.assign(p10=s["p10_bagimsiz"], p90=s["p90_bagimsiz"])
    else:
        e = e_naif = e_bag = pd.DataFrame()
    m = pb.kapsama_sinavi(e, kap, tz=tz); mn = pb.kapsama_sinavi(e_naif, kap, tz=tz); mb = pb.kapsama_sinavi(e_bag, kap, tz=tz)
    uyelik_degisti = any((p["uyelik"]["gecerli_bas"] or "0001-01-01") > (bugun - timedelta(days=gun)).isoformat() for p in plants)
    return {"durum": "ok", "portfoy_id": str(portfoy_id), "kural": KAPSAMA_KURALI, "gun": gun, "donem": {"bas": (bugun - timedelta(days=gun)).isoformat(), "bit": bugun.isoformat()},
            "kapasite_kwp": kap, "santral": h["santral"], "tahmin_yok": h["tahmin_yok"], "metrik": m,
            "karsilastirma": {"naif": {k: mn.get(k) for k in ("picp80", "p10_alti", "p90_ustu", "bant_genisligi_oran", "winkler_kw")},
                              "bagimsiz": {k: mb.get(k) for k in ("picp80", "p10_alti", "p90_ustu", "bant_genisligi_oran", "winkler_kw")}},
            "korelasyon": {"durum": ko["durum"], "n_gun": ko["n_gun"], "n_saat": ko["n_saat"], "yontem": ko["yontem"], "rho": ko["rho"].round(3).to_dict() if ko.get("rho") is not None else None},
            "meta": {"sozluk_surumu": SOZLUK_SURUMU, "tz": tz, "uyelik_tarihi": tarih.isoformat(), "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, tarih),
                     "uyelik_pencerede_degisti": bool(uyelik_degisti), "rho_orneklem": "örneklem içi (sınav penceresiyle aynı artıklar)",
                     "secim": "gün öncesi (yerel gün başlamadan önceki son yayın), geriye bakışlı ve elle koşular dışarıda", "olcum": f"SCADA {_ks.sql_kosulu('rapor')}, gündüz saatleri"}}


def kapsama_kaydet(tenant_id, portfoy_id, sonuc: dict) -> str:
    """YALNIZ EKLEME: dogrulama_sonuc, plant_id NULL (portföy), kural «portfoy_gun_oncesi»; meta portföy kimliği + üyelik anlık görüntüsü."""
    if sonuc.get("durum") != "ok":
        raise ValueError("kaydedilecek sonuç yok (üye yok)")
    meta = {**sonuc["meta"], "portfoy_id": str(portfoy_id), "kural": KAPSAMA_KURALI, "kaynak": "scada", "donem": sonuc["donem"], "santral": sonuc["santral"],
            "tahmin_yok": sonuc["tahmin_yok"], "kapasite_kwp": sonuc["kapasite_kwp"], "korelasyon": sonuc["korelasyon"], "karsilastirma": sonuc["karsilastirma"]}
    with tenant_baglami(tenant_id) as s:
        return str(s.execute(text(
            "INSERT INTO dogrulama_sonuc(tenant_id, plant_id, donem_bas, donem_bit, kural, kaynak, sozluk_surumu, metrik_json, meta_json) "
            "VALUES(CAST(:t AS uuid), NULL, :a, :b, :k, 'scada', :sv, CAST(:m AS jsonb), CAST(:me AS jsonb)) RETURNING id"),
            {"t": str(tenant_id), "a": sonuc["donem"]["bas"], "b": sonuc["donem"]["bit"], "k": KAPSAMA_KURALI, "sv": SOZLUK_SURUMU,
             "m": json.dumps(sonuc["metrik"], default=str), "me": json.dumps(meta, default=str)}).scalar())


def son_kapsama(tenant_id, portfoy_id, azami_yas_saat: float | None = 36.0) -> dict | None:
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT id, hesap_zamani, donem_bas, donem_bit, metrik_json, meta_json FROM dogrulama_sonuc WHERE plant_id IS NULL AND kural = :k "
                           "AND meta_json->>'portfoy_id' = :p ORDER BY hesap_zamani DESC LIMIT 1"), {"k": KAPSAMA_KURALI, "p": str(portfoy_id)}).mappings().first()
    if r is None:
        return None
    if azami_yas_saat is not None and (datetime.now(timezone.utc) - r["hesap_zamani"]).total_seconds() > azami_yas_saat * 3600:
        return None
    return {"id": str(r["id"]), "hesap_zamani": r["hesap_zamani"].isoformat(timespec="seconds"), "donem": {"bas": r["donem_bas"].isoformat(), "bit": r["donem_bit"].isoformat()},
            "metrik": r["metrik_json"], "meta": r["meta_json"], "kayitli": True}
