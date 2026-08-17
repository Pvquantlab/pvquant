"""C-3 (v2.150): s03 KPI kopya metnindeki hedef iddiası KPI_ESIK'ten türer.

Sözleşme testleri üreticiden beslenir (v2.149 dersi): beklenen metinler
elle değil, kanonik KPI_ESIK'in kendisinden doğrulanır; mutasyon denetimi
fonksiyonun sözlüğü GERÇEKTEN okuduğunu kanıtlar (sabit dönüş yakalanır).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reporting" / "html"))
import veri  # noqa: E402


def test_kanonik_metinler_birebir():
    """Kanonik eşiklerle md5 kalkanının beklediği metinler üretilir."""
    assert veri.kpi_hedef("WMAPE120") == "hedef %10 altı"
    assert veri.kpi_hedef("HOLDOUT") == "hedef %10 altı"
    assert veri.kpi_hedef("KAPSAMA") == "hedef %80 üstü"


def test_kanonik_esik_sozlugunden_turetilir():
    """Beklenen metin, KPI_ESIK'in kendisinden kurulur — elle yazılmaz."""
    for ad, (e, yon) in veri.KPI_ESIK.items():
        m = veri.kpi_hedef(ad)
        assert ("%g" % e).replace(".", ",") in m
        assert m.endswith("altı" if yon == "alt" else "üstü")
        assert m.startswith("hedef %")


def test_mutasyon_esigi_izler():
    """Eşik değişirse kopya izler: sabit dönüş bu testte yakalanır."""
    assert veri.kpi_hedef("WMAPE120", {"WMAPE120": (12.0, "alt")}) == "hedef %12 altı"
    assert veri.kpi_hedef("KAPSAMA", {"KAPSAMA": (75.0, "ust")}) == "hedef %75 üstü"
    assert veri.kpi_hedef("X", {"X": (12.5, "alt")}) == "hedef %12,5 altı"
