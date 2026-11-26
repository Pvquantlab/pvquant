"""Faz 1 — Mod C aktivasyon bekçisi (27.11.2026; DB'siz). Fail-closed: varsayılan kapalı; aylık kalibrasyon aktivasyon vermez;
yalnız ayar açık ∧ sha onaylı ∧ kodla uyumlu artefakt müşteriye C servis eder; onaysız/bozuk dosya için pickle HİÇ yüklenmez;
eksik artefakt eski v2.80 davranışıyla B'ye düşer; bayrak kapalıyken tahmin davranışı (Mod B zinciri) birebir korunur."""
from __future__ import annotations

import hashlib
import pickle
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_altin_cekirdek import KALIBRASYON, PLANT, _meteo

from pvquant.config import Settings
from pvquant.models_v2 import hybrid_residual as hr
from pvquant.services import ensemble_service as es
from pvquant.services import forecast_service as fs
from pvquant.services import mod_c_bekcisi as mb

KOK = Path(__file__).resolve().parents[1]


def _ayar(**k):
    d = {"mod_c_musteri": "kapali", "mod_c_onayli_artefakt": ""}
    d.update(k)
    return SimpleNamespace(**d)


class _Booster:
    def __init__(self, adlar):
        self.feature_name_ = list(adlar)


def _uyumlu_model():
    class HybridResidualModel:   # ad kodla aynı (type adı kontrolü)
        MODEL_VERSION = hr.HybridResidualModel.MODEL_VERSION
    m = HybridResidualModel()
    m._booster = _Booster(hr.FEATURE_COLUMNS)
    return m


def _girdi(mode="C"):
    return fs.TahminGirdisi(mode=mode, kalibrasyon_id="kal", kalibrasyon_params=KALIBRASYON)


def _dosya(tmp_path, icerik: bytes):
    yol = tmp_path / "hyb_test.pkl"
    yol.write_bytes(icerik)
    return str(yol), hashlib.sha256(icerik).hexdigest()[:16]


def _sayac(model):
    cagri = []

    def yukle(yol):
        cagri.append(yol)
        return model
    return yukle, cagri


# ---------------------------------------------------------------- ayar
def test_varsayilan_kapali_ve_ayar_okunamazsa_kapali():
    assert Settings().mod_c_musteri == "kapali" and Settings().mod_c_onayli_artefakt == ""
    assert mb.mod_c_aktivasyon(_ayar()) == {"etkin": False, "onayli": frozenset()}
    assert mb.mod_c_aktivasyon(_ayar(mod_c_musteri="ACIK ", mod_c_onayli_artefakt=" AbC123 , def456,, ")) == {"etkin": True, "onayli": frozenset({"abc123", "def456"})}
    assert mb.mod_c_aktivasyon(object()) == {"etkin": False, "onayli": frozenset()}          # alan yok → kapalı

    class _Patlak:
        @property
        def mod_c_musteri(self):
            raise RuntimeError("ayar katmanı bozuk")
    assert mb.mod_c_aktivasyon(_Patlak()) == {"etkin": False, "onayli": frozenset()}          # istisna → kapalı
    with pytest.raises(Exception):   # noqa: B017 — Literal dışı değer kabul edilmez (yanlış yazım açık anlamına gelmez)
        Settings(mod_c_musteri="evet")


# ---------------------------------------------------------------- karar zinciri (saf)
def test_bayrak_kapali_dosyaya_dokunmaz_ve_b(tmp_path):
    yol, _sha = _dosya(tmp_path, b"\x80\x04garbage")
    yukle, cagri = _sayac(_uyumlu_model())
    g = _girdi()
    mb.ml_artefakti_sec(g, yol, mb.mod_c_aktivasyon(_ayar()), yukle=yukle, sha16=fs._artefakt_sha16)
    assert (g.mode, g.model, g.ml_model_id, g.artefakt_sha16, g.geri_dusus) == ("B", None, None, None, "mod_c_kapali") and cagri == []


def test_kayit_yok_ve_dosya_yok_eski_davranis(tmp_path):
    yukle, cagri = _sayac(_uyumlu_model())
    g = _girdi()
    mb.ml_artefakti_sec(g, None, mb.mod_c_aktivasyon(_ayar(mod_c_musteri="acik")), yukle=yukle, sha16=fs._artefakt_sha16)
    assert (g.mode, g.geri_dusus) == ("B", "hibrit_artefakt_yok") and cagri == []
    g = _girdi()
    mb.ml_artefakti_sec(g, str(tmp_path / "yok.pkl"), mb.mod_c_aktivasyon(_ayar(mod_c_musteri="acik", mod_c_onayli_artefakt="x")), yukle=yukle, sha16=fs._artefakt_sha16)
    assert (g.mode, g.geri_dusus) == ("B", "hibrit_artefakt_yok") and cagri == []           # v2.80 vakası korunur


