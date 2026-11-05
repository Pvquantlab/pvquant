"""05.11.2026 v2.543 (P9 depolama ve hibrit hazırlığı; IH-109/111/112/113): beyan doğrulama, 30 MW dengeleme birimi eşiği (DUY m.22),
emre amadelik eşiği %85/%80 (DUY m.81/A; ölçüm belirsiz), segment özeti ve API."""
from datetime import date

import pytest

from pvquant.ext.turkiye import depolama as dp


def test_dogrula_bos_ve_gecerli():
    assert dp.dogrula({})["depolama_gucu_mw"] is None and dp.dogrula({"depolama_gucu_mw": 0})["depolama_konfigurasyon"] is None
    d = dp.dogrula({"depolama_gucu_mw": "32.5", "depolama_kapasite_mwh": 65, "depolama_konfigurasyon": "ek1a", "depolama_uevcb": " 40X000000000456B ",
                    "depolama_kabul_tarihi": "2026-03-15T00:00:00", "depolama_butunlesik": 1})
    assert d == {"depolama_gucu_mw": 32.5, "depolama_kapasite_mwh": 65.0, "depolama_konfigurasyon": "ek1a", "depolama_uevcb": "40X000000000456B",
                 "depolama_kabul_tarihi": "2026-03-15", "depolama_butunlesik": True}
    with pytest.raises(ValueError, match="2000"):
        dp.dogrula({"depolama_gucu_mw": 5000})
    with pytest.raises(ValueError, match="konfigurasyon"):
        dp.dogrula({"depolama_gucu_mw": 10, "depolama_konfigurasyon": "ek9"})
    with pytest.raises(ValueError, match="YYYY-AA-GG"):
        dp.dogrula({"depolama_gucu_mw": 10, "depolama_kabul_tarihi": "15.03.2026"})
    with pytest.raises(ValueError, match="kapasite"):
        dp.dogrula({"depolama_gucu_mw": 10, "depolama_kapasite_mwh": -1})


def test_dengeleme_birimi_esigi_depolama_gucune_bagli():
    assert dp.dengeleme_birimi(None)["yukumlu"] is None
    assert dp.dengeleme_birimi(29.9)["yukumlu"] is False and "muaf" in dp.dengeleme_birimi(29.9)["not"]
    assert dp.dengeleme_birimi(30.0)["yukumlu"] is True and dp.dengeleme_birimi(30.0)["esik_mw"] == 30.0
    assert "m.22(2)(ç)" in dp.dengeleme_birimi(30.0)["dayanak"] and dp.dengeleme_birimi(30.0)["kesinlik"] == "dogrulandi"


def test_emre_amadelik_ilk_bes_yil_85_sonra_80_olcum_belirsiz():
    e = dp.emre_amadelik("2024-03-01", date(2026, 11, 5))
    assert e["oran"] == 0.85 and e["yil"] == 3 and e["gecis_tarihi"] == "2029-03-01" and "%80'e geçiş 01.03.2029" in e["not"]
    assert dp.emre_amadelik("2024-03-01", date(2029, 2, 28))["oran"] == 0.85
    assert dp.emre_amadelik("2024-03-01", date(2029, 3, 1))["oran"] == 0.80
    assert dp.emre_amadelik("2024-02-29", date(2029, 2, 28))["gecis_tarihi"] == "2029-02-28"      # 29 Şubat
    assert e["esik_kesinlik"] == "dogrulandi" and e["olcum_kesinlik"] == "belirsiz" and "bulunamadı" in e["olcum_notu"]
    assert "tamamı uzlaştırmada dikkate alınmaz" in e["sonuc"]
    b = dp.emre_amadelik(None, date(2026, 11, 5))
    assert b["oran"] is None and "girilmedi" in b["not"]


def test_ozet_ve_segment_bilgisi_depolama_blogu():
    from pvquant.services import dengesizlik_service as ds
    o = dp.ozet({"depolama_gucu_mw": 35, "depolama_konfigurasyon": "ek2", "depolama_uevcb": "40X1", "depolama_kabul_tarihi": "2026-01-10", "depolama_butunlesik": False}, date(2026, 11, 5))
    assert o["var"] and o["dengeleme_birimi"]["yukumlu"] and o["emre_amadelik"]["oran"] == 0.85 and o["konfigurasyon_etiketi"].startswith("EK-2")
    assert o["smf_cozunurluk"]["deger"] == "saatlik" and o["smf_cozunurluk"]["kesinlik"] == "belirsiz" and "125,00" in o["yekdem_notu"] and "m.21(8)" in o["uevcb_notu"]
    bos = dp.ozet({}, date(2026, 11, 5))
    assert bos["var"] is False and bos["emre_amadelik"] is None and bos["dengeleme_birimi"]["yukumlu"] is None
    s = ds.segment_bilgisi({"segment": "lisansli_serbest", "depolama_gucu_mw": 12})
    assert s["depolama"]["var"] and s["depolama"]["dengeleme_birimi"]["yukumlu"] is False
    assert ds.segment_bilgisi({})["depolama"]["var"] is False


def test_dayanak_bloklari_rg_kunyeli():
    assert len(dp.DAYANAKLAR) == 7 and all("RG " in d or "bulunamadı" in d for d in dp.DAYANAKLAR) and "RG " in dp.DAYANAK_KUNYELERI
    from pvquant.ext.turkiye import kunye
    assert "31479" in kunye.kunye("DEPOLAMA_YON") and "33122" in kunye.kunye("DEPOLAMA_YON")


PLANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def istemci(monkeypatch):
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    durum = {"pj": {"segment": "lisansli_serbest"}}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "params_json": dict(durum["pj"])})
    def _birlestir(t, p, **an):
        durum["pj"] = {**durum["pj"], **an}; return durum["pj"]
    monkeypatch.setattr(plant_service, "params_birlestir", _birlestir)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    for r in api_main.app.routes:
        if getattr(r, "path", "") == "/v1/plants/{plant_id}/segment" and "PUT" in getattr(r, "methods", set()):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_segment_put_depolama_ve_get(istemci):
    r = istemci.put(f"/v1/plants/{PLANT}/segment", json={"segment": "lisansli_serbest", "depolama": {"depolama_gucu_mw": 40, "depolama_konfigurasyon": "ek1b", "depolama_kabul_tarihi": "2025-06-01"}})
    assert r.status_code == 200, r.text
    j = r.json(); assert j["params_json"]["depolama_gucu_mw"] == 40 and j["depolama"]["dengeleme_birimi"]["yukumlu"] is True and j["depolama"]["emre_amadelik"]["oran"] == 0.85
    g = istemci.get(f"/v1/plants/{PLANT}/depolama"); assert g.status_code == 200
    assert g.json()["var"] and g.json()["konfigurasyon"] == "ek1b" and len(g.json()["dayanaklar"]) == 7 and g.json()["smf_cozunurluk"]["deger"] == "saatlik"
    assert istemci.put(f"/v1/plants/{PLANT}/segment", json={"segment": "lisansli_serbest", "depolama": {"depolama_gucu_mw": 10, "depolama_konfigurasyon": "x"}}).status_code == 422
    r = istemci.put(f"/v1/plants/{PLANT}/segment", json={"segment": "lisansli_serbest", "depolama": {"depolama_gucu_mw": None}})
    assert r.status_code == 200 and r.json()["depolama"]["var"] is False
