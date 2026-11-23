"""A1 (göç v2650, 24.11.2026) — ensemble HAM PV bandının değiştirilemez arşivi: `ens_p10/p25/p75/p90_kw`, `ens_yayilim_kw`
(forecast_values) ve `bant_json` (forecast_runs). Saf testler DB'siz; `test_db_*` test DB (alembic head v2650) ister.

Sözleşme: (1) `ens_*` = `ensemble_service.bant_hesapla` çıktısı, ufuk σ / sapma / konformal ÖNCESİ; katmanlar dokunmaz.
(2) Bant kaynağı model ya da saat üye ufku dışında → NaN/NULL (0 değil). (3) Servis kantilleri (p10…p90, ham kopyalar) birebir
değişmez (altın referans). (4) Yalnız INSERT, tek işlem, aynı sayım bekçisi; UPDATE yolu yok; eski kayıtlar NULL kalır, değişmez.
(5) Künye: `bant_json` = `sonuc.bant`, `ensemble_kosu_zamani` = üye koşusunun yayın zamanı (UTC), `run_at` = koşu anı."""
from __future__ import annotations

import importlib.util
import re
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.pipeline.forecast import forecast_7day
from pvquant.services import ensemble_service as es
from pvquant.services import forecast_service as fs
from pvquant.services.plant_spec_service import plant_spec_kur

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_altin_cekirdek import KALIBRASYON, PLANT, _girdi, _karsilastir, _meteo, _oku_ya_da_yaz, _seri, _uyeler  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
ENS = list(fs.ENS_KOLONLAR)
SIMDI = pd.Timestamp("2026-06-21 00:00", tz="UTC")


@pytest.fixture()
def ensemble_ayari(monkeypatch):
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="otomatik", ensemble_min_uye=5))


def _ham_bant_bagimsiz(meteo, uyeler) -> pd.DataFrame:
    """`tahmin_uret`'ten bağımsız yeniden kurma: fizik çerçevesi + `bant_hesapla` → katman öncesi üye kantilleri."""
    spec = plant_spec_kur(PLANT, KALIBRASYON)
    h0 = forecast_7day(meteo, spec).hourly.rename(columns={"p_ac_kw": "p50_kw"})
    h0["physics_kw"] = h0["p50_kw"]
    q, bant = es.bant_hesapla(PLANT, spec, meteo, h0, uyeler)
    assert bant["kaynak"] == "gefs"
    return q.reindex(h0.index)


# ───────────────────────────────────────────── saf ─────────────────────────────────────────────
def test_ens_kolonlari_katman_oncesi_uye_kantilleri_ile_birebir(ensemble_ayari):
    """ens_* tam olarak bant_hesapla çıktısıdır (σ/sapma sonrası servis bandı değil)."""
    sonuc = fs.tahmin_uret(PLANT, _meteo(), _girdi(), simdi=SIMDI)
    h = sonuc.h
    assert sonuc.bant["kaynak"] == "gefs" and all(k in h.columns for k in ENS)
    q = _ham_bant_bagimsiz(_meteo(), _uyeler())
    for k, qk in (("ens_p10_kw", "p10"), ("ens_p25_kw", "p25"), ("ens_p75_kw", "p75"), ("ens_p90_kw", "p90"), ("ens_yayilim_kw", "yayilim")):
        a = pd.to_numeric(h[k], errors="coerce").to_numpy(dtype=float)
        b = q[qk].to_numpy(dtype=float)
        assert np.isnan(a).tolist() == np.isnan(b).tolist(), f"{k}: NaN deseni"
        assert np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]), f"{k}: üye kantilinden sapıyor"
    # katmanlar servis bandını değiştirdi (σ genişletir, sapma ölçekler) → ens ≠ servis en az bir gündüz saatinde
    gunduz = h["p50_kw"] > 0
    assert not np.allclose(h.loc[gunduz, "ens_p10_kw"].astype(float), h.loc[gunduz, "p10_kw"].astype(float))
    assert (h.loc[gunduz, "ens_p10_kw"] <= h.loc[gunduz, "ens_p25_kw"] + 1e-9).all() and (h.loc[gunduz, "ens_p75_kw"] <= h.loc[gunduz, "ens_p90_kw"] + 1e-9).all()
    assert (h["ens_yayilim_kw"].dropna() >= 0).all()


