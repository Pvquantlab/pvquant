"""24.10 Faz 1 — platform kimliği ve kiracı yönetimi UÇTAN UCA (DB'li; CI'da ve yerel timescale ile koşar).
İlk sahip → giriş → jeton kapsamı → 2FA kurulumu → kiracı oluşturma (posta kapalı: davet bağlantısı döner) → davetle parola
belirleme → müşteri girişi → askıya alma → müşteri girişi 403 (KiraciAskida) ve açık jetonların düşmesi → denetim izi."""
import datetime as dt
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
    # 26.10 denetim-3: hassas işlem yeniden doğrulaması — parola + kod; yalnız parola / yanlış kod / yanlış parola geçmez
    assert ps.yeniden_dogrula(pid, "cok-gizli-parola-123", pyotp.TOTP(k["secret"]).now()) is True
    assert ps.yeniden_dogrula(pid, "cok-gizli-parola-123", None) is False
    assert ps.yeniden_dogrula(pid, "cok-gizli-parola-123", "000000") is False
    assert ps.yeniden_dogrula(pid, "yanlis", pyotp.TOTP(k["secret"]).now()) is False
    assert ps.yeniden_dogrula(str(uuid.uuid4()), "x", "000000") is False
    # kiracı oluştur (posta kapalı → bağlantı döner), listede görünür
    firma = f"Firma {e}"; admin_eposta = f"admin-{e}@musteri.test"
    y = ps.kiraci_olustur(pid, firma, admin_eposta, rol="sahip")                  # uç aktörün rolünü geçirir
    assert y["davet_gonderildi"] is False and "davet_baglantisi" in y
    yo = ps.kiraci_olustur(pid, f"Operatorlu {e}", f"op-{e}@musteri.test", rol="operator")
    assert yo["davet_gonderildi"] is False and "davet_baglantisi" not in yo and "sahip" in yo["not"]   # 26.10 denetim-3: operatöre bağlantı yok
    assert any(x["id"] == y["tenant_id"] and x["kullanici"] == 1 for x in ps.kiraci_listesi(pid))
    d = ps.kiraci_detay(pid, y["tenant_id"])
    assert d["kullanicilar"][0]["email"] == admin_eposta and d["kullanicilar"][0]["rol"] == "admin"
    with pytest.raises(ValueError):
        ps.kiraci_olustur(pid, firma, f"baska-{e}@musteri.test")     # aynı ad
    y2 = ps.kiraci_olustur(pid, f"Ikinci {e}", f"ikinci-{e}@musteri.test")
    with pytest.raises(ValueError):
        ps.kiraci_guncelle(pid, y2["tenant_id"], ad=firma.upper())  # 26.10 denetim-3: güncellemede de ad benzersiz (büyük/küçük bağımsız)
    with pytest.raises(ValueError):
        ps.kiraci_guncelle(pid, y2["tenant_id"], ad=" " + firma)        # baştaki boşlukla da atlanmaz (kırpılır)
    with pytest.raises(ValueError):
        ps.kiraci_guncelle(pid, y2["tenant_id"], ad="")                 # boş ad reddedilir
    assert ps.kiraci_guncelle(pid, y2["tenant_id"], ad=f"Ikinci {e}")["yeni"]["name"] == f"Ikinci {e}"   # kendi adı serbest
    assert ps.giris(f"yok-{e}@pvq.test", "x") is None and au.giris(f"yok-{e}@musteri.test", "x") is None   # kukla hash yolu hatasız
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
    with sistem_baglami() as s_:
        once = s_.execute(text("SELECT token_hash FROM parola_sifirlama WHERE user_id=:u AND used_at IS NULL"), {"u": y["user_id"]}).scalars().all()
    assert "baglanti" not in ps.davet_gonder(pid, y["user_id"], saat=24, rol="operator")   # 26.10 denetim-3: operatöre bağlantı yok
    with sistem_baglami() as s_:
        sonra = s_.execute(text("SELECT token_hash FROM parola_sifirlama WHERE user_id=:u AND used_at IS NULL"), {"u": y["user_id"]}).scalars().all()
    assert sonra == once                                                 # posta yokken operatör jeton ÜRETMEZ, bekleyeni bozmaz
    dv = ps.davet_gonder(pid, y["user_id"], saat=24, rol="sahip")
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
    # v2.516 (#3/#4): izlenen işler listesi ve durum sözlüğü; piyasa kartında kimlik ve yön kapsamı alanları
    iz = o["izlenen"]
    assert len(iz["isler"]) == len(ss.IZLENEN_ISLER) and {x["durum"] for x in iz["isler"]} <= {"ok", "esik_asimi", "henuz_yok", "beklenmiyor"}
    assert all(x["is"] != x["kod"] for x in iz["isler"]) and set(iz["bayat"]) <= {x["is"] for x in iz["isler"]}
    assert set(o["piyasa"]) >= {"kimlik", "yon_son", "yon_saat_7g", "saat_7g", "yon_bayat", "gop_son"} and isinstance(o["piyasa"]["yon_bayat"], bool)
    assert ss._izlenen({"kgup_arsiv_temizlik": None}, dt.datetime.now(dt.timezone.utc), 0)["isler"][-2]["durum"] == "henuz_yok"   # aylık, hiç koşmadı → uyarı değil
    assert "etkin santral yok" in (ss._izlenen({}, dt.datetime.now(dt.timezone.utc), 0)["isler"][1]["not"] or "")                  # santral başına iş, santral yok
    # kiracı + santral + hatalı iş kaydı → platform iş listesinde kiracı/santral adı ve AYRINTI görünür
    y = ps.kiraci_olustur(pid, f"Firma3 {e}", f"admin3-{e}@musteri.test", rol="sahip")
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
        # v2.516 (#5): açık alarm özeti — okunmamış ve 7 günden yeni; kural etiketi Türkçe
        with sistem_baglami() as s2:
            s2.execute(text("INSERT INTO alerts(tenant_id, plant_id, rule, message, severity) VALUES (CAST(:t AS uuid), :p, 'kgup_teslim_gecikti', :m, 'warning')"),
                       {"t": y["tenant_id"], "p": plant_id, "m": f"test {e}"})
        al = ss.alarmlar(pid)
        kural = [k for k in al["kurallar"] if k["kural"] == "kgup_teslim_gecikti"][0]
        assert al["acik"] >= 1 and al["pencere_gun"] == 7 and kural["adet"] >= 1 and kural["etiket"] == "Program bildirimi hazırlanamadı"
        with sistem_baglami() as s2:
            s2.execute(text("UPDATE alerts SET acked_by = CAST(:u AS uuid) WHERE plant_id = :p"), {"u": y.get("user_id") or pid, "p": plant_id})
        assert ss.alarmlar(pid)["acik"] == al["acik"] - 1   # okunan alarm açık sayılmaz
        # v2.515: segment seçilmemiş santral «segment_yok»; yarın için KGÜP arşivi boş; müşteri detayında da segment/uevcb alanı
        assert "segment_yok" in bizim["sorunlar"] and bizim["segment"] is None and bizim["uevcb"] is None and bizim["kgup_yukumlu"] is None
        assert bizim["kgup_yarin"]["oneri_surum"] is None and bizim["kgup_yarin"]["bildirilen"] is False and bizim["kgup_yarin"]["eak"] is False
        assert len(bizim["kgup_yarin"]["gun"]) == 10
        dsan = [x for x in ps.kiraci_detay(pid, y["tenant_id"])["santraller"] if x["id"] == str(plant_id)][0]
        assert dsan["segment"] is None and "uevcb" in dsan and "kgup_yukumlu" in dsan
        with sistem_baglami() as s2:
            s2.execute(text("UPDATE plants SET params_json = '{\"segment\": \"lisansli_serbest\", \"uevcb\": \"40X0000000000001A\"}'::jsonb WHERE id = :p"), {"p": plant_id})
        bizim2 = [x for x in ss.santraller(pid)["santraller"] if x["id"] == str(plant_id)][0]
        assert "segment_yok" not in bizim2["sorunlar"] and bizim2["segment"] == "lisansli_serbest" and bizim2["uevcb"] == "40X0000000000001A" and bizim2["kgup_yukumlu"] is True
        assert {"scada_yok", "kosu_yok"} <= set(bizim["sorunlar"]) and bizim["kiraci"] == f"Firma3 {e}" and bizim["son_hata"]
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM alerts WHERE plant_id = :p"), {"p": plant_id})
            s.execute(text("DELETE FROM jobs_log WHERE plant_id = :p"), {"p": plant_id})
            s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": plant_id})


