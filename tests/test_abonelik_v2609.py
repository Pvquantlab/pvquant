"""v2.609 (Faz 6 F6-A) — abonelik / hak katmanı: saf kurallar (durum türetme, modül birleştirme, kota durumu), göç tohumu = servis sözlüğü,
DB (varsayılan satır, haklar, senkron, RLS izolasyonu, yalnız-ekleme geçmiş), uçlar (müşteri görünümü sözleşme notunu sızdırmaz; platform 404)."""
from __future__ import annotations

import datetime as dt
import importlib.util
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.services import abonelik_service as ab
from pvquant.services import yetki_service as ys

KOK = Path(__file__).resolve().parents[1]
BUGUN = dt.date(2026, 11, 13)


# ----------------------------------------------------------------------------------------------------------- saf
def test_durum_turet_tablosu():
    f = ys.durum_turet
    assert f("standart", "suspended", {"durum": "aktif"}, BUGUN) == "askida"                       # status her şeyi ezer
    assert f("standart", "active", {"durum": "feshedildi"}, BUGUN) == "feshedildi"                  # yapışkan
    assert f("pilot", "active", {"durum": "sona_erdi"}, BUGUN) == "sona_erdi"
    assert f("pilot", "active", {"durum": "pilot", "pilot_bitis": None}, BUGUN) == "pilot"
    assert f("pilot", "active", {"durum": "pilot", "pilot_bitis": BUGUN}, BUGUN) == "pilot"           # bitiş günü dâhil
    assert f("pilot", "active", {"durum": "pilot", "pilot_bitis": BUGUN - dt.timedelta(days=1)}, BUGUN) == "sona_erdi"
    assert f("standart", "active", {"durum": "aktif", "bitis": None}, BUGUN) == "aktif"
    assert f("standart", "active", {"durum": "aktif", "bitis": BUGUN + dt.timedelta(days=31)}, BUGUN) == "aktif"
    assert f("standart", "active", {"durum": "aktif", "bitis": BUGUN + dt.timedelta(days=30)}, BUGUN) == "sona_eriyor"
    assert f("standart", "active", {"durum": "aktif", "bitis": BUGUN}, BUGUN) == "sona_eriyor"
    assert f("standart", "active", {"durum": "aktif", "bitis": BUGUN - dt.timedelta(days=1)}, BUGUN) == "yenileme_bekliyor"
    assert f("kurumsal", "active", None, BUGUN) == "aktif"                                           # kayıt yok: tenants'tan
    assert f("standart", "active", {"durum": "askida", "bitis": None}, BUGUN) == "aktif"              # status active ise askıdan çıkar


def test_moduller_birlestir_ve_sozluk():
    pm = {"tahmin": {"dahil": True, "sinir": None}, "dis_api": {"dahil": True, "sinir": {"kapsamlar": "oku"}}}
    m = ys.moduller_birlestir(pm, ek=["finansal_etki"], cikar=["dis_api"])
    assert m["tahmin"]["dahil"] and m["tahmin"]["kaynak"] == "plan"
    assert m["finansal_etki"]["dahil"] and m["finansal_etki"]["kaynak"] == "ek"
    assert not m["dis_api"]["dahil"] and m["dis_api"]["kaynak"] == "cikar" and m["dis_api"]["sinir"] == {"kapsamlar": "oku"}
    assert not m["portfoy_dsg"]["dahil"] and m["portfoy_dsg"]["kaynak"] == "yok"
    assert m["santral_yetki"]["durum"] == "gelistirmede" and m["santral_yetki"]["durum_etiketi"] == "geliştirmede"
    assert set(m) == set(ys.MODULLER) and all("ad" in v for v in m.values())
    with pytest.raises(ValueError):
        ys.moduller_birlestir(pm, ek=["yok_boyle_modul"], cikar=None)
    assert ys.durum_turet.__doc__ and set(ys.DURUM_ETIKET) == set(ys.DURUMLAR)


