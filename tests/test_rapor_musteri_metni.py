"""19.11 canlı özellik testi (Bulgu 3) — PDF rapor 409'u müşteri yüzüne iç adsız iner; iç ayrıntı günlüğe."""
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import plant_service, report_service
from pvquant.services.report_html_service import RaporVerisiEksik, _zorunlu, musteri_rapor_hatasi

PLANT = "33333333-3333-3333-3333-333333333333"
IC_TERIM = ("ctx.", "worker", "B1/B5", "report_stats", "hourly", "ValueError")


class _Ctx:
    error_dist = None
    uninterrupted_days = 3


def test_zorunlu_tipli_hata_ic_ad_gunlukte_musteride_degil():
    try:
        _zorunlu(_Ctx(), "error_dist")
    except RaporVerisiEksik as e:
        assert isinstance(e, ValueError) and e.alan == "error_dist"
        assert "ctx.error_dist" in str(e) and "B1/B5" in str(e)   # günlük metni eski hâliyle (teşhis için)
        assert not any(t in e.musteri for t in IC_TERIM), e.musteri
        assert "ölçüm ve tahminin birlikte bulunduğu en az iki gün" in e.musteri and "Excel ve JSON" in e.musteri
    else:
        raise AssertionError("eksik alan hata vermedi")
    assert _zorunlu(_Ctx(), "uninterrupted_days") == 3


def test_musteri_rapor_hatasi_siniflari():
    assert musteri_rapor_hatasi(RaporVerisiEksik("uninterrupted_days")).startswith("PDF rapor üretilemedi. Kesintisiz ölçüm günü")
    assert musteri_rapor_hatasi(RaporVerisiEksik("bilinmeyen_alan")).startswith("PDF rapor üretilemedi. Gerekli bir istatistik")
    assert "Veri yükleme sayfasındaki «Hızlı tahminle devam et»" in musteri_rapor_hatasi(ValueError("rapor baglami kurulamadi — once tahmin uretin"))   # düğme VeriYukleme'de (inceleme)
    g = musteri_rapor_hatasi(ValueError("hourly boş — tipik gün türetilemedi"))
    assert "hourly" not in g and "günlüğüne" in g


def test_report_409_govdesi_musteri_metni(monkeypatch, capsys):
    """Canlıda Golden 33 için report?fmt=pdf gövdesi «worker alanı eksik: ctx.error_dist (bkz. B1/B5 kararı …)» idi."""
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": PLANT, "name": "PVDAQ Golden 33", "params_json": {}})
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"tenant_id": "t", "sub": "u", "role": "viewer"}
    try:
        c = TestClient(api_main.app)
        monkeypatch.setattr(report_service, "uret", lambda t, row, fmt: (_ for _ in ()).throw(RaporVerisiEksik("error_dist")))
        r = c.get(f"/v1/plants/{PLANT}/report?fmt=pdf")
        assert r.status_code == 409, r.text
        d = r.json()["detail"]
        assert not any(t in d for t in IC_TERIM), d
        assert d.startswith("PDF rapor üretilemedi. Hata dağılımı istatistiği")
        cik = capsys.readouterr().out
        assert "RAPOR uretilemedi" in cik and "ctx.error_dist" in cik and "fmt=pdf" in cik   # iç ayrıntı günlükte
        monkeypatch.setattr(report_service, "uret", lambda t, row, fmt: (_ for _ in ()).throw(ValueError("iklim çerçevesi tanınmadı — kolonlar: x")))
        r = c.get(f"/v1/plants/{PLANT}/report?fmt=xlsx")
        assert r.status_code == 409 and "iklim" not in r.json()["detail"] and "günlüğüne" in r.json()["detail"]
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)


def test_kaynak_pini_ham_str_409_yok():
    import inspect
    k = inspect.getsource(api_main.rapor_uret)
    assert "HTTPException(409, str(e))" not in k and "musteri_rapor_hatasi(e)" in k
