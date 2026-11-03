"""03.11.2026 doğrulama arşivi (~/Desktop/PVQuant_Kapsamli_Dogrulama_Arastirmasi) A kanıtlı bulguların koda yansıması — v2.529.
DK-249: 1.1.2025 öncesi DSG üye eşiği yok (m.111(3)-(5) RG 17.12.2024-32755 Md.24/30). DK-154: 2024 ve öncesi KGÜP kesimi D-1 16:00
(RG 14.04.2009-27200 m.69(1)), 1.1.2025'ten 15:30. DK-044 / DK-002: etiketler lafzî yürürlük ve çıkarımı söyler."""
from datetime import date

import numpy as np
import pandas as pd

from pvquant.ext.turkiye import dengesizlik as d
from pvquant.ext.turkiye import kurallar as kr
from pvquant.services import dengesizlik_service as ds


def test_dsg_esigi_2025_oncesi_yok():
    e, day = kr.dsg_esigi(date(2024, 12, 31))
    assert e is None and "üye eşiği yok" in day
    assert kr.dsg_esigi(date(2025, 1, 1))[0] == 0.10 and kr.dsg_esigi(date(2026, 1, 1))[0] == 0.05
    t = {r["gecerlilik_bas"]: r for r in kr.tablo("lisansli_serbest")}
    assert t["2023-01-01"]["dsg_esik"] is None and t["2025-01-01"]["dsg_esik"] == 0.10
    assert kr.parametre_cercevesi(pd.date_range("2024-12-30 20:00", periods=4, freq="h", tz="UTC"))["dsg_esik"].isna().all()   # İstanbul 30–31.12.2024


def _dsg(gun: str):
    idx = pd.date_range(f"{gun} 06:00", periods=6, freq="h", tz="UTC")
    ptf = pd.Series(2000.0, index=idx); smf = pd.Series(2000.0, index=idx)
    prog = {"u1": pd.Series(10.0, index=idx), "u2": pd.Series(10.0, index=idx)}
    ger = {"u1": pd.Series(12.0, index=idx), "u2": pd.Series(8.0, index=idx)}      # +2 / −2 MWh: tam netleşirse grup EDM 0
    return d.dsg_saatlik(prog, ger, ptf, smf, yon="dengede", segmentler={"u1": "lisansli_serbest", "u2": "lisansli_serbest"})


def test_dsg_netlesme_2024_esiksiz_2025_esikli():
    r24 = _dsg("2024-06-01"); sa = r24["saatlik"]
    assert sa["esik"].isna().all() and "üye eşiği yok" in r24["esik_kaynak"]
    assert np.allclose(sa["edt_bireysel"], 0.0) and np.allclose(sa["edt_grup"], 0.0)     # tamamı grupta netleşti
    assert not np.allclose(sa["edt_tek"], 0.0)                                            # tek başına olsaydı maliyet vardı
    r25 = _dsg("2025-06-01"); sb = r25["saatlik"]
    assert (sb["esik"] == 0.10).all()
    assert not np.allclose(sb["edt_bireysel"], 0.0)                                       # %10 × PH = 1,2 MWh netleşir, 0,8 MWh bireysel kalır
    assert "tamamen netleşir" in ds._esik_cumlesi(None) and "%10 × PH" in ds._esik_cumlesi(0.10)


def test_kgup_kesim_tarihli():
    assert kr.kgup_kesim(date(2024, 12, 31))[0] == (16, 0) and "16:00" in kr.kgup_kesim(date(2024, 12, 31))[1]
    assert kr.kgup_kesim(date(2025, 1, 1))[0] == (15, 30) and kr.kgup_kesim(date(2026, 11, 3))[0] == (15, 30)


def test_etiketler_lafzi_yururluk_ve_cikarim():
    assert "lafzen 1.8.2023" in kr.afl_dayanak(date(2023, 7, 4)) and kr.afl(date(2023, 7, 4)) == 2700.0
    assert "1.11.2026 çıkarım" in kr.edt_kurali(date(2026, 11, 1)).dayanak
    assert "çıkarım" in kr.kupst_kurali(date(2026, 11, 1), "lisansli_serbest").dayanak
    assert "çıkarım" not in kr.edt_kurali(date(2026, 10, 31)).dayanak