def test_kota_durumu_kenarlari():
    assert ys.kota_durumu(None, 5)["durum"] == "sinirsiz"
    assert ys.kota_durumu(10, None)["durum"] == "olculmuyor"
    assert ys.kota_durumu(10, 7)["durum"] == "saglikli" and ys.kota_durumu(10, 7)["oran"] == 0.7
    assert ys.kota_durumu(10, 8)["durum"] == "dikkat"                                                 # tam %80 dikkat
    assert ys.kota_durumu(10, 10)["durum"] == "dolu" and ys.kota_durumu(10, 11)["durum"] == "asildi"   # tam sınır «ulaşıldı», üstü «aşıldı»
    assert ys.KOTA_DURUM_ETIKET["dolu"] == "sınıra ulaşıldı"
    assert ys.kota_durumu(0, 0)["durum"] == "saglikli" and ys.kota_durumu(0, 1)["durum"] == "asildi"   # limit 0 = izin yok
    e = ys.kota_durumu(3, 5, ezme=10)
    assert e["durum"] == "saglikli" and e["limit"] == 10 and e["kaynak"] == "ezme"                      # sözleşme istisnası
    assert ys.kota_durumu(3, 5, ezme=None)["kaynak"] == "plan"
    assert ys.zorlama_kipi() == "uyari"                                                               # varsayılan: kısıt yok


def test_goc_tohumu_servis_sozlugu_ile_ayni():
    spec = importlib.util.spec_from_file_location("goc_v2609", KOK / "alembic" / "versions" / "v2609_abonelik.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert tuple(m.DURUMLAR) == tuple(ys.DURUMLAR) and m.PILOT_GUN == ys.PILOT_GUN
    tohum_moduller = {r[1] for r in m.TOHUM}
    assert tohum_moduller <= set(ys.MODULLER), tohum_moduller - set(ys.MODULLER)
    assert {r[1] for r in m.TOHUM if r[0] == "pilot"} == {"tahmin", "dogruluk", "veri", "alarm", "kgup"}
    assert "dis_api" not in {r[1] for r in m.TOHUM if r[0] == "pilot"} and "dis_api" in {r[1] for r in m.TOHUM if r[0] == "standart"}
    assert {r[1] for r in m.TOHUM if r[0] == "kurumsal"} == set(ys.MODULLER)


# ----------------------------------------------------------------------------------------------------------- DB
@pytest.fixture()
def iki_kiraci():
    ta, tb = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'AB Kiracı A', 'active', 'pilot')"), {"t": ta})
        s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'AB Kiracı B', 'active', 'standart')"), {"t": tb})
        for i in range(2):
            s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(CAST(:t AS uuid), :a, 1000, 37.0, 32.0, 'Europe/Istanbul', '{}')"),
                      {"t": ta, "a": f"AB A{i}"})
        s.execute(text("INSERT INTO users(tenant_id, email, pw_hash, role, aktif) VALUES(CAST(:t AS uuid), :e, 'x', 'admin', true)"), {"t": ta, "e": f"ab-{ta[:8]}@pvq.test"})
    ys.onbellek_dusur()
    yield ta, tb
    ys.onbellek_dusur()
    with bakim_baglami() as s:
        for tbl in ("abonelik_gecmisi", "kiraci_abonelik", "plants", "users"):
            s.execute(text(f"DELETE FROM {tbl} WHERE tenant_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"), {"a": ta, "b": tb})
        s.execute(text("DELETE FROM tenants WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))"), {"a": ta, "b": tb})


