"""08.11.2026 v2.545 (P4b ilk bağlayıcı): Modbus TCP istemcisi (FC3), SunSpec keşif/ortak model/inverter modeli, bağlantı sınaması (onay, adres kuralı)."""
import socket
import struct
import threading

import pytest

from pvquant.io.canli import sunspec
from pvquant.io.canli.modbus_tcp import ModbusHata, ModbusTcpIstemci
from pvquant.services import canli_alim_service as ca


def _metin_regs(s: str, n: int) -> list[int]:
    b = s.encode("ascii").ljust(2 * n, b"\x00")
    return list(struct.unpack(f">{n}H", b))


def _kayit_haritasi() -> dict[int, int]:
    """40000: SunS; model 1 (66); model 103 (50); son 0xFFFF."""
    regs: list[int] = [0x5375, 0x6E53]                                   # "SunS"
    regs += [1, 66] + _metin_regs("Ornek Uretici", 16) + _metin_regs("INV-100K", 16) + _metin_regs("", 8) + _metin_regs("1.2.3", 8) + _metin_regs("SN-0001", 16) + [1, 0x8000]
    # model 103: A, AphA, AphB, AphC, A_SF, PPVphAB, BC, CA, PhVphA, B, C, V_SF, W, W_SF, Hz, Hz_SF, VA, VA_SF, VAr, VAr_SF, PF, PF_SF,
    #            WH(2), WH_SF, DCA, DCA_SF, DCV, DCV_SF, DCW, DCW_SF, TmpCab, TmpSnk, TmpTrns, TmpOt, Tmp_SF, St, StVnd, Evt1(2) ... (50 kayıt)
    m103 = [1500, 500, 500, 500, 0xFFFF & -1 & 0xFFFF][:4] + [0x10000 - 1]        # A=150,0 A (SF -1)
    m103 = [1500, 500, 500, 500, 0xFFFF]                                    # A_SF = -1 (0xFFFF)
    m103 += [4000, 4000, 4000, 2310, 2310, 2310, 0xFFFF]                   # gerilimler ×0,1
    m103 += [9876, 1]                                                       # W = 98.760 W (SF +1)
    m103 += [4999, 0xFFFE]                                                  # Hz = 49,99 (SF -2)
    m103 += [9900, 1, 100, 1, 0x10000 - 990, 0xFFFE]                        # VA, VAr, PF = -0,990? → PF -9,90?: PF 990 × 10^-2 → 9,90? (ölçek -3 daha doğru) → düzelt
    m103[-1] = 0xFFFD                                                       # PF_SF = -3 → 0,990 (negatif işaret test için)
    wh = 123_456_789
    m103 += [(wh >> 16) & 0xFFFF, wh & 0xFFFF, 0]                           # WH 123.456.789 Wh
    m103 += [2000, 0xFFFF, 8500, 0xFFFF, 10100, 1]                          # DC: 200,0 A; 850,0 V; 101.000 W
    m103 += [452, 0x8000, 0x8000, 0x8000, 0xFFFF]                           # TmpCab 45,2 °C (SF -1); diğer sıcaklıklar yok
    m103 += [4, 0xFFFF]                                                     # St = 4 MPPT
    m103 += [0, 1 << 7]                                                     # Evt1: bit 7 aşırı sıcaklık
    m103 += [0] * (50 - len(m103))
    regs += [103, 50] + m103
    regs += [0xFFFF, 0]
    regs += [0] * 30                                                        # zincir sonrası dolgu: parçalı okuma testi (125 + 5)
    return {40000 + i: v for i, v in enumerate(regs)}


HARITA = _kayit_haritasi()


class SahteModbusSunucu(threading.Thread):
    """Tek bağlantılık FC3 sunucusu; HARITA dışı adreste istisna 2 döner."""
    def __init__(self):
        super().__init__(daemon=True)
        self.s = socket.socket(); self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); self.s.bind(("127.0.0.1", 0)); self.s.listen(1)
        self.port = self.s.getsockname()[1]; self.istek = 0

    def run(self):
        c, _ = self.s.accept()
        with c:
            while True:
                bas = c.recv(7)
                if len(bas) < 7:
                    return
                islem, proto, uz, birim = struct.unpack(">HHHB", bas)
                pdu = c.recv(uz - 1); fonk, adres, adet = struct.unpack(">BHH", pdu[:5]); self.istek += 1
                if fonk != 3:
                    govde = struct.pack(">BB", fonk | 0x80, 1)
                elif any(a not in HARITA for a in range(adres, adres + adet)):
                    govde = struct.pack(">BB", 0x83, 2)
                else:
                    govde = struct.pack(">BB", 3, 2 * adet) + struct.pack(f">{adet}H", *[HARITA[a] for a in range(adres, adres + adet)])
                c.sendall(struct.pack(">HHHB", islem, 0, len(govde) + 1, birim) + govde)


def test_modbus_istemci_okur_ve_istisnayi_bildirir():
    srv = SahteModbusSunucu(); srv.start()
    with ModbusTcpIstemci("127.0.0.1", srv.port, 1, 3.0) as c:
        assert c.oku(40000, 2) == [0x5375, 0x6E53]
        assert len(c.oku(40000, 130)) == 130 and srv.istek == 3          # 125 + 5 parçalı
        with pytest.raises(ModbusHata, match="istisnası 2"):
            c.oku(60000, 1)


