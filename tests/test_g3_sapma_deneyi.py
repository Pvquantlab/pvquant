"""G3 (F1-02) — sapma katmanı deneyi: gün-bloklu eşli bootstrap; DB yok. Sentetik: 40 gün × 10 gündüz saati."""
import numpy as np
import pandas as pd
import pytest

from pvquant.ext.tahmin import sapma_deneyi as sd


def _veri(gun=40, saat=10, servis_carpan=1.0, tohum=1):
    rng = np.random.default_rng(tohum)
    gunler = np.repeat([f"2026-10-{i + 1:02d}" if i < 30 else f"2026-11-{i - 29:02d}" for i in range(gun)], saat)
    y = rng.uniform(200, 1000, gun * saat)
    fizik = y * rng.normal(1.0, 0.08, gun * saat)                 # saf fizik: yansız, %8 gürültü
    servis = fizik * servis_carpan                                  # sapma katmanı = çarpan
    return pd.DataFrame({"y": y, "physics_kw": fizik, "p50_kw": servis, "gun": gunler,
                         "kova": np.where(np.arange(gun * saat) % 2 == 0, "0-24", "24-72")})


def test_servis_daha_kotu_anlamli_ve_isaret():
    e = _veri(servis_carpan=1.15)                                  # katman %15 şişiriyor → servis kötü
    r = sd.eslesmis_bootstrap(e.y, e.p50_kw, e.physics_kw, e.gun)
    assert r["n"] == 400 and r["n_gun"] == 40
    assert r["fark_wmape_puan"] > 0 and r["ga_alt"] > 0 and r["sonuc"] == sd.KOTU
    assert r["sapma_degistirdi_pay"] == 1.0
    assert r["wmape_servis"] == pytest.approx(float(np.abs(e.p50_kw - e.y).sum() / e.y.sum() * 100))


def test_ayni_tahmin_belirsiz_ve_fark_sifir():
    e = _veri(servis_carpan=1.0)
    r = sd.eslesmis_bootstrap(e.y, e.p50_kw, e.physics_kw, e.gun)
    assert r["fark_wmape_puan"] == 0.0 and r["ga_alt"] == 0.0 and r["ga_ust"] == 0.0
    assert r["sonuc"] == sd.BELIRSIZ and r["sapma_degistirdi_pay"] == 0.0


def test_servis_daha_iyi_anlamli():
    e = _veri(servis_carpan=1.0)
    e["p50_kw"] = e.y * 1.0 + (e.physics_kw - e.y) * 0.3            # katman hatayı %70 azaltıyor
    r = sd.eslesmis_bootstrap(e.y, e.p50_kw, e.physics_kw, e.gun)
    assert r["ga_ust"] < 0 and r["sonuc"] == sd.IYI


def test_deterministik_tohum_ve_yetersiz_gun():
    e = _veri(servis_carpan=1.1)
    a = sd.eslesmis_bootstrap(e.y, e.p50_kw, e.physics_kw, e.gun)
    b = sd.eslesmis_bootstrap(e.y, e.p50_kw, e.physics_kw, e.gun)
    assert a == b
    az = e[e.gun.isin(sorted(e.gun.unique())[:5])]                 # 5 gün < ASGARI_GUN
    r = sd.eslesmis_bootstrap(az.y, az.p50_kw, az.physics_kw, az.gun)
    assert r["sonuc"] == sd.YETERSIZ and r["ga_alt"] is None and r["wmape_servis"] is not None
    bos = sd.eslesmis_bootstrap([], [], [], [])
    assert bos["n"] == 0 and bos["sonuc"] == sd.YETERSIZ and bos["wmape_servis"] is None
    with pytest.raises(ValueError):
        sd.eslesmis_bootstrap([1, 2], [1], [1, 2], ["a", "b"])


def test_tablo_karar_ve_markdown():
    e = _veri(servis_carpan=1.15)
    t = sd.deney_tablosu(e)
    assert list(t["kova"]) == ["0-24", "24-72", "tum"] and (t["sonuc"] == sd.KOTU).all()
    k = sd.karar(t)
    assert k["oneri"] == "kapali" and k["kotu"] == 2 and k["iyi"] == 0
    md = sd.markdown(t)
    assert md.count("\n") == 4 and "servis anlamlı KÖTÜ" in md and "—" not in md
    # servis bir kovada iyi ise katman kalır
    e2 = _veri(servis_carpan=1.0)
    e2["p50_kw"] = e2.y + (e2.physics_kw - e2.y) * 0.3
    assert sd.karar(sd.deney_tablosu(e2))["oneri"] == "otomatik"
    assert sd.karar(sd.deney_tablosu(_veri(servis_carpan=1.0)))["oneri"] == "belirsiz"
    assert sd.karar(pd.DataFrame())["oneri"] == "belirsiz"
