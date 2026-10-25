"""24.10 Faz 1 — platform kimliği ve kiracı yönetimi UÇTAN UCA (DB'li; CI'da ve yerel timescale ile koşar).
İlk sahip → giriş → jeton kapsamı → 2FA kurulumu → kiracı oluşturma (posta kapalı: davet bağlantısı döner) → davetle parola
belirleme → müşteri girişi → askıya alma → müşteri girişi 403 (KiraciAskida) ve açık jetonların düşmesi → denetim izi."""
import os
import uuid
import jwt as _jwt
import pyotp
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import platform_service as ps, auth_service as au, denetim_service as dz


@pytest.fixture
def temiz(monkeypatch):
    monkeypatch.delenv("PVQ_SMTP_HOST", raising=False)       # posta kapalı → bağlantı yanıtta
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    etiket = uuid.uuid4().hex[:8]
    yield etiket
    ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM denetim_izi WHERE aktor_eposta LIKE :e OR ayrinti::text LIKE :e"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM parola_sifirlama WHERE user_id IN (SELECT id FROM users WHERE email LIKE :e)"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM users WHERE email LIKE :e"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM tenants WHERE name LIKE :e"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM platform_kullanicilar WHERE email LIKE :e"), {"e": f"%{etiket}%"})


def test_uctan_uca(temiz):
    e = temiz
    sahip_eposta = f"sahip-{e}@pvq.test"
    pid = ps.ilk_sahip_olustur(sahip_eposta, "cok-gizli-parola-123")
    # giriş + jeton kapsamı
    assert ps.giris(sahip_eposta, "yanlis") is None
    g = ps.giris(sahip_eposta, "cok-gizli-parola-123")
    assert g["iki_adim_kurulmali"] is True and g["rol"] == "sahip"
    c = _jwt.decode(g["token"], au._sir(), algorithms=["HS256"])
    assert c["kapsam"] == "platform" and c["sub"] == pid and c["sv"] == 0
    # 2FA kur → artık kodsuz giriş olmaz
    k = ps.iki_adim_baslat(pid)
    ps.iki_adim_dogrula(pid, pyotp.TOTP(k["secret"]).now())
    assert ps.giris(sahip_eposta, "cok-gizli-parola-123") == {"iki_adim_gerekli": True}
    assert ps.giris(sahip_eposta, "cok-gizli-parola-123", pyotp.TOTP(k["secret"]).now())["iki_adim_kurulmali"] is False
    # kiracı oluştur (posta kapalı → bağlantı döner), listede görünür
    firma = f"Firma {e}"; admin_eposta = f"admin-{e}@musteri.test"
    y = ps.kiraci_olustur(pid, firma, admin_eposta)
    assert y["davet_gonderildi"] is False and "davet_baglantisi" in y
    assert any(x["id"] == y["tenant_id"] and x["kullanici"] == 1 for x in ps.kiraci_listesi(pid))
    d = ps.kiraci_detay(pid, y["tenant_id"])
    assert d["kullanicilar"][0]["email"] == admin_eposta and d["kullanicilar"][0]["rol"] == "admin"
    with pytest.raises(ValueError):
        ps.kiraci_olustur(pid, firma, f"baska-{e}@musteri.test")     # aynı ad
    # davet bağlantısıyla parola belirle → müşteri girişi çalışır
    jeton = y["davet_baglantisi"].split("jeton=")[1]
    au.parola_sifirla(jeton, "musteri-parola-123")
    mg = au.giris(admin_eposta, "musteri-parola-123")
    assert mg and mg["role"] == "admin" and mg["tenant_id"] == y["tenant_id"]
    sv0 = _jwt.decode(mg["token"], au._sir(), algorithms=["HS256"])["sv"]
    # askıya al → müşteri girişi 403 mantığı (KiraciAskida), açık jetonlar düşer (sv arttı), gecerli_kullanici 403
    ps.kiraci_guncelle(pid, y["tenant_id"], status="suspended", notlar="ödeme bekleniyor")
    with pytest.raises(au.KiraciAskida):
        au.giris(admin_eposta, "musteri-parola-123")
    durum = au.oturum_durumu(y["user_id"])
    assert durum["kiraci_durum"] == "suspended" and durum["sv"] == sv0 + 1
    # yeniden aç → giriş çalışır
    ps.kiraci_guncelle(pid, y["tenant_id"], status="active")
    assert au.giris(admin_eposta, "musteri-parola-123")["role"] == "admin"
    # kullanıcı arama + destek bağlantısı
    assert any(u["email"] == admin_eposta for u in ps.kullanici_ara(pid, e))
    dv = ps.davet_gonder(pid, y["user_id"], saat=24)
    assert dv["gonderildi"] is False and "baglanti" in dv
    # denetim izi: yaz/oku, kiracıya göre süz
    assert dz.kaydet("platform", "kiraci_guncelle", aktor_id=pid, aktor_eposta=sahip_eposta, tenant_id=y["tenant_id"],
                     nesne_tur="tenant", nesne_id=y["tenant_id"], ayrinti={"etiket": e})
    kayitlar = dz.listele(tenant_id=y["tenant_id"])
    assert kayitlar and kayitlar[0]["eylem"] == "kiraci_guncelle" and kayitlar[0]["ayrinti"]["etiket"] == e
    assert kayitlar[0]["kiraci_ad"] == firma                      # 25.10 denetim O1: kiracı adı birleşik
    # 25.10 O6: görüntüleme izi günde tek satır; eylem_haric süzgeci dışlar
    assert dz.goruntule_kaydet(pid, sahip_eposta, y["tenant_id"]) is True
    assert dz.goruntule_kaydet(pid, sahip_eposta, y["tenant_id"]) is False
    goruntule = [k for k in dz.listele(tenant_id=y["tenant_id"]) if k["eylem"] == "kiraci_goruntule"]
    assert len(goruntule) == 1 and goruntule[0]["aktor_eposta"] == sahip_eposta
    assert all(k["eylem"] != "kiraci_goruntule" for k in dz.listele(tenant_id=y["tenant_id"], eylem_haric="kiraci_goruntule"))
    # operatör yönetimi: son sahip düşürülemez
    op = ps.operator_ekle(f"op-{e}@pvq.test", "operator")
    assert ps.operator_guncelle(op["id"], aktif=False)
    sahipler = [o for o in ps.operator_listesi() if o["rol"] == "sahip" and o["aktif"]]
    if len(sahipler) == 1:
        with pytest.raises(ValueError):
            ps.operator_guncelle(pid, aktif=False)


