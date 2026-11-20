# -*- coding: utf-8 -*-
"""v2.641 — Santralim denetimi Parti 2 (orta bulgular): alarm eşik/kural doğrulaması, boş segment tek politika, GHI beyanı PR uyarısı,
yağış arşivi kapsamı, bulut sınamasında sağlayıcı kıyası, deneme alarmı ucu."""
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from apps.api import main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import alarm_service as al
from pvquant.services import kirlenme_service as ks
from pvquant.services import performans_service as ps


# ---------------------------------------------------------------- 2 · alarm doğrulama
def _ak(monkeypatch):
    from pvquant.services import plant_service
    depo = {}
    def birlestir(t, p, **k):
        depo.update(k); return {"alarm_kurallari": depo.get("alarm_kurallari", []), "alarm_esik": depo.get("alarm_esik", {}), "alarm_alicilar": depo.get("alarm_alicilar", [])}
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    return depo


def test_alarm_bilinmeyen_anahtar_ve_sinirlar(monkeypatch):
    depo = _ak(monkeypatch)
    with pytest.raises(ValueError, match="bilinmeyen kural: olmayan_kural"):
        al.kural_ayarla("t", "p", ["pr_dustu", "olmayan_kural"], {})
    with pytest.raises(ValueError, match="bilinmeyen eşik: uydurma_esik"):
        al.kural_ayarla("t", "p", ["pr_dustu"], {"uydurma_esik": 5})
    for kotu in (-0.05, 0, 1.5, 50):
        with pytest.raises(ValueError, match="revizyon_esik"):
            al.kural_ayarla("t", "p", [], {"revizyon_esik": kotu})
    with pytest.raises(ValueError, match="ariza_esik tam sayı"):
        al.kural_ayarla("t", "p", [], {"ariza_esik": 2.5})
    with pytest.raises(ValueError, match="takvim_gun_once tam sayı"):
        al.kural_ayarla("t", "p", [], {"takvim_gun_once": 2.9})
    r = al.kural_ayarla("t", "p", ["veri_gelmedi", "pr_dustu"], {"revizyon_esik": 0.25, "ariza_esik": 3})   # sabit kural listede olabilir, yok sayılır
    assert depo["alarm_kurallari"] == ["pr_dustu"] and depo["alarm_esik"]["revizyon_esik"] == 0.25 and depo["alarm_esik"]["ariza_esik"] == 3 and "secili" in r


def test_deneme_alicilari():
    plant = {"params_json": {"alarm_alicilar": ["a@x.com", "b@x.com"]}}
    assert al.deneme_alicilari(plant, None) == ["a@x.com", "b@x.com"]
    assert al.deneme_alicilari(plant, ["C@y.com", "c@y.com"]) == ["c@y.com"]
    with pytest.raises(ValueError, match="geçersiz"):
        al.deneme_alicilari(plant, ["bozuk"])
    with pytest.raises(ValueError, match="en çok 10"):
        al.deneme_alicilari(plant, [f"k{i}@y.com" for i in range(11)])


# ---------------------------------------------------------------- 4 · GHI beyanı uyarısı
def test_isinim_uyarisi_yalniz_ghi_ve_pr_ok():
    assert ps.isinim_uyarisi({"duzlem": "ghi"}, "ok") and "yatay" in ps.isinim_uyarisi({"duzlem": "ghi"}, "ok")
    assert ps.isinim_uyarisi({"duzlem": "poa"}, "ok") is None
    assert ps.isinim_uyarisi({"duzlem": "ghi"}, "poa_yok") is None
    assert ps.isinim_uyarisi(None, "ok") is None
    # POA + GHI birlikte beyanlıysa düzlem poa seçilir → uyarı yok
    k = ps.isinim_kaynagi([{"tur": "piranometre", "olcum": "ghi", "sinif": "A"}, {"tur": "referans_hucre", "olcum": "poa", "sinif": "B"}], date(2026, 11, 20))
    assert k["duzlem"] == "poa" and ps.isinim_uyarisi(k, "ok") is None


# ---------------------------------------------------------------- 5 · yağış arşivi
def test_son_yagis_ozeti_arsiv_kapsamiyor_ile_yagis_yok_ayri():
    bitis = date(2019, 1, 1)
    bos = ks.son_yagis_ozeti(pd.Series(dtype=float), bitis)
    assert bos["arsiv"] is False and "kapsamıyor" in bos["not"] and bos["tarih"] is None
    idx = pd.Index([date(2026, 11, 10), date(2026, 11, 15)])
    kuru = ks.son_yagis_ozeti(pd.Series([0.2, 0.0], index=idx), date(2026, 11, 20))
    assert kuru["arsiv"] is True and "yağış yok" in kuru["not"]
    yagis = ks.son_yagis_ozeti(pd.Series([0.2, 4.0], index=idx), date(2026, 11, 20))
    assert yagis["arsiv"] is True and yagis["gun_once"] == 5 and yagis["mm"] == 4.0


