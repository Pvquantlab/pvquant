"""v2.250 — Dalga 1.5: NREL hakem seti ile CI regresyonu.

Bağımsız, kamuya açık tahmin+gerçekleşen (NREL 2006, üç santral, Haziran) üzerinde metrik motoru
(pvquant.ext.standart.sfa_metrik) ve worker'ın kova_skorlari'si bilinen DA/HA4 hatasını yeniden
üretmeli. Referanslar docs/research/nrel_hakem_metrik.py tanımıyla üretildi (5 dk→saatlik ortalama,
gündüz = gerçek ya da tahmin > %1 kapasite). Tanım değişirse bu test kırmızıya döner — istenen budur."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apps.worker.main import kova_skorlari
from pvquant.ext.standart import sfa_metrik

KOK = Path(__file__).parent / "fixtures" / "nrel"
REFERANS = {  # (klasör, ufuk): (n, wmape, nmae, nrmse, nmbe) — yüzde
    ("az_31.85_-110.85_UPV_100MW", "DA"): (366, 21.772, 8.208, 14.255, 1.777),
    ("az_31.85_-110.85_UPV_100MW", "HA4"): (366, 13.504, 5.091, 8.235, 0.818),
    ("ca_32.65_-115.15_UPV_75MW", "DA"): (364, 14.501, 5.645, 9.105, 2.331),
    ("ca_32.65_-115.15_UPV_75MW", "HA4"): (364, 11.539, 4.492, 6.787, -0.928),
    ("ny_41.25_-73.55_UPV_38MW", "DA"): (365, 30.812, 9.094, 12.714, -0.298),
    ("ny_41.25_-73.55_UPV_38MW", "HA4"): (365, 25.696, 7.585, 11.158, 0.120),
}


def _oku(klasor: str, dosya: str) -> pd.Series:
    df = pd.read_csv(KOK / klasor / dosya)
    t = pd.to_datetime(df["LocalTime"], format="%m/%d/%y %H:%M")
    return pd.Series(df["Power(MW)"].values, index=t).resample("h").mean()


def _kapasite(klasor: str) -> float:
    return float(klasor.split("_")[-1].rstrip("MW"))


@pytest.mark.parametrize("klasor,ufuk", sorted(REFERANS))
def test_sfa_metrikleri_referansi_yeniden_uretir(klasor, ufuk):
    cap = _kapasite(klasor)
    a = _oku(klasor, "Actual_5_Min_2006-06.csv"); f = _oku(klasor, f"{ufuk}_60_Min_2006-06.csv")
    idx = a.index.intersection(f.index); a, f = a.loc[idx], f.loc[idx]
    m = (a > 0.01 * cap) | (f > 0.01 * cap)
    h = sfa_metrik.hepsi(a[m], f[m], cap)
    n, wmape, nmae, nrmse, nmbe = REFERANS[(klasor, ufuk)]
    assert h["n"] == n
    wm = float(np.abs(f[m] - a[m]).sum() / a[m].sum() * 100)          # worker'ın WMAPE tanımı
    assert wm == pytest.approx(wmape, abs=2e-3)
    assert h["nmae"] == pytest.approx(nmae, abs=2e-3)
    assert h["nrmse"] == pytest.approx(nrmse, abs=2e-3)
    assert h["nmbe"] == pytest.approx(nmbe, abs=2e-3)


def test_ha4_da_dan_iyi_ve_kova_skorlari_calisir():
    """NREL bulgusu: 4 saat öncesi tahmin gün-öncesinden daha iyi (kısa ufkun değeri). Worker'ın gün+kova
    hesabı da aynı veriyle çalışır ve günlük WMAPE ortalaması havuzlanmış değerin ±6 puanında kalır."""
    for klasor in {k for k, _ in REFERANS}:
        assert REFERANS[(klasor, "HA4")][1] < REFERANS[(klasor, "DA")][1]
    klasor = "az_31.85_-110.85_UPV_100MW"; cap_kw = 100_000.0
    a = _oku(klasor, "Actual_5_Min_2006-06.csv") * 1000; f = _oku(klasor, "DA_60_Min_2006-06.csv") * 1000
    idx = a.index.intersection(f.index)
    df = pd.DataFrame({"ts_utc": idx.tz_localize("UTC"), "gun": idx.date, "kova": "0-24",
                       "power_kw": a.loc[idx].values, "p50_kw": f.loc[idx].values, "naif": np.nan})
    df = df[df.power_kw > 0.02 * cap_kw]
    satirlar = kova_skorlari(df, cap_kw, "t", "p")
    assert len(satirlar) == 30
    gunluk_ort = float(np.mean([r["m"] for r in satirlar]))
    assert abs(gunluk_ort - REFERANS[(klasor, "DA")][1]) < 6.0
    assert all(r["na"] is not None and r["nr"] is not None for r in satirlar)
