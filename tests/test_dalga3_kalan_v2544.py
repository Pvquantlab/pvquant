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
    # 08.11 inceleme (faz 3): dosya kaynağında 48 saat ölçütü yok — 17 günlük yükleme «dosya» (bilgi), 31 gün «dosya_eski» (uyarı)
    assert vy.tazelik(simdi - timedelta(days=17), simdi, "dosya")["tazelik"] == "dosya" and vy.tazelik(simdi - timedelta(days=31), simdi, "dosya")["tazelik"] == "dosya_eski"
    # EPİAŞ çekiş durumu: hata ≠ yeni kayıt yok ≠ SCADA öncelikli ≠ başarılı
    assert vy.epias_cekis_durumu("error", "HTTPError: 503")["kod"] == "hata" and vy.epias_cekis_durumu(None, None)["kod"] == "yok"
    assert vy.epias_cekis_durumu("ok", "{'durum': 'veri_yok', 'n_yazilan': 0}")["kod"] == "kayit_yok"
    assert vy.epias_cekis_durumu("ok", "{'durum': 'ok', 'n_yazilan': 0, 'n_cekilen': 24}")["kod"] == "yazilmadi"
    assert vy.epias_cekis_durumu("ok", "{'durum': 'ok', 'n_yazilan': 24, 'n_cekilen': 24}")["etiket"].endswith("(24 saat yazıldı)")
    assert vy.epias_cekis_durumu("ok", "")["kod"] == "ok"
    # 08.11 inceleme II (faz 3): bağlantı sağlığı ≠ veri tazeliği
    assert vy.veri_etiketi(vy.tazelik(simdi - timedelta(days=11), simdi)) == "11 gündür yeni veri yok" and vy.veri_etiketi(vy.tazelik(simdi - timedelta(hours=5), simdi)) == "veri güncel"
    assert vy.veri_etiketi(vy.tazelik(simdi - timedelta(days=16), simdi, "dosya")) == "son yükleme 16 gün önce" and vy.veri_etiketi(vy.tazelik(None, simdi)) == "veri gelmedi"
    assert vy.epias_baglanti({"kod": "kayit_yok", "zaman": "z"}) == {"durum": "ok", "etiket": "son sorgu başarılı", "zaman": "z"}   # eski veri, başarılı sorgu
    assert vy.epias_baglanti({"kod": "hata", "zaman": "z"})["durum"] == "hata" and vy.epias_baglanti(None)["durum"] == "bilinmiyor" and vy.epias_baglanti({"kod": "yok"})["durum"] == "yok"
    a_vm = vy.asamalar({"tur": "modbus_sunspec", "beyan_zamani": "t", "baglanti": {"host": "h"}, "son_sinama": {"durum": "veri_modeli_yok", "zaman": "z"}}, [])
    assert not a_vm[2]["tamam"] and a_vm[2]["etiket"] == "cihaza erişildi, veri modeli desteklenmiyor"
    # Aşamalar: seçildi → ayar → sınama → akış; hiçbiri diğerini ima etmez
    assert vy.asamalar(None, []) == []
    a = vy.asamalar({"tur": "modbus_sunspec", "beyan_zamani": "t", "baglanti": {"host": "10.8.0.12"}}, [])
    assert [x["kod"] for x in a] == ["secildi", "ayar", "sinama", "cekis", "akis"] and a[1]["tamam"] and not a[2]["tamam"] and a[2]["etiket"] == "bağlantı sınanmadı" and not a[3]["tamam"] and not a[4]["tamam"]   # v2.546: çekiş aşaması
    a2 = vy.asamalar({"tur": "modbus_sunspec", "beyan_zamani": "t", "baglanti": {"host": "h"}, "son_sinama": {"durum": "ok", "zaman": "z"}}, [])
    assert a2[2]["tamam"] and a2[2]["zaman"] == "z" and a2[3]["etiket"] == "düzenli veri çekişi başlatılmadı" and a2[4]["etiket"] == "veri alınmıyor"
    a3 = vy.asamalar({"tur": "scada_dosya", "beyan_zamani": "t"}, [{"tur": "scada_dosya", "son": "2026-10-22T21:05:00+00:00"}])
    assert [x["kod"] for x in a3] == ["secildi", "akis"] and a3[1]["tamam"]


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
    g = istemci.get(f"/v1/plants/{PLANT}/veri-yolu"); assert g.status_code == 200 and g.json()["beyan"] is None and len(g.json()["yollar"]) == 7 and g.json()["etkin"][0]["tur"] == "scada_dosya" and g.json()["asamalar"] == []
    r = istemci.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "inverter_bulut_api", "saglayici": "FusionSolar", "periyot_dk": 5, "salt_okuma_onayi": True})
    assert r.status_code == 200 and r.json()["beyan"]["tur"] == "inverter_bulut_api" and r.json()["hedef"]["durum"] == "kurulmadi" and len(r.json()["hedef"]["gerekenler"]) >= 4
    assert [x["kod"] for x in r.json()["asamalar"]] == ["secildi", "ayar", "sinama", "akis"] and not r.json()["asamalar"][1]["tamam"]
    assert istemci.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "yok"}).status_code == 422
    assert istemci.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": None}).json()["beyan"] is None


