"""v2.608 (Faz 5 F5-B) — Genel bakış: dört kart, saf kurallar + DB (bugün yalnız bugünün ölçümü; sapma ≥6 ortak saat; yarın programı KGÜP boyutundan;
riskler yalnız eylem gerektirenler; finans son kayıtlı sonuç + EPİAŞ bildirimi + maruziyet kayıttan)."""
from __future__ import annotations

import datetime as dt
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import genel_bakis_service as gb

UTC = dt.timezone.utc
IST = ZoneInfo("Europe/Istanbul")
SIMDI = dt.datetime(2026, 11, 20, 8, 0, tzinfo=UTC)   # 11:00 TSİ
GUN0 = dt.datetime(2026, 11, 19, 21, 0, tzinfo=UTC)    # 20.11 00:00 TSİ


def _df(bas: dt.datetime, n: int, p50: float = 100.0) -> pd.DataFrame:
    ix = pd.DatetimeIndex([bas + dt.timedelta(hours=h) for h in range(n)])
    return pd.DataFrame({"p50_kw": [p50] * n}, index=ix)


def test_gun_toplami_yerel_gun():
    df = _df(GUN0, 48)
    assert gb._gun_toplami(df, dt.date(2026, 11, 20), IST) == (2400.0, 24)
    assert gb._gun_toplami(df, dt.date(2026, 11, 21), IST) == (2400.0, 24)
    assert gb._gun_toplami(df, dt.date(2026, 11, 22), IST) == (None, 0)   # koşu o günü kapsamıyor → None, sıfır değil
    assert gb._gun_toplami(None, dt.date(2026, 11, 20), IST) == (None, 0)


def test_bugun_karti_sapma_kurali():
    df = _df(GUN0, 48)
    from pvquant.services import durum_sozlugu as ds
    tahmin = ds.tahmin_durumu(SIMDI - dt.timedelta(hours=6), True, SIMDI, son_dogrulama=SIMDI); tahmin["etiket_kosu"] = "yayin"
    hs = {"boyutlar": {"veri": ds.veri_durumu(SIMDI - dt.timedelta(hours=1), SIMDI, SIMDI), "tahmin": tahmin}}
    # 4 ortak saat: sapma yazılmaz, not yazılır
    gercek = pd.Series([80.0] * 4, index=pd.DatetimeIndex([GUN0 + dt.timedelta(hours=h + 6) for h in range(4)]))
    k = gb._bugun_karti({"id": "x"}, df, gercek, dt.date(2026, 11, 20), IST, SIMDI, hs)
    assert k["beklenen_kwh"] == 2400.0 and k["gerceklesen_kwh"] == 320.0 and k["sapma_pct"] is None and "6 ortak saat" in k["sapma_not"]
    assert k["tahmin"]["yayin"] == (SIMDI - dt.timedelta(hours=6)).isoformat() and k["tahmin"]["etiket"] == "yayin" and k["tahmin"]["yas_saat"] == 6.0
    assert k["baglanti"] == "santralim" and k["donem"] == "2026-11-20"
    # 8 ortak saat: sapma = (640 − 800)/800 = −20 %
    gercek8 = pd.Series([80.0] * 8, index=pd.DatetimeIndex([GUN0 + dt.timedelta(hours=h + 6) for h in range(8)]))
    k8 = gb._bugun_karti({"id": "x"}, df, gercek8, dt.date(2026, 11, 20), IST, SIMDI, hs)
    assert k8["sapma_pct"] == -20.0 and k8["ortak_saat"] == 8
    # tahmin yok → kritik, değerler null (sıfır uydurulmaz)
    k0 = gb._bugun_karti({"id": "x"}, None, pd.Series(dtype=float), dt.date(2026, 11, 20), IST, SIMDI, None)
    assert k0["durum"] == "kritik" and k0["beklenen_kwh"] is None and k0["gerceklesen_kwh"] is None and k0["tahmin"]["yayin"] is None


