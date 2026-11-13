"""v2.609 (Faz 6 F6-A) — abonelik YAZICI: kiracı oluşturulunca varsayılan satır, `tenants.plan/status` değişince eşzamanlama, yalnız-ekleme
geçmiş. Yaşam döngüsü eylemleri (plan değiştir, tarih, modül ek/çıkar, kota ezme) F6-C'de bu modüle eklenir. Çağıran platform bağlamı
(pvq_api BYPASSRLS) ya da bakım bağlamıdır; her yazım `abonelik_gecmisi` + çağıranın `denetim_izi` kaydıyla izlenir."""
from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import text

from pvquant.services import yetki_service


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def gecmis_yaz(s, tenant_id, aktor: str | None, eylem: str, eski: dict | None, yeni: dict | None, gerekce: str | None = None) -> None:
    s.execute(text("INSERT INTO abonelik_gecmisi(tenant_id, aktor, eylem, eski, yeni, gerekce) "
                   "VALUES (CAST(:t AS uuid), :a, :e, CAST(:es AS jsonb), CAST(:ye AS jsonb), :g)"),
              {"t": str(tenant_id), "a": aktor, "e": eylem, "es": _json(eski) if eski is not None else None, "ye": _json(yeni) if yeni is not None else None, "g": gerekce})


def varsayilan_olustur(s, tenant_id, plan: str, *, aktor: str | None = None, bugun: dt.date | None = None) -> dict:
    """Yeni kiracı: plan pilot → durum pilot + pilot_bitis = bugün + 60 gün; diğer → aktif, bitişsiz (sözleşme tarihi F6-C'de girilir)."""
    bugun = bugun or dt.datetime.now(dt.timezone.utc).date()
    durum = "pilot" if plan == "pilot" else "aktif"
    pb = (bugun + dt.timedelta(days=yetki_service.PILOT_GUN)) if plan == "pilot" else None
    r = s.execute(text("INSERT INTO kiraci_abonelik(tenant_id, plan, durum, baslangic, pilot_bitis, guncelleyen) VALUES (CAST(:t AS uuid), :p, :d, :b, :pb, :a) "
                       "ON CONFLICT (tenant_id) DO NOTHING"), {"t": str(tenant_id), "p": plan, "d": durum, "b": bugun, "pb": pb, "a": aktor})
    yeni = {"plan": plan, "durum": durum, "baslangic": bugun, "pilot_bitis": pb}
    if r.rowcount:   # zaten varsa (idempotent) geçmişe ikinci «oluşturma» yazılmaz
        gecmis_yaz(s, tenant_id, aktor, "olusturma", None, yeni, "kiracı oluşturuldu; varsayılan abonelik")
    yetki_service.onbellek_dusur(tenant_id)
    return yeni


def senkron(s, tenant_id, *, plan: str | None = None, status: str | None = None, aktor: str | None = None) -> dict | None:
    """`kiraci_guncelle` sonrası çift yazım: plan değişti → abonelik planı; status suspended → askida, active → tarihlerden yeniden türetilir.
    Satır yoksa (göç öncesi kiracı) oluşturur."""
    r = s.execute(text("SELECT plan, durum, bitis, pilot_bitis FROM kiraci_abonelik WHERE tenant_id = CAST(:t AS uuid)"), {"t": str(tenant_id)}).mappings().first()
    if r is None:
        return varsayilan_olustur(s, tenant_id, plan or "pilot", aktor=aktor)
    eski = dict(r)
    yeni_plan = plan or r["plan"]
    bugun = dt.datetime.now(dt.timezone.utc).date()
    if status == "suspended":
        yeni_durum = "askida"
    elif status == "active" or plan is not None:
        yeni_durum = yetki_service.durum_turet(yeni_plan, "active", {**eski, "durum": None if r["durum"] == "askida" else r["durum"]}, bugun)
    else:
        yeni_durum = r["durum"]
    pb = r["pilot_bitis"]
    if plan is not None and plan != r["plan"]:
        pb = (bugun + dt.timedelta(days=yetki_service.PILOT_GUN)) if plan == "pilot" else None   # plana dönüşte pilot süresi yeniden başlar
        yeni_durum = yetki_service.durum_turet(yeni_plan, status or "active", {**eski, "durum": None, "pilot_bitis": pb}, bugun) if status != "suspended" else "askida"
    if yeni_plan == r["plan"] and yeni_durum == r["durum"] and pb == r["pilot_bitis"]:
        return None
    s.execute(text("UPDATE kiraci_abonelik SET plan = :p, durum = :d, pilot_bitis = :pb, guncelleme = now(), guncelleyen = :a WHERE tenant_id = CAST(:t AS uuid)"),
              {"p": yeni_plan, "d": yeni_durum, "pb": pb, "a": aktor, "t": str(tenant_id)})
    yeni = {"plan": yeni_plan, "durum": yeni_durum, "pilot_bitis": pb}
    gecmis_yaz(s, tenant_id, aktor, "senkron", {"plan": eski["plan"], "durum": eski["durum"], "pilot_bitis": eski["pilot_bitis"]}, yeni, "tenants.plan/status değişikliği")
    yetki_service.onbellek_dusur(tenant_id)
    return yeni