def test_faz4_kullanim(temiz):
    """25.10 Faz 4 — günlük sayaç UPSERT, paylaşımlı pencere (iki «süreç» aynı satırı sayar), ay özeti ve günlük kırılımda
    türetilmiş sayımlar (report_log, forecast_runs) + sayaç türleri (DB'li)."""
    import datetime as dt
    from pvquant.services import kullanim_service as ks
    e = temiz
    pid = ps.ilk_sahip_olustur(f"sahip4-{e}@pvq.test", "cok-gizli-parola-123")
    y = ps.kiraci_olustur(pid, f"Firma4 {e}", f"admin4-{e}@musteri.test", rol="sahip")
    tid = y["tenant_id"]
    with sistem_baglami() as s:
        plant_id = s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, lat, lon, tz) "
                                  "VALUES (CAST(:t AS uuid), :n, 500, 38.0, 33.0, 'Europe/Istanbul') RETURNING id"), {"t": tid, "n": f"GES4 {e}"}).scalar()
        s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, mode, model) VALUES (CAST(:t AS uuid), :p, 'A', 'test')"), {"t": tid, "p": plant_id})
        s.execute(text("INSERT INTO report_log(tenant_id, plant_id, mode) VALUES (CAST(:t AS uuid), :p, 'html')"), {"t": tid, "p": plant_id})
        # v2.516 (#6): KGÜP öneri sürümü (pvquant) ve bildirilen dosya (musteri) kullanım sayımına girer; EAK girmez
        for kaynak in ("pvquant", "musteri", "eak"):
            s.execute(text("INSERT INTO kgup_surum(tenant_id, plant_id, teslim_gunu, surum, kantil, sha256, dosya, dosya_adi, kaynak) "
                           "VALUES (CAST(:t AS uuid), :p, CURRENT_DATE + 1, 1, 'p50', repeat('a', 64), '\\x00'::bytea, 'KGUP.csv', :k)"),
                      {"t": tid, "p": plant_id, "k": kaynak})
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
        assert o["ay"] == bu_ay and k["bu_ay"] == {"dis_api": 3, "webhook": 1, "webhook_hata": 1, "rapor": 1, "kosu": 1, "scada_saat": 0, "yukleme": 0,
                                                   "kgup": 1, "kgup_bildirilen": 1}
        assert k["onceki_ay"]["dis_api"] == 0 and k["etkin_anahtar"] == 0
        g = ks.gunler(pid, tid, bu_ay)
        bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
        assert g["ad"] == f"Firma4 {e}" and g["gunler"][0]["gun"] == bugun and g["gunler"][0]["dis_api"] == 3 and g["gunler"][0]["kosu"] == 1
        assert g["gunler"][0]["kgup"] == 1 and g["gunler"][0]["kgup_bildirilen"] == 1
        assert ks.gunler(pid, "00000000-0000-0000-0000-000000000000")["gunler"] == []
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM kullanim_sayac WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
            s.execute(text("DELETE FROM hiz_pencere WHERE anahtar = :a"), {"a": f"anahtar:{e}"})
            s.execute(text("DELETE FROM report_log WHERE plant_id = :p"), {"p": plant_id})
            s.execute(text("DELETE FROM kgup_surum WHERE plant_id = :p"), {"p": plant_id})
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
                       "(now() - interval '40 days', 'platform', 'kiraci_guncelle', :e), (now(), 'platform', 'giris', :e), "
                       "(now() - interval '40 days', 'musteri', 'giris', :e)"), {"e": eposta})   # 26.10 denetim-3: eski MÜŞTERİ girişi
    monkeypatch.setattr("pvquant.config.get_settings", lambda: type("S", (), {"denetim_saklama_ay": 0})())
    assert dz.temizle() == 0
    assert dz.temizle(1) == 1                                            # yalnız eski PLATFORM girişi; müşteri Ayarlar izi kalır
    with sistem_baglami() as s:
        kalan = s.execute(text("SELECT eylem FROM denetim_izi WHERE aktor_eposta = :e ORDER BY eylem"), {"e": eposta}).scalars().all()
    assert kalan == ["giris", "giris", "kiraci_guncelle"]


