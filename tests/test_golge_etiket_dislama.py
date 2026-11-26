"""Faz 1 G1/G3/G2 (26.11.2026, kısıtlı kapsam) — gölge etiketi, dışlama kuralı ve paralel mod arayüzleri (DB'siz).

- G1 depolama: 'golge' forecast_runs CHECK sözlüğünde (ETIKETLER / göç v2597) YOK → arşive yazım reddedilir → BLOCKED pini (göç gerekir).
- G3 dışlama: yayin_kosu_sql + geriye_bakisli + musteri_kosusu_mu gölgeyi dışarıda tutar; eksik etiket 'yayin' sayılır (geriye uyum);
  bagimsiz_dogrulama.kosu_sec gölge koşuyu hiçbir kuralda seçmez (simülasyonda da).
- G2 arayüz: golge_girdi A/B/C varyantları, golge_calistir ayrı sonuç / aynı yayın zamanı / run_id None; C düşüşü gizlenmez; worker kancası yok.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_altin_cekirdek import KALIBRASYON, PLANT, _meteo

from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import ensemble_service as es
from pvquant.services import forecast_service as fs
from pvquant.services import golge_service as gs
from pvquant.services import karne_kurali as kk

KOK = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- G1 depolama (BLOCKED pini)
def test_g1_golge_sozlukte_yok_arsiv_reddeder_blocked():
    assert kk.ETIKET_GOLGE == "golge" and kk.ETIKET_GOLGE not in kk.ETIKETLER and not gs.golge_kayit_izinli()
    spec = importlib.util.spec_from_file_location("v2597", KOK / "alembic" / "versions" / "v2597_arsiv_kunye.py")
    goc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(goc)
    assert tuple(goc.ETIKETLER) == tuple(kk.ETIKETLER) and "golge" not in goc.ETIKETLER   # kod sözlüğü = DB CHECK sözlüğü
    with pytest.raises(ValueError, match="sözlük dışı"):   # DB'ye dokunmadan, ilk satırda reddedilir
        fs.arsive_yaz(None, PLANT, None, None, etiket=kk.ETIKET_GOLGE)


# ---------------------------------------------------------------- G3 dışlama kuralı
def test_g3_sql_suzgeci_golge_disarida_geriye_uyum():
    sql = kk.yayin_kosu_sql("r")
    assert "'golge'" in sql and "COALESCE(r.etiket, 'yayin')" in sql
    for e in kk.GERIYE_BAKISLI_ETIKET:
        assert f"'{e}'" in sql                                  # eski küme aynen durur
    assert "'elle'" not in sql and "'elle'" in kk.yayin_kosu_sql("r", elle_dahil=False)
    assert "'yayin'" not in sql.split("NOT IN")[1].split(")")[0] and "'gun_ici'" not in sql   # yayın/gün içi dışlanmaz
    assert kk.GERIYE_BAKISLI_ETIKET < kk.DISLANAN_ETIKET and {"golge"} == kk.DISLANAN_ETIKET - kk.GERIYE_BAKISLI_ETIKET


def test_g3_df_suzgeci_ve_eksik_etiket():
    df = pd.DataFrame({"etiket": [None, "yayin", "gun_ici", "elle", "golge", "backtest"], "model": "barhdadi_bennis", "meteo_source": "acik-nwp"})
    assert kk.geriye_bakisli(df).tolist() == [False, False, False, False, True, True]
    assert not kk.geriye_bakisli(pd.DataFrame({"model": ["barhdadi_bennis"] * 3})).any()   # etiket sütunu yok → eski davranış


def test_g3_musteri_kosusu_mu():
    assert all(kk.musteri_kosusu_mu(e) for e in (None, "", "yayin", "gun_ici", "elle"))
    assert not kk.musteri_kosusu_mu("golge") and not kk.musteri_kosusu_mu("backtest") and not kk.musteri_kosusu_mu("simulasyon")
    assert not kk.musteri_kosusu_mu("yayin", model="backtest") and not kk.musteri_kosusu_mu(None, meteo_source="sentetik_tohum")


def _kosu(rid, run_at, etiket=None, saatler=None):
    return pd.DataFrame({"ts_utc": saatler, "run_at": pd.Timestamp(run_at, tz="UTC"), "run_id": rid, "p50_kw": 100.0, "p10_kw": 80.0,
                         "p90_kw": 120.0, "physics_kw": 100.0, "model": "barhdadi_bennis", "meteo_source": "acik-nwp", "etiket": etiket})


def test_g3_kosu_sec_golge_hic_secilmez():
    tz = "Europe/Istanbul"
    saatler = pd.date_range("2026-09-01 06:00", "2026-09-01 15:00", freq="h", tz="UTC")
    t = pd.concat([_kosu("gece", "2026-08-31 03:00", None, saatler), _kosu("golge_b", "2026-08-31 04:00", "golge", saatler),
                   _kosu("golge_c", "2026-08-31 11:30", "golge", saatler)], ignore_index=True)   # gölgeler daha YENİ
    for kural in ("gun_oncesi", "program", "ufuk"):
        sec = bd.kosu_sec(t, kural, tz)
        assert set(sec["run_id"]) == {"gece"}, kural
    sim = bd.kosu_sec(t, "gun_oncesi", tz, simulasyon=True)   # simülasyon eşlemesi gölgeyi yayına ÇEVİRMEZ
    assert set(sim["run_id"]) == {"gece"}
    yalniz_golge = bd.kosu_sec(t[t["etiket"] == "golge"], "gun_oncesi", tz)
    assert yalniz_golge.empty   # yalnız gölge varsa müşteri tahmini YOK (gölge son tahmin olamaz)


# ---------------------------------------------------------------- G2 arayüzleri (saf)
@pytest.fixture(autouse=True)
def _bant_kapali(monkeypatch):
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="model", ensemble_min_uye=20))


_MODEL = object()   # yüklü hibrit artefakt yerine işaretçi (fs.hybrid_forecast_hourly test içinde değiştirilir)


def _uretim_girdi(model=_MODEL):
    return fs.TahminGirdisi(mode="C", kalibrasyon_id="kal-1", kalibrasyon_params=KALIBRASYON, ml_model_id="ml-1", model=model,
                            artefakt_sha16="abc", konformal_ayar={"grup": "saat", "q_hat": {"_genel": 10.0}, "hesap_zamani": "2026-06-20T03:00:00+00:00"},
                            sapma_ayar={"aktif": False, "neden": "test"}, kalibrasyon_zamani="2026-06-01")


def _hh(model, meteo):
    ix = meteo.ghi.index
    p50 = pd.Series(np.clip(700.0 * np.sin(np.pi * (np.arange(len(ix)) % 24 - 3.5) / 13.0), 0, None), index=ix)
    return pd.DataFrame({"p50_kw": p50, "p10_kw": p50 * 0.8, "p90_kw": p50 * 1.2})


def test_g2_varyantlar_kaynak_degismez():
    g = _uretim_girdi()
    kopya = fs.TahminGirdisi(**vars(g))
    a, b, c = (gs.golge_girdi(g, m) for m in "ABC")
    assert (a.mode, a.kalibrasyon_params, a.kalibrasyon_id, a.model, a.konformal_ayar) == ("A", None, None, None, None)
    assert (b.mode, b.kalibrasyon_params, b.kalibrasyon_id, b.model, b.ml_model_id, b.konformal_ayar) == ("B", KALIBRASYON, "kal-1", None, None, None)
    assert (c.mode, c.kalibrasyon_params, c.model, c.ml_model_id, c.konformal_ayar) == ("C", KALIBRASYON, g.model, "ml-1", g.konformal_ayar)
    assert vars(g) == vars(kopya)   # kaynak girdi dokunulmadı
    with pytest.raises(ValueError):
        gs.golge_girdi(g, "D")


def test_g2_calistir_abc_ayri_sonuc_ayni_yayin_zamani(monkeypatch):
    monkeypatch.setattr(fs, "hybrid_forecast_hourly", _hh)
    simdi = pd.Timestamp("2026-06-21", tz="UTC")
    r = gs.golge_calistir(PLANT, _meteo(), _uretim_girdi(), simdi=simdi)
    assert set(r) == {"A", "B", "C"}
    for m, s in r.items():
        assert (s.mod, s.mode_gerceklesen, s.etiket, s.run_id, s.yayin_zamani) == (m, m, "golge", None, simdi)
        assert s.ufuk_saat == 71 and len(s.h) == 72 and s.geri_dusus is None
    assert r["A"].model_adi == r["B"].model_adi == "barhdadi_bennis" and r["C"].model_adi == "hybrid_residual"
    assert not np.allclose(r["A"].h["p50_kw"], r["B"].h["p50_kw"])      # kalibrasyon farkı görünür
    assert r["C"].h["ml_kw"].notna().any() and r["B"].h["ml_kw"].isna().all()


def test_g2_c_artefakt_yoksa_dusus_gizlenmez():
    r = gs.golge_calistir(PLANT, _meteo(), _uretim_girdi(model=None), modlar=("C",), simdi=pd.Timestamp("2026-06-21", tz="UTC"))
    s = r["C"]
    assert (s.mod, s.mode_gerceklesen, s.model_adi, s.geri_dusus) == ("C", "B", "barhdadi_bennis", "hibrit_artefakt_yok")


def test_g2_worker_ve_uretim_akisinda_golge_yok():
    for yol in ("apps/worker/main.py", "apps/api/main.py", "src/pvquant/services/forecast_service.py"):
        metin = (KOK / yol).read_text()   # (api'deki `golge_gorunum` kaynak-seçim görünümüdür, bu pakete ait değil)
        assert not any(k in metin for k in ("golge_service", "golge_calistir", "golge_girdi", "ETIKET_GOLGE")), yol   # zamanlama/uç/üretim kancası yok
