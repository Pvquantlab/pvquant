"""v2.79 — JWT sirri disiplini (DB'siz).
Gece vakasi: compose ${PVQ_JWT_SECRET:-} bos dize set eder; bos != yok.
Bos sir artik sessizce 500'e yurumez — gurultuyle reddedilir."""
import pytest


def test_bos_sir_gurultuyle_reddedilir(monkeypatch):
    from pvquant.services import auth_service
    monkeypatch.setenv("PVQ_JWT_SECRET", "")
    with pytest.raises(RuntimeError, match="BOS"):
        auth_service._sir()


def test_hic_yoksa_dev_varsayilani(monkeypatch):
    from pvquant.services import auth_service
    monkeypatch.delenv("PVQ_JWT_SECRET", raising=False)
    assert auth_service._sir() == "dev-secret-DEGISTIR"


def test_gercek_sir_gecerli_ve_coz_simetrik(monkeypatch):
    import jwt as _jwt
    from pvquant.services import auth_service
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef")
    token = _jwt.encode({"sub": "u"}, auth_service._sir(), algorithm="HS256")
    assert auth_service.token_coz(token)["sub"] == "u"
