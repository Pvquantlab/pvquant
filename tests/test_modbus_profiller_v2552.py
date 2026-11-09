"""v2.552 (Aşama 2, S2): üretici Modbus profilleri — Huawei SmartLogger (FC3, santral toplamı, big-endian), Sungrow dizi (FC4, adres−1, U32 küçük uçlu,
0xFFFF geçersiz), Growatt (FC4, 0,1 W / 0,1 kWh). Değerler üretici belgelerinden (K380/K381/K382 yerel kopyaları); gerçek cihaz yok."""
from __future__ import annotations

import struct

import pytest

from pvquant.io.canli import profiller as pf
from pvquant.io.canli.modbus_tcp import ModbusTcpIstemci
from pvquant.services import canli_alim_service as ca
from pvquant.services import canli_ornekleme_service as co
from pvquant.services import veri_yolu_service as vy


class SahteIstemci:
    """adres → register listesi; FC3 ve FC4 ayrı tablolar."""
    def __init__(self, h3=None, h4=None): self.h3, self.h4, self.istekler = h3 or {}, h4 or {}, []
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def _oku(self, tablo, adres, adet, fonk):
        self.istekler.append((fonk, adres, adet))
        return [tablo.get(adres + i, 0) for i in range(adet)]
    def oku(self, adres, adet): return self._oku(self.h3, adres, adet, 3)
    def oku_giris(self, adres, adet): return self._oku(self.h4, adres, adet, 4)


def _u32(v, little=False):
    hi, lo = (v >> 16) & 0xFFFF, v & 0xFFFF
    return (lo, hi) if little else (hi, lo)


def test_huawei_smartlogger_santral_toplami():
    h3 = {}
    h3[40525], h3[40526] = _u32((-0) & 0xFFFFFFFF)   # active power 0 W
    h3[40525], h3[40526] = _u32(1_234_567)             # 1.234.567 W (I32, gain 1000 → W)
    h3[40521], h3[40522] = _u32(1_300_000)             # input power W
    h3[40560], h3[40561] = _u32(98_765_4)              # E-Total 98765,4 kWh (gain 10)
    h3[40562], h3[40563] = _u32(1_234)                 # E-Daily 123,4 kWh
    h3[40543] = 2                                      # limited power operation
    c = pf.oku_cihaz_profil(SahteIstemci(h3=h3), "huawei_smartlogger")
    inv = c["inverter"]
    assert inv["guc_w"] == pytest.approx(1_234_567.0) and inv["dc_guc_w"] == pytest.approx(1_300_000.0)
    assert inv["enerji_wh"] == pytest.approx(98_765_400.0) and inv["gunluk_wh"] == pytest.approx(123_400.0)
    assert inv["durum_kodu"] == 5 and inv["durum"] == "kısıtlı" and inv["uretici_durum"] == "üretimde (sınırlı)"
    assert c["sinir"] == "plant_gross_ac" and c["cihaz_turu"] == "santral" and c["enerji_yolu"] == "profil" and c["ortak"]["uretici"] == "Huawei"
    # negatif aktif güç (I32) işaretli çözülür
    h3[40525], h3[40526] = _u32((-500) & 0xFFFFFFFF)
    assert pf.oku_cihaz_profil(SahteIstemci(h3=h3), "huawei_smartlogger")["inverter"]["guc_w"] == -500.0


def test_sungrow_fc4_adres_tabani_kucuk_uclu_ve_gecersiz():
    h4 = {}
    h4[5030], h4[5031] = _u32(98_760, little=True)     # 5031–5032 total active power W (belge adresi −1; düşük kelime önce)
    h4[5003], h4[5004] = _u32(12_345, little=True)     # 5004–5005 total yields kWh
    h4[5002] = 123                                     # 5003 daily 12,3 kWh
    h4[5016], h4[5017] = _u32(101_000, little=True)    # 5017 total DC W
    h4[5035] = 500                                     # 5036 50,0 Hz
    h4[5037] = 0x8100                                  # 5038 derating run
    h4[5000] = 1000                                    # 5001 nominal 100,0 kW
    for i, ch in enumerate(struct.unpack(">5H", b"A2301234PX")):
        h4[4989 + i] = ch                               # 4990–4999 SN
    ist = SahteIstemci(h4=h4)
    c = pf.oku_cihaz_profil(ist, "sungrow_string")
    inv = c["inverter"]
    assert all(f == 4 for f, _, _ in ist.istekler) and (4, 5030, 2) in ist.istekler   # yalnız FC4, protokol adresi 5030
    assert inv["guc_w"] == pytest.approx(98_760.0) and inv["enerji_wh"] == pytest.approx(12_345_000.0) and inv["gunluk_wh"] == pytest.approx(12_300.0)
    assert inv["dc_guc_w"] == pytest.approx(101_000.0) and inv["frekans_hz"] == pytest.approx(50.0) and c["kapasite"]["anma_guc_w"] == pytest.approx(100_000.0)
    assert inv["durum_kodu"] == 5 and inv["uretici_durum"] == "üretimde (kısıtlı)" and c["ortak"]["seri_no"] == "A2301234PX" and c["sinir"] == "inverter_ac"
    h4[5035] = 0xFFFF; h4[5037] = 0x5500
    c2 = pf.oku_cihaz_profil(SahteIstemci(h4=h4), "sungrow_string")
    assert c2["inverter"]["frekans_hz"] is None and "frekans_hz" in c2["inverter"]["uygulanmayan"] and c2["inverter"]["durum"] == "arıza"
    # büyük uçlu okunsaydı değer yanlış olurdu — profil küçük uçlu
    assert pf._coz([h4[5030], h4[5031]], "u32", "big", {}) != 98_760


