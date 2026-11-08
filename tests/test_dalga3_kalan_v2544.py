"""08.11.2026 v2.544 (dalga 3 kalanları): açık-gök tabanlı kirlenme göstergesi (IH-090/092), veri yolu beyanı ve protokol hazırlık listesi (P4b)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pvquant.services import kirlenme_service as ks
from pvquant.services import veri_yolu_service as vy

CAP = 1000.0


def _seri(gun=40, bas="2026-09-01", age=1.0, pr=0.85, age_egim_gun=0.0, pr_egim_gun=0.0, bulutlu_gunler=()):
    """Saat başı UTC; açık-gök POA sentetik (sinüs), ölçülen POA = cs × AGE(t); üretim = P0 × POA/1000 × PR(t)."""
    ts = pd.date_range(bas, periods=24 * gun, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour + 3 - 6) / 12 * np.pi), 0, None)
    cs = pd.Series(900 * g, index=ts)
    gun_no = np.array([(t.date() - ts[0].date()).days for t in ts], dtype=float)
    age_t = age + age_egim_gun * gun_no; pr_t = pr + pr_egim_gun * gun_no
    poa = cs.values * age_t
    for b in bulutlu_gunler:   # bulutlu gün: saatlik oran dalgalanır → açık saat yok
        m = gun_no == b; poa[m] = cs.values[m] * (0.4 + 0.5 * (np.arange(m.sum()) % 2))
    guc = CAP * poa / 1000 * pr_t
    return pd.DataFrame({"ts_utc": ts, "power_kw": guc, "poa_wm2": poa}), cs


def test_gunluk_endeks_acik_gun_ve_bulutlu_gun_ayrimi():
    df, cs = _seri(gun=5, bulutlu_gunler=(2,))
    g = ks.gunluk_endeks(df, cs, CAP)
    assert len(g) == 4 and str(date(2026, 9, 3)) not in g["gun"].astype(str).tolist()     # 2. gün (3 Eylül) bulutlu → düşer
    assert (g["acik_saat"] >= ks.ACIK_SAAT_MIN).all() and np.allclose(g["age"], 1.0, atol=0.01) and np.allclose(g["pr_acik"].astype(float), 0.85, atol=0.01)
    assert ks.gunluk_endeks(pd.DataFrame(), cs, CAP).empty


def test_egim_ve_yorum_sensor_modul_ikisi_kararli():
    bitis = date(2026, 10, 10)
    # sensör: AGE %10/40 gün düşer, PR aynı oranda yükselir (sensör düşük okur → PR yapay yükselir)
    df, cs = _seri(gun=40, age_egim_gun=-0.0025, pr_egim_gun=+0.0021)
    g = ks.gunluk_endeks(df, cs, CAP)
    ae, n = ks.egim_pct_ay(g, "age", bitis); pe, _ = ks.egim_pct_ay(g, "pr_acik", bitis)
    assert n >= ks.EGIM_MIN_ACIK_GUN and ae < -ks.EGIM_ESIK_PCT_AY and pe > ks.EGIM_ESIK_PCT_AY
    assert ks.yorumla(ae, pe)["kod"] == "sensor"
    # modül: AGE sabit, PR düşer
    df, cs = _seri(gun=40, pr_egim_gun=-0.0021); g = ks.gunluk_endeks(df, cs, CAP)
    assert ks.yorumla(ks.egim_pct_ay(g, "age", bitis)[0], ks.egim_pct_ay(g, "pr_acik", bitis)[0])["kod"] == "modul"
    # ikisi düşer
    df, cs = _seri(gun=40, age_egim_gun=-0.0025, pr_egim_gun=-0.0021); g = ks.gunluk_endeks(df, cs, CAP)
    assert ks.yorumla(ks.egim_pct_ay(g, "age", bitis)[0], ks.egim_pct_ay(g, "pr_acik", bitis)[0])["kod"] == "ikisi"
    # atmosfer / model: AGE düşer, PR sabit (ışınım ve üretim birlikte azalır) → kirlenme kanıtı yok
    df, cs = _seri(gun=40, age_egim_gun=-0.0025); g = ks.gunluk_endeks(df, cs, CAP)
    y = ks.yorumla(ks.egim_pct_ay(g, "age", bitis)[0], ks.egim_pct_ay(g, "pr_acik", bitis)[0])
    assert y["kod"] == "atmosfer" and y["tur"] == "olcum" and y["uretim_kaybi"] == "belirsiz"
    # toparlanma: AGE yükselir
    df, cs = _seri(gun=40, age=0.9, age_egim_gun=+0.0025); g = ks.gunluk_endeks(df, cs, CAP)
    assert ks.yorumla(ks.egim_pct_ay(g, "age", bitis)[0], ks.egim_pct_ay(g, "pr_acik", bitis)[0])["kod"] == "toparlanma"
    # kararlı
    df, cs = _seri(gun=40); g = ks.gunluk_endeks(df, cs, CAP)
    assert ks.yorumla(ks.egim_pct_ay(g, "age", bitis)[0], ks.egim_pct_ay(g, "pr_acik", bitis)[0])["kod"] == "kararli"
    assert ks.yorumla(None, 1.0)["kod"] == "yetersiz" and ks.egim_pct_ay(g.tail(3), "age", bitis) == (None, 3)
    assert ks.YORUM["sensor"]["tur"] == "olcum" and ks.YORUM["sensor"]["uretim_kaybi"] == "yok" and ks.YORUM["modul"]["uretim_kaybi"] == "olasi"   # ölçüm sapması ≠ üretim kaybı


def test_acik_gok_poa_ve_yagis():
    idx = pd.date_range("2026-06-21", periods=24, freq="h", tz="UTC")
    cs = ks.acik_gok_poa(idx, 39.0, 33.0, 25.0, 180.0)
    assert len(cs) == 24 and cs.max() > 700 and cs.min() >= 0 and cs.iloc[0] == 0.0    # gece 0, öğle yüksek
    m = pd.DataFrame({"precipitation": [0.0] * 20 + [0.6, 0.7, 0.0, 0.0] + [0.0] * 24}, index=pd.date_range("2026-10-01", periods=48, freq="h", tz="UTC"))
    y = ks.gunluk_yagis(m, "Europe/Istanbul")
    assert y[date(2026, 10, 1)] == pytest.approx(0.6) and y[date(2026, 10, 2)] == pytest.approx(0.7) and ks.gunluk_yagis(pd.DataFrame()).empty   # 20–21 UTC = 23:00 ve 00:00 yerel


def test_veri_yolu_beyani_ve_liste():
    assert vy.dogrula({})["veri_yolu"] is None and vy.dogrula({"tur": ""})["veri_yolu"] is None
    b = vy.dogrula({"tur": "modbus_sunspec", "saglayici": " Huawei SUN2000 ", "periyot_dk": "15", "salt_okuma_onayi": 1, "not": "x"})["veri_yolu"]
    assert b["tur"] == "modbus_sunspec" and b["saglayici"] == "Huawei SUN2000" and b["periyot_dk"] == 15 and b["salt_okuma_onayi"] is True and b["beyan_zamani"]
    with pytest.raises(ValueError, match="tur"):
        vy.dogrula({"tur": "telepati"})
    with pytest.raises(ValueError, match="periyot"):
        vy.dogrula({"tur": "opc_ua", "periyot_dk": 0})
    assert {v["durum"] for v in vy.VERI_YOLLARI.values()} == {"mevcut", "kurulmadi"} and len(vy.VERI_YOLLARI) == 7
    assert all(v["gerekenler"] for v in vy.VERI_YOLLARI.values()) and "RTU" in vy.VERI_YOLLARI["iec104"]["not"]
    assert all("canlı" not in v["not"].lower() for v in vy.VERI_YOLLARI.values())                      # «canlı» sözü kullanılmaz (dosya kaynağı sürekli bağlantı değil)
    from datetime import datetime, timedelta, timezone
    simdi = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
    assert vy.tazelik(simdi - timedelta(hours=20), simdi)["tazelik"] == "guncel"
    g = vy.tazelik(simdi - timedelta(days=17), simdi); assert g["tazelik"] == "gecikmis" and g["yas_saat"] == 408.0 and g["tazelik_etiketi"] == "gecikmiş"
    assert vy.tazelik(None, simdi) == {"tazelik": "yok", "tazelik_etiketi": "veri gelmedi", "yas_saat": None}


PLANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def istemci(monkeypatch):
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    durum = {"pj": {"segment": "lisansli_serbest"}}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "lat": 39.0, "lon": 33.0, "tilt": 25.0, "azimuth": 180.0, "params_json": dict(durum["pj"])})
    def _birlestir(t, p, **an):
        durum["pj"] = {**durum["pj"], **an}; return durum["pj"]
    monkeypatch.setattr(plant_service, "params_birlestir", _birlestir)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(vy, "etkin_yollar", lambda t, p, simdi=None: [{"tur": "scada_dosya", "etiket": "x", "son": None, "ayrinti": "a.csv", "tazelik": "yok"}])
    monkeypatch.setattr(ks, "ozet", lambda t, row, gun=90, bugun=None: {"durum": "ok", "pencere_gun": gun})
    for r in api_main.app.routes:
        if getattr(r, "path", "") == "/v1/plants/{plant_id}/veri-yolu" and "PUT" in getattr(r, "methods", set()):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kirlenme_ve_veri_yolu_kapilari(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/kirlenme?gun=60").json()["pencere_gun"] == 60
    assert istemci.get(f"/v1/plants/{PLANT}/kirlenme?gun=10").status_code == 422
    g = istemci.get(f"/v1/plants/{PLANT}/veri-yolu"); assert g.status_code == 200 and g.json()["beyan"] is None and len(g.json()["yollar"]) == 7 and g.json()["etkin"][0]["tur"] == "scada_dosya"
    r = istemci.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "inverter_bulut_api", "saglayici": "FusionSolar", "periyot_dk": 5, "salt_okuma_onayi": True})
    assert r.status_code == 200 and r.json()["beyan"]["tur"] == "inverter_bulut_api" and r.json()["hedef"]["durum"] == "kurulmadi" and len(r.json()["hedef"]["gerekenler"]) >= 4
    assert istemci.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "yok"}).status_code == 422
    assert istemci.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": None}).json()["beyan"] is None
