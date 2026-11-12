"""v2.608 (Faz 5 F5-C) — MÜŞTERİ HİZMET SAĞLIĞI: «PVQuant bu santral/kuruluş için şu an kullanılabilir sonuç üretiyor mu?»

Teknik sistem sağlığından (sistem_service: nabız, iş tazeliği, hava/piyasa arşivi, yedek) BAĞIMSIZ hesaplanır: hiçbir boyut jobs_log
başarısına bakarak yeşil olmaz. Beş boyut, her biri küme tabanlı TEK sorgu (santral başına döngüde sorgu yok):
  veri        en yeni geçerli ölçüm damgası + son alınma anı + 7 gün kapsama           (scada_hourly)
  tahmin      en yeni yayımlanmış koşu, yarını kapsıyor mu, girdi yaşları, bağımsız doğrulama (forecast_runs/values, dogrulama_sonuc)
  kgup        yükümlülük (segment), kesim öncesi koşu, öneri sürümü, bildirim beyanı, pencere; kabul HER ZAMAN doğrulanamadı (kgup_surum)
  mutabakat   son kapanmış dönemin EPİAŞ bildirimi takvime göre, sayaç kapsamı, FEM kaydı   (uzlastirma_bildirimi, sayac_saatlik, finansal_etki_sonuc)
  alarm       okunmamış alarm (7 gün), süren olay, 48 saatte başarısız santral işi          (alerts, olay, jobs_log)
Toplama: santral → kuruluş (tenant) → portföy (tarihli üyelik) → platform özeti; hüküm en kötü, sayımlar yanında.
Kiracı sınırı: müşteri ucu tenant_baglami (RLS), platform ucu platform_baglami (adlı). Hesap/formül yazmaz; durum kuralları durum_sozlugu'nda (saf)."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy import text

from pvquant.db import platform_baglami, tenant_baglami
from pvquant.services import durum_sozlugu as ds
from pvquant.services import kalite_sozlugu as _ks
from pvquant.services.dengesizlik_service import (  # inceleme: params_json çözümü tek yardımcıdan
    _pj,
    segment_bilgisi,
)
from pvquant.services.karne_kurali import yayin_kosu_sql as _yayin_sql
from pvquant.zaman import PIYASA_TZ

BOYUTLAR = ("veri", "tahmin", "kgup", "mutabakat", "alarm")
_IST = ZoneInfo(PIYASA_TZ)


def _utc(z):
    if z is None:
        return None
    return z.replace(tzinfo=dt.timezone.utc) if z.tzinfo is None else z.astimezone(dt.timezone.utc)


def _kesim_utc(yarin: dt.date, simdi: dt.datetime) -> dt.datetime:
    """Yarının programı için D-1 kesimi (İstanbul; kurallar.kgup_kesim) — henüz geçmediyse «şimdi» (kgup_service.kaynak_kosu_df ile aynı)."""
    from pvquant.ext.turkiye import kurallar as kr
    (kh, km), _ = kr.kgup_kesim(yarin)
    kesim = dt.datetime.combine(yarin - dt.timedelta(days=1), dt.time(kh, km), tzinfo=_IST).astimezone(dt.timezone.utc)
    return min(kesim, simdi)


def _sinyaller(s, simdi: dt.datetime, tenant_id: str | None = None) -> dict:
    """Beş boyutun ham sinyalleri, santral kimliğine göre sözlükler. Kiracı süzgeci yalnız platform bağlamında anlamlıdır (RLS yoksa)."""
    p = {"t": tenant_id}
    kosul = "AND p.tenant_id = CAST(:t AS uuid)" if tenant_id else ""
    santraller = s.execute(text(
        "SELECT p.id, p.name, p.tz, p.params_json, p.capacity_kwp, p.tenant_id, t.name AS kiraci, t.status AS kiraci_durum "
        f"FROM plants p JOIN tenants t ON t.id = p.tenant_id WHERE NOT p.archived {kosul} ORDER BY t.name, p.name"), p).mappings().all()
    ids = [r["id"] for r in santraller]
    if not ids:
        return {"santraller": [], "veri": {}, "kosu": {}, "kapsam": {}, "dogrulama": {}, "kesim": {}, "surum": {}, "bildirim": {}, "fem": {}, "sayac": {},
                "alarm": {}, "olay": {}, "hata": {}, "portfoy": []}
    q = {"ids": ids}
    yarin = (simdi.astimezone(_IST).date() + dt.timedelta(days=1))
    bugun_ist = simdi.astimezone(_IST).date()
    donem = (bugun_ist.replace(day=1) - dt.timedelta(days=1)).replace(day=1)   # son kapanmış ay
    veri = {r["plant_id"]: r for r in s.execute(text(
        f"SELECT plant_id, max(ts_utc) FILTER (WHERE {_ks.sql_kosulu('tazelik')}) AS son_olcum, max(alinma_zamani) AS son_alim, "
        f"count(*) FILTER (WHERE {_ks.sql_kosulu('tazelik')} AND ts_utc >= :s - interval '7 days') AS n7 "
        "FROM scada_hourly WHERE plant_id = ANY(:ids) GROUP BY plant_id"), {**q, "s": simdi}).mappings().all()}
    kosu = {r["plant_id"]: r for r in s.execute(text(
        "SELECT DISTINCT ON (r.plant_id) r.plant_id, r.id AS run_id, r.run_at, COALESCE(r.etiket, 'yayin') AS etiket, r.veri_kalitesi_json FROM forecast_runs r "
        f"WHERE r.plant_id = ANY(:ids) AND {_yayin_sql('r')} AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id = r.id) "
        "ORDER BY r.plant_id, r.run_at DESC, r.id DESC"), q).mappings().all()}
    kapsam = {}
    if kosu:
        kapsam = {r["run_id"]: r["son_ts"] for r in s.execute(text(
            "SELECT run_id, max(ts_utc) AS son_ts FROM forecast_values WHERE run_id = ANY(:rids) GROUP BY run_id"),
            {"rids": [k["run_id"] for k in kosu.values()]}).mappings().all()}
    dogrulama = {r["plant_id"]: r["son"] for r in s.execute(text(
        "SELECT plant_id, max(hesap_zamani) AS son FROM dogrulama_sonuc WHERE plant_id = ANY(:ids) GROUP BY plant_id"), q).mappings().all()}
    kesim = {r["plant_id"]: r["run_at"] for r in s.execute(text(
        "SELECT DISTINCT ON (r.plant_id) r.plant_id, r.run_at FROM forecast_runs r "
        f"WHERE r.plant_id = ANY(:ids) AND r.run_at <= :kesim AND {_yayin_sql('r')} "
        "AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id = r.id AND v.ts_utc >= :a AND v.ts_utc < :b) "
        "ORDER BY r.plant_id, r.run_at DESC, r.id DESC"),
        {**q, "kesim": _kesim_utc(yarin, simdi),
         "a": dt.datetime.combine(yarin, dt.time(0), tzinfo=_IST).astimezone(dt.timezone.utc),
         "b": dt.datetime.combine(yarin + dt.timedelta(days=1), dt.time(0), tzinfo=_IST).astimezone(dt.timezone.utc)}).mappings().all()}
    surum: dict = {}
    for r in s.execute(text(
            "SELECT plant_id, kaynak, max(surum) AS surum, max(olusturma) AS son FROM kgup_surum WHERE plant_id = ANY(:ids) AND teslim_gunu = :g "
            "GROUP BY plant_id, kaynak"), {**q, "g": yarin}).mappings().all():
        surum.setdefault(r["plant_id"], {})[r["kaynak"]] = {"surum": int(r["surum"]), "son": r["son"]}
    bildirim = {r["plant_id"]: r for r in s.execute(text(
        "SELECT plant_id, bool_or(surum = 'nihai') AS nihai, max(olusturma) AS son FROM uzlastirma_bildirimi "
        "WHERE plant_id = ANY(:ids) AND donem = :d GROUP BY plant_id"), {**q, "d": donem}).mappings().all()}
    fem = {r["plant_id"]: r["son"] for r in s.execute(text(
        "SELECT plant_id, max(hesap_zamani) AS son FROM finansal_etki_sonuc WHERE plant_id = ANY(:ids) AND donem_kodu = :k GROUP BY plant_id"),
        {**q, "k": donem.strftime("%Y-%m")}).mappings().all()}
    sayac = {r["plant_id"]: r["son"] for r in s.execute(text(
        "SELECT plant_id, max(ts_utc) AS son FROM sayac_saatlik WHERE plant_id = ANY(:ids) GROUP BY plant_id"), q).mappings().all()}
    alarm = {r["plant_id"]: r for r in s.execute(text(
        "SELECT plant_id, count(*) FILTER (WHERE severity = 'critical') AS kritik, count(*) FILTER (WHERE severity IS DISTINCT FROM 'critical') AS uyari "
        "FROM alerts WHERE plant_id = ANY(:ids) AND acked_by IS NULL AND created_at >= :s - (:g * interval '1 day') GROUP BY plant_id"),
        {**q, "s": simdi, "g": ds.ESIK["alarm_gun"]}).mappings().all()}
    olay = {r["plant_id"]: int(r["n"]) for r in s.execute(text(
        "SELECT plant_id, count(*) AS n FROM olay WHERE plant_id = ANY(:ids) AND durum = 'acik' AND baslangic <= :s AND (bitis IS NULL OR bitis > :s) "
        "GROUP BY plant_id"), {**q, "s": simdi}).mappings().all()}
    hata = {r["plant_id"]: r for r in s.execute(text(
        "SELECT DISTINCT ON (plant_id) plant_id, job, started FROM jobs_log WHERE plant_id = ANY(:ids) AND status IS DISTINCT FROM 'ok' "
        "AND started >= :s - (:h * interval '1 hour') ORDER BY plant_id, started DESC"), {**q, "s": simdi, "h": ds.ESIK["is_hatasi_saat"]}).mappings().all()}
    portfoy = s.execute(text(
        "SELECT po.id, po.ad, po.tur, po.tenant_id, pu.plant_id FROM portfoy po JOIN portfoy_uyelik pu ON pu.portfoy_id = po.id "
        "WHERE pu.plant_id = ANY(:ids) AND pu.gecerli_bas <= :g AND (pu.gecerli_bit IS NULL OR pu.gecerli_bit >= :g) "
        "AND po.gecerli_bas <= :g AND (po.gecerli_bit IS NULL OR po.gecerli_bit >= :g) ORDER BY po.ad"), {**q, "g": bugun_ist}).mappings().all()
    return {"santraller": santraller, "veri": veri, "kosu": kosu, "kapsam": kapsam, "dogrulama": dogrulama, "kesim": kesim, "surum": surum,
            "bildirim": bildirim, "fem": fem, "sayac": sayac, "alarm": alarm, "olay": olay, "hata": hata, "portfoy": portfoy,
            "yarin": yarin, "donem": donem, "bugun": bugun_ist}


def _yarini_kapsar(son_ts, tz: str, simdi: dt.datetime) -> bool | None:
    """Koşunun son saati yarının (santral yerel günü) son saatine ulaşıyor mu."""
    if son_ts is None:
        return None
    try:
        z = ZoneInfo(tz or PIYASA_TZ)
    except Exception:  # noqa: BLE001
        z = _IST
    yarin_son = dt.datetime.combine(simdi.astimezone(z).date() + dt.timedelta(days=1), dt.time(23), tzinfo=z)
    return _utc(son_ts) >= yarin_son.astimezone(dt.timezone.utc)


def _santral_sinifla(r, sg: dict, simdi: dt.datetime, pencere: dict, takvim: dict) -> dict:
    pid = r["id"]
    pj = _pj(r["params_json"])
    seg = segment_bilgisi(pj)
    v = sg["veri"].get(pid) or {}
    k = sg["kosu"].get(pid)
    sur = sg["surum"].get(pid, {})
    bil = sg["bildirim"].get(pid)
    al = sg["alarm"].get(pid) or {}
    ht = sg["hata"].get(pid)
    boyut = {
        "veri": ds.veri_durumu(v.get("son_olcum"), v.get("son_alim"), simdi, kapsama_saat_7g=(int(v["n7"]) if v else 0)),
        "tahmin": ds.tahmin_durumu(k["run_at"] if k else None, _yarini_kapsar(sg["kapsam"].get(k["run_id"]) if k else None, r["tz"], simdi), simdi,
                                   son_olcum=v.get("son_olcum"), veri_kalitesi=(k["veri_kalitesi_json"] if k else None), son_dogrulama=sg["dogrulama"].get(pid)),
        "kgup": ds.kgup_durumu(seg["kgup_yukumlu"], sg["kesim"].get(pid), (sur.get("pvquant") or {}).get("surum"), (sur.get("musteri") or {}).get("son"), pencere,
                               eksik=([] if seg.get("uevcb") or not seg["kgup_yukumlu"] else ["uevcb"])),
        "mutabakat": ds.mutabakat_durumu(sg["donem"].strftime("%Y-%m"), bil is not None, bool(bil["nihai"]) if bil else False, sg["bugun"],
                                         takvim["on"], takvim["nihai"], segment_var=seg["segment"] is not None, sayac_son=sg["sayac"].get(pid),
                                         fem_kayitli=(sg["fem"].get(pid) is not None) if (v.get("son_olcum") is not None) else None),
        "alarm": ds.alarm_durumu(int(al.get("kritik") or 0), int(al.get("uyari") or 0), sg["olay"].get(pid, 0), ht["started"] if ht else None, simdi),
    }
    if ht:
        from pvquant.services.isler_service import ISIM_TR
        boyut["alarm"]["son_is"] = ISIM_TR.get(ht["job"], ht["job"])
    if k:   # inceleme: Genel bakış yayın zamanını/etiketini aynı (süzgeçli) koşudan okur; kosu_gecmisi süzgeçsizdir
        boyut["tahmin"]["etiket_kosu"] = k["etiket"]
    hukum = ds.santral_hukmu(boyut)
    return {"id": str(pid), "ad": r["name"], "kapasite_kwp": float(r["capacity_kwp"] or 0), "tenant_id": str(r["tenant_id"]), "kiraci": r["kiraci"],
            "kiraci_durum": r["kiraci_durum"], "segment": seg["segment"], **hukum, "boyutlar": boyut}


def _topla(santraller: list[dict], anahtar: str, ad_alani: str) -> list[dict]:
    gruplar: dict = {}
    for p in santraller:
        g = gruplar.setdefault(p[anahtar], {"id": p[anahtar], "ad": p[ad_alani], "santral": 0, "durumlar": [], "boyut": {b: [] for b in BOYUTLAR}, "dikkat_santral": []})
        g["santral"] += 1
        g["durumlar"].append(p["durum"])
        for b in BOYUTLAR:
            g["boyut"][b].append(p["boyutlar"][b]["durum"])
        if p["durum"] in (ds.Durum.KRITIK.value, ds.Durum.DIKKAT.value):
            g["dikkat_santral"].append({"id": p["id"], "ad": p["ad"], "durum": p["durum"], "eylem_gereken": p["eylem_gereken"]})
    out = []
    for g in gruplar.values():
        genel = ds.en_kotu(g["durumlar"])
        out.append({"id": g["id"], "ad": g["ad"], "santral": g["santral"], "durum": genel.value, "etiket": ds.etiket(genel), "sayim": ds.sayim(g["durumlar"]),
                    "boyut": {b: {"durum": ds.en_kotu(v).value, "sayim": ds.sayim(v)} for b, v in g["boyut"].items()},
                    "dikkat_santral": sorted(g["dikkat_santral"], key=lambda x: (ds.SIRA.index(ds.Durum(x["durum"])), x["ad"]))})
    return sorted(out, key=lambda x: (ds.SIRA.index(ds.Durum(x["durum"])), x["ad"] or ""))


def _hesapla(s, simdi: dt.datetime, tenant_id: str | None, *, yalniz_sorunlu: bool = False) -> dict:
    import pandas as pd

    from pvquant.ext.turkiye import kgup as kg
    from pvquant.ext.turkiye import takvim as tk
    sg = _sinyaller(s, simdi, tenant_id)
    if not sg["santraller"]:
        return {"zaman": simdi.isoformat(), "santraller": [], "kuruluslar": [], "portfoyler": [], "ozet": {"santral": 0, "durum": ds.Durum.UYGULANMIYOR.value,
                "etiket": ds.etiket(ds.Durum.UYGULANMIYOR), "sayim": ds.sayim([]), "boyut": {}}, "esik": dict(ds.ESIK), "sozluk_surumu": ds.SOZLUK_SURUMU,
                "not": "etkin santral yok"}
    pencere = kg.teslim_durumu(pd.Timestamp(simdi))
    t = {o["kod"]: o for o in tk.donem_takvimi(sg["donem"].year, sg["donem"].month)}
    takvim = {"on": dt.date.fromisoformat(t["on_bildirim"]["tarih"]), "nihai": dt.date.fromisoformat(t["nihai_bildirim"]["tarih"])}
    santraller = [_santral_sinifla(r, sg, simdi, pencere, takvim) for r in sg["santraller"]]
    kuruluslar = _topla(santraller, "tenant_id", "kiraci")
    # portföy: tarihli üyelikten; santral hükmü santral listesinden (ikinci hesap yok)
    by_id = {p["id"]: p for p in santraller}
    pgrup: dict = {}
    for r in sg["portfoy"]:
        p = by_id.get(str(r["plant_id"]))
        if p is None:
            continue
        g = pgrup.setdefault(str(r["id"]), {"id": str(r["id"]), "ad": r["ad"], "tur": r["tur"], "tenant_id": str(r["tenant_id"]), "uyeler": []})
        g["uyeler"].append({**p, "portfoy_id": str(r["id"]), "portfoy_ad": r["ad"]})
    portfoyler = []
    for g in pgrup.values():
        top = _topla(g["uyeler"], "portfoy_id", "portfoy_ad")[0]
        portfoyler.append({**top, "tur": g["tur"], "tenant_id": g["tenant_id"]})
    durumlar = [p["durum"] for p in santraller]
    genel = ds.en_kotu(durumlar)
    ozet = {"santral": len(santraller), "kurulus": len(kuruluslar), "durum": genel.value, "etiket": ds.etiket(genel), "sayim": ds.sayim(durumlar),
            "boyut": {b: {"durum": ds.en_kotu([p["boyutlar"][b]["durum"] for p in santraller]).value,
                          "sayim": ds.sayim([p["boyutlar"][b]["durum"] for p in santraller])} for b in BOYUTLAR},
            "dikkat_kurulus": sum(1 for k in kuruluslar if k["durum"] in (ds.Durum.KRITIK.value, ds.Durum.DIKKAT.value))}
    if yalniz_sorunlu:
        santraller = [p for p in santraller if p["durum"] in (ds.Durum.KRITIK.value, ds.Durum.DIKKAT.value)]
    return {"zaman": simdi.isoformat(), "yarin": sg["yarin"].isoformat(), "donem": sg["donem"].strftime("%Y-%m"), "pencere": pencere,
            "santraller": santraller, "kuruluslar": kuruluslar, "portfoyler": portfoyler, "ozet": ozet, "boyutlar": list(BOYUTLAR),
            "esik": dict(ds.ESIK), "sozluk_surumu": ds.SOZLUK_SURUMU,
            "not": "Hizmet sağlığı teknik iş başarısından bağımsız hesaplanır; TPYS kabulü ve EPİAŞ uzlaştırma durumu doğrulanamaz."}


def ozet(tenant_id, simdi: dt.datetime | None = None) -> dict:
    """Müşteri ucu: kiracının santralleri (RLS). Kuruluş listesi tek öğedir; platform alanları (kiraci adı) kiracının kendi adıdır."""
    simdi = _utc(simdi) if simdi else dt.datetime.now(dt.timezone.utc)
    with tenant_baglami(tenant_id) as s:
        return _hesapla(s, simdi, None)


def platform_ozet(aktor_id: str, tenant_id: str | None = None, *, yalniz_sorunlu: bool = False, simdi: dt.datetime | None = None) -> dict:
    """Platform ucu: tüm kiracılar (ya da biri); adlı bağlam. Hata ayrıntısı (jobs_log.detail) burada da yok — hizmet görünümü teknik günlük değildir."""
    simdi = _utc(simdi) if simdi else dt.datetime.now(dt.timezone.utc)
    with platform_baglami(aktor_id) as s:
        return _hesapla(s, simdi, tenant_id, yalniz_sorunlu=yalniz_sorunlu)
