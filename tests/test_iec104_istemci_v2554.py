"""v2.554 (Aşama 2, S4): IEC 104 salt-okur veri istemcisi — sahte istasyon (STARTDT con, GI con, M_ME_NC_1 / M_IT_NA_1 / M_SP_NA_1 / zaman etiketli,
GI sonlanma, TESTFR), ASDU çözücü, kalite bitleri, nokta tablosu eşlemesi, sınama/örnekleme kapıları. Giden yönde yalnız 100 (ve 101). Gerçek RTU yok."""
from __future__ import annotations

import socket
import struct
import threading
from datetime import datetime, timezone

import pytest

from pvquant.io.canli import iec104_istemci as ic
from pvquant.services import canli_alim_service as ca
from pvquant.services import canli_ornekleme_service as co
from pvquant.services import iec104_nokta_service as nk
from pvquant.services import veri_yolu_service as vy

P = ic.Parametreler()


def _asdu(tip, cot, ca, nesneler, sq=False, pn=False):
    vsq = (0x80 if sq else 0) | len(nesneler)
    b = bytes([tip, vsq, cot | (0x40 if pn else 0), 0]) + struct.pack("<H", ca)
    if sq:
        b += nesneler[0][0].to_bytes(3, "little")
        for _, govde in nesneler:
            b += govde
    else:
        for ioa, govde in nesneler:
            b += ioa.to_bytes(3, "little") + govde
    return b


