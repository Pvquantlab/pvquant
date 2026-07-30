"""v2.71-D: Tahminler alt yazisi secili ufku soyler - 168 sabit degil."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.reporting.styles import ufuk_alt_yazisi  # noqa: E402

UFUKLAR = {"24s": 24, "72s": 72, "7g": 168, "16g": 384}   # tahminler.py ile ayni


def test_yedi_gun_168_der():
    assert ufuk_alt_yazisi(168).startswith("168 saatlik")


def test_onalti_gun_384_der():
    """v2.69 sonrasi 16g sekmesinde 168 yaziyordu - kusurun tam kendisi."""
    m = ufuk_alt_yazisi(384)
    assert m.startswith("384 saatlik")
    assert "168" not in m


def test_kisa_ufuklar_da_dogru():
    assert ufuk_alt_yazisi(24).startswith("24 saatlik")
    assert ufuk_alt_yazisi(72).startswith("72 saatlik")


def test_dort_sekmenin_dordu_de_farkli_metin():
    """Sabit metin dordunu ayni yapiyordu."""
    metinler = {ufuk_alt_yazisi(s) for s in UFUKLAR.values()}
    assert len(metinler) == 4


def test_cumle_kuyrugu_korunur():
    assert ufuk_alt_yazisi(168).endswith("arşivden, son koşu.")
