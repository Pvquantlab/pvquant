"""v2.71-B: bant sutunu - baslik ile hucre ayni siradan."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.reporting.styles import BANT_BASLIK, bant_araligi  # noqa: E402


def test_baslik_dusukten_yuksege():
    """Once P10, sonra P90 - hucrenin sirasi bu."""
    assert BANT_BASLIK.startswith("P10")
    assert BANT_BASLIK.index("P10") < BANT_BASLIK.index("P90")


def test_hucre_once_alt_sonra_ust():
    """29.076 - 33.287: kucuk olan basta."""
    assert bant_araligi(29076.0, 33287.0) == "29.076 - 33.287"


def test_baslik_ve_hucre_ayni_siralamada():
    """Basliktaki ilk etiket, hucredeki ilk sayiya karsilik gelir."""
    alt, ust = 100.0, 900.0
    ilk_sayi = float(bant_araligi(alt, ust).split(" - ")[0])
    ilk_etiket = BANT_BASLIK.split("-")[0]
    assert (ilk_etiket == "P10") == (ilk_sayi == alt)
    assert ilk_sayi == alt


def test_turkce_binlik_ayraci_korunur():
    """sayi_tr gecisi bozulmadi - K4."""
    assert bant_araligi(1234.0, 5678.0) == "1.234 - 5.678"