def test_ens_kolonlarina_katmanlar_dokunmaz(ensemble_ayari):
    """Aynı üyelerle: ufuk σ + sapma açık / kapalı → ens_* birebir aynı; servis bandı farklı."""
    acik = fs.tahmin_uret(PLANT, _meteo(), _girdi(), simdi=SIMDI).h
    g = _girdi()
    g.ufuk_ayar = None
    g.sapma_ayar = None
    kapali = fs.tahmin_uret(PLANT, _meteo(), g, simdi=SIMDI).h
    for k in ENS:
        pd.testing.assert_series_equal(acik[k].astype(float), kapali[k].astype(float), check_names=False)
    assert not np.allclose(acik["p10_kw"].fillna(-1).astype(float), kapali["p10_kw"].fillna(-1).astype(float))
    # konformal yalnız p10/p90 ham kopyasına bakar — ens_* kolon kümesi dışında (statik)
    import inspect

    from pvquant.services import konformal_service as kf
    from pvquant.services import sapma_service as sp
    from pvquant.services import ufuk_service as uf
    for mod in (kf, sp, uf):
        assert "ens_" not in inspect.getsource(mod), f"{mod.__name__} ens_* kolonuna dokunuyor"


def test_model_bandinda_ens_kolonlari_null(ensemble_ayari):
    g = _girdi()
    g.uyeler = None
    sonuc = fs.tahmin_uret(PLANT, _meteo(), g, simdi=SIMDI)
    assert sonuc.bant["kaynak"] == "model"
    for k in ENS:
        assert sonuc.h[k].isna().all(), f"{k}: model bandında NULL olmalı (0 ya da uydurma değil)"


def test_uye_ufku_disinda_ens_null_icinde_dolu(ensemble_ayari):
    """Üyeler yalnız ilk 48 saati kapsarsa: 48+ saatler NaN, kapsanan gündüz saatleri dolu."""
    g = _girdi()
    g.uyeler = {u: df.iloc[:48] for u, df in _uyeler().items()}
    h = fs.tahmin_uret(PLANT, _meteo(), g, simdi=SIMDI).h
    kuyruk = h.index >= pd.Timestamp("2026-06-23 00:00", tz="UTC")
    for k in ENS:
        assert h.loc[kuyruk, k].isna().all(), f"{k}: üye ufku dışı NULL değil"
    ilk = h.loc[~kuyruk]
    assert ilk.loc[ilk["p50_kw"] > 0, "ens_p90_kw"].notna().all()


def test_altin_servis_kantilleri_degismedi_ve_ens_pini(ensemble_ayari):
    """Altın zincir referansı (8 kolon) A1 ile birebir; ens_* ayrı referansla dondurulur."""
    from test_altin_cekirdek import KOLONLAR
    h = fs.tahmin_uret(PLANT, _meteo(), _girdi(), simdi=SIMDI).h
    ref = _oku_ya_da_yaz("katman_zinciri", lambda: pytest.fail("katman_zinciri.json yok"))
    _karsilastir(ref, _seri(h, KOLONLAR), KOLONLAR)
    yeni = _seri(h, ENS)
    ref_ens = _oku_ya_da_yaz("ens_ham_bant", lambda: dict(yeni))
    _karsilastir(ref_ens, yeni, ENS)


