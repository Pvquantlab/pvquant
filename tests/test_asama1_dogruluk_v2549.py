"""v2.549–v2.550 (Aşama 1, D1–D6): veri doğruluğu çekirdeği — Codex (Faz 2/3) sentetik kayıtları ve 29 sözleşme vektöründen PVQuant'a uyarlanan kabul
vektörleri. Dış sisteme dokunulmaz: Modbus çerçeveleri bellek içi, DB yok.
D1 saat sınırı (07a: 100 kW, 00:00–00:45 → 75 kWh kısmi; kapanışla 100 tam; interpolasyon), D2 tipli sentinel (OFF01–OFF05), D3 MBAP unit/uzunluk
(OFF06–OFF08), D4/D5 kaynak seçimi ve revizyon (SAF), D6 negatif kırpmada ham korunur."""
from __future__ import annotations

import socket
import struct
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from pvquant.io.canli import sunspec as ss
from pvquant.io.canli.modbus_tcp import ModbusHata, ModbusTcpIstemci
from pvquant.services import canli_alim_service as ca
from pvquant.services import canli_ornekleme_service as co
from pvquant.services import kaynak_secim_service as ks

T0 = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)


# ----------------------------------------------------------------------------- D1
def test_d1_saat_siniri_codex_07a_vektoru():
    ts = [T0 + timedelta(minutes=m) for m in (0, 15, 30, 45, 60)]
    df = pd.DataFrame({"ts_utc": ts, "guc_w": [100000] * 5, "enerji_wh": [0, 25000, 50000, 75000, 100000]})
    tam = co.saatlik_ozet(df, T0)
    assert tam["energy_kwh"] == 100.0 and tam["tamlik"] == "measured_complete" and tam["kapsama_dk"] == 60.0 and tam["power_kw"] == 100.0
    kismi = co.saatlik_ozet(df.head(4), T0)                                   # eski kod bunu 75 kWh «valid» tam saat yazıyordu
    assert kismi["energy_kwh"] == 75.0 and kismi["tamlik"] == "measured_partial" and kismi["kapsama_dk"] == 45.0
    # kapanış örneği bir sonraki saatin açılışı: çift sayım yok
    sonraki = pd.DataFrame({"ts_utc": [T0 + timedelta(minutes=m) for m in (60, 75, 90, 105, 120)], "guc_w": [100000] * 5, "enerji_wh": [100000, 125000, 150000, 175000, 200000]})
    assert co.saatlik_ozet(pd.concat([df, sonraki]), T0 + timedelta(hours=1))["energy_kwh"] == 100.0
    assert co.saatlik_ozet(pd.concat([df, sonraki]), T0)["energy_kwh"] == 100.0


def test_d1_sinir_interpolasyonu_ve_zaman_agirlikli_guc():
    # örnekler 5 dk kayık (:03, :18 …): sınır değeri bir periyot içindeki iki örnekten doğrusal taşınır
    ts = [T0 + timedelta(minutes=m) for m in (-12, 3, 18, 33, 48, 63)]
    df = pd.DataFrame({"ts_utc": ts, "guc_w": [100000] * 6, "enerji_wh": [-20000 + 0, 5000, 30000, 55000, 80000, 105000]})
    oz = co.saatlik_ozet(df, T0, periyot=15)
    assert oz["energy_kwh"] == pytest.approx(100.0) and oz["tamlik"] == "measured_complete" and oz["sinir_interpolasyon"] is True
    # komşu örnek bir periyottan uzaksa interpolasyon yok → kısmi
    df2 = df[df["ts_utc"] != T0 + timedelta(minutes=63)]
    assert co.saatlik_ozet(df2, T0, periyot=15)["tamlik"] == "measured_partial"
    # zaman ağırlıklı güç: 0–30 dk 100 kW, 30–60 dk 200 kW → ortalama 150 (aritmetik ortalama 133 değil)
    df3 = pd.DataFrame({"ts_utc": [T0, T0 + timedelta(minutes=30), T0 + timedelta(minutes=31), T0 + timedelta(minutes=60)], "guc_w": [100000, 100000, 200000, 200000], "enerji_wh": [None] * 4})
    oz3 = co.saatlik_ozet(df3, T0)
    assert oz3["power_kw"] == pytest.approx(150.0, rel=0.02) and oz3["nitelik"] == "entegrasyon" and oz3["tamlik"] == "measured_complete"


