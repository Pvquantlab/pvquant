"""26.11.2026 — hibrit altyapı hatası (run_hybrid_training ok=False) sessiz Mod B düşüşü olmaz: gate.hata=True, sebep öneki,
sonuc.hibrit_hata; kapı reddi (ok=True, iyileşme yetersiz) hata DEĞİLDİR; aylık iş yapılı sonuç döner ve durum semantiği korunur."""
from types import SimpleNamespace

from pvquant.services import calib_service as cs


def _cr():
    v = SimpleNamespace(mape_pct=10.0, wmape_pct=9.0, total_deviation_pct=0.5)
    return SimpleNamespace(eta_bos=0.9, bg=0.3, warnings=[], notes=[], n_valid_hours=800, validation_after=v, validation_before=v, plant=None)


def _hazirla(monkeypatch, res):
    scada = SimpleNamespace(power_kw=__import__("pandas").Series([1.0, 2.0], index=__import__("pandas").date_range("2026-01-01", periods=2, freq="1h", tz="UTC")),
                            poa_irradiance=None, temp_module=None, temp_ambient=None, wind_speed=None, energy_kwh=None)
    monkeypatch.setattr(cs, "_scada_data", lambda t, p: scada)
    monkeypatch.setattr(cs, "_meteo", lambda p, i: SimpleNamespace(kaynak="test"))
    monkeypatch.setattr(cs, "calibrate_from_scada", lambda **kw: _cr())
    monkeypatch.setattr(cs, "_kronolojik_holdout", lambda *a, **k: {"wmape_holdout_pct": None, "holdout_not": "yetersiz"})   # Mod B kapısı düşer → DB'ye yazılmaz
    monkeypatch.setattr(cs, "run_hybrid_training", lambda **kw: res)

    def _yasak(*a, **k):
        raise AssertionError("DB'ye yazılmamalı")
    monkeypatch.setattr(cs, "tenant_baglami", _yasak)
    return cs.kalibre_et("t", {"id": "p", "name": "t", "capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5, "tz": "UTC"}, hibrit=True)


def test_hibrit_istisnasi_gorunur_ve_mod_c_olmaz(monkeypatch):
    res = SimpleNamespace(ok=False, error="ValidationError: 1 validation error for PanelSpec technology", improvement_pct=None,
                          holdout_mape_pct=None, physics_mape_pct=None, holdout_wmape_pct=None, physics_wmape_pct=None)
    r = _hazirla(monkeypatch, res)
    assert r["mode"] == "atlandi" and r["gate"]["denendi"] and r["gate"]["gecti"] is False
    assert r["gate"]["hata"] is True and r["gate"]["sebep"].startswith("hibrit DENENEMEDİ") and "ValidationError" in r["gate"]["sebep"]
    assert r["hibrit_hata"].startswith("ValidationError")


def test_kapi_reddi_hata_degil(monkeypatch):
    res = SimpleNamespace(ok=True, error=None, improvement_pct=1.0, holdout_mape_pct=20.0, physics_mape_pct=20.5,
                          holdout_wmape_pct=18.0, physics_wmape_pct=18.2, coverage_p10_p90_pct=None, band_width_mean_kw=None, band_width_pct_of_p50=None)
    r = _hazirla(monkeypatch, res)
    assert r["gate"]["gecti"] is False and r["gate"]["hata"] is False and "iyilesme" in r["gate"]["sebep"] and r["hibrit_hata"] is None


def test_aylik_is_yapili_sonuc_ve_durum(monkeypatch):
    import apps.worker.main as w
    monkeypatch.setattr(w.ingest_service if hasattr(w, "ingest_service") else __import__("pvquant.services.ingest_service", fromlist=["x"]),
                        "veri_ozeti", lambda t, p: {"son_ts": None})
    monkeypatch.setattr(w.calib_service, "kalibrasyon_bayat_mi", lambda ts: (False, ""))
    plant = {"tenant_id": "t", "id": "p", "name": "P"}
    monkeypatch.setattr(w.calib_service, "kalibre_et", lambda t, p, hibrit=True: {"mode": "B", "calibration_id": "c1", "eta_bos": 0.9,
                                                                                   "gate": {"denendi": True, "gecti": False, "hata": True, "sebep": "hibrit DENENEMEDİ: X"}, "hibrit_hata": "X"})
    s = w.aylik_kalibrasyon(plant)
    assert isinstance(s, dict) and s["durum"] == "ok" and s["hibrit_hata"] == "X" and "hibrit DENENEMEDİ: X" in s["mesaj"] and w._is_durumu(s, str(s)) == "ok"
    monkeypatch.setattr(w.calib_service, "kalibre_et", lambda t, p, hibrit=True: {"mode": "atlandi", "kapi": "n<100", "gate": None, "hibrit_hata": None})
    s2 = w.aylik_kalibrasyon(plant)
    assert s2["durum"] == "atlandi" and w._is_durumu(s2, str(s2)) == "atlandi" and "hibrit denenmedi" in s2["mesaj"]