def test_yarin_karti_yukumlu_degil_ve_eylem():
    df = _df(GUN0, 48)
    hs = {"boyutlar": {"kgup": {"durum": "uygulanmiyor", "etiket": "Uygulanmıyor", "neden": "bu santral için program bildirimi yükümlülüğü yok", "adimlar": None, "eksik": []}}}
    k = gb._yarin_karti(df, dt.date(2026, 11, 21), IST, hs, SIMDI)
    assert k["durum"] == "uygulanmiyor" and k["beklenen_kwh"] == 2400.0 and k["eylem"] is None and "doğrulanamaz" in k["not_"]
    hs2 = {"boyutlar": {"kgup": {"durum": "veri_bekleniyor", "etiket": "Veri bekleniyor", "neden": "bildirim beyanı yok", "eksik": ["bildirim_beyani"],
                                 "adimlar": {"tahmin": {"durum": "saglikli"}, "hazirlik": {"durum": "saglikli"}, "bildirim": {"durum": "veri_bekleniyor"}, "kabul": {"durum": "dogrulanamadi"}}}}}
    k2 = gb._yarin_karti(df, dt.date(2026, 11, 21), IST, hs2, SIMDI)
    assert k2["durum"] == "veri_bekleniyor" and "bildirdiğiniz dosyayı" in k2["eylem"] and k2["baglanti"] == "kgup"


@pytest.fixture()
def santral():
    """Dünkü 24 saat + bugün 8 saat ölçüm (bugün = yalnız 8 saat sayılır); koşu 48 saat (bugün + yarın); okunmamış alarm; FEM Ekim kaydı (kısmi);
    Ekim EPİAŞ ön bildirimi (2 kalem). Segment lisanslı serbest (yükümlü), UEVÇB var, program dosyası yok."""
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'GB Kiracı', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'GB GES', 1000, 37.0, 32.0, 'Europe/Istanbul', "
                       "CAST('{\"segment\": \"lisansli_serbest\", \"uevcb\": \"40W000000000001A\"}' AS jsonb))"), {"p": pid, "t": tid})
        for h in range(24):   # dün
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag) VALUES(CAST(:t AS uuid), :p, :ts, 50, 'valid')"),
                      {"t": tid, "p": pid, "ts": GUN0 - dt.timedelta(hours=24 - h)})
        for h in range(8):    # bugün 00–08 TSİ
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag) VALUES(CAST(:t AS uuid), :p, :ts, 80, 'valid')"),
                      {"t": tid, "p": pid, "ts": GUN0 + dt.timedelta(hours=h)})
        rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket) "
                             "VALUES(CAST(:t AS uuid), :p, :r, 'B', 'barhdadi_bennis', 'acik-nwp', '{}', 'yayin') RETURNING id"), {"t": tid, "p": pid, "r": SIMDI - dt.timedelta(hours=6)}).scalar()
        for h in range(48):
            s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw) VALUES(CAST(:t AS uuid), :r, :p, :ts, 100)"),
                      {"t": tid, "r": rid, "p": pid, "ts": GUN0 + dt.timedelta(hours=h)})
        s.execute(text("INSERT INTO alerts(tenant_id, plant_id, rule, severity, message, created_at) VALUES(CAST(:t AS uuid), :p, 'veri_kesintisi', 'warning', 'x', :z)"),
                  {"t": tid, "p": pid, "z": SIMDI - dt.timedelta(days=1)})
        s.execute(text("INSERT INTO finansal_etki_sonuc(tenant_id, plant_id, hesap_zamani, donem_tur, donem_kodu, donem_bas, donem_bit, sozluk_surumu, uretim_json, gelir_json, "
                       "uzlastirma_json, maruziyet_json, toplam_json, meta_json) VALUES(CAST(:t AS uuid), :p, :z, 'ay', '2026-10', '2026-10-01', '2026-10-31', '1', '{}', '{}', '{}', "
                       "CAST(:ma AS jsonb), CAST(:top AS jsonb), CAST(:meta AS jsonb))"),
                  {"t": tid, "p": pid, "z": SIMDI - dt.timedelta(days=2),
                   "ma": '{"aralik_tl": {"p25": -1200.5, "p50": -800.0, "p75": -300.0}, "ufuk": {"bas": "2026-11-19", "bit": "2026-11-25", "gun": 7}, "program_mwh": 12.5}',   # ileri_maruziyet anahtarları
                   "top": '{"tutar_tl": -4321.5, "alacak_tl": 10000.0, "borc_tl": 14321.5, "nitelik": "kismi", "nitelik_ad": "kısmi", "giren": ["satis", "edt"], "eksik": ["kupst"], "isaret": "x"}',
                   "meta": '{"hesap_durumu": "kismi"}'})
        y = str(uuid.uuid4())
        for kalem, yon, tl in (("EDT", "borc", 1500.0), ("SATIS", "alacak", 9000.0)):
            s.execute(text("INSERT INTO uzlastirma_bildirimi(tenant_id, plant_id, donem, surum, yukleme_id, kalem, yon, tutar_tl, olusturma) "
                           "VALUES(CAST(:t AS uuid), :p, '2026-10-01', 'on', :y, :k, :yon, :tl, :z)"), {"t": tid, "p": pid, "y": y, "k": kalem, "yon": yon, "tl": tl, "z": SIMDI - dt.timedelta(days=3)})
    yield tid, pid
    with bakim_baglami() as s:
        for t in ("forecast_values", "forecast_runs", "scada_hourly", "alerts", "finansal_etki_sonuc", "uzlastirma_bildirimi"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tid})


