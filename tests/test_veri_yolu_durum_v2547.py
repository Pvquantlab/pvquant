"""09.11.2026 inceleme III — veri kaynakları: yetenek matrisi, tek bağlantı durum kodu, veri durumu kodları (SAF)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pvquant.services import veri_yolu_service as vy


def test_yetenek_matrisi_her_yolda_ve_durustluk():
    assert set(vy.YETENEKLER) == set(vy.VERI_YOLLARI)
    y = {k: vy._yol(k)["yetenekler"] for k in vy.VERI_YOLLARI}
    assert y["modbus_sunspec"]["sinama"] == "okuma" and y["modbus_sunspec"]["veri_okuma"] and y["modbus_sunspec"]["duzenli_cekis"]
    assert y["iec104"]["sinama"] == "ulasilabilirlik" and not y["iec104"]["veri_okuma"] and "veri okunmaz" in y["iec104"]["sinama_etiketi"]
    assert y["inverter_bulut_api"]["sinama"] == "kimlik" and y["inverter_bulut_api"]["veri_okuma"] and y["inverter_bulut_api"]["duzenli_cekis"] and y["inverter_bulut_api"]["dogrulama"] == "sahte"   # v2.557: şifreli kimlikle düzenli çekiş
    assert y["opc_ua"]["sinama"] is None and y["opc_ua"]["dogrulama"] == "yok"
    assert all(y[k]["dogrulama"] == "canli" for k in ("scada_dosya", "epias_seffaflik", "sayac_dosya"))
    assert all("doğrulanmadı" in y[k]["dogrulama_etiketi"] for k in ("modbus_sunspec", "iec104", "inverter_bulut_api"))   # sahte başarı yok
    for k in vy.VERI_YOLLARI:
        for yasak in ("P4", "paket", "bağlayıcı yazılmaz"):
            assert yasak not in vy.VERI_YOLLARI[k]["not"], (k, yasak)


def test_baglanti_durumu_kodlari():
    bd = vy.baglanti_durumu
    assert bd(None, [])["kod"] == "yapilandirilmadi"
    assert bd({"tur": "scada_dosya"}, [])["kod"] == "dosya"
    assert bd({"tur": "epias_seffaflik"}, [])["kod"] == "mevcut"
    assert bd({"tur": "opc_ua", "salt_okuma_onayi": True}, [])["kod"] == "desteklenmiyor"                          # sınama yok
    assert bd({"tur": "inverter_bulut_api", "saglayici": "GoodWe"}, [])["kod"] == "desteklenmiyor"                 # bağlayıcı yok
    assert bd({"tur": "inverter_bulut_api", "saglayici": "solaredge_v1"}, [])["kod"] == "desteklenmiyor"                # v2.548: V1 kapandı → bağlantı yok
    assert bd({"tur": "inverter_bulut_api", "saglayici": "fusionsolar"}, [])["kod"] == "sinanmadi"
    assert bd({"tur": "inverter_bulut_api", "saglayici": "fusionsolar", "son_sinama": {"durum": "kimlik_hatasi"}}, [])["kod"] == "kimlik_hatasi"
    assert bd({"tur": "modbus_sunspec", "baglanti": {"host": "h"}}, [])["kod"] == "sinanmadi"
    assert bd({"tur": "modbus_sunspec", "baglanti": {"host": "h"}, "son_sinama": {"durum": "ok"}}, [])["kod"] == "sinama_ok"
    assert bd({"tur": "modbus_sunspec", "baglanti": {"host": "h"}, "son_sinama": {"durum": "veri_modeli_yok"}}, [])["kod"] == "sinama_basarisiz"
    assert bd({"tur": "modbus_sunspec", "baglanti": {"host": "h"}, "son_sinama": {"durum": "ok"}, "ornekleme_acik": True}, [])["kod"] == "cekis_acik"
    assert bd({"tur": "modbus_sunspec", "baglanti": {"host": "h"}, "ornekleme_acik": True}, [{"tur": "modbus_sunspec", "son": "2026-11-09T06:00:00+00:00"}])["kod"] == "veri_akisi"
    assert bd({"tur": "iec104", "baglanti": {"host": "h"}, "son_sinama": {"durum": "protokol_yaniti_yok"}}, [])["kod"] == "sinama_basarisiz"
    assert bd({"tur": "iec104", "baglanti": {"host": "h"}, "son_sinama": {"durum": "ok", "ozet": {"yontem": "tcp"}}}, [])["kod"] == "tcp_ok"            # v2.548 H2: TCP kipi «başarılı» sayılmaz
    assert bd({"tur": "iec104", "baglanti": {"host": "h"}, "son_sinama": {"durum": "ok", "ozet": {"yontem": "startdt", "startdt_con": True}}}, [])["kod"] == "sinama_ok"
    assert set(vy.BAGLANTI_DURUM_ETIKET) >= {"yapilandirilmadi", "sinanmadi", "sinama_ok", "sinama_basarisiz", "kimlik_hatasi", "desteklenmiyor", "veri_akisi", "tcp_ok"}


def test_veri_kodu_ve_kayit_yok_sarti():
    simdi = datetime(2026, 11, 9, 9, tzinfo=timezone.utc)
    assert vy.veri_kodu(vy.tazelik(simdi - timedelta(hours=5), simdi), son_olcum="x") == "guncel"
    assert vy.veri_kodu(vy.tazelik(simdi - timedelta(days=11), simdi), son_olcum="x") == "gecikmis"
    assert vy.veri_kodu(vy.tazelik(simdi - timedelta(days=11), simdi), son_olcum=None) == "olcum_bilinmiyor"      # son ölçüm damgası yoksa «bilinmiyor»
    assert vy.veri_kodu(vy.tazelik(None, simdi, "dosya"), None, "dosya") == "yuklenmedi"
    assert vy.veri_kodu(vy.tazelik(simdi - timedelta(days=3), simdi, "dosya"), None, "dosya") == "dosya"
    assert vy.veri_kodu(vy.tazelik(None, simdi), None) == "gelmedi"
