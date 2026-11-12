"""v2.601 (Faz 4 F4-G, Stage 8) — fiyat sürümü (M6) ve finansal motor sınırı: piyasa_fiyat_surum yalnız-ekleme tarihçesi (değişen satır yeni sürüm,
aynı değer tekrar yazılmaz), `fiyatlar(itibariyle=)` o andaki sürümü okur, `fiyat_sha16` içerik damgası; FEM meta girdi referansları + hesap_durumu +
cikti_surumu; deterministiklik (aynı girdi → aynı sonuç, aynı sha) ve `ayni_girdili_kayit` (gece işi tekrar yazmaz); portföy finans DSG'yi bir kez kullanır."""
from __future__ import annotations

import json
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.services import finansal_etki_service as fe
from pvquant.services import piyasa_service as ps

TZ = "Europe/Istanbul"


def _temizle(bas: str):
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM piyasa_fiyat WHERE ts_utc >= :a"), {"a": bas})   # 2097+ yalnız bu testin satırları
    with bakim_baglami() as s:   # sürüm tablosu yalnız ekleme: test satırları bakım bağlamında temizlenir
        s.execute(text("DELETE FROM piyasa_fiyat_surum WHERE ts_utc >= :a"), {"a": bas})


# ───────────────────────────────────────────── saf ─────────────────────────────────────────────
def test_fiyat_sha16_icerik_damgasi():
    idx = pd.date_range("2026-09-01 00:00", periods=3, freq="h", tz="UTC")
    a = pd.DataFrame({"ptf": [2000.0, 2100.0, 2200.0], "smf": [1900.0, None, 2300.0], "yon": ["acik", None, "fazla"], "kaynak": ["epias", "epias", "epias"]}, index=idx)
    b = a.copy(); b.loc[idx[1], "ptf"] = 2100.0000001   # 1e-6 altı fark → aynı damga
    c = a.copy(); c.loc[idx[1], "ptf"] = 2101.0
    d = ps.senaryo_fiyat(idx)
    assert ps.fiyat_sha16(a) == ps.fiyat_sha16(b) == ps.fiyat_sha16(a.iloc[::-1]) and len(ps.fiyat_sha16(a)) == 16
    assert ps.fiyat_sha16(a) != ps.fiyat_sha16(c) != ps.fiyat_sha16(d) and ps.fiyat_sha16(pd.DataFrame()) == ps.fiyat_sha16(None)


def test_hesap_durumu_saf():
    u_tam = {"gerceklesen": {"saat": 24, "beklenen_saat": 24}}
    assert fe.hesap_durumu(u_tam, {"epias_saat": 24, "senaryo_saat": 0, "yon_varsayilan_saat": 0}, None) == "tam"
    assert fe.hesap_durumu(u_tam, {"epias_saat": 20, "senaryo_saat": 4, "yon_varsayilan_saat": 4}, None) == "kismi"
    assert fe.hesap_durumu({"gerceklesen": {"saat": 20, "beklenen_saat": 24}}, {"epias_saat": 24, "senaryo_saat": 0}, None) == "kismi"
    assert fe.hesap_durumu(u_tam, {"epias_saat": 0, "senaryo_saat": 24}, None) == "senaryo"
    assert fe.hesap_durumu(u_tam, {"epias_saat": 24, "senaryo_saat": 0}, {"pozisyon": {}}) == "senaryo"
    assert fe.hesap_durumu({"gerceklesen": {"saat": 0, "beklenen_saat": 24}}, {"epias_saat": 24, "senaryo_saat": 0}, None) == "hesaplanamadi"
    assert fe.CIKTI_SURUMU == "1.1" and set(fe.HESAP_DURUMLARI) == {"tam", "kismi", "senaryo", "hesaplanamadi"}