def test_db_kayitsiz_kiraci_turetilir_sonra_varsayilan_ve_senkron(iki_kiraci):
    ta, tb = iki_kiraci
    h = ys.haklar(ta, bugun=BUGUN)
    assert h["kayit_var"] is False and h["plan"]["ad"] == "pilot" and h["durum"] == "pilot" and h["tarihler"]["pilot_bitis"]   # göç öncesi kiracı: tenants'tan
    assert h["moduller"]["tahmin"]["dahil"] and not h["moduller"]["dis_api"]["dahil"] and not h["moduller"]["finansal_etki"]["dahil"]
    k = h["kotalar"]
    assert k["santral"]["kullanim"] == 2 and k["santral"]["limit"] == 3 and k["santral"]["durum"] == "saglikli"
    assert k["kullanici"]["kullanim"] == 1 and k["portfoy"]["kullanim"] == 0 and k["portfoy"]["limit"] == 0 and k["portfoy"]["durum"] == "saglikli"
    assert k["ac_mw"]["kullanim"] == 2.0 and k["ac_mw"]["durum"] == "sinirsiz" and "AC sınırı girilmemiş" in k["ac_mw"]["not_"]   # DC sayıldı, söylenir
    assert k["api_rpm"]["durum"] == "olculmuyor" and k["aylik_dis_api"]["kullanim"] == 0 and k["aylik_dis_api"]["limit"] == 5000
    with sistem_baglami() as s:
        ab.varsayilan_olustur(s, ta, "pilot", aktor="test", bugun=BUGUN)
        ab.varsayilan_olustur(s, ta, "kurumsal", aktor="test", bugun=BUGUN)   # ikinci çağrı yok sayılır (ON CONFLICT)
    h2 = ys.haklar(ta, bugun=BUGUN)
    assert h2["kayit_var"] and h2["plan"]["ad"] == "pilot" and h2["tarihler"]["pilot_bitis"] == (BUGUN + dt.timedelta(days=60)).isoformat() and h2["tarihler"]["kalan_gun"] == 60
    # senkron: plan standart → aktif, pilot_bitis düşer; askıya alma → askida; açma → aktif
    with sistem_baglami() as s:
        y = ab.senkron(s, ta, plan="standart", aktor="test")
        assert y["plan"] == "standart" and y["durum"] == "aktif" and y["pilot_bitis"] is None
        assert ab.senkron(s, ta, plan="standart", aktor="test") is None                        # değişiklik yok → geçmişe yazılmaz
        assert ab.senkron(s, ta, status="suspended", aktor="test")["durum"] == "askida"
        s.execute(text("UPDATE tenants SET status='suspended' WHERE id = CAST(:t AS uuid)"), {"t": ta})
    assert ys.haklar(ta, bugun=BUGUN)["durum"] == "askida"
    with sistem_baglami() as s:
        s.execute(text("UPDATE tenants SET status='active' WHERE id = CAST(:t AS uuid)"), {"t": ta})
        assert ab.senkron(s, ta, status="active", aktor="test")["durum"] == "aktif"
        g = ab.gecmis(s, ta)
    assert [x["eylem"] for x in g] == ["senkron", "senkron", "senkron", "olusturma"] and g[-1]["yeni"]["plan"] == "pilot"
    h3 = ys.haklar(ta, bugun=BUGUN)
    assert h3["moduller"]["finansal_etki"]["dahil"] and h3["moduller"]["dis_api"]["sinir"] == {"kapsamlar": "oku"} and h3["kotalar"]["santral"]["limit"] == 25
    # müşteri görünümü iç alanları sızdırmaz
    m = ys.musteri_gorunumu(h3)
    assert "sozlesme" not in m and "kayit_durumu" not in m and m["sozlesme_istisnasi"] is False and m["zorlama"] == "uyari"


def test_db_rls_izolasyon_ve_yalniz_ekleme(iki_kiraci):
    ta, tb = iki_kiraci
    with sistem_baglami() as s:
        ab.varsayilan_olustur(s, ta, "pilot", aktor="test", bugun=BUGUN)
        ab.varsayilan_olustur(s, tb, "standart", aktor="test", bugun=BUGUN)
    with tenant_baglami(tb) as s:
        assert s.execute(text("SELECT count(*) FROM kiraci_abonelik")).scalar() == 1                 # B yalnız kendini görür
        assert s.execute(text("SELECT plan FROM kiraci_abonelik")).scalar() == "standart"
        assert s.execute(text("SELECT count(*) FROM abonelik_gecmisi WHERE tenant_id = CAST(:a AS uuid)"), {"a": ta}).scalar() == 0
    with tenant_baglami(ta) as s:
        assert s.execute(text("SELECT plan FROM kiraci_abonelik")).scalar() == "pilot"
        with pytest.raises(ProgrammingError):   # uygulama rolünde geçmiş güncellenemez (yalnız ekleme; InsufficientPrivilege)
            s.execute(text("UPDATE abonelik_gecmisi SET gerekce = 'x' WHERE tenant_id = CAST(:a AS uuid)"), {"a": ta})
    # kota ezme sözleşme istisnası: limit ezilir, kaynak «ezme», müşteri görünümünde yalnız işaret
    with sistem_baglami() as s:
        s.execute(text("UPDATE kiraci_abonelik SET kota_ezme = CAST('{\"santral\": 10}' AS jsonb), modul_ek = ARRAY['dis_api'] WHERE tenant_id = CAST(:t AS uuid)"), {"t": ta})
    ys.onbellek_dusur(ta)
    h = ys.haklar(ta, bugun=BUGUN)
    assert h["kotalar"]["santral"]["limit"] == 10 and h["kotalar"]["santral"]["kaynak"] == "ezme" and h["moduller"]["dis_api"]["kaynak"] == "ek"
    assert ys.musteri_gorunumu(h)["sozlesme_istisnasi"] is True and ys.modul_var(ta, "dis_api") is True
    assert ys.kota(ta, "santral", artis=9)["durum"] == "asildi"                                    # 2 + 9 > 10: öngörü


