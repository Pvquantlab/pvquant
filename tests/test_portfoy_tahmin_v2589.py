"""v2.589 (Faz 3 F3-B, DB) — portföy tahmin servisi: zamanlı üyelikle santral kümesi, «son» ve «gün öncesi» koşu seçimi, hizalama, ρ, tazelik,
günlük/dönem bantları, kapsama sınavı ve yalnız-ekleme kaydı (dogrulama_sonuc, plant_id NULL), kiracı izolasyonu, tahminsiz üye."""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami, bakim_baglami
from pvquant.services import portfoy_tahmin_service as pt
from pvquant.services import portfoy_varlik_service as pv

TZ = "Europe/Istanbul"; Z = 1.2816; BUGUN = date(2026, 9, 11)
KAPS = {"A": 1000.0, "B": 700.0, "C": 1300.0}


def _profil(kap, idx):
    h = idx.tz_convert(TZ).hour.values
    return 0.85 * kap * np.clip(np.sin((h - 6) / 12 * np.pi), 0, None) * ((h >= 6) & (h <= 18))


@pytest.fixture()
def portfoy():
    tid, tid2 = str(uuid.uuid4()), str(uuid.uuid4())
    pl = {ad: str(uuid.uuid4()) for ad in ("A", "B", "C", "D")}
    rng = np.random.default_rng(3)
    idx = pd.date_range(pd.Timestamp("2026-08-01", tz=TZ), pd.Timestamp("2026-09-13", tz=TZ), freq="h", inclusive="left").tz_convert("UTC")   # 43 gün
    C = np.full((3, 3), 0.5); np.fill_diagonal(C, 1.0); z = rng.standard_normal((len(idx), 3)) @ np.linalg.cholesky(C).T
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'pt-test', 'active'), (:t2, 'pt-test-2', 'active')"), {"t": tid, "t2": tid2})
        for ad, pid in pl.items():
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :ad, :kap, :lat, 32.0, :tz, '{\"segment\": \"lisansli_serbest\"}')"),
                      {"p": pid, "t": tid, "ad": f"GES {ad}", "kap": KAPS.get(ad, 500.0), "lat": 37.0 + 0.05 * list(pl).index(ad), "tz": TZ})
        for i, ad in enumerate(("A", "B", "C")):
            kap = KAPS[ad]; p50 = _profil(kap, idx); sig = 0.12 * p50; e = z[:, i] * sig; y = np.clip(p50 - e, 0, None)
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, 'valid', 60)"),
                      [{"t": tid, "p": pl[ad], "ts": t.to_pydatetime(), "kw": float(v)} for t, v in zip(idx, y, strict=True) if t < pd.Timestamp(BUGUN, tz=TZ)])
            gunler = pd.DatetimeIndex(idx.tz_convert(TZ).normalize().unique())
            for g in gunler:   # gün öncesi koşu: D−1 18:00 UTC, D gününü kapsar
                ra = (g - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=18)
                rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"),
                                {"t": tid, "p": pl[ad], "ra": ra.to_pydatetime()}).scalar()
                m = (idx >= g.tz_convert("UTC")) & (idx < (g + pd.Timedelta(days=1)).tz_convert("UTC"))
                s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90)"),
                          [{"t": tid, "r": rid, "p": pl[ad], "ts": t.to_pydatetime(), "p50": float(a), "p10": float(max(a - Z * b, 0)), "p90": float(min(a + Z * b, kap))}
                           for t, a, b in zip(idx[m], p50[m], sig[m], strict=True)])
            # «son» koşu: bugün 04:00 UTC, bugün + yarın
            ra = pd.Timestamp(BUGUN, tz="UTC") + pd.Timedelta(hours=4)
            rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"),
                            {"t": tid, "p": pl[ad], "ra": ra.to_pydatetime()}).scalar()
            m = idx >= pd.Timestamp(BUGUN, tz=TZ).tz_convert("UTC")
            s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90)"),
                      [{"t": tid, "r": rid, "p": pl[ad], "ts": t.to_pydatetime(), "p50": float(a), "p10": float(max(a - Z * b, 0)), "p90": float(min(a + Z * b, kap))}
                       for t, a, b in zip(idx[m], p50[m], sig[m], strict=True)])
    pid = pv.portfoy_ekle(tid, "Toplayıcı T", "toplayici", "2026-01-01")
    pv.uyelik_ekle(tid, pid, pl["A"], "2026-01-01"); pv.uyelik_ekle(tid, pid, pl["B"], "2026-01-01")
    pv.uyelik_ekle(tid, pid, pl["C"], "2026-09-05"); pv.uyelik_ekle(tid, pid, pl["D"], "2026-01-01")   # C sonradan katılır; D'nin tahmini yok
    yield tid, tid2, pid, pl
    with bakim_baglami() as s:
        for t in ("dogrulama_sonuc", "portfoy_sonuc", "portfoy_uyelik", "toplayici_kapsami", "portfoy", "denetim_izi", "forecast_values", "forecast_runs", "scada_hourly", "plants"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id IN (:t, :t2)"), {"t": tid, "t2": tid2})
        s.execute(text("DELETE FROM tenants WHERE id IN (:t, :t2)"), {"t": tid, "t2": tid2})


def test_db_saatlik_kapsama_kayit_izolasyon(portfoy):
    tid, tid2, pid, pl = portfoy
    # zamanlı üyelik: 1 Eylül'de C yok
    assert [p["name"] for p in pt.santraller(tid, pid, date(2026, 9, 1))] == ["GES A", "GES B", "GES D"]
    o = pt.saatlik(tid, pid, kural="son", bugun=BUGUN)
    assert o["durum"] == "ok" and o["santral"] == 4 and o["tahmin_yok"] == ["GES D"] and sorted(o["katkilar"]) == ["GES A", "GES B", "GES C"]
    assert o["pencere"]["n_saat"] == 48 and o["kapasite_kwp"] == 3000.0 and o["tazelik"]["fark_saat"] == 0.0 and o["tazelik"]["farkli_yayin"] is False
    assert o["korelasyon"]["durum"] == "yeterli" and o["korelasyon"]["n_gun"] >= 30 and o["belirsizlik"]["durum"] == "dogrulanmadi" and o["belirsizlik"]["kapsama"] is None
    r = o["korelasyon"]["rho"]; off = [r[a][b] for a in r for b in r if a != b]
    assert 0.25 < float(np.mean(off)) < 0.75
    assert abs(sum(k["pay_pct"] for k in o["katkilar"].values()) - 100) < 0.2 and o["katkilar"]["GES C"]["uyelik"]["gecerli_bas"] == "2026-09-05"
    s = pd.DataFrame(o["saatlik"]); g = s[s["p50_kw"] > 0]
    assert (g["p10_kw"] <= g["p50_kw"]).all() and (g["p50_kw"] <= g["p90_kw"]).all() and (g["p10_naif_kw"] <= g["p10_kw"]).all() and not s["eksik"].any()
    assert len(o["gunluk"]) == 2 and o["gunluk_meta"]["durum"] == "ampirik" and o["gunluk"][0]["gun"] == "2026-09-11"
    # gün öncesi kuralı da aynı saat kümesini verir (bugün için koşu D−1 18:00 UTC)
    o2 = pt.saatlik(tid, pid, kural="gun_oncesi", bugun=BUGUN)
    assert o2["durum"] == "ok" and o2["pencere"]["n_saat"] == 48 and o2["kural_ad"] == "Gün öncesi tahmin"
    # günler + dönem bantları
    gl = pt.gunler(tid, pid, gun=2, bugun=BUGUN)
    assert gl["donem_bantlari"]["hafta"] and gl["donem_bantlari"]["ay"] and gl["donem_bantlari"]["hafta"]["q10_mwh"] < 0 < gl["donem_bantlari"]["hafta"]["q90_mwh"]
    # kapsama sınavı (30 gün) → kayıt → son → saatlik durumu güncellenir
    k = pt.kapsama(tid, pid, gun=30, bugun=BUGUN)
    m = k["metrik"]
    assert k["durum"] == "ok" and m["n_gun"] == 30 and 70 <= m["picp80"] <= 90 and m["durum"] == "dogrulandi" and k["tahmin_yok"] == ["GES D"]
    assert k["karsilastirma"]["naif"]["picp80"] >= m["picp80"] and k["meta"]["uyelik_pencerede_degisti"] is True and len(k["meta"]["uyelik_anlik"]) == 4
    kid = pt.kapsama_kaydet(tid, pid, k)
    son = pt.son_kapsama(tid, pid)
    assert son and son["id"] == kid and son["meta"]["portfoy_id"] == pid and son["metrik"]["picp80"] == m["picp80"] and son["kayitli"]
    with tenant_baglami(tid) as s_:
        assert s_.execute(text("SELECT count(*) FROM dogrulama_sonuc WHERE plant_id IS NULL AND kural = 'portfoy_gun_oncesi'")).scalar() == 1
    o3 = pt.saatlik(tid, pid, kural="son", bugun=BUGUN)
    assert o3["belirsizlik"]["durum"] == "dogrulandi" and o3["belirsizlik"]["kapsama"]["picp80"] == m["picp80"] and o3["belirsizlik"]["durum_ad"] == "Doğrulandı"
    # izolasyon
    assert pt.son_kapsama(tid2, pid) is None and pt.saatlik(tid2, pid, bugun=BUGUN)["durum"] == "uye_yok" and pt.kapsama(tid2, pid, bugun=BUGUN)["durum"] == "uye_yok"
    with pytest.raises(ValueError):
        pt.kapsama_kaydet(tid2, pid, pt.kapsama(tid2, pid, bugun=BUGUN))
    with pytest.raises(ValueError):
        pt.tahmin_sec(tid, {"id": pl["A"], "tz": TZ}, None, None, "yok")