def _cp56(dt):
    return struct.pack("<H", dt.second * 1000 + dt.microsecond // 1000) + bytes([dt.minute, dt.hour, dt.day, dt.month, dt.year - 2000])


def _sahte_istasyon(senaryo="tam", gelen=None):
    """Tek bağlantı kabul eden sahte IEC 104 slave. gelen: istemcinin gönderdiği ASDU tiplerini toplar."""
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
    gelen = gelen if gelen is not None else []
    def apdu(c):
        bas = c.recv(2)
        if not bas: return None
        return bas + c.recv(bas[1])
    def kos():
        c, _ = srv.accept(); c.settimeout(5.0); nr = 0
        try:
            a = apdu(c)
            if a[2] != 0x07: return
            if senaryo == "startdt_yok":
                c.sendall(ic.u_cerceve(0x43)); return   # yanlış U-çerçevesi
            c.sendall(ic.STARTDT_CON)
            a = apdu(c)   # I-çerçevesi GI act
            if a[2] & 1 == 0:
                gelen.append(a[6]); nr += 1
            ns = 0
            def i_gonder(asdu):
                nonlocal ns
                c.sendall(ic.i_cerceve(ns, nr, asdu)); ns += 1
            i_gonder(_asdu(100, 7, 1, [(0, bytes([20]))]))                                   # GI con
            i_gonder(_asdu(13, 20, 1, [(1001, struct.pack("<f", 987.6) + bytes([0])), (1002, struct.pack("<f", 12.5) + bytes([0x80]))]))   # kW; ikincisi IV
            i_gonder(_asdu(15, 20, 1, [(2001, struct.pack("<i", 123456) + bytes([0x05]))]))   # sayaç kWh, sıra 5
            i_gonder(_asdu(1, 20, 1, [(3001, bytes([0x01])), (3002, bytes([0x00]))]))        # tek konum
            t = datetime(2026, 11, 9, 7, 30, 15, tzinfo=timezone.utc)
            i_gonder(_asdu(36, 3, 1, [(1003, struct.pack("<f", 50.02) + bytes([0x20]) + _cp56(t))]))   # Hz, SB ikame, zaman etiketli
            i_gonder(_asdu(11, 20, 1, [(1004, struct.pack("<h", 250) + bytes([0]))] * 1 + [(1005, struct.pack("<h", 251) + bytes([0]))], sq=True))   # SQ=1: 1004, 1005
            i_gonder(_asdu(9, 20, 1, [(1006, struct.pack("<h", 16384) + bytes([0]))]))      # normalize 0,5
            i_gonder(_asdu(199, 20, 1, [(9, bytes([0]))]))                                    # bilinmeyen tip
            c.sendall(ic.TESTFR_ACT)                                                          # istemci con dönmeli
            a = apdu(c)                                                                       # TESTFR con ya da S
            if senaryo == "sonlanma_yok":
                return
            i_gonder(_asdu(100, 10, 1, [(0, bytes([20]))]))                                   # GI act term
            while True:
                a = apdu(c)
                if a is None: break
                if a[2] == 0x13: c.sendall(ic.STOPDT_CON); break
        except OSError:
            pass
        finally:
            c.close(); srv.close()
    threading.Thread(target=kos, daemon=True).start()
    return port, gelen


def test_cerceveler_ve_asdu_cozucu():
    assert ic.STARTDT_ACT == bytes.fromhex("680407000000") and ic.STARTDT_CON == bytes.fromhex("68040b000000") and ic.s_cerceve(3) == bytes.fromhex("680401000600")
    gi = ic.asdu_genel_sorgulama(7, P)
    assert gi == bytes([100, 1, 6, 0, 7, 0, 0, 0, 0, 20])
    with pytest.raises(ic.Iec104Hata):
        ic.asdu_genel_sorgulama(7, P, tip=45)   # komut tipi gönderilemez
    a = ic.asdu_coz(_asdu(13, 20, 5, [(1001, struct.pack("<f", 1.5) + bytes([0x80 | 0x20]))]), P)
    assert a["tip"] == 13 and a["ca"] == 5 and a["cot"] == 20 and a["nesneler"][0]["ioa"] == 1001 and a["nesneler"][0]["deger"] == pytest.approx(1.5)
    assert a["nesneler"][0]["kalite"] == {"iv": True, "nt": False, "sb": True, "bl": False, "ov": False}
    t = datetime(2026, 11, 9, 7, 30, 15, 250000, tzinfo=timezone.utc)
    z = ic.asdu_coz(_asdu(34, 3, 1, [(7, struct.pack("<h", -16384) + bytes([0]) + _cp56(t))]), P)["nesneler"][0]
    assert z["deger"] == pytest.approx(-0.5) and z["zaman"] == t and z["zaman_kaynagi"] == "cihaz"
    sq = ic.asdu_coz(_asdu(1, 20, 1, [(10, bytes([1])), (11, bytes([0])), (12, bytes([0x81]))], sq=True), P)
    assert [n["ioa"] for n in sq["nesneler"]] == [10, 11, 12] and sq["nesneler"][2]["kalite"]["iv"] and sq["nesneler"][2]["deger"] == 1
    assert ic.asdu_coz(_asdu(199, 20, 1, [(9, bytes([0]))]), P)["bilinmeyen"] is True
    with pytest.raises(ValueError):
        ic.Parametreler.ayardan({"w": 20, "k": 12})


def test_genel_sorgulama_sahte_istasyon():
    port, gelen = _sahte_istasyon()
    r = ic.genel_sorgulama("127.0.0.1", port, 1, P, azami_sure=8.0)
    assert r["sonlandi"] is True and gelen == [100] and r["gonderilen_tipler"] == [100]   # giden yönde yalnız tip 100
    ioa = {n["ioa"]: n for n in r["noktalar"]}
    assert ioa[1001]["deger"] == pytest.approx(987.6) and ioa[1002]["kalite"]["iv"] is True and ioa[2001]["deger"] == 123456.0 and ioa[3001]["deger"] == 1
    assert ioa[1003]["kalite"]["sb"] is True and ioa[1003]["zaman"].startswith("2026-11-09T07:30:15") and ioa[1004]["deger"] == 250.0 and ioa[1005]["deger"] == 251.0 and ioa[1006]["deger"] == pytest.approx(0.5)
    assert r["bilinmeyen"] == 1 and 10 in r["cot_akisi"]
    port2, _ = _sahte_istasyon("startdt_yok")
    with pytest.raises(ic.Iec104Hata) as e:
        ic.genel_sorgulama("127.0.0.1", port2, 1, P)
    assert e.value.kod == "protokol_yaniti_yok"


def test_nokta_tablosu_csv_dogrulama_ve_esleme():
    tablo = nk.csv_den("ioa;alan;carpan;ad\n1001;guc_w;1000;Santral aktif güç kW\n2001;enerji_wh;1000;Toplam üretim kWh\n1003;frekans_hz;1;Hz\n1002;dc_guc_w;1000;DC kW\n")
    assert [t["ioa"] for t in tablo] == [1001, 2001, 1003, 1002] and tablo[0]["carpan"] == 1000.0
    with pytest.raises(ValueError, match="tekrar"):
        nk.dogrula([{"ioa": 1, "alan": "guc_w"}, {"ioa": 1, "alan": "enerji_wh"}])
    with pytest.raises(ValueError, match="alan"):
        nk.dogrula([{"ioa": 1, "alan": "voltaj"}])
    with pytest.raises(ValueError, match="başlığında"):
        nk.csv_den("a,b\n1,2\n")
    port, _ = _sahte_istasyon()
    r = ic.genel_sorgulama("127.0.0.1", port, 1, P, azami_sure=8.0)
    e = nk.esle(r["noktalar"], tablo)
    assert e["olcum"]["guc_w"] == pytest.approx(987_600.0) and e["olcum"]["enerji_wh"] == pytest.approx(123_456_000.0) and e["olcum"]["frekans_hz"] == pytest.approx(50.02)
    assert e["olcum"]["dc_guc_w"] is None and e["eksik"][0] == {"ioa": 1002, "alan": "dc_guc_w", "neden": "geçersiz"}   # IV → eksik
    assert e["eslesen"] == 3 and e["ikame"] == 1 and e["gelmeyen_ioa"] == [] and e["nokta_sayisi"] == 9


def test_sina_iec104_gi_kipi_ve_ornekleme_kapisi():
    tablo = [{"ioa": 1001, "alan": "guc_w", "carpan": 1000}, {"ioa": 2001, "alan": "enerji_wh", "carpan": 1000}, {"ioa": 5555, "alan": "durum_kodu", "carpan": 1}]
    port, _ = _sahte_istasyon()
    r = ca.sina_iec104({"host": "10.0.0.9", "port": port}, onay=True, startdt_onayi=True, nokta_tablosu=tablo, iec104_ayar={"ca": 1},   # adres bekçisi loopback'i reddeder; sorgula enjekte
                       sorgula=lambda h, p, cax, prm, sure: ic.genel_sorgulama("127.0.0.1", port, cax, prm, 8.0))
    assert r["durum"] == "ok" and r["ozet"]["yontem"] == "gi" and r["ozet"]["guc_kw"] == pytest.approx(987.6) and r["ozet"]["enerji_mwh"] == pytest.approx(123.456)
    assert r["ozet"]["eslesen"] == 2 and r["ozet"]["gelmeyen_ioa"] == [5555] and r["ozet"]["gonderilen_tipler"] == [100] and "başka hiçbir komut" in r["not"]
    # STARTDT onayı yoksa nokta tablosu olsa da yalnız TCP
    t = ca.sina_iec104({"host": "10.0.0.9"}, onay=True, nokta_tablosu=tablo, ulas=lambda h, p, za, st: {"tcp": True, "startdt_con": None, "startdt_gonderildi": False})
    assert t["ozet"]["yontem"] == "tcp"
    # tablo eşleşmezse kismi
    k = ca.sina_iec104({"host": "10.0.0.9"}, onay=True, startdt_onayi=True, nokta_tablosu=[{"ioa": 9, "alan": "guc_w"}], iec104_ayar={"ca": 1},
                       sorgula=lambda *a: {"noktalar": [{"ioa": 1, "tip": 13, "deger": 1.0, "kalite": {}}], "sonlandi": True, "bilinmeyen": 0, "gonderilen_tipler": [100]})
    assert k["durum"] == "kismi" and "eşleşmedi" in k["aciklama"]
    # beyan: IEC 104 ayarları ve çekiş şartı
    b = vy.dogrula({"tur": "iec104", "salt_okuma_onayi": True, "startdt_onayi": True, "ornekleme_acik": True, "baglanti": {"host": "10.8.0.5"}, "iec104": {"ca": 3, "parametreler": {"t0": 20}}, "nokta_tablosu": tablo})["veri_yolu"]
    assert b["iec104"]["ca"] == 3 and b["iec104"]["parametreler"]["t0"] == 20.0 and b["iec104"]["parametreler"]["k"] == 12 and b["ornekleme_acik"] is True and len(b["nokta_tablosu"]) == 3
    b2 = vy.dogrula({"tur": "iec104", "salt_okuma_onayi": True, "startdt_onayi": False, "ornekleme_acik": True, "baglanti": {"host": "10.8.0.5"}, "nokta_tablosu": tablo})["veri_yolu"]
    assert b2["ornekleme_acik"] is False                                                                # STARTDT onayı yok → çekiş açılmaz
    with pytest.raises(ValueError, match="CA"):
        vy.dogrula({"tur": "iec104", "salt_okuma_onayi": True, "baglanti": {"host": "10.8.0.5"}, "iec104": {"ca": 70000}})
    a = vy.asamalar({**b, "beyan_zamani": "t", "son_sinama": {"durum": "ok", "zaman": "z", "ozet": {"yontem": "gi", "eslesen": 2}}}, [])
    assert [x["kod"] for x in a] == ["secildi", "ayar", "sinama", "nokta", "cekis", "akis"] and "2 alan" in a[2]["etiket"] and a[3]["tamam"] and a[4]["tamam"]
    # örnek: GI → ölçüm → canlı örnek (cihaz 'scada', sınır santral toplamı)
    plant = {"id": "p", "tenant_id": "t", "params_json": {"veri_yolu": b}}
    assert co.uygun(plant)[0]
    o = co.ornek_al_iec104(b, datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc), sorgula=lambda h, p, cax, prm, sure: ic.genel_sorgulama("127.0.0.1", _sahte_istasyon()[0], cax, prm, 8.0))
    assert o["cihaz_id"] == "scada" and o["sinir"] == "plant_gross_ac" and o["profil"] == "iec104" and o["guc_w"] == pytest.approx(987_600.0) and o["enerji_wh"] == pytest.approx(123_456_000.0)
    assert not co.uygun({"id": "p", "tenant_id": "t", "params_json": {"veri_yolu": {**b, "nokta_tablosu": None}}})[0]