def test_uclar(iki_kiraci, monkeypatch):
    import datetime as _dt

    import jwt as _jwt
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import auth_service as au
    from pvquant.services import denetim_service as dz
    from pvquant.services import platform_service as ps
    ta, tb = iki_kiraci
    c = TestClient(api_main.app)
    try:
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tb, "role": "viewer", "exp": 0}
        y = c.get("/v1/abonelik")
        assert y.status_code == 200 and y.json()["plan"]["ad"] == "standart" and "sozlesme" not in y.json() and y.json()["moduller"]["finansal_etki"]["dahil"]   # viewer okur
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": str(uuid.uuid4()), "role": "admin", "exp": 0}
        assert c.get("/v1/abonelik").status_code == 404
    finally:
        api_main.app.dependency_overrides.clear()
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(dz, "goruntule_kaydet", lambda *a, **k: True)
    try:
        jeton = {"Authorization": "Bearer " + _jwt.encode({"sub": "p1", "kapsam": "platform", "rol": "operator", "sv": 0,
                                                            "exp": _dt.datetime.now(_dt.UTC) + _dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
        y = c.get(f"/v1/yonetim/kiracilar/{ta}/abonelik", headers=jeton)
        assert y.status_code == 200 and y.json()["plan"]["ad"] == "pilot" and "sozlesme" in y.json() and isinstance(y.json()["gecmis"], list)
        assert c.get(f"/v1/yonetim/kiracilar/{uuid.uuid4()}/abonelik", headers=jeton).status_code == 404
        assert c.get("/v1/yonetim/kiracilar/abc/abonelik", headers=jeton).status_code == 422
        assert c.get(f"/v1/yonetim/kiracilar/{ta}/abonelik").status_code in (401, 422)
    finally:
        ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()


def test_db_platform_kancalari_cift_yazar(monkeypatch):
    """`kiraci_olustur` abonelik satırı + «olusturma» geçmişi yazar; `kiraci_guncelle(plan=…)` ve `status=suspended` abonelikle eşzamanlanır."""
    from pvquant.services import platform_service as ps
    monkeypatch.delenv("PVQ_SMTP_HOST", raising=False)
    aktor = "00000000-0000-4000-8000-000000000001"
    etiket = uuid.uuid4().hex[:8]
    tid = None
    try:
        r = ps.kiraci_olustur(aktor, f"AB Kanca {etiket}", f"kanca-{etiket}@pvq.test")
        tid = r["tenant_id"]
        h = ys.haklar(tid, bugun=BUGUN)
        assert h["kayit_var"] and h["plan"]["ad"] == "pilot" and h["durum"] == "pilot" and h["sozlesme"]["guncelleyen"] == aktor
        ps.kiraci_guncelle(aktor, tid, plan="standart")
        assert ys.haklar(tid, bugun=BUGUN)["plan"]["ad"] == "standart" and ys.haklar(tid, bugun=BUGUN)["durum"] == "aktif"
        ps.kiraci_guncelle(aktor, tid, status="suspended")
        assert ys.haklar(tid, bugun=BUGUN)["durum"] == "askida"
        with tenant_baglami(tid) as s:
            assert [g["eylem"] for g in ab.gecmis(s, tid)] == ["senkron", "senkron", "olusturma"]
    finally:
        ys.onbellek_dusur(); ps.oturum_onbellegi_dusur()
        with bakim_baglami() as s:
            s.execute(text("DELETE FROM denetim_izi WHERE ayrinti::text LIKE :e OR aktor_eposta LIKE :e"), {"e": f"%{etiket}%"})
            s.execute(text("DELETE FROM parola_sifirlama WHERE user_id IN (SELECT id FROM users WHERE email LIKE :e)"), {"e": f"%{etiket}%"})
            s.execute(text("DELETE FROM users WHERE email LIKE :e"), {"e": f"%{etiket}%"})
            s.execute(text("DELETE FROM tenants WHERE name LIKE :e"), {"e": f"%{etiket}%"})   # abonelik + geçmiş CASCADE
