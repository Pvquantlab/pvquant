"""v2.328 — vitrin başvuru kapısı (DB'siz: servis monkeypatch)."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from pvquant.services import basvuru_service


@pytest.fixture()
def istemci(monkeypatch):
    kayitlar: list[dict] = []

    def _sahte_insert(eposta, ad, kwp):
        kayitlar.append({"eposta": eposta, "santral_adi": ad, "kurulu_guc_kwp": kwp})

    # DB katmanını değil, servis içindeki insert'i taklit et: sistem_baglami çağrısını
    # tetiklememek için kaydet'in DB'ye giden kolunu saran küçük bir sahte bağlam kur.
    class _SahteOturum:
        def execute(self, _sql, p):
            _sahte_insert(p["e"], p["a"], p["k"])

    class _SahteBaglam:
        def __enter__(self):
            return _SahteOturum()

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(basvuru_service, "sistem_baglami", lambda: _SahteBaglam())
    c = TestClient(api_main.app)
    c.kayitlar = kayitlar  # type: ignore[attr-defined]
    yield c


def test_gecerli_basvuru_kaydedilir(istemci):
    y = istemci.post("/v1/vitrin/basvuru", json={
        "eposta": "Ornek@Firma.com", "santral_adi": "Deneme GES", "kurulu_guc_kwp": 4514})
    assert y.status_code == 200 and y.json()["tamam"] is True
    assert istemci.kayitlar == [{"eposta": "ornek@firma.com",
                                 "santral_adi": "Deneme GES", "kurulu_guc_kwp": 4514.0}]


def test_gecersiz_eposta_422(istemci):
    y = istemci.post("/v1/vitrin/basvuru", json={"eposta": "eposta-degil"})
    assert y.status_code == 422
    assert istemci.kayitlar == []


def test_balkupu_sessizce_yutulur(istemci):
    # bot alanı doluysa 'tamam' döner ama kayıt DÜŞMEZ (bota sinyal yok)
    y = istemci.post("/v1/vitrin/basvuru", json={
        "eposta": "bot@bot.com", "web": "http://spam"})
    assert y.status_code == 200 and y.json()["tamam"] is True
    assert istemci.kayitlar == []


def test_sacma_kurulu_guc_null_olur(istemci):
    y = istemci.post("/v1/vitrin/basvuru", json={
        "eposta": "a@b.co", "kurulu_guc_kwp": -5})
    assert y.status_code == 200
    assert istemci.kayitlar[0]["kurulu_guc_kwp"] is None


def test_liste_admin_ister(istemci):
    # başlıksız istek FastAPI doğrulamasında 422 düşer (depo sözleşmesi); jetonsuz asla 200 olmaz
    assert istemci.get("/v1/vitrin/basvurular").status_code in (401, 422)
