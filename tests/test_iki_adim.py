"""v2.338 — iki adımlı doğrulama: uç sözleşmeleri (kapılar, varlık sızmazlığı,
422 çevirisi) ve giriş akışının 2FA dalı. TOTP/DB tam akışı canlı kanıtla
ölçülür (mühür gövdesi); burada ağsız sözleşme + login mantığı test edilir."""
import pyotp
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import auth_service as au, iki_adim_service as ia


def _kimlik(uid="u1"):
    api_main.app.dependency_overrides[gecerli_kullanici] = \
        lambda: {"sub": uid, "tenant_id": "t1", "role": "admin", "exp": 0}


def test_uclar_kimlik_ister():
    api_main.app.dependency_overrides.clear()
    c = TestClient(api_main.app)
    # başlıksız → 422 (zorunlu Authorization başlığı eksik); bozuk token → 401.
    # İkisi de "kapı var" demek — 2FA uçları kimliksiz erişilemez.
    assert c.get("/v1/iki-adim").status_code == 422
    assert c.get("/v1/iki-adim", headers={"Authorization": "Bearer x"}).status_code == 401
    assert c.post("/v1/iki-adim/baslat").status_code == 422


def test_baslat_ve_durum(monkeypatch):
    _kimlik()
    monkeypatch.setattr(ia, "durum", lambda u: {"aktif": False, "kalan_kurtarma": 0})
    monkeypatch.setattr(au, "eposta_getir", lambda u: "ad@sirket.com")
    monkeypatch.setattr(ia, "baslat", lambda u, e: {"secret": "S", "otpauth_uri": "otpauth://x", "qr_svg": "<svg/>"})
    try:
        c = TestClient(api_main.app)
        assert c.get("/v1/iki-adim").json() == {"aktif": False, "kalan_kurtarma": 0}
        j = c.post("/v1/iki-adim/baslat").json()
        assert j["secret"] == "S" and j["qr_svg"] == "<svg/>"
    finally:
        api_main.app.dependency_overrides.clear()


def test_dogrula_gecersiz_kod_422(monkeypatch):
    _kimlik()

    def patla(u, kod):
        raise ValueError("kod doğrulanamadı — uygulamadaki 6 haneyi girin")
    monkeypatch.setattr(ia, "dogrula_ve_ac", patla)
    try:
        c = TestClient(api_main.app)
        y = c.post("/v1/iki-adim/dogrula", json={"kod": "000000"})
        assert y.status_code == 422 and "doğrulanamadı" in y.json()["detail"]
    finally:
        api_main.app.dependency_overrides.clear()


def test_login_2fa_dali(monkeypatch):
    """parola doğru + 2FA açık: kod yoksa iki_adim_gerekli (token yok),
    yanlış kod → None (401), doğru kod → token."""
    class _Row:
        id, tenant_id, role, aktif, totp_aktif = "u1", "t1", "admin", True, True
        pw_hash = "x"

    class _S:
        def execute(self, *a, **k):
            class _R:
                def first(self_): return _Row()
                def scalar(self_): return None
            return _R()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(au, "sistem_baglami", lambda: _S())
    monkeypatch.setattr(au.bcrypt, "verify", lambda s, h: True)     # parola doğru
    monkeypatch.setattr(au, "_sir", lambda: "test-sir")

    # kod yok → challenge, token YOK
    r = au.giris("a@b.co", "parola")
    assert r == {"iki_adim_gerekli": True}

    # yanlış kod → None
    monkeypatch.setattr(ia, "giris_dogrula", lambda uid, kod: False)
    assert au.giris("a@b.co", "parola", "000000") is None

    # doğru kod → token
    monkeypatch.setattr(ia, "giris_dogrula", lambda uid, kod: True)
    r = au.giris("a@b.co", "parola", "123456")
    assert "token" in r and r["role"] == "admin"


def test_login_2fa_kapali_kod_gerekmez(monkeypatch):
    """2FA kapalı hesap kod olmadan girer (geriye uyumluluk)."""
    class _Row:
        id, tenant_id, role, aktif, totp_aktif = "u2", "t1", "viewer", True, False
        pw_hash = "x"

    class _S:
        def execute(self, *a, **k):
            class _R:
                def first(self_): return _Row()
            return _R()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(au, "sistem_baglami", lambda: _S())
    monkeypatch.setattr(au.bcrypt, "verify", lambda s, h: True)
    monkeypatch.setattr(au, "_sir", lambda: "test-sir")
    r = au.giris("a@b.co", "parola")
    assert "token" in r


def test_kurtarma_kodu_uretimi_ve_tuketimi():
    """_kurtarma_uret 10 tireli kod döndürür; ham (tiresiz) hali bcrypt'le doğrulanır."""
    yazilan = []

    class _S:
        def execute(self, sql, params=None):
            if params and "h" in params:
                yazilan.append(params["h"])
            return None
    kodlar = ia._kurtarma_uret(_S(), "u1")
    assert len(kodlar) == 10
    assert all("-" in k and len(k) == 9 for k in kodlar)     # xxxx-xxxx
    # ilk kodun ham hali saklanan özetiyle eşleşmeli
    from passlib.hash import bcrypt
    ham = kodlar[0].replace("-", "")
    assert bcrypt.verify(ham, yazilan[0])