def test_insert_kolon_listesi_goc_ile_ayni_ve_update_yolu_yok():
    kaynak = (KOK / "src/pvquant/services/forecast_service.py").read_text(encoding="utf-8")
    m = re.search(r"INSERT INTO forecast_values\((.*?)\)\s*\"?\s*\"?VALUES", kaynak, re.S)
    assert m, "forecast_values INSERT bulunamadı"
    kolonlar = [k.strip() for k in m.group(1).replace('"', "").replace("\n", "").split(",") if k.strip()]
    for k in ENS:
        assert k in kolonlar, f"INSERT {k} içermiyor"
    yol = KOK / "alembic/versions/v2650_ens_ham_bant.py"
    spec = importlib.util.spec_from_file_location("v2650", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert tuple(mod.ENS_KOLONLAR) == tuple(fs.ENS_KOLONLAR), "göç ve servis kolon listesi ayrıştı"
    assert "bant_json" in kaynak.split("INSERT INTO forecast_runs")[1].split("RETURNING")[0]
    # değiştirilemezlik: hiçbir üretim ya da betik yolunda forecast_values UPDATE'i yok
    desen = re.compile(r"update\s+forecast_values\b", re.I)
    suclular = [d.relative_to(KOK).as_posix() for kok in ("src", "apps", "scripts") for d in (KOK / kok).rglob("*.py")
                if ".venv" not in d.parts and desen.search(d.read_text(encoding="utf-8", errors="ignore"))]
    assert suclular == [], f"forecast_values UPDATE yolu: {suclular}"


# ───────────────────────────────────────────── DB ──────────────────────────────────────────────
@pytest.fixture()
def santral():
    from pvquant.db import bakim_baglami, sistem_baglami
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'ens-arsiv-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Ens Arşiv GES', 1000, 900, 37.9, 32.5, 'Europe/Istanbul', '{}')"), {"p": pid, "t": tid})
        s.execute(text("INSERT INTO calibrations(tenant_id, plant_id, mode, params_json, active, created_at) "
                       "VALUES(:t, :p, 'B', '{\"eta_bos\": 0.9, \"bg\": 0.1}', true, TIMESTAMPTZ '2026-06-18 00:30:00+00')"), {"t": tid, "p": pid})
    plant = {"id": pid, "tenant_id": tid, "name": "Ens Arşiv GES", "capacity_kwp": 1000.0, "ac_limit_kw": 900.0, "lat": 37.9, "lon": 32.5,
             "tz": "Europe/Istanbul", "params_json": {}}
    yield tid, plant
    with bakim_baglami() as s:
        for t in ("forecast_values", "forecast_runs", "calibrations"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


YAYIN = pd.Timestamp("2026-06-20 18:00", tz="UTC")


def _kur(monkeypatch, uyeler, yakala: dict, simdi=SIMDI):
    class _Stub:
        def get_forecast(self, latitude, longitude, days):
            return _meteo()
    monkeypatch.setattr(fs, "OpenMeteoClient", _Stub)
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="otomatik", ensemble_min_uye=5))
    monkeypatch.setattr(es, "uyeler_getir", lambda plant, days: (uyeler, YAYIN if uyeler else None))
    asil = fs.tahmin_uret
    def sarmal(plant_, meteo_, girdi, simdi_=None):
        sonuc = asil(plant_, meteo_, girdi, simdi=simdi)
        if yakala.get("boz"):
            sonuc.h.iloc[10, sonuc.h.columns.get_loc("ens_p10_kw")] = "bozuk"   # kısmi yazım simülasyonu
        yakala["sonuc"] = sonuc
        return sonuc
    monkeypatch.setattr(fs, "tahmin_uret", sarmal)


def _oku(run_id):
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT run_at, ensemble_kosu_zamani, bant_json, satir_sayisi FROM forecast_runs WHERE id=CAST(:r AS uuid)"), {"r": run_id}).mappings().one()
        v = pd.read_sql(text("SELECT ts_utc, p50_kw, p10_kw, p90_kw, p25_kw, p75_kw, p10_ham_kw, p90_ham_kw, ens_p10_kw, ens_p25_kw, ens_p75_kw, ens_p90_kw, ens_yayilim_kw "
                             "FROM forecast_values WHERE run_id=CAST(:r AS uuid) ORDER BY ts_utc"), s.connection(), params={"r": run_id}, parse_dates=["ts_utc"])
    return dict(r), v


def _ayni(db: pd.Series, h: pd.Series):
    a = pd.to_numeric(db, errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(h, errors="coerce").to_numpy(dtype=float)
    return np.isnan(a).tolist() == np.isnan(b).tolist() and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)])


def test_db_sema_kolonlar_nullable_defaultsuz():
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT column_name, is_nullable, column_default, data_type FROM information_schema.columns "
                              "WHERE table_name='forecast_values' AND column_name LIKE 'ens_%'")).mappings().all()
        bj = s.execute(text("SELECT is_nullable, column_default, data_type FROM information_schema.columns "
                            "WHERE table_name='forecast_runs' AND column_name='bant_json'")).mappings().one()
    assert sorted(r["column_name"] for r in rows) == sorted(ENS)
    assert all(r["is_nullable"] == "YES" and r["column_default"] is None and r["data_type"] == "double precision" for r in rows)
    assert bj["is_nullable"] == "YES" and bj["column_default"] is None and bj["data_type"] == "jsonb"


def test_db_gidis_donus_ens_ve_kunye(santral, monkeypatch):
    tid, plant = santral
    yakala = {}
    _kur(monkeypatch, _uyeler(), yakala)
    run_id = fs.uret_ve_kaydet(tid, plant)
    r, v = _oku(run_id)
    h = yakala["sonuc"].h
    assert len(v) == len(h) == r["satir_sayisi"]
    assert [pd.Timestamp(t).tz_convert("UTC") for t in v["ts_utc"]] == list(h.index)
    for k in [*ENS, "p50_kw", "p10_kw", "p90_kw", "p25_kw", "p75_kw", "p10_ham_kw", "p90_ham_kw"]:
        assert _ayni(v[k], h[k].reset_index(drop=True)), f"{k}: DB ≠ çerçeve"
    assert v["ens_p10_kw"].notna().sum() > 0
    assert r["bant_json"] == yakala["sonuc"].bant and r["bant_json"]["kaynak"] == "gefs" and r["bant_json"]["uye"] == 8
    assert pd.Timestamp(r["ensemble_kosu_zamani"]).tz_convert("UTC") == YAYIN and pd.Timestamp(r["run_at"]).tz_convert("UTC") == SIMDI
    assert pd.Timestamp(r["ensemble_kosu_zamani"]).tz_convert("UTC") <= pd.Timestamp(r["run_at"]).tz_convert("UTC")   # yayın ≤ üretim


