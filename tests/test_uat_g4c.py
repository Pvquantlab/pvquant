"""UAT 21.11.2026 — G4-C1 (G4-3): /forecast serisinde gerçekleşen üretim. Kaynak scada_hourly (geçerli bayrak), yalnız tamamlanmış geçmiş saatler;
gelecek/süren saat ölçümü (sentetik tohum) verilmez; ölçüm yoksa null (0 yazılmaz); okuma düşerse seri ölmez; eski alanlar aynen. DB testi 55432."""
from __future__ import annotations

import datetime as dt
import uuid
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import bakim_baglami, sistem_baglami

TENANT = "11111111-1111-1111-1111-111111111111"
PLANT = "22222222-2222-2222-2222-222222222222"
IX = pd.date_range("2026-07-30 00:00", periods=5, freq="h", tz="UTC")


def _df():
    return pd.DataFrame({"p50_kw": np.linspace(0, 400, 5), "p10_kw": np.linspace(0, 300, 5), "p90_kw": np.linspace(0, 500, 5),
                         "p25_kw": np.linspace(0, 340, 5), "p75_kw": np.linspace(0, 460, 5)}, index=IX)


@pytest.fixture()
def istemci(monkeypatch):
    from pvquant.services import forecast_service as fs
    from pvquant.services import gunes_service as gs
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": TENANT, "role": "viewer", "exp": 0}
    monkeypatch.setattr(fs, "son_kosu", lambda t, p: _df())
    monkeypatch.setattr(fs, "kosu_gecmisi", lambda t, p, n=1: [SimpleNamespace(run_at=dt.datetime(2026, 7, 30, 2, 0), mode="C", model="hybrid")])
    monkeypatch.setattr(gs, "dogus_batis", lambda t, p, lo, hi: [])
    monkeypatch.setattr(api_main.yanit_onbellegi, "etkin", lambda: False)
    yield TestClient(api_main.app), monkeypatch
    api_main.app.dependency_overrides.clear()


def test_seri_gercek_kw_eslesir_ve_eski_alanlar_aynen(istemci):
    c, mp = istemci
    ep = int(IX[1].timestamp())
    mp.setattr(api_main, "_gercek_saatlik", lambda t, p, a, b, simdi=None: {ep: 123.5})
    mp.setattr(api_main, "_santral_veri_turu", lambda t, p: "sentetik")
    g = c.get(f"/v1/plants/{PLANT}/forecast?hours=5").json()
    assert g["gercek_veri_turu"] == "sentetik"
    assert [s["gercek_kw"] for s in g["series"]] == [None, 123.5, None, None, None]   # yalnız ölçülen saat; diğerleri null, 0 değil
    assert set(g["series"][0]) == {"ts_utc", "p10_kw", "p50_kw", "p90_kw", "p25_kw", "p75_kw", "gercek_kw"} and g["hours"] == 5
    assert g["series"][1]["p50_kw"] == pytest.approx(100.0)   # tahmin değerleri değişmez


