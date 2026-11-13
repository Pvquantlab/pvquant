"""v2.609 (Faz 6 F6-C) — abonelik yaşam döngüsü: geçiş tablosu (saf), `guncelle` doğrulamaları ve çift yazım (tenants.plan/status, oturum düşürme),
yalnız-ekleme geçmiş + gerekçe, `gece_turet` tarihlerden türetme, platform uçları (gerekçe zorunlu, fesih sahip-only, plan modülleri sahip-only)."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, platform_baglami, sistem_baglami
from pvquant.services import abonelik_service as ab
from pvquant.services import platform_service as ps
from pvquant.services import yetki_service as ys

AKTOR = "00000000-0000-4000-8000-000000000001"
BUGUN = dt.date(2026, 11, 13)


def test_gecis_tablosu():
    assert ab.gecis_izinli("pilot", "aktif") and ab.gecis_izinli("pilot", "askida") and ab.gecis_izinli("askida", "aktif")
    assert not ab.gecis_izinli("feshedildi", "aktif") and not ab.gecis_izinli("aktif", "pilot") and not ab.gecis_izinli("aktif", "sona_erdi")
    assert set(ab.GECISLER) == set(ys.DURUMLAR) and ab.GECISLER["feshedildi"] == set()
    for hedefler in ab.GECISLER.values():
        assert hedefler <= {"aktif", "askida", "feshedildi"}            # otomatik durumlar elle hedeflenmez


@pytest.fixture()
def kiraci():
    t = str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'YD Kiracı', 'active', 'pilot')"), {"t": t})
        s.execute(text("INSERT INTO users(tenant_id, email, pw_hash, role, aktif, oturum_surumu) VALUES(CAST(:t AS uuid), :e, 'x', 'admin', true, 0)"), {"t": t, "e": f"yd-{t[:8]}@pvq.test"})
        ab.varsayilan_olustur(s, t, "pilot", aktor="test", bugun=BUGUN)
    ys.onbellek_dusur()
    yield t
    ys.onbellek_dusur()
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM users WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


def _sv(t):
    with sistem_baglami() as s:
        return s.execute(text("SELECT max(oturum_surumu) FROM users WHERE tenant_id = CAST(:t AS uuid)"), {"t": t}).scalar()


def test_db_guncelle_dogrulama_cift_yazim_ve_gecmis(kiraci):
    t = kiraci
    with platform_baglami(AKTOR) as s:
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, plan="standart", bugun=BUGUN)                                   # gerekçe zorunlu
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, plan="altin", gerekce="x", bugun=BUGUN)                        # plan tanımsız
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, modul_ek=["yok"], gerekce="x", bugun=BUGUN)
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, modul_ek=["dis_api"], modul_cikar=["dis_api"], gerekce="x", bugun=BUGUN)
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, kota_ezme={"santral": -1}, gerekce="x", bugun=BUGUN)
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, bitis="2020-01-01", gerekce="x", bugun=BUGUN)                   # başlangıçtan önce
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, durum="sona_erdi", gerekce="x", bugun=BUGUN)                    # otomatik durum elle hedeflenmez
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, durum="feshedildi", gerekce="x", bugun=BUGUN)                   # fesih yalnız sahip
        # plan yükseltme + sözleşme istisnası + bitiş: çift yazım
        y = ab.guncelle(s, t, AKTOR, plan="standart", bitis="2027-06-30", modul_ek=["santral_yetki"], kota_ezme={"santral": 40, "portfoy": None},
                        sozlesme_notu="yıllık sözleşme", teklif_ref="T-2026-07", gerekce="sözleşme imzalandı", bugun=BUGUN)
        assert set(y["degisen"]) == {"plan", "durum", "pilot_bitis", "bitis", "modul_ek", "kota_ezme", "sozlesme_notu", "teklif_ref"}
        assert y["yeni"]["durum"] == "aktif" and y["yeni"]["pilot_bitis"] is None
        assert ab.guncelle(s, t, AKTOR, plan="standart", gerekce="aynı", bugun=BUGUN)["degisen"] == {}   # değişiklik yok → geçmişe yazılmaz
    with sistem_baglami() as s:
        assert s.execute(text("SELECT plan, status FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t}).first() == ("standart", "active")
    h = ys.haklar(t, bugun=BUGUN)
    assert h["plan"]["ad"] == "standart" and h["durum"] == "aktif" and h["moduller"]["santral_yetki"]["kaynak"] == "ek"
    assert h["kotalar"]["santral"]["limit"] == 40 and h["kotalar"]["santral"]["kaynak"] == "ezme" and h["kotalar"]["portfoy"]["durum"] == "saglikli"   # None = plan limiti (1)
    assert h["sozlesme"]["teklif_ref"] == "T-2026-07" and h["tarihler"]["bitis"] == "2027-06-30"
    # askıya alma: status + oturumlar; açma: tarihlerden türer; fesih sahip: terminal
    sv0 = _sv(t)
    with platform_baglami(AKTOR) as s:
        assert ab.guncelle(s, t, AKTOR, durum="askida", gerekce="ödeme gecikti", bugun=BUGUN)["yeni"]["durum"] == "askida"
    assert _sv(t) == sv0 + 1 and ys.haklar(t, bugun=BUGUN)["durum"] == "askida"
    with platform_baglami(AKTOR) as s:
        assert ab.guncelle(s, t, AKTOR, durum="aktif", gerekce="ödendi", bugun=BUGUN)["yeni"]["durum"] == "aktif"
        assert ab.guncelle(s, t, AKTOR, durum="aktif", bitis="2026-11-30", gerekce="kısa uzatma", bugun=BUGUN)["yeni"]["durum"] == "sona_eriyor"   # ≤30 gün
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, bitis="2026-11-01", gerekce="başlangıçtan önce", bugun=BUGUN)                       # bitiş < başlangıç (13.11)


def test_db_gecmis_bitis_aktif_ve_fesih_ve_gece(kiraci):
    t = kiraci
    with platform_baglami(AKTOR) as s:
        assert ab.guncelle(s, t, AKTOR, plan="standart", bitis="2026-11-13", gerekce="deneme", bugun=BUGUN)["yeni"]["durum"] == "sona_eriyor"   # bitiş = bugün
        y = ab.guncelle(s, t, AKTOR, durum="aktif", gerekce="açma", bugun=BUGUN + dt.timedelta(days=20))
    assert y["yeni"]["durum"] == "yenileme_bekliyor"                                                     # bitiş geçmişse «aktif» yenileme bekliyor olarak türer
    # gece türetme: bitiş ileri alınınca durum «aktif»e döner; elle sona_erdi/feshedildi dokunulmaz
    with platform_baglami(AKTOR) as s:
        s.execute(text("UPDATE kiraci_abonelik SET bitis = '2027-12-31', durum = 'yenileme_bekliyor' WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        g = ab.gece_turet(s, bugun=BUGUN)
    assert g["durum"] == "ok" and any(d["tenant_id"] == t and d["yeni"] == "aktif" for d in g["degisenler"])
    with platform_baglami(AKTOR) as s:
        assert ab.gece_turet(s, bugun=BUGUN)["degisen"] == 0 or all(d["tenant_id"] != t for d in ab.gece_turet(s, bugun=BUGUN)["degisenler"])   # idempotent
        y = ab.guncelle(s, t, AKTOR, durum="feshedildi", gerekce="sözleşme bitti", sahip=True, bugun=BUGUN)
        assert y["yeni"]["durum"] == "feshedildi" and y["degisen"]["status"]["yeni"] == "suspended"
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, durum="aktif", gerekce="geri", sahip=True, bugun=BUGUN)         # terminal
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, plan="kurumsal", gerekce="plan", sahip=True, bugun=BUGUN)       # inceleme: terminalde alan değişikliği yok
        assert ab.guncelle(s, t, AKTOR, sozlesme_notu="fesih notu", gerekce="not", bugun=BUGUN)["yeni"]["durum"] == "feshedildi"   # not serbest, durum kalır
        gec = ab.gecmis(s, t)
    assert [g["eylem"] for g in gec][:4] == ["guncelle", "guncelle", "turetme", "guncelle"] and gec[1]["gerekce"] == "sözleşme bitti" and gec[1]["yeni"]["status"] == "suspended"
    assert ys.haklar(t, bugun=BUGUN)["durum"] == "feshedildi"


def test_uclar(kiraci, monkeypatch):
    import datetime as _dt

    import jwt as _jwt
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from pvquant.services import auth_service as au
    from pvquant.services import denetim_service as dz
    t = kiraci
    kayitlar = []
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    monkeypatch.setattr(dz, "kaydet", lambda *a, **k: kayitlar.append((a, k)) or True)
    monkeypatch.setattr(dz, "goruntule_kaydet", lambda *a, **k: True)
    c = TestClient(api_main.app)

    def jeton(rol):
        monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": rol, "email": "o@pvq", "totp_aktif": True})
        ps.oturum_onbellegi_dusur()
        return {"Authorization": "Bearer " + _jwt.encode({"sub": "p1", "kapsam": "platform", "rol": rol, "sv": 0, "exp": _dt.datetime.now(_dt.UTC) + _dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
    try:
        op = jeton("operator")
        assert c.put(f"/v1/yonetim/kiracilar/{t}/abonelik", json={"plan": "standart"}, headers=op).status_code == 422                 # gerekçe zorunlu (pydantic)
        assert c.put(f"/v1/yonetim/kiracilar/{t}/abonelik", json={"plan": "altin", "gerekce": "x"}, headers=op).status_code == 422
        y = c.put(f"/v1/yonetim/kiracilar/{t}/abonelik", json={"plan": "standart", "kota_ezme": {"santral": 30}, "gerekce": "sözleşme"}, headers=op)
        assert y.status_code == 200 and y.json()["abonelik"]["plan"]["ad"] == "standart" and y.json()["abonelik"]["kotalar"]["santral"]["limit"] == 30
        assert kayitlar and kayitlar[-1][0][1] == "abonelik_guncelle" and kayitlar[-1][1]["ayrinti"]["gerekce"] == "sözleşme"
        assert c.put(f"/v1/yonetim/kiracilar/{t}/abonelik", json={"durum": "feshedildi", "gerekce": "x"}, headers=op).status_code == 422   # operatör feshedemez
        assert c.put(f"/v1/yonetim/kiracilar/{uuid.uuid4()}/abonelik", json={"gerekce": "x"}, headers=op).status_code == 404
        assert c.put("/v1/yonetim/planlar/standart/moduller", json={"moduller": {"dis_api": {"dahil": False}}}, headers=op).status_code == 403   # sahip-only
        sa = jeton("sahip")
        eski = {p["ad"]: p for p in ps.plan_listesi()}["standart"]["moduller"]["dis_api"]
        try:
            y = c.put("/v1/yonetim/planlar/standart/moduller", json={"moduller": {"dis_api": {"dahil": False, "sinir": None}}}, headers=sa)
            assert y.status_code == 200 and y.json()["moduller"]["dis_api"]["dahil"] is False and y.json()["moduller"]["dis_api"]["ad"]
            assert c.put("/v1/yonetim/planlar/standart/moduller", json={"moduller": {"yok": {"dahil": True}}}, headers=sa).status_code == 422
            assert c.put("/v1/yonetim/planlar/altin/moduller", json={"moduller": {"dis_api": {"dahil": True}}}, headers=sa).status_code == 404
        finally:
            ps.plan_modul_guncelle("standart", {"dis_api": {"dahil": eski["dahil"], "sinir": eski["sinir"]}})
        y = c.put(f"/v1/yonetim/kiracilar/{t}/abonelik", json={"durum": "feshedildi", "gerekce": "sahip fesih"}, headers=sa)
        assert y.status_code == 200 and y.json()["abonelik"]["durum"] == "feshedildi"
    finally:
        ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()


def test_db_pilot_uzatma_ve_dizi_sirasi(kiraci):
    """İnceleme: süresi dolmuş pilotta pilot bitişi ileri alınınca durum yeniden türer (sona_erdi yapışkan kalmaz); modül dizisi sıra farkı «değişti» değildir."""
    t = kiraci
    with platform_baglami(AKTOR) as s:
        s.execute(text("UPDATE kiraci_abonelik SET pilot_bitis = '2026-11-01', durum = 'sona_erdi' WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
    ys.onbellek_dusur(t)
    assert ys.haklar(t, bugun=BUGUN)["durum"] == "sona_erdi"
    with platform_baglami(AKTOR) as s:
        with pytest.raises(ab.AbonelikHata):
            ab.guncelle(s, t, AKTOR, durum="aktif", gerekce="tarihsiz açma", bugun=BUGUN)              # tarih geçmiş → açılamaz, mesaj yol gösterir
        y = ab.guncelle(s, t, AKTOR, pilot_bitis="2027-01-31", gerekce="pilot uzatıldı", bugun=BUGUN)
        assert y["yeni"]["durum"] == "pilot" and y["degisen"]["durum"]["eski"] == "sona_erdi"
        y = ab.guncelle(s, t, AKTOR, modul_ek=["dis_api", "finansal_etki"], gerekce="iki modül", bugun=BUGUN)
        assert y["degisen"]["modul_ek"]["yeni"] == ["dis_api", "finansal_etki"]
        assert ab.guncelle(s, t, AKTOR, modul_ek=["finansal_etki", "dis_api"], gerekce="sıra farkı", bugun=BUGUN)["degisen"] == {}   # sıra farkı değişiklik değil
        assert ab.guncelle(s, t, AKTOR, kota_ezme={"santral": 5.0}, gerekce="ezme", bugun=BUGUN)["degisen"]["kota_ezme"]["yeni"] == {"santral": 5.0}
        assert ab.guncelle(s, t, AKTOR, kota_ezme={"santral": 5}, gerekce="aynı ezme", bugun=BUGUN)["degisen"] == {}
