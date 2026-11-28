"""26.11.2026 — veri kalitesi taraması: sentetik seri; (1) 1 sa kaydırılmış dönem → zaman kayması uyarısı (başlangıç ayı), kaymasız → temiz;
(2) AC üstü saatler sayılır/kırpılmaz; (3) GHI varken sıfır üretim günleri (kar) sayılır/düzeltilmez; sınır yoksa «uygulanamaz»."""
import numpy as np
import pandas as pd
import pvlib

from pvquant.services import veri_kalite_tarama as vk

IDX = pd.date_range("2025-01-01", "2025-12-31 23:00", freq="1h", tz="UTC")
LOC = pvlib.location.Location(37.3, 40.7)


def _seri(kwp=9000.0):
    cs = LOC.get_clearsky(IDX + pd.Timedelta(minutes=30), model="ineichen")
    cs.index = IDX
    ghi = cs["ghi"].clip(lower=0)
    power = (ghi / 1000.0 * kwp * 0.8).clip(upper=kwp * 0.95)
    return power, ghi


def test_zaman_kaymasi_tespit_ve_temiz():
    power, ghi = _seri()
    temiz = vk.zaman_kaymasi(power, ghi)
    assert temiz["sinif"] == "temiz" and temiz["ardisik_kayma_ay"] == 0 and all(v == 0 for v in temiz["aylik_en_iyi_lag"].values() if v is not None)
    kaymis = power.copy()
    m = kaymis.index >= pd.Timestamp("2025-02-01", tz="UTC")                       # Şubat'tan itibaren güç 1 sa ERKEN etiketli (Mardin vakası)
    kaymis[m] = power.shift(-1)[m].fillna(0.0)
    r = vk.zaman_kaymasi(kaymis, ghi)
    assert r["sinif"] == "uyari" and r["kayma_baslangic"] == "2025-02" and r["ardisik_kayma_ay"] >= 10
    assert r["aylik_en_iyi_lag"]["2025-01"] == 0 and r["aylik_en_iyi_lag"]["2025-06"] == -1 and "KAYDIRILMADI" in r["mesaj"]
    assert (kaymis.values == kaymis.values).all()                                     # girdi değişmedi (yalnız rapor)


def test_ac_asimi_sayar_kirpmaz():
    power, _ = _seri()
    p = power.copy()
    sec = p[p.index.month == 2].nlargest(21).index                              # Şubat'ın en yüksek 21 saati
    p[sec] = 9350.0                                                                 # 21 saat sınır üstü (+%3,9)
    r = vk.ac_asimi(p, 9000.0)
    assert r["sinif"] == "uyari" and r["saat"] == 21 and r["aylar"] == {"2025-02": 21} and r["maks_oran"] == 1.039 and "KIRPILMADI" in r["mesaj"]
    assert float(p.max()) == 9350.0                                                 # kırpılmadı
    assert vk.ac_asimi(power, 9000.0)["sinif"] == "temiz" and vk.ac_asimi(power, None)["sinif"] == "uygulanamaz"


def test_kis_uretim_kaybi_gunleri():
    power, ghi = _seri(kwp=8800.0)
    p = power.copy()
    kar = [pd.Timestamp(f"2025-01-{d:02d}", tz="UTC").date() for d in (4, 5, 6, 8, 18)]
    p[np.isin(p.index.date, kar)] = 0.01                                             # 5 gün güneş var üretim yok
    t = pd.Series(5.0, index=IDX)
    t[np.isin(t.index.date, kar)] = -10.0
    r = vk.kis_uretim_kaybi(p, ghi, 8800.0, t_air=t)
    assert r["sinif"] == "uyari" and r["gun"] == 5 and r["gunler"][0] == "2025-01-04" and r["t_min_ort"] == -10.0
    assert r["normal_verim_medyan"] is not None and r["kayip_uretim_kwh_tahmini"] > 0 and "DÜZELTİLMEDİ" in r["mesaj"]
    assert vk.kis_uretim_kaybi(power, ghi, 8800.0)["sinif"] == "temiz"
    hepsi = vk.tara(p, ghi, kwp=8800.0, ac_limit_kw=8000.0, t_air=t)
    assert hepsi["sinif"] == "uyari" and hepsi["zaman_kaymasi"]["sinif"] == "temiz" and hepsi["kis_uretim_kaybi"]["gun"] == 5
