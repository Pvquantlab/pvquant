"""v2.71-C: egim/azimut metni - kunye ile Kalibrasyon ayni seyi soyler."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.reporting.styles import egim_azimut_metni  # noqa: E402


def test_bos_kayit_varsayilan_der():
    """Konya vakasi: tilt bos -> varsayilan kullanildigi soylenir."""
    m = egim_azimut_metni(None, None)
    assert "varsayılan" in m
    assert "20°" in m and "180°" in m


def test_dolu_kayit_gercek_degeri_der():
    assert egim_azimut_metni(25, 180) == "25° / 180° (santral kaydı)"


def test_azimut_sifir_korunur():
    """azimuth=0 (kuzey) gecerlidir - 'or 180' tuzagina dusulmez."""
    assert egim_azimut_metni(25, 0) == "25° / 0° (santral kaydı)"


def test_azimut_yoksa_180_varsayilir():
    assert egim_azimut_metni(30, None) == "30° / 180° (santral kaydı)"


def test_model_buldu_ifadesi_hicbir_dalda_gecmez():
    """Bekci: model fit etmedigi surece bu cumle geri gelmemeli."""
    for tilt, az in ((None, None), (25, 180), (25, 0), (30, None)):
        assert "model buldu" not in egim_azimut_metni(tilt, az)
