"""Faz 1 gölge MOTORU (28.11.2026) — DB'siz, ağsız testler. Sözleşme:
- Varsayılan KAPALI: `golge_etkin=kapali` → hiçbir bağımlılık çağrılmaz; santral listede değilse de koşmaz (açık santral onayı + kaynak sınırı).
- Aynı NWP yayını: gölge meteosunun `kosu_zamani` yayın koşusununkine eşit değilse atlanır (hata değil).
- Gölge C fail-closed: `mod_c_golge=kapali` ya da sha onaysız → pickle AÇILMAZ, C→B düşüşü not edilir; C gölgesi yazılmaz (B zaten var).
- Tekilleştirme: aynı (santral, mod, model, NWP yayını) için ikinci gölge satırı yazılmaz.
- Arşiv hatası bir modu düşürür, diğerini engellemez; durum 'kismi' (jobs_log görür).
- Değerlendirme: aynı maske (gerçek > %2 kWp ∧ her modda p50), kovalar 00-24/24-48, PICP80 yalnız bant varsa; eşikler donmuş (25/75–85/5).
Müşteri yolu (`girdileri_topla` + `mod_c_bekcisi.ml_artefakti_sec` müşteri bayrağıyla) DEĞİŞMEZ.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from pvquant.services import golge_service as gs
from pvquant.services import mod_c_bekcisi as bek
from pvquant.services.forecast_service import TahminGirdisi

PLANT = {"id": "11111111-1111-1111-1111-111111111111", "tenant_id": "t1", "name": "Gölge Test", "capacity_kwp": 1000.0,
         "lat": 37.0, "lon": 33.0, "tz": "Europe/Istanbul"}
NWP = pd.Timestamp("2026-12-01 00:00", tz="UTC")
SIMDI = pd.Timestamp("2026-12-01 02:00", tz="UTC")


def _ayar(**k):
    taban = {"golge_etkin": "kapali", "golge_santraller": "", "golge_modlar": "A,B,C", "mod_c_golge": "kapali", "mod_c_onayli_artefakt": "",
             "mod_c_musteri": "kapali"}
    taban.update(k)
    return SimpleNamespace(**taban)


def _patlat(*a, **k):
    raise AssertionError("kapalıyken bağımlılık çağrılmamalı")


# ---------------------------------------------------------------- kapılar
def test_varsayilan_kapali_hic_bir_bagimlilik_cagrilmaz():
    from pvquant.config import Settings
    assert Settings.model_fields["golge_etkin"].default == "kapali"
    assert Settings.model_fields["mod_c_golge"].default == "kapali"
    assert Settings.model_fields["golge_santraller"].default == ""
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=_ayar(), meteo_getir=_patlat, girdi_getir=_patlat, nwp_yayin_getir=_patlat,
                                 tekrar_var=_patlat, arsivle=_patlat)
    assert r == {"durum": "atlandi", "neden": "golge_etkin=kapali"}
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=_ayar(golge_etkin="acik"), meteo_getir=_patlat, girdi_getir=_patlat,
                                 nwp_yayin_getir=_patlat, tekrar_var=_patlat, arsivle=_patlat)
    assert r["durum"] == "atlandi" and "listesinde" in r["neden"]
    assert gs.golge_ayarlari(object())["etkin"] is False   # ayar okunamazsa kapalı


def test_devre_kesici_ardisik_hata_sinirinda_durur():
    ayar = _ayar(golge_etkin="acik", golge_santraller=PLANT["id"])
    assert gs.golge_ayarlari(ayar)["hata_sinir"] == 3 and gs.golge_ayarlari(_ayar(golge_ardisik_hata_sinir=0))["hata_sinir"] == 1
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=ayar, ardisik_hata_getir=lambda t, p: 3, nwp_yayin_getir=_patlat, meteo_getir=_patlat, girdi_getir=_patlat)
    assert r["durum"] == "atlandi" and "devre kesici" in r["neden"] and r["ardisik_hata"] == 3
    # sınır altı → akış sürer (yayın yok → bir sonraki kapıda atlanır)
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=ayar, ardisik_hata_getir=lambda t, p: 2, nwp_yayin_getir=lambda *a: None, meteo_getir=_patlat, girdi_getir=_patlat)
    assert "yayın koşusu yok" in r["neden"]


def test_yayin_yoksa_ve_meteo_farkliysa_atlanir():
    ayar = _ayar(golge_etkin="acik", golge_santraller=PLANT["id"])
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=ayar, nwp_yayin_getir=lambda *a: None, meteo_getir=_patlat, girdi_getir=_patlat, ardisik_hata_getir=lambda t, p: 0)
    assert r["durum"] == "atlandi" and "yayın koşusu yok" in r["neden"]
    meteo = SimpleNamespace(kosu_zamani=NWP - pd.Timedelta(hours=6))
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=ayar, nwp_yayin_getir=lambda *a: NWP, meteo_getir=lambda p: meteo, girdi_getir=_patlat, ardisik_hata_getir=lambda t, p: 0)
    assert r["durum"] == "atlandi" and "aynı değil" in r["neden"]


# ---------------------------------------------------------------- gölge C fail-closed
def test_golge_c_bekcisi_fail_closed_ve_musteri_bayragindan_bagimsiz(tmp_path):
    a = bek.golge_aktivasyon(_ayar())
    assert a == {"etkin": False, "onayli": frozenset()}
    a = bek.golge_aktivasyon(_ayar(mod_c_golge="acik", mod_c_onayli_artefakt="ABCDEF0123456789, ffff"))
    assert a["etkin"] is True and a["onayli"] == frozenset({"abcdef0123456789", "ffff"})
    assert bek.golge_aktivasyon(object())["etkin"] is False
    # müşteri bayrağı açık olsa bile gölge bayrağı kapalıysa gölge C yüklenmez (ayrı kapı)
    a = bek.golge_aktivasyon(_ayar(mod_c_musteri="acik"))
    assert a["etkin"] is False
    acildi = []
    g = TahminGirdisi(mode="C")
    bek.ml_artefakti_sec(g, "/x/model.pkl", bek.golge_aktivasyon(_ayar(mod_c_golge="acik")), yukle=lambda y: acildi.append(y), sha16=lambda y: "deadbeefdeadbeef")
    assert g.mode == "B" and g.geri_dusus == bek.GERI_DUSUS_ONAYSIZ and acildi == [], "onaysız sha → pickle açılmaz"


def _girdi_ve_calistir(monkeypatch, *, model_var: bool, arsiv_hata: set | None = None, tekrar: set | None = None, ayar=None):
    """golge_calistir'ı sahte sonuçlarla değiştirir: her mod için mode_gerceklesen (C artefaktsızsa B)."""
    ayar = ayar or _ayar(golge_etkin="acik", golge_santraller=PLANT["id"])
    meteo = SimpleNamespace(kosu_zamani=NWP)
    girdi = TahminGirdisi(mode="B", kalibrasyon_id="kal", model=(object() if model_var else None))

    def sahte_calistir(plant, m, g, modlar, simdi):
        out = {}
        for mod in modlar:
            gerc = mod if (mod != "C" or g.model is not None) else "B"
            out[mod] = SimpleNamespace(mod=mod, mode_gerceklesen=gerc, model_adi=("hybrid_residual" if gerc == "C" else "barhdadi_bennis"),
                                       geri_dusus=(None if gerc == mod else "hibrit_artefakt_yok"), ufuk_saat=48, girdi=g, run_id=None)
        return out
    monkeypatch.setattr(gs, "golge_calistir", sahte_calistir)
    monkeypatch.setattr(gs, "_aktif_artefakt_yolu", lambda t, p: "/x/model.pkl")   # dosya var ama gölge bayrağı kapalı → dokunulmaz
    yazilan = []

    def arsivle(t, p, m, snc):
        if arsiv_hata and snc.mod in arsiv_hata:
            raise RuntimeError("DB kısıtı")
        yazilan.append(snc.mod)
        return SimpleNamespace(run_id=f"run-{snc.mod}")
    r = gs.golge_motoru_calistir(PLANT, simdi=SIMDI, ayar=ayar, nwp_yayin_getir=lambda *a: NWP, meteo_getir=lambda p: meteo,
                                 girdi_getir=lambda p: girdi, tekrar_var=lambda t, p, mode, model, nwp: mode in (tekrar or set()), arsivle=arsivle,
                                 ardisik_hata_getir=lambda t, p: 0)
    return r, yazilan


