"""v2.553 (Aşama 2, S3): üretim dosyası itme — klasör tarama (gelen → islenen/hatali, bekleme süresi, tanınmayan klasör), dosya işleme hatası sınıfları, dış API ucu
(kapsam, 422/200) ve kapsam sicili. DB yazımı sahte; gerçek SFTP yok."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from pvquant.services import itme_service as it


def _plant(pid="11111111-1111-1111-1111-111111111111"):
    return {"id": pid, "tenant_id": "t1", "name": "Edikli", "capacity_kwp": 15230.0, "lat": 38.4, "lon": 34.6, "tz": "Europe/Istanbul", "params_json": {}}


def test_klasor_tara_akislari(tmp_path):
    p = _plant()
    kok = tmp_path / "itme"
    it.klasor_hazirla(kok, p["id"])
    (kok / "baska-klasor").mkdir()                                          # santral kimliği değil → dokunulmaz
    (kok / "baska-klasor" / "x.csv").write_text("a")
    gelen = kok / p["id"] / "gelen"
    (gelen / "iyi.csv").write_text("ts,kw\n2026-11-09 10:00,100\n"); (gelen / "kotu.xlsx").write_bytes(b"x"); (gelen / "taze.csv").write_text("…"); (gelen / "notlar.txt").write_text("…")
    eski = time.time() - 600
    for ad in ("iyi.csv", "kotu.xlsx"):
        import os; os.utime(gelen / ad, (eski, eski))
    def isle(tenant_id, plant, yol, ad, kanal):
        assert kanal == "itme_klasor" and plant["id"] == p["id"]
        return {"durum": "ok", "n_satir": 24} if ad == "iyi.csv" else {"durum": "hata", "hata": "kolon eşlemesi kurulamadı"}
    r = it.klasor_tara(kok, [p], isle=isle)
    assert "iyi.csv → ok (24 satır)" in r and "kotu.xlsx → hata" in r
    assert not (gelen / "iyi.csv").exists() and (gelen / "taze.csv").exists() and (gelen / "notlar.txt").exists()   # taze dosya ve .txt beklemede
    assert len(list((kok / p["id"] / "islenen").glob("*_iyi.csv"))) == 1
    assert len(list((kok / p["id"] / "hatali").glob("*_kotu.xlsx"))) == 1 and len(list((kok / p["id"] / "hatali").glob("*_kotu.xlsx.hata.txt"))) == 1
    assert (kok / "baska-klasor" / "x.csv").exists()
    assert it.klasor_tara(None, [p]) is None and it.klasor_tara(tmp_path / "yok", [p]) is None and it.klasor_tara(kok, [p], isle=isle) is None   # ikinci tur: iş yok


def test_dosya_isle_sinirlar_ve_hata_siniflari(tmp_path, monkeypatch):
    p = _plant()
    kotu = tmp_path / "x.txt"; kotu.write_text("a")
    assert "uzantı" in it.dosya_isle("t1", p, kotu, "x.txt")["hata"]
    buyuk = tmp_path / "b.csv"; buyuk.write_bytes(b"0" * 10)
    monkeypatch.setattr(it, "AZAMI_BAYT", 5)
    assert "50 MB" in it.dosya_isle("t1", p, buyuk, "b.csv")["hata"]
    monkeypatch.setattr(it, "AZAMI_BAYT", 50 * 1024 * 1024)
    # gerçek alım hattı: otomatik eşleme + sahte kalıcılaştırma
    csv = tmp_path / "scada.csv"
    satirlar = ["timestamp,power_kw"] + [f"2026-06-0{d} {h:02d}:00,{(0 if h < 6 or h > 19 else 800)}" for d in (1, 2) for h in range(24)]
    csv.write_text("\n".join(satirlar) + "\n")
    from pvquant.services import ingest_service
    kayit = {}
    monkeypatch.setattr(ingest_service, "yukle_ve_kaydet", lambda t, pid, ad, **k: kayit.update({"ad": ad, "n": len(k["hazir_sonuc"].data)}) or {"batch_id": "b1", "n_satir": len(k["hazir_sonuc"].data)})
    r = it.dosya_isle("t1", p, csv, "scada.csv", kanal="itme_http")
    assert r["durum"] == "ok" and r["batch_id"] == "b1" and r["n_satir"] == 48 and kayit["ad"] == "itme_http:scada.csv" and "n_rows_valid" in r["karne"]
    # cihaz bazlı dosya: tekrar politikası yoksa hata, 'sum' ile geçer
    cih = tmp_path / "cihaz.csv"
    cih.write_text("\n".join(["timestamp,power_kw"] + [f"2026-06-01 {h:02d}:00,{v}" for h in range(24) for v in (300, 500)]) + "\n")
    r2 = it.dosya_isle("t1", p, cih, "cihaz.csv")
    assert r2["durum"] == "hata" and "cihaz bazlı" in r2["hata"]
    p2 = {**p, "params_json": {"itme": {"tekrar": "sum"}}}
    assert it.tekrar_politikasi(p2) == "sum" and it.dosya_isle("t1", p2, cih, "cihaz.csv")["durum"] == "ok"


def test_dis_api_itme_ucu(monkeypatch):
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from pvquant.services import api_anahtar_service as ak, plant_service
    ak._kovalar.clear()
    def _kayit(secret, **k):
        r = {"id": "k1", "tenant_id": "t1", "key_hash": hashlib.sha256(secret.encode()).hexdigest(), "scopes": ["gerceklesen:yaz"], "revoked": False, "expires_at": None, "rpm": 120}
        r.update(k); return r
    monkeypatch.setattr(ak, "_kayit_bul", lambda pfx: _kayit("gizli") if pfx == "abcd1234" else (_kayit("gizli", scopes=["tahmin:oku"]) if pfx == "okur0000" else None))
    monkeypatch.setattr(ak, "_kullanim_isle", lambda i: None)
    monkeypatch.setattr(ak, "_paylasimli_izin", lambda p, r, t: ak._kova_izin(p, r))
    monkeypatch.setattr(plant_service, "getir", lambda t, p: _plant(p) if p == "p1" else None)
    izler = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: izler.append(k.get("ayrinti")))
    monkeypatch.setattr(it, "dosya_isle", lambda t, plant, yol, ad, kanal="itme_http": {"durum": "ok", "kanal": kanal, "dosya": ad, "batch_id": "b9", "n_satir": 7, "karne": {}} if ad.endswith(".csv") else {"durum": "hata", "hata": "uzantı desteklenmiyor"})
    c = TestClient(api_main.app)
    dosya = {"dosya": ("gun.csv", b"timestamp,power_kw\n2026-06-01 10:00,1\n", "text/csv")}
    assert c.post("/v1/dis/santral/p1/uretim-dosyasi", files=dosya).status_code == 422                                                     # başlık yok
    assert c.post("/v1/dis/santral/p1/uretim-dosyasi", files=dosya, headers={"X-API-Key": "pvq_okur0000_gizli"}).status_code == 403          # kapsam yok
    r = c.post("/v1/dis/santral/p1/uretim-dosyasi", files=dosya, headers={"X-API-Key": "pvq_abcd1234_gizli"})
    assert r.status_code == 200 and r.json()["n_satir"] == 7 and r.json()["kanal"] == "itme_http" and izler[-1]["durum"] == "ok"
    r2 = c.post("/v1/dis/santral/p1/uretim-dosyasi", files={"dosya": ("x.txt", b"a", "text/plain")}, headers={"X-API-Key": "pvq_abcd1234_gizli"})
    assert r2.status_code == 422 and "uzantı" in r2.json()["detail"] and izler[-1]["durum"] == "hata"
    assert c.post("/v1/dis/santral/yok/uretim-dosyasi", files=dosya, headers={"X-API-Key": "pvq_abcd1234_gizli"}).status_code == 404
    from pvquant.ext.platform.api_anahtar import KAPSAMLAR
    assert "gerceklesen:yaz" in KAPSAMLAR and "gerceklesen:yaz" in ak.CANLI_KAPSAMLAR and "gerceklesen:yaz" in ak.KAPSAM_ACIKLAMA
