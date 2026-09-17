"""v2.335 — "şifremi unuttum": uç sözleşmesi (varlık sızdırmama, 422 çevirisi)
ve servis doğrulamaları. SQL akışının kendisi canlı kanıtla ölçülür (mühür
gövdesi); burada ağ/DB'siz sözleşme testleri var."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from pvquant.services import auth_service as au


def test_istek_ucu_varlik_sizdirmaz(monkeypatch):
    """bilinen ve bilinmeyen e-posta AYNI yanıtı alır; dönüş değeri uca sızmaz."""
    sonuclar = iter([True, False])
    monkeypatch.setattr(au, "parola_sifirlama_istek", lambda e: next(sonuclar))
    c = TestClient(api_main.app)
    y1 = c.post("/v1/parola-sifirla-istek", json={"eposta": "var@ges.com"})
    y2 = c.post("/v1/parola-sifirla-istek", json={"eposta": "yok@ges.com"})
    assert y1.status_code == y2.status_code == 200
    assert y1.json() == y2.json() == {"tamam": True}


def test_sifirla_ucu_422_cevirisi(monkeypatch):
    def patla(j, p):
        raise ValueError("bağlantı geçersiz ya da süresi dolmuş")
    monkeypatch.setattr(au, "parola_sifirla", patla)
    c = TestClient(api_main.app)
    y = c.post("/v1/parola-sifirla", json={"jeton": "x", "parola": "y" * 12})
    assert y.status_code == 422
    assert "geçersiz" in y.json()["detail"]

    monkeypatch.setattr(au, "parola_sifirla", lambda j, p: None)
    assert c.post("/v1/parola-sifirla",
                  json={"jeton": "x", "parola": "y" * 12}).json() == {"tamam": True}


def test_kisa_parola_dbye_gitmeden_reddedilir():
    with pytest.raises(ValueError, match="10 karakter"):
        au.parola_sifirla("jeton", "kisa")


def test_jeton_ozeti_tek_yonlu():
    """jeton düz saklanmaz: özet sabit uzunlukta ve girdiye duyarlı."""
    a = au._jeton_ozet("jeton-bir")
    b = au._jeton_ozet("jeton-iki")
    assert a != b and len(a) == len(b) == 64
    assert "jeton" not in a