def test_faz5_planlar_ve_temsil(temiz):
    """26.10 Faz 5 — planlar tohumu + FK (bilinmeyen plan reddedilir), plan_guncelle (None = sınırsız), temsil jetonu (viewer, temsil, 15 dk;
    askıdaki kiracıya açılmaz)."""
    import jwt as _j
    e = temiz
    pid = ps.ilk_sahip_olustur(f"sahip5-{e}@pvq.test", "cok-gizli-parola-123")
    planlar = {p["ad"]: p for p in ps.plan_listesi()}
    assert {"pilot", "standart", "kurumsal"} <= set(planlar) and planlar["pilot"]["santral_limit"] == 3 and planlar["kurumsal"]["santral_limit"] is None
    y = ps.kiraci_olustur(pid, f"Firma5 {e}", f"admin5-{e}@musteri.test", "pilot", rol="sahip")
    with pytest.raises(Exception):                                   # FK: bilinmeyen plan
        with sistem_baglami() as s:
            s.execute(text("UPDATE tenants SET plan = 'yok-boyle-plan' WHERE id = CAST(:t AS uuid)"), {"t": y["tenant_id"]})
    assert ps.plan_guncelle("pilot", santral_limit=4)["santral_limit"] == 4
    assert ps.plan_guncelle("pilot", santral_limit=None)["santral_limit"] is None
    ps.plan_guncelle("pilot", santral_limit=3)
    with pytest.raises(ValueError):
        ps.plan_guncelle("pilot", santral_limit=-1)
    assert ps.plan_guncelle("yok", santral_limit=1) is None
    with pytest.raises(ValueError):                                  # 26.10 denetim-2: bilinmeyen plan 500 değil 422
        ps.kiraci_olustur(pid, f"Firma5b {e}", f"admin5b-{e}@musteri.test", "yok-plan")
    with pytest.raises(ValueError):
        ps.kiraci_guncelle(pid, y["tenant_id"], plan="yok-plan")
    t = ps.temsil_jetonu(pid, y["tenant_id"])
    c = _j.decode(t["token"], au._sir(), algorithms=["HS256"])
    assert c["role"] == "viewer" and c["temsil"] == pid and c["tenant_id"] == y["tenant_id"] and t["sure_dk"] == 15 and t["kiraci"] == f"Firma5 {e}"
    assert ps.temsil_jetonu(pid, "00000000-0000-0000-0000-000000000000") is None
    ps.kiraci_guncelle(pid, y["tenant_id"], status="suspended")
    with pytest.raises(ValueError):
        ps.temsil_jetonu(pid, y["tenant_id"])
    ps.kiraci_guncelle(pid, y["tenant_id"], status="active")


