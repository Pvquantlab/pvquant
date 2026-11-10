"""v2.560/v2.561 — pilot kapıları + referans kıyası (SAF) ve saha toplayıcısı alımı (SAF: anahtar, doğrulama, idempotent ack/çatışma)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from pvquant.services import edge_service as es
from pvquant.services import pilot_service as ps

T0 = datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc)


def test_pilot_durum_ve_kapilar():
    d = ps.durum({"params_json": {}})
    assert len(d["kapilar"]) == 10 and not d["sahaya_hazir"] and d["p0_acik"] == ["G01", "G02", "G03", "G04", "G10"]   # kod kapıları (G05/G06) testlerle kapalı
    assert all(k["tamam"] for k in d["kapilar"] if k["kaynak"] == "kod")
    kap = {k: {"tamam": True, "not": "yazılı izin", "zaman": "2026-11-09T10:00+00:00"} for k in ("G01", "G02", "G03", "G04", "G10")}
    d2 = ps.durum({"params_json": {"pilot": {"kapilar": kap}}})
    assert d2["sahaya_hazir"] and d2["p0_acik"] == [] and not next(k for k in d2["kapilar"] if k["kod"] == "G07")["tamam"]   # marka kapısı P0 değil


def test_referans_csv_ve_kiyas():
    ref = ps.referans_csv_oku("zaman;kwh\n2026-11-09T06:00:00+03:00;100,0\n2026-11-09T07:00+03:00;200\n2026-11-09 08:00;300\nbozuk;x\n")
    assert len(ref) == 3 and ref[0]["ts_utc"] == datetime(2026, 11, 9, 3, 0, tzinfo=timezone.utc) and ref[2]["kwh"] == 300.0 and "UTC varsayıldı" in ref[0]["_uyari"]
    with pytest.raises(ValueError, match="sütunları"):
        ps.referans_csv_oku("a,b\n1,2\n")
    golge = [{"ts_utc": (T0 + timedelta(hours=i)).isoformat(), "secilen": {"tamlik": "measured_complete", "energy_kwh": 100.0 + i, "kaynak": "modbus_sunspec"}} for i in range(30)]
    golge[5]["secilen"]["tamlik"] = "measured_partial"
    ref = [{"ts_utc": T0 + timedelta(hours=i), "kwh": 100.0 + i} for i in range(32)]   # 30, 31. saatte gölge yok
    ref[7]["kwh"] = 90.0   # 17 kWh fark → tolerans dışı
    k = ps.referans_kiyas(golge, ref)
    assert k["n_referans"] == 32 and k["n_golge_yok"] == 2 and k["n_golge_kismi_disi"] == 1 and k["n_ortak"] == 29 and k["n_tolerans_ici"] == 28
    assert k["sonuc"] == "uyumlu" and k["tolerans_disi_saatler"][0]["fark_kwh"] == 17.0 and k["maks_mutlak_fark_kwh"] == 17.0
    assert ps.referans_kiyas(golge[:10], ref[:10])["sonuc"] == "yetersiz"
    kotu = [{**r, "kwh": r["kwh"] * 1.1} for r in ref]
    ku = ps.referans_kiyas(golge, kotu)
    assert ku["sonuc"] == "uyumsuz"
    # 10.11 inceleme: müşteri metninde Türkçe ondalık (virgül) ve ek sorunu olmayan «N tanesi» kalıbı
    assert k["metin"] == "29 ortak tam saatin 28 tanesi toleransta (%96,6; saat başına en çok %2 ya da 0,5 kWh)."
    assert f"yalnız {ku['n_tolerans_ici']} tanesi toleransta (%" in ku["metin"] and not re.search(r"\d\.\d", ku["metin"])


class Defter:
    def __init__(self):
        self.d = {}
    def oku(self, siralar):
        return {s: self.d[s] for s in siralar if s in self.d}
    def yaz(self, sira, ozet, ts):
        self.d[sira] = ozet


def _o(sira, guc=1000.0, cihaz="SN-A"):
    return {"sira": sira, "ts_utc": (T0 + timedelta(minutes=sira)).isoformat(), "cihaz_id": cihaz, "guc_w": guc, "enerji_wh": 5000.0 + sira, "durum_kodu": 4, "olaylar": [], "kisit_yuzde": None}


def test_anahtar_ve_dogrulama():
    anahtar, onek, oz = es.anahtar_uret()
    assert anahtar.startswith("pvqe_") and es.ayristir(anahtar) == (onek, anahtar.split("_", 2)[2]) and es.ayristir("x") is None
    kayit = {"id": "t1", "tenant_id": "ten", "plant_id": "pl", "ad": "saha", "anahtar_hash": oz, "durum": "etkin"}
    assert es.dogrula(anahtar, bul=lambda o: kayit)["plant_id"] == "pl"
    with pytest.raises(PermissionError, match="geçersiz"):
        es.dogrula(anahtar[:-2] + "zz", bul=lambda o: kayit)
    with pytest.raises(PermissionError, match="iptal"):
        es.dogrula(anahtar, bul=lambda o: {**kayit, "durum": "iptal"})
    with pytest.raises(PermissionError):
        es.dogrula(anahtar, bul=lambda o: None)


def test_ornek_dogrula_ve_ozet():
    o = es.ornek_dogrula({"sira": "3", "ts_utc": "2026-11-09T09:00:00Z", "guc_w": "1200", "olaylar": ["GRID_DISCONNECT"]})
    assert o["sira"] == 3 and o["ts_utc"].tzinfo is not None and o["guc_w"] == 1200.0 and o["kanal"] == "edge" and o["cihaz_id"] == "santral"
    for kotu, msg in (({"sira": -1, "ts_utc": "2026-11-09T09:00:00Z"}, "negatif"), ({"sira": 1, "ts_utc": "2026-11-09T09:00:00"}, "saat dilimi"), ({"sira": 1, "ts_utc": "x"}, "ISO"),
                      ({"sira": 1, "ts_utc": "2026-11-09T09:00:00Z", "guc_w": "inf"}, "sonlu"), ({"sira": 1, "ts_utc": "2026-11-09T09:00:00Z", "sinir": "yok"}, "sinir")):
        with pytest.raises(ValueError, match=msg):
            es.ornek_dogrula(kotu)
    a = es.ornek_dogrula(_o(1)); b = es.ornek_dogrula({**_o(1), "sira": 99})
    assert es.icerik_ozeti(a) == es.icerik_ozeti(b)   # sıra özete girmez
    assert es.icerik_ozeti(a) != es.icerik_ozeti(es.ornek_dogrula(_o(1, guc=1001.0)))


def test_al_idempotent_ack_catisma_hatali():
    top = {"id": "t1", "tenant_id": "ten", "plant_id": "pl", "ad": "saha"}; defter = Defter(); yazilan = []
    gunc = []
    r = es.al(top, {"id": "pl"}, [_o(0), _o(1), _o(2), {"sira": 3, "ts_utc": "bozuk"}], T0, defter=defter, yaz=lambda o: yazilan.append(o), topla=False, guncelle=lambda t, z, a: gunc.append(a))
    assert r["kabul"] == 3 and r["yinelenen"] == 0 and r["catisma"] == [] and r["ack_sira"] == 2 and len(r["hatali"]) == 1 and r["hatali"][0]["sira"] == 3 and gunc == [2]
    assert [o["kanal"] for o in yazilan] == ["edge"] * 3
    # yeniden gönderim (aynı içerik) → yinelenen, ack ilerler; aynı sıra farklı içerik → çatışma, ack ilerlemez
    r2 = es.al(top, {"id": "pl"}, [_o(1), _o(2), _o(3), {**_o(0), "guc_w": 999.0}], T0, defter=defter, yaz=lambda o: yazilan.append(o), topla=False, guncelle=lambda *a: None)
    assert r2["kabul"] == 1 and r2["yinelenen"] == 2 and r2["catisma"] == [0] and r2["ack_sira"] == 3 and len(yazilan) == 4
    with pytest.raises(ValueError, match="en çok 500"):
        es.al(top, {"id": "pl"}, [_o(i) for i in range(501)], T0, defter=defter, yaz=lambda o: None, topla=False, guncelle=lambda *a: None)
