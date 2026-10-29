"""v2.276 — DSG netleştirmesi (SAF) + gün içi tazeleme (monkeypatch) + kapı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.io import acik_nwp
from pvquant.services import dengesizlik_service as dz


def _prog(sapma_kw):
    ix = pd.date_range("2026-08-01", periods=48, freq="h", tz="UTC")
    g = np.full(48, 1000.0)
    return pd.DataFrame({"ts_utc": ix, "gercek_kw": g, "kgup_kw": g - sapma_kw, "naif_kw": np.nan})


def test_dsg_netlesme():
    fiyat = pd.DataFrame({"ptf": 2000.0, "smf": 2500.0, "kaynak": "senaryo"}, index=pd.date_range("2026-08-01", periods=48, freq="h", tz="UTC"))
    # v2.502 (F-08): yürürlükteki kural — yalnız eşik (Ağustos 2026: %5 × PH) kadarı netleşir; A fazla / B açık tam netleşmez
    r = dz.dsg_hesapla_df({"A": _prog(+200), "B": _prog(-200)}, fiyat, segmentler={"A": "lisansli_serbest", "B": "lisansli_serbest"})
    assert r["santral"] == 2 and r["ayri_tl"] > r["net_tl"] > 0 and r["kazanc_tl"] == r["ayri_tl"] - r["net_tl"] and r["esik"] == 0.05
    assert r["gosterge"] is False and r["kupst_uye_tl"] is not None and r["netlesme_farki_tl"] > 0 and r["disi"] == []
    # eşik: A için PH = max(1,0; 0,8) = 1,0 → grup +0,05; B için PH = max(1,0; 1,2) = 1,2 → grup −0,06; grup net −0,01 MWh/saat × 48 = 0,48 → 0,5
    assert r["sapma_net_mwh"] == 0.5 and r["sapma_ayri_mwh"] == 19.2
    tek = dz.dsg_hesapla_df({"A": _prog(+200)}, fiyat, segmentler={"A": "lisansli_serbest"})
    assert tek["kazanc_tl"] == 0                                                  # tek santral: netleşme yok
    disi = dz.dsg_hesapla_df({"A": _prog(+200), "B": _prog(-200)}, fiyat, segmentler={"A": "lisansli_serbest", "B": "lisanssiz_dagitim"})
    assert disi["disi"] == ["B"] and disi["santral"] == 1                        # dengesizlik taşımayan üye portföy dışı
    assert dz.dsg_hesapla_df({}, fiyat)["ayri_tl"] is None
    assert dz.dsg_hesapla_df({"A": _prog(100).iloc[:10], "B": _prog(50)}, fiyat)["not"] == "ortak saat yetersiz"


def test_gun_ici_tazele(monkeypatch, tmp_path):
    ix = pd.date_range("2026-09-06", periods=240, freq="h", tz="UTC")
    e = pd.DataFrame({"ghi": 300.0, "dni": 200.0, "dhi": 100.0, "temp_air": 25.0, "wind_speed_10m": 2.0, "cloud_cover": 10.0, "precipitation": 0.0, "relative_humidity": 40.0}, index=ix)
    i = pd.DataFrame({"ghi": 500.0, "dni": 300.0, "dhi": 150.0, "temp_air": 27.0, "wind_speed_10m": 3.0, "cloud_cover": 5.0}, index=ix[12:132])
    i_kosu = pd.Timestamp("2026-09-06 12:00", tz="UTC")
    monkeypatch.setattr(acik_nwp, "icon_indir", lambda dizin=None, kosu=None: (tmp_path, i_kosu))
    monkeypatch.setattr(acik_nwp, "icon_noktalar", lambda kd, n: {(37.87, 32.49): i})
    monkeypatch.setattr(acik_nwp, "_arsivden_son_kosu_df", lambda la, lo: (e, pd.Timestamp("2026-09-06 06:00", tz="UTC")))
    yazilan = {}
    monkeypatch.setattr(acik_nwp, "_arsive_yaz", lambda rows: yazilan.setdefault("rows", rows) and len(rows))
    monkeypatch.setattr(acik_nwp, "eski_temizle", lambda d, t=2: [])
    r = acik_nwp.gun_ici_tazele([(37.87, 32.49)], tmp_path)
    rows = yazilan["rows"]
    assert r["satir"] == len(rows) == 240 and rows[0]["z"] == i_kosu.to_pydatetime()     # ufuk ECMWF omurgasıyla korunur
    assert abs(rows[200]["temp_air"] - 25.0) < 1e-6 and rows[50]["temp_air"] > 25.0        # ICON dışı saatler omurga, içi harman
    monkeypatch.setattr(acik_nwp, "_arsivden_son_kosu_df", lambda la, lo: (e, pd.Timestamp("2026-09-06 15:00", tz="UTC")))
    r2 = acik_nwp.gun_ici_tazele([(37.87, 32.49)], tmp_path)
    assert r2["satir"] == 0 and "atlandı" in r2["hata"][0]                                   # daha yeni arşiv varsa yazılmaz


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    monkeypatch.setattr(dz, "dsg_ozet", lambda t, gun=30, dagitim_anahtari="sapma": {"santral": 1, "n_saat": 100, "ayri_tl": 10.0, "net_tl": 10.0, "kazanc_tl": 0.0, "pencere_gun": gun, "dagitim_anahtari": dagitim_anahtari, "fiyat": {"epias_saat": 0, "senaryo_saat": 100}, "not": "tek"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_dsg_kapisi(istemci):
    assert istemci.get("/v1/portfoy/dsg?gun=45").json()["pencere_gun"] == 45
    assert istemci.get("/v1/portfoy/dsg?gun=5").status_code == 422
    # 29.10: dağıtım anahtarı kapısı — geçerli değer servise iletilir, geçersiz 422
    assert istemci.get("/v1/portfoy/dsg?gun=30&anahtar=uretim").json()["dagitim_anahtari"] == "uretim"
    assert istemci.get("/v1/portfoy/dsg?gun=30&anahtar=yanlis").status_code == 422


def test_dsg_dagitim_anahtari():
    """29.10 — grubun EDT'si üyelere anahtarla paylaştırılır; her anahtarda Σ üye = grup (edt_dsg ve netleşme farkı), paylar Σ=1."""
    from pvquant.ext.turkiye import dengesizlik as d
    fiyat = pd.DataFrame({"ptf": 2000.0, "smf": 2500.0, "kaynak": "senaryo"}, index=pd.date_range("2026-08-01", periods=48, freq="h", tz="UTC"))
    prog = {"A": _prog(+200), "B": _prog(-200), "C": _prog(+50)}; seg = {k: "lisansli_serbest" for k in prog}
    for anahtar in d.DAGITIM_ANAHTARLARI:
        r = dz.dsg_hesapla_df(prog, fiyat, segmentler=seg, dagitim_anahtari=anahtar)
        u = r["uyeler"]
        assert r["dagitim_anahtari"] == anahtar and r["dagitim_etiket"] == d.DAGITIM_ETIKET[anahtar]
        assert abs(sum(v["edt_dsg_tl"] for v in u.values()) - r["edt_dsg_tl"]) <= 2          # yuvarlama payı (üye başına 0 ondalık)
        assert abs(sum(v["netlesme_farki_tl"] for v in u.values()) - r["netlesme_farki_tl"]) <= 2
        assert abs(sum(v["pay_pct"] for v in u.values()) - 100) <= 0.3
        for v in u.values():
            assert abs(v["edt_dsg_tl"] - v["edt_tek_tl"] - v["netlesme_farki_tl"]) <= 1
    esit = dz.dsg_hesapla_df(prog, fiyat, segmentler=seg, dagitim_anahtari="esit")["uyeler"]
    assert all(abs(v["pay_pct"] - 33.3) <= 0.1 for v in esit.values())
    uretim = dz.dsg_hesapla_df(prog, fiyat, segmentler=seg, dagitim_anahtari="uretim")["uyeler"]
    assert all(abs(v["pay_pct"] - 33.3) <= 0.1 for v in uretim.values())              # üç üye de 1 MW üretiyor → eşit
    sapma = dz.dsg_hesapla_df(prog, fiyat, segmentler=seg, dagitim_anahtari="sapma")["uyeler"]
    assert sapma["B"]["pay_pct"] > sapma["C"]["pay_pct"]                                  # |grup payı| B (0,06) > C (0,05×1,0) → B'nin payı büyük
    with pytest.raises(ValueError):
        dz.dsg_hesapla_df(prog, fiyat, segmentler=seg, dagitim_anahtari="x")
