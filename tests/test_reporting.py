"""pvquant.reporting testleri — Tur 3.

Dört düzeltmeyi kilitler + üç formatın uçtan uca üretimini doğrular.
Ağ erişimi YOK: sentetik ForecastResult benzeri nesne kullanılır.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from pvquant.reporting import (
    ReportContext, from_results, build_pdf, build_excel, build_json,
)


# ----------------------------------------------------------------- fixtures
def _sentetik_forecast(saat=168, tilt=30.0):
    """168 saatlik UTC forecast — gerçek pipeline çıktısının biçimi."""
    idx = pd.date_range("2026-07-14 00:00", periods=saat, freq="1h", tz="UTC")
    saat_ici = idx.tz_convert("Europe/Istanbul").hour.values
    gunes = np.clip(np.sin((saat_ici - 5) / 14 * np.pi), 0, None)
    p_ac = gunes * 3800.0
    hourly = pd.DataFrame({
        "poa": gunes * 1050,
        "temp_cell": 25 + 25 * gunes,
        "p_dc_kw": p_ac * 1.03,
        "p_ac_kw": p_ac,
        "energy_kwh": p_ac,
    }, index=idx)
    plant = SimpleNamespace(
        p_nom_kwp=4514.0, latitude=37.87, longitude=32.49,
        tilt=tilt, azimuth=180.0,
    )
    meta = {"power_model": "barhdadi_bennis", "meteo_source": "open-meteo"}
    return SimpleNamespace(hourly=hourly, plant=plant, meta=meta)


def _sentetik_calibration(warnings=None):
    va = SimpleNamespace(mape_pct=27.5, deviation_pct=-3.23)
    return SimpleNamespace(
        eta_bos=0.897, bg=0.151, validation_after=va,
        warnings=warnings if warnings is not None else [],
    )


# ----------------------------------------------------------------- düzeltme 2+3
def test_yedi_gun_yedi_bar_168_saat():
    """UTC forecast 168 saat -> tam 7 günlük grup; 8. gün DOĞMAZ."""
    fr = _sentetik_forecast(saat=168)
    ctx = from_results(fr, None, plant_name="Test", plant_tz="Europe/Istanbul")
    assert len(ctx.daily_kwh) == 7, f"7 gün beklenir, {len(ctx.daily_kwh)} çıktı"
    assert len(ctx.hourly) == 168
    # son gün sıfıra yakın taşma OLMAMALI
    assert ctx.daily_kwh.iloc[-1] > ctx.daily_kwh.max() * 0.3


def test_gun_sayisi_kpi_ile_tutarli():
    fr = _sentetik_forecast(saat=168)
    ctx = from_results(fr, None, plant_name="Test")
    assert len(ctx.daily_kwh) == 7        # "P50 · 7 gün" KPI'ı buradan


# ----------------------------------------------------------------- düzeltme 1
def test_ad_plant_context_name_anahtarindan():
    fr = _sentetik_forecast()
    ctx = from_results(fr, None, plant_context={"name": "Konya GES"})
    assert ctx.plant_name == "Konya GES"


def test_ad_plant_context_plant_name_anahtarindan():
    fr = _sentetik_forecast()
    ctx = from_results(fr, None, plant_context={"plant_name": "Referans GES"})
    assert ctx.plant_name == "Referans GES"


def test_ad_acik_arguman_context_i_ezer():
    fr = _sentetik_forecast()
    ctx = from_results(fr, None, plant_name="Açık Ad",
                       plant_context={"name": "Context Ad"})
    assert ctx.plant_name == "Açık Ad"


def test_ad_bos_context_son_care():
    fr = _sentetik_forecast()
    ctx = from_results(fr, None, plant_context={})
    assert ctx.plant_name == "Santral"


# ----------------------------------------------------------------- düzeltme 4
def test_uyarilar_context_e_tasiniyor():
    fr = _sentetik_forecast()
    cr = _sentetik_calibration(warnings=["POA birim düzeltmesi devrede.",
                                         "Bulutlu geçiş belirsizliği."])
    ctx = from_results(fr, cr, plant_name="Test")
    assert len(ctx.warnings) == 2
    assert "POA" in ctx.warnings[0]


def test_uyari_yoksa_liste_bos():
    fr = _sentetik_forecast()
    cr = _sentetik_calibration(warnings=[])
    ctx = from_results(fr, cr, plant_name="Test")
    assert ctx.warnings == []


# ----------------------------------------------------------------- KPI doğruluk
def test_kpi_degerleri_makul():
    fr = _sentetik_forecast()
    cr = _sentetik_calibration()
    ctx = from_results(fr, cr, plant_name="Test")
    assert ctx.total_mwh > 0
    assert 0 < ctx.capacity_factor_pct < 100
    assert ctx.specific_yield > 0
    # özgül verim = toplam kWh / kWp; kabaca total_mwh*1000/4514
    assert ctx.specific_yield == pytest.approx(
        ctx.total_kwh / 4514.0, rel=1e-6)


def test_mod_b_de_band_yok():
    fr = _sentetik_forecast()
    ctx = from_results(fr, None, plant_name="Test", mode="B")
    assert ctx.has_band is False
    assert ctx.band_mwh is None


# ----------------------------------------------------------------- format üretimi
def test_pdf_uretiliyor():
    fr = _sentetik_forecast()
    cr = _sentetik_calibration(warnings=["Test uyarısı."])
    ctx = from_results(fr, cr, plant_name="Test GES")
    pdf = build_pdf(ctx)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 5000


def test_excel_uretiliyor():
    fr = _sentetik_forecast()
    ctx = from_results(fr, _sentetik_calibration(), plant_name="Test")
    xlsx = build_excel(ctx)
    assert xlsx[:2] == b"PK"          # zip/xlsx imzası
    assert len(xlsx) > 3000


def test_json_semasi_ve_gun_sayisi():
    import json
    fr = _sentetik_forecast()
    ctx = from_results(fr, _sentetik_calibration(), plant_name="Test")
    d = json.loads(build_json(ctx))
    assert d["schema_version"] == "1.1.0"   # Tur 6: quality.hybrid eklendi (minor)
    assert len(d["daily"]) == 7           # düzeltme 2+3 JSON'da da geçerli
    assert len(d["hourly"]) == 168
    assert d["plant"]["name"] == "Test"
    assert d["hourly"][0]["ts"].endswith("Z")   # ISO 8601 UTC


# ----------------------------------------------------------------- Tur 4
def test_sayi_tr():
    from pvquant.reporting.styles import sayi_tr
    assert sayi_tr(218.9, 1) == "218,9"
    assert sayi_tr(4514, 0) == "4.514"
    assert sayi_tr(1234.5, 1) == "1.234,5"     # eski replace bug'ının kanıtı


def test_donem_tr():
    import pandas as pd
    from pvquant.reporting.styles import donem_tr
    ayni = donem_tr(pd.Timestamp("2026-07-14"), pd.Timestamp("2026-07-21"))
    assert ayni == "14 – 21 Temmuz 2026"
    gecis = donem_tr(pd.Timestamp("2026-07-28"), pd.Timestamp("2026-08-03"))
    assert gecis == "28 Temmuz – 3 Ağustos 2026"
    yil = donem_tr(pd.Timestamp("2026-12-28"), pd.Timestamp("2027-01-03"))
    assert yil == "28 Aralık 2026 – 3 Ocak 2027"


def test_normalize_plant_name():
    from pvquant.reporting.contracts import normalize_plant_name
    assert normalize_plant_name("SANTRAL_GES_yillik_SCADA") == "SANTRAL GES"
    assert normalize_plant_name("konya-ges_2025_export") == "konya ges"
    assert normalize_plant_name("Konya GES") == "Konya GES"   # temiz ad dokunulmaz
    assert normalize_plant_name("") == "Santral"


def test_fallback_ad_normalize_ediliyor():
    fr = _sentetik_forecast()
    ctx = from_results(fr, None,
                       plant_context={"name": "SANTRAL_GES_yillik_SCADA"})
    assert ctx.plant_name == "SANTRAL GES"


def test_holdout_kutusu_pdf_de():
    fr = _sentetik_forecast()
    cr = _sentetik_calibration()
    ctx = from_results(fr, cr, plant_name="Test")
    ctx.holdout_mape_pct = 18.5
    pdf = build_pdf(ctx)
    assert pdf[:4] == b"%PDF" and len(pdf) > 5000


def test_pozitif_not_n_valid_ile():
    fr = _sentetik_forecast()
    cr = _sentetik_calibration()
    cr.n_valid_hours = 4162
    ctx = from_results(fr, cr, plant_name="Test")
    assert ctx.n_valid_hours == 4162
    assert build_pdf(ctx)[:4] == b"%PDF"


# ----------------------------------------------------------------- Tur 6
def _mod_c_ctx():
    ctx = from_results(_sentetik_forecast(), _sentetik_calibration(),
                       plant_name="Test")
    session = {"hybrid_active": True, "hybrid_report": {
        "holdout_mape_pct": 17.6, "holdout_rmse_kw": 260.0,
        "physics_mape_pct": 26.8, "improvement_pct": 34.3,
        "holdout_hours": 832}}
    from pvquant.reporting import apply_hybrid_session
    return apply_hybrid_session(ctx, session)


def test_json_hybrid_block_when_mode_c():
    import json
    d = json.loads(build_json(_mod_c_ctx()))
    assert d["schema_version"] == "1.1.0"
    hy = d["quality"]["hybrid"]
    assert hy["holdout_mape_pct"] == 17.6
    assert hy["holdout_rmse_kw"] == 260.0
    assert hy["physics_mape_pct"] == 26.8
    assert hy["improvement_pct"] == 34.3
    assert hy["holdout_hours"] == 832
    assert hy["note"] is None                  # %34 > kapı eşiği %3


def test_json_no_hybrid_block_when_mode_b():
    import json
    ctx = from_results(_sentetik_forecast(), _sentetik_calibration(),
                       plant_name="Test", mode="B")
    d = json.loads(build_json(ctx))
    assert "hybrid" not in d["quality"]        # null değil, YOK


def test_excel_holdout_visible_when_mode_c():
    import zipfile, io
    xlsx = build_excel(_mod_c_ctx())
    z = zipfile.ZipFile(io.BytesIO(xlsx))
    metin = z.read("xl/sharedStrings.xml").decode("utf-8")
    assert "HOLDOUT (Mod C)" in metin
    assert "Holdout MAPE (%)" in metin         # Metadata künyesi


def test_excel_holdout_hidden_when_mode_b():
    import zipfile, io
    ctx = from_results(_sentetik_forecast(), _sentetik_calibration(),
                       plant_name="Test", mode="B")
    xlsx = build_excel(ctx)
    z = zipfile.ZipFile(io.BytesIO(xlsx))
    metin = z.read("xl/sharedStrings.xml").decode("utf-8")
    assert "HOLDOUT" not in metin


def test_json_marjinal_iyilesme_notu():
    ctx = _mod_c_ctx()
    ctx.holdout_improvement_pct = 1.8          # kapı eşiği %3 altı
    import json
    d = json.loads(build_json(ctx))
    assert "marjinal" in d["quality"]["hybrid"]["note"]
