"""05.11.2026 v2.542 (P8b-2; IH-083/092/099/104): ölçülen havayla beklenen seri + EPI, ışınım endeksi düzlem kuralı, sensör envanteri ve vade."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pvquant.services import performans_service as ps

CAP = 1000.0


def _df(gun=60, tmod=True, tair=False, wind=True, bas="2026-06-01"):
    ts = pd.date_range(bas, periods=24 * gun, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour + 3 - 6) / 12 * np.pi), 0, None)          # İstanbul güneşi
    poa = 900 * g
    tm = 25 + 20 * g
    guc = CAP * poa / 1000 * 0.85 * (1 - 0.0035 * (tm - 25))              # PR_stc = 0,85
    return pd.DataFrame({"ts_utc": ts, "power_kw": guc, "poa_wm2": poa,
                         "t_module": tm if tmod else np.nan, "t_air": (tm - 15) if tair else np.nan,
                         "wind_ms": (2.0 if wind else np.nan), "flag": "valid", "kirpma": False})


# ----------------------------------------------------------------------------- beklenen + EPI
def test_beklenen_modul_sicakligiyla_epi_bire_yakin():
    d, kaynak = ps.beklenen_olculen(_df(), CAP, 0.85)
    assert kaynak == "modul"
    aylar = ps.aylik_tablo(d, CAP)
    assert [a["ay"] for a in aylar] == ["2026-06", "2026-07"] and all(a["durum"] == "ok" for a in aylar)
    for a in aylar:
        assert abs(a["epi"] - 1.0) < 0.01 and a["epi_temiz"] == a["epi"] and a["poa_kapsam"] == 1.0 and a["isinim_kwh_m2"] > 0


def test_sicaklik_kaynagi_faiman_ve_yok():
    _, k = ps.beklenen_olculen(_df(tmod=False, tair=True), CAP, 0.85)
    assert k == "faiman"
    _, k = ps.beklenen_olculen(_df(tmod=False, tair=True, wind=False), CAP, 0.85)
    assert k == "faiman_ruzgarsiz"
    d, k = ps.beklenen_olculen(_df(tmod=False), CAP, 0.85)
    assert k == "yok"
    a = ps.aylik_tablo(d, CAP)[0]
    assert a["epi"] < 1.0                      # sıcaklık terimi yok → beklenen yüksek kalır, EPI 1'in altında


def test_ac_siniri_beklentiyi_keser_ve_poa_eksik_ay_tire():
    d, _ = ps.beklenen_olculen(_df(), CAP, 0.85, ac_sinir_kw=500.0)
    assert d["beklenen_kw"].max() <= 500.0
    df = _df()
    df.loc[df["ts_utc"] < "2026-06-20", "poa_wm2"] = np.nan          # haziranın çoğu POA'sız
    d, _ = ps.beklenen_olculen(df, CAP, 0.85)
    aylar = ps.aylik_tablo(d, CAP)
    haz = next(a for a in aylar if a["ay"] == "2026-06")
    assert haz["durum"] == "poa_yok" and haz["beklenen_kwh"] is None and haz["epi"] is None and haz["uretim_kwh"] > 0
    assert next(a for a in aylar if a["ay"] == "2026-07")["durum"] == "ok"


def test_kirpma_ve_kisinti_saatleri_temiz_epiden_dislanir():
    df = _df(gun=30)
    g = df["ts_utc"].dt.hour == 9
    df.loc[g, "kirpma"] = True; df.loc[g, "power_kw"] = 0.0           # kırpma işaretli saatte üretim 0 (yapay)
    d, _ = ps.beklenen_olculen(df, CAP, 0.85)
    a = ps.aylik_tablo(d, CAP)[0]
    assert a["kirpma_saat"] == 30 and a["epi"] < a["epi_temiz"] and abs(a["epi_temiz"] - 1.0) < 0.01


# ----------------------------------------------------------------------------- referans PR
def test_referans_pr_sirasi():
    assert ps.referans_pr({"pr_referans": 0.8}, {"durum": "ok", "PR_sicaklik": 0.7})["kaynak"] == "tasarim"
    r = ps.referans_pr({}, {"durum": "ok", "PR": 0.75, "PR_sicaklik": None, "PR_kirpma_disi": 0.77, "pencere_gun": 365})
    assert r["kaynak"] == "olcum" and r["deger"] == 0.77 and "kırpma dışı" in r["etiket"]
    assert ps.referans_pr({}, {"durum": "poa_yok"}) is None and ps.referans_pr({}, None) is None


# ----------------------------------------------------------------------------- ışınım endeksi
def test_isinim_endeksi_duzlem_kurali():
    aylar = [{"ay": "2026-06", "isinim_kwh_m2": 200.0, "durum": "ok"}, {"ay": "2026-07", "isinim_kwh_m2": 190.0, "durum": "poa_yok"}]
    iklim = {"ghi": {6: 210.0, 7: 215.0}, "poa": {6: 230.0, 7: 240.0}}
    e = ps.isinim_endeksi(aylar, iklim, "ghi")
    assert e["durum"] == "ok" and e["aylar"]["2026-06"]["endeks"] == round(200 / 210, 3) and "2026-07" not in e["aylar"] and e["yil"] == round(200 / 210, 3)
    e = ps.isinim_endeksi(aylar, iklim, "poa")                       # düzlem-içi sensör → düzlem-içi beklentiyle
    assert e["durum"] == "ok" and e["aylar"]["2026-06"]["p50_kwh_m2"] == 230.0 and e["aylar"]["2026-06"]["endeks"] == round(200 / 230, 3)
    assert ps.isinim_endeksi(aylar, {"ghi": iklim["ghi"], "poa": {}}, "poa")["durum"] == "poa_p50_yok"   # yatayla kıyas YAPILMAZ
    assert ps.isinim_endeksi(aylar, iklim, None)["durum"] == "sensor_yok"
    assert ps.isinim_endeksi(aylar, None, "ghi")["durum"] == "iklim_yok"
    assert ps.isinim_endeksi([aylar[1]], iklim, "ghi")["durum"] == "olcum_yok"


# ----------------------------------------------------------------------------- sensör envanteri
def test_sensor_dogrula_ve_varsayilanlar():
    s = ps.sensor_dogrula({"tur": "piranometre", "olcum": "poa", "sinif": "a", "kalibrasyon_tarihi": "2025-03-15T00:00:00", "marka_model": " Kipp & Zonen SMP10 "})
    assert s == {"tur": "piranometre", "olcum": "poa", "marka_model": "Kipp & Zonen SMP10", "seri_no": None, "sinif": "A",
                 "kalibrasyon_tarihi": "2025-03-15", "kalibrasyon_periyodu_ay": 24, "not": None}
    with pytest.raises(ValueError, match="tur"):
        ps.sensor_dogrula({"tur": "lidar", "olcum": "poa"})
    with pytest.raises(ValueError, match="t_module"):
        ps.sensor_dogrula({"tur": "modul_sicaklik", "olcum": "ghi"})
    with pytest.raises(ValueError, match="poa ya da ghi"):
        ps.sensor_dogrula({"tur": "referans_hucre", "olcum": "t_air"})
    with pytest.raises(ValueError, match="sinif"):
        ps.sensor_dogrula({"tur": "piranometre", "olcum": "ghi", "sinif": "C"})
    with pytest.raises(ValueError, match="YYYY-AA-GG"):
        ps.sensor_dogrula({"tur": "piranometre", "olcum": "ghi", "kalibrasyon_tarihi": "15.03.2025"})
    with pytest.raises(ValueError, match="1–120"):
        ps.sensor_dogrula({"tur": "piranometre", "olcum": "ghi", "kalibrasyon_periyodu_ay": 0})


def test_sensor_vade_durumlari_ve_isinim_kaynagi():
    bugun = date(2026, 11, 5)
    sens = [{"tur": "piranometre", "olcum": "ghi", "sinif": "A", "kalibrasyon_tarihi": "2024-10-01", "kalibrasyon_periyodu_ay": 24},   # vade 2026-10-01 → geçti
            {"tur": "referans_hucre", "olcum": "poa", "sinif": "B", "kalibrasyon_tarihi": "2024-12-20", "kalibrasyon_periyodu_ay": 24},  # 2026-12-20 → 45 gün, yaklaşıyor
            {"tur": "modul_sicaklik", "olcum": "t_module", "kalibrasyon_tarihi": "2026-01-10", "kalibrasyon_periyodu_ay": 24},          # 2028-01-10 → uygun
            {"tur": "meteo_istasyonu", "olcum": "t_air"}]
    d = ps.sensor_durumlari(sens, bugun)
    assert [x["durum"] for x in d] == ["gecti", "yaklasiyor", "uygun", "tarih_yok"]
    assert d[0]["vade"] == "2026-10-01" and d[0]["kalan_gun"] == -35 and d[1]["kalan_gun"] == 45 and d[3]["vade"] is None
    k = ps.isinim_kaynagi(sens, bugun)
    assert k["duzlem"] == "poa" and k["sinif"] == "B" and k["kalibrasyon"] == "yaklasiyor" and "Referans hücre" in k["etiket"]
    assert ps.isinim_kaynagi([sens[0]], bugun)["duzlem"] == "ghi"
    assert ps.isinim_kaynagi([], bugun) == {"duzlem": None, "etiket": "ışınım sensörü beyan edilmedi", "sinif": None, "kalibrasyon": None, "tur": None}
    assert ps._ay_ekle(date(2024, 1, 31), 1) == date(2024, 2, 29) and ps._ay_ekle(date(2026, 11, 1), -12) == date(2025, 11, 1)


# ----------------------------------------------------------------------------- API kapıları (sahte servis)
PLANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def istemci(monkeypatch):
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    durum = {"pj": {"sensorler": [{"tur": "piranometre", "olcum": "ghi", "sinif": "A", "kalibrasyon_tarihi": "2024-10-01", "kalibrasyon_periyodu_ay": 24}]}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "tz": "Europe/Istanbul", "params_json": dict(durum["pj"])})
    def _birlestir(t, p, **an):
        durum["pj"] = {**durum["pj"], **an}; return durum["pj"]
    monkeypatch.setattr(plant_service, "params_birlestir", _birlestir)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(ps, "ozet", lambda t, row, ay=12: {"durum": "ok", "ay": ay, "aylar": []})
    # yazma_yetkisi() her çağrıda yeni bağımlılık üretir → rota üzerinden bul
    for r in api_main.app.routes:
        if getattr(r, "path", "") == "/v1/plants/{plant_id}/sensorler" and "PUT" in getattr(r, "methods", set()):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_sensorler_kapisi_oku_ve_yaz(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/sensorler"); assert r.status_code == 200
    j = r.json(); assert j["sensorler"][0]["durum"] == "gecti" and j["isinim"]["duzlem"] == "ghi" and "A" in j["siniflar"] and j["varsayilan_periyot_ay"] == 24
    r = istemci.put(f"/v1/plants/{PLANT}/sensorler", json={"sensorler": [{"tur": "referans_hucre", "olcum": "poa", "sinif": "b", "kalibrasyon_tarihi": "2026-01-10"}]})
    assert r.status_code == 200 and r.json()["sensorler"][0]["sinif"] == "B" and r.json()["sensorler"][0]["durum"] == "uygun" and r.json()["isinim"]["duzlem"] == "poa"
    assert istemci.put(f"/v1/plants/{PLANT}/sensorler", json={"sensorler": [{"tur": "lidar", "olcum": "poa"}]}).status_code == 422
    assert istemci.put(f"/v1/plants/{PLANT}/sensorler", json={"sensorler": [{"tur": "piranometre", "olcum": "poa"}] * 21}).status_code == 422
    assert istemci.put(f"/v1/plants/{PLANT}/sensorler", json={"sensorler": []}).status_code == 200


def test_performans_kapisi_ay_siniri(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/performans?ay=6").json()["ay"] == 6
    assert istemci.get(f"/v1/plants/{PLANT}/performans?ay=0").status_code == 422
    assert istemci.get(f"/v1/plants/{PLANT}/performans?ay=37").status_code == 422


# ----------------------------------------------------------------------------- iklim POA beklentisi, takvim, aylık rapor (P8b-2 kalanı)
def _sahte_ghi(yillar):
    ix = pd.date_range(f"{yillar[0]}-01-01", f"{yillar[-1]}-12-31 23:00", freq="h", tz="UTC")
    g = np.clip(np.sin((ix.hour + 3 - 6) / 12 * np.pi), 0, None)           # İstanbul güneşi
    mevsim = 1.0 - 0.45 * np.cos((ix.dayofyear - 172) / 365 * 2 * np.pi)   # yaz 1,45 / kış 0,55
    return pd.DataFrame({"ghi": 800 * g * mevsim}, index=ix)


def test_iklim_poa_beklentisi_guneye_egik_kista_yataydan_yuksek():
    from pvquant.services import iklim_service as ik
    df = _sahte_ghi([2021, 2022])
    poa = ik.poa_serisi(df, 39.0, 33.0, 25.0, 180.0)                     # Erbs ayrışımı (dni/dhi yok)
    assert len(poa) == len(df) and (poa >= 0).all() and poa.max() > 0
    t, b = ik._beklenti_birlestir(df, 2021, 2022, "Europe/Istanbul", 39.0, 33.0, 25.0, 180.0)
    assert {"ghi_kwh_m2", "poa_kwh_m2"} <= set(t.columns) and {"poa_p10", "poa_p50", "poa_p90"} <= set(b.columns) and len(b) == 12
    ara = b[b["ay"] == 12].iloc[0]; tem = b[b["ay"] == 7].iloc[0]
    assert ara["poa_p50"] > ara["p50"] * 1.15                          # güneye 25° eğik düzlem kışın yataydan belirgin yüksek
    assert 0.85 < tem["poa_p50"] / tem["p50"] < 1.15                   # yazın yakın
    assert b.attrs["poa_egim"] == 25.0 and b.attrs["poa_azimut"] == 180.0
    t0, b0 = ik._beklenti_birlestir(df, 2021, 2022, None, 39.0, 33.0, None, None)   # eğim yoksa POA sütunu yok
    assert "poa_p50" not in b0.columns and "poa_kwh_m2" not in t0.columns


def test_takvim_sensor_kalibrasyon_vadesi_uyum_satiri():
    from pvquant.services import takvim_service
    pj = {"segment": "lisansli_serbest", "sensorler": [
        {"tur": "piranometre", "olcum": "poa", "sinif": "A", "marka_model": "SMP10", "kalibrasyon_tarihi": "2025-01-10", "kalibrasyon_periyodu_ay": 24},   # vade 2027-01-10
        {"tur": "modul_sicaklik", "olcum": "t_module", "kalibrasyon_tarihi": "2024-01-01", "kalibrasyon_periyodu_ay": 24},                             # geçmiş → listede yok
        {"tur": "meteo_istasyonu", "olcum": "t_air"}]}                                                                                               # tarih yok
    o = takvim_service.ozet({"id": "x", "name": "X", "capacity_kwp": 1000.0, "params_json": pj}, gun=90, bugun=date(2026, 11, 5))
    s = [x for x in o["uyum"] if x["kod"] == "sensor_kalibrasyon"]
    assert len(s) == 1 and s[0]["tarih"] == "2027-01-10" and s[0]["kalan_gun"] == 66 and s[0]["islem"] == "islem" and s[0]["sorumlu"] == "santral"
    assert s[0]["kaynak_turu"] == "kunye" and "Piranometre" in s[0]["ad"] and "SMP10" in s[0]["not"]
    assert [x["kod"] for x in o["yaklasan"] if x["kod"] == "sensor_kalibrasyon"] == ["sensor_kalibrasyon"]   # 66 gün ≤ 90 → yaklaşanlarda da
    assert all(o["uyum"][i]["tarih"] <= o["uyum"][i + 1]["tarih"] for i in range(len(o["uyum"]) - 1))
    o2 = takvim_service.ozet({"id": "x", "name": "X", "capacity_kwp": 1000.0, "params_json": pj}, gun=30, bugun=date(2026, 11, 5))
    assert not [x for x in o2["yaklasan"] if x["kod"] == "sensor_kalibrasyon"]                               # 30 günlük pencerede değil


def test_aylik_rapor_performans_bolumu(monkeypatch):
    from pvquant.services import aylik_rapor_service as ar
    sahte = {"durum": "ok", "referans": {"etiket": "tasarım/sözleşme PR (Santral ayarlarından)"}, "sicaklik": {"etiket": "modül sıcaklık sensörü"},
             "sensorler": {"etiket": "Piranometre (termopil) — düzlem-içi ışınım (POA), sınıf A"}, "not": ps.BEKLENEN_NOTU,
             "toplam": {"ay_ok": 1, "ay": 1, "uretim_kwh": 1520000.0, "beklenen_kwh": 1563800.0, "epi": 0.972, "tahmin_kwh": None, "p50_kwh": None},
             "isinim": {"durum": "ok", "yil": 0.97, "not": ps.ISINIM_NOTU["ok"]},
             "aylar": [{"ay": "2026-10", "uretim_kwh": 1520000.0, "beklenen_kwh": 1563800.0, "epi": 0.972, "epi_temiz": 0.974, "isinim_endeksi": 0.97, "poa_kapsam": 0.99}]}
    cagri = {}
    monkeypatch.setattr(ps, "donem", lambda t, p, bas, bit, bugun=None: cagri.update(bas=bas, bit=bit) or sahte)
    d = ar.donem_cozumle("2026-10", date(2026, 11, 5))
    r = ar.performans("t", {"id": "x"}, d)
    assert cagri["bas"] == date(2026, 10, 1) and cagri["bit"] == date(2026, 10, 31)
    assert r["durum"] == "ok" and r["epi"] == 0.972 and r["aylar"][0]["isinim_endeksi"] == 0.97 and r["isinim"]["durum"] == "ok"
    monkeypatch.setattr(ps, "donem", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db yok")))
    assert ar.performans("t", {"id": "x"}, d)["durum"] == "hata"
