"""v2.570 (Faz 0 onay paketi 2) — sır kasası sarmalayıcısı ve TOTP tekrar koruması (saf)."""
from __future__ import annotations

import pyotp
import pytest

from pvquant.guvenlik import kasa, sir


def _temiz(monkeypatch):
    for k in ("PVQ_KEK", "PVQ_KEK_ID", "PVQ_KEK_ESKI"):
        monkeypatch.delenv(k, raising=False)


def test_zarf_gidis_donus_ve_baglam(monkeypatch):
    _temiz(monkeypatch); monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret())
    z, duz = sir.sakla("JBSWY3DPEHPK3PXP", "users:u1:totp")
    assert duz is None and z and set(z) == {"kek_id", "dek_sarili", "sifreli", "surum"} and z["kek_id"] == "k1"
    assert "JBSWY3DPEHPK3PXP" not in str(z)
    assert sir.oku(z, None, "users:u1:totp") == "JBSWY3DPEHPK3PXP"
    with pytest.raises(kasa.KasaHata):        # başka kullanıcıya taşınamaz
        sir.oku(z, None, "users:u2:totp")


def test_kek_yokken_duz_metin_ve_cift_okuma(monkeypatch):
    _temiz(monkeypatch)
    z, duz = sir.sakla("JBSWY3DPEHPK3PXP", "users:u1:totp")
    assert z is None and duz == "JBSWY3DPEHPK3PXP"
    assert sir.oku(None, "JBSWY3DPEHPK3PXP", "users:u1:totp") == "JBSWY3DPEHPK3PXP"   # geçiş dönemi: düz sütun okunur
    assert sir.oku(None, None, "x") is None and sir.sakla("", "x") == (None, None)


def test_totp_tekrar_reddi_ve_pencere():
    s = pyotp.random_base32(); t = 1_800_000_000.0; adim = int(t // 30)
    kod = pyotp.TOTP(s).at(int(t))
    ok, a = sir.totp_dogrula(s, kod, None, simdi=t)
    assert ok and a == adim
    assert sir.totp_dogrula(s, kod, a, simdi=t) == (False, None)            # aynı kod ikinci kez: tekrar
    assert sir.totp_dogrula(s, kod, a, simdi=t + 29) == (False, None)       # pencere içinde de tekrar
    sonraki = pyotp.TOTP(s).at(int(t) + 30)
    ok2, a2 = sir.totp_dogrula(s, sonraki, a, simdi=t + 30)
    assert ok2 and a2 == adim + 1
    onceki = pyotp.TOTP(s).at(int(t) - 30)
    assert sir.totp_dogrula(s, onceki, None, simdi=t)[0]                    # ±1 pencere eski davranışla aynı
    assert sir.totp_dogrula(s, "000000", None, simdi=t) == (False, None)
    assert sir.totp_dogrula(s, "12 34 56", None, simdi=t) == (False, None) and sir.totp_dogrula(None, kod, None, simdi=t) == (False, None)
    assert sir.totp_dogrula(s, kod.replace(kod[0], kod[0] + " ", 1), None, simdi=t)[0]   # boşluk temizlenir


def test_servisler_tek_yardimciyi_kullanir():
    import inspect
    from pvquant.services import iki_adim_service, platform_service, webhook_service
    for m in (iki_adim_service, platform_service):
        kaynak = inspect.getsource(m)
        import re
        assert not re.search(r"TOTP\([^)]*\)\.verify\(", kaynak), m.__name__   # eski pyotp doğrulaması kodda kalmadı
        assert "_sir.totp_dogrula" in kaynak and "_sir.sakla" in kaynak and "_sir.oku" in kaynak
    k = inspect.getsource(webhook_service)
    assert "_sir.sakla(secret" in k and "_sir.oku(getattr(r, \"secret_zarf\"" in k
