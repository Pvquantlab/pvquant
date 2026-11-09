"""v2.561 — DB'li kabul: toplayıcı kimliği (özet saklanır, bir kez gösterilir), alım defteri, kanal='edge' örnekler, yeniden gönderimde çift sayım yok, iptal. Test DB (göç v2558)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import edge_service as es
from pvquant.services import pilot_service as ps

T0 = datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc)


@pytest.fixture
def santral():
    t, p = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name) VALUES(:i, 'T')"), {"i": t})
    with tenant_baglami(t) as s:
        s.execute(text("INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) VALUES(:p, :t, 'P', 38.4, 34.6, 'Europe/Istanbul', 1000)"), {"p": p, "t": t})
    yield {"id": p, "tenant_id": t, "name": "P", "params_json": {}}
    with sistem_baglami() as s:
        for tbl in ("edge_alim", "edge_toplayici", "kaynak_saatlik", "scada_hourly", "ingestion_batches", "canli_ornek"):
            s.execute(text(f"DELETE FROM {tbl} WHERE plant_id=:p"), {"p": p})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": p}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": t})


def _o(sira, wh):
    return {"sira": sira, "ts_utc": (T0 + timedelta(minutes=15 * sira)).isoformat(), "cihaz_id": "SN-E", "guc_w": 100000.0, "enerji_wh": wh, "durum_kodu": 4, "olaylar": []}


def test_toplayici_alim_defter_ve_iptal(santral):
    t, p = santral["tenant_id"], santral
    r = es.toplayici_olustur(t, p["id"], "Kabin A")
    anahtar = r["anahtar"]; assert anahtar.startswith("pvqe_")
    with sistem_baglami() as s:
        row = dict(s.execute(text("SELECT * FROM edge_toplayici WHERE id=CAST(:i AS uuid)"), {"i": r["id"]}).mappings().first())
    assert anahtar.split("_")[2] not in str(row.values()) and row["anahtar_hash"] != anahtar   # yalnız özet
    top = es.dogrula(anahtar); assert top["plant_id"] == p["id"] and top["tenant_id"] == t
    assert es.toplayici_listele(t, p["id"])[0]["durum"] == "etkin" and "anahtar" not in es.toplayici_listele(t, p["id"])[0]
    # 06:00–07:00 tam saat (5 örnek, kapanış dâhil) → canli_ornek kanal edge, defter, toplama tam saat
    o1 = es.al(top, p, [_o(i, 0 + 25000 * i) for i in range(5)], T0 + timedelta(hours=1, minutes=1))
    assert o1["kabul"] == 5 and o1["ack_sira"] == 4 and o1["toplama"] and o1["toplama"].get("n_yazilan", 0) >= 1
    with tenant_baglami(t) as s:
        assert s.execute(text("SELECT count(*) FROM canli_ornek WHERE plant_id=:p AND kanal='edge'"), {"p": p["id"]}).scalar() == 5
        assert s.execute(text("SELECT count(*) FROM edge_alim WHERE plant_id=:p"), {"p": p["id"]}).scalar() == 5
        n_saat = s.execute(text("SELECT count(*) FROM scada_hourly WHERE plant_id=:p"), {"p": p["id"]}).scalar()
    # yeniden gönderim (ağ kesintisi senaryosu): çift sayım yok, ack aynı
    o2 = es.al(top, p, [_o(i, 25000 * i) for i in range(5)] + [_o(5, 125000)], T0 + timedelta(hours=1, minutes=16))
    assert o2["kabul"] == 1 and o2["yinelenen"] == 5 and o2["catisma"] == [] and o2["ack_sira"] == 5
    with tenant_baglami(t) as s:
        assert s.execute(text("SELECT count(*) FROM canli_ornek WHERE plant_id=:p"), {"p": p["id"]}).scalar() == 6
        assert s.execute(text("SELECT count(*) FROM scada_hourly WHERE plant_id=:p"), {"p": p["id"]}).scalar() == n_saat   # 06–07 saati yeniden yazılmadı
    assert es.toplayici_listele(t, p["id"])[0]["son_sira"] == 5
    # iptal → anahtar reddedilir
    assert es.toplayici_iptal(t, p["id"], r["id"]) and not es.toplayici_iptal(t, p["id"], r["id"])
    with pytest.raises(PermissionError, match="iptal"):
        es.dogrula(anahtar)
    # pilot kapısı beyanı params_json'a yazılır; kod kapısı elle kapanmaz
    d = ps.kapi_ayarla(t, p["id"], "G02", True, "sahip + O&M yazılı izni", "u1")
    assert next(k for k in d["kapilar"] if k["kod"] == "G02")["tamam"] and "G02" not in d["p0_acik"]
    with pytest.raises(ValueError, match="kod testleriyle"):
        ps.kapi_ayarla(t, p["id"], "G05", True, None, "u1")
