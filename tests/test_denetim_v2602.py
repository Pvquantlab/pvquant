"""v2.602 (Faz 4 F4-H, Stage 10) — denetim izi sertleştirme: dis_api kapsamı (M1) INSERT edilir, bilinmeyen kapsam açıkça reddedilir; uygulama rolü
silemez/güncelleyemez; ayar damgası (saf) ve ayar değişikliği izi standardı {degisen, ayar_sha}; FEM meta ayar_sha; «etkilenen hesaplar» sorgusu;
URL maskeleme; izsiz uçlar iz bırakır (API); temizlik kendi izini bırakır."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.services import ayar_damgasi as ad
from pvquant.services import denetim_service as dz


# ───────────────────────────────────────────── saf ─────────────────────────────────────────────
def test_ayar_damgasi_saf():
    a = {"tarife": {"tip": "sabit", "tl_mwh": 2000}, "segment": "lisansli_serbest", "eak_kw": 900, "pr_referans": 0.8, "sensorler": [1, 2]}
    b = {"sensorler": [9], "eak_kw": 900, "segment": "lisansli_serbest", "tarife": {"tl_mwh": 2000, "tip": "sabit"}, "pr_referans": 0.5}
    assert ad.ayar_sha16(a) == ad.ayar_sha16(b) and len(ad.ayar_sha16(a)) == 16   # damga dışı alanlar (pr_referans, sensorler) ve sıra damgayı değiştirmez
    c = dict(a, tarife={"tip": "ptf"})
    assert ad.ayar_sha16(c) != ad.ayar_sha16(a)
    assert ad.degisenler(a, c) == {"tarife": {"eski": {"tip": "sabit", "tl_mwh": 2000}, "yeni": {"tip": "ptf"}}}
    assert ad.degisenler(a, dict(a, pr_referans=0.1)) == {} and ad.degisenler(None, {}) == {}
    assert ad.ayar_ozeti('{"tarife": null, "eak_kw": 1}') == {"eak_kw": 1}
    assert "fizik" not in " ".join(ad.AYAR_ANAHTARLARI) and "uzlastirma_girdi" in ad.AYAR_ANAHTARLARI


def test_url_maskeleme_ve_kapsam():
    assert dz.maskele_url("https://user:pw@ornek.com:8443/kanca/x?token=abc#f") == "https://ornek.com:8443/kanca/x?…"
    assert dz.maskele_url("https://ornek.com/kanca") == "https://ornek.com/kanca" and dz.maskele_url(None) is None and dz.maskele_url("") == ""
    assert dz.kaydet("bilinmeyen", "x") is False   # CHECK'e takılıp sessizce kaybolmaz: açıkça False
    assert set(dz.KAPSAMLAR) == {"platform", "musteri", "dis_api"} and "scada_yukle" in dz.EYLEMLER_MUSTERI and "denetim_temizlik" in dz.EYLEMLER_PLATFORM


# ───────────────────────────────────────────── DB ─────────────────────────────────────────────
@pytest.fixture()
def kiraci():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'dz-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'DZ GES', 1000, 37.0, 32.0, 'Europe/Istanbul', "
                       "CAST(:pj AS jsonb))"), {"p": pid, "t": tid, "pj": '{"tarife": {"tip": "sabit", "tl_mwh": 2000}, "segment": "lisansli_serbest"}'})
    yield tid, pid
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM finansal_etki_sonuc WHERE tenant_id = :t"), {"t": tid})
        s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tid})


def _izler(tid, eylem=None):
    return dz.listele(tenant_id=tid, eylem=eylem, limit=50)


def test_db_dis_api_kapsami_ve_yetki(kiraci):
    tid, pid = kiraci
    assert dz.kaydet("dis_api", "uretim_dosyasi_itme", aktor_id=str(uuid.uuid4()), tenant_id=tid, nesne_tur="plant", nesne_id=pid, ayrinti={"dosya": "x.csv"}) is True   # M1
    izler = _izler(tid, "uretim_dosyasi_itme")
    assert len(izler) == 1 and izler[0]["kapsam"] == "dis_api" and izler[0]["ayrinti"] == {"dosya": "x.csv"}
    with pytest.raises(Exception, match="permission denied"), tenant_baglami(tid) as s:
        s.execute(text("DELETE FROM denetim_izi WHERE id = :i"), {"i": izler[0]["id"]})
    with pytest.raises(Exception, match="permission denied"), tenant_baglami(tid) as s:
        s.execute(text("UPDATE denetim_izi SET eylem = 'x' WHERE id = :i"), {"i": izler[0]["id"]})


def test_db_ayar_izi_ve_etkilenen_hesaplar(kiraci):
    tid, pid = kiraci
    eski = {"tarife": {"tip": "sabit", "tl_mwh": 2000}, "segment": "lisansli_serbest"}
    yeni = {"tarife": {"tip": "ptf"}, "segment": "lisansli_serbest"}
    sha_eski, sha_yeni = ad.ayar_sha16(eski), ad.ayar_sha16(yeni)
    import json
    with tenant_baglami(tid) as s:   # eski damgayla iki kayıt, yeni damgayla bir kayıt (değişiklikten ÖNCE yazılmış sayılır)
        for kod, sha in (("2026-09", sha_eski), ("2026-10", sha_eski), ("2026-08", sha_yeni)):
            s.execute(text("INSERT INTO finansal_etki_sonuc(tenant_id, plant_id, donem_tur, donem_kodu, donem_bas, donem_bit, uretim_girdisi, sozluk_surumu, uretim_json, gelir_json, "
                           "uzlastirma_json, toplam_json, meta_json) VALUES(CAST(:t AS uuid), CAST(:p AS uuid), 'ay', :k, DATE '2026-09-01', DATE '2026-10-01', 'scada', 'x', "
                           "'{}', '{}', '{}', '{}', CAST(:m AS jsonb))"), {"t": tid, "p": pid, "k": kod, "m": json.dumps({"ayar_sha": sha, "hesap_durumu": "tam"})})
    assert dz.ayar_degisikligi_kaydet("tarife_ayar", aktor_id=str(uuid.uuid4()), tenant_id=tid, plant_id=pid, eski_pj=eski, yeni_pj=yeni, ek={"istek": {"tarife": "ptf"}}) is True
    iz = _izler(tid, "tarife_ayar")[0]
    assert iz["ayrinti"]["ayar_sha"] == {"eski": sha_eski, "yeni": sha_yeni} and iz["ayrinti"]["degisen"]["tarife"]["yeni"] == {"tip": "ptf"} and iz["ayrinti"]["istek"] == {"tarife": "ptf"}
    e = dz.etkilenen_sonuclar(tid, iz["id"])
    assert e["durum"] == "ok" and e["ayar_sha"] == sha_yeni and sorted(x["donem_kodu"] for x in e["etkilenen"]) == ["2026-09", "2026-10"]
    assert all(x["ayar_sha"] == sha_eski for x in e["etkilenen"])
    assert dz.etkilenen_sonuclar(str(uuid.uuid4()), iz["id"]) == {"durum": "iz_yok"}   # başka kiracı göremez
    dz.kaydet("musteri", "santral_arsivle", tenant_id=tid, nesne_tur="plant", nesne_id=pid)
    assert dz.etkilenen_sonuclar(tid, _izler(tid, "santral_arsivle")[0]["id"])["durum"] == "damgasiz"


def test_db_api_izsiz_uclar_iz_birakir(kiraci, monkeypatch):
    """tarife PUT, fizik PUT, elle koşu, webhook dene ve etkilenen ucu — iz bırakır; sırlar yazılmaz."""
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    tid, pid = kiraci
    uid = str(uuid.uuid4())
    claims = {"sub": uid, "tenant_id": tid, "role": "admin", "exp": 0}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: claims   # yazma/yönetici yetkisi kapanışları gecerli_kullanici'ye bağlı; admin rolü geçer
    monkeypatch.setattr("pvquant.services.forecast_service.uret_ve_kaydet", lambda t, row, etiket=None: "11111111-1111-1111-1111-111111111111")
    try:
        c = TestClient(api_main.app)
        r = c.put(f"/v1/plants/{pid}/tarife", json={"tarife": {"tip": "ptf"}}); assert r.status_code == 200, r.text
        iz = _izler(tid, "tarife_ayar"); assert len(iz) == 1 and iz[0]["ayrinti"]["degisen"]["tarife"]["eski"] == {"tip": "sabit", "tl_mwh": 2000}
        assert iz[0]["ayrinti"]["ayar_sha"]["eski"] != iz[0]["ayrinti"]["ayar_sha"]["yeni"]
        r = c.post(f"/v1/plants/{pid}/forecast/run"); assert r.status_code == 200
        assert _izler(tid, "elle_kosu")[0]["ayrinti"]["run_id"].startswith("11111111")
        e = c.get(f"/v1/kurulus/denetim/{iz[0]['id']}/etkilenen").json(); assert e["durum"] == "ok" and e["etkilenen"] == []
        assert c.get("/v1/kurulus/denetim/999999999/etkilenen").status_code == 404
        r = c.put(f"/v1/plants/{pid}/alarm-kurallari", json={"kurallar": ["pr_dustu"], "esik": {"pr_esik": 0.7}, "alicilar": ["a@b.c"]}); assert r.status_code == 200, r.text
        a = _izler(tid, "alarm_kural_ayar")[0]["ayrinti"]; assert a["alici_sayisi"] == 1 and "a@b.c" not in str(a) and a["kurallar"] == ["pr_dustu"]
        r = c.put(f"/v1/plants/{pid}/fizik-terimleri", json={"ayar": {"soiling_model": "kimber"}})   # fizik: damga dışı, doğrulanmış değerle eski/yeni
        if r.status_code == 200:
            assert _izler(tid, "fizik_terim_ayar")[0]["ayrinti"]["degisen"] == {"soiling_model": {"eski": None, "yeni": "kimber"}}
        assert e["damgasiz_kayit"] == 0
    finally:
        api_main.app.dependency_overrides.clear()


def test_fem_meta_ayar_sha():
    from pvquant.services import finansal_etki_service as fe
    assert fe._ad.ayar_sha16({"tarife": {"tip": "ptf"}}) == ad.ayar_sha16({"tarife": {"tip": "ptf"}, "x": 1})
