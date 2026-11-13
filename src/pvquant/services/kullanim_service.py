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
import json as _json

from sqlalchemy import text

from pvquant.db import platform_baglami, sistem_baglami
from pvquant.services import kalite_sozlugu as _ks  # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.services import yetki_service as _ys  # v2.609 (F6-B): kota hükümleri tek yerden

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


def pencere_basi(simdi: dt.datetime, saniye: int = PENCERE_SN) -> dt.datetime:
    """Sabit pencerenin başı: epoch saniyesi `saniye`'ye yuvarlanır (mikrosaniye atılır). Aynı pencere içindeki her an aynı
    başlangıcı verir — v2.486'da mikrosaniye iki kez çıkarılıyordu, her istek kendi satırına düşüyor ve sınır hiç dolmuyordu
    (canlıda 25.10 yakalandı; yerel test mikrosaniyesiz zamanla maskelemişti)."""
    epoch = int(simdi.timestamp())
    return dt.datetime.fromtimestamp(epoch - epoch % saniye, tz=dt.timezone.utc)


def pencere_temizle(saat: int = 1) -> int:
    """26.10 denetim-3: pencere_say yalnız aynı anahtarın eski satırlarını siler; bir kez görülen her IP/anahtar süresiz kalıyordu.
    Worker günlük temizlikte `saat` saatten eski tüm pencereleri siler; silinen satır sayısını döner."""
    with sistem_baglami() as s:
        return int(s.execute(text("DELETE FROM hiz_pencere WHERE pencere < now() - make_interval(hours => :h)"), {"h": int(saat)}).rowcount)


def pencere_say(anahtar: str, saniye: int = PENCERE_SN, simdi: dt.datetime | None = None) -> int:
    """Sabit pencerede paylaşımlı artış; pencere içindeki yeni toplamı döner. Eski pencereler silinir.
    DB'ye ulaşılamazsa 0 döner (kapı açık kalır: sayaç kesintisi müşteriyi kilitlemesin; olay günlükte)."""
    bas = pencere_basi(simdi or dt.datetime.now(dt.timezone.utc), saniye)
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
    """Kiracı → {dis_api, webhook, webhook_hata, rapor, kosu, scada_saat, yukleme, kgup, kgup_bildirilen} — [ilk, son) aralığı.
    v2.516 (#6): kgup = PVQuant önerisinin yeni sürümü (kgup_surum kaynak=pvquant; aynı içerik yeni sürüm açmaz), kgup_bildirilen = müşterinin
    yüklediği beyan dosyası (kaynak=musteri); ikisi de oluşturma gününe göre."""
    sayac = s.execute(text(
        "SELECT tenant_id, tur, sum(adet) AS n FROM kullanim_sayac WHERE gun >= :a AND gun < :b GROUP BY tenant_id, tur"),
        {"a": ilk, "b": son}).mappings().all()
    rapor = s.execute(text("SELECT tenant_id, count(*) AS n FROM report_log WHERE created_at >= :a AND created_at < :b GROUP BY tenant_id"),
                      {"a": ilk, "b": son}).mappings().all()
    kosu = s.execute(text("SELECT tenant_id, count(*) AS n FROM forecast_runs WHERE run_at >= :a AND run_at < :b GROUP BY tenant_id"),
                     {"a": ilk, "b": son}).mappings().all()
    scada = s.execute(text(f"SELECT tenant_id, count(*) AS n FROM scada_hourly WHERE ts_utc >= :a AND ts_utc < :b AND {_ks.sql_kosulu('tazelik')} GROUP BY tenant_id"),
                      {"a": ilk, "b": son}).mappings().all()
    yukleme = s.execute(text("SELECT tenant_id, count(*) AS n FROM ingestion_batches WHERE created_at >= :a AND created_at < :b GROUP BY tenant_id"),
                        {"a": ilk, "b": son}).mappings().all()
    kgup = s.execute(text("SELECT tenant_id, kaynak, count(*) AS n FROM kgup_surum WHERE olusturma >= :a AND olusturma < :b "
                          "AND kaynak IN ('pvquant', 'musteri') GROUP BY tenant_id, kaynak"), {"a": ilk, "b": son}).mappings().all()
    bos = lambda: {"dis_api": 0, "webhook": 0, "webhook_hata": 0, "rapor": 0, "kosu": 0, "scada_saat": 0, "yukleme": 0, "kgup": 0, "kgup_bildirilen": 0}  # noqa: E731
    out: dict[str, dict] = {}
    for r in sayac:
        if r["tur"] in TURLER:
            out.setdefault(str(r["tenant_id"]), bos())[r["tur"]] = int(r["n"])
    for ad, rows in (("rapor", rapor), ("kosu", kosu), ("scada_saat", scada), ("yukleme", yukleme)):
        for r in rows:
            out.setdefault(str(r["tenant_id"]), bos())[ad] = int(r["n"])
    for r in kgup:
        out.setdefault(str(r["tenant_id"]), bos())["kgup" if r["kaynak"] == "pvquant" else "kgup_bildirilen"] = int(r["n"])
    return out


