"""v2.502 — KGÜP sürüm arşivi (F-06): DB testi (kgup_surum, RLS, değiştirilemezlik) + API kapıları (sahte servis)."""
import hashlib
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import kgup_arsiv_service as ka

PLANT = "22222222-2222-2222-2222-222222222222"


def _ornek(gun="2026-10-25", kantil="p50", satir="0,5"):
    """24 saatlik örnek dosya: saat 0 = `satir`, diğer saatler 0,000 (kıyas testleri 24 saat ister)."""
    csv = "Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n" + "\n".join(f"25.10.2026;{h};UEVCB-1;{satir if h == 0 else '0,000'};9,000" for h in range(24)) + "\n"
    return {"gun": gun, "kantil": kantil, "csv": csv, "bom": True, "sha256": hashlib.sha256(csv.encode("utf-8-sig")).hexdigest(),   # v2.512: BOM şablona bağlı
            "kosu": {"run_id": str(uuid.uuid4()), "run_at": "2026-10-24T06:12:00+00:00", "kesim": "2026-10-24T12:30:00+00:00"},
            "eak": {"eak_mw": 9.0, "kaynak": "ac_tavani"}, "toplam_mwh": 40.5, "dosya_adi": f"KGUP_UEVCB-1_{gun}_{kantil}.csv",
            "sablon": {"durum": "karşılaştırılmadı", "kolonlar": ["Tarih", "Saat", "UEVCB", "KGUP_MWh", "EAK_MW"]}}


@pytest.fixture()
def kiraci():
    """Geçici kiracı + santral; test sonunda silinir (kgup_surum satırları pvquant rolüyle temizlenir — pvq_app silemez)."""
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'arsiv-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz) VALUES(:p, :t, 'A', 1000, 37.0, 32.0, 'Europe/Istanbul')"), {"p": pid, "t": tid})
    yield tid, pid
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM kgup_surum WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_kaydet_surum_sha_ve_degistirilemezlik(kiraci):
    tid, pid = kiraci
    r1 = ka.kaydet(tid, pid, _ornek()); assert r1["yeni"] and r1["surum"] == 1 and len(r1["sha256"]) == 64
    r1b = ka.kaydet(tid, pid, _ornek()); assert not r1b["yeni"] and r1b["id"] == r1["id"]            # aynı içerik → yeni sürüm yok
    r2 = ka.kaydet(tid, pid, _ornek(satir="0,7")); assert r2["yeni"] and r2["surum"] == 2            # içerik değişti → sürüm 2
    r3 = ka.kaydet(tid, pid, _ornek(gun="2026-10-26")); assert r3["surum"] == 1                      # başka gün kendi sayacı
    liste = ka.listele(tid, pid); assert [(x["teslim_gunu"], x["surum"]) for x in liste] == [("2026-10-26", 1), ("2026-10-25", 2), ("2026-10-25", 1)]
    assert ka.listele(tid, pid, date(2026, 10, 25))[0]["surum"] == 2 and liste[1]["bayt"] > 0 and liste[1]["run_at"]
    g = ka.getir(tid, pid, r2["id"]); assert g["dosya"].startswith(b"\xef\xbb\xbf") and hashlib.sha256(g["dosya"]).hexdigest() == r2["sha256"] and g["surum"] == 2
    assert ka.getir(tid, pid, str(uuid.uuid4())) is None
    with pytest.raises(ValueError):                                                                     # yanıt sha'sı dosya baytlarıyla uyuşmalı
        ka.kaydet(tid, pid, {**_ornek(satir="0,9"), "sha256": "0" * 64})
    # değiştirilemezlik: uygulama rolü (pvq_app) UPDATE/DELETE yapamaz
    for sql in ("UPDATE kgup_surum SET surum = 99 WHERE id = :i", "DELETE FROM kgup_surum WHERE id = :i"):
        with pytest.raises(Exception) as e:                      # her deneme ayrı işlemde (ilk hata işlemi iptal eder)
            with tenant_baglami(tid) as s:
                s.execute(text(sql), {"i": r1["id"]})
        assert "permission denied" in str(e.value).lower()
    # RLS: başka kiracı görmez
    assert ka.listele(str(uuid.uuid4()), pid) == []


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service, kgup_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 10000.0, "ac_limit_kw": 9000.0, "params_json": {"uevcb": "UEVCB-1"}})
    monkeypatch.setattr(kgup_service, "uret", lambda t, pl, gun, kantil="p50", uevcb=None: _ornek(gun.isoformat(), kantil))
    kayit = {}
    monkeypatch.setattr(ka, "kaydet", lambda t, p, r, indiren=None: kayit.setdefault("k", {"id": "s1", "surum": 3, "sha256": r["sha256"], "yeni": True, "indiren": indiren}))
    monkeypatch.setattr(ka, "listele", lambda t, p, g=None, n=30: [{"id": "s1", "teslim_gunu": "2026-10-25", "surum": 3, "kantil": "p50", "sha256": "a" * 64, "dosya_adi": "x.csv", "olusturma": "2026-10-24T10:00:00+00:00", "indiren": "u@x", "bayt": 80, "run_id": None, "run_at": None, "kesim": None, "eak_mw": 9.0, "eak_kaynak": "ac_tavani", "toplam_mwh": 40.5}])
    monkeypatch.setattr(ka, "getir", lambda t, p, i: {"dosya": b"\xef\xbb\xbfTarih;Saat\n", "dosya_adi": "KGUP_s1.csv", "sha256": "a" * 64, "surum": 3, "teslim_gunu": "2026-10-25"} if i == "s1" else None)
    yield TestClient(api_main.app), kayit
    api_main.app.dependency_overrides.clear()


