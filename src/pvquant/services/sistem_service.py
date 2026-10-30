"""25.10 Faz 3 — SİSTEM İZLEME (platform): zamanlayıcı nabzı, kiracılar arası iş kayıtları (hata ayrıntısıyla),
santral envanteri ve tazelik özeti (gece turu, hava arşivi, piyasa fiyatı, yedek).

Salt okunur servis; tek yazan `nabiz_yaz` (worker, sistem bağlamı). Tahmin/kalibrasyon/hesap servislerine dokunmaz;
«gece turu taze mi» ölçütü isler_service.bayat_isler ile BİREBİR aynıdır (müşteri ve platform aynı hükmü görür).
Okumalar `platform_baglami(aktör)` ile: RLS dışı ama adlı. Müşteri `/v1/isler` sözleşmesi değişmez — orada hata
ayrıntısı bilerek yoktur (v2.282 ilkesi); platform ucu ayrıntıyı gösterir, çünkü günlüğe bakacak olan zaten personeldir."""
from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import text

from pvquant.db import sistem_baglami, platform_baglami
from pvquant.services.isler_service import ISIM_TR, URETEN_ISLER, bayat_isler

NABIZ_ARALIK_DK = 5       # worker nabız sıklığı
NABIZ_SESSIZ_DK = 15      # üç kaçırılmış nabız → «sessiz»
BAYAT_SAAT = 30           # isler_service ile aynı eşik
SCADA_BAYAT_SAAT = 48     # santral envanteri: geçerli SCADA bundan eskiyse sorun
KOSU_BAYAT_SAAT = 30      # santral envanteri: son tahmin koşusu bundan eskiyse sorun
METEO_BAYAT_SAAT = 36     # gece_meteo günlük: son indirme bundan eskiyse hava verisi bayat
PIYASA_BAYAT_SAAT = 36    # gece_piyasa günlük: son güncelleme bundan eskiyse piyasa verisi bayat
YEDEK_BAYAT_SAAT = 30     # gece_yedek günlük (+ açılış yakalaması 24 sa): son başarılı yedek bundan eskiyse bayat
# v2.516 (yönetim boşlukları #3): PLATFORM izleme listesi — uzlaştırma, piyasa ve bakım işleri; her işin kendi eşiği (saat) ve sıklığı.
# Müşteri hükmü (isler_service.URETEN_ISLER / bayat_isler) DEĞİŞMEZ: bu işler düşünce müşteri kartı değil platform kartı uyarır.
# (kod, eşik saat, sıklık, santral gerekir mi — _logla ile santral başına koşan işler 0 santralde iz bırakmaz)
IZLENEN_ISLER = (
    ("gun_ici_tahmin", 30, "gün içi", True),            # ayar (gun_ici_guncelleme) kapalıysa beklenmez
    ("kgup_revizyon_kontrol", 30, "gün içi", True),     # 07:10–18:10 TSİ saat başı
    ("kgup_teslim_kontrol", 36, "günlük", True),        # 15:35 TSİ
    ("gun_oncesi_ptf", 36, "günlük", False),            # 14:35 TSİ; «henuz_yok» da başarılı koşudur
    ("gece_piyasa", 36, "günlük", False),
    ("gece_epias_uretim", 36, "günlük", True),
    ("alarm", 36, "günlük", True),
    ("gece_hijyen", 36, "günlük", True),
    ("gece_ufuk_sigma", 36, "günlük", True),
    ("gece_konformal", 36, "günlük", True),
    ("rapor_alanlari", 36, "günlük", True),
    ("kgup_arsiv_temizlik", 24 * 35, "aylık", False),   # ayın 1'i; hiç koşmamışsa «henüz koşmadı» (uyarı değil)
    ("denetim_temizlik", 24 * 35, "aylık", False),
)
_iso = lambda v: v.isoformat() if v else None  # noqa: E731


def nabiz_yaz(bilesen: str = "worker", ayrinti: dict | None = None) -> None:
    """Worker'dan çağrılır: bileşen başına tek satır UPSERT. Hata yutulur ve günlüğe yazılır — nabız, asıl işleri düşürmez."""
    try:
        with sistem_baglami() as s:
            s.execute(text("INSERT INTO sistem_nabiz(bilesen, zaman, ayrinti) VALUES (:b, now(), CAST(:a AS jsonb)) "
                           "ON CONFLICT (bilesen) DO UPDATE SET zaman = now(), ayrinti = EXCLUDED.ayrinti"),
                      {"b": bilesen, "a": json.dumps(ayrinti or {}, default=str)})
    except Exception as e:  # noqa: BLE001
        print(f"[nabiz] yazılamadı: {type(e).__name__}: {e}")


