"""v2.568 (Faz 0 onay paketi 1) — karne kuralı: çoklu koşu çift sayımı, gün içi ayrımı, geriye bakışlı dışlama, program kovası, tek gündüz eşiği."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.worker.main import kova_skorlari  # noqa: E402
from pvquant.services import karne_kurali as kk  # noqa: E402

GUN = pd.Timestamp("2026-11-09", tz="UTC")
SAATLER = list(range(6, 18))                                       # 12 gündüz saati (UTC)
GERCEK = np.array([200, 600, 1200, 1800, 2200, 2400, 2400, 2200, 1800, 1200, 600, 200], float)


def _satirlar(run_at, carpan, etiket=None, model="barhdadi_bennis", meteo="acik"):
    return [{"ts_utc": GUN + pd.Timedelta(hours=h), "run_at": run_at, "p50_kw": g * carpan, "power_kw": g,
             "model": model, "meteo_source": meteo, "etiket": etiket} for h, g in zip(SAATLER, GERCEK)]


def _skor(df):
    d = df.copy(); d["gun"] = d.ts_utc.dt.date; d["naif"] = np.nan
    return {r["k"]: round(r["m"], 2) for r in kova_skorlari(d, 3000.0, "t", "p")}


def test_cift_sayim_kalkar_ve_gun_ici_ayri_kovada():
    sabah = _satirlar(GUN + pd.Timedelta(hours=2), 1.20)                         # 02:00 UTC, %20 fazla
    gun_ici = _satirlar(GUN + pd.Timedelta(hours=9, minutes=30), 1.02, etiket="gun_ici")   # 09:30 UTC revizyon
    ham = pd.DataFrame(sabah + gun_ici)
    # eski davranış: aynı saat iki satır → iyimser
    eski = ham.copy(); eski["kova"] = "0-24"
    assert _skor(eski)["0-24"] == 11.0
    # yeni kural: 0-24 yalnız sabah koşusu; gün içi ayrı kova
    yeni = kk.karne_secimi(ham)
    assert set(yeni["kova"]) == {"0-24", "gun_ici"}
    assert yeni[yeni.kova == "0-24"].ts_utc.is_unique and len(yeni[yeni.kova == "0-24"]) == 12
    s = _skor(yeni)
    assert s["0-24"] == 20.0 and s["gun_ici"] == 2.0


def test_ana_kovada_en_erken_kosu_tutulur():
    dun = _satirlar(GUN - pd.Timedelta(hours=9), 1.30)      # D-1 15:00 UTC: ufuk 15–26 s → bir kısmı 0-24, kalanı 24-72
    sabah = _satirlar(GUN + pd.Timedelta(hours=2), 1.20)    # ufuk 4–15 s
    yeni = kk.karne_secimi(pd.DataFrame(dun + sabah))
    k24 = yeni[yeni.kova == "0-24"]
    assert k24.ts_utc.is_unique
    # 15:00 koşusunun 0-24'e düşen saatleri (ufuk ≤ 24: 06..15 UTC; 15:00 tam 24 s) sabah koşusunu ezer (en erken yayımlanan)
    erken = k24[k24.ts_utc.dt.hour <= 15]
    assert (erken.p50_kw / erken.power_kw).round(2).eq(1.30).all()
    gec = k24[k24.ts_utc.dt.hour > 15]
    assert (gec.p50_kw / gec.power_kw).round(2).eq(1.20).all()
    assert (yeni[yeni.kova == "24-72"].p50_kw / yeni[yeni.kova == "24-72"].power_kw).round(2).eq(1.30).all()


def test_geriye_bakisli_kosular_disarida():
    sabah = _satirlar(GUN + pd.Timedelta(hours=2), 1.20)
    bt = _satirlar(GUN + pd.Timedelta(hours=1), 1.00, model="backtest", meteo="open-meteo-arsiv")
    yeni = kk.karne_secimi(pd.DataFrame(sabah + bt))
    assert len(yeni) == 12 and (yeni.p50_kw / yeni.power_kw).round(2).eq(1.20).all()
    assert kk.karne_secimi(pd.DataFrame(bt)).empty
    assert kk.karne_secimi(pd.DataFrame()).empty


def test_etiket_ve_model_sutunu_yoksa_eski_davranis_tek_satir():
    sabah = [{k: v for k, v in r.items() if k not in ("model", "meteo_source", "etiket")} for r in _satirlar(GUN + pd.Timedelta(hours=2), 1.2)]
    yeni = kk.karne_secimi(pd.DataFrame(sabah))
    assert len(yeni) == 12 and set(yeni.kova) == {"0-24"}


def test_program_kovasi_kesim_oncesi_son_kosu():
    # teslim günü 9 Kasım 2026 (İstanbul); kesim D-1 15:30 TSİ = 8 Kasım 12:30 UTC
    kesim = pd.Timestamp("2026-11-08 12:30", tz="UTC")
    once1 = _satirlar(kesim - pd.Timedelta(hours=10), 1.40)    # D-1 02:30 UTC sabah koşusu
    once2 = _satirlar(kesim - pd.Timedelta(hours=3), 1.25, etiket="gun_ici")   # D-1 09:30 UTC: kesimden önce → program kaynağı
    sonra = _satirlar(kesim + pd.Timedelta(hours=1), 1.05)     # kesimden sonra: programa giremez
    bt = _satirlar(kesim - pd.Timedelta(hours=1), 1.00, model="backtest")
    prog = kk.program_kovasi(pd.DataFrame(once1 + once2 + sonra + bt))
    assert set(prog.kova) == {"program"} and len(prog) == 12 and prog.ts_utc.is_unique
    assert (prog.p50_kw / prog.power_kw).round(2).eq(1.25).all()
    assert kk.program_kesimi(date(2026, 11, 9)) == pd.Timestamp("2026-11-08 15:30", tz="Europe/Istanbul")
    assert kk.program_kesimi(date(2024, 6, 1)) == pd.Timestamp("2024-05-31 16:00", tz="Europe/Istanbul")   # 2025 öncesi 16:00
    # kesim öncesi koşu yoksa satır yok
    assert kk.program_kovasi(pd.DataFrame(sonra)).empty


def test_karne_satirlari_butun_kovalar_ve_gunduz_esigi():
    kesim = pd.Timestamp("2026-11-08 12:30", tz="UTC")
    ham = pd.DataFrame(_satirlar(kesim - pd.Timedelta(hours=3), 1.25) + _satirlar(GUN + pd.Timedelta(hours=2), 1.20)
                       + _satirlar(GUN + pd.Timedelta(hours=9, minutes=30), 1.02, etiket="gun_ici"))
    hepsi = kk.karne_satirlari(ham)
    assert set(hepsi.kova) == {"0-24", "24-72", "gun_ici", "program"}
    assert set(kk.ana_kovalar(hepsi).kova) <= set(kk.ANA_KOVALAR)
    assert kk.GUNDUZ_ORAN == 0.02 and list(kk.gunduz_maskesi(pd.Series([50.0, 70.0]), 3000.0)) == [False, True]
    assert list(kk.kova_etiketle(pd.Series([1, 24, 25, 72, 73, 168, 169, 383]))) == ["0-24", "0-24", "24-72", "24-72", "72-168", "72-168", "168+", "168+"]