# ───────────────────────────────────────────── DB: fiyat sürümü ─────────────────────────────────────────────
def test_db_fiyat_surumu_yalniz_ekleme_ve_itibariyle():
    bas = "2098-03-01 00:00:00+00"
    idx = pd.date_range("2098-03-01 00:00", periods=3, freq="h", tz="UTC")
    _temizle(bas)
    try:
        # 1) gün öncesi PTF (smf/yön yok) → sürüm 1
        ps.kaydet(pd.DataFrame({"ptf": [1000.0, 1100.0, 1200.0], "smf": [None] * 3, "yon": [None] * 3, "kaynak": "epias_gop"}, index=idx))
        t1 = datetime.now(timezone.utc)
        with sistem_baglami() as s:
            n1 = s.execute(text("SELECT count(*) FROM piyasa_fiyat_surum WHERE ts_utc >= :a"), {"a": bas}).scalar()
        assert n1 == 3
        # 2) aynı değer tekrar → sürüm EKLENMEZ
        ps.kaydet(pd.DataFrame({"ptf": [1000.0, 1100.0, 1200.0], "smf": [None] * 3, "yon": [None] * 3, "kaynak": "epias_gop"}, index=idx))
        with sistem_baglami() as s:
            assert s.execute(text("SELECT count(*) FROM piyasa_fiyat_surum WHERE ts_utc >= :a"), {"a": bas}).scalar() == 3
        # 3) gece tam satırı (smf/yön + PTF düzeltmesi 2. saatte) → değişen 3 satır yeni sürüm (kaynak epias → hepsi değişti)
        time.sleep(0.05)   # alinma sıralaması için
        ps.kaydet(pd.DataFrame({"ptf": [1000.0, 1150.0, 1200.0], "smf": [900.0, 950.0, 1000.0], "yon": ["acik", "fazla", "dengede"], "kaynak": "epias"}, index=idx))
        with sistem_baglami() as s:
            assert s.execute(text("SELECT count(*) FROM piyasa_fiyat_surum WHERE ts_utc >= :a"), {"a": bas}).scalar() == 6
        guncel = ps.fiyatlar(idx)
        eski = ps.fiyatlar(idx, itibariyle=t1)
        assert list(guncel["ptf"]) == [1000.0, 1150.0, 1200.0] and list(guncel["kaynak"]) == ["epias"] * 3
        assert list(eski["ptf"]) == [1000.0, 1100.0, 1200.0] and list(eski["kaynak"]) == ["epias_gop"] * 3 and eski["smf"].isna().all()
        assert ps.fiyat_sha16(guncel) != ps.fiyat_sha16(eski)
        # itibariyle hiçbir sürümden önce → tamamı senaryo (uydurulmaz: kaynak 'senaryo')
        hic = ps.fiyatlar(idx, itibariyle=t1 - timedelta(days=1))
        assert list(hic["kaynak"]) == ["senaryo"] * 3
        th = ps.surum_tarihcesi(idx[1].to_pydatetime())
        assert len(th) == 2 and th[0]["ptf"] == 1150.0 and th[1]["ptf"] == 1100.0 and th[1]["kaynak"] == "epias_gop"
        # uygulama rolü (pvq_app; kiracı bağlamı) güncelleyemez / silemez — sistem bağlamı rol değiştirmez (DB sahibi), orada sınanmaz
        with pytest.raises(Exception, match="permission denied"), tenant_baglami(str(uuid.uuid4())) as s:
            s.execute(text("DELETE FROM piyasa_fiyat_surum WHERE ts_utc >= :a"), {"a": bas})
        with sistem_baglami() as s:
            assert s.execute(text("SELECT count(*) FROM piyasa_fiyat_surum WHERE ts_utc >= :a"), {"a": bas}).scalar() == 6
    finally:
        _temizle(bas)


