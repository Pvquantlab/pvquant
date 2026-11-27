"""Faz 1 ticari hazırlık — C1 (belgeli γ adapter) ve D4 (etkin tavan şüphesi uyarısı) regresyonları (28.11.2026).
Formül/parametre/eşik değişmedi: C1 yalnız params_json.gamma_pdc varsa PlantSpec.gamma_pdc'yi doldurur; D4 yalnız uyarı metni ekler."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.io.ingestion.validate import etkin_tavan_suphesi, validate
from pvquant.services.plant_spec_service import gamma_pdc_oku, plant_spec_kur

PLANT = {"capacity_kwp": 4738.0, "lat": 40.3864, "lon": -104.5512, "tilt": 0.0, "azimuth": 180.0, "panel_tech": "thin_film",
         "ac_limit_kw": 3820.0, "params_json": {"izleyici": "tek_eksen"}}


# ----------------------------------------------------------------------------- C1
def test_c1_gamma_yoksa_eski_yol_birebir():
    s = plant_spec_kur(PLANT)
    assert s.gamma_pdc is None and s.effective_gamma == -0.0040
    assert s.izleyici == "tek_eksen" and s.module_tech == "mono_si" and s.bifacial_factor == 0.0   # thin_film → otomatik eşleme YOK


def test_c1_belgeli_gamma_params_json_ile_islenir():
    p = dict(PLANT, params_json={"izleyici": "tek_eksen", "gamma_pdc": -0.0028})
    s = plant_spec_kur(p)
    assert s.gamma_pdc == -0.0028 and s.effective_gamma == -0.0028
    s2 = plant_spec_kur(dict(PLANT, params_json='{"gamma_pdc": "-0.0022"}'))      # JSON metni + sayısal metin
    assert s2.effective_gamma == -0.0022


def test_c1_gecersiz_gamma_sessizce_varsayilan():
    for v in (-0.28, 0.0, 0.004, "abc", None, True, float("nan"), -0.5):
        assert gamma_pdc_oku(v) is None, v
        assert plant_spec_kur(dict(PLANT, params_json={"gamma_pdc": v})).effective_gamma == -0.0040
    assert gamma_pdc_oku(-0.0028) == -0.0028 and gamma_pdc_oku("-0.0045") == -0.0045


def test_c1_kalibrasyon_parametreleri_gammaya_dokunmaz():
    s = plant_spec_kur(dict(PLANT, params_json={"gamma_pdc": -0.0028}), {"eta_bos": 0.8, "bg": 0.3})
    assert s.eta_bos == 0.8 and s.bifacial_gain_geometric == 0.3 and s.effective_gamma == -0.0028


# ----------------------------------------------------------------------------- D4
def _seri(tavan_kw: float | None, kwp: float = 4738.0, gun: int = 365) -> pd.Series:
    t = pd.date_range("2022-01-01", periods=gun * 24, freq="h", tz="UTC")
    saat = np.array(t.hour) + 0.5
    cane = np.clip(np.sin(np.pi * (saat - 12.0) / 14.0), 0, None) ** 1.3           # 12–26 UTC ≈ gündüz (Colorado)
    mevsim = 0.9 + 0.1 * np.cos(2 * np.pi * (np.array(t.dayofyear) - 172) / 365)
    p = kwp * 1.0 * cane * mevsim * (0.92 + 0.08 * np.sin(np.arange(len(t)) / 7.0))     # DC/AC 1,24: yaz öğlesi 3 820 üstüne çıkar
    if tavan_kw is not None:
        p = np.minimum(p, tavan_kw + np.sin(np.arange(len(t))) * 0.0007 * tavan_kw)   # 3 500 ± 2,5 kW dalgalı plato (9068 imzası)
    return pd.Series(np.clip(p, 0, None), index=t)


def test_d4_ac_altinda_plato_supheli_uyari():
    s = _seri(3500.0)
    r = etkin_tavan_suphesi(s, 4738.0, 3820.0)
    assert r is not None and abs(r["p99_kw"] - 3500) < 15 and r["yigin_oran"] >= 0.05 and r["oran_ac"] < 0.95
    df = pd.DataFrame({"power_kw": s})
    df.index.name = "ts_utc"
    out, rep = validate(df, capacity_kwp=4738.0, latitude=40.3864, longitude=-104.5512, ac_limit_kw=3820.0)
    assert any("Etkin tavan şüphesi" in w for w in rep.warnings)
    assert "frozen_value" not in out["flag"].value_counts()                           # dalgalı plato donmuş sayılmaz


def test_d4_negatif_kontroller_uyari_yok():
    # (a) çan biçimli, tavansız seri — plato yok
    assert etkin_tavan_suphesi(_seri(None), 4738.0, 3820.0) is None
    # (b) kırpma AC'nin %97'sinde — kırpma platosu, şüphe DEĞİL (mevcut muafiyet yolu)
    assert etkin_tavan_suphesi(_seri(0.97 * 3820.0), 4738.0, 3820.0) is None
    # (c) AC bilinmiyor → kural koşmaz; (d) günlük özet → koşmaz; (e) yetersiz veri → koşmaz
    assert etkin_tavan_suphesi(_seri(3500.0), 4738.0, None) is None
    assert etkin_tavan_suphesi(_seri(3500.0), 4738.0, 3820.0, gunluk_ozet=True) is None
    assert etkin_tavan_suphesi(_seri(3500.0, gun=10), 4738.0, 3820.0) is None
    df = pd.DataFrame({"power_kw": _seri(None)})
    df.index.name = "ts_utc"
    _, rep = validate(df, capacity_kwp=4738.0, latitude=40.3864, longitude=-104.5512, ac_limit_kw=3820.0)
    assert not any("Etkin tavan" in w for w in rep.warnings)
