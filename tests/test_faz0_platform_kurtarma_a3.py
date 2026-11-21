"""Faz 0 C3-a / A3 (21.11.2026, rapor §22-R): platform 2FA kurtarma kodları — güvenlik testleri (test DB, sentetik hesaplar).
Canlı hesap yok; müşteri kimlik doğrulaması (auth_service/iki_adim_service/kurtarma_kodlari) DOKUNULMAZ."""
from __future__ import annotations

import base64
import hashlib
import os
import re
import threading
import time
import uuid

import pyotp
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.skipif(not os.environ.get("PVQ_DB_URL"), reason="test DB gerekir")
KOD_DESENI = re.compile(r"^[A-Z2-7]{5}-[A-Z2-7]{5}-[A-Z2-7]{5}-[A-Z2-7]{5}-[A-Z2-7]{5}-[A-Z2-7]$")


@pytest.fixture()
def sahip():
    """2FA'lı sentetik sahip: (pid, email, parola, totp_secret, kurtarma_kodlari)."""
    from pvquant.db import bakim_baglami
    from pvquant.services import platform_service as ps
    onek = f"faz0a3-{uuid.uuid4().hex[:6]}"
    email, parola = f"{onek}@example.invalid", "Gizli-Parola-123456"
    pid = ps.ilk_sahip_olustur(email, parola)
    secret = ps.iki_adim_baslat(pid)["secret"]
    kodlar = ps.iki_adim_dogrula(pid, pyotp.TOTP(secret).now())["kurtarma_kodlari"]
    yield {"pid": pid, "email": email, "parola": parola, "secret": secret, "kodlar": kodlar, "onek": onek}
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM denetim_izi WHERE aktor_eposta LIKE :e"), {"e": onek + "%"})
        s.execute(text("DELETE FROM platform_kullanicilar WHERE email LIKE :e"), {"e": onek + "%"})   # kurtarma kodları CASCADE


def _totp_sonraki(secret: str, adim: int = 1) -> str:
    return pyotp.TOTP(secret).at(int(time.time()) + 30 * adim)


def test_1_uretim_10_kod_128_bit_ve_sha256(sahip):
    from pvquant.db import sistem_baglami
    from pvquant.services import platform_service as ps
    kodlar = sahip["kodlar"]
    assert len(kodlar) == 10 and len(set(kodlar)) == 10 and all(KOD_DESENI.match(k) for k in kodlar)
    ham = ps.kurtarma_normalize(kodlar[0])
    assert ham and len(ham) == 26
    assert len(base64.b32decode(ham + "======")) == 16   # 128 bit
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT kod_hash, grup_id, kullanildi_at FROM platform_kurtarma_kodlari WHERE platform_user_id = CAST(:p AS uuid)"), {"p": sahip["pid"]}).all()
    assert len(rows) == 10 and len({r.grup_id for r in rows}) == 1 and all(r.kullanildi_at is None for r in rows)
    assert hashlib.sha256(ham.encode()).hexdigest() in {r.kod_hash for r in rows}
    assert not any(ham in r.kod_hash or kodlar[0] in r.kod_hash for r in rows)   # düz kod saklanmaz
    assert ps.kurtarma_normalize("123456") is None and ps.kurtarma_normalize(kodlar[0].lower().replace("-", " ")) == ham


def test_2_kurtarma_ile_giris_tek_kullanim_ve_parola_once(sahip):
    from pvquant.services import platform_service as ps
    e, p, k = sahip["email"], sahip["parola"], sahip["kodlar"]
    assert ps.giris(e, "yanlis-parola-1234", k[0]) is None            # parola önce: yanlış parola + doğru kod → red, kod TÜKETİLMEZ
    assert ps.kurtarma_kalan(sahip["pid"]) == 10
    g = ps.giris(e, p, k[0])
    assert g and g["ikinci_adim"] == "kurtarma" and g["kurtarma_kalan"] == 9 and g["kurtarma_uyari"] is None
    import jwt as _jwt

    from pvquant.services import auth_service as au
    assert _jwt.decode(g["token"], au._sir(), algorithms=["HS256"])["yontem"] == "kurtarma"
    assert ps.giris(e, p, k[0]) is None                                  # tekrar: aynı kod bir daha geçmez
    assert ps.giris(e, p, "000000") is None                              # yanlış TOTP → red
    g2 = ps.giris(e, p, _totp_sonraki(sahip["secret"], 1))   # kurulumda kullanılan adım tekrar korumasına takılır → sonraki adım
    assert g2 and g2["ikinci_adim"] == "totp" and "kurtarma_kalan" not in g2   # TOTP yolu değişmedi
    y = ps.oturum_yenile(sahip["pid"], yontem="kurtarma")
    assert _jwt.decode(y["token"], au._sir(), algorithms=["HS256"])["yontem"] == "kurtarma"   # yenilemede yöntem taşınır


