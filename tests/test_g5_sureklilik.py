"""G5-P1 / F1-14 (25.11.2026) — tahmin yayın sürekliliği: saf hüküm + kimliksiz /v1/sureklilik (200/503) + DB duman."""
import datetime as dt

from pvquant.services import sureklilik_service as sr

SIMDI = dt.datetime(2026, 11, 25, 9, 0, tzinfo=dt.timezone.utc)


def test_hukum_ok_bayat_yok_sinir():
    ok = sr.degerlendir(SIMDI - dt.timedelta(hours=5), SIMDI, 30, etkin_santral=4, bayat_santral=0)
    assert ok["ok"] and ok["durum"] == "ok" and ok["yas_saat"] == 5.0 and ok["esik_saat"] == 30.0 and ok["son_yayin"].startswith("2026-11-25T04:00:00")
    sinir = sr.degerlendir(SIMDI - dt.timedelta(hours=30), SIMDI, 30, etkin_santral=4, bayat_santral=0)
    assert sinir["ok"] and sinir["yas_saat"] == 30.0                          # eşit → henüz bayat değil
    bayat = sr.degerlendir(SIMDI - dt.timedelta(hours=94), SIMDI, 30, etkin_santral=4, bayat_santral=4)   # D-9 vakası
    assert not bayat["ok"] and bayat["durum"] == "bayat" and bayat["yas_saat"] == 94.0
    yok = sr.degerlendir(None, SIMDI, 30, etkin_santral=2)
    assert not yok["ok"] and yok["durum"] == "yok" and yok["yas_saat"] is None
    bos = sr.degerlendir(None, SIMDI, 30, etkin_santral=0)
    assert bos["ok"] and bos["durum"] == "santral_yok"                      # santral yoksa yanlış alarm yok
    # platform taze ama bir santral bayat → yine 503 (santral başına süreklilik)
    kismi = sr.degerlendir(SIMDI - dt.timedelta(hours=2), SIMDI, 30, etkin_santral=3, bayat_santral=1)
    assert not kismi["ok"] and kismi["durum"] == "bayat" and "1 etkin santral" in kismi["aciklama"]
    # tz'siz (naive) run_at UTC sayılır; gelecek tarihli koşu negatif yaş vermez
    assert sr.degerlendir(dt.datetime(2026, 11, 25, 8, 0), SIMDI, 30, 1, 0)["yas_saat"] == 1.0
    assert sr.degerlendir(SIMDI + dt.timedelta(hours=1), SIMDI, 30, 1, 0)["yas_saat"] == 0.0


def test_uc_200_ve_503_kimliksiz(monkeypatch):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    c = TestClient(api_main.app)
    monkeypatch.setattr(sr, "ozet", lambda: sr.degerlendir(SIMDI - dt.timedelta(hours=5), SIMDI, 30, 4, 0))
    r = c.get("/v1/sureklilik")
    assert r.status_code == 200 and r.json()["durum"] == "ok" and set(r.json()) >= {"yas_saat", "esik_saat", "etkin_santral"}
    assert "tenant" not in r.text and "plant_id" not in r.text                # kiracı verisi yok
    monkeypatch.setattr(sr, "ozet", lambda: sr.degerlendir(SIMDI - dt.timedelta(hours=94), SIMDI, 30, 4, 4))
    r = c.get("/v1/sureklilik")
    assert r.status_code == 503 and "94.0 sa önce" in r.json()["detail"] and "eşik 30 sa" in r.json()["detail"]
    monkeypatch.setattr(sr, "ozet", lambda: sr.degerlendir(None, SIMDI, 30, 2))
    assert c.get("/v1/sureklilik").status_code == 503

    def bozuk():
        raise RuntimeError("sentetik: db yok")
    monkeypatch.setattr(sr, "ozet", bozuk)
    r = c.get("/v1/sureklilik")
    assert r.status_code == 503 and "veritabanı" in r.json()["detail"] and "sentetik" not in r.text   # ayrıntı sızmaz


def test_db_duman_ozet_sozlesmesi():
    """Test DB varsa gerçek sorgu koşar (yazma yok); yoksa atlanır."""
    import pytest
    try:
        o = sr.ozet(simdi=SIMDI)
    except Exception as e:
        pytest.skip(f"test DB yok: {type(e).__name__}")
    assert set(o) >= {"durum", "ok", "son_yayin", "yas_saat", "esik_saat", "etkin_santral", "bayat_santral"}
    assert o["esik_saat"] == 30.0 and isinstance(o["etkin_santral"], int) and o["durum"] in {"ok", "bayat", "yok", "santral_yok"}