def test_db_model_bandinda_null_ve_bant_json_model(santral, monkeypatch):
    tid, plant = santral
    yakala = {}
    _kur(monkeypatch, None, yakala)
    run_id = fs.uret_ve_kaydet(tid, plant)
    r, v = _oku(run_id)
    assert all(v[k].isna().all() for k in ENS) and r["bant_json"]["kaynak"] == "model" and r["ensemble_kosu_zamani"] is None
    assert v["p50_kw"].notna().all()


def test_db_eski_kayit_degismez_yeni_kosu_ayri_run(santral, monkeypatch):
    """Eski (ens'siz) koşu NULL kalır ve bayt-bayt değişmez; yeniden koşu yeni run_id açar, UPDATE yok."""
    from pvquant.db import sistem_baglami
    tid, plant = santral
    ozet_sql = text("SELECT count(*), md5(string_agg(ts_utc::text||'|'||p50_kw::text||'|'||coalesce(p10_kw::text,'')||'|'||coalesce(ens_p10_kw::text,'N'), ',' ORDER BY ts_utc)) "
                    "FROM forecast_values WHERE run_id=CAST(:r AS uuid)")
    with sistem_baglami() as s:
        eski = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, etiket) "
                              "VALUES(:t, :p, TIMESTAMPTZ '2026-06-19 00:00+00', 'B', 'barhdadi_bennis', 'acik-nwp', 'yayin') RETURNING id"),
                         {"t": tid, "p": plant["id"]}).scalar()
        s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, physics_kw) VALUES(:t, :r, :p, :ts, 100.0, 100.0)"),
                  [{"t": tid, "r": eski, "p": plant["id"], "ts": pd.Timestamp("2026-06-19", tz="UTC").to_pydatetime() + pd.Timedelta(hours=i)} for i in range(24)])
        onceki = s.execute(ozet_sql, {"r": eski}).one()
    yakala = {}
    _kur(monkeypatch, _uyeler(), yakala)
    r1 = fs.uret_ve_kaydet(tid, plant)
    r2 = fs.uret_ve_kaydet(tid, plant)   # yeniden çalıştırma
    assert r1 != r2 and str(eski) not in (r1, r2)
    with sistem_baglami() as s:
        sonraki = s.execute(ozet_sql, {"r": eski}).one()
        n_run = s.execute(text("SELECT count(*) FROM forecast_runs WHERE tenant_id=:t"), {"t": tid}).scalar()
        eski_ens = s.execute(text("SELECT bool_and(ens_p10_kw IS NULL AND ens_yayilim_kw IS NULL) FROM forecast_values WHERE run_id=CAST(:r AS uuid)"), {"r": eski}).scalar()
        bant_eski = s.execute(text("SELECT bant_json FROM forecast_runs WHERE id=:r"), {"r": eski}).scalar()
    assert onceki == sonraki and onceki[0] == 24 and eski_ens is True and bant_eski is None and n_run == 3
    _, v1 = _oku(r1)
    _, v2 = _oku(r2)
    assert _ayni(v1["ens_p10_kw"], v2["ens_p10_kw"])   # aynı girdi → aynı ham bant; ayrı satırlar


def test_db_kismi_yazim_tum_kosuyu_geri_alir(santral, monkeypatch):
    """ens değeri sayıya çevrilemezse hata → run + values tek işlemde geri alınır (başsız/eksik koşu kalmaz)."""
    from pvquant.db import sistem_baglami
    tid, plant = santral
    yakala = {"boz": True}
    _kur(monkeypatch, _uyeler(), yakala)
    with pytest.raises((ValueError, TypeError)):
        fs.uret_ve_kaydet(tid, plant)
    with sistem_baglami() as s:
        n_run = s.execute(text("SELECT count(*) FROM forecast_runs WHERE tenant_id=:t"), {"t": tid}).scalar()
        n_val = s.execute(text("SELECT count(*) FROM forecast_values WHERE tenant_id=:t"), {"t": tid}).scalar()
    assert n_run == 0 and n_val == 0