def test_faz3_sistem_izleme(temiz):
    """25.10 Faz 3 — nabız yaz/oku, özet alanları, kiracılar arası iş kayıtları (ayrıntıyla) ve santral envanteri (DB'li)."""
    from pvquant.services import sistem_service as ss
    e = temiz
    pid = ps.ilk_sahip_olustur(f"sahip3-{e}@pvq.test", "cok-gizli-parola-123")
    ss.nabiz_yaz("worker", {"etiket": e, "is_sayisi": 21})
    ss.nabiz_yaz("worker", {"etiket": e, "is_sayisi": 22})                       # ikinci yazım UPSERT: tek satır kalır
    with sistem_baglami() as s:
        assert s.execute(text("SELECT count(*) FROM sistem_nabiz WHERE bilesen='worker'")).scalar() == 1
    o = ss.ozet(pid)
    assert o["nabiz"]["durum"] == "calisiyor" and o["nabiz"]["ayrinti"]["is_sayisi"] == 22 and o["nabiz"]["yas_dk"] == 0
    assert set(o) >= {"gece_turu", "isler_24", "meteo", "piyasa", "yedek", "db", "santral"}
    assert isinstance(o["gece_turu"]["taze"], bool) and len(o["gece_turu"]["uretici_isler"]) == 3 and o["db"]["boyut_bayt"] > 0
    # kiracı + santral + hatalı iş kaydı → platform iş listesinde kiracı/santral adı ve AYRINTI görünür
    y = ps.kiraci_olustur(pid, f"Firma3 {e}", f"admin3-{e}@musteri.test")
    with sistem_baglami() as s:
        plant_id = s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, lat, lon, tz) "
                                  "VALUES (CAST(:t AS uuid), :n, 1000, 37.0, 32.5, 'Europe/Istanbul') RETURNING id"),
                             {"t": y["tenant_id"], "n": f"GES {e}"}).scalar()
        s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status, detail) "
                       "VALUES ('sabah_tahmin', CAST(:t AS uuid), :p, now() - interval '1 hour', now() - interval '59 minutes', 'error', :d)"),
                  {"t": y["tenant_id"], "p": plant_id, "d": f"KeyError: {e}"})
    try:
        kayitlar = ss.isler(pid, saat=24, yalniz_hata=True, tenant_id=y["tenant_id"])["isler"]
        assert len(kayitlar) == 1 and kayitlar[0]["ayrinti"] == f"KeyError: {e}" and kayitlar[0]["santral"] == f"GES {e}"
        assert kayitlar[0]["kiraci"] == f"Firma3 {e}" and kayitlar[0]["tamam"] is False and kayitlar[0]["is"] == "Sabah tahmini"
        assert ss.isler(pid, saat=24, job="gece_skill", tenant_id=y["tenant_id"])["isler"] == []
        env = ss.santraller(pid, sorunlu=True)["santraller"]
        bizim = [x for x in env if x["id"] == str(plant_id)][0]
        assert {"scada_yok", "kosu_yok"} <= set(bizim["sorunlar"]) and bizim["kiraci"] == f"Firma3 {e}" and bizim["son_hata"]
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM jobs_log WHERE plant_id = :p"), {"p": plant_id})
            s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": plant_id})