# ───────────────────────────────────────────── DB: FEM deterministiklik ─────────────────────────────────────────────
@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    pj = '{"tarife": {"tip": "ptf"}, "segment": "lisansli_serbest"}'
    bas = "2097-06-01 00:00:00+00"
    _temizle(bas)
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'fs-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) VALUES(:p, :t, 'FS GES', 1000, 900, 37.0, 32.0, :tz, CAST(:pj AS jsonb))"),
                  {"p": pid, "t": tid, "tz": TZ, "pj": pj})
        for g in (1, 2):
            gun0 = pd.Timestamp(f"2097-06-{g:02d}", tz=TZ)
            for h in range(24):
                ts = (gun0 + pd.Timedelta(hours=h)).tz_convert("UTC").to_pydatetime()
                kw = float(100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk, kaynak, alinma_zamani) "
                               "VALUES(:t, :p, :ts, :kw, :kw, 'valid', 60, 'scada_dosya', '2097-06-03 10:00+00')"), {"t": tid, "p": pid, "ts": ts, "kw": kw})
            ra = (gun0 - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=3)
            rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket) "
                                 "VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}', 'yayin') RETURNING id"), {"t": tid, "p": pid, "ra": ra.to_pydatetime()}).scalar()
            for h in range(24):
                ts = (gun0 + pd.Timedelta(hours=h)).tz_convert("UTC").to_pydatetime()
                kw = (float(100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0) * 1.1
                s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw, physics_kw) VALUES(:t, :r, :p, :ts, :kw, :kw, :kw, :kw)"),
                          {"t": tid, "r": rid, "p": pid, "ts": ts, "kw": kw})
    # 1 Haziran 2097: EPİAŞ fiyatı (sürüm 1)
    idx = pd.date_range(pd.Timestamp("2097-06-01", tz=TZ), periods=24, freq="h").tz_convert("UTC")
    ps.kaydet(pd.DataFrame({"ptf": 2000.0, "smf": 1900.0, "yon": "acik", "kaynak": "epias"}, index=idx))
    plant = {"id": pid, "name": "FS GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": TZ, "params_json": {"tarife": {"tip": "ptf"}, "segment": "lisansli_serbest"}, "archived": False}
    yield tid, plant, idx
    with bakim_baglami() as s:
        for t in ("finansal_etki_sonuc", "forecast_values", "forecast_runs", "scada_hourly"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})
    _temizle(bas)


def _karsilastirilabilir(o: dict) -> str:
    m = {k: v for k, v in o["meta"].items() if k not in ("hesap_zamani",)}
    return json.dumps({**{k: v for k, v in o.items() if k != "meta"}, "meta": m}, sort_keys=True, default=str)


def test_db_fem_deterministik_girdi_referanslari_ve_fiyat_surumu(santral):
    tid, plant, idx = santral
    bugun = date(2097, 6, 3)
    o1 = fe.ozet(tid, plant, "2097-06-01", bugun=bugun)
    o2 = fe.ozet(tid, plant, "2097-06-01", bugun=bugun)
    assert _karsilastirilabilir(o1) == _karsilastirilabilir(o2)   # aynı girdi → bayt eşit sonuç (hesap zamanı hariç)
    m = o1["meta"]
    assert m["cikti_surumu"] == "1.1" and m["hesap_durumu"] == "tam" and m["fiyat"]["sha16"] == m["girdi"]["fiyat"]["sha16"] and m["fiyat"]["itibariyle"] is None
    g = m["girdi"]
    assert g["sha16"] == o2["meta"]["girdi"]["sha16"] and len(g["sha16"]) == 16
    assert g["olcum"]["saat"] == 24 and g["olcum"]["son_alinma"].startswith("2097-06-03T10:00") and g["olcum"]["kaynaklar"] == ["scada_dosya"] and g["olcum"]["sinir"] == "plant_gross_ac"
    assert g["olcum"]["tablo"] == "scada_hourly" and g["olcum"]["sayac"] is None and g["sozlukler"]["fem"] == fe.SURUM
    assert g["program"]["kaynak"] == "oneri" and len(g["program"]["kosular"]) == 1 and g["program"]["not"] is None
    assert g["fiyat"]["epias_saat"] == 24 and g["fiyat"]["senaryo_saat"] == 0 and g["sozlukler"]["kural_sicili_sha"] and g["sozlukler"]["kalite"]
    # 2 Haziran: fiyat yok → senaryo; hesap durumu senaryo; sha farklı
    o3 = fe.ozet(tid, plant, "2097-06-02", bugun=bugun)
    assert o3["meta"]["hesap_durumu"] == "senaryo" and o3["meta"]["girdi"]["sha16"] != g["sha16"]
    # kaydet → aynı girdiyle ikinci kayıt YAZILMAZ (ayni_girdili_kayit), fiyat düzeltmesi gelince yazılır
    kid = fe.kaydet(tid, o1, plant["id"])
    assert fe.ayni_girdili_kayit(tid, plant, o2) == kid
    t_once = datetime.now(timezone.utc)
    ps.kaydet(pd.DataFrame({"ptf": 2500.0, "smf": 1900.0, "yon": "acik", "kaynak": "epias"}, index=idx))   # EPİAŞ düzeltmesi: sürüm 2
    o4 = fe.ozet(tid, plant, "2097-06-01", bugun=bugun)
    assert o4["meta"]["girdi"]["fiyat"]["sha16"] != g["fiyat"]["sha16"] and fe.ayni_girdili_kayit(tid, plant, o4) is None
    assert o4["gelir"]["bilesenler"][0]["tutar_tl"] > o1["gelir"]["bilesenler"][0]["tutar_tl"]   # PTF endeksli tarife yeni fiyatı görür
    # M6: kayıtlı sonuç eski fiyat sürümüyle yeniden kurulur
    o5 = fe.ozet(tid, plant, "2097-06-01", bugun=bugun, itibariyle=t_once)
    assert o5["meta"]["girdi"]["fiyat"]["sha16"] == g["fiyat"]["sha16"] and o5["meta"]["fiyat"]["itibariyle"] is not None
    assert o5["gelir"]["bilesenler"][0]["tutar_tl"] == o1["gelir"]["bilesenler"][0]["tutar_tl"] and o5["toplam"]["tutar_tl"] == o1["toplam"]["tutar_tl"]
    ge = fe.gecmis(tid, plant["id"], "2097-06-01")
    assert ge[0]["girdi_sha16"] == g["sha16"] and ge[0]["hesap_durumu"] == "tam" and ge[0]["cikti_surumu"] == "1.1"