# ---------------------------------------------------------------- 3 · 7 · 8 (api)
@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {"alarm_alicilar": ["a@x.com"], "veri_yolu": {"tur": "inverter_bulut_api", "saglayici": "deye", "salt_okuma_onayi": True}}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "Deneme GES", "capacity_kwp": 2.4, "lat": 39.0, "lon": 32.0, "tz": "Europe/Istanbul", "tilt": 20, "azimuth": 180, **depo})
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **k: {**depo["params_json"], **k})
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    yield TestClient(api_main.app), depo
    api_main.app.dependency_overrides.clear()


def test_bulut_sinama_saglayici_kiyasi(istemci, monkeypatch):
    c, depo = istemci
    from pvquant.services import bulut_sinama_service
    monkeypatch.setattr(bulut_sinama_service, "sina", lambda *a, **k: {"zaman": "2026-11-20T10:00:00+00:00", "durum": "kimlik_hatasi", "ozet": None})
    y = c.post("/v1/plants/p1/veri-yolu/bulut-sinama", json={"saglayici": "fusionsolar", "kimlik": {}})
    assert y.status_code == 422 and "beyan edilen sağlayıcı «deye»" in y.json()["detail"]
    assert c.post("/v1/plants/p1/veri-yolu/bulut-sinama", json={"saglayici": "Deye", "kimlik": {}}).status_code == 200   # büyük/küçük harf duyarsız


def test_alarm_deneme_ucu(istemci, monkeypatch):
    c, depo = istemci
    from pvquant.services import posta_service
    monkeypatch.setattr(posta_service, "yapilandirildi", lambda: False)
    y = c.post("/v1/plants/p1/alarm-kurallari/deneme", json={})
    assert y.status_code == 409 and "yapılandırılmamış" in y.json()["detail"]
    gidenler = []
    monkeypatch.setattr(posta_service, "yapilandirildi", lambda: True)
    monkeypatch.setattr(posta_service, "gonder", lambda kime, konu, govde, html=None: gidenler.append((kime, konu)) or kime != "kotu@x.com")
    y = c.post("/v1/plants/p1/alarm-kurallari/deneme", json={})
    assert y.status_code == 200 and y.json()["gonderildi"] == ["a@x.com"] and "yazılmaz" in y.json()["not"]
    assert gidenler[-1][0] == "a@x.com" and "Deneme alarmı" in gidenler[-1][1] and "Deneme GES" in gidenler[-1][1]
    y = c.post("/v1/plants/p1/alarm-kurallari/deneme", json={"alicilar": ["kotu@x.com", "iyi@x.com"]})
    assert y.status_code == 200 and y.json()["basarisiz"] == ["kotu@x.com"] and y.json()["gonderildi"] == ["iyi@x.com"]
    assert c.post("/v1/plants/p1/alarm-kurallari/deneme", json={"alicilar": ["bozuk"]}).status_code == 422
    depo["params_json"]["alarm_alicilar"] = []
    y = c.post("/v1/plants/p1/alarm-kurallari/deneme", json={})
    assert y.status_code == 422 and "alıcı yok" in y.json()["detail"]


def test_pr_ucu_ghi_uyarisi(istemci, monkeypatch):
    c, depo = istemci
    from pvquant.services import pr_service
    monkeypatch.setattr(pr_service, "pr_karti", lambda t, p, gun=30: {"durum": "ok", "PR": 0.77, "gun": 28})
    depo["params_json"]["sensorler"] = [{"tur": "piranometre", "olcum": "ghi", "sinif": "A", "kalibrasyon_tarihi": "2026-01-01", "kalibrasyon_periyodu_ay": 24}]
    y = c.get("/v1/plants/p1/pr?gun=31").json()   # 31: önbellek anahtarı testler arasında çakışmasın
    assert "yatay (GHI)" in y["isinim_uyari"]
    depo["params_json"]["sensorler"][0]["olcum"] = "poa"
    assert "isinim_uyari" not in c.get("/v1/plants/p1/pr?gun=32").json()


def test_finansal_etki_segment_yok_kupst_hesaplanmaz():
    from pvquant.services import finansal_etki_service as fe
    assert "KÜPST hesaplanmadı" in fe.NOT_SEGMENT_YOK and fe.kupst_uygulanir(None) is True   # dsg_ozet varsayımı değişmedi
    src = open(fe.__file__, encoding="utf-8").read()
    assert 'if not segment:   # v2.641' in src and 'kaynak="segment seçilmedi", toplanir=False' in src
