"""v2.597 (Faz 4 F4-A) — orkestratör ayrımı ve M2 düzeltmesi (DB'siz).

- `uret_ve_kaydet` = meteo çek → `girdileri_topla` → `tahmin_uret` → `arsive_yaz` (bileşim; her parça yerine konabilir).
- M2: hibrit artefakt yüklü ama predict patlarsa künye C/hybrid_residual YAZILMAZ: B / barhdadi_bennis / ml_model_id None /
  konformal atlanır / geri_dusus='hibrit_basarisiz'. Hibrit başarılıysa C kalır, ml_kw dolu, konformal uygulanır.
- `plant_spec_kur` tek kaynak: eski `_plant_spec` kalibrasyonsuz hâlle birebir; kalibre katsayılar doğru yuvaya.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_altin_cekirdek import KALIBRASYON, PLANT, _meteo  # noqa: E402

from pvquant.services import ensemble_service as es  # noqa: E402
from pvquant.services import forecast_service as fs  # noqa: E402
from pvquant.services.calib_service import _plant_spec  # noqa: E402
from pvquant.services.plant_spec_service import plant_spec_kur  # noqa: E402


class _PatlayanModel:
    def predict(self, *a, **k):
        raise RuntimeError("artefakt bozuk")


@pytest.fixture(autouse=True)
def _bant_kapali(monkeypatch):
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="model", ensemble_min_uye=20))


def _girdi(**k) -> fs.TahminGirdisi:
    temel = dict(mode="C", kalibrasyon_id="kal-1", kalibrasyon_params=KALIBRASYON, ml_model_id="ml-1", model=_PatlayanModel(),
                 konformal_ayar={"grup": "saat", "q_hat": {"_genel": 10.0}, "hesap_zamani": "2026-06-20T03:00:00+00:00"},
                 sapma_ayar={"aktif": False, "neden": "test"})
    temel.update(k)
    return fs.TahminGirdisi(**temel)


def test_m2_hibrit_basarisiz_kunye_b_ve_konformal_atlanir():
    s = fs.tahmin_uret(PLANT, _meteo(), _girdi(), simdi=pd.Timestamp("2026-06-21", tz="UTC"))
    assert (s.mode, s.model_adi, s.ml_model_id, s.geri_dusus, s.konformal_ayar) == ("B", "barhdadi_bennis", None, "hibrit_basarisiz", None)
    h = s.h
    assert h["ml_kw"].isna().all() and np.allclose(h["p50_kw"], h["physics_kw"])
    assert h["p10_kw"].isna().all() and h["p10_ham_kw"].isna().all()   # bant yok (model kaynağı, A/B) — konformal q̂ uygulanmadı


def test_hibrit_basarili_c_kalir_ml_kw_dolu_konformal_uygulanir(monkeypatch):
    def _hh(model, meteo):
        ix = meteo.ghi.index
        p50 = pd.Series(np.clip(700.0 * np.sin(np.pi * (np.arange(len(ix)) % 24 - 3.5) / 13.0), 0, None), index=ix)
        return pd.DataFrame({"p50_kw": p50, "p10_kw": p50 * 0.8, "p90_kw": p50 * 1.2})
    monkeypatch.setattr(fs, "hybrid_forecast_hourly", _hh)
    s = fs.tahmin_uret(PLANT, _meteo(), _girdi(model=object()), simdi=pd.Timestamp("2026-06-21", tz="UTC"))
    assert (s.mode, s.model_adi, s.ml_model_id, s.geri_dusus) == ("C", "hybrid_residual", "ml-1", None)
    assert s.konformal_ayar is not None
    h = s.h; gunduz = h["p50_kw"] > 0
    assert h.loc[gunduz, "ml_kw"].notna().all() and not np.allclose(h.loc[gunduz, "p50_kw"], h.loc[gunduz, "physics_kw"])
    assert (h.loc[gunduz, "p10_kw"] <= h.loc[gunduz, "p10_ham_kw"] - 9.0).all()   # q̂=10 ham bandı genişletti (p10 ≥ 0 kırpması hariç)
    assert (h["p90_kw"].dropna() <= 900.0 + 1e-9).all()


def test_mod_c_ama_model_yok_b_ve_artefakt_yok_etiketi():
    s = fs.tahmin_uret(PLANT, _meteo(), _girdi(model=None, ml_model_id=None, geri_dusus="hibrit_artefakt_yok"), simdi=pd.Timestamp("2026-06-21", tz="UTC"))
    assert (s.mode, s.ml_model_id, s.geri_dusus, s.konformal_ayar) == ("B", None, "hibrit_artefakt_yok", None)


def test_uret_ve_kaydet_bilesimi(monkeypatch):
    class _Stub:
        def get_forecast(self, latitude, longitude, days):
            assert (latitude, longitude) == (PLANT["lat"], PLANT["lon"]) and days == 15
            return _meteo()
    monkeypatch.setattr(fs, "OpenMeteoClient", _Stub)
    monkeypatch.setattr(fs, "get_settings", lambda: SimpleNamespace(forecast_horizon_days=15))
    girdi_ = _girdi(mode="B", model=None, ml_model_id=None, konformal_ayar=None)
    goruldu = {}
    monkeypatch.setattr(fs, "girdileri_topla", lambda t, p, d: goruldu.setdefault("topla", (t, p["id"], d)) and girdi_)
    def _yaz(t, p, meteo, sonuc, kalibrasyon_id=None, etiket=None, girdi=None):
        goruldu["yaz"] = (t, kalibrasyon_id, etiket, sonuc.mode, int(len(sonuc.h)))
        assert girdi is girdi_   # v2.597: künye için girdi arşive geçer
        return "run-1"
    monkeypatch.setattr(fs, "arsive_yaz", _yaz)
    assert fs.uret_ve_kaydet("t1", PLANT, etiket="elle") == "run-1"
    assert goruldu["topla"] == ("t1", "altin-ges", 15) and goruldu["yaz"] == ("t1", "kal-1", "elle", "B", 72)


def test_plant_spec_kur_tek_kaynak_eski_adla_birebir():
    p = {**PLANT, "params_json": '{"iam_model": "physical", "izleyici": "tek_eksen", "izleyici_gcr": "0.4"}'}
    a, b = _plant_spec(p), plant_spec_kur(p)
    assert a == b and a.iam_model == "physical" and a.izleyici == "tek_eksen" and a.izleyici_gcr == 0.4 and a.eta_bos == 0.93
    k = plant_spec_kur(p, '{"eta_bos": 0.88, "bg": 0.2}')
    assert (k.eta_bos, k.bifacial_gain_geometric, k.bifacial_factor) == (0.88, 0.2, 0.7)   # bg GEOMETRİK BG'ye, BF teknolojiden
    assert plant_spec_kur(p, {"eta_bos": None, "bg": None}).eta_bos == 0.93
    assert plant_spec_kur({**p, "params_json": "{bozuk"}).iam_model == "none"
