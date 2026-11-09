"""v2.556/v2.557 — DB'li kabul: zarf şifreli kayıt tabloda düz metin içermez, RLS başka kiracıya kapalı, worker çözer; çekiş turu ham tabloya yazar,
gölge görünüme yalnız «birim doğrulandı» sonrası ve değişen değerde yeni revizyon. Test DB (docker pvq-test-db, göç v2556) gerekir."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.guvenlik import kasa
from pvquant.services import bulut_cekis_service as bc
from pvquant.services import bulut_kimlik_service as bk
from tests.test_bulut_cekis_v2557 import SahteIstemci

T = datetime(2026, 11, 9, 10, 30, tzinfo=timezone.utc)
ONAY2 = {"yalniz_okuma": True, "sifreli_saklama": True}


def _sina_ok(kod, kimlik, onay, bolge):
    return {"durum": "ok", "zaman": "z", "ozet": {"santral_sayisi": 1, "santraller": [{"kimlik": "NE=1", "ad": "Edikli", "kapasite_kwp": 1000.0}]}}


@pytest.fixture
def santral():
    t, p = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name) VALUES(:i, 'T')"), {"i": t})
    with tenant_baglami(t) as s:
        s.execute(text("INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) VALUES(:p, :t, 'P', 38.4, 34.6, 'Europe/Istanbul', 1000)"), {"p": p, "t": t})
    yield {"id": p, "tenant_id": t}
    with sistem_baglami() as s:
        for tbl in ("kaynak_saatlik", "bulut_saatlik_ham", "bulut_kimlik"):
            s.execute(text(f"DELETE FROM {tbl} WHERE plant_id=:p"), {"p": p})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": p}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": t})


def test_kasa_db_rls_cekis_ve_revizyon(santral, monkeypatch):
    for k in ("PVQ_KEK_ID", "PVQ_KEK_ESKI"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret())
    t, p = santral["tenant_id"], santral
    r = bk.kaydet(t, p, "fusionsolar", {"kullanici": "nbi_x", "sistem_kodu": "Gizli-99"}, "eu5", ONAY2, "aktor", sina=_sina_ok)
    assert r["kaydedildi"] and r["dis_kimlik"] == "NE=1"
    kay = bk.listele(t, p["id"])
    assert len(kay) == 1 and kay[0]["etiket"] == "nb…x" and kay[0]["kek_id"] == "k1" and not kay[0]["cekis_acik"] and "sifreli" not in kay[0] and "dek_sarili" not in kay[0]
    with sistem_baglami() as s:
        row = dict(s.execute(text("SELECT * FROM bulut_kimlik WHERE plant_id=:p"), {"p": p["id"]}).mappings().first())
    assert b"Gizli-99" not in bytes(row["sifreli"]) and "Gizli-99" not in json.dumps({k: v for k, v in row.items() if k not in ("sifreli", "dek_sarili")}, default=str)
    assert bk.coz_kimlik(row) == {"kullanici": "nbi_x", "sistem_kodu": "Gizli-99"}
    with tenant_baglami(str(uuid.uuid4())) as s:   # RLS: başka kiracı görmez
        assert s.execute(text("SELECT count(*) FROM bulut_kimlik WHERE plant_id=:p"), {"p": p["id"]}).scalar() == 0
    # aynı kayıt yeniden → güncellenir (tek satır), etiket değişir
    r2 = bk.kaydet(t, p, "fusionsolar", {"kullanici": "yeni_hesap", "sistem_kodu": "Gizli-100"}, "eu5", ONAY2, "aktor", sina=_sina_ok)
    assert r2["kaydedildi"] and len(bk.listele(t, p["id"])) == 1 and bk.listele(t, p["id"])[0]["etiket"] == "yen…ap"
    # çekiş: kapalıyken listede yok; açınca tur ham yazar, gölgeye yazmaz (birim doğrulanmadı)
    assert not [k for k in bc.kayitlar_cekis_acik() if str(k["plant_id"]) == p["id"]]
    assert bk.ayarla(t, p["id"], "fusionsolar", cekis_acik=True)["cekis_acik"] is True
    mine = [k for k in bc.kayitlar_cekis_acik() if str(k["plant_id"]) == p["id"]]
    assert len(mine) == 1 and mine[0]["dis_kimlik"] == "NE=1" and mine[0]["tz"] == "Europe/Istanbul"
    SahteIstemci.girisler.clear(); SahteIstemci.cagrilar.clear()
    out = bc.tur(simdi=T, kayitlar=mine, istemci_fabrikasi=SahteIstemci)
    assert "3 ham saat" in out and "gölge 0" in out and SahteIstemci.cagrilar[0][0] == "NE=1"
    ham = bc.ham_son(t, p["id"]); assert len(ham) == 3 and ham[0]["alanlar"]["inverter_power"] == 20.0
    with tenant_baglami(t) as s:
        assert s.execute(text("SELECT count(*) FROM kaynak_saatlik WHERE plant_id=:p AND kaynak='fusionsolar'"), {"p": p["id"]}).scalar() == 0
    k = bk.listele(t, p["id"])[0]; assert k["son_durum"] == "ok" and k["kota_sayac"] == 1 and k["kota_gun"] == date(2026, 11, 9).isoformat()
    # birim doğrulandı → gölgeye 3 saat; aynı değerle tekrar → revizyon yok; farklı değer → yeni revizyon (0,0 → 0,0 değişmez)
    bk.ayarla(t, p["id"], "fusionsolar", birim_dogrulandi=True)
    taze = lambda: [k for k in bc.kayitlar_cekis_acik() if str(k["plant_id"]) == p["id"]]   # noqa: E731 — her tur kayıtları yeniden okur (kota sayacı)
    assert "gölge 3" in bc.tur(simdi=T, kayitlar=taze(), istemci_fabrikasi=SahteIstemci)
    assert "gölge 0" in bc.tur(simdi=T, kayitlar=taze(), istemci_fabrikasi=SahteIstemci)

    class Iki(SahteIstemci):
        def saatlik_ham(self, kodlar, gun):
            return [{**r, "alanlar": {**r["alanlar"], "enerji_kwh_belge": r["alanlar"]["enerji_kwh_belge"] * 2}} for r in super().saatlik_ham(kodlar, gun)]
    assert "gölge 2" in bc.tur(simdi=T, kayitlar=taze(), istemci_fabrikasi=Iki)
    with tenant_baglami(t) as s:
        rows = s.execute(text("SELECT ts_utc, revizyon, energy_kwh, tamlik, yontem, cihaz_id FROM kaynak_saatlik WHERE plant_id=:p AND kaynak='fusionsolar' ORDER BY ts_utc, revizyon"),
                         {"p": p["id"]}).mappings().all()
    assert len(rows) == 5 and max(r["revizyon"] for r in rows) == 2 and all(r["tamlik"] == "measured_complete" and r["yontem"] == "saglayici" and r["cihaz_id"] == "bulut" for r in rows)
    assert bk.listele(t, p["id"])[0]["kota_sayac"] == 4
    assert bk.sil(t, p["id"], "fusionsolar") == 1 and bk.listele(t, p["id"]) == []