# ----------------------------------------------------------------------------- v2.545: kirlenme kaybı tahmini (IH-090 kalanı)
def test_kayip_tahmini_modul_kirlenmesi_ve_temizlik_esigi():
    bitis = date(2026, 10, 10)
    df, cs = _seri(gun=40, pr_egim_gun=-0.0021)                       # modül: PR 0,85 → ~0,77 (40 günde %10 düşüş)
    g = ks.gunluk_endeks(df, cs, CAP)
    ur = df.set_index("ts_utc")["power_kw"].groupby(lambda t: t.tz_convert("Europe/Istanbul").date()).sum()
    fiyat = pd.Series(2000.0, index=ur.index)                          # TL/MWh sabit
    k = ks.kayip_tahmini(g, ur, fiyat, bitis, temizlik_maliyeti_tl=5000.0, yorum_kodu="modul")
    assert k["durum"] == "ok" and 0.83 < k["referans_pr"] <= 0.85 and k["gecerlilik"] == "anlamli" and k["nitelik"] == "tahmin" and k["son30_gun"] == 30 and k["bitis"] == "2026-10-10"
    assert k["son30_kayip_kwh"] > 0 and k["son30_kayip_tl"] == pytest.approx(k["son30_kayip_kwh"] / 1000 * 2000, abs=1.0)
    assert 5 < k["son7_gunluk_kayip_pct"] < 12 and k["pencere_kayip_kwh"] >= k["son30_kayip_kwh"]
    assert k["temizlik"]["maliyet_tl"] == 5000.0 and isinstance(k["temizlik"]["son30_karsilar"], bool) and k["temizlik"]["geri_odeme_gun"] > 0
    # 08.11 inceleme (faz 1): sensör şüphesinde PR yanlı → tahmin ASKIYA alınır, sayı ve temizlik karşılaştırması verilmez
    df2, cs2 = _seri(gun=40, age_egim_gun=-0.0025, pr_egim_gun=+0.0021); g2 = ks.gunluk_endeks(df2, cs2, CAP)
    ur2 = df2.set_index("ts_utc")["power_kw"].groupby(lambda t: t.tz_convert("Europe/Istanbul").date()).sum()
    k2 = ks.kayip_tahmini(g2, ur2, None, bitis, 5000.0, "sensor")
    assert k2["durum"] == "askida" and k2["gecerlilik"] == "yanli" and k2["temizlik"] is None and "son30_kayip_kwh" not in k2 and "sensörü temizleyin" in k2["aciklama"]
    # kararlı/atmosfer/yetersiz yorumunda sayı yalnız koşullu senaryo; temizlik maliyeti girilse de karşılaştırma yapılmaz
    k3 = ks.kayip_tahmini(g, ur, fiyat, bitis, 5000.0, "kararli")
    assert k3["durum"] == "ok" and k3["nitelik"] == "senaryo" and k3["gecerlilik"] == "zayif" and k3["temizlik"] is None and "karşılaştırması yapılmadı" in k3["temizlik_neden"]
    assert ks.kayip_tahmini(g, ur, fiyat, bitis, 5000.0, "yetersiz")["gecerlilik"] == "belirsiz" and ks.kayip_tahmini(g, ur, None, bitis, 5000.0, "modul")["temizlik_neden"].startswith("satış fiyatı yok")
    assert ks.kayip_tahmini(g.head(3), ur, None, bitis)["durum"] == "yetersiz" and ks.kayip_tahmini(pd.DataFrame(), ur, None, bitis)["durum"] == "yetersiz"