def gecmis(s, tenant_id, n: int = 50) -> list[dict]:
    rows = s.execute(text("SELECT id, zaman, aktor, eylem, eski, yeni, gerekce FROM abonelik_gecmisi WHERE tenant_id = CAST(:t AS uuid) ORDER BY zaman DESC, id DESC LIMIT :n"),
                     {"t": str(tenant_id), "n": int(n)}).mappings().all()
    return [{"id": int(r["id"]), "zaman": r["zaman"].isoformat(), "aktor": r["aktor"], "eylem": r["eylem"], "eski": r["eski"], "yeni": r["yeni"], "gerekce": r["gerekce"]} for r in rows]


# ----------------------------------------------------------------------------------------------------------- v2.609 (F6-C) yaşam döngüsü
class AbonelikHata(ValueError):
    pass


YOK = object()   # «alan gönderilmedi» (None = temizle)
# Elle hedeflenebilen durumlar: eski (türetilmiş) → izinli hedefler. «aktif» = askıdan çıkarma / yenileme; tarihlerden yeniden türetilir.
# Otomatik durumlar (sona_eriyor, yenileme_bekliyor, sona_erdi) elle hedeflenmez: tarihlerle gelir. feshedildi terminal (yalnız sahip).
GECISLER: dict[str, set[str]] = {
    "pilot": {"aktif", "askida", "feshedildi"},
    "aktif": {"aktif", "askida", "feshedildi"},   # aktif→aktif = yenileme (bitiş ileri) ya da idempotent açma
    "sona_eriyor": {"aktif", "askida", "feshedildi"},
    "yenileme_bekliyor": {"aktif", "askida", "feshedildi"},
    "askida": {"aktif", "feshedildi"},
    "sona_erdi": {"aktif", "askida", "feshedildi"},
    "feshedildi": set(),
}


def gecis_izinli(eski: str, yeni: str) -> bool:
    return yeni in GECISLER.get(eski, set())


def _tarih(v, ad: str):
    if v is None or isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v))
    except ValueError:
        raise AbonelikHata(f"{ad}: tarih YYYY-AA-GG olmalı") from None