def test_csv_indirme_arsive_yazar_ve_surum_uclari(istemci):
    c, kayit = istemci
    r = c.get(f"/v1/plants/{PLANT}/kgup?gun=2026-10-25")
    assert r.status_code == 200 and r.headers["X-PVQ-Surum"] == "3" and len(r.headers["X-PVQ-SHA256"]) == 64 and kayit["k"]["indiren"] == "u1"
    assert "k" in kayit and c.get(f"/v1/plants/{PLANT}/kgup?gun=2026-10-25&fmt=json").status_code == 200   # json önizleme arşive yazmaz (tek kayıt kaldı)
    j = c.get(f"/v1/plants/{PLANT}/kgup/surumler").json(); assert j["surumler"][0]["surum"] == 3
    assert c.get(f"/v1/plants/{PLANT}/kgup/surumler?gun=2026-13-01").status_code == 422
    d = c.get(f"/v1/plants/{PLANT}/kgup/surumler/s1"); assert d.status_code == 200 and d.content.startswith(b"\xef\xbb\xbf") and d.headers["X-PVQ-Surum"] == "3"
    assert c.get(f"/v1/plants/{PLANT}/kgup/surumler/yok").status_code == 404


def test_eak_dosyasi_arsivlenir(kiraci):
    """v2.513: EAK dosyası (TPYS EAK.csv) kaynak 'eak' ile değiştirilemez kayıt; sürüm sayacı KGÜP'ten ayrı; kıyasa girmez."""
    tid, pid = kiraci
    eak = "Saat,Miktar,ic_tuketim,kaynak_yetersizligi,iklim_verim,mucbir,dissal,guvenlik\r\n" + "".join(f"{h},9,,1,,,,\r\n" for h in range(24))
    r = {**_ornek(), "csv": eak, "bom": False, "sha256": hashlib.sha256(eak.encode()).hexdigest(), "kantil": "eak", "toplam_mwh": None, "dosya_adi": "EAK_UEVCB-1_2026-10-25.csv"}
    k1 = ka.kaydet(tid, pid, r, kaynak="eak"); k2 = ka.kaydet(tid, pid, r, kaynak="eak")
    assert k1["yeni"] and k1["surum"] == 1 and k1["kaynak"] == "eak" and not k2["yeni"]
    kg = ka.kaydet(tid, pid, _ornek()); assert kg["surum"] == 1                      # KGÜP sayacı ayrı
    l = ka.listele(tid, pid); assert {x["kaynak"] for x in l} == {"eak", "pvquant"} and next(x for x in l if x["kaynak"] == "eak")["kantil"] == "eak"
    g = ka.getir(tid, pid, k1["id"]); assert g["dosya"] == eak.encode() and not g["dosya"].startswith(b"\xef\xbb\xbf")
    with pytest.raises(ValueError):
        ka.kaydet(tid, pid, r, kaynak="baska")


