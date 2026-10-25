"""25.10 Faz 4 — KULLANIM SAYAÇLARI ve PAYLAŞIMLI HIZ PENCERESİ (platform).

Yazım: `say(tenant, tur)` günlük UPSERT, asla yükseltmez (sayaç, asıl işi düşürmez). Yalnız mevcut tablolarda izi olmayan
türler yazılır: dis_api (anahtarla başarılı istek), webhook / webhook_hata (teslim denemesi). Rapor (report_log), koşu
(forecast_runs), SCADA saati (scada_hourly, veri ayı, flag='valid') ve yükleme (ingestion_batches) sayıları SORGUYLA türetilir:
tahmin, rapor ve SCADA işleme koduna kanca yoktur.

Hız: `pencere_say(anahtar, saniye)` sabit pencerede paylaşımlı sayaç — 4 uvicorn işçisi aynı satırı artırır; süreç içi token
bucket işçi başına saydığından anahtar başına rpm fiilen 4× idi. Eski pencereler aynı çağrıda silinir (cron gerekmez).
Okumalar `platform_baglami(aktör)` ile (RLS dışı, adlı)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import text

from pvquant.db import sistem_baglami, platform_baglami

TURLER = ("dis_api", "webhook", "webhook_hata")
PENCERE_SN = 60


def say(tenant_id, tur: str, adet: int = 1) -> None:
    """Günlük sayaç artışı (UTC günü). Hata yutulur ve günlüğe düşer."""
    try:
        with sistem_baglami() as s:
            s.execute(text(
                "INSERT INTO kullanim_sayac(tenant_id, gun, tur, adet) VALUES (CAST(:t AS uuid), CURRENT_DATE, :k, :n) "
                "ON CONFLICT (tenant_id, gun, tur) DO UPDATE SET adet = kullanim_sayac.adet + EXCLUDED.adet, guncelleme = now()"),
                {"t": str(tenant_id), "k": tur, "n": int(adet)})
    except Exception as e:  # noqa: BLE001
        print(f"[kullanim] sayaç yazılamadı ({tur}): {type(e).__name__}: {e}")


def pencere_say(anahtar: str, saniye: int = PENCERE_SN, simdi: dt.datetime | None = None) -> int:
    """Sabit pencerede paylaşımlı artış; pencere içindeki yeni toplamı döner. Eski pencereler silinir.
    DB'ye ulaşılamazsa 0 döner (kapı açık kalır: sayaç kesintisi müşteriyi kilitlemesin; olay günlükte)."""
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    bas = simdi - dt.timedelta(seconds=simdi.timestamp() % saniye, microseconds=simdi.microsecond)
    try:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM hiz_pencere WHERE anahtar = :a AND pencere < :p"), {"a": anahtar, "p": bas})
            return int(s.execute(text(
                "INSERT INTO hiz_pencere(anahtar, pencere, adet) VALUES (:a, :p, 1) "
                "ON CONFLICT (anahtar, pencere) DO UPDATE SET adet = hiz_pencere.adet + 1 RETURNING adet"),
                {"a": anahtar, "p": bas}).scalar())
    except Exception as e:  # noqa: BLE001
        print(f"[hiz] pencere sayılamadı: {type(e).__name__}: {e}")
        return 0


# ---------------- okuma (platform) ----------------
def _ay_sinirlari(ay: str | None) -> tuple[dt.date, dt.date, str]:
    """'YYYY-MM' → (ilk gün, sonraki ayın ilk günü, 'YYYY-MM'); boşsa bu ay (UTC)."""
    if ay:
        y, m = (int(x) for x in ay.split("-")[:2])
    else:
        bugun = dt.datetime.now(dt.timezone.utc).date(); y, m = bugun.year, bugun.month
    ilk = dt.date(y, m, 1)
    son = dt.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
    return ilk, son, f"{y:04d}-{m:02d}"


def _onceki_ay(ilk: dt.date) -> str:
    o = ilk - dt.timedelta(days=1)
    return f"{o.year:04d}-{o.month:02d}"


def _ay_toplamlari(s, ilk: dt.date, son: dt.date) -> dict[str, dict]:
    """Kiracı → {dis_api, webhook, webhook_hata, rapor, kosu, scada_saat, yukleme} — [ilk, son) aralığı."""
    sayac = s.execute(text(
        "SELECT tenant_id, tur, sum(adet) AS n FROM kullanim_sayac WHERE gun >= :a AND gun < :b GROUP BY tenant_id, tur"),
        {"a": ilk, "b": son}).mappings().all()
    rapor = s.execute(text("SELECT tenant_id, count(*) AS n FROM report_log WHERE created_at >= :a AND created_at < :b GROUP BY tenant_id"),
                      {"a": ilk, "b": son}).mappings().all()
    kosu = s.execute(text("SELECT tenant_id, count(*) AS n FROM forecast_runs WHERE run_at >= :a AND run_at < :b GROUP BY tenant_id"),
                     {"a": ilk, "b": son}).mappings().all()
    scada = s.execute(text("SELECT tenant_id, count(*) AS n FROM scada_hourly WHERE ts_utc >= :a AND ts_utc < :b AND flag = 'valid' GROUP BY tenant_id"),
                      {"a": ilk, "b": son}).mappings().all()
    yukleme = s.execute(text("SELECT tenant_id, count(*) AS n FROM ingestion_batches WHERE created_at >= :a AND created_at < :b GROUP BY tenant_id"),
                        {"a": ilk, "b": son}).mappings().all()
    bos = lambda: {"dis_api": 0, "webhook": 0, "webhook_hata": 0, "rapor": 0, "kosu": 0, "scada_saat": 0, "yukleme": 0}  # noqa: E731
    out: dict[str, dict] = {}
    for r in sayac:
        if r["tur"] in TURLER:
            out.setdefault(str(r["tenant_id"]), bos())[r["tur"]] = int(r["n"])
    for ad, rows in (("rapor", rapor), ("kosu", kosu), ("scada_saat", scada), ("yukleme", yukleme)):
        for r in rows:
            out.setdefault(str(r["tenant_id"]), bos())[ad] = int(r["n"])
    return out


