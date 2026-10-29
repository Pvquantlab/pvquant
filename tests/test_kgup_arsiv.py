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
    csv = f"Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n25.10.2026;0;UEVCB-1;{satir};9,000\n"
    return {"gun": gun, "kantil": kantil, "csv": csv, "sha256": hashlib.sha256(csv.encode("utf-8-sig")).hexdigest(),
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
