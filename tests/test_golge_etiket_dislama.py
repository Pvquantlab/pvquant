"""Faz 1 G1/G3/G2 (26.11.2026, kısıtlı kapsam) — gölge etiketi, dışlama kuralı ve paralel mod arayüzleri (DB'siz).

- G1 depolama (göç v2667): 'golge' kod sözlüğü = göç sözlüğü (yalnız ekleme, eski 8 etiket aynen); downgrade bekçisi gölge satırı varsa durur;
  DB: golge_arsivle mevcut arsive_yaz sözleşmesiyle künye (id/mode/model/run_at/ufuk_saat/kalibrasyon_id/etiket) yazar.
- G3 dışlama: yayin_kosu_sql + geriye_bakisli + musteri_kosusu_mu gölgeyi dışarıda tutar; eksik etiket 'yayin' sayılır (geriye uyum);
  bagimsiz_dogrulama.kosu_sec gölge koşuyu hiçbir kuralda seçmez (simülasyonda da); golge_disi_sql koşu geçmişi/damga/kullanım/platform
  sorgularında; DB'de son koşu, yayımlanmış koşu, koşu geçmişi ve damga daha YENİ gölge koşuyu görmez.
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
from sqlalchemy import text
from test_altin_cekirdek import KALIBRASYON, PLANT, _meteo
from test_kosu_kunyesi_v2572 import (  # noqa: F401 — DB fixture'ı (tenant+plant+kalibrasyon, teardown siler)
    _sentetik_meteo,
    santral,
)

from pvquant.db import sistem_baglami
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import damga_service as ds
from pvquant.services import ensemble_service as es
from pvquant.services import forecast_service as fs
from pvquant.services import golge_service as gs
from pvquant.services import karne_kurali as kk

KOK = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- G1 depolama (göç v2667)
def _modul(ad: str, dosya: str):
    spec = importlib.util.spec_from_file_location(ad, KOK / "alembic" / "versions" / dosya)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_g1_golge_sozlugu_goc_ile_birebir_yalniz_ekleme():
    assert kk.ETIKET_GOLGE == "golge" and kk.ETIKET_GOLGE in kk.ETIKETLER and gs.golge_kayit_izinli()
    goc, eski = _modul("v2667", "v2667_golge_etiket.py"), _modul("v2597", "v2597_arsiv_kunye.py")
    assert tuple(goc.ETIKETLER) == tuple(kk.ETIKETLER)                      # kod sözlüğü = DB CHECK sözlüğü
    assert tuple(goc.ESKI_ETIKETLER) == tuple(eski.ETIKETLER) and tuple(goc.ETIKETLER[:-1]) == tuple(eski.ETIKETLER)   # yalnız sona ekleme
    assert goc.down_revision == "v2650_ens_ham_bant" and goc.KISIT == "forecast_runs_etiket_check"
    assert "NOT NULL" not in goc._kisit_sql(goc.ETIKETLER) and "DEFAULT" not in goc._kisit_sql(goc.ETIKETLER)   # kolon/varsayılan dokunulmaz
    with pytest.raises(ValueError, match="sözlük dışı"):   # sözlük kapısı duruyor
        fs.arsive_yaz(None, PLANT, None, None, etiket="yok_boyle")


def test_g1_downgrade_bekcisi_golge_satiri_varsa_durur():
    goc = _modul("v2667b", "v2667_golge_etiket.py")

    class _Baglanti:
        def __init__(self, n):
            self.n = n

        def execute(self, *a, **k):
            return SimpleNamespace(scalar=lambda: self.n)

    assert goc.golge_satir_kontrol(_Baglanti(0)) == 0
    with pytest.raises(RuntimeError, match="2 'golge'"):
        goc.golge_satir_kontrol(_Baglanti(2))


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


def test_g3_golge_disi_sql_ve_tuketiciler():
    import inspect

    from pvquant.services import kullanim_service, platform_service
    assert kk.golge_disi_sql("r") == "COALESCE(r.etiket, 'yayin') <> 'golge'" and kk.golge_disi_sql("") == "COALESCE(etiket, 'yayin') <> 'golge'"
    assert "golge_disi_sql" in inspect.getsource(fs.kosu_gecmisi)                      # müşteri geçmiş koşular tablosu
    assert inspect.getsource(ds).count("golge_disi_sql('r')") == 3                      # damga: santral / kiracı / portföy son koşu
    assert inspect.getsource(kullanim_service).count("golge_disi_sql('')") == 2         # kiracı kullanım sayacı (2 sorgu)
    assert "golge_disi_sql('r')" in inspect.getsource(platform_service)                 # platform santral listesi son koşu


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


# ---------------------------------------------------------------- G1+G3 DB entegrasyonu (test DB; göç v2667 uygulanmış olmalı)
def test_g1_g3_db_golge_arsiv_kunye_ve_musteri_yuzeyleri_gormez(santral):   # noqa: F811 — pytest fixture parametresi
    tid, plant, cid = santral
    simdi = pd.Timestamp.now("UTC").floor("h")
    meteo = _sentetik_meteo(simdi.strftime("%Y-%m-%d"), 3, kosu_zamani=simdi - pd.Timedelta(hours=6))
    girdi = fs.TahminGirdisi(mode="B", kalibrasyon_id=cid, kalibrasyon_params={"eta_bos": 0.85}, sapma_ayar={"aktif": False, "neden": "test"})
    # 1) normal yayın koşusu (eski sözleşme: etiket None → 'yayin'), gölgeden 1 saat ÖNCE
    yayin_an = simdi - pd.Timedelta(hours=1)
    yayin_id = fs.arsive_yaz(tid, plant, meteo, fs.tahmin_uret(plant, meteo, girdi, simdi=yayin_an), kalibrasyon_id=cid, etiket=None, girdi=girdi)
    # 2) gölge A/B koşuları (daha YENİ) — izole arayüz + G1 arşiv yolu
    golge = gs.golge_calistir(plant, meteo, girdi, modlar=("A", "B"), simdi=simdi)
    assert all(g.run_id is None for g in golge.values())
    kayit = {m: gs.golge_arsivle(tid, plant, meteo, g) for m, g in golge.items()}
    with sistem_baglami() as s:
        satirlar = s.execute(text("SELECT id, etiket, mode, model, run_at, ufuk_saat, kalibrasyon_id, meteo_ozet_json->>'etiket' AS je, satir_sayisi, "
                                  "(SELECT count(*) FROM forecast_values v WHERE v.run_id = r.id) AS n FROM forecast_runs r WHERE tenant_id = :t ORDER BY run_at, mode"),
                             {"t": tid}).mappings().all()
    assert [r["etiket"] for r in satirlar] == ["yayin", "golge", "golge"] and [r["je"] for r in satirlar] == ["yayin", "golge", "golge"]
    g_a, g_b = satirlar[1], satirlar[2]
    assert str(g_a["id"]) == kayit["A"].run_id and str(g_b["id"]) == kayit["B"].run_id and str(satirlar[0]["id"]) == yayin_id
    assert (g_a["mode"], g_b["mode"]) == ("A", "B") and g_a["model"] == g_b["model"] == "barhdadi_bennis"      # kimlik: mod + model
    assert pd.Timestamp(g_a["run_at"]).tz_convert("UTC") == simdi == pd.Timestamp(g_b["run_at"]).tz_convert("UTC")   # yayın zamanı
    assert g_a["ufuk_saat"] == kayit["A"].ufuk_saat > 0 and g_a["satir_sayisi"] == g_a["n"] == len(kayit["A"].h)   # ufuk + bütünlük
    assert g_a["kalibrasyon_id"] is None and str(g_b["kalibrasyon_id"]) == cid                                  # A kalibrasyonsuz, B kalibre
    assert all(kk.musteri_kosusu_mu(r["etiket"]) == (r["etiket"] == "yayin") for r in satirlar)
    # 3) G3: müşteri yüzeyleri daha yeni gölgeyi GÖRMEZ, eski kayıt (etiket NULL yazılmış → 'yayin') aynen geçerli
    gecmis = fs.kosu_gecmisi(tid, plant["id"], n=10)
    assert len(gecmis) == 1 and gecmis[0].etiket == "yayin" and pd.Timestamp(gecmis[0].run_at).tz_convert("UTC") == yayin_an
    hedef = kayit["A"].h.index[30]
    yk = fs.yayimlanmis_kosu(tid, plant["id"], hedef, yayin_oncesi=simdi + pd.Timedelta(minutes=5))
    assert yk is not None and yk["kosu"]["run_id"] == yayin_id and yk["kosu"]["etiket"] == "yayin"
    sk = fs.son_kosu(tid, plant["id"])
    assert sk is not None and len(sk) == len(kayit["B"].h)
    damga = ds.hesapla(tid, plant["id"])
    assert pd.Timestamp(damga["son_kosu"]).tz_convert("UTC") == yayin_an                                        # gölge damgayı oynatmaz