def test_growatt_fc4_carpanlar_ve_durum():
    h4 = {0: 1}
    h4[35], h4[36] = _u32(987_600)      # Pac 0,1 W → 98.760 W
    h4[1], h4[2] = _u32(1_010_000)      # Ppv 0,1 W
    h4[37] = 4998                        # 49,98 Hz
    h4[53], h4[54] = _u32(1234)          # Eac today 123,4 kWh
    h4[55], h4[56] = _u32(5_678_901)     # Eac total 567.890,1 kWh
    c = pf.oku_cihaz_profil(SahteIstemci(h4=h4), "growatt_rtu")
    inv = c["inverter"]
    assert inv["guc_w"] == pytest.approx(98_760.0) and inv["dc_guc_w"] == pytest.approx(101_000.0) and inv["frekans_hz"] == pytest.approx(49.98)
    assert inv["gunluk_wh"] == pytest.approx(123_400.0) and inv["enerji_wh"] == pytest.approx(567_890_100.0) and inv["durum_kodu"] == 4 and inv["uretici_durum"] == "üretimde"
    assert pf.oku_cihaz_profil(SahteIstemci(h4={**h4, 0: 3}), "growatt_rtu")["inverter"]["durum"] == "arıza"


def test_profil_dogrulama_sinama_ve_ornek():
    with pytest.raises(ValueError, match="kayıt haritası"):
        ca.hedef_dogrula("10.0.0.5", 502, 0, None, "bilinmeyen")
    h = ca.hedef_dogrula("10.0.0.5", 502, 0, None, "huawei_smartlogger")
    assert h["profil"] == "huawei_smartlogger" and "profil" not in ca.hedef_dogrula("10.0.0.5", 502, 1, None, "sunspec")
    h3 = {}; h3[40525], h3[40526] = _u32(500_000); h3[40560], h3[40561] = _u32(10_000); h3[40543] = 1
    class Fab:
        def __init__(self, host, port, birim, za): self.i = SahteIstemci(h3=h3)
        def __enter__(self): return self.i
        def __exit__(self, *a): return False
    r = ca.sina({"host": "10.0.0.5", "birim": 0, "profil": "huawei_smartlogger"}, onay=True, istemci_fabrikasi=Fab)
    assert r["durum"] == "ok" and r["ozet"]["guc_kw"] == pytest.approx(500.0) and r["ozet"]["profil"] == "huawei_smartlogger" and r["ozet"]["sinir"] == "plant_gross_ac" and r["ozet"]["uretici"] == "Huawei"
    o = co.ornek_al({"host": "10.0.0.5", "birim": 0, "profil": "huawei_smartlogger"}, istemci_fabrikasi=Fab)
    assert o["cihaz_id"] == "santral" and o["sinir"] == "plant_gross_ac" and o["profil"] == "huawei_smartlogger" and o["guc_w"] == 500_000.0
    # beyan: yalnız Modbus hedefinde profil taşınır; liste ozet'e girer
    b = vy.dogrula({"tur": "modbus_sunspec", "salt_okuma_onayi": True, "baglanti": {"host": "10.8.0.12", "birim": 0, "profil": "sungrow_string"}})["veri_yolu"]
    assert b["baglanti"]["profil"] == "sungrow_string"
    assert {p["kod"] for p in pf.liste()} == {"sunspec", "huawei_smartlogger", "sungrow_string", "growatt_rtu"} and all(p["dogrulama"] for p in pf.liste())


def test_modbus_istemci_fc4_cercevesi():
    import socket, threading
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
    gelen = {}
    def kos():
        c, _ = srv.accept()
        try:
            istek = c.recv(12); gelen["fonk"] = istek[7]
            c.sendall(istek[0:2] + struct.pack(">HHB", 0, 5, 1) + bytes([0x04, 2]) + struct.pack(">H", 777))
            c.settimeout(1.0)
            try: c.recv(12)
            except OSError: pass
        finally:
            c.close(); srv.close()
    threading.Thread(target=kos, daemon=True).start()
    with ModbusTcpIstemci("127.0.0.1", port, 1, 2.0) as c:
        assert c.oku_giris(5030, 1) == [777]
    assert gelen["fonk"] == 0x04
