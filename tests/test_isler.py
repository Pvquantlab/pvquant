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
    """v2.336/v2.339 — hüküm bayat_isler'den gelir: boşsa tur koşulmaz, doluysa koşulur."""
    import apps.worker.main as wm
    from pvquant.services import isler_service as js

    kosulan = []
    monkeypatch.setattr(wm, "tam_tur", lambda: kosulan.append(1))

    monkeypatch.setattr(js, "bayat_isler", lambda saat=30, tenant_id=None: [])
    wm.acilis_yakalama()
    assert kosulan == []                       # taze — dokunmadı

    monkeypatch.setattr(js, "bayat_isler", lambda saat=30, tenant_id=None: ["sabah_tahmin"])
    wm.acilis_yakalama()
    assert kosulan == [1]                      # tek bir iş bile bayatsa tur koşar


def test_bayat_isler_is_bazinda(monkeypatch):
    """v2.339 — ASIL HATA: 'grubun biri koştu' ölçütü bayat işi maskeliyordu.
    gece_skill taze ama sabah_tahmin 10 gün eski ise sistem BAYAT sayılmalı."""
    import datetime as dt
    from pvquant.services import isler_service as js

    simdi = dt.datetime.now(dt.timezone.utc)

    class _R:
        def __init__(self, job, son): self.job, self.son = job, son

    def kur(kayitlar):
        class _S:
            def execute(self, *a, **k):
                class _Q:
                    def all(self_): return kayitlar
                return _Q()
            def __enter__(self): return self
            def __exit__(self, *a): return False
        import pvquant.db as _db
        monkeypatch.setattr(_db, "sistem_baglami", lambda: _S())

    # hepsi taze → boş liste
    kur([_R(j, simdi - dt.timedelta(hours=2)) for j in js.URETEN_ISLER])
    assert js.bayat_isler(30) == []

    # gece_skill taze ama sabah_tahmin 10 gün eski → SADECE o bayat sayılır
    kur([_R("gece_skill", simdi - dt.timedelta(hours=1)),
         _R("gunluk_beklenti", simdi - dt.timedelta(hours=1)),
         _R("sabah_tahmin", simdi - dt.timedelta(days=10))])
    assert js.bayat_isler(30) == ["sabah_tahmin"]

    # hiç kaydı olmayan iş de bayattır
    kur([_R("gece_skill", simdi - dt.timedelta(hours=1))])
    assert set(js.bayat_isler(30)) == {"sabah_tahmin", "gunluk_beklenti"}

    # gece_meteo ölçüte GİRMEZ (girdi adımı; ağ hatası turu tetiklemesin)
    assert "gece_meteo" not in js.URETEN_ISLER


def test_acilis_yedek_esigi(monkeypatch):
    """v2.339 — yedek 24 saatten eskiyse açılışta alınır, tazeyse alınmaz."""
    import datetime as dt
    import apps.worker.main as wm

    alindi = []
    monkeypatch.setattr(wm, "gece_yedek", lambda: alindi.append(1))

    class _S:
        def __init__(self, son): self._son = son
        def execute(self, *a, **k):
            class _R:
                def __init__(self, v): self._v = v
                def scalar(self): return self._v
            return _R(self._son)
        def __enter__(self): return self
        def __exit__(self, *a): return False

    simdi = dt.datetime.now(dt.timezone.utc)
    monkeypatch.setattr(wm, "sistem_baglami", lambda: _S(simdi - dt.timedelta(hours=3)))
    wm.acilis_yedek()
    assert alindi == []                                  # taze — alınmadı

    monkeypatch.setattr(wm, "sistem_baglami", lambda: _S(simdi - dt.timedelta(hours=25)))
    wm.acilis_yedek()
    monkeypatch.setattr(wm, "sistem_baglami", lambda: _S(None))
    wm.acilis_yedek()
    assert alindi == [1, 1]                              # eski ve hiç-yok: birer yedek
