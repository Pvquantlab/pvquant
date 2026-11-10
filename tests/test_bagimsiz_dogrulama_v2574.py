"""v2.574 (Faz 1 F1-C, Stage 4–5, test turu 1) — bağımsız doğrulama motoru: bilinen sonuçlu formüller, eksik/sıfır/yinelenen/tz/birim/bant kenarları,
koşu seçim kuralları, bilgi kümesi tutarlı referanslar; test DB'de uçtan uca hesap + yalnız-ekleme kayıt + API."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import sistem_baglami
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import olcum_uygunluk_service as ou

UTC = timezone.utc
PLANT = {"id": "p1", "name": "Test GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul"}


def _e(y, f, p10=None, p90=None, gun="2026-09-01"):
    n = len(y)
    ts = pd.date_range(f"{gun} 06:00", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"ts_utc": ts, "y": y, "p50_kw": f, "p10_kw": p10 if p10 is not None else [np.nan] * n, "p90_kw": p90 if p90 is not None else [np.nan] * n,
                         "gun": [pd.Timestamp(gun).date()] * n, "kirpma": False})


def test_metrik_bilinen_sonuc_ve_isaret():
    e = _e([100, 200, 300], [110, 190, 330], [90, 150, 250], [130, 230, 320])
    m = bd.metrikler(e, 1000.0)
    assert m["n_saat"] == 3 and m["wmape"] == round(50 / 600 * 100, 2)          # Σ|e|/Σy
    assert m["mae_kw"] == round(50 / 3, 2) and m["mbe_kw"] == 10.0 and m["nmbe"] == 1.0   # pozitif = fazla tahmin
    assert m["rmse_kw"] == round(np.sqrt((100 + 100 + 900) / 3), 2) and m["nmae"] == round(50 / 3 / 10, 2)
    assert m["enerji_sapma_kwh_gun"] == 30.0
    assert m["picp80"] == 100.0 and m["p90_ustu"] == 0.0 and m["p10_alti"] == 0.0   # gerçek üçü de bant içinde
    assert m["bant_genisligi_oran"] == round((40 + 80 + 70) / 3 / 10, 1)
    assert m["winkler_kw"] == round(np.mean([40, 80, 70]), 1)
    m2 = bd.metrikler(_e([100, 200, 300], [110, 190, 330], [90, 150, 250], [130, 230, 290]), 1000.0)
    assert m2["picp80"] == round(2 / 3 * 100, 1) and m2["p90_ustu"] == round(1 / 3 * 100, 1)   # 300 > 290
    assert m2["winkler_kw"] == round(np.mean([40, 80, 40 + (2 / 0.2) * 10]), 1)
    assert m["bias_isareti"].startswith("tahmin − gerçek")


def test_payda_yetersiz_ve_asgari_saat():
    e = _e([1, 2, 1], [5, 6, 5])
    m = bd.metrikler(e, 1000.0)
    assert m["wmape"] is None and "payda" in m["not"] and m["mae_kw"] is not None   # MAE yine verilir
    assert bd.metrikler(_e([100, 200], [100, 200]), 1000.0)["wmape"] is None


def test_gunduz_maskesi_gercek_veya_tahmin():
    d = pd.DataFrame({"y": [0, 50, 0, np.nan], "p50_kw": [0, 0, 50, 30]})
    assert list(bd.gunduz_maskesi(d, 1000.0)) == [False, True, True, True]


def test_eksik_saat_sifir_sayilmaz_ve_bant_kismi():
    iz = ou.saat_izgarasi("2026-09-01 06:00", "2026-09-01 10:00")
    olc = pd.DataFrame({"power_kw": [100, 200, 300], "energy_kwh": [100, 200, 300], "flag": "valid", "kirpma": False, "kapsama_dk": 60}, index=iz[:3])   # 09:00 yok
    saatler = ou.siniflandir(iz, olc)
    ra = pd.Timestamp("2026-08-31 03:00", tz="UTC")
    tahmin = pd.DataFrame({"ts_utc": iz, "run_at": ra, "run_id": "r1", "p50_kw": [110, 190, 330, 400], "p10_kw": [90, np.nan, 250, 300], "p90_kw": [130, np.nan, 320, 500],
                           "physics_kw": [120, 200, 340, 410], "model": "barhdadi_bennis", "meteo_source": "acik-nwp", "etiket": None})
    s = bd.hesapla_saf(tahmin, saatler, ou.dokum(saatler), PLANT, date(2026, 9, 1), date(2026, 9, 2), "gun_oncesi")
    m = s["metrik"]
    assert m["n_saat"] == 3 and m["wmape"] == round(50 / 600 * 100, 2)          # eksik 09:00 payda/paya girmedi (0 sayılsaydı WMAPE 450/600)
    assert m["bant_n"] == 2 and m["picp80"] is None                              # bant 2 saat < asgari → hesaplanmaz
    assert s["butunluk"]["gunduz_dislanan"] == {"eksik": 1} and s["butunluk"]["degerlendirilen_saat"] == 3
    assert s["referans"]["fizik"]["wmape"] == round((20 + 0 + 40) / 600 * 100, 2) and s["referans"]["fizik"]["sonuc"] == "model daha iyi"   # 10 % > 8,33 %
    assert s["referans"]["fizik"]["beceri_pct"] == round((1 - (50 / 600) / (60 / 600)) * 100, 1)
    assert s["referans"]["persistans"]["wmape"] is None   # geçmiş ölçüm yok → uydurulmaz


def test_kosu_secimi_yinelenen_saat_ve_tz_sinirlari():
    tz = "Europe/Istanbul"
    saatler = pd.date_range("2026-09-01 06:00", "2026-09-01 15:00", freq="h", tz="UTC")   # 1 Eylül İstanbul günü
    def run(rid, run_at, etiket=None, model="barhdadi_bennis", meteo="acik-nwp"):
        return pd.DataFrame({"ts_utc": saatler, "run_at": pd.Timestamp(run_at, tz="UTC"), "run_id": rid, "p50_kw": 100.0, "p10_kw": 80.0, "p90_kw": 120.0, "physics_kw": 100.0,
                             "model": model, "meteo_source": meteo, "etiket": etiket})
    t = pd.concat([run("gece", "2026-08-31 03:00"), run("gunici", "2026-08-31 09:30", "gun_ici"), run("gece_yarisi", "2026-08-31 21:30"),   # 00:30 İstanbul 1 Eylül → gün öncesi DEĞİL
                   run("backtest", "2026-08-31 02:00", model="backtest"), run("elle", "2026-08-31 11:00", "elle")], ignore_index=True)
    p = bd.kosu_sec(t, "program", tz); assert set(p["run_id"]) == {"elle"} and len(p) == len(saatler)            # kesim 15:30 İst = 12:30 UTC öncesi son koşu: elle 11:00
    g = bd.kosu_sec(t, "gun_oncesi", tz); assert set(g["run_id"]) == {"elle"} and len(g) == len(saatler)         # 21:30 UTC koşusu yerel gün başladıktan sonra
    gi = bd.kosu_sec(t, "gun_ici", tz); assert set(gi["run_id"]) == {"gunici"}
    u = bd.kosu_sec(t, "ufuk", tz); assert "backtest" not in set(u["run_id"]) and "elle" not in set(u["run_id"]) and "gunici" not in set(u["run_id"])
    assert u.groupby(["ts_utc", "kova"]).size().max() == 1                                                   # saat×kova başına tek satır
    assert bd.kosu_sec(t.iloc[0:0], "program", tz).empty
    with pytest.raises(ValueError):
        bd.kosu_sec(t, "yok", tz)


def test_persistans_bilgi_kumesi_tutarli():
    gecmis = pd.Series(np.nan, index=pd.date_range("2026-08-28", "2026-09-02", freq="h", tz="UTC"))
    gecmis[:] = 100.0
    gecmis[pd.Timestamp("2026-08-31 12:00", tz="UTC")] = 300.0   # yayından sonra ölçülmüş: kullanılmamalı
    gecmis[pd.Timestamp("2026-08-30 12:00", tz="UTC")] = 200.0   # yayından önce ölçülmüş son aynı saat
    e = pd.DataFrame({"ts_utc": [pd.Timestamp("2026-09-01 12:00", tz="UTC"), pd.Timestamp("2026-09-01 02:00", tz="UTC")],
                      "run_at": [pd.Timestamp("2026-08-31 03:00", tz="UTC")] * 2})
    p = bd.persistans(e, gecmis, 37.0, 32.0)
    assert abs(p.iloc[0] - 200.0) < 5.0 and p.iloc[0] != 300.0   # k=2 → 30 Ağu 12:00 (açık gök oranı ≈ 1; 31 Ağu değeri kullanılmaz)
    assert np.isnan(p.iloc[1])                 # 02:00 gece: açık gök 0 → NaN


def test_cliper_orneklem_disi_agirlik():
    ix = pd.date_range("2025-06-01", "2026-09-01", freq="h", tz="UTC")
    saat = ix.hour; prof = np.clip(np.sin(np.pi * (saat - 3) / 14), 0, None) * 800
    rng = np.random.default_rng(3); y = pd.Series(prof * rng.uniform(0.5, 1.0, size=len(ix)), index=ix)
    iz = ou.saat_izgarasi("2026-09-01 00:00", "2026-09-08 00:00")
    e = pd.DataFrame({"ts_utc": iz, "run_at": [pd.Timestamp(t.date(), tz="UTC") - pd.Timedelta(hours=21) for t in iz]})
    c, info = bd.cliper(e, y, datetime(2026, 9, 1, tzinfo=UTC), 37.0, 32.0)
    assert info is not None and 0.0 <= info["agirlik_persistans"] <= 1.0 and c.notna().sum() > 24
    c2, info2 = bd.cliper(e, y[y.index >= pd.Timestamp("2026-08-25", tz="UTC")], datetime(2026, 9, 1, tzinfo=UTC), 37.0, 32.0)
    assert info2 is None and c2.isna().all()   # ay×saat ≥20 gün yok → hesaplanmaz


def test_kesitler_en_zayif_ve_uretim_sinifi():
    parcalar = []
    for i in range(1, 10):
        kat = 1 + 0.1 * i   # gün ilerledikçe hata büyür; üretim de günden güne artar (üçte birlikler için)
        y = [v * i for v in (100, 200, 300, 200)]
        parcalar.append(_e(y, [v * kat for v in y], gun=f"2026-09-0{i}"))
    e = pd.concat(parcalar, ignore_index=True); e["hafta"] = "2026-W36"; e["ay"] = "2026-09"; e["mevsim"] = "sonbahar"; e["saat_yerel"] = e["ts_utc"].dt.hour
    k = bd.kesitler(e, 1000.0)
    assert [g["kesit"] for g in k["en_zayif_gunler"]] == ["2026-09-09", "2026-09-08", "2026-09-07", "2026-09-06", "2026-09-05"]
    assert k["en_zayif_gunler"][0]["wmape"] == 90.0 and len(k["gun"]) == 9 and len(k["saat"]) == 4
    assert {g["kesit"] for g in k["uretim_sinifi"]} == {"düşük üretim günleri", "orta", "yüksek üretim günleri"}


def test_meta_yeniden_uretim_ozeti():
    e = _e([100, 200, 300], [110, 190, 330]); e["run_id"] = ["r1", "r1", "r2"]
    m = bd.meta(e, e, "program", "scada", 1000.0, PLANT, date(2026, 9, 1), date(2026, 10, 1), None)
    assert m["kosu_sayisi"] == 2 and len(m["kosu_kumesi_sha"]) == 16 and m["sozluk_surumu"] == bd.SOZLUK_SURUMU and m["gunduz_orani"] == 0.02
    m2 = bd.meta(e, e, "program", "scada", 1000.0, PLANT, date(2026, 9, 1), date(2026, 10, 1), None)
    assert m2["kosu_kumesi_sha"] == m["kosu_kumesi_sha"] and m2["saat_kumesi_sha"] == m["saat_kumesi_sha"]


# ---------------------------------------------------------------- test DB
@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    tz = "Europe/Istanbul"
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'bd-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) VALUES(:p, :t, 'BD GES', 1000, 900, 37.0, 32.0, :tz, '{}')"),
                  {"p": pid, "t": tid, "tz": tz})
        # 10 gün: 1–10 Eylül 2026; gerçek 06–18 TSİ saatlik 100..600 kWh; her gün D-1 03:00 UTC koşusu (p50 = gerçek×1,1) + D-1 09:30 gün içi (×1,02)
        for g in range(1, 11):
            for h in range(6, 19):
                ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=tz).tz_convert("UTC").to_pydatetime()
                kw = 100 + 50 * min(h - 6, 18 - h)
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, :f, 60)"),
                          {"t": tid, "p": pid, "ts": ts, "kw": kw, "f": ("frozen_value" if (g == 5 and h == 12) else "valid")})
            for saat_utc, et, kat in ((3, None, 1.10), (9.5, "gun_ici", 1.02)):
                ra = (pd.Timestamp(f"2026-09-{g:02d}", tz=tz) - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=saat_utc)
                rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, etiket) "
                                     "VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', CAST(:oz AS jsonb), :et) RETURNING id"),
                                {"t": tid, "p": pid, "ra": ra.to_pydatetime(), "oz": '{"etiket": %s}' % ('"gun_ici"' if et else "null"), "et": et}).scalar()
                for h in range(0, 24):
                    ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=tz).tz_convert("UTC").to_pydatetime()
                    kw = (100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0
                    s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw, physics_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90, :ph)"),
                              {"t": tid, "r": rid, "p": pid, "ts": ts, "p50": kw * kat, "p10": kw * kat * 0.85, "p90": kw * kat * 1.15, "ph": kw * 1.2})
        s.execute(text("INSERT INTO olay(tenant_id, plant_id, tur, baslangic, bitis, durum, eak_gerekcesi) VALUES(:t, :p, 'ariza', :b, :e, 'kapali', 'kaynak_yetersizligi')"),
                  {"t": tid, "p": pid, "b": datetime(2026, 9, 3, 8, 0, tzinfo=UTC), "e": datetime(2026, 9, 3, 10, 0, tzinfo=UTC)})
    yield tid, {"id": pid, "name": "BD GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": tz, "params_json": {}, "archived": False}
    with sistem_baglami() as s:
        for t in ("dogrulama_sonuc", "olay", "forecast_values", "forecast_runs", "scada_hourly"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_db_hesapla_kaydet_son_ve_api(santral, monkeypatch):
    tid, plant = santral
    bugun = date(2026, 9, 11)
    s = bd.hesapla(tid, plant, gun=10, kural="gun_oncesi", bugun=bugun)
    m = s["metrik"]
    # gün öncesi = D 00:00 yerel öncesi SON koşu → D-1 09:30 UTC gün içi koşusu (×1,02); frozen 1 saat + arıza 2 saat dışarıda
    assert m["n_saat"] == 10 * 13 - 1 - 2 and m["wmape"] == 2.0 and m["nmbe"] > 0
    assert s["butunluk"]["gunduz_dislanan"] == {"olay:ariza": 2, "bayrak:frozen_value": 1}
    assert s["referans"]["fizik"]["wmape"] == 20.0 and s["referans"]["fizik"]["sonuc"] == "model daha iyi"
    assert s["meta"]["kosu_kunyesi"]["model"] == ["barhdadi_bennis"] and s["meta"]["kosu_sayisi"] == 10
    gi = bd.hesapla(tid, plant, gun=10, kural="gun_ici", bugun=bugun)
    assert gi["metrik"]["wmape"] == 2.0 and gi["meta"]["kosu_sayisi"] == 10
    pr = bd.hesapla(tid, plant, gun=10, kural="program", bugun=bugun)
    assert pr["metrik"]["wmape"] == 2.0   # kesim 15:30 İst öncesi son koşu = 09:30 UTC gün içi koşusu (kgup ile aynı)
    uf = bd.hesapla(tid, plant, gun=10, kural="ufuk", bugun=bugun)
    kova = {k["kesit"]: k["wmape"] for k in uf["kesit"]["ufuk"]}
    assert kova.get("24-48") == 10.0 and "0-24" not in kova   # gece koşusu (D-1 03:00 UTC) D saatlerine 24–36 s ufukla bakar; gün içi ana kovaya girmez
    kid = bd.kaydet(tid, s, plant["id"])
    son = bd.son(tid, plant["id"], "gun_oncesi", 10)
    assert son and son["id"] == kid and son["metrik"]["wmape"] == 2.0 and son["kayitli"]
    assert bd.son(tid, plant["id"], "program", 10) is None
    with sistem_baglami() as c:
        assert c.execute(text("SELECT count(*) FROM dogrulama_sonuc WHERE tenant_id=:t"), {"t": tid}).scalar() == 1
    pf = bd.portfoy(tid, [plant], gun=10, kural="gun_oncesi", bugun=bugun)
    assert pf["metrik"]["wmape"] == 2.0 and pf["kapasite_kwp"] == 1000.0 and pf["santraller"][0]["n_saat"] == m["n_saat"]
    # API: kayıtlı sonuç döner; taze=1 anında hesap; kural/gun doğrulama
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/plants/{plant['id']}/dogrulama/bagimsiz?gun=10&kural=gun_oncesi"); assert r.status_code == 200 and r.json()["kayitli"] and r.json()["id"] == kid
        monkeypatch.setattr(bd, "hesapla", lambda *a, **k: s)
        r = c.get(f"/v1/plants/{plant['id']}/dogrulama/bagimsiz?gun=10&kural=gun_oncesi&taze=1"); assert r.status_code == 200 and r.json()["kayitli"] is False
        assert c.get(f"/v1/plants/{plant['id']}/dogrulama/bagimsiz?kural=yok").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/dogrulama/bagimsiz?gun=3").status_code == 422
        assert c.get(f"/v1/plants/{uuid.uuid4()}/dogrulama/bagimsiz").status_code == 404
    finally:
        api_main.app.dependency_overrides.clear()