def guncelle(s, tenant_id, aktor: str | None, *, plan=YOK, bitis=YOK, pilot_bitis=YOK, modul_ek=YOK, modul_cikar=YOK, kota_ezme=YOK,
             sozlesme_notu=YOK, teklif_ref=YOK, durum: str | None = None, gerekce: str | None = None, sahip: bool = False,
             bugun: dt.date | None = None) -> dict:
    """Platform eylemi (tek çağrıda bir ya da birkaç alan). Gerekçe ZORUNLU (sözleşme istisnası ve durum değişikliği izlenir). Plan değişince
    `tenants.plan` da yazılır (çift yazım); askıya alma `tenants.status=suspended` + kiracı oturumları düşer; «aktif» status=active ve tarihlerden
    yeniden türetme; «feshedildi» yalnız sahip, terminal, status=suspended. Döner: {eski, yeni, degisen}."""
    from pvquant.services import auth_service
    if not (gerekce or "").strip():
        raise AbonelikHata("gerekçe zorunlu")
    bugun = bugun or dt.datetime.now(dt.timezone.utc).date()
    t = s.execute(text("SELECT plan, status, created_at FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": str(tenant_id)}).mappings().first()
    if t is None:
        raise LookupError("kiracı yok")
    r = s.execute(text("SELECT plan, durum, baslangic, bitis, pilot_bitis, modul_ek, modul_cikar, kota_ezme, sozlesme_notu, teklif_ref "
                       "FROM kiraci_abonelik WHERE tenant_id = CAST(:t AS uuid)"), {"t": str(tenant_id)}).mappings().first()
    if r is None:
        varsayilan_olustur(s, tenant_id, t["plan"] or "pilot", aktor=aktor, bugun=bugun)
        r = s.execute(text("SELECT plan, durum, baslangic, bitis, pilot_bitis, modul_ek, modul_cikar, kota_ezme, sozlesme_notu, teklif_ref "
                           "FROM kiraci_abonelik WHERE tenant_id = CAST(:t AS uuid)"), {"t": str(tenant_id)}).mappings().first()
    eski = dict(r); yeni = dict(r)
    if isinstance(yeni.get("kota_ezme"), str):
        yeni["kota_ezme"] = json.loads(yeni["kota_ezme"])
    eski_durum = yetki_service.durum_turet(eski["plan"], t["status"], eski, bugun)
    if eski_durum == "feshedildi" and any(v is not YOK for v in (plan, bitis, pilot_bitis, modul_ek, modul_cikar, kota_ezme)):
        raise AbonelikHata("feshedilmiş abonelikte plan, tarih, modül ya da kota değiştirilemez (terminal); yalnız not ve teklif referansı")   # inceleme
    # --- alanlar
    if plan is not YOK:
        if plan is None or s.execute(text("SELECT 1 FROM planlar WHERE ad = :p"), {"p": plan}).first() is None:
            raise AbonelikHata("plan tanımsız")
        if plan != eski["plan"]:
            yeni["plan"] = plan
            yeni["pilot_bitis"] = (bugun + dt.timedelta(days=yetki_service.PILOT_GUN)) if plan == "pilot" else None
    if bitis is not YOK:
        yeni["bitis"] = _tarih(bitis, "bitiş")
    if pilot_bitis is not YOK:
        yeni["pilot_bitis"] = _tarih(pilot_bitis, "pilot bitişi")
    if yeni.get("bitis") is not None and yeni["bitis"] < yeni["baslangic"]:
        raise AbonelikHata("bitiş başlangıçtan önce olamaz")
    for ad, deger in (("modul_ek", modul_ek), ("modul_cikar", modul_cikar)):
        if deger is not YOK:
            kodlar = sorted(set(deger or []))
            for k in kodlar:
                if k not in yetki_service.MODULLER:
                    raise AbonelikHata(f"bilinmeyen modül: {k}")
            yeni[ad] = kodlar
    if set(yeni.get("modul_ek") or []) & set(yeni.get("modul_cikar") or []):
        raise AbonelikHata("bir modül hem ek hem çıkar olamaz")
    if kota_ezme is not YOK:
        ez = {}
        for k, v in (kota_ezme or {}).items():
            if k not in yetki_service.KOTALAR:
                raise AbonelikHata(f"bilinmeyen kota alanı: {k}")
            if v is not None:
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    raise AbonelikHata(f"{k}: sayı olmalı") from None
                if v < 0:
                    raise AbonelikHata(f"{k}: negatif olamaz")
            ez[k] = v
        yeni["kota_ezme"] = {k: v for k, v in ez.items()}
    if sozlesme_notu is not YOK:
        yeni["sozlesme_notu"] = (sozlesme_notu or None)
    if teklif_ref is not YOK:
        yeni["teklif_ref"] = (teklif_ref or None)
    # --- durum
    yeni_status = t["status"]
    if durum is not None:
        if durum not in ("aktif", "askida", "feshedildi"):
            raise AbonelikHata("durum elle yalnız aktif | askida | feshedildi olabilir; diğerleri tarihlerden türer")
        if not gecis_izinli(eski_durum, durum):
            raise AbonelikHata(f"{eski_durum} → {durum} geçişi izinli değil")
        if durum == "feshedildi" and not sahip:
            raise AbonelikHata("fesih yalnız platform sahibi")
        yeni_status = "active" if durum == "aktif" else "suspended"
    if durum == "feshedildi" or eski["durum"] == "feshedildi":
        yeni["durum"] = "feshedildi"                                   # terminal: status ne olursa olsun
    elif durum == "askida" or yeni_status == "suspended":
        yeni["durum"] = "askida"
    else:
        plan_degisti = plan is not YOK and yeni["plan"] != eski["plan"]
        tarih_geldi = bitis is not YOK or pilot_bitis is not YOK
        if durum == "aktif" or plan_degisti or tarih_geldi:
            taban = None if (durum == "aktif" or plan_degisti or tarih_geldi or eski["durum"] == "askida") else eski["durum"]   # inceleme: tarih uzatınca yapışkan sona_erdi de sıfırlanır
            yeni["durum"] = yetki_service.durum_turet(yeni["plan"], "active", {**yeni, "durum": taban}, bugun)
        else:
            yeni["durum"] = eski["durum"]
        if durum == "aktif" and yeni["durum"] == "sona_erdi":
            raise AbonelikHata("etkinleştirmek için önce pilot bitişini ileri alın ya da planı değiştirin (pilot süresi geçmiş)")
    def _norm(k, v):   # inceleme: dizi sırası ve JSON metni «değişti» sayılmasın
        if k in ("modul_ek", "modul_cikar"):
            return sorted(v or [])
        if k == "kota_ezme":
            return json.loads(v) if isinstance(v, str) else dict(v or {})
        return v
    degisen = {k: {"eski": eski.get(k), "yeni": yeni.get(k)} for k in ("plan", "durum", "bitis", "pilot_bitis", "modul_ek", "modul_cikar", "kota_ezme", "sozlesme_notu", "teklif_ref")
               if _norm(k, eski.get(k)) != _norm(k, yeni.get(k))}
    if yeni_status != t["status"]:
        degisen["status"] = {"eski": t["status"], "yeni": yeni_status}
    if not degisen:
        return {"eski": eski, "yeni": yeni, "degisen": {}}
    s.execute(text("UPDATE kiraci_abonelik SET plan = :p, durum = :d, bitis = :b, pilot_bitis = :pb, modul_ek = :me, modul_cikar = :mc, kota_ezme = CAST(:ke AS jsonb), "
                   "sozlesme_notu = :sn, teklif_ref = :tr, guncelleme = now(), guncelleyen = :a WHERE tenant_id = CAST(:t AS uuid)"),
              {"p": yeni["plan"], "d": yeni["durum"], "b": yeni.get("bitis"), "pb": yeni.get("pilot_bitis"), "me": list(yeni.get("modul_ek") or []),
               "mc": list(yeni.get("modul_cikar") or []), "ke": _json(yeni.get("kota_ezme") or {}), "sn": yeni.get("sozlesme_notu"), "tr": yeni.get("teklif_ref"),
               "a": aktor, "t": str(tenant_id)})
    s.execute(text("UPDATE tenants SET plan = :p, status = :s, updated_at = now() WHERE id = CAST(:t AS uuid)"), {"p": yeni["plan"], "s": yeni_status, "t": str(tenant_id)})
    if yeni_status != t["status"]:
        s.execute(text("UPDATE users SET oturum_surumu = oturum_surumu + 1 WHERE tenant_id = CAST(:t AS uuid)"), {"t": str(tenant_id)})   # askı/fesih/açma: oturumlar düşer
        auth_service.oturum_onbellegi_dusur()
    gecmis_yaz(s, tenant_id, aktor, "guncelle", {k: v["eski"] for k, v in degisen.items()}, {k: v["yeni"] for k, v in degisen.items()}, gerekce)
    yetki_service.onbellek_dusur(tenant_id)
    return {"eski": eski, "yeni": yeni, "degisen": degisen}


