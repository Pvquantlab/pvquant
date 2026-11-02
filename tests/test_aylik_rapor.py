"""v2.525 (raporlama) — dönem raporu: dönem çözümleme (ay/çeyrek/yıl, süren dönem kırpılır, gelecek 422), günlük üretim + beklenti + sapma, olay kaydı ve
olay kaydına göre kullanılabilirlik, POA varsa temel PR, ay döneminde uzlaştırma kalemleri, HTML; zamanlanmış gönderim (ayar doğrulama, günü gelme
kuralı, gönderim sonucu params_json + denetim), API uçları."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import aylik_rapor_service as ar


@pytest.fixture()
def kiraci():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'rapor-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Rapor GES', 1200, 1000, 37.0, 32.0, 'Europe/Istanbul', '{\"segment\": \"lisansli_serbest\", \"alarm_alicilar\": [\"ops@ornek.com\"]}')"), {"p": pid, "t": tid})
        # Ekim 2026: 1–20 Ekim her gün 08–17 TSİ saatlik 100 kWh (10 saat → 1.000 kWh/gün); 1–12 Ekim POA 600 W/m² (saatlik); 21–31 veri yok
        for g in range(1, 21):
            for h in range(8, 18):
                ts = datetime(2026, 10, g, h, tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, poa_wm2, flag) VALUES(:t, :p, :ts, 100, 100, :poa, 'valid')"),
                          {"t": tid, "p": pid, "ts": ts, "poa": (600.0 if g <= 12 else None)})
        rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, mode, model) VALUES (CAST(:t AS uuid), :p, 'C', 'test') RETURNING id"), {"t": tid, "p": pid}).scalar()
        for g in range(1, 32):
            s.execute(text("INSERT INTO forecast_daily(tenant_id, plant_id, gun, p50_kwh, p10_kwh, p90_kwh, run_id, saat_sayisi) VALUES(:t, :p, :g, 1100, 900, 1300, :r, 24)"),
                      {"t": tid, "p": pid, "g": date(2026, 10, g), "r": rid})
        # olaylar: arıza 5 Ekim 10:00–14:00 (500 kW), planlı bakım 7 Ekim 09:00–12:00 (tamamı)
        s.execute(text("INSERT INTO olay(tenant_id, plant_id, tur, baslangic, bitis, etkilenen_kw, durum, eak_gerekcesi) VALUES(:t, :p, 'ariza', :b1, :e1, 500, 'kapali', 'kaynak_yetersizligi'), "
                       "(:t, :p, 'planli_bakim', :b2, :e2, NULL, 'kapali', 'kaynak_yetersizligi')"),
                  {"t": tid, "p": pid, "b1": datetime(2026, 10, 5, 7, tzinfo=timezone.utc), "e1": datetime(2026, 10, 5, 11, tzinfo=timezone.utc),
                   "b2": datetime(2026, 10, 7, 6, tzinfo=timezone.utc), "e2": datetime(2026, 10, 7, 9, tzinfo=timezone.utc)})
    yield tid, {"id": pid, "name": "Rapor GES", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0, "params_json": {"segment": "lisansli_serbest", "alarm_alicilar": ["ops@ornek.com"]}}
    with sistem_baglami() as s:
        for t in ("olay", "forecast_daily", "forecast_runs", "scada_hourly", "sayac_saatlik", "uzlastirma_bildirimi"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_donem_cozumle():
    b = date(2026, 11, 2)
    d = ar.donem_cozumle(None, b); assert d["tur"] == "ay" and d["kod"] == "2026-10" and d["bas"] == date(2026, 10, 1) and d["bit"] == date(2026, 11, 1) and d["saat"] == 744 and not d["kirpildi"]
    q = ar.donem_cozumle("2026-q3", b); assert q["tur"] == "ceyrek" and q["bas"] == date(2026, 7, 1) and q["bit"] == date(2026, 10, 1) and q["etiket"] == "2026 3. çeyrek"
    y = ar.donem_cozumle("2026", b); assert y["tur"] == "yil" and y["kirpildi"] and y["bit"] == date(2026, 11, 3) and "süren dönem" in y["etiket"]
    s = ar.donem_cozumle("2026-11", b); assert s["kirpildi"] and s["saat"] == 48   # 1–2 Kasım
    for kotu in ("2026-13", "2026-Q5", "Ekim", "2027-01"):
        with pytest.raises(ValueError):
            ar.donem_cozumle(kotu, b)
    assert ar.donem_cozumle("2025-Q4", b)["bit"] == date(2026, 1, 1)   # yıl geçişi


def test_veri_rapor_html(kiraci):
    tid, plant = kiraci
    v = ar.veri(tid, plant, "2026-10", bugun=date(2026, 11, 2))
    oz = v["ozet"]
    assert oz["uretim_kwh"] == 20000.0 and oz["beklenen_kwh"] == 34100.0 and oz["ortak_gun"] == 20 and oz["sapma_pct"] == round((20000 - 22000) / 22000 * 100, 1)
    assert oz["saat"] == 200 and oz["beklenen_saat"] == 744 and oz["kapsam_pct"] == 26.9 and oz["veri_gun"] == 20 and oz["olay"] == 2 and oz["ariza"] == 1
    assert len(v["gunler"]) == 31 and v["gunler"][0]["kwh"] == 1000.0 and v["gunler"][0]["sapma_pct"] == -9.1 and v["gunler"][25]["kwh"] is None and v["aylar"] is None
    # olay kaydına göre kullanılabilirlik: arıza 4 sa × 500/1000 = 2 eşdeğer saat / 744; planlı bakım istisna (3 sa × 1)
    k = v["kullanilabilirlik"]; assert k["ariza_esdeger_saat"] == 2.0 and k["istisna_esdeger_saat"] == 3.0 and k["oran"] == round(1 - 2 / 744, 4)
    # PR: 12 gün POA; E = 12.000 kWh, H = 12 × 10 × 0,6 = 72 kWh/m² → (12000/1200)/72 = 0,1389
    assert v["pr"]["gun"] == 12 and v["pr"]["h_kwh_m2"] == 72.0 and v["pr"]["pr"] == round((12000 / 1200) / 72, 3)
    assert v["olaylar"][0]["etiket"] == "Arıza" and v["olaylar"][0]["sure_saat"] == 4.0 and v["olaylar"][1]["istisna"]
    assert v["uzlastirma"] is not None and ("satirlar" in v["uzlastirma"] or "hata" in v["uzlastirma"])
    r, _ = ar.rapor(tid, plant, "2026-10", bugun=date(2026, 11, 2))
    adlar = [a for a, _ in r.bolumler]; assert adlar[:2] == ["Özet", "Günlük üretim ve beklenti"] and "Olay kaydı" in adlar and "Notlar" in adlar and "Performans oranı" in adlar
    h = ar.html(r); assert h.startswith("<!doctype html>") and "Ekim 2026" in h and "20.000" in h and "Arıza" in h and "Üretim zamanı" in h
    # 02.11 inceleme: veri durumu sınıfı önizleme JSON'unda, HTML Özet tablosunda ve kaynak listesi Notlar'da; ölçüm yoksa üretim «yok» (None), 0 değil
    assert v["ozet"]["veri_durumu"] == "kismi" and v["ozet"]["veri_durumu_metni"].startswith("Kısmi: 200/744") and "Kısmi: 200/744" in h and "Kaynaklar:" in h
    bos = ar.veri(tid, plant, "2026-09", bugun=date(2026, 11, 2))
    assert bos["ozet"]["uretim_kwh"] is None and bos["ozet"]["beklenen_kwh"] is None and bos["ozet"]["veri_durumu"] == "yok" and bos["ozet"]["sapma_pct"] is None
    assert "—" in ar.html(ar.rapor(tid, plant, "2026-09", bugun=date(2026, 11, 2))[0])
    # çeyrek: aylık tablo, günlük tablo yok, uzlaştırma yok (not)
    c = ar.veri(tid, plant, "2026-Q4", bugun=date(2026, 11, 2)); assert c["gunler"] == [] and c["aylar"][0]["ay"] == "2026-10" and c["aylar"][0]["uretim_kwh"] == 20000.0 and c["uzlastirma"] is None
    assert any("yalnız ay döneminde" in n for n in c["notlar"])
    assert ar.pr_temel(__import__("pandas").DataFrame({"poa_saat": [0] * 31, "poa_kwh_m2": [None] * 31, "kwh": [1.0] * 31}), 1200.0) is None   # POA yoksa PR yok


def test_gonderim_ayar_kural_ve_gonder(kiraci, monkeypatch):
    tid, plant = kiraci
    assert ar.gonderim_dogrula({"aktif": True, "gun": 5, "alicilar": ["a@b.c", " d@e.f "]}) == {"aktif": True, "gun": 5, "alicilar": ["a@b.c", "d@e.f"]}
    for kotu in ({"aktif": "evet"}, {"gun": 0}, {"gun": 29}, {"alicilar": ["adres"]}, {"alicilar": "a@b.c"}):
        with pytest.raises(ValueError):
            ar.gonderim_dogrula(kotu)
    g = ar.gonderim_ayari({"rapor_gonderim": {"aktif": True, "gun": "4", "alicilar": ["x@y.z", 5, ""]}}); assert g == {"aktif": True, "gun": 4, "alicilar": ["x@y.z"]}
    assert ar.gonderim_ayari(None) == {"aktif": False, "gun": 3, "alicilar": []}
    # günü gelme: aktif değil → hayır; 2 Kasım, gün 3 → hayır; 3 Kasım → evet; 10 Kasım (geçmiş, gönderilmemiş) → evet; bu ay gönderildiyse → hayır
    assert not ar.gonderilmeli_mi({"rapor_gonderim": {"aktif": False, "gun": 1}}, date(2026, 11, 5))
    assert not ar.gonderilmeli_mi({"rapor_gonderim": {"aktif": True, "gun": 3}}, date(2026, 11, 2))
    assert ar.gonderilmeli_mi({"rapor_gonderim": {"aktif": True, "gun": 3}}, date(2026, 11, 3)) and ar.gonderilmeli_mi({"rapor_gonderim": {"aktif": True, "gun": 3}}, date(2026, 11, 10))
    assert not ar.gonderilmeli_mi({"rapor_gonderim": {"aktif": True, "gun": 3, "son_donem": "2026-10"}}, date(2026, 11, 10))
    # alıcılar: ayarda yoksa alarm alıcıları
    assert ar.alicilar(plant) == ["ops@ornek.com"] and ar.alicilar({**plant, "params_json": {**plant["params_json"], "rapor_gonderim": {"alicilar": ["f@g.h"]}}}) == ["f@g.h"]
    # gönderim: SMTP yok → yapılandırılmadı; var → gönderildi; sonuç params_json'da
    from pvquant.services import posta_service
    monkeypatch.setattr(posta_service, "yapilandirildi", lambda: False)
    r = ar.gonder(tid, plant, "2026-10", bugun=date(2026, 11, 2), kaynak="elle"); assert r["durum"] == "posta_yapilandirilmadi" and r["donem"] == "2026-10" and r["alici"] == 1
    gonderilen = {}
    monkeypatch.setattr(posta_service, "yapilandirildi", lambda: True)
    monkeypatch.setattr(posta_service, "gonder", lambda kime, konu, govde, html=None: gonderilen.update({"kime": kime, "konu": konu, "html": html}) or True)
    r2 = ar.gonder(tid, plant, "2026-10", bugun=date(2026, 11, 2)); assert r2["durum"] == "gonderildi" and gonderilen["kime"] == "ops@ornek.com" and "Ekim 2026" in gonderilen["konu"] and gonderilen["html"].startswith("<!doctype")
    with sistem_baglami() as s:
        pj = s.execute(text("SELECT params_json FROM plants WHERE id=:p"), {"p": plant["id"]}).scalar()
    assert pj["rapor_gonderim"]["son_durum"] == "gonderildi" and pj["rapor_gonderim"]["son_donem"] == "2026-10" and pj["rapor_gonderim"]["son_gonderim"]
    assert not ar.gonderilmeli_mi(pj, date(2026, 11, 10))   # bu ay gönderildi
    assert pj["rapor_gonderim"]["deneme"] == 0
    # 02.11 inceleme — yeniden deneme: başarısız gönderim dönemi kapatmaz; günde bir, en çok 3 deneme; bugün denendiyse bekler
    monkeypatch.setattr(posta_service, "gonder", lambda *a, **k: False)
    r3 = ar.gonder(tid, plant, "2026-10", bugun=date(2026, 11, 2)); assert r3["durum"] == "gonderim_hatasi"
    with sistem_baglami() as s:
        pj = s.execute(text("SELECT params_json FROM plants WHERE id=:p"), {"p": plant["id"]}).scalar()
    assert pj["rapor_gonderim"]["son_durum"] == "gonderim_hatasi" and pj["rapor_gonderim"]["deneme"] == 1
    bugun_kayit = date.fromisoformat(pj["rapor_gonderim"]["son_gonderim"][:10])
    pjg = {"rapor_gonderim": {**pj["rapor_gonderim"], "aktif": True}}   # fixture'da zamanlama kapalı; kural için açık kopya
    assert not ar.gonderilmeli_mi(pjg, bugun_kayit) and ar.gonderilmeli_mi(pjg, date(2026, 11, 10) if bugun_kayit != date(2026, 11, 10) else date(2026, 11, 11))
    assert not ar.gonderilmeli_mi({"rapor_gonderim": {**pjg["rapor_gonderim"], "deneme": 3}}, date(2026, 11, 20))
    # rapor üretim hatası e-posta hatasından ayrı durumdur ve kayda düşer
    monkeypatch.setattr(ar, "rapor", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tablo yok")))
    r4 = ar.gonder(tid, {**plant, "params_json": pj}, "2026-10", bugun=date(2026, 11, 2)); assert r4["durum"] == "rapor_hatasi" and r4["donem"] == "2026-10"   # worker/API gibi güncel ayarla
    with sistem_baglami() as s:
        pj = s.execute(text("SELECT params_json FROM plants WHERE id=:p"), {"p": plant["id"]}).scalar()
    assert pj["rapor_gonderim"]["son_durum"] == "rapor_hatasi" and pj["rapor_gonderim"]["deneme"] == 2


def test_api_rapor_donem_ve_gonderim(kiraci, monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service, posta_service
    tid, plant = kiraci
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "admin", "exp": 0}
    satir = {"id": plant["id"], "name": "Rapor GES", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0, "params_json": dict(plant["params_json"])}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: satir if p == plant["id"] else None)
    kayit = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: kayit.append((a, k)))
    monkeypatch.setattr(posta_service, "yapilandirildi", lambda: False)
    c = TestClient(api_main.app)
    try:
        j = c.get(f"/v1/plants/{plant['id']}/rapor-donem?donem=2026-10&fmt=json"); assert j.status_code == 200 and j.json()["ozet"]["uretim_kwh"] == 20000.0 and j.json()["donem"]["kod"] == "2026-10"
        h = c.get(f"/v1/plants/{plant['id']}/rapor-donem?donem=2026-10"); assert h.status_code == 200 and h.headers["content-disposition"].endswith('2026-10.html"') and "<h1>" in h.text
        assert kayit[-1][0][:2] == ("musteri", "rapor_donem_indir")
        assert c.get(f"/v1/plants/{plant['id']}/rapor-donem?donem=2099-01").status_code == 422 and c.get(f"/v1/plants/{plant['id']}/rapor-donem?fmt=pdf").status_code == 422
        g = c.get(f"/v1/plants/{plant['id']}/rapor-gonderim"); assert g.status_code == 200 and g.json()["aktif"] is False and g.json()["varsayilan_alicilar"] == ["ops@ornek.com"] and g.json()["posta_yapilandirildi"] is False
        p = c.put(f"/v1/plants/{plant['id']}/rapor-gonderim", json={"aktif": True, "gun": 5, "alicilar": ["mali@ornek.com"]}); assert p.status_code == 200, p.text
        assert p.json()["aktif"] and p.json()["gun"] == 5 and p.json()["alicilar"] == ["mali@ornek.com"] and kayit[-1][0][1] == "rapor_gonderim_ayar" and kayit[-1][1]["ayrinti"]["alicilar"] == 1
        assert c.put(f"/v1/plants/{plant['id']}/rapor-gonderim", json={"gun": 31}).status_code == 422
        d = c.post(f"/v1/plants/{plant['id']}/rapor-gonderim/dene?donem=2026-10"); assert d.status_code == 200 and d.json()["durum"] == "posta_yapilandirilmadi"
        assert c.get("/v1/plants/00000000-0000-0000-0000-000000000000/rapor-donem").status_code == 404
    finally:
        api_main.app.dependency_overrides.clear()