def test_faz4_kullanim(temiz):
    """25.10 Faz 4 — günlük sayaç UPSERT, paylaşımlı pencere (iki «süreç» aynı satırı sayar), ay özeti ve günlük kırılımda
    türetilmiş sayımlar (report_log, forecast_runs) + sayaç türleri (DB'li)."""
    import datetime as dt
    from pvquant.services import kullanim_service as ks
    e = temiz
    pid = ps.ilk_sahip_olustur(f"sahip4-{e}@pvq.test", "cok-gizli-parola-123")
    y = ps.kiraci_olustur(pid, f"Firma4 {e}", f"admin4-{e}@musteri.test")
    tid = y["tenant_id"]
    with sistem_baglami() as s:
        plant_id = s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, lat, lon, tz) "
                                  "VALUES (CAST(:t AS uuid), :n, 500, 38.0, 33.0, 'Europe/Istanbul') RETURNING id"), {"t": tid, "n": f"GES4 {e}"}).scalar()
        s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, mode, model) VALUES (CAST(:t AS uuid), :p, 'A', 'test')"), {"t": tid, "p": plant_id})
        s.execute(text("INSERT INTO report_log(tenant_id, plant_id, mode) VALUES (CAST(:t AS uuid), :p, 'html')"), {"t": tid, "p": plant_id})
    try:
        ks.say(tid, "dis_api"); ks.say(tid, "dis_api", 2); ks.say(tid, "webhook"); ks.say(tid, "webhook_hata")
        # paylaşımlı pencere: aynı anahtar + aynı pencere → ardışık sayım; eski pencere silinir
        t0 = dt.datetime(2026, 10, 25, 12, 0, 10, 345678, tzinfo=dt.timezone.utc)   # mikrosaniyeli: v2.486 hizalama hatası burada yakalanır
        t1 = t0 + dt.timedelta(seconds=7, microseconds=111)
        assert [ks.pencere_say(f"anahtar:{e}", simdi=t0), ks.pencere_say(f"anahtar:{e}", simdi=t1)] == [1, 2]
        assert ks.pencere_say(f"anahtar:{e}", simdi=t0 + dt.timedelta(seconds=60)) == 1
        assert ks.pencere_say(f"anahtar:{e}") == 1 and ks.pencere_say(f"anahtar:{e}") == 2       # gerçek saat, mikrosaniyeli
        with sistem_baglami() as s:
            assert s.execute(text("SELECT count(*) FROM hiz_pencere WHERE anahtar = :a"), {"a": f"anahtar:{e}"}).scalar() == 1
        bu_ay = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
        o = ks.ozet(pid, bu_ay)
        k = [x for x in o["kiracilar"] if x["id"] == tid][0]
        assert o["ay"] == bu_ay and k["bu_ay"] == {"dis_api": 3, "webhook": 1, "webhook_hata": 1, "rapor": 1, "kosu": 1, "scada_saat": 0, "yukleme": 0}
        assert k["onceki_ay"]["dis_api"] == 0 and k["etkin_anahtar"] == 0
        g = ks.gunler(pid, tid, bu_ay)
        bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
        assert g["ad"] == f"Firma4 {e}" and g["gunler"][0]["gun"] == bugun and g["gunler"][0]["dis_api"] == 3 and g["gunler"][0]["kosu"] == 1
        assert ks.gunler(pid, "00000000-0000-0000-0000-000000000000")["gunler"] == []
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM kullanim_sayac WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
            s.execute(text("DELETE FROM hiz_pencere WHERE anahtar = :a"), {"a": f"anahtar:{e}"})
            s.execute(text("DELETE FROM report_log WHERE plant_id = :p"), {"p": plant_id})
            s.execute(text("DELETE FROM forecast_runs WHERE plant_id = :p"), {"p": plant_id})
            s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": plant_id})


