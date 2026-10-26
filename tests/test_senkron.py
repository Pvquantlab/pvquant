"""26.10 — İKİ PANEL EŞZAMANLAMA PAKETİ (DB'li; CI ve yerel timescale ile koşar).

Doğrulananlar: (1) sözlük — worker'ın zamanladığı her iş adının ortak etiketi (isler_service.ISIM_TR) var; müşteri /v1/isler ve platform
/v1/yonetim/isler AYNI etiketi, zamanı ve durumu verir; (2) tazelik hükmü — platform sistem özeti ile müşteri gece işleri özeti aynı eşiği ve
aynı «eski işler» listesini üretir; (3) kiracı izolasyonu — müşteri yalnız kendi (ve küresel) iş kayıtlarını görür, başka kiracının santral
damgasını okuyamaz; (4) damga — yeni iş kaydı, piyasa fiyatı, SCADA ölçümü ve santral parametresi değişince ETag değişir; değişmeyince sabit kalır."""
import os
import re
import uuid
import datetime as dt
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import isler_service, sistem_service, damga_service, platform_service as ps, auth_service as au

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_sozluk_worker_isleri_etiketli():
    """Worker'ın zamanladığı her iş (apps/worker/main.py add_job) ISIM_TR'de etiketli — iki panel de bu etiketi gösterir."""
    kaynak = open(os.path.join(KOK, "apps", "worker", "main.py"), encoding="utf-8").read()
    isler = set(re.findall(r'_logla(?:_tek)?\("([a-z_0-9]+)"', kaynak))
    assert isler, "worker iş adı bulunamadı"
    eksik = sorted(isler - set(isler_service.ISIM_TR))
    assert not eksik, f"ISIM_TR'de etiketi olmayan işler: {eksik}"
    assert sistem_service.BAYAT_SAAT == 30 == isler_service.bayat_isler.__defaults__[0]   # tazelik eşiği iki panelde aynı


@pytest.fixture
def temiz(monkeypatch):
    monkeypatch.delenv("PVQ_SMTP_HOST", raising=False)
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    e = uuid.uuid4().hex[:8]
    yield e
    ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM jobs_log WHERE detail LIKE :e"), {"e": f"%{e}%"})
        s.execute(text("DELETE FROM piyasa_fiyat WHERE kaynak = :e"), {"e": f"senkron-{e}"})
        for t in ("scada_hourly", "alerts", "plants"):
            s.execute(text(f"DELETE FROM {t} WHERE plant_id IN (SELECT id FROM plants WHERE name LIKE :e)" if t != "plants" else "DELETE FROM plants WHERE name LIKE :e"), {"e": f"%{e}%"})
        s.execute(text("DELETE FROM denetim_izi WHERE aktor_eposta LIKE :e OR ayrinti::text LIKE :e"), {"e": f"%{e}%"})
        s.execute(text("DELETE FROM parola_sifirlama WHERE user_id IN (SELECT id FROM users WHERE email LIKE :e)"), {"e": f"%{e}%"})
        s.execute(text("DELETE FROM users WHERE email LIKE :e"), {"e": f"%{e}%"})
        s.execute(text("DELETE FROM tenants WHERE name LIKE :e"), {"e": f"%{e}%"})
        s.execute(text("DELETE FROM platform_kullanicilar WHERE email LIKE :e"), {"e": f"%{e}%"})


def _kur(e):
    pid = ps.ilk_sahip_olustur(f"sahip-{e}@pvq.test", "cok-gizli-parola-123")
    a = ps.kiraci_olustur(pid, f"SenkA {e}", f"a-{e}@m.test", rol="sahip")
    b = ps.kiraci_olustur(pid, f"SenkB {e}", f"b-{e}@m.test", rol="sahip")
    with sistem_baglami() as s:
        pa = s.execute(text("INSERT INTO plants(tenant_id, name, lat, lon, tz, capacity_kwp) VALUES (CAST(:t AS uuid), :n, 38.0, 35.0, 'Europe/Istanbul', 1000) RETURNING id"),
                       {"t": a["tenant_id"], "n": f"SantralA {e}"}).scalar()
        pb = s.execute(text("INSERT INTO plants(tenant_id, name, lat, lon, tz, capacity_kwp) VALUES (CAST(:t AS uuid), :n, 39.0, 36.0, 'Europe/Istanbul', 1000) RETURNING id"),
                       {"t": b["tenant_id"], "n": f"SantralB {e}"}).scalar()
        simdi = dt.datetime.now(dt.timezone.utc)
        s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status, detail) VALUES "
                       "('sabah_tahmin', CAST(:ta AS uuid), :pa, :s1, :s1 + interval '2 seconds', 'ok', :e), "
                       "('gun_ici_tahmin', CAST(:tb AS uuid), :pb, :s2, :s2 + interval '3 seconds', 'error', :e), "
                       "('gece_piyasa', NULL, NULL, :s3, :s3 + interval '1 second', 'ok', :e)"),
                  {"ta": a["tenant_id"], "tb": b["tenant_id"], "pa": pa, "pb": pb, "e": f"senkron {e}",
                   "s1": simdi - dt.timedelta(minutes=30), "s2": simdi - dt.timedelta(minutes=20), "s3": simdi - dt.timedelta(minutes=10)})
    return pid, a, b, str(pa), str(pb)


