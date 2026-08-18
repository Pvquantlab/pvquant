"""D21 (v2.155): kapak dönemi ↔ günlük seri tutarlılığı — 18 Ağu kabul avı.

Canlı vaka: kapak "18 Ağustos – 02 Eylül" derken eksen 05–20 basıyordu.
Kök s01'in elle range(5,21) ekseniydi (bu mühürde söküldü); D21 girdi-tarafı
sapmayı da (forecast bloğu ↔ daily bloğu) kalıcı bekçiye bağlar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reporting" / "html"))
import veri     # noqa: E402
import denetim  # noqa: E402


def _kos(yuzey):
    kayit = []
    denetim._d21(yuzey, lambda kod, durum, mesaj, beklenen, bulunan:
                 kayit.append({"durum": durum, "mesaj": mesaj,
                               "beklenen": str(beklenen), "bulunan": str(bulunan)}))
    return kayit[0]


def _y(tarih=None, bas=None, bit=None, n=None):
    t = tarih if tarih is not None else list(veri.GUN_TARIH)
    return {"FORECAST_BASLANGIC": bas if bas is not None else t[0],
            "FORECAST_BITIS": bit if bit is not None else t[-1],
            "GUN_TARIH": t,
            "GUN_SAYISI": n if n is not None else len(t)}


def test_kanonik_yuzeyler_ve_gecis():
    assert veri.GUN_TARIH[0] == veri.FORECAST_BASLANGIC == "2026-08-05"
    assert veri.GUN_TARIH[-1] == veri.FORECAST_BITIS == "2026-08-20"
    assert len(veri.GUN_TARIH) == veri.GUN_SAYISI == 16
    assert _kos(vars(veri))["durum"] == "gecti"


def test_uc_celiskisi_hata():
    """Canlı vakanın imzası: forecast bloğu taze, daily bayat."""
    k = _kos(_y(bas="2026-08-18", bit="2026-09-02"))
    assert k["durum"] == "hata" and "çelişiyor" in k["mesaj"]
    assert "2026-08-05" in k["beklenen"] and "2026-08-18" in k["bulunan"]


def test_ardisiklik_kirilmasi_hata():
    t = list(veri.GUN_TARIH)
    del t[7]                                            # bir gün atlanmış
    k = _kos(_y(tarih=t, n=15))
    assert k["durum"] == "hata" and "ardışık değil" in k["mesaj"]


def test_gun_sayisi_celiskisi_hata():
    k = _kos(_y(n=15))
    assert k["durum"] == "hata" and "GUN_SAYISI" in k["mesaj"]


def test_yuzey_yoksa_uyari():
    assert _kos({"GUN_SAYISI": 16})["durum"] == "uyari"


def test_s01_ekseni_gun_etiketten():
    """C-5/1: elle eksen geri dönmesin — fan_chart doğrudan GUN_ETIKET alır,
    yerel 'days' ataması yok (yorumlardaki anma serbest)."""
    kaynak = (Path(__file__).resolve().parents[1]
              / "reporting" / "html" / "build_s01.py").read_text()
    kod = "\n".join(l.split("#", 1)[0] for l in kaynak.splitlines())
    assert "fan_chart(p50, hw, GUN_ETIKET" in kod
    assert "days =" not in kod and "list(range(" not in kod