def test_sunspec_kesif_ortak_ve_inverter():
    oku = lambda a, n: [HARITA[x] for x in range(a, a + n)]
    temel, modeller = sunspec.kesfet(oku)
    assert temel == 40000 and [m[0] for m in modeller] == [1, 103]
    cihaz = sunspec.oku_cihaz(oku)
    assert cihaz["ortak"]["uretici"] == "Ornek Uretici" and cihaz["ortak"]["model"] == "INV-100K" and cihaz["ortak"]["seri_no"] == "SN-0001"
    inv = cihaz["inverter"]
    assert inv["faz"] == "üç faz" and inv["akim_a"] == pytest.approx(150.0) and inv["gerilim_v"] == pytest.approx(231.0)
    assert inv["guc_w"] == pytest.approx(98760.0) and inv["frekans_hz"] == pytest.approx(49.99) and inv["guc_faktoru"] == pytest.approx(-0.990)
    assert inv["enerji_wh"] == pytest.approx(123_456_789.0) and inv["dc_guc_w"] == pytest.approx(101000.0) and inv["kabin_sicaklik_c"] == pytest.approx(45.2)
    assert inv["sogutucu_sicaklik_c"] is None and inv["durum"] == "üretimde (MPPT)" and inv["olaylar"] == ["aşırı sıcaklık"]
    bos = lambda a, n: [0] * n
    with pytest.raises(ValueError, match="SunS"):
        sunspec.kesfet(bos)


def test_sinama_onay_adres_ve_basari():
    assert ca.sina({"host": "10.0.0.5"}, onay=False)["durum"] == "onay_yok"
    assert ca.sina({"host": "127.0.0.1"}, onay=True)["durum"] == "adres_reddedildi"
    assert ca.sina({"host": "169.254.169.254"}, onay=True)["durum"] == "adres_reddedildi"
    assert ca.sina({"host": "", "port": 502}, onay=True)["durum"] == "ayar_hatasi"
    assert ca.sina({"host": "10.0.0.5", "port": 70000}, onay=True)["durum"] == "ayar_hatasi"
    assert ca.adres_izinli("10.8.0.12") == (True, "özel ağ (VPN) adresi") and ca.adres_izinli("8.8.8.8")[0] is True

    class Sahte:
        def __init__(self, host, port, birim, za): self.args = (host, port, birim)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def oku(self, a, n): return [HARITA[x] for x in range(a, a + n)]
    r = ca.sina({"host": "10.0.0.5", "port": "502", "birim": "3"}, onay=True, istemci_fabrikasi=Sahte)
    assert r["durum"] == "ok" and r["hedef"]["birim"] == 3 and r["ozet"]["uretici"] == "Ornek Uretici" and r["ozet"]["guc_kw"] == pytest.approx(98.76)
    assert r["ozet"]["enerji_mwh"] == pytest.approx(123.457, abs=1e-3) and r["ozet"]["durum"] == "üretimde (MPPT)" and "yazılmadı" in r["not"]

    class Kopuk(Sahte):
        def __enter__(self): raise OSError("bağlantı reddedildi")
    assert ca.sina({"host": "10.0.0.5"}, onay=True, istemci_fabrikasi=Kopuk)["durum"] == "baglanti_hatasi"


PLANT = "22222222-2222-2222-2222-222222222222"


def test_sinama_kapisi(monkeypatch):
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    durum = {"pj": {"segment": "lisansli_serbest"}}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "params_json": dict(durum["pj"])})
    def _birlestir(t, p, **an):
        durum["pj"] = {**durum["pj"], **an}; return durum["pj"]
    monkeypatch.setattr(plant_service, "params_birlestir", _birlestir)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(ca, "sina", lambda ayar, onay, istemci_fabrikasi=None: {"durum": "ok" if onay else "onay_yok", "zaman": "z", "hedef": ayar, "ozet": {"uretici": "X"}})
    from pvquant.services import veri_yolu_service as vy
    monkeypatch.setattr(vy, "etkin_yollar", lambda t, p, simdi=None: [])
    for r in api_main.app.routes:
        if getattr(r, "path", "") in ("/v1/plants/{plant_id}/veri-yolu", "/v1/plants/{plant_id}/veri-yolu/sinama") and ({"PUT", "POST"} & getattr(r, "methods", set())):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    c = TestClient(api_main.app)
    try:
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").status_code == 422                      # hedef yok
        r = c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "modbus_sunspec", "salt_okuma_onayi": False, "baglanti": {"host": "10.8.0.12", "port": "502", "birim": "1"}})
        assert r.status_code == 200 and r.json()["beyan"]["baglanti"] == {"host": "10.8.0.12", "port": 502, "birim": 1}
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").json()["durum"] == "onay_yok"
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "modbus_sunspec", "salt_okuma_onayi": True, "baglanti": {"host": "10.8.0.12"}})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").json()["durum"] == "ok"
        g = c.get(f"/v1/plants/{PLANT}/veri-yolu").json()   # 08.11 inceleme (faz 4): sınama sonucu beyana yazılır, aşama 3 «başarılı», aşama 4 (veri akışı) hâlâ değil
        assert g["beyan"]["son_sinama"]["durum"] == "ok" and [x["tamam"] for x in g["asamalar"]] == [True, True, True, False]
        assert c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "modbus_sunspec", "baglanti": {"host": "10.8.0.12", "port": 99999}}).status_code == 422
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "inverter_bulut_api"})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").status_code == 422                      # Modbus değil
    finally:
        api_main.app.dependency_overrides.clear()
