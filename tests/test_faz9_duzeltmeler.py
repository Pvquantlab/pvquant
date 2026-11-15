"""Faz 9 düzeltmeleri (15.11.2026; P1 = F9-B01, P2 = F9-D01, P6 = F9-D02, P7 = F9-A04, P8 = F9-F01, P16 = F9-E05, P17 = F9-E09, A03) için CI regresyon testleri.
P1/P2 sentetik ve DB'siz; P8 test DB ister.

P1: bağımsız doğrulama bütünlük paydası, tahmin ve geçerli ölçümün BİRLİKTE eksik olduğu astronomik gündüz saatlerini de sayar
    (`butunluk(..., konum=...)`); aksi hâlde «Değerlendirilen ölçüm» oranı şişiyordu (sentetik: %100 yerine doğru 8/12 = %66,7).
P2: portföy finansal ana toplamı, santral FEM'inde `toplanir=False` işaretli bileşeni (dağıtıma bağlı lisanssız santralın bilgi amaçlı
    EDT/KÜPST'ü) toplamaz; tutar ayrı bilgi satırında görünür (sentetik: doğru 1.400 TL, düzeltme öncesi 1.000 TL).
Kaynak: ~/Desktop/PVQuant_Faz9_Basari_Dogrulama/12_Oncelikli_Duzeltme_Plani.md P1, P2."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.platform import portfoy_finans as pf
from pvquant.services import bagimsiz_dogrulama_service as bd

TZ = "Europe/Istanbul"
KAP = 1000.0
KONUM = (37.87, 32.48)   # Konya civarı (sentetik)


def _gun(gun: str, prof: np.ndarray, kayip: list[int], tahmin_de_yok: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    ts = pd.date_range(pd.Timestamp(gun, tz=TZ), periods=24, freq="1h").tz_convert("UTC")
    eksik = np.isin(np.arange(24), kayip)
    saatler = pd.DataFrame({"ts_utc": ts, "kwh": np.where(eksik, np.nan, prof), "durum": np.where(eksik, "eksik", "olculdu"),
                            "neden": np.where(eksik, "eksik", None), "kirpma": False})
    t = pd.DataFrame({"ts_utc": ts, "run_at": pd.Timestamp(gun, tz=TZ).tz_convert("UTC") - pd.Timedelta(hours=12), "run_id": "r1",
                      "p50_kw": prof * 1.05, "p10_kw": prof * 0.9, "p90_kw": prof * 1.1, "physics_kw": prof, "model": "hibrit",
                      "meteo_source": "open-meteo", "etiket": "yayin"})
    if tahmin_de_yok:
        t = t[~eksik]
    d = bd.eslestir(bd.kosu_sec(t, "program", TZ), saatler, TZ)
    return d, bd.degerlendirilebilir(d, KAP)


def _yaz_profili() -> np.ndarray:
    h = np.arange(24)
    return np.clip(900 * np.sin(np.pi * (h - 6) / 13), 0, None)   # yerel 07–18 > %2 kWp (12 saat)


def test_p1_ortak_kesinti_saatleri_paydaya_girer():
    prof = _yaz_profili()
    gunduz = np.where(prof > 0.02 * KAP)[0]
    d, e = _gun("2026-06-10", prof, list(gunduz[3:7]))
    b = bd.butunluk(d, e, {}, KAP, konum=KONUM)
    assert b["gunduz_saat"] == 12 and b["gunduz_saat_gozlenen"] == 8 and b["gunduz_saat_veri_yok_eklenen"] == 4
    assert b["degerlendirilen_saat"] == 8 and b["degerlendirilen_pct"] == pytest.approx(66.7, abs=0.06)
    assert b["gunduz_dislanan"] == {"eksik": 4}


def test_p1_gece_eksik_saatleri_paydaya_girmez():
    """Gece (astronomik) eksik saatler paydaya eklenmez: oran tam veride %100 kalır."""
    prof = _yaz_profili()
    d, e = _gun("2026-06-10", prof, [0, 1, 2, 23])   # yerel 00–02 ve 23: gece
    b = bd.butunluk(d, e, {}, KAP, konum=KONUM)
    assert b["gunduz_saat_veri_yok_eklenen"] == 0 and b["degerlendirilen_pct"] == 100.0


def test_p1_gecerli_dusuk_uretim_saati_payday_eklenmez():
    """Geçerli ama %2 kWp altı ölçüm (şafak/çok bulutlu) gözlenen maske dışında kalır ve EKLENMEZ — oran yapay düşmez."""
    prof = _yaz_profili()
    prof[[7, 18]] = 5.0                               # ölçülü ama düşük
    d, e = _gun("2026-06-10", prof, [])
    b = bd.butunluk(d, e, {}, KAP, konum=KONUM)
    assert b["gunduz_saat_veri_yok_eklenen"] == 0 and b["degerlendirilen_pct"] == 100.0


def test_p1_tum_gun_kesintisi_kis_gunu():
    """Kış günü (Aralık) tam gün ortak kesinti: payda astronomik gündüz saatlerinden oluşur, değerlendirilen %0 (önce: payda 0 → None)."""
    prof = np.zeros(24)
    d, e = _gun("2026-12-21", prof, list(range(24)))
    b = bd.butunluk(d, e, {}, KAP, konum=KONUM)
    assert 8 <= b["gunduz_saat"] <= 11 and b["degerlendirilen_pct"] == 0.0
    assert bd.butunluk(d, e, {}, KAP)["degerlendirilen_pct"] is None   # konumsuz eski davranış


def test_p1_hesapla_saf_konum_yolunu_kullanir_ve_sozluk_surumu():
    prof = _yaz_profili()
    gunduz = np.where(prof > 0.02 * KAP)[0]
    gun = "2026-06-10"
    ts = pd.date_range(pd.Timestamp(gun, tz=TZ), periods=24, freq="1h").tz_convert("UTC")
    eksik = np.isin(np.arange(24), gunduz[3:7])
    saatler = pd.DataFrame({"ts_utc": ts, "kwh": np.where(eksik, np.nan, prof), "durum": np.where(eksik, "eksik", "olculdu"),
                            "neden": np.where(eksik, "eksik", None), "kirpma": False})
    t = pd.DataFrame({"ts_utc": ts, "run_at": pd.Timestamp(gun, tz=TZ).tz_convert("UTC") - pd.Timedelta(hours=12), "run_id": "r1",
                      "p50_kw": prof * 1.05, "p10_kw": np.nan, "p90_kw": np.nan, "physics_kw": prof, "model": "hibrit",
                      "meteo_source": "open-meteo", "etiket": "yayin"})[~eksik]
    r = bd.hesapla_saf(t, saatler, {}, {"capacity_kwp": KAP, "tz": TZ, "lat": KONUM[0], "lon": KONUM[1]},
                       pd.Timestamp(gun, tz=TZ), pd.Timestamp(gun, tz=TZ) + pd.Timedelta(days=1))
    assert r["butunluk"]["degerlendirilen_pct"] == pytest.approx(66.7, abs=0.06)
    assert r["butunluk"]["payda_kurali"].startswith("gözlenen gündüz ∪")
    assert r["meta"]["sozluk_surumu"] == bd.SOZLUK_SURUMU == "2026-11-14"
    assert r["metrik"]["wmape"] == pytest.approx(5.0, abs=0.01)   # metrik maskesi değişmedi


def _oz(edt, toplanir, kupst=-100.0, gelir=1000.0):
    return {"bilesenler": [
        {"kod": pf.KOD_GELIR, "tutar_tl": gelir, "alacak_tl": gelir, "borc_tl": 0.0, "nitelik": "hesaplanan", "toplanir": True},
        {"kod": pf.KOD_EDT, "tutar_tl": edt, "alacak_tl": max(edt, 0.0), "borc_tl": max(-edt, 0.0), "nitelik": "hesaplanan", "toplanir": toplanir},
        {"kod": pf.KOD_KUPST, "tutar_tl": kupst, "alacak_tl": 0.0, "borc_tl": -kupst, "nitelik": "hesaplanan", "toplanir": toplanir}]}


def test_p2_toplanmaz_bilesen_ana_toplama_girmez_bilgi_satirinda_gorunur():
    r = pf.birlestir({"S1": _oz(-500.0, True), "S2": _oz(-300.0, False)})
    k = {b["kod"]: b for b in r["bilesenler"]}
    assert k[pf.KOD_EDT]["tutar_tl"] == pytest.approx(-500.0) and k[pf.KOD_KUPST]["tutar_tl"] == pytest.approx(-100.0)
    assert r["toplam"]["tutar_tl"] == pytest.approx(1400.0)
    assert k[f"{pf.KOD_EDT}_toplanmayan"]["tutar_tl"] == pytest.approx(-300.0) and not k[f"{pf.KOD_EDT}_toplanmayan"]["toplanir"]
    assert k[f"{pf.KOD_KUPST}_toplanmayan"]["tutar_tl"] == pytest.approx(-100.0)
    assert any("taşınmaz" in n for n in k[pf.KOD_EDT]["notlar"])


def test_p2_hepsi_toplanmaz_ise_katki_sifir_ve_nitelik_bozulmaz():
    r = pf.birlestir({"S1": _oz(-200.0, False), "S2": _oz(-300.0, False)})
    k = {b["kod"]: b for b in r["bilesenler"]}
    assert k[pf.KOD_EDT]["tutar_tl"] == 0.0 and k[pf.KOD_EDT]["nitelik"] == "hesaplanan"
    assert r["toplam"]["tutar_tl"] == pytest.approx(2000.0) and r["toplam"]["eksik"] == []
    assert k[f"{pf.KOD_EDT}_toplanmayan"]["tutar_tl"] == pytest.approx(-500.0)


def test_p2_hepsi_toplanir_ise_davranis_degismez():
    r = pf.birlestir({"S1": _oz(-500.0, True), "S2": _oz(-300.0, True)})
    k = {b["kod"]: b for b in r["bilesenler"]}
    assert k[pf.KOD_EDT]["tutar_tl"] == pytest.approx(-800.0) and r["toplam"]["tutar_tl"] == pytest.approx(2000 - 800 - 200)
    assert f"{pf.KOD_EDT}_toplanmayan" not in k


# ---------------------------------------------------------------- P7 (F9-A04): portföy havuzunda normalize ölçütler santral kWp'siyle
def _e(y, f, kap):
    n = len(y)
    return pd.DataFrame({"y": y, "p50_kw": f, "p10_kw": f * 0.9, "p90_kw": f * 1.1, "gun": pd.date_range("2026-06-01", periods=n, freq="1h").date, "_kap": kap})


def test_p7_iki_ozdes_santral_havuzu_tek_santral_nmae_verir():
    rng = np.random.default_rng(11); n = 200
    y = rng.uniform(100, 800, n); f = y * rng.normal(1.05, 0.12, n)
    tek = _e(y, f, KAP); m1 = bd.metrikler(tek.drop(columns="_kap"), KAP)
    havuz = pd.concat([tek.assign(_plant="a"), tek.assign(_plant="b")], ignore_index=True)
    eski = bd.metrikler(havuz, 2 * KAP)                 # düzeltme öncesi bileşim: N kat küçülür
    assert eski["nmae"] == pytest.approx(m1["nmae"] / 2, abs=0.01)
    m2 = bd.havuz_metrikleri(havuz, 2 * KAP)
    for k in ("nmae", "nrmse", "nmbe", "bant_genisligi_oran"):
        assert m2[k] == pytest.approx(m1[k], abs=0.02), k
    assert m2["wmape"] == pytest.approx(m1["wmape"], abs=0.01) and m2["mae_kw"] == pytest.approx(m1["mae_kw"], abs=0.01)
    assert m2["havuz_kurali"] == bd.HAVUZ_KURALI and m2["n_saat"] == 2 * n


def test_p7_farkli_kwp_santraller_kendi_kapasitesiyle_normalize():
    y = np.full(100, 500.0); f = np.full(100, 550.0)          # 1 MW santral: hata 50 kW = %5
    y2 = np.full(100, 5000.0); f2 = np.full(100, 5500.0)      # 10 MW santral: hata 500 kW = %5
    havuz = pd.concat([_e(y, f, 1000.0), _e(y2, f2, 10000.0)], ignore_index=True)
    m = bd.havuz_metrikleri(havuz, 11000.0)
    assert m["nmae"] == pytest.approx(5.0, abs=0.01)           # her santral-saatte %5 → %5 (eski bileşim: 275/11000 = %2,5)
    assert bd.metrikler(havuz, 11000.0)["nmae"] == pytest.approx(2.5, abs=0.01)
    assert bd.havuz_metrikleri(havuz.drop(columns="_kap"), 11000.0).get("havuz_kurali") is None   # _kap yoksa eski davranış


# ---------------------------------------------------------------- P8 (F9-F01): /v1/readyz
def _db_var() -> bool:
    try:
        from sqlalchemy import text

        from pvquant.db import sistem_baglami
        with sistem_baglami() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception: 
        return False


@pytest.mark.skipif(not _db_var(), reason="test DB yok (PVQ_DB_URL)")
def test_p8_readyz_db_varken_200_yokken_503(monkeypatch):
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from pvquant import db as pdb
    c = TestClient(api_main.app)
    r = c.get("/v1/readyz"); assert r.status_code == 200 and r.json()["db"] == "ok" and "worker_nabiz_dk" in r.json()
    assert c.get("/v1/healthz").json() == {"ok": True}

    @contextmanager
    def bozuk():
        raise RuntimeError("faz9 sentetik: db yok")
        yield
    monkeypatch.setattr(pdb, "sistem_baglami", bozuk)
    r = c.get("/v1/readyz"); assert r.status_code == 503 and "hazır değil" in r.json()["detail"]
    assert c.get("/v1/healthz").status_code == 200           # canlılık DB'den bağımsız kalır (sözleşme değişmedi)


# ---------------------------------------------------------------- P16 (F9-E05): temsil oturumunda KGÜP CSV (arşive yazar) 403
def test_p16_temsil_oturumu_kgup_csv_403_json_acik(monkeypatch):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    temsil = {"sub": "p1", "tenant_id": "00000000-0000-0000-0000-000000000001", "role": "viewer", "temsil": "p1", "kapsam": "musteri"}
    monkeypatch.setattr(api_main, "_kgup_yaniti", lambda *a, **k: {"onizleme": True})
    api_main.app.dependency_overrides[api_main.gecerli_kullanici] = lambda: temsil
    try:
        c = TestClient(api_main.app)
        assert c.get("/v1/plants/p1/kgup?fmt=csv").status_code == 403
        assert c.get("/v1/plants/p1/kgup?fmt=json").status_code == 200
        api_main.app.dependency_overrides[api_main.gecerli_kullanici] = lambda: {**temsil, "temsil": None}
        assert c.get("/v1/plants/p1/kgup?fmt=csv").status_code == 200   # normal oturum etkilenmez
    finally:
        api_main.app.dependency_overrides.pop(api_main.gecerli_kullanici, None)
