"""v2.550 (Aşama 1, D4/D5) — DB'li kabul: örnekler cihaz kimliğiyle yazılır; saatlik toplama tam saatleri scada_hourly'ye, her saati (kısmi dâhil)
kaynak_saatlik'e yazar; kapanış örneği sonradan gelince kısmi → tam, yeni REVİZYON; gölge görünüm seçimi yapar. Test DB (docker pvq-test-db) gerekir."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import canli_ornekleme_service as co
from pvquant.services import kaynak_secim_service as ks

T0 = datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc)


@pytest.fixture
def santral():
    t, p = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name) VALUES(:i, 'T')"), {"i": t})
    with tenant_baglami(t) as s:
        s.execute(text("INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) VALUES(:p, :t, 'P', 38.4, 34.6, 'Europe/Istanbul', 1000)"), {"p": p, "t": t})
    yield {"id": p, "tenant_id": t, "name": "P", "params_json": {"veri_yolu": {"tur": "modbus_sunspec", "periyot_dk": 15}}}
    with sistem_baglami() as s:
        for tbl in ("kaynak_saatlik", "scada_hourly", "ingestion_batches", "canli_ornek"):
            s.execute(text(f"DELETE FROM {tbl} WHERE plant_id=:p"), {"p": p})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": p}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": t})


def _ornek(ts, guc_w, wh, cihaz="SN-A"):
    return {"ts_utc": ts, "cihaz_id": cihaz, "sinir": "inverter_ac", "profil": "1xx", "guc_w": guc_w, "enerji_wh": wh, "dc_guc_w": None, "durum_kodu": 4, "olaylar": []}


def test_toplama_tam_kismi_revizyon_ve_golge(santral):
    t, p = santral["tenant_id"], santral
    # 06:00–07:00 tam (5 örnek, kapanış dâhil), 07:00–07:45 kısmi; ikinci cihaz aynı saatlerde → PK çakışmaz
    for m, wh in ((0, 0), (15, 25000), (30, 50000), (45, 75000), (60, 100000), (75, 125000), (90, 150000), (105, 175000)):
        assert co.ornek_yaz(t, p, _ornek(T0 + timedelta(minutes=m), 100000, wh)) == 1
        assert co.ornek_yaz(t, p, _ornek(T0 + timedelta(minutes=m), 50000, wh // 2, "SN-B")) == 1
    assert co.ornek_yaz(t, p, _ornek(T0, 1, 1)) == 0   # aynı cihaz + zaman → DO NOTHING (ham örnek değiştirilmez)
    r = co.saatlik_topla(t, p, simdi=T0 + timedelta(hours=2), geri_saat=3)
    assert r["durum"] == "ok" and r["n_yazilan"] == 1 and r["n_kismi"] == 2 and r["n_golge"] == 4 and r["n_revizyon"] == 0   # 1 tam saat (iki cihaz toplandı), 2 kısmi (iki cihaz)
    with tenant_baglami(t) as s:
        sh = s.execute(text("SELECT ts_utc, power_kw, energy_kwh, flag FROM scada_hourly WHERE plant_id=:p ORDER BY ts_utc"), {"p": p["id"]}).all()
        assert len(sh) == 1 and sh[0][0] == T0 and sh[0][2] == pytest.approx(150.0) and sh[0][1] == pytest.approx(150.0) and sh[0][3] == "valid"   # SN-A 100 + SN-B 50
        g = s.execute(text("SELECT ts_utc, cihaz_id, tamlik, energy_kwh, revizyon FROM kaynak_saatlik WHERE plant_id=:p ORDER BY ts_utc, cihaz_id, revizyon"), {"p": p["id"]}).all()
        assert [(x[1], x[2], x[4]) for x in g] == [("SN-A", "measured_complete", 1), ("SN-B", "measured_complete", 1), ("SN-A", "measured_partial", 1), ("SN-B", "measured_partial", 1)]
        assert g[2][3] == pytest.approx(75.0)
    # tekrar tur: değişiklik yok → yeni revizyon yok, scada_hourly değişmez
    r2 = co.saatlik_topla(t, p, simdi=T0 + timedelta(hours=2), geri_saat=3)
    assert r2["n_revizyon"] == 0 and r2["n_yazilan"] == 0
    # 08:00 kapanış örneği geliyor → 07:00 saati tam olur → revizyon 2, scada_hourly'ye yazılır
    co.ornek_yaz(t, p, _ornek(T0 + timedelta(minutes=120), 100000, 200000)); co.ornek_yaz(t, p, _ornek(T0 + timedelta(minutes=120), 50000, 100000, "SN-B"))
    r3 = co.saatlik_topla(t, p, simdi=T0 + timedelta(hours=2, minutes=5), geri_saat=3)
    assert r3["n_revizyon"] == 2 and r3["n_yazilan"] == 1 and r3["n_kismi"] == 0
    with tenant_baglami(t) as s:
        g2 = s.execute(text("SELECT cihaz_id, tamlik, revizyon, energy_kwh FROM kaynak_saatlik WHERE plant_id=:p AND ts_utc=:ts ORDER BY cihaz_id, revizyon"), {"p": p["id"], "ts": T0 + timedelta(hours=1)}).all()
        assert [(x[0], x[1], x[2]) for x in g2] == [("SN-A", "measured_partial", 1), ("SN-A", "measured_complete", 2), ("SN-B", "measured_partial", 1), ("SN-B", "measured_complete", 2)]   # eski satır silinmedi
        assert s.execute(text("SELECT count(*) FROM scada_hourly WHERE plant_id=:p"), {"p": p["id"]}).scalar() == 2
    # gölge görünüm: 07:00 için son revizyon seçilir, alternatif (SN-B) sayılır, mevcut scada_hourly toplamıyla fark
    gg = ks.golge_gorunum(t, p, T0, T0 + timedelta(hours=3))
    s7 = next(x for x in gg["saatler"] if x["ts_utc"].startswith("2026-11-09T07:00"))
    assert s7["secilen"]["revizyon"] == 2 and s7["secilen"]["tamlik"] == "measured_complete" and s7["alternatif_sayisi"] == 1
    assert s7["mevcut"]["kaynak"] == "modbus_sunspec" and s7["fark_kwh"] == pytest.approx(-50.0)   # seçilen tek cihaz (100) − santral toplamı (150)
    assert gg["ozet"]["n_tam"] == 2 and gg["ozet"]["n_mevcut"] == 2
    d = co.durum(t, p)
    assert d["n_cihaz"] == 2 and d["son_saat"] == T0 + timedelta(hours=1)
