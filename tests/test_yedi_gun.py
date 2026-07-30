"""v2.71: 7 gunluk KPI/grafik dilimi - v2.69 ufku 384 saate cikinca
dilimsiz toplam 16 gunu topluyordu (kart 'kayan 7 gun' diyordu).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.services.ozet_service import yedi_gun_serisi  # noqa: E402


def _gunluk(gun_sayisi: int, mwh: float = 30.0) -> pd.Series:
    """gun_sayisi kadar dolu yerel gun iceren gunluk MWh serisi."""
    idx = pd.date_range("2026-07-30", periods=gun_sayisi, freq="D").date
    return pd.Series([mwh] * gun_sayisi, index=idx)


def test_onalti_gunluk_kosu_yediye_kirpilir():
    """v2.69 ufku: 17 dolu gun gelse de kart 7 gun gostermeli."""
    s = yedi_gun_serisi(_gunluk(17))
    assert len(s) == 7
    assert float(s.sum()) == 210.0


def test_kisa_kosu_bozulmaz():
    """4 gunluk kosuda kirpma yapilmaz - eldeki kadarini dondurur."""
    s = yedi_gun_serisi(_gunluk(4))
    assert len(s) == 4


def test_sifir_gunler_once_dusulur():
    """Sifir-kuyruk gunler (v2.16 F2) sayima girmez."""
    ham = _gunluk(9)
    ham.iloc[0] = 0.0
    ham.iloc[-1] = 0.0
    s = yedi_gun_serisi(ham)
    assert len(s) == 7
    assert (s > 0).all()


def test_sira_korunur():
    """Kirpma bastan yapilir - en buyuk 7 gun degil, ILK 7 gun."""
    ham = _gunluk(10)
    ham.iloc[8] = 99.0
    s = yedi_gun_serisi(ham)
    assert 99.0 not in list(s.values)