def test_d4_parola_sifirla_ve_d6_temizlik(temiz, monkeypatch):
    """26.10 D4: CLI parola yenileme (oturumlar düşer, 2FA aynı); D6: saklama yalnız hacimli eylemleri ve yalnız N aydan eskisini siler."""
    import datetime as dt
    e = temiz
    eposta = f"sahip6-{e}@pvq.test"
    pid = ps.ilk_sahip_olustur(eposta, "cok-gizli-parola-123")
    sv0 = ps.oturum_durumu(pid)["sv"]
    with pytest.raises(ValueError):
        ps.parola_sifirla_cli(eposta, "kisa")
    assert ps.parola_sifirla_cli(eposta, "yeni-gizli-parola-456") == pid
    assert ps.giris(eposta, "cok-gizli-parola-123") is None and ps.giris(eposta, "yeni-gizli-parola-456")["rol"] == "sahip"
    assert ps.oturum_durumu(pid)["sv"] == sv0 + 1
    with pytest.raises(ValueError):
        ps.parola_sifirla_cli(f"yok-{e}@pvq.test", "yeni-gizli-parola-456")
    # D6: eski giriş + eski kiracı_guncelle + yeni giriş; temizle(1) yalnız eski girişi siler; ayar 0 dokunmaz
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO denetim_izi(zaman, kapsam, eylem, aktor_eposta) VALUES (now() - interval '40 days', 'platform', 'giris', :e), "
                       "(now() - interval '40 days', 'platform', 'kiraci_guncelle', :e), (now(), 'platform', 'giris', :e)"), {"e": eposta})
    monkeypatch.setattr("pvquant.config.get_settings", lambda: type("S", (), {"denetim_saklama_ay": 0})())
    assert dz.temizle() == 0
    assert dz.temizle(1) == 1
    with sistem_baglami() as s:
        kalan = s.execute(text("SELECT eylem FROM denetim_izi WHERE aktor_eposta = :e ORDER BY eylem"), {"e": eposta}).scalars().all()
    assert kalan == ["giris", "kiraci_guncelle"]