def _yas_dk(zaman, simdi) -> int | None:
    """Negatife düşmez: DB ile uygulama saati birkaç saniye kayarsa «-1 dk» yazmasın."""
    return None if zaman is None else max(0, int((simdi - zaman).total_seconds() // 60))


def ozet(aktor_id: str) -> dict:
    """Sistem sayfasının KPI'ları. Her alan ya gerçek değer ya None — hiçbir değer uydurulmaz."""
    simdi = dt.datetime.now(dt.timezone.utc)
    with platform_baglami(aktor_id) as s:
        nabiz = s.execute(text("SELECT zaman, ayrinti FROM sistem_nabiz WHERE bilesen = 'worker'")).mappings().first()
        son_ok = {r["job"]: r["son"] for r in s.execute(text(
            "SELECT job, max(started) AS son FROM jobs_log WHERE status = 'ok' AND job = ANY(:g) GROUP BY job"),
            {"g": list(URETEN_ISLER)}).mappings().all()}
        gece_son = s.execute(text("SELECT max(started) FROM jobs_log WHERE job = ANY(:g)"), {"g": list(URETEN_ISLER)}).scalar()
        sayim = s.execute(text(
            "SELECT count(*) AS toplam, count(*) FILTER (WHERE status <> 'ok') AS hata "
            "FROM jobs_log WHERE started >= now() - interval '24 hours'")).mappings().first()
        yedek_ok = s.execute(text("SELECT max(started) FROM jobs_log WHERE job IN ('gece_yedek','acilis_yedek') AND status = 'ok'")).scalar()
        yedek_son = s.execute(text(
            "SELECT started, status, detail FROM jobs_log WHERE job IN ('gece_yedek','acilis_yedek') "
            "ORDER BY started DESC LIMIT 1")).mappings().first()
        piyasa = s.execute(text(
            "SELECT max(ts_utc) AS son_ts, max(guncelleme) AS son_guncelleme, count(*) AS satir FROM piyasa_fiyat")).mappings().first()
        # v2.516 (#4): yön kapsamı ve gün öncesi PTF — 29.10'da yön 0 saatti, kart «güncel»di; artık yön ayrı sınanır
        piyasa_ek = s.execute(text(
            "SELECT max(ts_utc) FILTER (WHERE yon IS NOT NULL AND kaynak = 'epias') AS yon_son, "
            "count(yon) FILTER (WHERE kaynak = 'epias' AND ts_utc >= now() - interval '7 days') AS yon_saat_7g, "
            "count(*) FILTER (WHERE kaynak = 'epias' AND ts_utc >= now() - interval '7 days') AS saat_7g, "
            "max(ts_utc) FILTER (WHERE kaynak = 'epias_gop') AS gop_son FROM piyasa_fiyat")).mappings().first()
        # v2.516 (#3): izlenen işlerin son başarılı koşusu
        izlenen_son = {r["job"]: r["son"] for r in s.execute(text(
            "SELECT job, max(started) AS son FROM jobs_log WHERE status = 'ok' AND job = ANY(:g) GROUP BY job"),
            {"g": [k for k, *_ in IZLENEN_ISLER]}).mappings().all()}
        santral = s.execute(text(
            "SELECT count(*) FILTER (WHERE NOT archived) AS etkin, count(*) FILTER (WHERE archived) AS arsivli FROM plants")).mappings().first()
        db_boyut = s.execute(text("SELECT pg_database_size(current_database())")).scalar()
    try:
        from pvquant.io.acik_nwp import arsiv_durumu
        arsiv = arsiv_durumu()
    except Exception:  # noqa: BLE001 — arşiv tablosu boş/yok: sayfa yine açılır
        arsiv = {}
    bayat = bayat_isler(BAYAT_SAAT)
    nabiz_yas = _yas_dk(nabiz["zaman"], simdi) if nabiz else None

    def saat_yas(z) -> float | None:
        if z is None:
            return None
        if isinstance(z, str):
            z = dt.datetime.fromisoformat(z)
        return max(0.0, round((simdi - z).total_seconds() / 3600, 1))

    def bayat_mi(yas: float | None, esik: int) -> bool:
        return yas is None or yas > esik
    piyasa_yas, yedek_yas = saat_yas(piyasa["son_guncelleme"]), saat_yas(yedek_ok)
    izlenen = _izlenen(izlenen_son, simdi, int(santral["etkin"]))
    try:
        from pvquant.services.piyasa_service import kimlik_var
        kimlik: bool | None = bool(kimlik_var())
    except Exception:  # noqa: BLE001 — ayar okunamazsa hüküm verilmez
        kimlik = None
    yon_son, son_ts = piyasa_ek["yon_son"], piyasa["son_ts"]
    yon_bayat = yon_son is None or (son_ts is not None and (son_ts - yon_son) > dt.timedelta(hours=24))   # yön, fiyatın 1 günden fazla gerisindeyse eksik
    return {
        "zaman": simdi.isoformat(),
        "nabiz": {"durum": "yok" if nabiz is None else ("calisiyor" if nabiz_yas <= NABIZ_SESSIZ_DK else "sessiz"),
                  "son": _iso(nabiz["zaman"]) if nabiz else None, "yas_dk": nabiz_yas,
                  "ayrinti": (nabiz["ayrinti"] if isinstance(nabiz["ayrinti"], dict) else json.loads(nabiz["ayrinti"] or "{}")) if nabiz else {},
                  "aralik_dk": NABIZ_ARALIK_DK, "sessiz_dk": NABIZ_SESSIZ_DK},
        "gece_turu": {"taze": not bayat, "bayat_isler": [ISIM_TR.get(b, b) for b in bayat], "son": _iso(gece_son), "esik_saat": BAYAT_SAAT,
                      "uretici_isler": [{"kod": j, "is": ISIM_TR.get(j, j), "son_ok": _iso(son_ok.get(j))} for j in URETEN_ISLER]},
        "isler_24": {"toplam": int(sayim["toplam"]), "hata": int(sayim["hata"])},
        "meteo": {"esik_saat": METEO_BAYAT_SAAT,
                  "kaynaklar": [{"kaynak": k, "son_indirme": v.get("son"), "nokta": v.get("nokta"), "satir": v.get("satir"),
                                 "ilk": v.get("ilk"), "son_ts": v.get("son_ts"), "yas_saat": saat_yas(v.get("son")),
                                 "bayat": bayat_mi(saat_yas(v.get("son")), METEO_BAYAT_SAAT)} for k, v in sorted(arsiv.items())]},
        "piyasa": {"son_ts": _iso(piyasa["son_ts"]), "son_guncelleme": _iso(piyasa["son_guncelleme"]), "satir": int(piyasa["satir"]),
                   "yas_saat": piyasa_yas, "esik_saat": PIYASA_BAYAT_SAAT, "bayat": bayat_mi(piyasa_yas, PIYASA_BAYAT_SAAT),
                   # v2.516 (#4)
                   "kimlik": kimlik, "yon_son": _iso(yon_son), "yon_saat_7g": int(piyasa_ek["yon_saat_7g"] or 0),
                   "saat_7g": int(piyasa_ek["saat_7g"] or 0), "yon_bayat": bool(yon_bayat), "gop_son": _iso(piyasa_ek["gop_son"])},
        "izlenen": izlenen,   # v2.516 (#3)
        "yedek": {"son_basarili": _iso(yedek_ok), "yas_saat": yedek_yas, "esik_saat": YEDEK_BAYAT_SAAT, "bayat": bayat_mi(yedek_yas, YEDEK_BAYAT_SAAT),
                  "son_deneme": None if yedek_son is None else {"zaman": _iso(yedek_son["started"]), "tamam": yedek_son["status"] == "ok",
                                                                "ayrinti": yedek_son["detail"] or None}},
        "db": {"boyut_bayt": int(db_boyut or 0)},
        "santral": {"etkin": int(santral["etkin"]), "arsivli": int(santral["arsivli"])},
    }


def _izlenen(son_ok: dict, simdi: dt.datetime, etkin_santral: int) -> dict:
    """v2.516 (#3): IZLENEN_ISLER için durum kodu — ok / esik_asimi / henuz_yok (aylık iş hiç koşmadı) / beklenmiyor (ayar kapalı ya da santral yok).
    Kodlar görünen sözcük değildir (panel sözlükten «güncel/eski» yazar).
    `bayat` listesi platform kartının hükmüne girer; müşteri hükmüne girmez."""
    try:
        from pvquant.config import get_settings
        gun_ici_acik = bool(get_settings().gun_ici_guncelleme)
    except Exception:  # noqa: BLE001
        gun_ici_acik = True
    isler_, bayat = [], []
    for kod, esik, siklik, santral_gerek in IZLENEN_ISLER:
        son = son_ok.get(kod)
        if isinstance(son, str):
            son = dt.datetime.fromisoformat(son)
        yas = None if son is None else max(0.0, round((simdi - son).total_seconds() / 3600, 1))
        not_ = None
        if kod == "gun_ici_tahmin" and not gun_ici_acik:
            durum, not_ = "beklenmiyor", "gün içi güncelleme ayarı kapalı"
        elif santral_gerek and etkin_santral == 0:
            durum, not_ = "beklenmiyor", "etkin santral yok; iş santral başına koşar"
        elif son is None:
            durum = "henuz_yok" if siklik == "aylık" else "esik_asimi"
        else:
            durum = "esik_asimi" if yas > esik else "ok"
        if durum == "esik_asimi":
            bayat.append(ISIM_TR.get(kod, kod))
        isler_.append({"kod": kod, "is": ISIM_TR.get(kod, kod), "siklik": siklik, "esik_saat": esik, "son_ok": _iso(son),
                       "yas_saat": yas, "durum": durum, "not": not_})
    return {"isler": isler_, "bayat": bayat}


def alarmlar(aktor_id: str) -> dict:
    """v2.516 (#5): müşteriler arası AÇIK alarm özeti — tanım müşteri panelindekiyle aynı (okunmamış ve 7 günden yeni; damga_service).
    Kural etiketi arka uçtan (alarm_service.KURAL_ETIKET); panel ham kod göstermez."""
    from pvquant.services.alarm_service import KURAL_ETIKET
    with platform_baglami(aktor_id) as s:
        rows = s.execute(text(
            "SELECT rule, count(*) AS n, count(DISTINCT tenant_id) AS musteri FROM alerts "
            "WHERE acked_by IS NULL AND created_at >= now() - interval '7 days' GROUP BY rule ORDER BY n DESC, rule")).mappings().all()
        top = s.execute(text(
            "SELECT count(*) AS n, count(DISTINCT tenant_id) AS musteri, count(DISTINCT plant_id) AS santral, min(created_at) AS en_eski "
            "FROM alerts WHERE acked_by IS NULL AND created_at >= now() - interval '7 days'")).mappings().first()
    return {"acik": int(top["n"] or 0), "musteri": int(top["musteri"] or 0), "santral": int(top["santral"] or 0),
            "en_eski": _iso(top["en_eski"]), "pencere_gun": 7,
            "kurallar": [{"kural": r["rule"], "etiket": KURAL_ETIKET.get(r["rule"], r["rule"]), "adet": int(r["n"]), "musteri": int(r["musteri"])}
                         for r in rows]}


def isler(aktor_id: str, *, saat: int = 48, yalniz_hata: bool = False, job: str | None = None,
          tenant_id: str | None = None, limit: int = 200, plant_id: str | None = None) -> dict:
    """Kiracılar arası iş kayıtları, hata ayrıntısı (jobs_log.detail) DAHİL. Kiracı ve santral adı birleştirilir;
    silinmiş santral/kiracı için ad None kalır (satır yine görünür)."""
    kosul, p = ["j.started >= now() - (:h * interval '1 hour')"], {"h": max(1, min(int(saat), 24 * 30)), "n": max(1, min(int(limit), 1000))}
    if yalniz_hata:
        kosul.append("j.status <> 'ok'")
    if job:
        kosul.append("j.job = :j"); p["j"] = job
    if tenant_id:
        kosul.append("j.tenant_id = CAST(:t AS uuid)"); p["t"] = str(tenant_id)
    if plant_id:   # 26.10 D2: envanterden «son hata» tıklaması
        kosul.append("j.plant_id = CAST(:pl AS uuid)"); p["pl"] = str(plant_id)
    with platform_baglami(aktor_id) as s:
        rows = s.execute(text(
            "SELECT j.id, j.job, j.tenant_id, t.name AS kiraci, j.plant_id, p.name AS santral, j.started, j.finished, j.status, j.detail "
            "FROM jobs_log j LEFT JOIN tenants t ON t.id = j.tenant_id LEFT JOIN plants p ON p.id = j.plant_id "
            f"WHERE {' AND '.join(kosul)} ORDER BY j.started DESC LIMIT :n"), p).mappings().all()
    cikti = []
    for r in rows:
        sure = None if r["finished"] is None else round((r["finished"] - r["started"]).total_seconds(), 1)
        cikti.append({"id": str(r["id"]), "kod": r["job"], "is": ISIM_TR.get(r["job"], r["job"]),
                      "tenant_id": str(r["tenant_id"]) if r["tenant_id"] else None, "kiraci": r["kiraci"],
                      "plant_id": str(r["plant_id"]) if r["plant_id"] else None, "santral": r["santral"],
                      "zaman": _iso(r["started"]), "sure_sn": sure, "tamam": r["status"] == "ok", "durum": r["status"],
                      "ayrinti": r["detail"] or None})
    return {"isler": cikti, "pencere_saat": p["h"], "is_turleri": [{"kod": k, "is": v} for k, v in ISIM_TR.items()]}


def santraller(aktor_id: str, *, sorunlu: bool = False) -> dict:
    """Tüm kiracıların etkin santralleri: son geçerli SCADA, son tahmin koşusu, son iş hatası; sorun bayrakları eşiklerle.
    `sorunlu=True` yalnız en az bir bayrağı olanları döndürür."""
    simdi = dt.datetime.now(dt.timezone.utc)
    with platform_baglami(aktor_id) as s:
        rows = s.execute(text(
            "SELECT p.id, p.name, p.capacity_kwp, p.tz, p.created_at, p.params_json, t.id AS tenant_id, t.name AS kiraci, t.status AS kiraci_durum, "
            "(SELECT max(ts_utc) FROM scada_hourly sh WHERE sh.plant_id = p.id AND sh.flag = 'valid') AS son_scada, "
            "(SELECT max(run_at) FROM forecast_runs r WHERE r.plant_id = p.id) AS son_kosu, "
            "(SELECT max(started) FROM jobs_log j WHERE j.plant_id = p.id AND j.status <> 'ok') AS son_hata "
            "FROM plants p JOIN tenants t ON t.id = p.tenant_id WHERE NOT p.archived ORDER BY t.name, p.name")).mappings().all()
        # v2.515 (yönetim boşlukları #1): yarının (İstanbul) teslim günü için KGÜP arşivi — öneri sürümü, bildirilen, EAK. kgup_surum'u platform
        # bağlamı pvq_api ile okur (v2488: BYPASSRLS + varsayılan ayrıcalıklar; göç gerekmez); dosya baytı değil, yalnız sayaçlar.
        yarin = s.execute(text("SELECT (now() AT TIME ZONE 'Europe/Istanbul')::date + 1")).scalar()
        arsiv = {}
        for a in s.execute(text(
                "SELECT plant_id, kaynak, max(surum) AS surum, max(olusturma) AS son FROM kgup_surum WHERE teslim_gunu = :g GROUP BY plant_id, kaynak"),
                {"g": yarin}).mappings().all():
            arsiv.setdefault(str(a["plant_id"]), {})[a["kaynak"]] = {"surum": int(a["surum"]), "son": _iso(a["son"])}
    from pvquant.services.dengesizlik_service import segment_bilgisi
    cikti = []
    for r in rows:
        sorunlar = []
        sb = segment_bilgisi(r["params_json"])
        if sb["segment"] is None:
            sorunlar.append("segment_yok")   # v2.515: segment seçilmeden KÜPST/DSG hesaplanamaz, KGÜP yükümlülüğü bilinmez
        if r["son_scada"] is None:
            sorunlar.append("scada_yok")
        elif (simdi - r["son_scada"]) > dt.timedelta(hours=SCADA_BAYAT_SAAT):
            sorunlar.append("scada_bayat")
        if r["son_kosu"] is None:
            sorunlar.append("kosu_yok")
        elif (simdi - r["son_kosu"]) > dt.timedelta(hours=KOSU_BAYAT_SAAT):
            sorunlar.append("kosu_bayat")
        if r["kiraci_durum"] != "active":
            sorunlar.append("kiraci_askida")
        if sorunlu and not sorunlar:
            continue
        ar = arsiv.get(str(r["id"]), {})
        cikti.append({"id": str(r["id"]), "ad": r["name"], "kapasite_kwp": float(r["capacity_kwp"] or 0), "tz": r["tz"],
                      "olusturma": _iso(r["created_at"]), "tenant_id": str(r["tenant_id"]), "kiraci": r["kiraci"],
                      "kiraci_durum": r["kiraci_durum"], "son_scada": _iso(r["son_scada"]), "son_kosu": _iso(r["son_kosu"]),
                      "son_hata": _iso(r["son_hata"]), "sorunlar": sorunlar,
                      "segment": sb["segment"], "uevcb": sb.get("uevcb"), "kgup_yukumlu": sb["kgup_yukumlu"],   # v2.515
                      "kgup_yarin": {"gun": yarin.isoformat(), "oneri_surum": (ar.get("pvquant") or {}).get("surum"),
                                     "bildirilen": "musteri" in ar, "eak": "eak" in ar}})
    return {"santraller": cikti, "esik": {"scada_saat": SCADA_BAYAT_SAAT, "kosu_saat": KOSU_BAYAT_SAAT}, "toplam": len(rows), "yarin": yarin.isoformat()}