def test_faz6_kurulus_politikasi(temiz):
    """26.10 Faz 6 — kuruluş ayarı: politika açılınca 2FA'sız yöneticide oturum_durumu.iki_adim_kurulmali True, editörde False; kiracı
    detayında alan; kapanınca False."""
    from pvquant.services import kurulus_service as kr
    e = temiz
    pid = ps.ilk_sahip_olustur(f"sahip7-{e}@pvq.test", "cok-gizli-parola-123")
    y = ps.kiraci_olustur(pid, f"Firma7 {e}", f"admin7-{e}@musteri.test", rol="sahip")
    tid, uid = y["tenant_id"], y["user_id"]
    assert kr.ayarlar(tid) == {"yonetici_2fa_zorunlu": False, "iki_adimsiz_yonetici": 1}
    assert au.oturum_durumu(uid)["iki_adim_kurulmali"] is False
    assert kr.ayar_guncelle(tid, yonetici_2fa_zorunlu=True)["yonetici_2fa_zorunlu"] is True
    assert au.oturum_durumu(uid)["iki_adim_kurulmali"] is True                               # önbellek düşürüldü, DB'den
    assert ps.kiraci_detay(pid, tid)["yonetici_2fa_zorunlu"] is True
    with sistem_baglami() as s:
        s.execute(text("UPDATE users SET totp_aktif = true WHERE id = CAST(:u AS uuid)"), {"u": uid})
    au.oturum_onbellegi_dusur()
    assert au.oturum_durumu(uid)["iki_adim_kurulmali"] is False                              # 2FA kurulunca kapı açılır
    assert kr.ayarlar(tid)["iki_adimsiz_yonetici"] == 0
    kr.ayar_guncelle(tid, yonetici_2fa_zorunlu=False)