def test_c_artefakti_yoksa_c_golgesi_yazilmaz_dusus_gizlenmez(monkeypatch):
    r, yazilan = _girdi_ve_calistir(monkeypatch, model_var=False)
    assert yazilan == ["A", "B"]
    assert r["durum"] == "ok" and r["modlar"]["C"]["durum"] == "atlandi" and "C→B" in r["modlar"]["C"]["neden"]
    assert r["golge_c"] == bek.GERI_DUSUS_KAPALI   # mod_c_golge kapalı → artefakt dosyasına dokunulmadı
    assert r["modlar"]["A"]["run_id"] == "run-A" and r["nwp_kosu_zamani"] == str(NWP)


def test_tekrar_ve_arsiv_hatasi(monkeypatch):
    r, yazilan = _girdi_ve_calistir(monkeypatch, model_var=True, tekrar={"A", "B"})
    assert yazilan == ["C"] and r["modlar"]["A"]["durum"] == "atlandi" and r["modlar"]["B"]["durum"] == "atlandi" and r["modlar"]["C"]["durum"] == "ok"
    r, yazilan = _girdi_ve_calistir(monkeypatch, model_var=True, arsiv_hata={"B"})
    assert yazilan == ["A", "C"] and r["durum"] == "kismi" and r["modlar"]["B"]["durum"] == "error"
    r, _ = _girdi_ve_calistir(monkeypatch, model_var=True, tekrar={"A", "B", "C"})
    assert r["durum"] == "atlandi"


