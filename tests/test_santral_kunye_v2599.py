"""v2.599 (Faz 4 F4-E, Stage 6) — tarihli santral kimliği: güç tanımları tek kaynak (EAK kuralı birebir), künye sürümleme (kapanış,
taşıma, çift yazım, denetim), tarihli okuma, plant_service bağı, beyan uyarısı, API (GET/POST, dış API alanları), yükleme kapasite
tavanı AC, EPİAŞ anomali tavanı EAK."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.io.ingestion import RowFlag
from pvquant.io.ingestion import validate as vd
from pvquant.services import kgup_service as kg
from pvquant.services import plant_service as ps
from pvquant.services import santral_kunye_service as sk


# ───────────────────────────────────────────── saf ─────────────────────────────────────────────
def test_guc_tanimlari_eak_kurali_eak_etkin_ile_birebir():
    p = {"capacity_kwp": 4514.0, "ac_limit_kw": 3600.0, "params_json": {}}
    g = sk.guc_tanimlari(p, date(2026, 9, 7))
    assert g["dc_kwp"] == 4514.0 and g["ac_kw"] == 3600.0 and g["eak"] == {"eak_mw": 3.6, "kaynak": "ac_tavani"} and g["ihracat_siniri_kw"] == 3600.0
    assert g["kaynaklar"] == {"dc": "plants", "ac": "plants", "eak": "ac_tavani", "kunye": False}
    assert kg.eak_etkin(p, date(2026, 9, 7)) == g["eak"]
    p["params_json"] = {"eak_kw": 3000, "eak_gecici": {"kw": 1500, "bitis": "2026-09-10"}}
    assert sk.guc_tanimlari(p, date(2026, 9, 7))["eak"] == {"eak_mw": 1.5, "kaynak": "gecici", "bitis": "2026-09-10"}
    assert sk.guc_tanimlari(p, date(2026, 9, 11))["eak"]["kaynak"] == "eak_alani"
    # künye verilirse plants'ın önüne geçer
    k = {"dc_kwp": 5000.0, "ac_kw": 4000.0, "eak_kw": 3500.0}
    g2 = sk.guc_tanimlari(p, date(2026, 9, 11), k)
    assert g2["dc_kwp"] == 5000.0 and g2["ac_kw"] == 4000.0 and g2["eak"] == {"eak_mw": 3.5, "kaynak": "eak_alani"} and g2["kaynaklar"]["kunye"] is True
    assert sk.guc_tanimlari({"capacity_kwp": 1000.0, "params_json": '{"eak_kw": 5000}'}, date(2026, 1, 1))["eak"]["eak_mw"] == 1.0   # kurulu gücü aşamaz
    assert sk.guc_tanimlari({"capacity_kwp": 1000.0}, date(2026, 1, 1))["eak"] == {"eak_mw": 1.0, "kaynak": "kurulu_guc"}


def test_validate_kapasite_ustu_tavani_ac():
    ix = pd.date_range("2026-06-21 10:00", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({"power_kw": [900.0, 950.0, 1100.0]}, index=ix)
    out_ac, _ = vd.validate(df, capacity_kwp=1200.0, latitude=37.9, longitude=32.5, ac_limit_kw=900.0)
    out_dc, _ = vd.validate(df, capacity_kwp=1200.0, latitude=37.9, longitude=32.5)
    assert out_ac["flag"].tolist() == [RowFlag.VALID.value, RowFlag.OVER_CAPACITY.value, RowFlag.OVER_CAPACITY.value]   # 945 kW = 1,05×AC tavanı
    assert out_dc["flag"].tolist() == [RowFlag.VALID.value, RowFlag.VALID.value, RowFlag.VALID.value]                  # AC bilinmiyorsa 1,05×DC = 1260


def test_dogrulama_kurallari():
    with pytest.raises(ValueError, match="bilinmeyen"):
        sk._dogrula({"yok": 1})
    with pytest.raises(ValueError, match="negatif"):
        sk._dogrula({"dc_kwp": -1})
    with pytest.raises(ValueError, match="baglanti_turu"):
        sk._dogrula({"baglanti_turu": "hava"})
    with pytest.raises(ValueError, match="1,5 katını"):
        sk._dogrula({"dc_kwp": 1000, "ac_kw": 2000})
    assert sk._dogrula({"ac_kw": "900", "segment": "lisansli_serbest", "eic": ""}) == {"ac_kw": 900.0, "segment": "lisansli_serbest", "eic": None}


# ───────────────────────────────────────────── DB ──────────────────────────────────────────────
@pytest.fixture()
def kiraci():
    tid = str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'kunye-test', 'active')"), {"t": tid})
    yield tid
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
        for t in ("portfoy_uyelik", "dsg_grubu", "portfoy", "scada_hourly", "ingestion_batches", "santral_kunye"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid}); s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": tid})


def test_db_olustur_ilk_surum_yeni_surum_kapanis_cift_yazim_denetim(kiraci):
    tid = kiraci
    pid = ps.olustur(tid, name="Künye GES", lat=37.9, lon=32.5, tz="Europe/Istanbul", capacity_kwp=1200.0, ac_limit_kw=1000.0)
    g0 = sk.guncel(tid, pid)
    assert g0 and g0["kaynak"] == "kayit" and g0["dc_kwp"] == 1200.0 and g0["ac_kw"] == 1000.0 and g0["gecerli_bit"] is None and g0["segment"] is None and g0["gecerli_bas"] == "2000-01-01"
    # yeni sürüm: 1.10.2026'dan DC 1500, segment + UEVÇB; verilmeyen AC taşınır
    g1 = sk.yeni_surum(tid, pid, gecerli_bas="2026-10-01", aktor_id=uuid.uuid4(), dc_kwp=1500, segment="lisansli_serbest", uevcb_kod="40W000000000001X", eak_kw=950)
    assert g1["dc_kwp"] == 1500.0 and g1["ac_kw"] == 1000.0 and g1["segment"] == "lisansli_serbest" and g1["gecerli_bas"] == "2026-10-01"
    th = sk.tarihce(tid, pid)
    assert len(th) == 2 and th[1]["gecerli_bit"] == "2026-10-01" and th[0]["gecerli_bit"] is None
    assert sk.guncel(tid, pid, date(2026, 9, 30))["dc_kwp"] == 1200.0 and sk.guncel(tid, pid, date(2026, 10, 1))["dc_kwp"] == 1500.0   # tarihli okuma
    row = ps.getir(tid, pid)
    assert float(row["capacity_kwp"]) == 1500.0 and float(row["ac_limit_kw"]) == 1000.0                     # plants güncel görünümü
    pj = row["params_json"]; assert pj["segment"] == "lisansli_serbest" and pj["uevcb"] == "40W000000000001X" and pj["eak_kw"] == 950.0   # params_json çift yazım
    assert kg.eak_etkin(row, date(2026, 10, 2)) == {"eak_mw": 0.95, "kaynak": "eak_alani"} and sk.guc_tanimlari_db(tid, row)["kaynaklar"]["kunye"] is True
    with sistem_baglami() as s:   # denetim_izi uygulama rolüne açık değil
        iz = s.execute(text("SELECT eylem, ayrinti FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid) AND eylem = 'santral_kunye'"), {"t": tid}).fetchall()
    assert len(iz) == 1 and iz[0].ayrinti["degisen"]["dc_kwp"] == 1500.0 and iz[0].ayrinti["onceki"]["dc_kwp"] == 1200.0
    with pytest.raises(ValueError, match="sonra olmalı"):
        sk.yeni_surum(tid, pid, gecerli_bas="2026-09-15", dc_kwp=1600)      # var olan sürümün başlangıcından önce olamaz
    sk.yeni_surum(tid, pid, gecerli_bas="2026-10-01", ac_kw=1100)           # aynı gün ikinci düzeltme: satır yerinde güncellenir
    assert len(sk.tarihce(tid, pid)) == 2 and sk.guncel(tid, pid)["ac_kw"] == 1100.0 and sk.guncel(tid, pid)["dc_kwp"] == 1500.0
    with pytest.raises(ValueError, match="belge adı"):
        sk.yeni_surum(tid, pid, gecerli_bas="2026-11-01", dogrulama="belgeli", dc_kwp=1600)
    # geçmişe sürüm bugünü kapsamıyorsa plants değişmez — gelecek sürüm
    yarin = (date.today() + timedelta(days=1)).isoformat()
    sk.yeni_surum(tid, pid, gecerli_bas=yarin, dc_kwp=2000)
    assert float(ps.getir(tid, pid)["capacity_kwp"]) == 1500.0 and sk.guncel(tid, pid)["dc_kwp"] == 1500.0 and sk.guncel(tid, pid, date.today() + timedelta(days=1))["dc_kwp"] == 2000.0


def test_db_plant_service_guncelle_kunye_acar_ve_denetim(kiraci):
    tid = kiraci
    pid = ps.olustur(tid, name="G GES", lat=37.9, lon=32.5, tz="Europe/Istanbul", capacity_kwp=1000.0)
    ps.guncelle(tid, pid, aktor_id=uuid.uuid4(), name="G GES yeni", ac_limit_kw=800.0)
    row = ps.getir(tid, pid)
    assert row["name"] == "G GES yeni" and float(row["ac_limit_kw"]) == 800.0
    th = sk.tarihce(tid, pid)
    assert len(th) == 2 and th[0]["ac_kw"] == 800.0 and th[0]["dc_kwp"] == 1000.0 and th[0]["kaynak"] == "beyan" and th[1]["gecerli_bit"] == date.today().isoformat()
    ps.guncelle(tid, pid, name="G GES yeni 2")                       # güç değişmedi → sürüm açılmaz
    assert len(sk.tarihce(tid, pid)) == 2
    with sistem_baglami() as s:
        n = s.execute(text("SELECT count(*) FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid) AND eylem = 'santral_guncelle'"), {"t": tid}).scalar()
    assert n == 2
    # künyesiz eski santral (doğrudan INSERT) güncellenince önce ilk sürüm açılır
    pid2 = str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'Eski GES', 500, 37.0, 32.0, 'Europe/Istanbul', '{}')"), {"p": pid2, "t": tid})
    assert sk.guncel(tid, pid2) is None and sk.guc_tanimlari_db(tid, ps.getir(tid, pid2))["kaynaklar"]["kunye"] is False
    ps.guncelle(tid, pid2, capacity_kwp=600.0)
    th2 = sk.tarihce(tid, pid2)
    assert len(th2) == 2 and th2[1]["dc_kwp"] == 500.0 and th2[0]["dc_kwp"] == 600.0


def test_db_beyan_uyarisi_ve_api(kiraci):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import api_anahtari, gecerli_kullanici
    tid = kiraci
    pid = ps.olustur(tid, name="API GES", lat=37.9, lon=32.5, tz="Europe/Istanbul", capacity_kwp=1200.0, ac_limit_kw=1000.0)
    ps.params_birlestir(tid, pid, dsg_kodu="DSG-ANK-07")
    uy = sk.beyan_uyarilari(tid, ps.getir(tid, pid))
    assert len(uy) == 1 and uy[0]["kod"] == "dsg_beyani" and uy[0]["portfoy_id"] is None and "üyelik ekleyin" in uy[0]["oneri"]
    with tenant_baglami(tid) as s:   # DSG koduyla portföy var ama üyelik yok → aday portföy önerilir
        pfid = s.execute(text("INSERT INTO portfoy(tenant_id, ad, tur, gecerli_bas) VALUES(CAST(:t AS uuid), 'Anadolu DSG', 'dsg', '2026-01-01') RETURNING id"), {"t": tid}).scalar()
        s.execute(text("INSERT INTO dsg_grubu(portfoy_id, tenant_id, dsg_kodu) VALUES(:p, CAST(:t AS uuid), 'DSG-ANK-07')"), {"p": pfid, "t": tid})
    assert sk.beyan_uyarilari(tid, ps.getir(tid, pid))[0]["portfoy_id"] == str(pfid)
    sub = str(uuid.uuid4())
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": sub, "tenant_id": tid, "role": "admin", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/plants/{pid}/kunye"); j = r.json()
        assert r.status_code == 200 and j["guncel"]["kaynak"] == "kayit" and j["guc"]["eak"]["kaynak"] == "ac_tavani" and j["uyarilar"][0]["kod"] == "dsg_beyani" and "alanlar" in j["sozluk"]
        r2 = c.post(f"/v1/plants/{pid}/kunye", json={"gecerli_bas": "2026-10-01", "dc_kwp": 1300, "baglanti_turu": "dagitim", "gerilim_kv": 34.5, "olcum_siniri": "pcc_net"})
        assert r2.status_code == 200 and r2.json()["guncel"]["dc_kwp"] == 1300.0 and r2.json()["guncel"]["baglanti_turu"] == "dagitim" and len(r2.json()["tarihce"]) == 2
        assert c.post(f"/v1/plants/{pid}/kunye", json={"gecerli_bas": "2026-09-01", "dc_kwp": 1}).status_code == 422
        assert c.post(f"/v1/plants/{pid}/kunye", json={"gecerli_bas": "2026-11-01", "baglanti_turu": "hava"}).status_code == 422
        assert c.get(f"/v1/plants/{uuid.uuid4()}/kunye").status_code == 404
        # dış API: künye alanları
        api_main.app.dependency_overrides[api_anahtari("tahmin:oku")] = lambda: {"tenant_id": tid, "kapsam": ["tahmin:oku"]}
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)
    ds = [x for x in _dis_santraller(tid) if x["id"] == pid][0]
    assert ds["dc_kwp"] == 1300.0 and ds["ac_kw"] == 1000.0 and ds["baglanti_turu"] == "dagitim" and ds["kunye_gecerli_bas"] == "2026-10-01" and ds["kapasite_kwp"] == 1300.0


def _dis_santraller(tid):
    import apps.api.main as api_main
    return api_main.dis_santraller({"tenant_id": tid, "kapsam": ["tahmin:oku"]})


def test_db_epias_anomali_tavani_eak(kiraci, monkeypatch):
    from pvquant.services import epias_uretim_service as eu
    tid = kiraci
    pid = ps.olustur(tid, name="EPİAŞ GES", lat=37.9, lon=32.5, tz="Europe/Istanbul", capacity_kwp=5000.0, ac_limit_kw=4000.0)
    ps.params_birlestir(tid, pid, epias_santral_id="123", eak_kw=3000)
    plant = ps.getir(tid, pid)
    ix = pd.date_range("2026-11-01", periods=24, freq="h", tz="UTC")
    seri = pd.Series(np.where((ix.hour >= 6) & (ix.hour <= 16), 3.2, 0.0), index=ix)   # 3,2 MW: EAK 3 MW'ı aşar, DC 5 MW'ın altında
    monkeypatch.setattr(eu, "cek", lambda plant_, bas, bitis, istemci=None: seri)
    monkeypatch.setattr(eu, "uygun_mu", lambda p_: (True, None))
    r = eu.yukle(tid, plant, gun=2, istemci=object())
    with tenant_baglami(tid) as s:
        fl = s.execute(text("SELECT flag, count(*) FROM scada_hourly WHERE plant_id = CAST(:p AS uuid) GROUP BY 1"), {"p": pid}).fetchall()
    d = dict(fl)
    assert r["durum"] == "ok" and d.get("anomali", 0) == 11 and d.get("valid", 0) == 13   # tavan EAK (3 MW) → 11 gündüz saati anomali