def ozet(aktor_id: str, ay: str | None = None) -> dict:
    """Tüm kiracılar için seçili ay ve önceki ay; etkin anahtar/webhook sayısı ve son API kullanımı."""
    ilk, son, etiket = _ay_sinirlari(ay)
    o_ilk, _, o_etiket = _ay_sinirlari(_onceki_ay(ilk))
    with platform_baglami(aktor_id) as s:
        kiracilar = s.execute(text(
            "SELECT t.id, t.name, t.plan, t.status, "
            "(SELECT count(*) FROM api_keys k WHERE k.tenant_id = t.id AND NOT k.revoked AND (k.expires_at IS NULL OR k.expires_at > now())) AS anahtar, "
            "(SELECT count(*) FROM webhooks w WHERE w.tenant_id = t.id AND w.active) AS webhook, "
            "(SELECT max(k.last_used_at) FROM api_keys k WHERE k.tenant_id = t.id) AS son_api "
            "FROM tenants t ORDER BY t.name")).mappings().all()
        bu = _ay_toplamlari(s, ilk, son)
        onceki = _ay_toplamlari(s, o_ilk, ilk)
    bos = {"dis_api": 0, "webhook": 0, "webhook_hata": 0, "rapor": 0, "kosu": 0, "scada_saat": 0, "yukleme": 0}
    return {"ay": etiket, "onceki_ay": o_etiket, "turler": list(TURLER),
            "kiracilar": [{"id": str(k["id"]), "ad": k["name"], "plan": k["plan"], "durum": k["status"],
                           "etkin_anahtar": int(k["anahtar"]), "etkin_webhook": int(k["webhook"]),
                           "son_api_kullanim": k["son_api"].isoformat() if k["son_api"] else None,
                           "bu_ay": bu.get(str(k["id"]), dict(bos)), "onceki_ay": onceki.get(str(k["id"]), dict(bos))}
                          for k in kiracilar]}


def gunler(aktor_id: str, tenant_id: str, ay: str | None = None) -> dict:
    """Tek kiracı için günlük kırılım (seçili ay): sayaç türleri + türetilmiş sayımlar gün gün."""
    ilk, son, etiket = _ay_sinirlari(ay)
    p = {"t": str(tenant_id), "a": ilk, "b": son}
    with platform_baglami(aktor_id) as s:
        ad = s.execute(text("SELECT name FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": str(tenant_id)}).scalar()
        if ad is None:
            return {"ay": etiket, "tenant_id": str(tenant_id), "ad": None, "gunler": []}
        sayac = s.execute(text("SELECT gun, tur, adet FROM kullanim_sayac WHERE tenant_id = CAST(:t AS uuid) AND gun >= :a AND gun < :b"), p).mappings().all()
        rapor = s.execute(text("SELECT CAST(created_at AT TIME ZONE 'UTC' AS date) AS gun, count(*) AS n FROM report_log "
                               "WHERE tenant_id = CAST(:t AS uuid) AND created_at >= :a AND created_at < :b GROUP BY 1"), p).mappings().all()
        kosu = s.execute(text("SELECT CAST(run_at AT TIME ZONE 'UTC' AS date) AS gun, count(*) AS n FROM forecast_runs "
                              "WHERE tenant_id = CAST(:t AS uuid) AND run_at >= :a AND run_at < :b GROUP BY 1"), p).mappings().all()
        scada = s.execute(text("SELECT CAST(ts_utc AT TIME ZONE 'UTC' AS date) AS gun, count(*) AS n FROM scada_hourly "
                               "WHERE tenant_id = CAST(:t AS uuid) AND ts_utc >= :a AND ts_utc < :b AND flag = 'valid' GROUP BY 1"), p).mappings().all()
        yukleme = s.execute(text("SELECT CAST(created_at AT TIME ZONE 'UTC' AS date) AS gun, count(*) AS n FROM ingestion_batches "
                                 "WHERE tenant_id = CAST(:t AS uuid) AND created_at >= :a AND created_at < :b GROUP BY 1"), p).mappings().all()
    g: dict[dt.date, dict] = {}
    bos = lambda: {"dis_api": 0, "webhook": 0, "webhook_hata": 0, "rapor": 0, "kosu": 0, "scada_saat": 0, "yukleme": 0}  # noqa: E731
    for r in sayac:
        if r["tur"] in TURLER:
            g.setdefault(r["gun"], bos())[r["tur"]] = int(r["adet"])
    for alan, rows in (("rapor", rapor), ("kosu", kosu), ("scada_saat", scada), ("yukleme", yukleme)):
        for r in rows:
            g.setdefault(r["gun"], bos())[alan] = int(r["n"])
    return {"ay": etiket, "tenant_id": str(tenant_id), "ad": ad,
            "gunler": [{"gun": d.isoformat(), **g[d]} for d in sorted(g, reverse=True)]}
