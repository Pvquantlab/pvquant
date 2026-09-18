"""v2.301 — gece işleri görünürlüğü: uç, işçi-durdu uyarısı, ayrıntı sızmazlığı."""
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import isler_service as js


def test_uc_ve_sizmazlik(monkeypatch):
    monkeypatch.setattr(js, "ozet", lambda t, saat=48: {
        "isler": [{"is": "Sabah tahmini", "zaman": "2026-09-08T02:00:00+00:00", "sure_sn": 42.0, "tamam": False}],
        "pencere_saat": 48, "gece_calisiyor": True, "son_gece_isi": "2026-09-08T02:00:00+00:00", "not": None})
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    try:
        j = TestClient(api_main.app).get("/v1/isler").json()
        assert j["isler"][0]["tamam"] is False
        assert "detail" not in j["isler"][0] and "hata" not in j["isler"][0]   # ayrıntı panele çıkmaz
    finally:
        api_main.app.dependency_overrides.clear()


def test_isim_haritasi_tam():
    """Zamanlayıcıya kayıtlı her iş operatör adıyla eşlenmiş olmalı — ham kod adı panele düşmesin."""
    import re
    src = open("apps/worker/main.py").read()
    kayitli = set(re.findall(r'_logla\("([a-z_]+)"', src))
    eksik = kayitli - set(js.ISIM_TR)
    assert not eksik, f"ISIM_TR eksik: {eksik}"


def test_acilis_yakalama_esigi(monkeypatch):
    """v2.336 — taze (son BAŞARILI iz <30s) izde tur koşulmaz, bayat/boş izde koşulur."""
    import datetime as dt
    import apps.worker.main as wm

    kosulan = []
    monkeypatch.setattr(wm, "tam_tur", lambda: kosulan.append(1))

    class _S:
        def __init__(self, son):
            self._son = son

        def execute(self, *a, **k):
            class _R:
                def __init__(self, v): self._v = v
                def scalar(self): return self._v
            return _R(self._son)

        def __enter__(self): return self

        def __exit__(self, *a): return False

    simdi = dt.datetime.now(dt.timezone.utc)
    monkeypatch.setattr(wm, "sistem_baglami", lambda: _S(simdi - dt.timedelta(hours=2)))
    wm.acilis_yakalama()
    assert kosulan == []                       # taze — dokunmadı

    monkeypatch.setattr(wm, "sistem_baglami", lambda: _S(simdi - dt.timedelta(hours=31)))
    wm.acilis_yakalama()
    monkeypatch.setattr(wm, "sistem_baglami", lambda: _S(None))
    wm.acilis_yakalama()
    assert kosulan == [1, 1]                   # bayat ve hiç-yok: birer tur