def test_db_dort_kart(santral):
    from pvquant.services import plant_service
    tid, pid = santral
    plant = {**plant_service.getir(tid, pid), "id": pid}
    o = gb.ozet(tid, plant, simdi=SIMDI)
    assert o["bugun_gun"] == "2026-11-20" and o["yarin_gun"] == "2026-11-21" and o["santral"]["kgup_yukumlu"] is True
    b = o["bugun"]
    assert b["beklenen_kwh"] == 2400.0 and b["gerceklesen_kwh"] == 640.0 and b["gerceklesen_saat"] == 8      # dünkü 24 saat sayılmadı
    assert b["sapma_pct"] == -20.0 and b["ortak_saat"] == 8 and b["tahmin"]["etiket"] == "yayin" and b["olcum"]["durum"] == "saglikli"
    assert b["tahmin"]["yayin"] == (SIMDI - dt.timedelta(hours=6)).isoformat() and b["tahmin"]["yas_saat"] == 6.0   # yayımlanmış koşudan (süzgeçli)
    assert b["durum"] == "saglikli"
    y = o["yarin"]
    assert y["beklenen_kwh"] == 2400.0 and y["program"]["adimlar"]["tahmin"]["durum"] == "saglikli" and y["program"]["adimlar"]["kabul"]["durum"] == "dogrulanamadi"
    assert y["durum"] == "veri_bekleniyor" and "program dosyasını üretin" in y["eylem"]
    r = o["riskler"]
    kodlar = [x["kod"] for x in r["liste"]]
    assert "alarm" in kodlar and "mutabakat" in kodlar and "olcum" not in kodlar     # ölçüm güncel; alarm okunmamış; Ekim nihai bildirimi yok (20.11 > 16.11)
    assert r["durum"] == "dikkat" and r["kiraci"]["santral"] == 1 and r["kiraci"]["baglanti"] == "portfoy"
    f = o["finans"]
    assert f["son_sonuc"]["tutar_tl"] == -4321.5 and f["son_sonuc"]["hesap_durumu"] == "kismi" and f["son_sonuc"]["nitelik"] == "tahmini"
    assert f["son_sonuc"]["maruziyet"]["aralik_tl"]["p50"] == -800.0 and f["son_sonuc"]["maruziyet"]["nitelik"] == "senaryo"
    assert f["epias"]["donem"] == "2026-10" and f["epias"]["borc_tl"] == 1500.0 and f["epias"]["alacak_tl"] == 9000.0 and f["epias"]["net_tl"] == 7500.0
    assert f["epias"]["resmi_durum"] == "dogrulanmadi" and f["hesaplanamiyor"] is None and f["durum"] == "dikkat"
    assert o["genel"]["durum"] == "dikkat" and set(o["genel"]["eylem_gereken"]) == {"riskler", "finans"}


def test_uc_404_ve_sozlesme(monkeypatch):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": uuid.UUID(p), "name": "X", "tz": "Europe/Istanbul", "capacity_kwp": 1.0, "params_json": {}} if p.startswith("1") else None)
    monkeypatch.setattr(gb, "ozet", lambda t, plant, simdi=None: {"santral": {"id": plant["id"], "ad": plant["name"]}, "genel": {"durum": "saglikli"}})
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        assert c.get("/v1/plants/00000000-0000-4000-8000-000000000000/genel-bakis").status_code == 404
        y = c.get("/v1/plants/11111111-1111-4111-8111-111111111111/genel-bakis")
        assert y.status_code == 200 and y.json()["santral"]["id"] == "11111111-1111-4111-8111-111111111111"   # kimlik dizge olarak geçer
    finally:
        api_main.app.dependency_overrides.clear()