# ----------------------------------------------------------------------------- D2
def test_d2_tipli_sentinel_codex_off01_05():
    assert ss._i16(0xFFFF) == -1 and ss._i16(0x8000) is None                       # OFF01: int16 0xFFFF geçerli −1
    assert ss._u16(0x8000) == 32768 and ss._u16(0xFFFF) is None                    # OFF02: uint16 0x8000 geçerli
    assert ss._acc32(0xFFFF, 0xFFFF) == 4294967295 and ss._acc32(0, 0) is None      # OFF03/04: acc32 üst sınır geçerli, 0 birikmemiş
    assert ss._f32(0x7F80, 0x0000) is None and ss._f32(0x7FC0, 0) is None and ss._f32(0x42C8, 0) == 100.0   # OFF05: ∞ ve NaN karantina
    assert ss._u64([0xFFFF] * 4) is None and ss._u64([0, 0, 0, 5]) == 5 and ss._sf(0x8000) is None and ss._sf(0xFFFF) == -1 and ss._sf(11) is None
    assert ss._i32(0x8000, 0) is None and ss._i32(0xFFFF, 0xFFFF) == -1 and ss._u32(0xFFFF, 0xFFFF) is None


def _harita_103(**degis):
    """Sahte SunSpec cihaz: 1 + 103; değiştirilebilir alanlar."""
    r103 = [1500, 500, 500, 500, 0xFFFF, 400, 400, 400, 230, 230, 230, 0, 9876, 1, 5000, 0xFFFE, 0, 0, 0, 0, 0, 0,
            0x7A, 0x1200, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0] + [0] * 10
    for k, v in degis.items():
        r103[int(k)] = v
    def oku(adres, adet):
        if adres == 40000: return [0x5375, 0x6E53]
        if adres == 40002: return [1, 66]
        if adres == 40070: return [103, 50]
        if adres == 40122: return [0xFFFF, 0]
        if adres == 40004: return [0] * 66
        if adres == 40072: return r103[:adet]
        return [0] * adet
    return oku


def test_d2_model_103_tipli_ve_birikmemis_sayac():
    c = ss.oku_cihaz(_harita_103())
    inv = c["inverter"]
    assert inv["guc_w"] == pytest.approx(98760.0) and inv["enerji_wh"] == pytest.approx(8_000_000.0) and inv["enerji_durumu"] == "ok" and c["enerji_yolu"] == "1xx"
    assert inv["akim_a"] == pytest.approx(150.0)                                        # A_SF 0xFFFF = −1 (sentinel değil) → 1500 × 10⁻¹
    c0 = ss.oku_cihaz(_harita_103(**{"4": 0x8000}))                                     # A_SF 0x8000 → ölçek yok → değer uydurulmaz
    assert "akim_a" in c0["inverter"]["uygulanmayan"] and c0["inverter"]["akim_a"] is None
    c2 = ss.oku_cihaz(_harita_103(**{"22": 0, "23": 0}))                                # WH acc32 = 0 → birikmemiş, 0 kWh değil
    assert c2["inverter"]["enerji_wh"] is None and c2["inverter"]["enerji_durumu"] == "birikmemis" and c2["enerji_yolu"] == "yok"
    c3 = ss.oku_cihaz(_harita_103(**{"12": 0xFFFF, "13": 0}))                          # W int16 0xFFFF → −1 W (sentinel değil)
    assert c3["inverter"]["guc_w"] == -1.0
    c4 = ss.oku_cihaz(_harita_103(**{"36": 0xFFFF}))                                   # St enum16 0xFFFF → durum bilinmiyor
    assert c4["inverter"]["durum_kodu"] is None and c4["inverter"]["durum"] == "bilinmiyor"


