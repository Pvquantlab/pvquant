"""24.10 Faz 0 güvenlik tabanı (DB'siz: servis monkeypatch) — docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §1.
1) vitrin başvuruları yalnız PVQ_PLATFORM_TENANT_ID kiracısının yöneticisine; boşsa kimseye.
2) gecerli_kullanici: oturum sürümü (sv) uyuşmazlığı 401, pasif 401, askıdaki kiracı 403, eski jeton (sv yok) sürüm 0'da geçerli.
3) giriş/tazeleme: KiraciAskida → 403.
4) migration metni: iki rapor tablosuna politika + users.oturum_surumu."""
import pathlib
import jwt as _jwt
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import auth_service as au, basvuru_service


def _rol(r, tenant="t1"):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": tenant, "role": r, "exp": 0}


@pytest.fixture(autouse=True)
def _temiz():
    yield
    api_main.app.dependency_overrides.clear()
    au.oturum_onbellegi_dusur()


def test_basvurular_musteri_ucunda_yok(monkeypatch):
    """Faz 0 geçici kilidi (PVQ_PLATFORM_TENANT_ID) Faz 2'de kalktı: müşteri uçları artık YOK (404); başvurular yalnız
    /v1/yonetim/basvurular* (tests/test_yonetim_api.py). Başvuru GÖNDERME ucu (/v1/vitrin/basvuru) kamuya açık kalır."""
    monkeypatch.setattr(basvuru_service, "listele", lambda n=100: [{"id": "b1"}])
    c = TestClient(api_main.app)
    _rol("admin", "t1")
    assert c.get("/v1/vitrin/basvurular").status_code == 404
    assert c.post("/v1/vitrin/basvurular/b1/okundu").status_code == 404


_REQ = type("R", (), {"method": "GET"})()   # 26.10 Faz 5: gecerli_kullanici(request, authorization)


def _jeton(monkeypatch, **ek):
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    import datetime as dt
    g = {"sub": "u1", "tenant_id": "t1", "role": "admin", "exp": dt.datetime.utcnow() + dt.timedelta(hours=1)}
    g.update(ek)
    return "Bearer " + _jwt.encode(g, au._sir(), algorithm="HS256")


def test_gecerli_kullanici_surum_ve_durum(monkeypatch):
    durum = {"sv": 0, "aktif": True, "kiraci_durum": "active"}
    monkeypatch.setattr(au, "oturum_durumu", lambda u: dict(durum))
    # eski jeton (sv yok) sürüm 0'da geçerli — geriye uyumluluk
    assert gecerli_kullanici(_REQ, _jeton(monkeypatch))["sub"] == "u1"
    # sürüm eşleşiyor
    durum["sv"] = 3
    assert gecerli_kullanici(_REQ, _jeton(monkeypatch, sv=3))["role"] == "admin"
    # sürüm artmış (pasifleştirme/rol/parola) → 401
    with pytest.raises(Exception) as e:
        gecerli_kullanici(_REQ, _jeton(monkeypatch, sv=2))
    assert e.value.status_code == 401
    # pasif kullanıcı → 401
    durum.update(sv=3, aktif=False)
    with pytest.raises(Exception) as e:
        gecerli_kullanici(_REQ, _jeton(monkeypatch, sv=3))
    assert e.value.status_code == 401
    # askıdaki kiracı → 403
    durum.update(aktif=True, kiraci_durum="suspended")
    with pytest.raises(Exception) as e:
        gecerli_kullanici(_REQ, _jeton(monkeypatch, sv=3))
    assert e.value.status_code == 403
    # kullanıcı yok → 401
    monkeypatch.setattr(au, "oturum_durumu", lambda u: None)
    with pytest.raises(Exception) as e:
        gecerli_kullanici(_REQ, _jeton(monkeypatch, sv=3))
    assert e.value.status_code == 401


def test_oturum_durumu_onbellegi(monkeypatch):
    sayac = {"n": 0}

    class _S:
        def execute(self, _q, _p):
            sayac["n"] += 1

            class _R:
                oturum_surumu, aktif, status = 2, True, "active"
                role, totp_aktif, yonetici_2fa_zorunlu = "admin", False, False   # 26.10 Faz 6 alanları
            return type("X", (), {"first": lambda self: _R()})()

    class _B:
        def __enter__(self): return _S()
        def __exit__(self, *a): return False
    monkeypatch.setattr(au, "sistem_baglami", lambda: _B())
    au.oturum_onbellegi_dusur()
    assert au.oturum_durumu("u9") == {"sv": 2, "aktif": True, "kiraci_durum": "active", "iki_adim_kurulmali": False}
    au.oturum_durumu("u9"); au.oturum_durumu("u9")
    assert sayac["n"] == 1                       # 60 sn içinde tek sorgu
    au.oturum_onbellegi_dusur("u9"); au.oturum_durumu("u9")
    assert sayac["n"] == 2                       # düşürünce yeniden sorar


def test_askidaki_kiraci_giris_ve_tazeleme_403(monkeypatch):
    def _askida(*a, **k):
        raise au.KiraciAskida()
    monkeypatch.setattr(au, "giris", _askida)
    c = TestClient(api_main.app)
    assert c.post("/v1/auth/login", json={"email": "a@b.c", "sifre": "x" * 10}).status_code == 403
    monkeypatch.setattr(au, "oturum_yenile", _askida)
    _rol("admin")
    assert c.post("/v1/oturum/yenile").status_code == 403


def test_migration_metni():
    m = pathlib.Path("alembic/versions/v2479_faz0_guvenlik.py").read_text()
    assert 'down_revision = "v2338_iki_adim"' in m
    assert 'for tablo in ("report_stats", "report_log")' in m
    assert "ENABLE ROW LEVEL SECURITY" in m and "FORCE ROW LEVEL SECURITY" in m
    assert "CREATE POLICY p_{tablo} ON {tablo}" in m and "current_setting('app.tenant_id')::uuid" in m
    assert "oturum_surumu INTEGER NOT NULL DEFAULT 0" in m
    # kaynak kodda sürüm artırma noktaları
    src = pathlib.Path("src/pvquant/services/auth_service.py").read_text()
    assert src.count("oturum_surumu_artir(s,") >= 3        # rol/durum, parola değişimi, parola sıfırlama
    assert "oturum_surumu = oturum_surumu + 1" in pathlib.Path("src/pvquant/services/iki_adim_service.py").read_text()
