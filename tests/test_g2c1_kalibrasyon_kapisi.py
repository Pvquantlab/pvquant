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
                                            ("thin_film", "thin_film"), (None, "mono"), ("", "mono"), ("bilinmeyen", "mono")])   # G4-P0: beyansız → mono
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


def test_kalibre_et_kapi_dusunce_db_yazmaz(monkeypatch):
    """QA C1-M06: kapı düşerse `kalibre_et` 'atlandi' döner ve `tenant_baglami`'ye HİÇ girmez (kayıt yok, aktif ayar korunur)."""
    from types import SimpleNamespace
    ix = pd.date_range("2026-10-05", periods=240, freq="h", tz="UTC")
    scada = SimpleNamespace(power_kw=pd.Series(100.0, index=ix), energy_kwh=None, poa_irradiance=None, temp_ambient=None,
                            temp_module=None, wind_speed=None, plant_name="t", timestep_minutes=60)
    cr = SimpleNamespace(eta_bos=0.9, bg=0.1, warnings=[], n_valid_hours=8, plant=None,
                         validation_after=SimpleNamespace(total_deviation_pct=-98.6, mape_pct=99.0, wmape_pct=99.0),
                         validation_before=SimpleNamespace(total_deviation_pct=-99.0, mape_pct=99.0, wmape_pct=99.0))
    monkeypatch.setattr(cs, "_scada_data", lambda t, p: scada)
    monkeypatch.setattr(cs, "_meteo", lambda p, i: SimpleNamespace(kaynak="test"))
    monkeypatch.setattr(cs, "calibrate_from_scada", lambda **kw: cr)
    monkeypatch.setattr(cs, "_kronolojik_holdout", lambda *a, **k: {"wmape_holdout_pct": None, "holdout_not": "yetersiz"})
    def _yasak(*a, **k):
        raise AssertionError("kapı düştü ama DB işlemine girildi")
    monkeypatch.setattr(cs, "tenant_baglami", _yasak)
    r = cs.kalibre_et("t", {"id": "p", "name": "t", "capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5, "tz": "UTC"}, hibrit=False)
    assert r["mode"] == "atlandi" and r["calibration_id"] is None and "gündüz saati" in r["kapi"]


# ── G4-P0 panel beyanı ──────────────────────────────────────────────────
def test_g4p0_beyansiz_panel_mono_ve_bf_yok():
    """Beyansız/bilinmeyen panel bifacial kazancı almaz; beyanlı bifacial değişmez; bilgi fonksiyonu beyanı söyler."""
    assert cs.panel_teknolojisi_bilgi(None) == ("mono", False) and cs.panel_teknolojisi_bilgi("Unknown") == ("mono", False)
    assert cs.panel_teknolojisi_bilgi("bifacial") == ("bifacial", True) and cs.panel_teknolojisi_bilgi(" Monofacial") == ("mono", True)
    from pvquant.pipeline.hybrid_ui import _plant_profile as _pp
    ctx = {"capacity_kwp": 1000.0, "latitude": 37.0, "longitude": 33.0, "tilt": 25.0, "azimuth": 180.0}
    assert _pp({**ctx}).panel.bifaciality_factor is None and _pp({**ctx}).panel.technology == "mono"
    assert _pp({**ctx, "panel_technology": "bifacial"}).panel.bifaciality_factor == 0.7
