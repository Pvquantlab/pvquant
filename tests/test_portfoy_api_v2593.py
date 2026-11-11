"""v2.593 (Faz 3 F3-F, DB) — portföy API ve gece işi: viewer yalnız okur (POST/PUT 403), editor kuruluş/portföy/üyelik yazar ama sözleşme yazamaz (403) ve okur,
admin sözleşme yazar, viewer sözleşme okuyamaz (403); doğrulama 422, bulunamadı 404, ikinci kiracı 404; hesap uçları (tahmin/kapsama/sapma/risk/dsg/revizyon) 200;
gece_portfoy (bugün = fixture günü) portfoy_sonuc + dogrulama_sonuc yazar, gecmis uçları kayıtları döner; API yazma uçları denetim izine düşer."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import text
from test_portfoy_sapma_db_v2590 import portfoy as _portfoy

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import sistem_baglami, tenant_baglami

portfoy = _portfoy
BUGUN = date(2026, 9, 11)


def _rol(tid, rol):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": tid, "role": rol, "exp": 0}
    return TestClient(api_main.app)


def test_db_api_yetki_dogrulama_ve_gece_isi(portfoy):
    tid, tid2, pid, pl = portfoy
    try:
        v = _rol(tid, "viewer")
        assert v.get("/v1/portfoyler").status_code == 200 and [p["ad"] for p in v.get("/v1/portfoyler").json()["portfoyler"]] == ["Portföy S"]
        assert v.get(f"/v1/portfoyler/{pid}").json()["tur"] == "ozel" and len(v.get(f"/v1/portfoyler/{pid}/uyeler?tum=1").json()["uyeler"]) == 3
        assert v.post("/v1/kuruluslar", json={"ad": "X", "tur": "diger"}).status_code == 403 and v.post("/v1/portfoyler", json={"ad": "Y", "tur": "ozel", "gecerli_bas": "2026-01-01"}).status_code == 403
        assert v.post(f"/v1/portfoyler/{pid}/uyeler", json={"plant_id": pl["A"], "gecerli_bas": "2026-01-01"}).status_code == 403 and v.get("/v1/sozlesmeler").status_code == 403
        assert v.get(f"/v1/portfoyler/{uuid.uuid4()}").status_code == 404 and v.get("/v1/portfoyler?tarih=2026-13-01").status_code == 422
        # editor: kuruluş + DSG portföyü + üyelik; sözleşme yazamaz, okur
        e = _rol(tid, "editor")
        k = e.post("/v1/kuruluslar", json={"ad": "DSG Yön.", "tur": "dsg_yoneticisi"}); assert k.status_code == 200
        assert e.post("/v1/kuruluslar", json={"ad": "DSG Yön.", "tur": "diger"}).status_code == 422 and e.post("/v1/kuruluslar", json={"ad": "Z", "tur": "yok"}).status_code == 422
        assert e.put(f"/v1/kuruluslar/{k.json()['id']}", json={"notlar": "n"}).json()["notlar"] == "n" and e.put(f"/v1/kuruluslar/{uuid.uuid4()}", json={"notlar": "n"}).status_code == 404
        d = e.post("/v1/portfoyler", json={"ad": "DSG-API", "tur": "dsg", "gecerli_bas": "2026-01-01", "dsg": {"dsg_kodu": "DSG-API", "yonetici_kurulus_id": k.json()["id"]}})
        assert d.status_code == 200 and e.post("/v1/portfoyler", json={"ad": "DSG-2", "tur": "dsg", "gecerli_bas": "2026-01-01"}).status_code == 422
        did = d.json()["id"]
        u = e.post(f"/v1/portfoyler/{did}/uyeler", json={"plant_id": pl["A"], "gecerli_bas": "2026-01-01"}); assert u.status_code == 200
        assert e.post(f"/v1/portfoyler/{did}/uyeler", json={"plant_id": pl["A"], "gecerli_bas": "2026-03-01"}).status_code == 422   # çakışma
        assert e.post(f"/v1/portfoyler/{did}/uyeler", json={"plant_id": str(uuid.uuid4()), "gecerli_bas": "2026-03-01"}).status_code == 404
        assert e.post(f"/v1/portfoyler/{did}/uyeler", json={"plant_id": pl["B"], "gecerli_bas": "2026-01-01", "dogrulama": "belgeli"}).status_code == 422   # belge adı yok
        assert e.post(f"/v1/portfoyler/{did}/uyeler", json={"plant_id": pl["B"], "gecerli_bas": "2026-01-01", "dogrulama": "dogrulandi", "belge_adi": "b.pdf"}).status_code == 200
        assert e.put(f"/v1/portfoyler/{did}/uyeler/{u.json()['id']}", json={"notlar": "x"}).json()["notlar"] == "x"
        assert e.put(f"/v1/portfoyler/{did}", json={"notlar": "güncel", "dsg_kodu": "DSG-API-2"}).json()["dsg_kodu"] == "DSG-API-2"
        assert e.post("/v1/sozlesmeler", json={"tur": "dsg_uyelik", "gecerli_bas": "2026-01-01", "portfoy_id": did, "dagitim_yontemi": "esit"}).status_code == 403
        assert e.get("/v1/sozlesmeler").status_code == 200 and e.get("/v1/sozlesmeler").json()["sozlesmeler"] == []
        # admin: sözleşme
        a = _rol(tid, "admin")
        z = a.post("/v1/sozlesmeler", json={"tur": "dsg_uyelik", "gecerli_bas": "2026-01-01", "portfoy_id": did, "dagitim_yontemi": "sabit_pay",
                                            "parametreler": {"paylar": {"GES A": 0.5, "GES B": 0.5}}, "dogrulama": "dogrulandi", "belge_adi": "s.pdf"})
        assert z.status_code == 200 and a.post("/v1/sozlesmeler", json={"tur": "dsg_uyelik", "gecerli_bas": "2026-01-01", "portfoy_id": did, "dagitim_yontemi": "sabit_pay",
                                                                        "parametreler": {"paylar": {"GES A": 0.9}}}).status_code == 422
        assert a.put(f"/v1/sozlesmeler/{z.json()['id']}", json={"notlar": "ok"}).json()["notlar"] == "ok" and a.get(f"/v1/sozlesmeler?portfoy_id={did}&tarih=2026-09-10").json()["sozlesmeler"][0]["dagilim_etiketi"] == "Sözleşmeye dayalı dağılım"
        # hesap uçları (viewer okur)
        r = v.get(f"/v1/portfoyler/{pid}/tahmin?gun=2&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["durum"] == "ok" and r.json()["santral"] == 3
        assert v.get(f"/v1/portfoyler/{pid}/tahmin?kural=x").status_code == 422 and v.get(f"/v1/portfoyler/{pid}/tahmin?gun=0").status_code == 422
        r = v.get(f"/v1/portfoyler/{pid}/sapma?donem=2026-09-10&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["ozet"]["saat"] == 24
        assert v.get(f"/v1/portfoyler/{pid}/sapma?donem=2026-13").status_code == 422 and v.get(f"/v1/portfoyler/{pid}/sapma?uretim=x").status_code == 422
        r = v.get(f"/v1/portfoyler/{pid}/risk?gun=2&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["risk"]["etiket"] in ("tahmini", "dogrulanmis", "eksik")
        r = v.get(f"/v1/portfoyler/{pid}/dsg?donem=2026-09-10&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["durum"] == "dsg_degil"
        r = v.get(f"/v1/portfoyler/{did}/dsg?donem=2026-09-10&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["durum"] == "ok" and r.json()["perspektifler"]["sozlesmesel"]["etiket"] == "Sözleşmeye dayalı dağılım"
        assert v.get(f"/v1/portfoyler/{did}/dsg?anahtar=yok").status_code == 422
        r = v.get(f"/v1/portfoyler/{pid}/revizyon?hedef=yarin&simdi=2026-09-11T14:20:00%2B03:00"); assert r.status_code == 200 and r.json()["oneriler"] and r.json()["hedef"] == "yarin"
        assert v.get(f"/v1/portfoyler/{pid}/revizyon?hedef=x").status_code == 422 and v.get(f"/v1/portfoyler/{pid}/revizyon?simdi=abc").status_code == 422
        r = v.get(f"/v1/portfoyler/{pid}/kapsama?taze=1&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["durum"] == "ok" and r.json()["metrik"]["n_gun"] >= 7
        assert v.get(f"/v1/portfoyler/{pid}/kapsama?gun=3").status_code == 422 and v.get(f"/v1/portfoyler/{pid}/gecmis").json()["kayitlar"] == []
        assert v.get(f"/v1/portfoyler/{pid}/gecmis?tur=yok").status_code == 422
        # ikinci kiracı hiçbir şey görmez
        o = _rol(tid2, "admin")
        assert o.get("/v1/portfoyler").json()["portfoyler"] == [] and o.get(f"/v1/portfoyler/{pid}").status_code == 404 and o.get(f"/v1/portfoyler/{pid}/sapma").status_code == 404
        assert o.get(f"/v1/portfoyler/{did}/dsg").status_code == 404 and o.get("/v1/sozlesmeler").json()["sozlesmeler"] == [] and o.get(f"/v1/portfoyler/{pid}/gecmis").status_code == 404
        # gece işi (fixture günü) → kayıtlar (yetki geçersiz kılması küreseldir: görüntüleyici istemci yeniden kurulur)
        v = _rol(tid, "viewer")
        from apps.worker.main import gece_portfoy
        sonuc = gece_portfoy(bugun=BUGUN)
        assert "Portföy S" in sonuc and "DSG-API" in sonuc and "HATA" not in sonuc and "kapsama" in sonuc and "tahmin" in sonuc
        with tenant_baglami(tid) as s:
            assert s.execute(text("SELECT count(*) FROM portfoy_sonuc WHERE portfoy_id = CAST(:p AS uuid)"), {"p": pid}).scalar() >= 3   # sapma dün + ay, tahmin
            assert s.execute(text("SELECT count(*) FROM portfoy_sonuc WHERE portfoy_id = CAST(:p AS uuid) AND tur = 'dsg'"), {"p": did}).scalar() >= 1
            assert s.execute(text("SELECT count(*) FROM dogrulama_sonuc WHERE plant_id IS NULL AND kural = 'portfoy_gun_oncesi'")).scalar() == 2
        g = v.get(f"/v1/portfoyler/{pid}/gecmis?tur=sapma").json()["kayitlar"]
        assert g and g[0]["donem_kodu"] in ("2026-09-10", "2026-09") and "uyelik_anlik" in g[0]["meta_json"]
        kayit = v.get(f"/v1/portfoyler/{pid}/gecmis/{g[0]['id']}").json()
        assert kayit["kayitli"] and kayit["sonuc"]["durum"] == "ok" and v.get(f"/v1/portfoyler/{pid}/gecmis/{uuid.uuid4()}").status_code == 404
        k2 = v.get(f"/v1/portfoyler/{pid}/kapsama"); assert k2.status_code == 200 and k2.json()["kayitli"] is True
        with sistem_baglami() as s:
            ey = {r[0] for r in s.execute(text("SELECT eylem FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})}
        assert {"kurulus_ekle", "portfoy_ekle", "uyelik_ekle", "uyelik_guncelle", "portfoy_guncelle", "sozlesme_ekle", "sozlesme_guncelle"} <= ey
    finally:
        api_main.app.dependency_overrides.clear()