# ----------------------------------------------------------------------------- D3
def _mbap_sunucu(yanit_uret):
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
    def kos():
        c, _ = srv.accept()
        try:
            istek = c.recv(12)
            cevap = yanit_uret(istek)
            if cevap: c.sendall(cevap)
            c.settimeout(1.0)
            try: c.recv(12)
            except OSError: pass
        finally:
            c.close(); srv.close()
    threading.Thread(target=kos, daemon=True).start()
    return port


def test_d3_mbap_unit_uzunluk_ve_kisa_govde_codex_off06_08():
    def dogru(istek):
        tx = istek[0:2]; return tx + struct.pack(">HHB", 0, 5, 126) + bytes([3, 2]) + struct.pack(">H", 123)
    p = _mbap_sunucu(dogru)
    with ModbusTcpIstemci("127.0.0.1", p, 126, 2.0) as c:
        assert c.oku(10, 1) == [123]
    def yanlis_birim(istek):   # OFF06: istek unit 126, yanıt unit 1 → reddedilmeli
        tx = istek[0:2]; return tx + struct.pack(">HHB", 0, 5, 1) + bytes([3, 2]) + struct.pack(">H", 123)
    with pytest.raises(ModbusHata) as e:
        with ModbusTcpIstemci("127.0.0.1", _mbap_sunucu(yanlis_birim), 126, 2.0) as c:
            c.oku(10, 1)
    assert e.value.kod == "protokol_hatasi" and "birim" in str(e.value)
    def kisa(istek):           # OFF08: uzunluk=1 → IndexError değil, yapısal protokol hatası
        tx = istek[0:2]; return tx + struct.pack(">HHB", 0, 1, 126)
    with pytest.raises(ModbusHata) as e2:
        with ModbusTcpIstemci("127.0.0.1", _mbap_sunucu(kisa), 126, 2.0) as c:
            c.oku(10, 1)
    assert e2.value.kod == "protokol_hatasi" and "uzunlu" in str(e2.value)
    def yanlis_tx(istek):      # OFF07: işlem kimliği uyuşmazlığı (zaten reddediliyordu)
        return struct.pack(">HHHB", 0xBEEF, 0, 5, 126) + bytes([3, 2]) + struct.pack(">H", 1)
    with pytest.raises(ModbusHata):
        with ModbusTcpIstemci("127.0.0.1", _mbap_sunucu(yanlis_tx), 126, 2.0) as c:
            c.oku(10, 1)
    def bytecount(istek):      # byte-count ≠ 2×adet
        tx = istek[0:2]; return tx + struct.pack(">HHB", 0, 7, 126) + bytes([3, 4]) + struct.pack(">HH", 1, 2)
    with pytest.raises(ModbusHata) as e3:
        with ModbusTcpIstemci("127.0.0.1", _mbap_sunucu(bytecount), 126, 2.0) as c:
            c.oku(10, 1)
    assert "byte-count" in str(e3.value)
    def mesgul(istek):         # istisna 6 → cihaz_mesgul (sınıflı)
        tx = istek[0:2]; return tx + struct.pack(">HHB", 0, 3, 126) + bytes([0x83, 6])
    with pytest.raises(ModbusHata) as e4:
        with ModbusTcpIstemci("127.0.0.1", _mbap_sunucu(mesgul), 126, 2.0) as c:
            c.oku(10, 1)
    assert e4.value.kod == "cihaz_mesgul" and e4.value.istisna_kodu == 6
    def sessiz(istek): return b""   # zaman aşımı sınıflı
    with pytest.raises(ModbusHata) as e5:
        with ModbusTcpIstemci("127.0.0.1", _mbap_sunucu(sessiz), 126, 0.5) as c:
            c.oku(10, 1)
    assert e5.value.kod == "zaman_asimi"


def test_d3_zaman_asimi_baglanti_basina():
    h = ca.hedef_dogrula("10.0.0.5", 502, 1, 12)
    assert h["zaman_asimi_sn"] == 12.0 and ca.zaman_asimi(h) == 12.0 and ca.zaman_asimi({"host": "x"}) == 5.0
    with pytest.raises(ValueError):
        ca.hedef_dogrula("10.0.0.5", 502, 1, 0.2)
    gorulen = {}
    class Sahte:
        def __init__(self, host, port, birim, za): gorulen["za"] = za
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def oku(self, a, n): return _harita_103()(a, n)
    r = ca.sina({"host": "10.0.0.5", "zaman_asimi_sn": 20}, onay=True, istemci_fabrikasi=Sahte)
    assert r["durum"] == "ok" and gorulen["za"] == 20.0 and r["ozet"]["profil"] == "1xx" and r["ozet"]["enerji_yolu"] == "1xx"


