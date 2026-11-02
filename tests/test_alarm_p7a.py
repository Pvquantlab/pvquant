"""v2.519 (P7a) — alarm: kural bazlı sıklık, alıcı/kanal, yeni kurallar (takvim son tarihi, PTF düşük saat, arıza sayacı, teminat/avans
hatırlatması), kgup_teslim_gecikti «bildirildi» beyanı, webhook alarm.yeni; API alıcı alanı. DB'siz (saf fonksiyonlar + monkeypatch)."""
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from pvquant.services import alarm_service as al
from pvquant.services import webhook_service


def _p(kurallar, esik=None, **pj):
    return {"id": "p1", "tenant_id": "t", "name": "Edikli GES", "params_json": {"alarm_kurallari": kurallar, "alarm_esik": esik or {}, **pj}}


def test_yeni_kurallar_secilebilir_ve_esikler():
    for k in ("takvim_son_tarih", "ptf_dusuk_saat", "ariza_sayaci_yaklasti", "teminat_hatirlatma", "avans_hatirlatma"):
        assert k in al.EK_KURALLAR and k in al.KURAL_ETIKET
    e = al.esikler(_p([], {"takvim_gun_once": 5}))
    assert e["takvim_gun_once"] == 5 and e["ptf_esik_tl_mwh"] == 0.0 and e["ariza_esik"] == 25


def test_kgup_teslim_gecikti_bildirildi_beyani():
    p = _p(["kgup_teslim_gecikti"])
    kritik = al.ek_alarmlar(p, {"kgup_gecikti": True})
    assert kritik[0][1] == "kritik" and "15:30" in kritik[0][2] and "koşu" not in kritik[0][2]
    uyari = al.ek_alarmlar(p, {"kgup_gecikti": False, "kgup_bildirildi": False})
    assert uyari[0][1] == "uyari" and "PVQuant'a yüklenmedi" in uyari[0][2] and "beyanınız" in uyari[0][2]
    assert al.ek_alarmlar(p, {"kgup_gecikti": False, "kgup_bildirildi": True}) == []
    assert al.ek_alarmlar(p, {"kgup_gecikti": False}) == []          # beyan bilgisi yoksa (15:30 öncesi) sessiz


def test_ptf_dusuk_saat_mesaj_ve_baglam():
    p = _p(["ptf_dusuk_saat"])
    r = al.ek_alarmlar(p, {"ptf_dusuk_saatler": [11, 12, 13], "ptf_esik_kullanilan": 0.0, "ptf_yarin": "2026-11-02"})
    assert r[0][1] == "uyari" and "3 saatte" in r[0][2] and "PTF ≤ 0" in r[0][2] and "11:00, 12:00, 13:00" in r[0][2]
    assert "yarın (2 Kas 2026 Pzt)" in r[0][2]                                       # tarih müşteri biçiminde, ISO değil
    assert al.ek_alarmlar(p, {"ptf_dusuk_saatler": []}) == []
    # bağlam: sahte fiyat — 24 saat, 10–13 arası PTF 0, 14 senaryo (sayılmaz)
    def fiyatlar(idx):
        f = pd.DataFrame(index=idx, data={"ptf": 1500.0, "smf": float("nan"), "yon": None, "kaynak": "epias_gop"})
        saat = idx.tz_convert("Europe/Istanbul").hour
        f.loc[(saat >= 10) & (saat <= 13), "ptf"] = 0.0
        f.loc[saat == 14, ["ptf", "kaynak"]] = [-5.0, "senaryo"]
        return f
    b = al.ptf_baglam(p, bugun=date(2026, 11, 1), fiyatlar=fiyatlar)
    assert b["ptf_dusuk_saatler"] == [10, 11, 12, 13] and b["ptf_yarin"] == "2026-11-02" and b["ptf_veri_saat"] == 23 and not b["ptf_v_ile"]
    # YEKDEM'de eşik 0 → V = 10,8 ¢/kWh × 10 × 34 TL = 3672 TL/MWh; 1500 < V → 23 EPİAŞ saatinin hepsi
    py = _p(["ptf_dusuk_saat"], segment="lisansli_yekdem", tarife={"tip": "yekdem", "usd_cent_kwh": 10.8, "kur_tl_usd": 34.0})
    by = al.ptf_baglam(py, bugun=date(2026, 11, 1), fiyatlar=fiyatlar)
    assert by["ptf_v_ile"] and abs(by["ptf_esik_kullanilan"] - 3672.0) < 1e-6 and len(by["ptf_dusuk_saatler"]) == 23
    # kullanıcı eşiği (serbest): PTF < 100 → yalnız 0'lar
    bs = al.ptf_baglam(_p(["ptf_dusuk_saat"], {"ptf_esik_tl_mwh": 100}), bugun=date(2026, 11, 1), fiyatlar=fiyatlar)
    assert bs["ptf_dusuk_saatler"] == [10, 11, 12, 13] and "PTF < 100" in al.ek_alarmlar(_p(["ptf_dusuk_saat"]), bs)[0][2]


