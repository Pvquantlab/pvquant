"""v2.609 (Faz 6 F6-B) — kullanım ve kota ölçümü: `kullanim_service.ozet` anlık sayımları (etkin santral, güç MW, kullanıcı, portföy) doğrudan SQL
sayımına eşit; kota hükümleri plan limiti + sözleşme ezmesiyle; `plan_listesi` yeni kota alanları + modüller; `plan_guncelle` ondalıklı MW ve ret."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import kullanim_service as ku
from pvquant.services import platform_service as ps
from pvquant.services import yetki_service as ys

AKTOR = "00000000-0000-4000-8000-000000000001"


@pytest.fixture()
def kiraci():
    """Pilot kiracı: 2 etkin + 1 arşivli santral (biri AC sınırlı 800 kW, biri yalnız DC 1.200 kWp), 2 etkin + 1 pasif kullanıcı, 1 geçerli + 1 bitmiş portföy,
    bu ay 3 dış API isteği (sayaç), kota ezmesi santral=5."""
    t = str(uuid.uuid4()); bugun = dt.datetime.now(dt.timezone.utc).date()
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'KU Kiracı', 'active', 'pilot')"), {"t": t})
        s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json, archived) VALUES"
                       "(CAST(:t AS uuid), 'KU A', 1000, 800, 37, 32, 'Europe/Istanbul', '{}', false),"
                       "(CAST(:t AS uuid), 'KU B', 1200, NULL, 37, 32, 'Europe/Istanbul', '{}', false),"
                       "(CAST(:t AS uuid), 'KU C', 5000, 5000, 37, 32, 'Europe/Istanbul', '{}', true)"), {"t": t})
        for i, aktif in enumerate((True, True, False)):
            s.execute(text("INSERT INTO users(tenant_id, email, pw_hash, role, aktif) VALUES(CAST(:t AS uuid), :e, 'x', 'viewer', :a)"), {"t": t, "e": f"ku-{t[:8]}-{i}@pvq.test", "a": aktif})
        s.execute(text("INSERT INTO portfoy(tenant_id, ad, tur, gecerli_bas, gecerli_bit) VALUES(CAST(:t AS uuid), 'KU P1', 'dsg', '2026-01-01', NULL), (CAST(:t AS uuid), 'KU P0', 'dsg', '2025-01-01', '2025-12-31')"), {"t": t})
        s.execute(text("INSERT INTO kullanim_sayac(tenant_id, gun, tur, adet) VALUES(CAST(:t AS uuid), :g, 'dis_api', 3)"), {"t": t, "g": bugun})
        s.execute(text("INSERT INTO kiraci_abonelik(tenant_id, plan, durum, baslangic, pilot_bitis, kota_ezme) VALUES(CAST(:t AS uuid), 'pilot', 'pilot', :b, :pb, CAST('{\"santral\": 5}' AS jsonb))"),
                  {"t": t, "b": bugun, "pb": bugun + dt.timedelta(days=60)})
    ys.onbellek_dusur()
    yield t
    with bakim_baglami() as s:
        for tbl in ("kullanim_sayac", "portfoy", "users", "plants"):
            s.execute(text(f"DELETE FROM {tbl} WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})   # abonelik CASCADE


def test_anlik_sayimlar_sql_ile_ayni_ve_kotalar(kiraci):
    o = ku.ozet(AKTOR)
    k = next(x for x in o["kiracilar"] if x["id"] == kiraci)
    with sistem_baglami() as s:
        dogrudan = s.execute(text("SELECT (SELECT count(*) FROM plants WHERE tenant_id = CAST(:t AS uuid) AND NOT archived), "
                                  "(SELECT count(*) FROM users WHERE tenant_id = CAST(:t AS uuid) AND aktif), "
                                  "(SELECT count(*) FROM portfoy WHERE tenant_id = CAST(:t AS uuid) AND (gecerli_bit IS NULL OR gecerli_bit >= CURRENT_DATE))"), {"t": kiraci}).first()
    assert (k["anlik"]["santral"], k["anlik"]["kullanici"], k["anlik"]["portfoy"]) == tuple(int(x) for x in dogrudan) == (2, 2, 1)
    assert k["anlik"]["ac_mw"] == 2.0 and k["anlik"]["ac_eksik_santral"] == 1                      # 800 kW AC + 1.200 kWp DC (yaklaşık), arşivli sayılmaz
    assert k["plan"] == "pilot" and k["abonelik_durum"] == "pilot" and k["abonelik_etiketi"] == "Pilot"
    kt = k["kotalar"]
    assert kt["santral"]["limit"] == 5 and kt["santral"]["kaynak"] == "ezme" and kt["santral"]["durum"] == "saglikli" and kt["santral"]["kullanim"] == 2   # sözleşme ezmesi 3 → 5
    assert kt["kullanici"]["limit"] == 3 and kt["kullanici"]["oran"] == 0.667 and kt["kullanici"]["durum"] == "saglikli"
    assert kt["portfoy"]["limit"] == 0 and kt["portfoy"]["durum"] == "asildi"                          # pilot portföy 0, bir portföy var → aşıldı (uyarı)
    assert kt["ac_mw"]["durum"] == "sinirsiz" and "AC sınırı girilmemiş" in kt["ac_mw"]["not_"]
    assert kt["aylik_dis_api"]["kullanim"] == 3 and kt["aylik_dis_api"]["limit"] == 5000 and kt["aylik_rapor"]["kullanim"] == 0 and kt["aylik_isleme_saat"]["durum"] == "sinirsiz"
    assert set(o["kota_alanlari"]) == set(ku.KOTA_KAYNAK) and o["kota_sozlugu"]["asildi"] == "sınır aşıldı"
    # yetki_service aynı kiracı için aynı hükmü verir (iki yol tek tanım)
    h = ys.haklar(kiraci, taze=True)
    assert h["kotalar"]["santral"]["limit"] == 5 and h["kullanim"]["ac_mw"] == 2.0 and h["kullanim"]["portfoy"] == 1


def test_plan_listesi_ve_guncelleme_yeni_alanlar():
    pl = {p["ad"]: p for p in ps.plan_listesi()}
    assert pl["pilot"]["portfoy_limit"] == 0 and pl["standart"]["portfoy_limit"] == 1 and pl["kurumsal"]["portfoy_limit"] is None
    assert {k for k, m in pl["pilot"]["moduller"].items() if m["dahil"]} == {"tahmin", "dogruluk", "veri", "alarm", "kgup"} and pl["standart"]["moduller"]["dis_api"]["sinir"] == {"kapsamlar": "oku"}
    assert set(pl["pilot"]["moduller"]) == set(ys.MODULLER) and pl["pilot"]["moduller"]["dis_api"]["dahil"] is False and pl["pilot"]["moduller"]["dis_api"]["ad"]   # her modül adıyla
    assert {k for k, m in pl["kurumsal"]["moduller"].items() if m["dahil"]} == set(ys.MODULLER)
    eski = pl["standart"]["ac_mw_limit"]
    try:
        y = ps.plan_guncelle("standart", ac_mw_limit=12.5, aylik_isleme_saat_limit=20000)
        assert y["ac_mw_limit"] == 12.5 and y["aylik_isleme_saat_limit"] == 20000 and y["moduller"]
        with pytest.raises(ValueError):
            ps.plan_guncelle("standart", ac_mw_limit=-1)
        y2 = ps.plan_guncelle("standart", ac_mw_limit=None, aylik_isleme_saat_limit=None)
        assert y2["ac_mw_limit"] is None and y2["aylik_isleme_saat_limit"] is None
    finally:
        ps.plan_guncelle("standart", ac_mw_limit=eski, aylik_isleme_saat_limit=None)