def test_faz5_temsil_uctan_uca_get_ler(temiz, monkeypatch):
    """26.10 denetim-2 (2. aşama) — GERÇEK DB + gerçek kapı: temsil jetonuyla müşteri GET uçları 500 vermez; yazanlar ve rapor 403;
    platform ucu 403; kiracı askıya alınınca 403."""
    import jwt as _j
    from fastapi.testclient import TestClient
    import apps.api.main as api_main
    e = temiz
    pid = ps.ilk_sahip_olustur(f"sahip8-{e}@pvq.test", "cok-gizli-parola-123")
    y = ps.kiraci_olustur(pid, f"Firma8 {e}", f"admin8-{e}@musteri.test", rol="sahip")
    with sistem_baglami() as s:
        plant_id = s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, lat, lon, tz) VALUES (CAST(:t AS uuid), :n, 500, 38.0, 33.0, 'Europe/Istanbul') RETURNING id"),
                             {"t": y["tenant_id"], "n": f"GES8 {e}"}).scalar()
    try:
        t = ps.temsil_jetonu(pid, y["tenant_id"]); tj = {"Authorization": "Bearer " + t["token"]}
        c = TestClient(api_main.app)
        kodlar = {}
        for yol in ("/v1/plants", "/v1/portfoy", "/v1/isler", "/v1/hakkinda", "/v1/iki-adim", "/v1/takim", "/v1/paylasimlar", "/v1/plants-arsiv",
                    f"/v1/plants/{plant_id}/summary", f"/v1/plants/{plant_id}/forecast", "/v1/kurulus/ayarlar", "/v1/api-anahtarlari"):
            kodlar[yol] = c.get(yol, headers=tj).status_code
        assert all(k < 500 for k in kodlar.values()), kodlar                                   # hiçbir GET 500 vermez
        assert kodlar["/v1/plants"] == 200 and kodlar["/v1/hakkinda"] == 200
        assert kodlar["/v1/takim"] == 403 and kodlar["/v1/kurulus/ayarlar"] == 403 and kodlar["/v1/api-anahtarlari"] == 403   # yönetici uçları
        assert c.post("/v1/oturum/yenile", headers=tj).status_code == 403
        assert c.get(f"/v1/plants/{plant_id}/report?fmt=html", headers=tj).status_code == 403
        assert c.get("/v1/yonetim/ben", headers=tj).status_code == 403
        ps.kiraci_guncelle(pid, y["tenant_id"], status="suspended")
        assert c.get("/v1/plants", headers=tj).status_code == 403
        ps.kiraci_guncelle(pid, y["tenant_id"], status="active")
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": y["tenant_id"]})
            s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": plant_id})