def test_is_kayitlari_iki_panelde_ayni_ve_izole(temiz):
    e = temiz; pid, a, b, pa, pb = _kur(e)
    musteri_a = isler_service.ozet(a["tenant_id"], saat=48)["isler"]
    musteri_b = isler_service.ozet(b["tenant_id"], saat=48)["isler"]
    platform = sistem_service.isler(pid, saat=48, limit=500)["isler"]
    etiket = isler_service.ISIM_TR
    # izolasyon: A kendi + küresel işi görür, B'nin başarısız işini GÖRMEZ
    a_adlar = [x["is"] for x in musteri_a if f"senkron" in str(x) or x["is"] in (etiket["sabah_tahmin"], etiket["gece_piyasa"], etiket["gun_ici_tahmin"])]
    assert etiket["sabah_tahmin"] in a_adlar and etiket["gece_piyasa"] in a_adlar
    assert all(not (x["is"] == etiket["gun_ici_tahmin"] and not x["tamam"]) for x in musteri_a)
    assert any(x["is"] == etiket["gun_ici_tahmin"] and not x["tamam"] for x in musteri_b)
    # platform aynı kayıtları aynı etiket/zaman/durumla, hata ayrıntısıyla görür (müşteride ayrıntı yok)
    pl = {(x["is"], x["zaman"][:19], x["tamam"]) for x in platform if x["ayrinti"] and f"senkron {e}" in x["ayrinti"]}
    mu = {(x["is"], x["zaman"][:19], x["tamam"]) for x in musteri_a + musteri_b if x["is"] in (etiket["sabah_tahmin"], etiket["gun_ici_tahmin"], etiket["gece_piyasa"])}
    assert pl and pl <= mu, (pl, mu)
    assert all("ayrinti" not in x for x in musteri_a)
    # tazelik hükmü: platform özeti ile müşteri gece işleri özeti aynı «eski» listesini verir (etiketli)
    platform_eski = sistem_service.ozet(pid)["gece_turu"]["bayat_isler"]
    musteri_eski = isler_service.ozet(a["tenant_id"])["bayat_isler"]
    assert set(platform_eski) == {etiket[i] for i in isler_service.bayat_isler(30)} and set(musteri_eski) == {etiket[i] for i in isler_service.bayat_isler(30, a["tenant_id"])}


def test_damga_degisim_kaynaklari_ve_izolasyon(temiz):
    e = temiz; pid, a, b, pa, pb = _kur(e)
    d0 = damga_service.hesapla(a["tenant_id"], pa); et0 = damga_service.etag_uret(d0)
    assert damga_service.etag_uret(damga_service.hesapla(a["tenant_id"], pa)) == et0           # değişiklik yok → sabit
    assert {"son_piyasa", "son_is", "son_meteo", "santral_ozu"} <= set(d0) and d0["santral_ozu"]
    # 1) yeni iş kaydı (kiracının)
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status, detail) VALUES ('sabah_tahmin', CAST(:t AS uuid), :p, now(), now(), 'ok', :e)"),
                  {"t": a["tenant_id"], "p": pa, "e": f"senkron {e}"})
    et1 = damga_service.etag_uret(damga_service.hesapla(a["tenant_id"], pa)); assert et1 != et0
    # 2) piyasa fiyatı güncellemesi (küresel) — her iki kiracının damgası değişir
    etb0 = damga_service.etag_uret(damga_service.hesapla(b["tenant_id"], pb))
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO piyasa_fiyat(ts_utc, ptf, smf, yon, kaynak, guncelleme) VALUES (now() + interval '400 days', 1, 1, 'x', :e, now()) "
                       "ON CONFLICT (ts_utc) DO UPDATE SET guncelleme = now(), kaynak = EXCLUDED.kaynak"), {"e": f"senkron-{e}"})
    et2 = damga_service.etag_uret(damga_service.hesapla(a["tenant_id"], pa)); assert et2 != et1
    assert damga_service.etag_uret(damga_service.hesapla(b["tenant_id"], pb)) != etb0
    # 3) santral parametresi (Santral ayarları) değişince
    with sistem_baglami() as s:
        s.execute(text("UPDATE plants SET params_json = COALESCE(params_json, '{}'::jsonb) || '{\"senkron\": 1}'::jsonb WHERE id = :p"), {"p": pa})
    et3 = damga_service.etag_uret(damga_service.hesapla(a["tenant_id"], pa)); assert et3 != et2
    # 4) SCADA ölçümü
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag) VALUES (CAST(:t AS uuid), :p, now(), 1.0, 'valid')"), {"t": a["tenant_id"], "p": pa})
    et4 = damga_service.etag_uret(damga_service.hesapla(a["tenant_id"], pa)); assert et4 != et3
    # izolasyon: B kiracısı A'nın santral özünü/damgasını okuyamaz — santral_ozu None, SCADA/koşu boş
    db = damga_service.hesapla(b["tenant_id"], pa)
    assert db["santral_ozu"] is None and db["son_scada"] is None