# ----------------------------------------------------------------------------- D4/D5
def test_d5_kaynak_secimi_tamlik_oncelik_revizyon():
    a = {"ts_utc": T0, "kaynak": "modbus_sunspec", "cihaz_id": "SN1", "sinir": "inverter_ac", "revizyon": 1, "energy_kwh": 75.0, "tamlik": "measured_partial"}
    b = {"ts_utc": T0, "kaynak": "epias_seffaflik", "cihaz_id": "santral", "sinir": "inverter_ac", "revizyon": 1, "energy_kwh": 98.0, "tamlik": "measured_complete"}
    s = ks.sec([a, b])
    assert s["secilen"]["kaynak"] == "epias_seffaflik" and "kısmi" in s["neden"]                      # tamlık önce gelir (öncelik düşük olsa da)
    a2 = {**a, "revizyon": 2, "energy_kwh": 100.0, "tamlik": "measured_complete"}
    s2 = ks.sec([a, a2, b])
    assert s2["secilen"]["kaynak"] == "modbus_sunspec" and s2["secilen"]["revizyon"] == 2 and len(s2["alternatifler"]) == 1   # son revizyon, öncelik 2 > 1
    assert ks.sec([a, b], sinir="pcc_net") is None                                                      # farklı sınır karıştırılmaz
    c = {"ts_utc": T0, "kaynak": "scada_dosya", "cihaz_id": "santral", "sinir": "inverter_ac", "revizyon": 1, "energy_kwh": 99.0, "tamlik": "measured_complete"}
    assert ks.sec([a2, c])["secilen"]["kaynak"] == "scada_dosya"                                        # varsayılan öncelik dosya > canlı
    assert ks.sec([a2, c], onc={"modbus_sunspec": 9})["secilen"]["kaynak"] == "modbus_sunspec"          # santral önceliği ezer
    k = ks.karsilastir([a, a2, b], [{"ts_utc": T0, "energy_kwh": 97.0, "power_kw": 97.0, "flag": "valid", "kaynak": "scada_dosya"}])
    assert k["ozet"]["n_saat"] == 1 and k["saatler"][0]["fark_kwh"] == pytest.approx(3.0) and k["saatler"][0]["alternatif_sayisi"] == 1
    assert ks.oncelik({"params_json": {"kaynak_onceligi": {"modbus_sunspec": 7}}})["modbus_sunspec"] == 7


def test_d5_ayni_satir_revizyon_uretmez():
    onceki = {"power_kw": 120.0, "energy_kwh": 100.0, "tamlik": "measured_complete", "yontem": "sayac"}
    assert co._ayni(onceki, {"power_kw": 120.0, "energy_kwh": 100.0000001, "tamlik": "measured_complete", "nitelik": "sayac"})
    assert not co._ayni(onceki, {"power_kw": 120.0, "energy_kwh": 75.0, "tamlik": "measured_partial", "nitelik": "sayac"})


# ----------------------------------------------------------------------------- D6
def test_d6_kucuk_negatif_ham_korunur():
    from pvquant.io.ingestion.validate import validate
    ix = pd.date_range("2026-06-01 00:00", periods=6, freq="h", tz="UTC")
    df = pd.DataFrame({"power_kw": [-2.0, 0.0, 10.0, 500.0, 800.0, -300.0]}, index=ix)
    out, rep = validate(df, capacity_kwp=1000.0, latitude=38.4, longitude=34.6)
    assert out["power_kw"].iloc[0] == 0.0 and out["power_kw_ham"].iloc[0] == -2.0          # kırpıldı ama ham duruyor
    assert out["flag"].iloc[5] == "negative_power" and out["power_kw_ham"].iloc[5] == -300.0
    assert any("power_kw_ham" in w for w in rep.warnings)