def test_kosu_kimligi_deterministik():
    k1 = gs.golge_kosu_kimligi(PLANT["id"], "B", "barhdadi_bennis", NWP)
    k2 = gs.golge_kosu_kimligi(PLANT["id"], "B", "barhdadi_bennis", NWP.tz_convert("Europe/Istanbul"))
    assert k1 == k2 and k1[-1] == "2026-12-01T00:00:00+00:00"
    assert gs.golge_kosu_kimligi(PLANT["id"], "B", "barhdadi_bennis", None)[-1] is None


# ---------------------------------------------------------------- değerlendirme (saf)
def _df():
    ts = pd.date_range("2026-12-02 03:00", periods=20, freq="h", tz="UTC")
    gercek = pd.Series(np.r_[np.zeros(3), np.linspace(50, 800, 7), np.linspace(800, 50, 7), np.zeros(3)], index=ts)
    satirlar = []
    for mod, hata, bant in (("yayin", 1.10, None), ("golge_B", 1.05, None), ("golge_C", 0.98, 0.25)):
        for i, t in enumerate(ts):
            if mod == "golge_C" and i == 10:   # bir saat eksik → o saat HER mod için maske dışı
                continue
            p50 = float(gercek[t]) * hata
            satirlar.append({"ts_utc": t, "mod": mod, "ufuk_saat": 24 + i, "p50_kw": p50, "gercek_kw": float(gercek[t]),
                             "p10_kw": (p50 * (1 - bant) if bant else None), "p90_kw": (p50 * (1 + bant) if bant else None)})
    return pd.DataFrame(satirlar)


def test_degerlendirme_ayni_maske_ve_metrikler():
    out = gs.golge_degerlendir_df(_df(), capacity_kwp=1000.0)
    k = {(r["mod"], r["kova"]): r for r in out}
    assert set(k) == {("yayin", "24-48"), ("golge_B", "24-48"), ("golge_C", "24-48")}
    n = {r["mod"]: r["n"] for r in out}
    assert len(set(n.values())) == 1 and n["yayin"] == 13, "aynı maske: gündüz 14 saat − C'de eksik 1 saat = 13, her modda aynı"
    assert abs(k[("yayin", "24-48")]["wmape"] - 10.0) < 0.05 and abs(k[("golge_B", "24-48")]["sapma_pct"] - 5.0) < 0.05
    assert abs(k[("golge_C", "24-48")]["wmape"] - 2.0) < 0.05 and k[("golge_C", "24-48")]["picp80"] == 100.0
    assert k[("yayin", "24-48")]["picp80"] is None and k[("yayin", "24-48")]["esik"]["picp80"] is None
    assert k[("golge_C", "24-48")]["esik"] == {"wmape": True, "sapma": True, "picp80": False}   # 100 > 85: bant fazla geniş
    assert k[("golge_B", "24-48")]["esik"]["sapma"] is True and k[("yayin", "24-48")]["esik"]["sapma"] is False
    assert gs.GOLGE_ESIKLER == {"wmape_tavan": 25.0, "picp80_alt": 75.0, "picp80_ust": 85.0, "sapma_tavan": 5.0}


def test_degerlendirme_bos_ve_kova_disi():
    assert gs.golge_degerlendir_df(pd.DataFrame(), 1000.0) == []
    d = _df()
    d["ufuk_saat"] = 60
    assert gs.golge_degerlendir_df(d, 1000.0) == []


def test_golge_modlari_sozlugu():
    assert gs.golge_ayarlari(_ayar(golge_modlar="B, c ,x"))["modlar"] == ("B", "C")
    assert gs.golge_ayarlari(_ayar(golge_etkin="acik", golge_santraller=f" {PLANT['id'].upper()} ,"))["santraller"] == frozenset({PLANT["id"]})


@pytest.mark.parametrize("bayrak", ["acik", "kapali"])
def test_worker_kancasi_yalniz_bayrakla(bayrak, monkeypatch):
    """apps/worker/main.tam_tur: gölge işi yalnız golge_etkin=acik iken _logla ile sarılır; kapalıyken jobs_log satırı bile düşmez."""
    import importlib
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "worker"))
    m = importlib.import_module("main")
    cagrilar = []
    monkeypatch.setattr(m, "_logla", lambda job, fn: (lambda: cagrilar.append(job)))
    monkeypatch.setattr(m, "_logla_tek", lambda job, fn: (lambda: cagrilar.append(job)))
    monkeypatch.setattr(m.golge_service, "golge_ayarlari", lambda ayar=None: {"etkin": bayrak == "acik", "santraller": frozenset(), "modlar": ("A",)})
    m.tam_tur()
    assert ("golge_tahmin" in cagrilar) is (bayrak == "acik")
    assert cagrilar.index("sabah_tahmin") < cagrilar.index("alarm")
    if bayrak == "acik":
        assert cagrilar.index("sabah_tahmin") < cagrilar.index("golge_tahmin") < cagrilar.index("alarm")