def test_portfoy_finans_dsg_sonucu_bir_kez(monkeypatch):
    """pfs.donem(dsg_sonuc=…) verilen DSG sonucunu kullanır; sd.donem çağrılmaz (gece işi DSG'yi bir kez hesaplar)."""
    from pvquant.services import portfoy_finans_service as pfs
    sayac = {"sd": 0}
    monkeypatch.setattr(pfs.pv, "portfoy", lambda *a, **k: {"tur": "dsg", "ad": "P", "dsg_kodu": "DSG-1"})
    monkeypatch.setattr(pfs.pt, "santraller", lambda *a, **k: [{"id": "p1", "name": "A", "capacity_kwp": 100.0, "tz": TZ, "params_json": {}}])
    monkeypatch.setattr(pfs.fe, "son", lambda *a, **k: {"kayitli": True, "id": "k1", "bilesenler": [], "uretim": {"planlanan": {"mwh": 1.0}, "gerceklesen": {"mwh": 1.0}, "sapma": {"mwh": 0.0, "pct": 0.0}},
                                                        "uzlastirma": {"santral_tasir": True}, "toplam": {"tutar_tl": 10.0, "nitelik": "hesaplanan", "giren": 1, "eksik": 0}, "donem": {},
                                                        "meta": {"segment": "lisansli_serbest", "hesap_durumu": "kismi", "girdi": {"sha16": "abc"}}})
    monkeypatch.setattr(pfs.sd, "donem", lambda *a, **k: sayac.__setitem__("sd", sayac["sd"] + 1) or {"durum": "ok"})
    monkeypatch.setattr(pfs.pv, "uyelik_anlik", lambda *a, **k: []); monkeypatch.setattr(pfs.pv, "sozlesme_anlik", lambda *a, **k: [])
    dsg = {"durum": "ok", "meta": {"hesap_durumu": "senaryo", "fiyat": {"sha16": "f1"}}, "dsg": {}, "perspektifler": {}, "uyeler": []}
    monkeypatch.setattr(pfs.pf, "birlestir", lambda *a, **k: {"toplam": {"tutar_tl": 10.0, "nitelik": "hesaplanan"}})   # saf birleştirme ayrı testlerde; burada çağrı sayısı ve meta
    out = pfs.donem("t", "p", "2026-10", bugun=date(2026, 11, 12), dsg_sonuc=dsg)
    assert sayac["sd"] == 0 and out["meta"]["cikti_surumu"] == "1.1" and out["meta"]["hesap_durumu"] == "senaryo"
    assert out["meta"]["girdi"]["santraller"]["A"] == {"kaynak": "kayıtlı", "kayit_id": "k1", "girdi_sha16": "abc", "hesap_durumu": "kismi", "hata": None}
    assert out["meta"]["girdi"]["dsg_fiyat"]["sha16"] == "f1" and len(out["meta"]["girdi"]["sha16"]) == 16