def test_okuma_duserse_seri_olmez(istemci):
    c, mp = istemci
    mp.setattr(api_main, "_gercek_saatlik", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db yok")))
    g = c.get(f"/v1/plants/{PLANT}/forecast?hours=3").json()
    assert g["hours"] == 3 and all(s["gercek_kw"] is None for s in g["series"]) and g["gercek_veri_turu"] is None


def test_utc_ts_ciplak_ve_tzli():
    a = api_main._utc_ts(pd.Timestamp("2026-07-30 10:00"))
    b = api_main._utc_ts(pd.Timestamp("2026-07-30 13:00", tz="Europe/Istanbul"))
    assert a == b and a.tzinfo is not None and a.utcoffset() == dt.timedelta(0)


def test_db_gercek_saatlik_gecmis_gecerli_tamamlanmis():
    """DB: geçmiş geçerli saat girer; geçerli olmayan bayrak (kisinti: tazelik kümesi dışında) girmez; süren saat (ts+1 sa > şimdi) ve gelecek saat girmez (sentetik tohum tüm saatleri yazsa da)."""
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    simdi = dt.datetime(2026, 7, 30, 12, 30, tzinfo=dt.timezone.utc)
    satirlar = [(dt.datetime(2026, 7, 30, 9, 0, tzinfo=dt.timezone.utc), 100.0, "valid"), (dt.datetime(2026, 7, 30, 10, 0, tzinfo=dt.timezone.utc), 200.0, "kisinti"),
                (dt.datetime(2026, 7, 30, 11, 0, tzinfo=dt.timezone.utc), 300.0, "valid"), (dt.datetime(2026, 7, 30, 12, 0, tzinfo=dt.timezone.utc), 400.0, "valid"),
                (dt.datetime(2026, 7, 30, 15, 0, tzinfo=dt.timezone.utc), 500.0, "valid")]
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'G4C Kiracı', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'G4C GES', 1000, 37.0, 32.0, 'Europe/Istanbul', CAST(:j AS jsonb))"),
                  {"p": pid, "t": tid, "j": '{"veri_turu": "sentetik", "santral_turu": "sanal_test"}'})
        for ts, kw, fl in satirlar:
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag) VALUES(CAST(:t AS uuid), :p, :ts, :kw, :f)"), {"t": tid, "p": pid, "ts": ts, "kw": kw, "f": fl})
    try:
        g = api_main._gercek_saatlik(tid, pid, pd.Timestamp("2026-07-30 08:00", tz="UTC"), pd.Timestamp("2026-07-31 08:00", tz="UTC"), simdi=simdi)
        assert g == {int(satirlar[0][0].timestamp()): 100.0, int(satirlar[2][0].timestamp()): 300.0}
        assert api_main._santral_veri_turu(tid, pid) == "sentetik"
        assert api_main._gercek_saatlik(tid, pid, pd.Timestamp("2026-07-30 13:00", tz="UTC"), pd.Timestamp("2026-07-31 08:00", tz="UTC"), simdi=simdi) == {}   # aralık tamamen gelecek
    finally:
        with bakim_baglami() as s:
            s.execute(text("DELETE FROM scada_hourly WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
            s.execute(text("DELETE FROM plants WHERE tenant_id = CAST(:t AS uuid)"), {"t": tid})
            s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": tid})


# ----------------------------------------------------------------------------------------------------------- G4-C2 (G4-7): histogram kutusu
def _kd(s, cap, w=None):
    from pvquant.services import accuracy_service as a
    return a.kutu_dagilimi(s, w, cap)


def test_g4c2_kutu_veriden_ve_olcek():
    """Veri güdümlü kutu: küçük/büyük sapma ve santralde 6–24 kutu; 1-2-5 dizisi; toplam sayım = n; eski sabit davranış aynen."""
    import math
    rng = np.random.default_rng(7)
    for sd, cap in ((0.01, 300.0), (0.5, 1000.0), (5.0, 48000.0), (0.3, 4800.0)):
        d = _kd(rng.normal(0, sd, 120), cap)
        assert 6 <= len(d["kutular"]) <= 24, (sd, cap, len(d["kutular"]), d["kutu_mwh"])
        assert sum(k["adet"] for k in d["kutular"]) == 120 == d["ndays"]
        m = d["kutu_mwh"] / 10 ** math.floor(math.log10(d["kutu_mwh"]))
        assert round(m, 6) in (1.0, 2.0, 5.0) and d["kutu_kaynak"] in ("fd", "scott", "taban")   # taban bağlayıcıysa etiket «taban» (QA Ö-2)
        assert d["birim"] == "MWh/gun"
    # std 0,01 MWh (Format Lab benzeri) artık 2 çubuk değil; taban 0,01 MWh (10 kWh) çözünürlük sınırı → aralık/0,01 kadar kutu (≥5)
    assert len(_kd(rng.normal(0, 0.01, 60), 300.0)["kutular"]) >= 5
    # eski sabit yol: 0,5 verilirse kutu 0,5 ve kaynak «sabit» (geri uyumluluk; sayım tam)
    d = _kd(rng.normal(0, 0.5, 120), 1000.0, 0.5)
    assert d["kutu_mwh"] == 0.5 and d["kutu_kaynak"] == "sabit" and sum(k["adet"] for k in d["kutular"]) == 120
    assert {"kutular", "mu", "sd", "ndays", "p10", "p50", "p90", "birim", "kova", "tz", "kutu_mwh", "kutu_kaynak"} == set(d)


def test_g4c2_taban_kapasiteye_olcekli():
    from pvquant.services import accuracy_service as a
    assert a.kutu_genisligi([], 300.0)["kutu_mwh"] == 0.01
    assert a.kutu_genisligi([], 4800.0)["kutu_mwh"] == 0.05
    assert a.kutu_genisligi([], 48000.0)["kutu_mwh"] == 0.5
    assert a._yuvarla_125(0.013) == 0.01 and a._yuvarla_125(0.3) == 0.2 and a._yuvarla_125(0.35) == 0.5 and a._yuvarla_125(7.0) == 5.0


def test_g4c2_az_ornek_sifir_bos_uc_deger():
    # az örneklem (n<4): taban genişliği, her değer sayılır (kenardaki en büyük değer dahil)
    d = _kd([0.1, 0.2, 0.3], 4800.0)
    assert d["kutu_kaynak"] == "taban" and d["kutu_mwh"] == 0.05 and sum(k["adet"] for k in d["kutular"]) == 3
    # sıfır sapma: tek kutu, n sayım, istatistikler 0
    d = _kd([0.0] * 30, 4800.0)
    assert len(d["kutular"]) == 1 and d["kutular"][0]["adet"] == 30 and d["mu"] == 0.0 and d["sd"] == 0.0 and d["p50"] == 0.0
    # aynı değer (0,7) tam bölünen kenar: eskiden 0 sayılıyordu
    d = _kd([0.7] * 20, 1000.0)
    assert d["kutular"] == [{"lo": 0.7, "hi": 0.71, "adet": 20}]
    # boş: kutu yok, istatistik None, anahtarlar var
    d = _kd([], 4800.0)
    assert d["kutular"] == [] and d["ndays"] == 0 and d["mu"] is None and d["kutu_mwh"] is None
    # uç değer: veri atılmaz, kutu sayısı tavanı aşmaz, genişlik büyür
    rng = np.random.default_rng(3)
    d = _kd([*rng.normal(0, 0.3, 100).tolist(), 12.0], 4800.0)
    assert sum(k["adet"] for k in d["kutular"]) == 101 and len(d["kutular"]) <= 24 and d["kutular"][-1]["hi"] >= 12.0
    # tek gün, negatif: sayım 1
    d = _kd([-0.37], 1000.0)
    assert sum(k["adet"] for k in d["kutular"]) == 1 and d["kutular"][0]["lo"] <= -0.37 < d["kutular"][0]["hi"]
    # NaN/inf süzülür (kutu genişliği hesabı ve sayım), hata vermez (QA Ö-3)
    from pvquant.services import accuracy_service as a
    assert a.kutu_genisligi([0.1, float("nan"), 0.2, float("inf"), 0.3, 0.4, 0.5], 1000.0)["n"] == 5
    d = _kd([0.1, float("nan"), 0.3, 0.4], 1000.0)
    assert d["ndays"] == 3 and sum(k["adet"] for k in d["kutular"]) == 3
    # taban bağlayıcıysa kaynak «taban» (QA Ö-2): 48 MWp, sd 0,02 MWh → FD tabanın altında
    rng = np.random.default_rng(11)
    d = _kd(rng.normal(0, 0.02, 100), 48000.0)
    assert d["kutu_mwh"] == 0.5 and d["kutu_kaynak"] == "taban"
    # QA Ö-1: 2000 tohumda gerçek kutu sayısı 5–24 bandında, sayım her zaman n
    for i in range(300):
        r = np.random.default_rng(i)
        n, sd, cap = int(r.integers(4, 300)), float(10 ** r.uniform(-3, 1.5)), float(10 ** r.uniform(2, 5))
        d = _kd(r.normal(0, sd, n), cap)
        assert 1 <= len(d["kutular"]) <= 24 and sum(k["adet"] for k in d["kutular"]) == n, (i, n, sd, cap, len(d["kutular"]))
        if d["kutu_kaynak"] != "taban":
            assert 5 <= len(d["kutular"]) <= 24, (i, n, sd, cap, len(d["kutular"]), d["kutu_mwh"])
