"""v2.154: doldur() dürüst hata — boş token sessiz TypeError yerine adını söyler.

Eski davranış "replace() argument 2 must be str, not None" idi: hangi alanın
boş olduğu görünmüyordu (canlıda ayıklaması pahalı). Fikstür üreticinin
kendisidir: gerçek doldur, gerçek modül globali (geçici mutasyon + finally).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reporting" / "html"))
import veri  # noqa: E402


def test_kanonik_doldur_calisir():
    assert "{{" not in veri.doldur("a {{SANTRAL}} b {{DONEM}}")


def test_none_token_adiyla_soylenir():
    eski = veri.NARR_S07_BASLIK
    veri.NARR_S07_BASLIK = None
    try:
        with pytest.raises(ValueError, match=r"\{\{NARR_S07_BASLIK\}\}.*None"):
            veri.doldur("x {{NARR_S07_BASLIK}} y")
    finally:
        veri.NARR_S07_BASLIK = eski


def test_yanlis_tip_adi_ve_tipiyle_soylenir():
    eski = veri.NARR_S07_BASLIK
    veri.NARR_S07_BASLIK = 42
    try:
        with pytest.raises(ValueError, match=r"\{\{NARR_S07_BASLIK\}\}.*int"):
            veri.doldur("x")            # metinde geçmese de bekçi tüm D'yi tarar
    finally:
        veri.NARR_S07_BASLIK = eski
