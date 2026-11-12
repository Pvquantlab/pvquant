"""v2.597 (Faz 4 F4-B, Stage 3) — tahmin arşivi: künye sütunları, etiket sözlüğü, değişmezlik tetikleyicisi + bakım bağlamı,
yayımlanmış koşu süzgeci (tek yer), program seçimi üçlü denkliği, arşiv sorgusu (servis + API), q̂ geçmişi, NWP bileşen künyesi,
karne yeniden hesap bayrağı, seed_sentetik koruması (M3). Saf testler DB'siz; `test_db_*` test DB (alembic head v2597) ister."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.ext.turkiye import kurallar as kr
from pvquant.services import ensemble_service as es
from pvquant.services import forecast_service as fs
from pvquant.services import karne_kurali as kk

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_altin_cekirdek import _meteo  # noqa: E402

KOK = Path(__file__).resolve().parents[1]


# ───────────────────────────────────────────── saf ─────────────────────────────────────────────
def test_etiket_sozlugu_goc_ile_ayni():
    spec = importlib.util.spec_from_file_location("goc_v2597", KOK / "alembic" / "versions" / "v2597_arsiv_kunye.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert tuple(m.ETIKETLER) == tuple(kk.ETIKETLER)
    assert kk.GERIYE_BAKISLI_ETIKET | {"yayin", "gun_ici", "elle"} == set(kk.ETIKETLER)


def test_yayin_kosu_sql_ve_geriye_bakisli_ayni_kume():
    sql = kk.yayin_kosu_sql("r")
    for e in kk.GERIYE_BAKISLI_ETIKET:
        assert f"'{e}'" in sql
    assert "'elle'" not in sql and "'elle'" in kk.yayin_kosu_sql("r", elle_dahil=False)
    assert "'open-meteo-arsiv'" in sql and "'sentetik_tohum'" in sql and "'backtest'" in sql
    assert kk.yayin_kosu_sql("").startswith("(COALESCE(etiket")
    df = pd.DataFrame({"etiket": ["yayin", "backtest", "elle", "demo", None], "model": ["barhdadi_bennis"] * 5, "meteo_source": ["acik-nwp"] * 5})
    assert kk.geriye_bakisli(df).tolist() == [False, True, False, True, False]
    # eski damgalar hâlâ tanınır
    df2 = pd.DataFrame({"etiket": ["yayin", "yayin"], "model": ["backtest", "x"], "meteo_source": ["acik-nwp", "sentetik_tohum"]})
    assert kk.geriye_bakisli(df2).tolist() == [True, True]


def test_kgup_kesim_sql_python_ile_ayni():
    sql = kr.kgup_kesim_sql("g.gun")
    assert "DATE '2025-01-01'" in sql and "INTERVAL '16 hours 0 minutes'" in sql and "INTERVAL '15 hours 30 minutes'" in sql
    assert kr.kgup_kesim(date(2024, 12, 31))[0] == (16, 0) and kr.kgup_kesim(date(2025, 1, 1))[0] == (15, 30)


def test_arsive_yaz_sozluk_disi_etiketi_reddeder():
    sonuc = SimpleNamespace(h=pd.DataFrame({"p50_kw": [1.0]}, index=pd.date_range("2026-06-21", periods=1, freq="h", tz="UTC")),
                            simdi=pd.Timestamp("2026-06-21", tz="UTC"), mode="B", model_adi="barhdadi_bennis", ml_model_id=None, bant={}, sapma={},
                            ufuk=None, konformal_ayar=None, n_eksik=0, geri_dusus=None, spec=None)
    with pytest.raises(ValueError, match="sözlük dışı"):
        fs.arsive_yaz("t", {"id": "p", "tz": "UTC"}, _meteo(), sonuc, etiket="test")


def test_seed_sentetik_santral_ve_onay_zorunlu():
    r = subprocess.run([sys.executable, str(KOK / "scripts" / "seed_sentetik.py"), "--gun", "3"], capture_output=True, text=True, timeout=120,
                       env={"PATH": "", "PYTHONPATH": str(KOK / "src"), "PVQ_DB_URL": "postgresql+psycopg://x:y@127.0.0.1:1/yok"})
    assert r.returncode == 2 and "--onay" in (r.stderr + r.stdout)
    kaynak = (KOK / "scripts" / "seed_sentetik.py").read_text(encoding="utf-8")
    assert "meteo_source <> 'sentetik_tohum'" not in kaynak.split("def _temizle")[1].split("def _sentetik_seri")[0].replace("count(*)", "")  or "DELETE FROM forecast_values WHERE plant_id=:p AND ts_utc" not in kaynak
    assert "'sentetik')" in kaynak and "app.arsiv_bakim" in kaynak


# ───────────────────────────────────────────── DB ──────────────────────────────────────────────
@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'arsiv-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Arşiv GES', 1200, 1000, 37.0, 32.0, 'Europe/Istanbul', '{}')"), {"p": pid, "t": tid})
        cid = s.execute(text("INSERT INTO calibrations(tenant_id, plant_id, mode, params_json, active, created_at) "
                             "VALUES(:t, :p, 'B', '{\"eta_bos\": 0.85}', true, TIMESTAMPTZ '2026-06-18 00:30:00+00') RETURNING id"), {"t": tid, "p": pid}).scalar()
    plant = {"id": pid, "tenant_id": tid, "name": "Arşiv GES", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0, "lat": 37.0, "lon": 32.0,
             "tz": "Europe/Istanbul", "params_json": {}}
    yield tid, plant, str(cid)
    with bakim_baglami() as s:
        for t in ("skill_daily", "forecast_daily", "forecast_values", "forecast_runs", "konformal_ayar_gecmis", "konformal_ayar", "scada_hourly", "calibrations"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def _kosu_yaz(s, tid, pid, run_at, saatler, p50, etiket="yayin", model="barhdadi_bennis", meteo="acik-nwp"):
    rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, etiket) "
                         "VALUES(:t, :p, :ra, 'B', :mo, :ms, :et) RETURNING id"),
                    {"t": tid, "p": pid, "ra": pd.Timestamp(run_at).to_pydatetime(), "mo": model, "ms": meteo, "et": etiket}).scalar()
    s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, physics_kw) VALUES(:t, :r, :p, :ts, :v, :v)"),
              [{"t": tid, "r": rid, "p": pid, "ts": pd.Timestamp(ts).to_pydatetime(), "v": float(p50)} for ts in saatler])
    return str(rid)


def test_db_uret_ve_kaydet_kunye_sutunlari(santral, monkeypatch):
    tid, plant, cid = santral
    yayin = pd.Timestamp("2026-06-20 18:00", tz="UTC")
    bilesenler = {"ECMWF IFS": "2026-06-20T18:00:00+00:00", "ICON-EU": "2026-06-20T21:00:00+00:00"}
    m0 = _meteo("2026-06-21", 3)
    from pvquant.io.meteo import MeteoData
    meteo = MeteoData(ghi=m0.ghi, temp_air=m0.temp_air, wind_speed_10m=m0.wind_speed_10m, relative_humidity=None, cloud_cover=None,
                      latitude=37.0, longitude=32.0, timezone="UTC", kaynak="acik-nwp", nwp_model="ECMWF IFS + ICON-EU", kosu_zamani=yayin, bilesenler=bilesenler)

    class _Stub:
        def get_forecast(self, latitude, longitude, days):
            return meteo
    monkeypatch.setattr(fs, "OpenMeteoClient", _Stub)
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="model", ensemble_min_uye=20))
    sabit = pd.Timestamp("2026-06-21 00:30", tz="UTC")
    asil = fs.tahmin_uret
    monkeypatch.setattr(fs, "tahmin_uret", lambda plant_, meteo_, girdi, simdi=None: asil(plant_, meteo_, girdi, simdi=sabit))
    run_id = fs.uret_ve_kaydet(tid, plant)   # etiket None → 'yayin'
    with sistem_baglami() as s:
        r = s.execute(text("SELECT run_at, etiket, ufuk_saat, satir_sayisi, cozunurluk_dk, spec_json, nwp_bilesenler_json, veri_kalitesi_json, sapma_oran_json, "
                           "konformal_q_json, ufuk_sigma_json, artefakt_sha16, ensemble_kosu_zamani, meteo_ozet_json->>'etiket' AS je, "
                           "(SELECT count(*) FROM forecast_values v WHERE v.run_id=forecast_runs.id) AS n FROM forecast_runs WHERE id=CAST(:r AS uuid)"),
                      {"r": run_id}).mappings().one()
    assert r["etiket"] == "yayin" and r["je"] == "yayin" and pd.Timestamp(r["run_at"]).tz_convert("UTC") == sabit
    assert r["satir_sayisi"] == r["n"] == 72 and r["ufuk_saat"] == int((pd.Timestamp("2026-06-23 23:00", tz="UTC") - sabit).total_seconds() // 3600)
    assert r["cozunurluk_dk"] == 60 and r["spec_json"]["eta_bos"] == 0.85 and r["spec_json"]["p_ac_clip_kw"] == 1000.0
    assert r["nwp_bilesenler_json"] == bilesenler and r["artefakt_sha16"] is None and r["konformal_q_json"] is None and r["ensemble_kosu_zamani"] is None
    vk = r["veri_kalitesi_json"]
    assert vk["meteo_yas_saat"] == 6.5 and 2.9 <= vk["kalibrasyon_yas_gun"] <= 3.1 and vk["konformal_yas_gun"] is None and vk["bant_kaynagi"] == "model"
    assert vk["eksik_saat"] == 0 and vk["sapma_aktif"] is False and vk["geri_dusus"] is None
    assert r["sapma_oran_json"]["aktif"] is False and r["ufuk_sigma_json"] is None
    # arşiv sorgusu: yayımlanmış koşu
    out = fs.yayimlanmis_kosu(tid, plant["id"], "2026-06-22T12:00:00Z", "2026-06-21T06:00:00Z")
    assert out["kosu"]["run_id"] == run_id and out["ufuk_saat"] == 35.5 and out["deger"]["p50_kw"] > 0 and out["kosu"]["spec"]["eta_bos"] == 0.85
    assert fs.yayimlanmis_kosu(tid, plant["id"], "2026-06-22T12:00:00Z", "2026-06-21T00:00:00Z") is None   # koşudan önce yayımlanmış değil


def test_db_degismezlik_tetikleyicisi_ve_bakim_baglami(santral):
    tid, plant, _ = santral
    pid = plant["id"]
    saatler = pd.date_range("2026-06-22 06:00", periods=3, freq="h", tz="UTC")
    with sistem_baglami() as s:
        rid = _kosu_yaz(s, tid, pid, "2026-06-21 02:00+00:00", saatler, 100.0)
    # uygulama rolü: UPDATE/DELETE yetkisi yok
    for sql in ("UPDATE forecast_runs SET mode='A' WHERE id=CAST(:r AS uuid)", "DELETE FROM forecast_values WHERE run_id=CAST(:r AS uuid)"):
        with pytest.raises(Exception) as ei, tenant_baglami(tid) as s:
            s.execute(text(sql), {"r": rid})
        assert "permission denied" in str(ei.value) or "değişmez" in str(ei.value)
    # bakım bayrağı yok: tetikleyici reddeder (CI'da PVQ_DB_URL pvq_api'dir → yetki reddi tetikleyiciden önce gelir; ikisi de kabul)
    for sql in ("UPDATE forecast_runs SET mode='A' WHERE id=CAST(:r AS uuid)", "DELETE FROM forecast_values WHERE run_id=CAST(:r AS uuid)",
                "DELETE FROM forecast_runs WHERE id=CAST(:r AS uuid)"):
        with pytest.raises(Exception, match="değişmez|permission denied") , sistem_baglami() as s:
            s.execute(text(sql), {"r": rid})
    with sistem_baglami() as s:
        assert s.execute(text("SELECT count(*) FROM forecast_values WHERE run_id=CAST(:r AS uuid)"), {"r": rid}).scalar() == 3
    # bakım bağlamı: geçer
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM forecast_values WHERE run_id=CAST(:r AS uuid)"), {"r": rid})
        s.execute(text("DELETE FROM forecast_runs WHERE id=CAST(:r AS uuid)"), {"r": rid})
    with sistem_baglami() as s:
        assert s.execute(text("SELECT count(*) FROM forecast_runs WHERE id=CAST(:r AS uuid)"), {"r": rid}).scalar() == 0
    # etiket CHECK
    with pytest.raises(Exception, match="forecast_runs_etiket_check"), sistem_baglami() as s:
        s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, mode, model, etiket) VALUES(:t, :p, 'A', 'x', 'test')"), {"t": tid, "p": pid})
    with sistem_baglami() as s:   # varsayılan 'yayin'
        rid2 = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, mode, model) VALUES(:t, :p, 'A', 'x') RETURNING etiket"), {"t": tid, "p": pid}).scalar()
    assert rid2 == "yayin"


def test_db_yayimlanmis_suzgec_son_kosu_ve_api(santral):
    tid, plant, _ = santral
    pid = plant["id"]
    saatler = pd.date_range("2026-06-22 00:00", periods=24, freq="h", tz="UTC")
    with sistem_baglami() as s:
        ra = _kosu_yaz(s, tid, pid, "2026-06-21 02:00+00:00", saatler, 100.0)
        _kosu_yaz(s, tid, pid, "2026-06-21 03:00+00:00", saatler, 200.0, etiket="backtest")
        rc = _kosu_yaz(s, tid, pid, "2026-06-21 04:00+00:00", saatler, 300.0, etiket="elle")
        _kosu_yaz(s, tid, pid, "2026-06-21 05:00+00:00", saatler, 400.0, etiket="simulasyon")
        _kosu_yaz(s, tid, pid, "2026-06-21 06:00+00:00", saatler, 500.0, etiket="yayin", meteo="open-meteo-arsiv")   # eski damga
    df = fs.son_kosu(tid, pid)
    assert float(df["p50_kw"].iloc[0]) == 300.0                                   # elle dâhil, backtest/simülasyon/eski damga dışarıda
    o = fs.yayimlanmis_kosu(tid, pid, "2026-06-22T12:00:00Z", "2026-06-21T03:30:00Z")
    assert o["kosu"]["run_id"] == ra and o["deger"]["p50_kw"] == 100.0           # 03:00 backtest koşusu «yayımlanmış» sayılmaz
    o2 = fs.yayimlanmis_kosu(tid, pid, "2026-06-22T12:00:00Z")
    assert o2["kosu"]["run_id"] == rc and o2["kosu"]["etiket"] == "elle"
    # API
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/plants/{pid}/tahmin-arsivi", params={"hedef": "2026-06-22T12:00:00Z", "yayin_oncesi": "2026-06-21T03:30:00Z"})
        assert r.status_code == 200 and r.json()["kosu"]["run_id"] == ra and r.json()["ufuk_saat"] == 34.0
        assert c.get(f"/v1/plants/{pid}/tahmin-arsivi", params={"hedef": "2026-06-22T12:00:00Z", "yayin_oncesi": "2026-06-20T00:00:00Z"}).status_code == 404
        assert c.get(f"/v1/plants/{pid}/tahmin-arsivi", params={"hedef": "dün"}).status_code == 422
        assert c.get(f"/v1/plants/{uuid.uuid4()}/tahmin-arsivi", params={"hedef": "2026-06-22T12:00:00Z"}).status_code == 404
        # eski uç da süzülü: /forecast son yayımlanmış koşu
        f = c.get(f"/v1/plants/{pid}/forecast", params={"hours": 3}).json()
        assert f["series"][0]["p50_kw"] == 300.0
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)


def test_db_program_secimi_uclu_denklik(santral):
    """program_df (SQL, kgup_kesim_sql) = kgup_service.kaynak_kosu_df (SQL+Python) = karne_kurali.program_kovasi (pandas): teslim günü D için
    D-1 15:30 İstanbul öncesi SON yayımlanmış koşu; elle koşu sayılır, backtest sayılmaz (B11 kapanışı)."""
    from pvquant.services import dengesizlik_service as ds
    from pvquant.services import kgup_service as kg
    tid, plant, _ = santral
    pid = plant["id"]
    D = date(2026, 6, 10)
    ist = "Europe/Istanbul"
    saatler = pd.date_range(pd.Timestamp(D, tz=ist), periods=24, freq="h").tz_convert("UTC")
    with sistem_baglami() as s:
        _kosu_yaz(s, tid, pid, pd.Timestamp("2026-06-09 14:00", tz=ist), saatler, 100.0)                       # kesim öncesi yayın
        r_elle = _kosu_yaz(s, tid, pid, pd.Timestamp("2026-06-09 15:20", tz=ist), saatler, 200.0, etiket="elle")   # kesim öncesi SON → program kaynağı
        _kosu_yaz(s, tid, pid, pd.Timestamp("2026-06-09 15:25", tz=ist), saatler, 300.0, etiket="backtest")   # dışarıda
        _kosu_yaz(s, tid, pid, pd.Timestamp("2026-06-09 15:45", tz=ist), saatler, 400.0)                       # kesim sonrası
        s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, 150, 150, 'valid', 60)"),
                  [{"t": tid, "p": pid, "ts": ts.to_pydatetime()} for ts in saatler])
    # 1) kaynak_kosu_df
    kdf, bilgi = kg.kaynak_kosu_df(tid, pid, D)
    assert bilgi["run_id"] == r_elle and (kdf["kw"] == 200.0).all() and len(kdf) == 24
    # 2) program_df
    pdf = ds.program_df(tid, pid, gun=3)
    assert len(pdf) == 24 and (pdf["kgup_kw"] == 200.0).all()
    # 3) karne_kurali.program_kovasi (tüm satırlar; geriye bakışlı dâhil verilir, kural eler)
    with tenant_baglami(tid) as s:
        tum = pd.read_sql(text("SELECT f.ts_utc, r.run_at, f.p50_kw, r.model, r.meteo_source, r.etiket FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
                               "WHERE f.plant_id=:p"), s.connection(), params={"p": pid}, parse_dates=["ts_utc", "run_at"])
    prog = kk.program_kovasi(tum)
    assert len(prog) == 24 and (prog["p50_kw"] == 200.0).all() and (prog["etiket"] == "elle").all()


def test_db_konformal_gecmisi_yalniz_ekleme(santral, monkeypatch):
    from pvquant.services import konformal_service as kf
    tid, plant, _ = santral
    ix = pd.date_range("2026-05-01", periods=60 * 24, freq="h", tz="UTC")
    saat = ix.hour
    p50 = pd.Series(np.where((saat >= 6) & (saat <= 18), 500.0, 0.0), index=ix)
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"ts_utc": ix, "power_kw": p50 * (1 + rng.normal(0, 0.1, len(ix))), "p50": p50, "p10": p50 * 0.9, "p90": p50 * 1.1,
                       "ufuk_saat": (np.arange(len(ix)) % 24).astype(float)}).reset_index(drop=True)
    monkeypatch.setattr(kf, "gecmis_band_df", lambda *a, **k: df)
    a1 = kf.q_hat_hesapla(tid, plant); assert a1 is not None
    a2 = kf.q_hat_hesapla(tid, plant); assert a2 is not None
    with tenant_baglami(tid) as s:
        n_g = s.execute(text("SELECT count(*), string_agg(DISTINCT kaynak, ',') FROM konformal_ayar_gecmis WHERE plant_id=:p"), {"p": plant["id"]}).fetchone()
        n_a = s.execute(text("SELECT count(*) FROM konformal_ayar WHERE plant_id=:p"), {"p": plant["id"]}).scalar()
    assert n_g[0] == 2 and n_g[1] == "gece" and n_a == 1
    with pytest.raises(Exception, match="permission denied"), tenant_baglami(tid) as s:
        s.execute(text("DELETE FROM konformal_ayar_gecmis WHERE plant_id=:p"), {"p": plant["id"]})


def test_db_meteo_kosu_kunyesi_yaz_oku():
    from pvquant.io import acik_nwp
    lat, lon = 36.123, 31.456
    kosu = pd.Timestamp("2026-06-20 00:00", tz="UTC")
    ix = pd.date_range(pd.Timestamp.now(tz="UTC").floor("D"), periods=48, freq="h")
    try:
        with sistem_baglami() as s:
            s.execute(text("INSERT INTO meteo_arsiv(kaynak,kosu_zamani,lat,lon,ts_utc,ghi,temp_air,wind_speed_10m,cloud_cover) VALUES(:k,:z,:la,:lo,:ts,100,20,2,10) ON CONFLICT DO NOTHING"),
                      [{"k": acik_nwp.KAYNAK, "z": kosu.to_pydatetime(), "la": lat, "lo": lon, "ts": ts.to_pydatetime()} for ts in ix])
        assert acik_nwp._kunye_yaz([{"k": acik_nwp.KAYNAK, "z": kosu.to_pydatetime(), "la": lat, "lo": lon, "b": '{"ECMWF IFS": "2026-06-20T00:00:00+00:00"}'}]) == 1
        md = acik_nwp.arsivden_tahmin(lat, lon, days=2, azami_yas_saat=10 ** 6)
        assert md is not None and md.bilesenler == {"ECMWF IFS": "2026-06-20T00:00:00+00:00"} and md.nwp_model == "ECMWF IFS" and md.kosu_zamani == kosu
        assert acik_nwp.nwp_model_etiketi(None) == acik_nwp.KAYNAK_ETIKET
    finally:
        with bakim_baglami() as s:   # meteo_kosu_kunye yalnız ekleme: temizlik bakım (sahip) bağlamında
            s.execute(text("DELETE FROM meteo_kosu_kunye WHERE lat=:la AND lon=:lo"), {"la": lat, "lo": lon})
            s.execute(text("DELETE FROM meteo_arsiv WHERE lat=:la AND lon=:lo"), {"la": lat, "lo": lon})


def test_db_skill_daily_yeniden_hesap_bayragi(santral):
    import apps.worker.main as w
    tid, plant, _ = santral
    pid = plant["id"]
    simdi = pd.Timestamp.now(tz="UTC").floor("h")
    gun0 = (simdi - pd.Timedelta(days=2)).floor("D")
    saatler = pd.date_range(gun0 + pd.Timedelta(hours=6), periods=12, freq="h")
    with sistem_baglami() as s:
        _kosu_yaz(s, tid, pid, gun0 - pd.Timedelta(hours=22), saatler, 500.0)
        s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, 480, 480, 'valid', 60)"),
                  [{"t": tid, "p": pid, "ts": ts.to_pydatetime()} for ts in list(saatler) + [ts - pd.Timedelta(hours=24) for ts in saatler]])
    w.gece_skill(plant)
    w.gece_skill(plant)
    with tenant_baglami(tid) as s:
        rows = s.execute(text("SELECT horizon_bucket, yeniden_hesap_sayisi, hesap_zamani FROM skill_daily WHERE plant_id=:p"), {"p": pid}).fetchall()
    assert rows and all(r[1] == 1 and r[2] is not None for r in rows)
