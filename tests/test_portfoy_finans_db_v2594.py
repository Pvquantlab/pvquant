"""v2.594 (Faz 3 F3-G, DB) — portföy finansal etki servisi DSG portföyünde: santral FEM (anında) + F3-D perspektifleri; API ucu; fe.portfoy() kayıtlı sonuç + B13;
gece_portfoy finans kaydı; izolasyon."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import text
from test_portfoy_dsg_db_v2591 import dsg as _dsg

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import tenant_baglami
from pvquant.services import finansal_etki_service as fe
from pvquant.services import portfoy_finans_service as pfs

dsg = _dsg
BUGUN = date(2026, 9, 11)


def test_db_portfoy_finans_dsg_api_gece(dsg):
    tid, tid2, pid, tp, pl = dsg
    o = pfs.donem(tid, pid, "2026-09-10", bugun=BUGUN)
    assert o["durum"] == "ok" and o["santral"] == 3 and o["dsg_durum"] == "ok" and o["portfoy"]["tur"] == "dsg" and set(o["kaynaklar"].values()) == {"anında"}
    kod = {b["kod"]: b for b in o["bilesenler"]}
    assert o["toplam"]["tutar_tl"] is not None and set(o["toplam"]["giren"]) == {"satis_geliri", "dengesizlik", "kupst"} or "kupst" in o["toplam"]["eksik"]
    assert o["toplam_dsg"] is not None and "dengesizlik" not in o["toplam_dsg"]["giren"] and kod["dengesizlik_dsg"]["toplanir"] is False
    assert kod["sozlesmesel_dagilim"]["ad"].endswith("Sözleşmeye dayalı dağılım") and o["dsg"]["etiket"] == "Sözleşmeye dayalı dağılım" and len(o["dsg_santraller"]) == 3
    assert o["mwh"]["toplanan"]["santral"] == o["mwh"]["toplanan"]["santral"] and len(o["meta"]["uyelik_anlik"]) == 3 and o["meta"]["sozlesme_anlik"]
    assert kod["dengesizlik"]["nitelik"] == "senaryo" and o["toplam"]["nitelik"] == "senaryo"   # fiyat senaryo (test DB'de EPİAŞ yok)
    # kayıt yok → fe.son None; toplayıcı portföy → dsg_degil; ikinci kiracı → portfoy_yok
    assert pfs.donem(tid, tp, "2026-09-10", bugun=BUGUN)["durum"] == "uye_yok" and pfs.donem(tid2, pid, "2026-09-10", bugun=BUGUN)["durum"] == "portfoy_yok"   # toplayıcı portföyü üyesiz
    # fe.portfoy(): B13 — tum_santral alanı; kayıtlı santral sonucu kullanılır
    with tenant_baglami(tid) as s:
        plants = [dict(r._mapping) for r in s.execute(text("SELECT id, name, capacity_kwp, tz, lat, lon, params_json, archived FROM plants ORDER BY name"))]
    p0 = fe.ozet(tid, plants[0], "2026-09-10", bugun=BUGUN); fe.kaydet(tid, p0, plants[0]["id"])
    pf = fe.portfoy(tid, plants, "2026-09-10", bugun=BUGUN)
    assert pf["toplam"]["tum_santral"]["planlanan_mwh"] is not None and pf["santraller"][0]["kayitli"] is True and pf["santraller"][1]["kayitli"] is False
    assert fe.portfoy(tid, plants, "2026-09-10", bugun=BUGUN, taze=True)["santraller"][0]["kayitli"] is False
    o2 = pfs.donem(tid, pid, "2026-09-10", bugun=BUGUN)
    assert o2["kaynaklar"]["GES A"] == "kayıtlı" and o2["kayitli_santral"] == 1 and pfs.donem(tid, pid, "2026-09-10", bugun=BUGUN, taze=True)["kayitli_santral"] == 0
    # API
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/portfoyler/{pid}/finansal-etki?donem=2026-09-10&bugun=2026-09-11"); assert r.status_code == 200 and r.json()["toplam_dsg"] is not None
        assert c.get(f"/v1/portfoyler/{pid}/finansal-etki?donem=2026-13").status_code == 422 and c.get(f"/v1/portfoyler/{uuid.uuid4()}/finansal-etki").status_code == 404
        r = c.get("/v1/portfoy/finansal-etki?donem=2026-09-10"); assert r.status_code == 200 and "tum_santral" in r.json()["toplam"]
    finally:
        api_main.app.dependency_overrides.clear()
    # gece işi finans kaydı
    from apps.worker.main import gece_portfoy
    sonuc = gece_portfoy(bugun=BUGUN)
    assert "finans 2026-09-10" in sonuc and "HATA" not in sonuc
    with tenant_baglami(tid) as s:
        assert s.execute(text("SELECT count(*) FROM portfoy_sonuc WHERE portfoy_id = CAST(:p AS uuid) AND tur = 'finans'"), {"p": pid}).scalar() >= 1