def gece_turet(s, bugun: dt.date | None = None, aktor: str = "gece_abonelik") -> dict:
    """Gece işi: tarihlerden türeyen durumlar (sona_eriyor / yenileme_bekliyor / sona_erdi) kayda yazılır; yapışkan (feshedildi, askida ↔ status)
    dokunulmaz. Uyarı kipinde yalnız durum sözcüğü değişir; kısıt yok. Döner: sayımlar + değişen kiracı listesi."""
    bugun = bugun or dt.datetime.now(dt.timezone.utc).date()
    rows = s.execute(text("SELECT a.tenant_id, a.plan, a.durum, a.baslangic, a.bitis, a.pilot_bitis, t.status FROM kiraci_abonelik a JOIN tenants t ON t.id = a.tenant_id")).mappings().all()
    degisen = []; sayim: dict[str, int] = {}
    for r in rows:
        yeni = yetki_service.durum_turet(r["plan"], r["status"], dict(r), bugun)
        sayim[yeni] = sayim.get(yeni, 0) + 1
        if yeni != r["durum"]:
            s.execute(text("UPDATE kiraci_abonelik SET durum = :d, guncelleme = now(), guncelleyen = :a WHERE tenant_id = CAST(:t AS uuid)"),
                      {"d": yeni, "a": aktor, "t": str(r["tenant_id"])})
            gecmis_yaz(s, r["tenant_id"], aktor, "turetme", {"durum": r["durum"]}, {"durum": yeni}, "gece türetme: tarihlere göre")
            degisen.append({"tenant_id": str(r["tenant_id"]), "eski": r["durum"], "yeni": yeni})
            yetki_service.onbellek_dusur(r["tenant_id"])
    return {"durum": "ok", "kiraci": len(rows), "degisen": len(degisen), "sayim": sayim, "degisenler": degisen[:50]}
