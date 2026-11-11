"""v2.583 (Faz 2 F2-E, Stage 2 meta / Stage 6 geçmiş) — finansal_etki_sonuc yalnız ekleme: kaydet/son/gecmis, meta içeriği, senaryo kipi (kaydet reddeder,
EDT/KÜPST senaryo damgası), kiracı izolasyonu (RLS), portföy, API uçları (son kayıt / taze / 422 / 404 / geçmiş / senaryo / portföy), gece işi (ölçüm yok → atlandı)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import finansal_etki_service as fe
from tests.test_finansal_etki_v2580 import santral as _santral

santral = _santral   # pytest fixture'ı bu modülde ad olarak tanıtır (noqa'sız; ruff --fix içe aktarmayı silmesin)

BUGUN = date(2026, 9, 11)


def test_db_kaydet_son_gecmis_senaryo_izolasyon_portfoy_api(santral, monkeypatch):
    tid, plant = santral
    o = fe.ozet(tid, plant, "2026-09-05", bugun=BUGUN)
    m = o["meta"]
    assert o["kayitli"] is False and m["sozluk_surumu"] and m["donem"]["kod"] == "2026-09-05" and m["uretim_girdisi"] == "scada" and m["senaryo"] is None
    assert m["tarife"] == {"tip": "sabit", "sha": m["tarife"]["sha"]} and len(m["tarife"]["sha"]) == 16 and m["program_kaynak"]["kaynak"] == "oneri"
    assert m["fiyat"]["epias_saat"] + m["fiyat"]["senaryo_saat"] == 23 and "isaret" in m and m["pozisyon"]["kaynak"] == "program"
    # kaydet / son / gecmis (yalnız ekleme)
    kid = fe.kaydet(tid, o, plant["id"])
    s1 = fe.son(tid, plant["id"], "2026-09-05")
    assert s1 and s1["id"] == kid and s1["kayitli"] is True and s1["toplam"]["tutar_tl"] == o["toplam"]["tutar_tl"] and s1["uretim"]["gerceklesen"]["saat"] == 23
    assert fe.son(tid, plant["id"], "2026-09-05", uretim="sayac") is None and fe.son(tid, plant["id"], "2026-09-06") is None
    assert fe.son(tid, plant["id"], "2026-09-05", azami_yas_saat=0.0) is None   # bayat
    kid2 = fe.kaydet(tid, o, plant["id"])
    g = fe.gecmis(tid, plant["id"], "2026-09-05")
    assert [x["id"] for x in g] == [kid2, kid] and g[0]["varsayimlar"]["tarife"]["tip"] == "sabit" and g[0]["varsayimlar"]["kural_surumu"] and g[0]["toplam"]["giren"][0] == "satis_geliri"
    with sistem_baglami() as c:
        assert c.execute(text("SELECT count(*) FROM finansal_etki_sonuc WHERE tenant_id=:t"), {"t": tid}).scalar() == 2
    # senaryo: EDT/KÜPST senaryo damgası, kaydet reddeder, sabit pozisyon
    sn = fe.senaryo(tid, plant, "2026-09-05", "uretim", bugun=BUGUN)
    kod = {b["kod"]: b for b in sn["bilesenler"]}
    assert sn["meta"]["senaryo"]["pozisyon"] == {"kaynak": "uretim", "sabit_mwh": None} and "üretildiği kadar" in sn["meta"]["senaryo"]["etiket"]
    assert kod["dengesizlik"]["nitelik"] == "senaryo" and any("Senaryo hesabı" in n for n in kod["dengesizlik"]["notlar"]) and kod["satis_geliri"]["nitelik"] == "sozlesme_tahmini"
    assert abs(kod["dengesizlik"]["tutar_tl"]) < 1e-6   # üretildiği kadar satış: EDM = 0
    with pytest.raises(ValueError):
        fe.kaydet(tid, sn, plant["id"])
    sb = fe.senaryo(tid, plant, "2026-09-05", "sabit", sabit_mwh=0.3, bugun=BUGUN)
    assert sb["meta"]["pozisyon"] == {"kaynak": "sabit", "sabit_mwh": 0.3} and sb["meta"]["senaryo"]["etiket"].startswith("sabit 0.3")
    # kiracı izolasyonu: ikinci kiracı hiçbir satırı görmez
    tid2 = str(uuid.uuid4())
    with sistem_baglami() as c:
        c.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'fe-test-2', 'active')"), {"t": tid2})
    try:
        assert fe.son(tid2, plant["id"], "2026-09-05") is None and fe.gecmis(tid2, plant["id"], "2026-09-05") == []
        with tenant_baglami(tid2) as c:
            assert c.execute(text("SELECT count(*) FROM finansal_etki_sonuc")).scalar() == 0
        with tenant_baglami(tid) as c:
            assert c.execute(text("SELECT count(*) FROM finansal_etki_sonuc")).scalar() == 2
    finally:
        with sistem_baglami() as c:
            c.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid2})
    # portföy
    pf = fe.portfoy(tid, [plant], "2026-09-05", bugun=BUGUN)
    sat = pf["santraller"][0]
    assert sat["ad"] == "FE GES" and sat["toplam"]["tutar_tl"] == o["toplam"]["tutar_tl"] and pf["toplam"]["toplanan_santral"] == 1 and pf["toplam"]["tutar_tl"] == o["toplam"]["tutar_tl"]
    assert pf["toplam"]["planlanan_mwh"] == o["uretim"]["planlanan"]["mwh"] and pf["toplam"]["nitelik"] == o["toplam"]["nitelik"] and sat["dengesizlik"]["toplanir"] is True
    pf2 = fe.portfoy(tid, [plant, {"id": str(uuid.uuid4()), "name": "yok", "tz": "Europe/Istanbul", "params_json": {}}], "2026-09-05", bugun=BUGUN)
    assert len(pf2["santraller"]) == 2 and pf2["toplam"]["toplanan_santral"] >= 1
    # API
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2026-09-05"); assert r.status_code == 200 and r.json()["kayitli"] is True and r.json()["id"] == kid2
        with monkeypatch.context() as mp:   # anında hesap yolu: ozet taklidi yalnız bu iki çağrı için (senaryo gerçek ozet'i kullanır)
            mp.setattr(fe, "ozet", lambda *a, **k: o)
            r = c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2026-09-05&taze=1"); assert r.status_code == 200 and r.json()["kayitli"] is False
            r = c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2026-09-06"); assert r.status_code == 200 and r.json()["kayitli"] is False   # kayıt yok → anında
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2026-13").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2027-01").status_code == 422   # gelecek dönem
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2026-09-05&uretim=x").status_code == 422
        assert c.get(f"/v1/plants/{uuid.uuid4()}/finansal-etki").status_code == 404
        r = c.get(f"/v1/plants/{plant['id']}/finansal-etki/gecmis?donem=2026-09-05"); assert r.status_code == 200 and len(r.json()["surumler"]) == 2
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki/gecmis?donem=2026-09-05&n=0").status_code == 422
        r = c.get(f"/v1/plants/{plant['id']}/finansal-etki/senaryo?donem=2026-09-05&pozisyon=uretim"); assert r.status_code == 200 and r.json()["meta"]["senaryo"]["pozisyon"]["kaynak"] == "uretim"
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki/senaryo?donem=2026-09-05&pozisyon=x").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki/senaryo?donem=2026-09-05&pozisyon=sabit").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/finansal-etki/senaryo?donem=2026-09-05&pozisyon=sabit&sabit_mwh=5").status_code == 422   # kurulu güç 1 MW üstü
        r = c.get(f"/v1/plants/{plant['id']}/finansal-etki/senaryo?donem=2026-09-05&pozisyon=sabit&sabit_mwh=0.3"); assert r.status_code == 200
        r = c.get("/v1/portfoy/finansal-etki?donem=2026-09-05"); assert r.status_code == 200 and r.json()["toplam"]["santral_sayisi"] >= 1
        assert c.get("/v1/portfoy/finansal-etki?donem=abc").status_code == 422
    finally:
        api_main.app.dependency_overrides.clear()
    with sistem_baglami() as c:   # API ve senaryo çağrıları yeni satır yazmadı (yalnız gece işi/kaydet yazar)
        assert c.execute(text("SELECT count(*) FROM finansal_etki_sonuc WHERE tenant_id=:t"), {"t": tid}).scalar() == 2


def test_db_gece_isi_olcum_yoksa_atlar(santral):
    tid, plant = santral
    from apps.worker.main import gece_finansal_etki
    p = {**plant, "tenant_id": tid}
    r = gece_finansal_etki(p)   # bugün gerçek tarih (Kasım 2026): fixture Eylül'de → ölçüm yok, iki dönem de atlanır
    assert r.count("atlandı") == 2
    with sistem_baglami() as c:
        assert c.execute(text("SELECT count(*) FROM finansal_etki_sonuc WHERE tenant_id=:t"), {"t": tid}).scalar() == 0


def test_izleme_ve_ad_sozlugu():
    from pvquant.services import isler_service, sistem_service
    assert any(i[0] == "gece_finansal_etki" for i in sistem_service.IZLENEN_ISLER) and isler_service.ISIM_TR["gece_finansal_etki"] == "Finansal etki"


def test_gocun_basi():
    from pathlib import Path
    g = Path(__file__).resolve().parents[1] / "alembic/versions/v2583_finansal_etki_sonuc.py"
    s = g.read_text(encoding="utf-8")
    assert 'down_revision = "v2574_dogrulama_sonuc"' in s and "GRANT SELECT, INSERT ON finansal_etki_sonuc TO pvq_app" in s and "FORCE ROW LEVEL SECURITY" in s
    assert "UPDATE" not in s.split("def upgrade")[1].split("def downgrade")[0].replace("DEFAULT", "")
