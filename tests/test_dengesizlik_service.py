"""v2.259 — dengesizlik_service.hesapla_df (SAF) + segment bilgisi + /dengesizlik kapısı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import piyasa_service as ps
from pvquant.services.dengesizlik_service import hesapla_df, segment_bilgisi

PLANT = "22222222-2222-2222-2222-222222222222"


def _df(gun=45, seed=0):
    ts = pd.date_range("2025-07-01", periods=24 * gun, freq="h", tz="Europe/Istanbul").tz_convert("UTC"); rng = np.random.default_rng(seed)
    g = np.clip(np.sin((np.asarray(ts.tz_convert("Europe/Istanbul").hour) - 6) / 12 * np.pi), 0, None)
    ger = 10000 * g * rng.uniform(0.5, 1.0, len(ts))
    kg = ger * (1 + rng.normal(0, 0.08, len(ts)))
    naif = pd.Series(ger).shift(24).values
    return pd.DataFrame({"ts_utc": ts, "gercek_kw": ger, "kgup_kw": kg, "naif_kw": naif})


def test_hesapla_pvquant_naiften_ucuz_ve_aylar_istanbul():
    df = _df(); f = ps.senaryo_fiyat(pd.DatetimeIndex(df.ts_utc))
    r = hesapla_df(df, f)
    assert r["gun_sayisi"] == 45 and [a["ay"] for a in r["aylar"]] == ["2025-07", "2025-08"]
    assert r["toplam"]["kurtarilan_tl"] > 0 and 0 < r["toplam"]["gelir_oran_pct"] < 5 and r["fiyat"]["senaryo_saat"] == len(f)
    assert all(a["naif_tl"] > a["pvquant_tl"] for a in r["aylar"])


def test_bos_ve_eksik():
    assert hesapla_df(pd.DataFrame(), pd.DataFrame())["gun_sayisi"] == 0
    df = _df(gun=3); df["kgup_kw"] = np.nan
    assert hesapla_df(df, ps.senaryo_fiyat(pd.DatetimeIndex(df.ts_utc)))["gun_sayisi"] == 0


def test_segment_bilgisi():
    s = segment_bilgisi({"segment": "lisanssiz_dagitim"}); assert s["santral_tasir"] is False and s["kgup_yukumlu"] is False
    s2 = segment_bilgisi('{"segment": "lisansli_serbest"}'); assert s2["santral_tasir"] is True and s2["kgup_yukumlu"] is True
    assert segment_bilgisi(None)["segment"] is None and segment_bilgisi({"segment": "yok"})["segment"] is None


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service, dengesizlik_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {"segment": "lisansli_serbest"}})
    monkeypatch.setattr(dengesizlik_service, "simulasyon", lambda t, pl, gun=90: {"gun_sayisi": 30, "toplam": {"kurtarilan_tl": 1234.0}, "pencere_gun": gun})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapi(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/dengesizlik?gun=60").json()["toplam"]["kurtarilan_tl"] == 1234.0
    assert istemci.get(f"/v1/plants/{PLANT}/dengesizlik?gun=5").status_code == 422


def test_oneri_kantili_ve_teminat():
    """v2.287: gazeteci-çocuk kuralı — eksik cezası ağırsa düşük kantil; senaryo fiyatta dürüst tire; teminat toplam blokta."""
    import numpy as np
    import pandas as pd
    from pvquant.services import dengesizlik_service as dz
    ix = pd.date_range("2026-08-01", periods=200, freq="h", tz="UTC")
    # yarı yarıya yön: açıkta SMF 3000 (pahalı geri alım), fazlada 2000
    smf = np.where(np.arange(200) % 2 == 0, 3000.0, 2000.0)
    f = pd.DataFrame({"ptf": 2500.0, "smf": smf, "kaynak": "epias"}, index=ix)
    r = dz.oneri_kantili(f)
    assert r["durum"] == "ok" and r["acik_saat_orani"] == 0.5
    # c_eksik = 3000·1,03−2500 = 590; c_fazla = 2500−2000·0,97 = 560 → τ ≈ 0,487 → p50
    assert abs(r["tau"] - 560 / (590 + 560)) < 1e-3 and r["kantil"] == "p50"
    agir = pd.DataFrame({"ptf": 2500.0, "smf": 4000.0, "kaynak": "epias"}, index=ix)   # hep açık, ceza ağır
    assert dz.oneri_kantili(agir)["kantil"] in ("p10", "p25")
    sen = pd.DataFrame({"ptf": 2651.81, "smf": 2524.09, "kaynak": "senaryo"}, index=ix)
    assert dz.oneri_kantili(sen) == {"durum": "senaryo", "kantil": None, "not": dz.oneri_kantili(sen)["not"]}
    assert dz.oneri_kantili(pd.DataFrame())["durum"] == "veri_yok"
    # teminat: negatif gider yoğun ay tavan olur
    g = pd.DataFrame({"ts_utc": ix, "gercek_kw": 800.0, "kgup_kw": 1000.0, "naif_kw": np.nan})
    out = dz.hesapla_df(g, f)
    assert out["toplam"]["teminat_tl"] > 0