def test_3_yaris_ayni_kod_esz_zamanli_yalniz_biri(sahip):
    from pvquant.services import platform_service as ps
    kod = sahip["kodlar"][1]
    sonuc = []
    def dene():
        sonuc.append(ps.kurtarma_tuket(sahip["pid"], kod))
    t = [threading.Thread(target=dene) for _ in range(6)]
    for x in t:
        x.start()
    for x in t:
        x.join()
    assert sum(1 for r in sonuc if r is not None) == 1 and ps.kurtarma_kalan(sahip["pid"]) == 9


def test_4_rotasyon_totp_sart_eski_grup_gecersiz(sahip):
    from pvquant.services import platform_service as ps
    with pytest.raises(ps.PlatformHata):
        ps.kurtarma_yenile(sahip["pid"], sahip["kodlar"][2])            # kurtarma koduyla yenileme yok
    yeni = ps.kurtarma_yenile(sahip["pid"], _totp_sonraki(sahip["secret"], 1))
    assert len(yeni) == 10 and not set(yeni) & set(sahip["kodlar"]) and ps.kurtarma_kalan(sahip["pid"]) == 10
    assert ps.giris(sahip["email"], sahip["parola"], sahip["kodlar"][3]) is None    # eski grup geçersiz
    assert ps.giris(sahip["email"], sahip["parola"], yeni[0])["ikinci_adim"] == "kurtarma"


def test_5_uyari_esigi_ve_sifirlama_kodlari_siler(sahip):
    from pvquant.services import platform_service as ps
    e, p, k = sahip["email"], sahip["parola"], sahip["kodlar"]
    for i in range(7):
        assert ps.giris(e, p, k[i])["ikinci_adim"] == "kurtarma"
    g = ps.giris(e, p, k[7])
    assert g["kurtarma_kalan"] == 2 and "2 kod kaldı" in g["kurtarma_uyari"]
    assert ps.ben(sahip["pid"])["kalan_kurtarma"] == 2
    assert ps.operator_guncelle(sahip["pid"], iki_adim_sifirla=True) is True
    assert ps.kurtarma_kalan(sahip["pid"]) == 0 and ps.giris(e, p)["iki_adim_kurulmali"] is True


def test_6_yeniden_kur_kilitlenme_cikisi(sahip):
    from pvquant.services import platform_service as ps
    e, p = sahip["email"], sahip["parola"]
    assert ps.giris(e, p, sahip["kodlar"][0])["ikinci_adim"] == "kurtarma"
    sv_once = ps.oturum_durumu(sahip["pid"])["sv"]
    b = ps.iki_adim_yeniden_kur(sahip["pid"])
    assert b["secret"] and b["secret"] != sahip["secret"] and ps.oturum_durumu(sahip["pid"])["sv"] == sv_once + 1   # oturumlar düşer
    assert ps.kurtarma_kalan(sahip["pid"]) == 0 and ps.giris(e, p)["iki_adim_kurulmali"] is True
    yeni = ps.iki_adim_dogrula(sahip["pid"], pyotp.TOTP(b["secret"]).now())["kurtarma_kodlari"]
    assert len(yeni) == 10 and ps.giris(e, p, _totp_sonraki(b["secret"], 1))["ikinci_adim"] == "totp"


