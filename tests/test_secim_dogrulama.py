"""26.11.2026 — model seçimi doğrulaması: zaman sıralı mevsim blokları (sızıntısız), havuzlanmış B/C, geri dönüş ve hata işleme.
Değerlendiriciler sahte (hızlı); üretim sargısı kalibre_et'te bayrak "son20" varsayılanıyla eski davranış korunur."""
import numpy as np
import pandas as pd

from pvquant.services import secim_dogrulama as sd

IDX = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="1h", tz="UTC")


def test_bloklar_zaman_sirali_mevsim_kapsar_ve_sizintisiz():
    bl = sd.bloklar(IDX)
    assert len(bl) == 4 and [b.mevsim for b in bl] == ["MAM", "JJA", "SON", "DJF"]   # blok ortaları Mar / Haz / Eyl / Ara
    for b in bl:
        assert b.egitim_bit == b.test_bas < b.test_bit                                 # eğitim bloktan ÖNCE biter, çakışma yok
        assert b.durum == "aday"                                                       # ilk blok öncesi ~73 gün ≥ 45 gün eğitim
    assert all(bl[i].test_bit <= bl[i + 1].test_bas for i in range(3))                 # bloklar birbirini izler
    assert sd.bloklar(IDX[:1]) == [] and sd.bloklar(pd.DatetimeIndex([])) == []
    kisa = sd.bloklar(pd.date_range("2024-06-01", "2024-07-31 23:00", freq="1h", tz="UTC"))   # 61 gün → ilk bloklar eğitim kısa
    assert kisa[0].durum.startswith("atlandi:egitim_kisa") and kisa[-1].durum == "aday"


def _gercek():
    saat = IDX.hour
    return pd.Series(np.where((saat >= 6) & (saat <= 17), 100.0, 0.0), index=IDX)


def _dilim(a, tb, tt, carpan=1.0):
    m = IDX.slice_indexer(tb, tt)
    return a.iloc[m] * carpan


def test_havuzlanmis_metrik_ve_iyilesme_ayni_saatlerde():
    a = _gercek()

    def mod_b(eb, tb, tt):
        return _dilim(a, tb, tt, 1.20)        # +%20 → WMAPE 20

    def mod_c(eb, tb, tt):
        return _dilim(a, tb, tt, 1.10)        # +%10 → WMAPE 10
    r = sd.degerlendir(IDX, a, mod_b, mod_c, esik_kw=1.0)
    assert r is not None and r["sizinti_ok"] and r["mevsimler"] == ["DJF", "JJA", "MAM", "SON"]
    assert r["B"]["wmape"] == 20.0 and r["C"]["wmape"] == 10.0 and r["iyilesme_pct"] == 50.0
    assert sum(b["saat"] for b in r["bloklar"]) == r["saat"] and all(b["durum"] == "ok" for b in r["bloklar"])
    assert r["saat"] < 0.25 * int((a > 1).sum())                                           # toplam holdout ≈ %20 (eski oranla aynı)


def test_hata_ve_geri_donus():
    a = _gercek()
    def mod_b(eb, tb, tt):
        return _dilim(a, tb, tt, 1.2)

    def mod_c_patlar(eb, tb, tt):
        if tb.month == 9:
            raise RuntimeError("LightGBM yok")
        return _dilim(a, tb, tt, 1.1)
    r = sd.degerlendir(IDX, a, mod_b, mod_c_patlar, esik_kw=1.0)
    assert r["B"]["wmape"] == 20.0 and r["C"]["wmape"] == 10.0 and r["C"]["ortak_blok"] == 3 and r["iyilesme_pct"] == 50.0
    assert "1 blokta hibrit hatası" in r["C_not"] and any("mod_c hata" in b["not"] for b in r["bloklar"])   # hata gizlenmez; kıyas 3 ortak blokta
    assert r["C"]["ortak_mevsimler"] == ["DJF", "JJA", "MAM"] and r["C"]["ortak_saat"] < r["saat"]

    def mod_c_tek(eb, tb, tt):                                                             # tek blokta başarılı → ortak blok yetersiz → C None
        if tb.month != 12:
            raise RuntimeError("yok")
        return _dilim(a, tb, tt, 1.1)

    r1 = sd.degerlendir(IDX, a, mod_b, mod_c_tek, esik_kw=1.0)
    assert r1["C"] is None and "ortak blok yetersiz (1 blok" in r1["C_not"] and r1["B"]["wmape"] == 20.0

    def mod_b_patlar(eb, tb, tt):
        raise ValueError("yetersiz veri")

    assert sd.degerlendir(IDX, a, mod_b_patlar, None, esik_kw=1.0) is None                 # hiç geçerli blok yok → None (çağıran eski yola döner)
    r2 = sd.degerlendir(IDX, a, mod_b, None, esik_kw=1.0)
    assert r2["C"] is None and r2["C_not"] == "hibrit istenmedi"
    # eğitim verisinin gelecekten gelmemesi: değerlendiriciye verilen egitim_bit her zaman test_bas'a eşit/önce
    gorulen = []
    def mod_b_izle(eb, tb, tt):
        gorulen.append(eb <= tb)
        return _dilim(a, tb, tt)

    sd.degerlendir(IDX, a, mod_b_izle, None, esik_kw=1.0)
    assert gorulen and all(gorulen)


def test_varsayilan_ayar_eski_yol():
    from pvquant.config import Settings
    assert Settings.model_fields["secim_dogrulama"].default == "son20"