def test_sayac_eksik_saat_kurali():
    """v2.526 (P7b): vadesi gelen ama yüklenmemiş sayaç saati eşiği aşınca uyarı; eşik doğrulaması 1–744."""
    assert "sayac_eksik_saat" in al.EK_KURALLAR and al.ESIK_VARSAYILAN["sayac_eksik_esik_saat"] == 24 and al.KURAL_ETIKET["sayac_eksik_saat"] == "Sayaç verisi eksik"
    p = _p(["sayac_eksik_saat"], {"sayac_eksik_esik_saat": 12})
    r = al.ek_alarmlar(p, {"sayac_eksik_saat": 20, "sayac_vadesi_gelen": 100, "sayac_eksik_donem": "2026-11 (bu ay)"})
    assert r[0][0] == "sayac_eksik_saat" and r[0][1] == "uyari" and "100 sayaç saatinden 20 saat" in r[0][2] and "eşik 12" in r[0][2] and "2026-11" in r[0][2]
    assert al.ek_alarmlar(p, {"sayac_eksik_saat": 11}) == [] and al.ek_alarmlar(p, {"sayac_eksik_saat": None}) == [] and al.ek_alarmlar(p, {}) == []
    for kotu in ({"sayac_eksik_esik_saat": 0}, {"sayac_eksik_esik_saat": 745}):
        with pytest.raises(ValueError, match="sayac_eksik_esik_saat"):
            al.kural_ayarla("t", "p", ["sayac_eksik_saat"], kotu)


def test_ariza_sayaci_ve_hatirlatma_mesajlari():
    p = _p(["ariza_sayaci_yaklasti"], {"ariza_esik": 20})
    r = al.ek_alarmlar(p, {"ariza_sayisi_ay": 22})
    assert r[0][1] == "uyari" and "22" in r[0][2] and "eşiği 20" in r[0][2]
    assert al.ek_alarmlar(p, {"ariza_sayisi_ay": 19}) == [] and al.ek_alarmlar(p, {"ariza_sayisi_ay": None}) == []
    p2 = _p(["teminat_hatirlatma", "avans_hatirlatma"])
    assert al.ek_alarmlar(p2, {}) == []                                                     # zamanlayıcı tetiklemeden sessiz
    t = al.ek_alarmlar(p2, {"hatirlatma": "teminat_hatirlatma"})
    assert [x[0] for x in t] == ["teminat_hatirlatma"] and t[0][1] == "bilgi" and "10:30" in t[0][2] and "11:00" in t[0][2]
    a = al.ek_alarmlar(p2, {"hatirlatma": "avans_hatirlatma"})
    assert [x[0] for x in a] == ["avans_hatirlatma"] and "15:00" in a[0][2] and "17:00" in a[0][2]


def test_takvim_alarmlari_olay_basina(monkeypatch):
    p = _p(["takvim_son_tarih"], {"takvim_gun_once": 3}, segment="lisansli_serbest")
    r = al.takvim_alarmlari(p, bugun=date(2026, 11, 13))   # Cuma: 14.11 itiraz sonucu (1 gün), 16.11 nihai (3 gün), 23.11 fatura (10 gün → dışarıda)
    kod = {m.split(" — ")[1].split(";")[0]: s for _, s, m in r}
    assert any("EPİAŞ itirazları" in k for k in kod) and any("Nihai uzlaştırma" in k for k in kod)
    assert all("Fatura düzenleme" not in k for k in kod)
    uy = next(m for _, s, m in r if "EPİAŞ itirazları" in m); assert uy.startswith("Edikli GES: 14 Kas 2026 Cmt 16:00 — ")
    assert next(s for _, s, m in r if "EPİAŞ itirazları" in m) == "uyari" and next(s for _, s, m in r if "Nihai" in m) == "bilgi"
    assert all("dayanak: " in m for _, _, m in r)
    assert al.takvim_alarmlari(_p(["takvim_son_tarih"], {"takvim_gun_once": 1}, segment="lisansli_serbest"), bugun=date(2026, 11, 20)) == []
    assert al.takvim_alarmlari(_p(["takvim_son_tarih"], {"takvim_gun_once": 3}), bugun=date(2026, 11, 13)) == []   # segment seçili değil → alarm yok


def test_hatirlatma_is_gunu_ve_segment(monkeypatch):
    cagri = []
    monkeypatch.setattr(al, "_tek_kural", lambda plant, kural, ek=None: cagri.append((kural, ek)))
    p = _p(["teminat_hatirlatma"], segment="lisansli_serbest")
    al.hatirlatma(p, "teminat", bugun=date(2026, 11, 2)); assert cagri == [("teminat_hatirlatma", {"hatirlatma": "teminat_hatirlatma"})]   # Pazartesi
    al.hatirlatma(p, "teminat", bugun=date(2026, 11, 1)); assert len(cagri) == 1                                                        # Pazar
    al.hatirlatma(p, "teminat", bugun=date(2027, 1, 1)); assert len(cagri) == 1                                                         # yılbaşı
    al.hatirlatma(_p(["teminat_hatirlatma"], segment="lisanssiz_dagitim"), "teminat", bugun=date(2026, 11, 2)); assert len(cagri) == 1  # lisanssız
    al.hatirlatma(_p([], segment="lisansli_serbest"), "teminat", bugun=date(2026, 11, 2)); assert len(cagri) == 1                        # seçili değil


