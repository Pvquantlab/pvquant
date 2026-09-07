"""v2.289 — Tablo 3.5 satır 6: kuruluşlar arası veri paylaşımı (SFA 'data sharing' kalıbı).

Bir kiracının yöneticisi, bir santralin SEÇİLİ verilerini (tahmin/karne/gerçekleşen özeti) başka bir kiracıya
(toplayıcı, danışman, alıcı kuruluş) zaman sınırlı ve izin kümeli paylaşır; istenirse santral adı takma adla gizlenir
(SFA 'anonymous' kalıbı). Hedef taraf paylaşılan veriyi YALNIZ bu servisin uçlarından okur: paylaşım satırı + süre +
izin denetiminden geçen sorgular sistem bağlamında koşar (RLS kiracı duvarı bilinçli olarak burada aşılır; kapsam bu
dosyadaki üç okuma ile sınırlıdır). Her karar paylasim_denetim'e yazılır (kaynak kiracı görür). İzin kümesi ve rol
sınırı pvquant.ext.platform.paylasim.ROL_IZIN ile aynı dildedir.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

PAYLASILABILIR = ("tahmin:oku", "karne:oku", "gerceklesen:oku")
ETIKET = {"tahmin:oku": "tahmin", "karne:oku": "karne", "gerceklesen:oku": "gerçekleşen özeti"}


def _denetle(s, kaynak_tenant, kullanici, kullanici_tenant, eylem, plant_id, sonuc, not_=""):
    from sqlalchemy import text
    s.execute(text("INSERT INTO paylasim_denetim(tenant_id,kullanici,kullanici_tenant,eylem,plant_id,sonuc,not_) "
                   "VALUES(:t,:k,:kt,:e,:p,:s,:n)"),
              {"t": kaynak_tenant, "k": kullanici, "kt": kullanici_tenant, "e": eylem, "p": plant_id, "s": "izin" if sonuc else "ret", "n": not_[:200]})


def hedef_bul(eposta: str) -> dict | None:
    """Hedef kuruluş: kullanıcı e-postasından (sistem bağlamı — yalnız kimlik eşleme, veri değil)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT u.tenant_id, t.name FROM users u JOIN tenants t ON t.id = u.tenant_id WHERE u.email = :e"),
                      {"e": (eposta or "").strip().lower()}).first()
    return {"tenant_id": str(r.tenant_id), "kurulus": r.name} if r else None


def paylas(tenant_id, kullanici_id, plant: dict, hedef_eposta: str, izinler: list[str], bitis: str | None, takma_ad: str | None) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    iz = sorted(set(izinler or []))
    if not iz or not set(iz) <= set(PAYLASILABILIR):
        raise ValueError(f"izinler: {PAYLASILABILIR}")
    hedef = hedef_bul(hedef_eposta)
    if hedef is None:
        raise ValueError("hedef kuruluş bulunamadı — karşı tarafın bir kullanıcısının e-postasını girin")
    if hedef["tenant_id"] == str(tenant_id):
        raise ValueError("kendi kuruluşunuza paylaşım gerekmez")
    b = None
    if bitis:
        b = pd.Timestamp(bitis, tz="Europe/Istanbul") + pd.Timedelta(days=1)   # bitiş günü dâhil
    with tenant_baglami(tenant_id) as s:
        pid = s.execute(text(
            "INSERT INTO paylasimlar(kaynak_tenant,hedef_tenant,plant_id,izinler,takma_ad,bitis,olusturan) "
            "VALUES(:k,:h,:p,CAST(:i AS jsonb),:ta,:b,:o) RETURNING id"),
            {"k": tenant_id, "h": hedef["tenant_id"], "p": plant["id"], "i": json.dumps(iz),
             "ta": (takma_ad or "").strip()[:60] or None, "b": b.to_pydatetime() if b is not None else None, "o": kullanici_id}).scalar()
        _denetle(s, tenant_id, kullanici_id, tenant_id, "paylas", plant["id"], True, f"→ {hedef['kurulus']} {iz}")
    return {"id": str(pid), "hedef_kurulus": hedef["kurulus"], "izinler": iz}


def iptal(tenant_id, kullanici_id, paylasim_id) -> bool:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text("UPDATE paylasimlar SET iptal=true WHERE id=:i AND kaynak_tenant=:t AND NOT iptal"),
                      {"i": paylasim_id, "t": tenant_id}).rowcount
        if n:
            _denetle(s, tenant_id, kullanici_id, tenant_id, "paylasim_iptal", None, True, str(paylasim_id))
    return n > 0