# ---------------------------------------------------------------- v2.503: müşteri KGÜP içe alma + kıyas ------------------------
def test_csv_oku_sablon_ve_ceyrek():
    sat = "\n".join(f"25.10.2026;{h};UEVCB-1;{str(round(h*0.5,3)).replace('.', ',')};9,000" for h in range(24))
    t = ka.csv_oku(("Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n" + sat + "\n").encode("utf-8-sig"))
    assert t["saat"].tolist() == list(range(24)) and t.kgup_mwh[3] == 1.5 and t.eak_mw[0] == 9.0
    # virgül ayraç + nokta ondalık, farklı başlık adları
    t2 = ka.csv_oku(("Date,Hour,UEVCB,Program_MWh\n" + "\n".join(f"2026-10-25,{h},X,{h*0.25}" for h in range(24))).encode())
    assert t2.kgup_mwh[4] == 1.0 and t2["eak_mw"] is None or t2["eak_mw"].isna().all()
    # çeyrek satırlar saatliğe toplanır
    q = "Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW;Ceyrek\n" + "\n".join(f"25.10.2026;{h};U;0,250;9,000;{m}" for h in range(24) for m in (0, 15, 30, 45))
    t3 = ka.csv_oku(q.encode()); assert len(t3) == 24 and t3.kgup_mwh[0] == 1.0 and t3.eak_mw[0] == 9.0
    with pytest.raises(ValueError):
        ka.csv_oku(b"Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n25.10.2026;0;U;1,0;9,0\n")            # 24 saat yok
    with pytest.raises(ValueError):
        ka.csv_oku(("Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n" + "\n".join(f"25.10.2026;{h};U;-1;9" for h in range(24))).encode())   # negatif


def test_musteri_kaydet_ve_kiyas(kiraci):
    tid, pid = kiraci
    o = ka.kaydet(tid, pid, _ornek(satir="0,5"))                                       # öneri (pvquant) sürüm 1
    sat = "\n".join(f"25.10.2026;{h};UEVCB-1;{'0,700' if h == 0 else '0,000'};9,000" for h in range(24))
    b = ("Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n" + sat + "\n").encode("utf-8-sig")
    m = ka.musteri_kaydet(tid, pid, date(2026, 10, 25), b, "tpys.csv", indiren=None)
    assert m["yeni"] and m["surum"] == 1 and m["kaynak"] == "musteri" and m["toplam_mwh"] == 0.7
    assert not ka.musteri_kaydet(tid, pid, date(2026, 10, 25), b, "tpys.csv")["yeni"]  # aynı içerik
    l = ka.listele(tid, pid, date(2026, 10, 25)); assert sorted((x["kaynak"], x["surum"]) for x in l) == [("musteri", 1), ("pvquant", 1)]
    k = ka.kiyas(tid, pid, date(2026, 10, 25))
    assert k["oneri"]["surum"] == 1 and k["bildirilen"]["surum"] == 1 and k["ozet"]["farkli_saat"] == 1 and k["ozet"]["en_buyuk_fark_saat"] == 0
    assert k["ozet"]["fark_toplam_mwh"] == pytest.approx(0.2) and not k["ozet"]["ayni"] and k["saatler"][0]["fark_mwh"] == pytest.approx(0.2)
    assert ka.kiyas(tid, pid, date(2026, 10, 26))["ozet"] is None
    with pytest.raises(ValueError):
        ka.musteri_kaydet(tid, pid, date(2026, 10, 25), b"Tarih;Saat\n", "bozuk.csv")
    assert o["kaynak"] == "pvquant"