def test_onaysiz_veya_bozuk_dosya_pickle_yuklenmez(tmp_path):
    yol, sha = _dosya(tmp_path, pickle.dumps({"tur": "sahte"}))
    yukle, cagri = _sayac(_uyumlu_model())
    g = _girdi()
    mb.ml_artefakti_sec(g, yol, mb.mod_c_aktivasyon(_ayar(mod_c_musteri="acik", mod_c_onayli_artefakt="baskasha0000000")), yukle=yukle, sha16=fs._artefakt_sha16)
    assert (g.mode, g.geri_dusus) == ("B", "hibrit_artefakt_onaysiz") and cagri == []
    bozuk, _ = _dosya(tmp_path, b"bu bir pickle degil")                                       # bozuk dosya: sha onaylı değil → açılmaz
    g = _girdi()
    mb.ml_artefakti_sec(g, bozuk, mb.mod_c_aktivasyon(_ayar(mod_c_musteri="acik", mod_c_onayli_artefakt=sha)), yukle=fs._model_yukle, sha16=fs._artefakt_sha16)
    assert (g.mode, g.geri_dusus) == ("B", "hibrit_artefakt_onaysiz")


def test_onayli_ama_uyumsuz_b_onayli_uyumlu_c(tmp_path):
    yol, sha = _dosya(tmp_path, pickle.dumps({"tur": "sahte"}))
    akt = mb.mod_c_aktivasyon(_ayar(mod_c_musteri="acik", mod_c_onayli_artefakt=sha.upper()))
    # uyumsuz: sınıf adı farklı / sürüm farklı / özellik şeması farklı
    yukle, cagri = _sayac({"tur": "sahte"})
    g = _girdi()
    mb.ml_artefakti_sec(g, yol, akt, yukle=yukle, sha16=fs._artefakt_sha16)
    assert (g.mode, g.geri_dusus) == ("B", "hibrit_artefakt_uyumsuz") and cagri == [yol]
    m = _uyumlu_model()
    m.MODEL_VERSION = "9.9.9"
    g = _girdi()
    mb.ml_artefakti_sec(g, yol, akt, yukle=_sayac(m)[0], sha16=fs._artefakt_sha16)
    assert g.geri_dusus == "hibrit_artefakt_uyumsuz"
    m = _uyumlu_model()
    m._booster = _Booster(hr.FEATURE_COLUMNS[:-1])
    g = _girdi()
    mb.ml_artefakti_sec(g, yol, akt, yukle=_sayac(m)[0], sha16=fs._artefakt_sha16)
    assert g.geri_dusus == "hibrit_artefakt_uyumsuz"
    assert mb.artefakt_uyumlu(_uyumlu_model()) == (True, None)
    # uyumlu + onaylı → C
    m = _uyumlu_model()
    g = _girdi()
    mb.ml_artefakti_sec(g, yol, akt, yukle=_sayac(m)[0], sha16=fs._artefakt_sha16)
    assert (g.mode, g.model is m, g.artefakt_sha16, g.geri_dusus) == ("C", True, sha, None)


# ---------------------------------------------------------------- tahmin davranışı (bayrak kapalı = Mod B zinciri birebir)
@pytest.fixture(autouse=True)
def _bant_kapali(monkeypatch):
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="model", ensemble_min_uye=20))


def test_bayrak_kapali_tahmin_mod_b_ile_birebir():
    simdi = pd.Timestamp("2026-06-21", tz="UTC")
    g = _girdi("C")
    mb.ml_artefakti_sec(g, "/var/artifacts/hyb_x.pkl", mb.mod_c_aktivasyon(_ayar()), yukle=fs._model_yukle, sha16=fs._artefakt_sha16)
    s_bekci = fs.tahmin_uret(PLANT, _meteo(), g, simdi=simdi)
    s_b = fs.tahmin_uret(PLANT, _meteo(), fs.TahminGirdisi(mode="B", kalibrasyon_id="kal", kalibrasyon_params=KALIBRASYON), simdi=simdi)
    assert (s_bekci.mode, s_bekci.model_adi, s_bekci.ml_model_id, s_bekci.geri_dusus) == ("B", "barhdadi_bennis", None, "mod_c_kapali")
    assert np.allclose(s_bekci.h["p50_kw"], s_b.h["p50_kw"]) and s_bekci.h["ml_kw"].isna().all()   # fizik zinciri aynı


# ---------------------------------------------------------------- zamanlanmış kalibrasyon aktivasyon vermez
def test_kalibrasyon_yazari_aktivasyon_notu_ve_kapi_degismedi():
    import inspect

    from pvquant.services import calib_service as cs
    src = inspect.getsource(cs.kalibre_et)
    assert "musteri_aktivasyon" in src and "aylık kalibrasyon müşteri aktivasyonu vermez" in src
    assert "INSERT INTO ml_models" in src and "active) VALUES(:t,:p,:y,:r,true)" in src         # yazıcı/ kayıt sözleşmesi değişmedi
    assert "gate_min_improvement_pct" in src and "gate_wmape_ceiling" in src                      # kapı eşikleri ayardan, dokunulmadı
    assert "kalibre_et(plant[\"tenant_id\"], plant, hibrit=True)" in (KOK / "apps/worker/main.py").read_text()   # zamanlı iş kapatılmadı
    assert "ml_artefakti_sec" in inspect.getsource(fs.girdileri_topla) and "_model_yukle(ml.artifact_path)" not in inspect.getsource(fs.girdileri_topla)
