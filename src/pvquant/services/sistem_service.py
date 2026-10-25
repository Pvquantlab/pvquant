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
                   "yas_saat": piyasa_yas, "esik_saat": PIYASA_BAYAT_SAAT, "bayat": bayat_mi(piyasa_yas, PIYASA_BAYAT_SAAT)},
        "yedek": {"son_basarili": _iso(yedek_ok), "yas_saat": yedek_yas, "esik_saat": YEDEK_BAYAT_SAAT, "bayat": bayat_mi(yedek_yas, YEDEK_BAYAT_SAAT),
                  "son_deneme": None if yedek_son is None else {"zaman": _iso(yedek_son["started"]), "tamam": yedek_son["status"] == "ok",
                                                                "ayrinti": yedek_son["detail"] or None}},
        "db": {"boyut_bayt": int(db_boyut or 0)},
        "santral": {"etkin": int(santral["etkin"]), "arsivli": int(santral["arsivli"])},
    }


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
            "SELECT p.id, p.name, p.capacity_kwp, p.tz, p.created_at, t.id AS tenant_id, t.name AS kiraci, t.status AS kiraci_durum, "
            "(SELECT max(ts_utc) FROM scada_hourly sh WHERE sh.plant_id = p.id AND sh.flag = 'valid') AS son_scada, "
            "(SELECT max(run_at) FROM forecast_runs r WHERE r.plant_id = p.id) AS son_kosu, "
            "(SELECT max(started) FROM jobs_log j WHERE j.plant_id = p.id AND j.status <> 'ok') AS son_hata "
            "FROM plants p JOIN tenants t ON t.id = p.tenant_id WHERE NOT p.archived ORDER BY t.name, p.name")).mappings().all()
    cikti = []
    for r in rows:
        sorunlar = []
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
        cikti.append({"id": str(r["id"]), "ad": r["name"], "kapasite_kwp": float(r["capacity_kwp"] or 0), "tz": r["tz"],
                      "olusturma": _iso(r["created_at"]), "tenant_id": str(r["tenant_id"]), "kiraci": r["kiraci"],
                      "kiraci_durum": r["kiraci_durum"], "son_scada": _iso(r["son_scada"]), "son_kosu": _iso(r["son_kosu"]),
                      "son_hata": _iso(r["son_hata"]), "sorunlar": sorunlar})
    return {"santraller": cikti, "esik": {"scada_saat": SCADA_BAYAT_SAAT, "kosu_saat": KOSU_BAYAT_SAAT}, "toplam": len(rows)}