def test_bildirilen_yukleme_ve_kiyas_kapilari(monkeypatch):
    from apps.api.deps import yazma_yetkisi
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t", "role": "editor", "exp": 0}
    try:
        from pvquant.services import plant_service
        monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {}})
        kayit = {}
        monkeypatch.setattr(ka, "musteri_kaydet", lambda t, p, g, b, ad, indiren=None, sablon=None: kayit.setdefault("m", {"id": "m1", "surum": 1, "sha256": "b" * 64, "yeni": True, "kaynak": "musteri", "toplam_mwh": 12.0, "satir": 24, "bayt": len(b)}))
        monkeypatch.setattr(ka, "kiyas", lambda t, p, g: {"gun": g.isoformat(), "oneri": None, "bildirilen": {"surum": 1}, "saatler": [], "ozet": None})
        c = TestClient(api_main.app)
        r = c.post(f"/v1/plants/{PLANT}/kgup/bildirilen?gun=2026-10-25", files={"dosya": ("tpys.csv", b"Tarih;Saat\n0;1\n", "text/csv")})
        assert r.status_code == 200 and r.json()["kayit"]["surum"] == 1 and r.json()["kiyas"]["gun"] == "2026-10-25" and kayit["m"]["bayt"] > 0
        assert c.post(f"/v1/plants/{PLANT}/kgup/bildirilen?gun=2026-13-25", files={"dosya": ("t.csv", b"x", "text/csv")}).status_code == 422
        assert c.post(f"/v1/plants/{PLANT}/kgup/bildirilen?gun=2026-10-25", files={"dosya": ("t.csv", b"", "text/csv")}).status_code == 422
        assert c.get(f"/v1/plants/{PLANT}/kgup/kiyas?gun=2026-10-25").json()["bildirilen"]["surum"] == 1
        assert c.get(f"/v1/plants/{PLANT}/kgup/kiyas?gun=x").status_code == 422
    finally:
        api_main.app.dependency_overrides.clear()


def test_temizle_saklama(kiraci, monkeypatch):
    """29.10 F-06 saklama — teslim günü N aydan eski satırlar silinir; 0 dokunmaz; 1–14 tabana (15) çekilir; taze kayıt kalır."""
    tid, pid = kiraci
    from dateutil.relativedelta import relativedelta
    bugun = date.today()
    for gun in (bugun - relativedelta(months=40), bugun - relativedelta(months=16), bugun - relativedelta(days=1)):
        ka.kaydet(tid, pid, _ornek(gun=gun.isoformat()))
    assert len(ka.listele(tid, pid)) == 3
    assert ka.temizle(0) == 0 and len(ka.listele(tid, pid)) == 3
    assert ka.temizle(24) == 1 and {r["teslim_gunu"] for r in ka.listele(tid, pid)} == {(bugun - relativedelta(months=16)).isoformat(), (bugun - relativedelta(days=1)).isoformat()}
    assert ka.temizle(3) == 1                                                        # taban 15 ay → 16 aylık silinir, dünkü kalır
    assert [r["teslim_gunu"] for r in ka.listele(tid, pid)] == [(bugun - relativedelta(days=1)).isoformat()]
    monkeypatch.setattr("pvquant.config.get_settings", lambda: type("S", (), {"kgup_saklama_ay": 0})())
    assert ka.temizle() == 0                                                         # ayar 0 → dokunmaz
    assert ka.SAKLAMA_TABAN_AY == 15