def ozet(aktor_id: str, ay: str | None = None) -> dict:
    """Tüm kiracılar için seçili ay ve önceki ay; etkin anahtar/webhook sayısı ve son API kullanımı."""
    ilk, son, etiket = _ay_sinirlari(ay)
    o_ilk, _, o_etiket = _ay_sinirlari(_onceki_ay(ilk))
    with platform_baglami(aktor_id) as s:
        kiracilar = s.execute(text(
            "SELECT t.id, t.name, t.plan, t.status, t.created_at, "
            "(SELECT count(*) FROM api_keys k WHERE k.tenant_id = t.id AND NOT k.revoked AND (k.expires_at IS NULL OR k.expires_at > now())) AS anahtar, "
            "(SELECT count(*) FROM webhooks w WHERE w.tenant_id = t.id AND w.active) AS webhook, "
            "(SELECT max(k.last_used_at) FROM api_keys k WHERE k.tenant_id = t.id) AS son_api "
            "FROM tenants t ORDER BY t.name")).mappings().all()
        bu = _ay_toplamlari(s, ilk, son)
        onceki = _ay_toplamlari(s, o_ilk, ilk)
        anlik = _anlik_sayimlar(s)
        abonelik = {str(r["tenant_id"]): dict(r) for r in s.execute(text(
            "SELECT tenant_id, plan, durum, bitis, pilot_bitis, kota_ezme FROM kiraci_abonelik")).mappings().all()}
        planlar = {r["ad"]: dict(r) for r in s.execute(text("SELECT ad, " + ", ".join(_ys.KOTALAR[k]["sutun"] for k in _ys.KOTALAR) + " FROM planlar")).mappings().all()}
    bos = {"dis_api": 0, "webhook": 0, "webhook_hata": 0, "rapor": 0, "kosu": 0, "scada_saat": 0, "yukleme": 0, "kgup": 0, "kgup_bildirilen": 0}
    bugun = dt.datetime.now(dt.timezone.utc).date()
    out = []
    for k in kiracilar:
        tid = str(k["id"]); bu_ay = bu.get(tid, dict(bos))
        plan_ad = (abonelik[tid]["plan"] if tid in abonelik else k["plan"]) or "pilot"
        a = abonelik.get(tid) or _ys.varsayilan_kayit(plan_ad, k["created_at"], bugun)   # inceleme: kayıtsız kiracı yetki_service ile aynı türetme
        durum = _ys.durum_turet(plan_ad, k["status"], a, bugun)
        out.append({"id": tid, "ad": k["name"], "plan": plan_ad, "durum": k["status"],
                    "abonelik_durum": durum, "abonelik_etiketi": _ys.DURUM_ETIKET[durum],
                    "etkin_anahtar": int(k["anahtar"]), "etkin_webhook": int(k["webhook"]),
                    "son_api_kullanim": k["son_api"].isoformat() if k["son_api"] else None,
                    "bu_ay": bu_ay, "onceki_ay": onceki.get(tid, dict(bos)),
                    "anlik": anlik.get(tid, {"santral": 0, "ac_mw": 0.0, "ac_eksik_santral": 0, "kullanici": 0, "portfoy": 0}),
                    "kotalar": _kotalar(planlar.get(plan_ad), a, anlik.get(tid), bu_ay)})
    return {"ay": etiket, "onceki_ay": o_etiket, "turler": list(TURLER), "kota_alanlari": list(KOTA_KAYNAK), "kota_sozlugu": _ys.KOTA_DURUM_ETIKET,
            "kiracilar": out}


