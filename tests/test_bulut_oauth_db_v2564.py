"""v2.564 — DB'li kabul: state satırı yalnız özetle durur, tek kez kullanılır (ikinci arama boş), süresi dolan bulunmaz, `son()` özeti gizli içermez, RLS
başka kiracıya kapalı. Test DB (docker pvq-test-db, göç v2564) gerekir."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.guvenlik import kasa
from pvquant.services import bulut_oauth_service as bo

ONAY2 = {"yalniz_okuma": True, "sifreli_saklama": True}


@pytest.fixture
def santral():
    t, p = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name) VALUES(:i, 'T')"), {"i": t})
    with tenant_baglami(t) as s:
        s.execute(text("INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) VALUES(:p, :t, 'P', 38.4, 34.6, 'Europe/Istanbul', 1000)"), {"p": p, "t": t})
    yield {"id": p, "tenant_id": t}
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM bulut_oauth_durum WHERE plant_id=:p"), {"p": p})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": p}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": t})


def test_state_tek_kullanim_sure_ve_rls(santral, monkeypatch):
    monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret()); monkeypatch.setenv("PVQ_SUNGROW_APPKEY", "A"); monkeypatch.setenv("PVQ_SUNGROW_ACCESS_KEY", "Gizli-K"); monkeypatch.setenv("PVQ_SUNGROW_APP_ID", "app")
    t, p = santral["tenant_id"], santral["id"]
    simdi = datetime.now(timezone.utc)
    r = bo.baslat(t, {"id": p}, "sungrow", "eu", ONAY2, "u1", simdi)
    assert r["durum"] == "yonlendir"
    state = r["yetki_url"].split("state=")[1].split("#")[0]
    with tenant_baglami(t) as s:
        row = s.execute(text("SELECT state_hash, kullanildi, onay_json, aktor_id FROM bulut_oauth_durum WHERE plant_id=CAST(:p AS uuid)"), {"p": p}).mappings().one()
    assert row["state_hash"] == bo._ozet(state) and state not in json.dumps(dict(row), default=str) and not row["kullanildi"] and row["aktor_id"] == "u1"
    son = bo.son(t, p)
    assert son["durum"] == "bekliyor" and son["saglayici"] == "sungrow" and "Gizli-K" not in json.dumps(son)
    with tenant_baglami(str(uuid.uuid4())) as s:   # RLS: başka kiracı görmez
        assert s.execute(text("SELECT count(*) FROM bulut_oauth_durum WHERE plant_id=CAST(:p AS uuid)"), {"p": p}).scalar() == 0
    bulunan = bo._bul_ve_isaretle_db(bo._ozet(state), simdi + timedelta(minutes=1))
    assert bulunan and str(bulunan["plant_id"]) == p and str(bulunan["tenant_id"]) == t and bulunan["saglayici"] == "sungrow" and bulunan["onay_json"]["onaylar"] == ONAY2
    assert bo._bul_ve_isaretle_db(bo._ozet(state), simdi + timedelta(minutes=1)) is None   # ikinci kez (yeniden oynatma) bulunmaz
    bo._sonuc_yaz_db(bulunan["id"], t, {"durum": "tamam", "etiket": "x", "zaman": simdi.isoformat(), "santraller": [{"kimlik": "1", "ad": "A", "kapasite_kwp": 1.0}]})
    son = bo.son(t, p)
    assert son["durum"] == "tamam" and son["kullanildi"] and son["santraller"][0]["kimlik"] == "1"
    # süresi dolan state bulunmaz
    r2 = bo.baslat(t, {"id": p}, "sungrow", "eu", ONAY2, "u1", simdi - timedelta(minutes=30))
    state2 = r2["yetki_url"].split("state=")[1].split("#")[0]
    assert bo._bul_ve_isaretle_db(bo._ozet(state2), simdi) is None
    assert bo.geri_donus("sungrow", {"state": state2, "code": "c"}, simdi)["durum"] == "durum_gecersiz"
