"""v2.70: kova_etiketle sinir durusmasi — 7-16g kovasi dogru ayrilir."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.worker.main import kova_etiketle  # noqa: E402


def test_dort_kova_sinirlari():
    s = pd.Series([1, 24, 25, 72, 73, 168, 169, 383])
    beklenen = ["0-24", "0-24", "24-72", "24-72",
                "72-168", "72-168", "168+", "168+"]
    assert list(kova_etiketle(s).astype(str)) == beklenen


def test_eski_uc_kova_ayni_kalir():
    """0-24 ve 24-72 etiketleri degismedi — alarm servisi '0-24' okur."""
    s = pd.Series([12, 48])
    assert list(kova_etiketle(s).astype(str)) == ["0-24", "24-72"]