# v2.609 (Faz 6 F6-B): kota alanı → bu fonksiyonun sayımındaki kaynak (anlık ya da bu ay). api_rpm anahtar başına: ölçülmez.
KOTA_KAYNAK = {"santral": ("anlik", "santral"), "kullanici": ("anlik", "kullanici"), "portfoy": ("anlik", "portfoy"), "ac_mw": ("anlik", "ac_mw"),
               "aylik_dis_api": ("bu_ay", "dis_api"), "aylik_rapor": ("bu_ay", "rapor"), "aylik_isleme_saat": ("bu_ay", "scada_saat")}


def _anlik_sayimlar(s) -> dict[str, dict]:
    """Kiracı → {santral, ac_mw, ac_eksik_santral, kullanici, portfoy}; tek küme sorgusu (tüm kiracılar); tanım yetki_service.ANLIK_ALT_SORGU."""
    rows = s.execute(text(f"SELECT t.id, {_ys.ANLIK_ALT_SORGU.format(T='t.id')} FROM tenants t")).mappings().all()   # inceleme: tek tanım (yetki_service)
    return {str(r["id"]): _ys.anlik_sozluk(r) for r in rows}


def _kotalar(plan: dict | None, abonelik: dict | None, anlik: dict | None, bu_ay: dict) -> dict:
    """Plan limiti (yoksa sınırsız) + kiracı kota ezmesi → yetki_service.kota_durumu; kullanım kaynağı KOTA_KAYNAK."""
    ezme = (abonelik or {}).get("kota_ezme") or {}
    if isinstance(ezme, str):
        ezme = _json.loads(ezme)
    out = {}
    for alan, (kaynak, anahtar) in KOTA_KAYNAK.items():
        kullanim = (anlik or {}).get(anahtar) if kaynak == "anlik" else bu_ay.get(anahtar)
        limit = plan.get(_ys.KOTALAR[alan]["sutun"]) if plan else None
        d = _ys.kota_durumu(limit, kullanim, ezme=ezme.get(alan))
        out[alan] = {**d, "ad": _ys.KOTALAR[alan]["ad"], "birim": _ys.KOTALAR[alan]["birim"]}
    if anlik and anlik.get("ac_eksik_santral"):
        out["ac_mw"]["not_"] = f"{anlik['ac_eksik_santral']} santralde AC sınırı girilmemiş; DC gücü sayıldı (yaklaşık)"
    return out


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
                               f"WHERE tenant_id = CAST(:t AS uuid) AND ts_utc >= :a AND ts_utc < :b AND {_ks.sql_kosulu('tazelik')} GROUP BY 1"), p).mappings().all()
        yukleme = s.execute(text("SELECT CAST(created_at AT TIME ZONE 'UTC' AS date) AS gun, count(*) AS n FROM ingestion_batches "
                                 "WHERE tenant_id = CAST(:t AS uuid) AND created_at >= :a AND created_at < :b GROUP BY 1"), p).mappings().all()
        kgup = s.execute(text("SELECT CAST(olusturma AT TIME ZONE 'UTC' AS date) AS gun, kaynak, count(*) AS n FROM kgup_surum "
                              "WHERE tenant_id = CAST(:t AS uuid) AND olusturma >= :a AND olusturma < :b AND kaynak IN ('pvquant', 'musteri') GROUP BY 1, 2"), p).mappings().all()
    g: dict[dt.date, dict] = {}
    bos = lambda: {"dis_api": 0, "webhook": 0, "webhook_hata": 0, "rapor": 0, "kosu": 0, "scada_saat": 0, "yukleme": 0, "kgup": 0, "kgup_bildirilen": 0}  # noqa: E731
    for r in sayac:
        if r["tur"] in TURLER:
            g.setdefault(r["gun"], bos())[r["tur"]] = int(r["adet"])
    for alan, rows in (("rapor", rapor), ("kosu", kosu), ("scada_saat", scada), ("yukleme", yukleme)):
        for r in rows:
            g.setdefault(r["gun"], bos())[alan] = int(r["n"])
    for r in kgup:
        g.setdefault(r["gun"], bos())["kgup" if r["kaynak"] == "pvquant" else "kgup_bildirilen"] = int(r["n"])
    return {"ay": etiket, "tenant_id": str(tenant_id), "ad": ad,
            "gunler": [{"gun": d.isoformat(), **g[d]} for d in sorted(g, reverse=True)]}
