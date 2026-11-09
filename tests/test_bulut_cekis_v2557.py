"""v2.557 (Aşama 3, K2) — FusionSolar düzenli çekiş (SAF): satır dönüşümü, gün seçimi, kota sayacı, hesap başına tek giriş/çağrı, birim kapısı, hata sınıfı."""
from __future__ import annotations

from datetime import date, datetime, timezone

from pvquant.services import bulut_cekis_service as bc

T = datetime(2026, 11, 9, 10, 30, tzinfo=timezone.utc)   # 13:30 TSİ


class SahteIstemci:
    girisler: list = []
    cagrilar: list = []

    def __init__(self, bolge):
        self.bolge = bolge

    def giris(self, kimlik):
        SahteIstemci.girisler.append((self.bolge, kimlik.get("kullanici")))

    def saatlik(self, kodlar, gun):
        """FusionSolar ham biçimi (satirlar() testi için)."""
        ms = int(gun.timestamp() * 1000)
        return [{"collectTime": ms + 3_600_000 * h, "stationCode": k, "dataItemMap": {"inverter_power": 10.0 * h}} for k in (kodlar if isinstance(kodlar, list) else kodlar.split(",")) for h in range(3)]

    def saatlik_ham(self, kodlar, gun):
        SahteIstemci.cagrilar.append((",".join(kodlar), gun))
        return [{**r, "alanlar": {**r["alanlar"], "enerji_kwh_belge": r["alanlar"]["inverter_power"]}} for r in bc.satirlar(self.saatlik(kodlar, gun))]

    def kapat(self):
        pass


def _kayit(i, plant, kod, dogrulandi=False, kota_gun=None, kota_sayac=0):
    return {"id": i, "tenant_id": "t", "plant_id": plant, "saglayici": "fusionsolar", "bolge": "eu5", "dis_kimlik": kod, "birim_dogrulandi": dogrulandi,
            "kota_gun": kota_gun, "kota_sayac": kota_sayac, "tz": "Europe/Istanbul", "santral_adi": plant}


def test_satirlar_gunler_kota_sinif():
    ms = int(datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc).timestamp() * 1000)
    st = bc.satirlar([{"collectTime": ms, "stationCode": "A", "dataItemMap": {"inverter_power": 12.5}}, {"collectTime": "x"}])
    assert len(st) == 1 and st[0]["kimlik"] == "A" and st[0]["ts_utc"] == datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc) and st[0]["alanlar"] == {"inverter_power": 12.5}
    g = bc.gunler(T, "Europe/Istanbul"); assert len(g) == 1 and g[0].hour == 0 and g[0].day == 9 and g[0].tzinfo is not None
    g2 = bc.gunler(datetime(2026, 11, 9, 22, 30, tzinfo=timezone.utc), "Europe/Istanbul")   # 01:30 TSİ (10 Kasım): dün de
    assert [x.day for x in g2] == [10, 9]
    assert bc.kota_sayaci([{"kota_gun": "2026-11-09", "kota_sayac": 5}, {"kota_gun": date(2026, 11, 8), "kota_sayac": 20}], date(2026, 11, 9)) == 5
    assert bc.siniflandir("FusionSolarHata: kimlik doğrulanamadı (305)") == "kimlik_hatasi" and bc.siniflandir("istek sıklığı aşıldı (407)") == "kota"
    assert bc.siniflandir("sistem düzeyi istek sınırı (HTTP 429)") == "kota" and bc.siniflandir("HTTP 500") == "hata"


def test_tur_hesap_basina_tek_giris_tek_cagri_ve_birim_kapisi():
    SahteIstemci.girisler.clear(); SahteIstemci.cagrilar.clear()
    kayitlar = [_kayit(1, "p1", "A"), _kayit(2, "p2", "B", dogrulandi=True)]
    ham, golge, gunc = [], [], []
    out = bc.tur(simdi=T, kayitlar=kayitlar, coz=lambda k: {"kullanici": "u", "sistem_kodu": "Gizli-Sifre"}, istemci_fabrikasi=SahteIstemci,
                 ham_yaz=lambda k, st: (ham.append((k["plant_id"], len(st))), len(st))[1], golge_yaz=lambda k, st, simdi: (golge.append(k["plant_id"]), 1)[1],
                 guncelle=lambda k, d, h, z, g, s: gunc.append((k["plant_id"], d, s)))
    assert len(SahteIstemci.girisler) == 1 and len(SahteIstemci.cagrilar) == 1 and SahteIstemci.cagrilar[0][0] == "A,B"   # iki santral, tek hesap, tek çağrı
    assert sorted(ham) == [("p1", 3), ("p2", 3)] and golge == ["p2"]   # birim doğrulanmayan p1 gölgeye yazılmaz
    assert gunc == [("p1", "ok", 1), ("p2", "ok", 1)] and "çağrı 1/24" in out and "Gizli-Sifre" not in out
    assert bc.tur(simdi=T, kayitlar=[]) is None


def test_tur_kota_dolu_ve_kimlik_hatasi_kimlik_sizdirmaz():
    SahteIstemci.girisler.clear(); SahteIstemci.cagrilar.clear()
    gunc = []
    out = bc.tur(simdi=T, kayitlar=[_kayit(1, "p1", "A", kota_gun=date(2026, 11, 9), kota_sayac=24)], coz=lambda k: {"kullanici": "u", "sistem_kodu": "s"},
                 istemci_fabrikasi=SahteIstemci, ham_yaz=lambda *a: 0, golge_yaz=lambda *a: 0, guncelle=lambda k, d, h, z, g, s: gunc.append((d, s)))
    assert gunc == [("kota_doldu", 24)] and not SahteIstemci.girisler and "kota doldu" in out

    class Kotu(SahteIstemci):
        def giris(self, kimlik):
            raise RuntimeError("kimlik doğrulanamadı (305): oturum yok")
    gunc.clear()
    out = bc.tur(simdi=T, kayitlar=[_kayit(1, "p1", "A")], coz=lambda k: {"kullanici": "nbi_u", "sistem_kodu": "Gizli-Sifre"}, istemci_fabrikasi=Kotu,
                 ham_yaz=lambda *a: 0, golge_yaz=lambda *a: 0, guncelle=lambda k, d, h, z, g, s: gunc.append((d, h)))
    assert gunc[0][0] == "kimlik_hatasi" and "Gizli-Sifre" not in out and "Gizli-Sifre" not in (gunc[0][1] or "")
    gunc.clear()
    out = bc.tur(simdi=T, kayitlar=[_kayit(1, "p1", "A")], coz=lambda k: (_ for _ in ()).throw(RuntimeError("KEK yok")), istemci_fabrikasi=SahteIstemci,
                 ham_yaz=lambda *a: 0, golge_yaz=lambda *a: 0, guncelle=lambda k, d, h, z, g, s: gunc.append((d, h)))
    assert gunc[0][0] == "kasa_hatasi" and "kimlik çözülemedi" in out
