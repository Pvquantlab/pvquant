"""G2-C1 (24.11.2026) — kalibrasyon penceresi (C2-1), Mod B kalite kapısı (C2-8), panel teknolojisi eşlemesi (C2-2),
CQR «tire ilkesi» geri düşüşü (C2-4). Saf testler; DB yok."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.services import calib_service as cs
from pvquant.services.konformal_service import q_hat_hesapla_df


# ── C2-1 pencere ───────────────────────────────────────────────────────────────
def _df(bas: str, n: int, tz="UTC") -> pd.DataFrame:
    ix = pd.date_range(bas, periods=n, freq="h", tz=tz)
    return pd.DataFrame({"power_kw": np.arange(n, dtype=float)}, index=ix)


def test_pencere_arsiv_kesiminden_once_satir_birakmaz():
    once = _df("2024-12-31", 48)
    sonra = _df("2026-10-05", 48)
    df = pd.concat([once, sonra])
    out = cs.kalibrasyon_penceresi(df)   # varsayılan kesim: acik_nwp.ARSIV_KESIM_UTC (02.10.2026 06:00)
    from pvquant.io.acik_nwp import ARSIV_KESIM_UTC
    assert len(out) == 48 and out.index.min() >= ARSIV_KESIM_UTC and out["power_kw"].iloc[0] == 0.0


def test_pencere_kesim_sonrasi_veri_aynen_ve_tzsiz_index():
    df = _df("2026-10-10", 24, tz=None)
    out = cs.kalibrasyon_penceresi(df, kesim=pd.Timestamp("2026-10-02 06:00"))
    assert len(out) == 24 and out.equals(df)
    assert cs.kalibrasyon_penceresi(df.iloc[0:0]).empty and cs.kalibrasyon_penceresi(None) is None


def test_pencere_kesim_parametresi():
    df = _df("2026-10-01", 72)
    out = cs.kalibrasyon_penceresi(df, kesim=pd.Timestamp("2026-10-02 06:00", tz="UTC"))
    assert out.index.min() == pd.Timestamp("2026-10-02 06:00", tz="UTC") and len(out) == 72 - 30


# ── C2-8 Mod B kapısı ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("n,holdout,sapma,gecer,imza", [
    (8, None, -98.6, False, "gündüz saati"),          # Format Lab vakası: kör B
    (450, None, 5.0, False, "holdout"),                # holdout hesaplanamadı → kanıtsız
    (450, float("nan"), 5.0, False, "holdout"),
    (450, 24.0, 35.0, False, "sapma"),                 # uydurma sonrası sapma tavan üstü
    (450, 24.0, None, False, "sapma"),
    (450, 24.0, -5.0, True, "geçti"),
    (100, 30.0, 30.0, True, "geçti"),                  # sınırlar dâhil
    (99, 30.0, 0.0, False, "gündüz saati"),
])
def test_mod_b_kapisi(n, holdout, sapma, gecer, imza):
    ok, neden = cs.mod_b_kapisi(n, holdout, sapma)
    assert ok is gecer and imza in neden


def test_kapi_sabitleri_pinli():
    assert cs.MOD_B_ASGARI_SAAT == 100 and cs.MOD_B_SAPMA_TAVAN_PCT == 30.0


# ── C2-2 panel teknolojisi ─────────────────────────────────────────────────────
@pytest.mark.parametrize("girdi,beklenen", [("monofacial", "mono"), ("mono", "mono"), ("Monofacial ", "mono"), ("bifacial", "bifacial"),
                                            ("thin_film", "thin_film"), (None, "bifacial"), ("", "bifacial"), ("bilinmeyen", "bifacial")])
def test_panel_teknolojisi_eslemesi(girdi, beklenen):
    assert cs.panel_teknolojisi(girdi) == beklenen


def test_panel_spec_monofacial_artik_dogrulamadan_gecer():
    from pvquant.models_v2.contracts import PanelSpec
    PanelSpec(technology=cs.panel_teknolojisi("monofacial"), nominal_power_w=545, temperature_coefficient_gamma=-0.34)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):   # eski yol: ham 'monofacial' Literal'e uymaz — kusurun kanıtı
        PanelSpec(technology="monofacial", nominal_power_w=545, temperature_coefficient_gamma=-0.34)


def test_hibrit_profil_bf_yalniz_bifacial():
    from pvquant.pipeline import hybrid_ui
    ctx = {"capacity_kwp": 1000.0, "latitude": 37.9, "longitude": 32.5, "timezone": "Europe/Istanbul", "tilt": 20, "azimuth": 180}
    mono = hybrid_ui._plant_profile({**ctx, "panel_technology": "mono"}, "t")
    bif = hybrid_ui._plant_profile({**ctx, "panel_technology": "bifacial"}, "t")
    assert mono.panel.technology == "mono" and mono.panel.bifaciality_factor is None
    assert bif.panel.technology == "bifacial" and bif.panel.bifaciality_factor == 0.7


# ── C2-4 CQR geri düşüşü ──────────────────────────────────────────────────────
def test_cqr_hicbir_saat_20_degilse_genel_q_ile_doner():
    """Kova ≥ min_toplam satır, 24 saat × 7 gün (her saat 7 < 20) → eskiden ValueError, şimdi yalnız `_genel` q̂."""
    ix = pd.date_range("2026-10-01", periods=24 * 7, freq="h", tz="UTC")
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"ts_utc": ix, "power_kw": 500.0 + rng.normal(0, 40, len(ix)), "p10": 420.0, "p90": 580.0,
                       "ufuk_saat": (np.arange(len(ix)) % 23) + 0.5})
    ayar = q_hat_hesapla_df(df, capacity_kwp=1000.0)
    assert ayar is not None and ayar["grup"] == "saat_ufuk"
    assert ayar["q_hat"]["0-24"].keys() == {"_genel"} and np.isfinite(ayar["q_hat"]["0-24"]["_genel"])
    assert "_genel" in ayar["q_hat"] and np.isfinite(ayar["ort_q"])