def test_alicilar_ve_bildir(monkeypatch):
    monkeypatch.setenv("PVQ_ALARM_TO", "ops@ornek.com")
    p = _p([], alarm_alicilar=["sahip@ornek.com", " ops@ornek.com "])
    assert al.alicilar(p) == ["sahip@ornek.com", "ops@ornek.com"]
    monkeypatch.delenv("PVQ_ALARM_TO"); assert al.alicilar(_p([])) == []
    from pvquant.services import posta_service
    gonderilen = []; olaylar = []
    monkeypatch.setattr(posta_service, "gonder", lambda kime, konu, govde: gonderilen.append((kime, konu)) or False)
    monkeypatch.setattr(webhook_service, "gonder", lambda tid, olay, govde, plant_id=None, **k: olaylar.append((tid, olay, govde, plant_id)) or [])
    al._bildir(p, "ptf_dusuk_saat", "Edikli GES: yarın …", "warning")
    assert [k for k, _ in gonderilen] == ["sahip@ornek.com", "ops@ornek.com"] and gonderilen[0][1] == "[PVQuant] Yarın düşük fiyat saati"
    assert olaylar and olaylar[0][1] == "alarm.yeni" and olaylar[0][3] == "p1" and olaylar[0][2]["kural_adi"] == "Yarın düşük fiyat saati"
    assert "alarm.yeni" in webhook_service.OLAYLAR
    monkeypatch.setattr(webhook_service, "gonder", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ağ")))
    al._bildir(p, "veri_gelmedi", "x", "warning")   # webhook hatası yükselmez


def test_isci_isleri_kayitli():
    """Yeni zamanlayıcı işleri iş adı sözlüğünde (müşteri yüzü) ve platform izleme listesinde; _mail kalıntısı yok."""
    from pvquant.services import isler_service, sistem_service
    for ad in ("iletisim_kontrol", "teminat_hatirlatma", "ptf_kontrol", "avans_hatirlatma"):
        assert ad in isler_service.ISIM_TR and any(x[0] == ad for x in sistem_service.IZLENEN_ISLER), ad
    assert not hasattr(al, "_mail")


def test_kural_ayarla_dogrulama_db_dokunmadan():
    with pytest.raises(ValueError, match="takvim_gun_once"):
        al.kural_ayarla("t", "p", ["takvim_son_tarih"], {"takvim_gun_once": 45})
    with pytest.raises(ValueError, match="ariza_esik"):
        al.kural_ayarla("t", "p", [], {"ariza_esik": 0})
    with pytest.raises(ValueError, match="geçersiz"):
        al.kural_ayarla("t", "p", [], None, alicilar=["bozuk-adres"])
    with pytest.raises(ValueError, match="10"):
        al.kural_ayarla("t", "p", [], None, alicilar=[f"a{i}@x.com" for i in range(11)])
    d = al.kural_durumu({"params_json": {"alarm_alicilar": ["a@x.com", 3]}})
    assert d["alicilar"] == ["a@x.com"] and "ortam_alicisi" in d


@pytest.fixture()
def istemci(monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t", "role": "editor", "exp": 0}
    depo = {"params_json": {"alarm_kurallari": [], "alarm_alicilar": []}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "params_json": depo["params_json"]})

    def birlestir(t, p, **a):
        depo["params_json"] = {**depo["params_json"], **a}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_api_alicilar_ve_yeni_esikler(istemci):
    j = istemci.put("/v1/plants/p1/alarm-kurallari", json={"kurallar": ["takvim_son_tarih", "ptf_dusuk_saat"], "esik": {"takvim_gun_once": 5, "ptf_esik_tl_mwh": 250},
                                                            "alicilar": ["Sahip@Ornek.com"]}).json()
    assert j["secili"] == ["takvim_son_tarih", "ptf_dusuk_saat"] and j["esik"]["takvim_gun_once"] == 5 and j["esik"]["ptf_esik_tl_mwh"] == 250
    assert j["alicilar"] == ["sahip@ornek.com"]
    j2 = istemci.put("/v1/plants/p1/alarm-kurallari", json={"kurallar": ["takvim_son_tarih"], "esik": {}}).json()   # alicilar verilmedi → dokunulmaz
    assert j2["alicilar"] == ["sahip@ornek.com"] and j2["secili"] == ["takvim_son_tarih"]
    assert istemci.put("/v1/plants/p1/alarm-kurallari", json={"kurallar": [], "alicilar": ["x"]}).status_code == 422
    assert istemci.get("/v1/plants/p1/alarm-kurallari").json()["alicilar"] == ["sahip@ornek.com"]