def listele(tenant_id) -> dict:
    """Verilenler + alınanlar. Sistem bağlamı + açık WHERE: RLS altında plants/tenants JOIN'i hedef tarafta
    satırı düşürür (karşı kiracının santral satırı görünmez — canlı doğrulama dersi); kapsam WHERE ile aynı
    politikaya sabitlenir (kaynak YA DA hedef = kiracı)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT p.id, p.kaynak_tenant, p.hedef_tenant, p.plant_id, p.izinler, p.takma_ad, p.baslangic, p.bitis, p.iptal, "
            " tk.name AS kaynak_kurulus, th.name AS hedef_kurulus, pl.name AS santral, pl.capacity_kwp "
            "FROM paylasimlar p JOIN tenants tk ON tk.id=p.kaynak_tenant JOIN tenants th ON th.id=p.hedef_tenant "
            "JOIN plants pl ON pl.id=p.plant_id WHERE p.kaynak_tenant=:t OR p.hedef_tenant=:t ORDER BY p.created_at DESC"),
            {"t": tenant_id}).mappings().all()
    def satir(r, alinan: bool):
        ad = (r["takma_ad"] or r["santral"]) if alinan else r["santral"]
        return {"id": str(r["id"]), "santral": ad, "takma_ad": r["takma_ad"], "kapasite_kwp": (None if (alinan and r["takma_ad"]) else float(r["capacity_kwp"])),
                "karsi_kurulus": r["kaynak_kurulus"] if alinan else r["hedef_kurulus"], "izinler": list(r["izinler"] or []),
                "bitis": r["bitis"].isoformat() if r["bitis"] else None, "iptal": bool(r["iptal"]),
                "aktif": (not r["iptal"]) and (r["bitis"] is None or pd.Timestamp(r["bitis"]) > pd.Timestamp.now(tz="UTC"))}
    return {"verilenler": [satir(r, False) for r in rows if str(r["kaynak_tenant"]) == str(tenant_id)],
            "alinanlar": [satir(r, True) for r in rows if str(r["hedef_tenant"]) == str(tenant_id)],
            "izin_secenekleri": [{"deger": i, "etiket": ETIKET[i]} for i in PAYLASILABILIR]}


def _gecerli_paylasim(hedef_tenant, paylasim_id, izin: str):
    """Sistem bağlamında paylaşım satırını doğrular; geçersizse PermissionError."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text(
            "SELECT p.*, pl.name AS santral, pl.tz, pl.capacity_kwp FROM paylasimlar p JOIN plants pl ON pl.id=p.plant_id WHERE p.id=:i"),
            {"i": paylasim_id}).mappings().first()
        gecerli = (r is not None and str(r["hedef_tenant"]) == str(hedef_tenant) and not r["iptal"]
                   and (r["bitis"] is None or pd.Timestamp(r["bitis"]) > pd.Timestamp.now(tz="UTC")) and izin in (r["izinler"] or []))
        if r is not None:
            _denetle(s, r["kaynak_tenant"], None, hedef_tenant, izin, r["plant_id"], gecerli, "paylasim")
    if not gecerli:
        raise PermissionError("paylaşım geçersiz, süresi dolmuş ya da izin kapsam dışı")
    return dict(r)


def paylasilan_tahmin(hedef_tenant, paylasim_id) -> dict:
    """Son koşunun günlük P10/P50/P90 toplamları (kayıt sızdırmadan: saatlik değil, günlük; ad takma adla)."""
    from pvquant.services import forecast_service
    from pvquant.services.portfoy_service import gunluk_toplamlar
    r = _gecerli_paylasim(hedef_tenant, paylasim_id, "tahmin:oku")
    df = forecast_service.son_kosu(r["kaynak_tenant"], r["plant_id"])
    ad = r["takma_ad"] or r["santral"]
    if df is None or df.empty:
        return {"santral": ad, "gunler": [], "not": "koşu yok"}
    g = gunluk_toplamlar(df, r["tz"] or "Europe/Istanbul")
    return {"santral": ad, "kapasite_kwp": (None if r["takma_ad"] else float(r["capacity_kwp"])),
            "gunler": [{"gun": k, "p50_kwh": v["p50_kwh"], "p10_kwh": v.get("p10_kwh"), "p90_kwh": v.get("p90_kwh")} for k, v in list(g.items())[:10]]}


def paylasilan_karne(hedef_tenant, paylasim_id) -> dict:
    """Son 30 günün 0–24 s karnesi (WMAPE/nMAE ortalamaları) — santral adı takma adla."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    r = _gecerli_paylasim(hedef_tenant, paylasim_id, "karne:oku")
    with sistem_baglami() as s:
        k = s.execute(text(
            "SELECT count(*) AS gun, avg(mape) AS wmape, avg(nmae) AS nmae, avg(picp80) AS picp FROM skill_daily "
            "WHERE plant_id=:p AND horizon_bucket='0-24' AND date >= current_date - 30"), {"p": r["plant_id"]}).mappings().first()
    return {"santral": r["takma_ad"] or r["santral"], "gun": int(k["gun"] or 0),
            "wmape_pct": round(float(k["wmape"]), 2) if k["wmape"] is not None else None,
            "nmae_pct": round(float(k["nmae"]), 2) if k["nmae"] is not None else None,
            "picp80": round(float(k["picp"]), 3) if k["picp"] is not None else None}


def paylasilan_gerceklesen(hedef_tenant, paylasim_id) -> dict:
    """Son 14 günün günlük gerçekleşen toplamları (kWh) — saatlik ayrıntı paylaşılmaz."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    r = _gecerli_paylasim(hedef_tenant, paylasim_id, "gerceklesen:oku")
    with sistem_baglami() as s:
        g = s.execute(text(
            "SELECT date_trunc('day', ts_utc AT TIME ZONE :tz)::date AS gun, round(sum(power_kw)::numeric, 0) AS kwh FROM scada_hourly "
            "WHERE plant_id=:p AND flag='valid' AND ts_utc >= now() - interval '14 days' GROUP BY 1 ORDER BY 1"),
            {"p": r["plant_id"], "tz": r["tz"] or "Europe/Istanbul"}).mappings().all()
    return {"santral": r["takma_ad"] or r["santral"], "gunler": [{"gun": x["gun"].isoformat(), "kwh": float(x["kwh"])} for x in g]}


def denetim(tenant_id, n: int = 50) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT zaman, eylem, plant_id, sonuc, not_, kullanici_tenant FROM paylasim_denetim ORDER BY zaman DESC LIMIT :n"),
                         {"n": n}).mappings().all()
    return [{"zaman": r["zaman"].isoformat(), "eylem": r["eylem"], "sonuc": r["sonuc"], "not": r["not_"]} for r in rows]
