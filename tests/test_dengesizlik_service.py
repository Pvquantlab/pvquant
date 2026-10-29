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
    r = hesapla_df(df, f, segment="lisansli_serbest")          # 2025 Temmuz–Ağustos → 2025 rejimi; senaryo fiyat, yön varsayımı
    assert r["gun_sayisi"] == 45 and [a["ay"] for a in r["aylar"]] == ["2025-07", "2025-08"]
    assert r["toplam"]["kurtarilan_tl"] > 0 and 0 < r["toplam"]["gelir_oran_pct"] < 5 and r["fiyat"]["senaryo_saat"] == len(f)
    assert r["fiyat"]["yon_varsayilan_saat"] == len(f) and r["fiyat"]["yon_eksik_saat"] == 0 and r["hesaplanamayan_saat"] == 0
    assert all(a["naif_tl"] > a["pvquant_tl"] for a in r["aylar"])
    # EDT ve KÜPST ayrı; toplam = kayıp + KÜPST; kural sürümü etiketi dolu
    for a in r["aylar"]:
        assert a["kupst_tl"] is not None and a["edt_neg_tl"] is not None and a["edta_tl"] is not None
        assert abs(a["pvquant_tl"] - (a["dengesizlik_tl"] + a["kupst_tl"])) <= 1.0 and a["kural_surumu"] == "edt-2025+kupst-13025"
    assert r["kural_surumu"] == "edt-2025+kupst-13025"
    # segment yoksa KÜPST ve toplam None (0 değil), kayıp yine hesaplanır
    r0 = hesapla_df(df, f)
    assert r0["toplam"]["kupst_tl"] is None and r0["toplam"]["pvquant_tl"] is None and r0["toplam"]["dengesizlik_tl"] > 0
    assert r0["hesaplanamayan_saat"] == len(f)


def test_2026_epias_yon_eksik_saat_hesaplanmaz():
    ts = pd.date_range("2026-06-01", periods=48, freq="h", tz="Europe/Istanbul").tz_convert("UTC")
    df = pd.DataFrame({"ts_utc": ts, "gercek_kw": 800.0, "kgup_kw": 1000.0, "naif_kw": np.nan})
    yon = ["Enerji Açığı"] * 24 + [None] * 24
    f = pd.DataFrame({"ptf": 2000.0, "smf": 2500.0, "yon": yon, "kaynak": "epias"}, index=ts)
    r = hesapla_df(df, f, segment="lisansli_serbest")
    assert r["fiyat"]["yon_eksik_saat"] == 24 and r["hesaplanamayan_saat"] == 24 and r["fiyat"]["yon_varsayilan_saat"] == 0
    a = r["aylar"][0]
    # 24 saat × 0,2 MWh × P(−) = max(150, 2000, 2500) × 1,06 = 2.650 → EDT(−) 12.720; eksik saatler 0 sayılmaz (toplam yalnız hesaplanan saatlerden)
    assert a["edt_neg_tl"] == pytest.approx(24 * 0.2 * 2650, abs=0.5) and a["hesaplanamayan_saat"] == 24 and a["kural_surumu"] == "edt-2026-V150-edta_net+kupst-14029"


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
    yon = np.where(np.arange(200) % 2 == 0, "acik", "fazla")           # yön EPİAŞ sütunundan; SMF>PTF'den çıkarılmaz
    f = pd.DataFrame({"ptf": 2500.0, "smf": smf, "yon": yon, "kaynak": "epias"}, index=ix)
    r = dz.oneri_kantili(f)
    assert r["durum"] == "ok" and r["acik_saat_orani"] == 0.5
    # 2026 kuralı (bugün): c_eksik = max(V, 2500, 3000)·1,06 − 2500 = 680; c_fazla = 2500 − 2000·0,94 = 620 → τ ≈ 0,477 → p50
    assert abs(r["tau"] - 620 / (680 + 620)) < 1e-3 and r["kantil"] == "p50"
    assert dz.oneri_kantili(f.drop(columns=["yon"]))["durum"] == "yon_eksik"
    agir = pd.DataFrame({"ptf": 2500.0, "smf": 4000.0, "yon": "acik", "kaynak": "epias"}, index=ix)   # hep açık, eksik üretim pahalı
    assert dz.oneri_kantili(agir)["kantil"] in ("p10", "p25")
    sen = pd.DataFrame({"ptf": 2651.81, "smf": 2524.09, "kaynak": "senaryo"}, index=ix)
    assert dz.oneri_kantili(sen) == {"durum": "senaryo", "kantil": None, "not": dz.oneri_kantili(sen)["not"]}
    assert dz.oneri_kantili(pd.DataFrame())["durum"] == "veri_yok"
    # teminat: negatif gider yoğun ay tavan olur
    g = pd.DataFrame({"ts_utc": ix, "gercek_kw": 800.0, "kgup_kw": 1000.0, "naif_kw": np.nan})
    out = dz.hesapla_df(g, f, segment="lisansli_serbest")
    assert out["toplam"]["teminat_tl"] > 0
