"""v2.556 (Aşama 3, K1) — zarf şifreleme kasası: gidiş-dönüş, AAD bağlamı, KEK yokluğu, KEK dönüşü."""
from __future__ import annotations

import pytest

from pvquant.guvenlik import kasa

VERI = {"kullanici": "nbi_user", "sistem_kodu": "gizli-123"}
AAD = "t:p:fusionsolar"


def _temiz(monkeypatch):
    for k in ("PVQ_KEK", "PVQ_KEK_ID", "PVQ_KEK_ESKI"):
        monkeypatch.delenv(k, raising=False)


def test_zarf_gidis_donus_ve_aad(monkeypatch):
    _temiz(monkeypatch); monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret())
    z = kasa.sifrele_json(VERI, AAD)
    assert set(z) == {"kek_id", "dek_sarili", "sifreli", "surum"} and z["kek_id"] == "k1" and z["surum"] == 1
    assert b"gizli-123" not in z["sifreli"] and b"nbi_user" not in z["sifreli"] and len(z["dek_sarili"]) == 12 + 32 + 16
    assert kasa.coz_json(z, AAD) == VERI
    with pytest.raises(kasa.KasaHata, match="bağlam"):
        kasa.coz_json(z, "t:p2:fusionsolar")   # başka santrala taşınamaz
    assert kasa.sifrele_json(VERI, AAD)["sifreli"] != z["sifreli"]   # kayıt başına rastgele DEK/nonce
    assert kasa.kek_durum() == {"var": True, "id": "k1", "eski": []}


def test_kek_yok_ya_da_bozuk(monkeypatch):
    _temiz(monkeypatch)
    assert kasa.kek_durum()["var"] is False
    with pytest.raises(kasa.KasaHata, match="PVQ_KEK tanımlı değil"):
        kasa.sifrele(b"x", AAD)
    monkeypatch.setenv("PVQ_KEK", "kisa")
    d = kasa.kek_durum(); assert d["var"] is False and "hata" in d
    monkeypatch.setenv("PVQ_KEK", "AAAA")   # 3 bayt
    assert "32 bayt" in kasa.kek_durum()["hata"]


def test_kek_donusu_eski_anahtarla_cozme_ve_yeniden_sarma(monkeypatch):
    _temiz(monkeypatch)
    k0 = kasa.anahtar_uret(); monkeypatch.setenv("PVQ_KEK", k0); monkeypatch.setenv("PVQ_KEK_ID", "k0")
    z = kasa.sifrele_json(VERI, AAD); assert z["kek_id"] == "k0"
    k1 = kasa.anahtar_uret(); monkeypatch.setenv("PVQ_KEK", k1); monkeypatch.setenv("PVQ_KEK_ID", "k1"); monkeypatch.setenv("PVQ_KEK_ESKI", f"k0={k0}")
    assert kasa.kek_durum() == {"var": True, "id": "k1", "eski": ["k0"]}
    assert kasa.coz_json(z, AAD) == VERI   # eski KEK yalnız çözer
    y = kasa.yeniden_sar(z); assert y["kek_id"] == "k1" and y["dek_sarili"] != z["dek_sarili"]
    z2 = {**z, **y}
    monkeypatch.delenv("PVQ_KEK_ESKI")
    assert kasa.coz_json(z2, AAD) == VERI and kasa.yeniden_sar(z2) is None
    with pytest.raises(kasa.KasaHata, match="ortamda yok"):
        kasa.coz_json(z, AAD)   # eski KEK kaldırıldı, eski zarf çözülmez
