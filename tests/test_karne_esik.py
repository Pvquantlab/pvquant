"""C-3b (v2.151): s08 bütünlük kurallarının makine karşılığı — rapor tarafı.

Kural 2 (kapsama < %60 → karne dışı) D19 ile, kural 4 (geçerli gün < 14 →
başlık uyarısı) karne_uyari + D20 ile denetimlenir. Beklenenler elle değil
KARNE_ESIK'ten kurulur; mutasyon denetimleri sabit dönüşü yakalar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reporting" / "html"))
import veri     # noqa: E402
import denetim  # noqa: E402


def _kos(fn, yuzey):
    kayit = []
    fn(yuzey, lambda kod, durum, mesaj, beklenen, bulunan: kayit.append(
        {"kod": kod, "durum": durum, "mesaj": mesaj,
         "beklenen": str(beklenen), "bulunan": str(bulunan)}))
    return kayit


# ---------------------------------------------------------------- kanonik
def test_kanonik_esikler_ve_yuzeyler():
    assert veri.KARNE_ESIK == {"kapsama_pct": 60, "kucuk_orneklem_gun": 14}
    assert veri.KARNE_KAPSAMA == [100] * 30
    assert veri.KARNE_GECERLI_GUN == 30
    assert veri.KARNE_UYARI == ""          # md5 kalkanı: kanonikte boş token


def test_kanonik_d19_d20_gecer():
    assert [k["durum"] for k in _kos(denetim._d19, vars(veri))] == ["gecti"]
    assert [k["durum"] for k in _kos(denetim._d20, vars(veri))] == ["gecti"]


# ---------------------------------------------------------------- karne_uyari
def test_uyari_esikten_turetilir():
    e = veri.KARNE_ESIK["kucuk_orneklem_gun"]
    assert veri.karne_uyari(e) == ""                      # eşik dahil değil
    m = veri.karne_uyari(e - 1)
    assert ("%d geçerli gün" % (e - 1)) in m and ("eşik %d" % e) in m


def test_uyari_mutasyon_izler():
    """Sabit dönüş yakalanır: eşik sözlükten değişince metin izler."""
    m = veri.karne_uyari(5, {"kucuk_orneklem_gun": 7})
    assert "5 geçerli gün" in m and "eşik 7" in m
    assert veri.karne_uyari(7, {"kucuk_orneklem_gun": 7}) == ""


# ---------------------------------------------------------------- D19
def _y19(kap, olc, esik=None):
    return {"KARNE_ESIK": esik or veri.KARNE_ESIK,
            "KARNE_KAPSAMA": kap, "KARNE_OLCULDU": olc}


def test_d19_esik_alti_skorlu_gun_hata():
    e = veri.KARNE_ESIK["kapsama_pct"]
    k = _kos(denetim._d19, _y19([e - 1, e], [True, True]))
    assert k[0]["durum"] == "hata" and "satır [1]" in k[0]["mesaj"]


def test_d19_esik_alti_dislanmis_gun_gecer():
    e = veri.KARNE_ESIK["kapsama_pct"]
    k = _kos(denetim._d19, _y19([e - 1, e], [False, True]))
    assert k[0]["durum"] == "gecti"


def test_d19_esik_siniri_dahil_degil():
    """Kapsama tam eşikte = karne İÇİ (kural '< %60' der, '<=' değil)."""
    e = veri.KARNE_ESIK["kapsama_pct"]
    k = _kos(denetim._d19, _y19([e], [True]))
    assert k[0]["durum"] == "gecti"


def test_d19_alan_yoksa_uyari():
    k = _kos(denetim._d19, _y19([None, None], [True, True]))
    assert k[0]["durum"] == "uyari" and "kapsama" in k[0]["mesaj"]


def test_d19_hizasiz_seri_hata():
    k = _kos(denetim._d19, _y19([100], [True, True]))
    assert k[0]["durum"] == "hata"


# ---------------------------------------------------------------- D20
def _y20(olc, uyari_gecerli=None):
    g = sum(1 for o in olc if o)
    uy = veri.karne_uyari(g if uyari_gecerli is None else uyari_gecerli)
    return {"KARNE_ESIK": veri.KARNE_ESIK, "KARNE_OLCULDU": olc,
            "KARNE_UYARI": uy}


def test_d20_ureticiden_beslenen_tutarlilik():
    """Fikstür karne_uyari'nin KENDİSİNDEN kurulur (v2.149 dersi)."""
    e = veri.KARNE_ESIK["kucuk_orneklem_gun"]
    assert _kos(denetim._d20, _y20([True] * e))[0]["durum"] == "gecti"
    assert _kos(denetim._d20, _y20([True] * (e - 1)))[0]["durum"] == "gecti"


def test_d20_bayat_bos_uyari_hata():
    e = veri.KARNE_ESIK["kucuk_orneklem_gun"]
    y = _y20([True] * (e - 1))
    y["KARNE_UYARI"] = ""                                  # elle ezilmiş
    assert _kos(denetim._d20, y)[0]["durum"] == "hata"


def test_d20_gereksiz_dolu_uyari_hata():
    e = veri.KARNE_ESIK["kucuk_orneklem_gun"]
    y = _y20([True] * e, uyari_gecerli=e - 1)              # 30 günde uyarı
    assert _kos(denetim._d20, y)[0]["durum"] == "hata"