def test_7_api_hassas_islem_kurtarma_oturumunda_403_ve_hijyen(sahip, monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from apps.api import yonetim as yo
    from pvquant.services import platform_service as ps
    monkeypatch.setattr(yo, "paylasimli_sinir", lambda *a, **k: None)
    monkeypatch.setattr(yo, "hesap_siniri", lambda *a, **k: None)
    izler = []
    monkeypatch.setattr(yo.dz, "kaydet", lambda *a, **k: izler.append((a, k)) or True)
    c = TestClient(api_main.app)
    e, p, k = sahip["email"], sahip["parola"], sahip["kodlar"]
    g = c.post("/v1/yonetim/giris", json={"email": e, "sifre": p, "kod": k[0]}).json()
    assert g["ikinci_adim"] == "kurtarma" and g["kurtarma_kalan"] == 9
    h = {"Authorization": "Bearer " + g["token"]}
    assert c.get("/v1/yonetim/ben", headers=h).status_code == 200                                   # okuma açık
    y = c.post("/v1/yonetim/operatorler", json={"email": f"{sahip['onek']}-2@example.invalid", "rol": "sahip", "sifre": p, "kod": k[1]}, headers=h)
    assert y.status_code == 403 and "kurtarma" in y.json()["detail"]                                 # hassas işlem 403
    assert c.post("/v1/yonetim/iki-adim/kurtarma-yenile", json={"kod": k[1]}, headers=h).status_code == 403
    r = c.post("/v1/yonetim/iki-adim/yeniden-kur", json={}, headers=h)                              # kurtarma oturumu → yeniden kur serbest
    assert r.headers.get("cache-control") == "no-store"                                             # QA İ-4: sır/kod döndüren yanıt önbelleğe alınmaz
    assert r.status_code == 200 and r.json()["secret"]
    # hijyen: izlerde ve yanıt dışında kod/parola/sır yok
    duz = " ".join(str(x) for x in izler)
    for gizli in [*k, p, sahip["secret"], r.json()["secret"]]:
        assert gizli not in duz and ps.kurtarma_normalize(gizli) not in duz if ps.kurtarma_normalize(gizli) else gizli not in duz
    assert any(a[1] == "giris" and kw.get("ayrinti") == {"ikinci_adim": "kurtarma", "kurtarma_kalan": 9} for a, kw in izler)
    assert any(a[1] == "iki_adim_yeniden_kur" for a, _ in izler)
    # başarısız giriş izi: kod yazılmaz
    assert c.post("/v1/yonetim/giris", json={"email": e, "sifre": "yanlis-parola-1234", "kod": k[2]}).status_code == 401
    bas = [kw for a, kw in izler if a[1] == "giris_basarisiz"][-1]
    assert bas["ayrinti"] == {"ikinci_adim_denendi": True} and k[2] not in str(bas)


def test_8_hesap_basina_hiz_siniri(monkeypatch):
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from apps.api import yonetim as yo
    from pvquant.services import platform_service as ps
    monkeypatch.setattr(yo, "paylasimli_sinir", lambda *a, **k: None)   # IP sınırı devre dışı; hesap sınırı gerçek sayaçla
    monkeypatch.setattr(yo.limiter, "enabled", False)   # slowapi IP sınırı (5/dk) da devre dışı — yalnız hesap sınırı sınanır
    monkeypatch.setattr(ps, "giris", lambda e, s, k=None: None)
    monkeypatch.setattr(yo.dz, "kaydet", lambda *a, **k: True)
    c = TestClient(api_main.app)
    e = f"faz0a3-hiz-{uuid.uuid4().hex[:6]}@example.invalid"
    from pvquant.services import kullanim_service as ks
    try:
        kodlar = [c.post("/v1/yonetim/giris", json={"email": e, "sifre": "x", "kod": "y"}).status_code for _ in range(11)]
        assert kodlar[:10] == [401] * 10 and kodlar[10] == 429
    finally:
        ks.pencere_sil(ks.hesap_anahtari(ps.HESAP_SINIR_AD, e))   # R2: test DB'de pencere kalıntısı bırakma


def test_9_tablo_yokken_totp_yolu_calisir_kurtarma_kapali(sahip, monkeypatch):
    from pvquant.services import platform_service as ps
    monkeypatch.setattr(ps, "_kurtarma_ozet", lambda ham: (_ for _ in ()).throw(RuntimeError("tablo yok")))   # tablo hatasını temsil eder
    assert ps.kurtarma_tuket(sahip["pid"], sahip["kodlar"][0]) is None and ps.giris(sahip["email"], sahip["parola"], sahip["kodlar"][0]) is None
    assert ps.giris(sahip["email"], sahip["parola"], _totp_sonraki(sahip["secret"], 1))["ikinci_adim"] == "totp"


def test_10_musteri_kimlik_dogrulamasi_degismedi():
    import subprocess
    # auth/iki_adim bu turda (Faz 0 P0-08) dokunuldu ama A3 ile DEĞİL: A3 yalnız platform_service/yonetim/deps/hiz/denetim/alembic v2642
    a3 = subprocess.run(["git", "diff", "HEAD", "--", "src/pvquant/services/auth_service.py", "src/pvquant/services/iki_adim_service.py"], capture_output=True, text=True).stdout
    for a3_imza in ("platform_kurtarma", "KURTARMA_ADET", "kurtarma_normalize", "kurtarma_tuket", "yontem="):
        assert a3_imza not in a3   # müşteri kimlik dosyalarında A3 izi yok (bu turdaki P0-08 düzeltmeleri ayrı)


def test_11_tablo_yokken_kurulum_sifirlama_yeniden_kur_calisir(sahip, monkeypatch):
    """QA A3 göç geri dönüşü (21.11): tablo yokken (v2642 geri alınmış) 2FA kurulumu, sıfırlama ve yeniden-kur ProgrammingError ile çöküyor,
    kurulumun totp_aktif yazımı da geri alınıyordu. Düzeltme: _kurtarma_tablo_var aynı işlemde to_regclass → kodlar [] / silme atlanır."""
    from pvquant.db import sistem_baglami
    from pvquant.services import platform_service as ps
    pid, email, parola = sahip["pid"], sahip["email"], sahip["parola"]
    monkeypatch.setattr(ps, "_kurtarma_tablo_var", lambda s: False)
    secret = ps.iki_adim_yeniden_kur(pid)["secret"]          # yeniden kurulum (silme atlanır, çökmez)
    y = ps.iki_adim_dogrula(pid, pyotp.TOTP(secret).now())
    assert y == {"kurtarma_kodlari": []}                      # kurulum tamamlanır, kod üretilmez
    with sistem_baglami() as s:
        assert s.execute(text("SELECT totp_aktif FROM platform_kullanicilar WHERE id=:i"), {"i": pid}).scalar() is True
    g = ps.giris(email, parola, pyotp.TOTP(secret).at(int(time.time()) + 30))
    assert g is not None and g["ikinci_adim"] == "totp"
    assert ps.operator_guncelle(pid, iki_adim_sifirla=True) is True
