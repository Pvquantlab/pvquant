"""G2-C2 (23.11.2026, bulgu C2-5): ufuk σ katmanı iç bandı (p25/p75) da alttan sınırlar.

Eskiden `uygula_df` yalnız p10/p90'ı Z10·σ ile genişletir, p25/p75 ham GEFS kantili kalırdı → iç/dış genişlik 0,25 (normal 0,53),
PICP50 ≈ 0,25. Pinler: p10/p50/p90 BİREBİR değişmez; p25/p75 yarı genişliği ≥ Z25·σ; sıralama; gece dokunulmaz; σ=0 değişmez;
tavan; iç bant yoksa uydurulmaz; tavan bekçisiyle (G2-A1) birlikte AC aşımı yok.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.services import ufuk_service as uf
from pvquant.services.forecast_service import tavan_bekcisi

RUN = pd.Timestamp("2026-11-20 03:00", tz="UTC")
AYAR = {"sigma_kw": {"0": 100.0, "1": 160.0, "2": 220.0, "3": 300.0}, "kova_saat": 24}


def _cerceve(n: int = 96, p50_tepe: float = 1500.0, ic: float = 0.03, dis: float = 0.08) -> pd.DataFrame:
    """Gündüz/gece döngülü sentetik koşu: ham iç bant dar (±%3), dış bant ±%8; gece 0."""
    idx = pd.date_range(RUN, periods=n, freq="h")
    saat = idx.hour
    gun = np.clip(np.sin((saat - 6) / 12 * np.pi), 0, None)
    p50 = p50_tepe * gun
    h = pd.DataFrame({"p10_kw": p50 * (1 - dis), "p25_kw": p50 * (1 - ic), "p50_kw": p50, "p75_kw": p50 * (1 + ic), "p90_kw": p50 * (1 + dis)}, index=idx)
    return h


def _sigma_kova(idx: pd.DatetimeIndex) -> np.ndarray:
    k = (((idx - RUN) / pd.Timedelta(hours=1)) // 24).astype(int)
    return np.array([AYAR["sigma_kw"][str(min(int(x), 3))] for x in k])


def test_z_sabitleri_pinli():
    """QA İ-2: Z25/Z10 sayısal değerleri ve oranı sabitlenir (normal dağılım %50 / %80 bant z'leri)."""
    assert uf.Z10 == 1.2816 and uf.Z25 == 0.6745
    assert np.isclose(uf.Z25 / uf.Z10, 0.5263, atol=1e-3)


def test_p10_p50_p90_birebir_degismez():
    h = _cerceve()
    # eski davranış = yalnız p10/p90 kuralı; aynı fonksiyonun p10/p90 çıktısı iç bant eklenince değişmemeli
    once = uf.uygula_df(h.drop(columns=["p25_kw", "p75_kw"]), AYAR, RUN, None)
    sonra = uf.uygula_df(h, AYAR, RUN, None)
    for k in ("p10_kw", "p50_kw", "p90_kw"):
        np.testing.assert_allclose(sonra[k].to_numpy(float), once[k].to_numpy(float), rtol=0, atol=1e-9)
    np.testing.assert_allclose(sonra["p50_kw"].to_numpy(float), h["p50_kw"].to_numpy(float), atol=1e-9)   # merkez dokunulmaz


def test_ic_bant_yari_genislik_en_az_z25_sigma_ve_yalniz_genisler():
    h = _cerceve()
    u = uf.uygula_df(h, AYAR, RUN, None)
    g = u["p50_kw"] > 0
    sig = _sigma_kova(u.index)
    alt_beklenen = np.clip(u["p50_kw"] - uf.Z25 * sig, 0, None)
    assert (u.loc[g, "p25_kw"] <= np.minimum(h.loc[g, "p25_kw"], alt_beklenen[g.to_numpy()]) + 1e-9).all()
    assert (u.loc[g, "p75_kw"] >= np.maximum(h.loc[g, "p75_kw"], (u["p50_kw"] + uf.Z25 * sig)[g.to_numpy()]) - 1e-9).all()
    # yalnız genişletir: hiçbir gündüz satırında iç bant daralmaz
    assert (u.loc[g, "p25_kw"] <= h.loc[g, "p25_kw"] + 1e-9).all() and (u.loc[g, "p75_kw"] >= h.loc[g, "p75_kw"] - 1e-9).all()
    # ham iç bant zaten σ'dan genişse (geniş GEFS yayılımı) o saatlerde dokunulmaz; dar olduğu (düşük p50) saatlerde genişler
    genis = _cerceve(ic=0.5)
    ug = uf.uygula_df(genis, AYAR, RUN, None)
    sg = _sigma_kova(ug.index)
    genis_yeter = (genis["p50_kw"] > 0) & ((genis["p50_kw"] - genis["p25_kw"]) >= uf.Z25 * sg) & ((genis["p75_kw"] - genis["p50_kw"]) >= uf.Z25 * sg)
    assert genis_yeter.sum() > 10
    np.testing.assert_allclose(ug.loc[genis_yeter, "p25_kw"], genis.loc[genis_yeter, "p25_kw"], atol=1e-9)
    np.testing.assert_allclose(ug.loc[genis_yeter, "p75_kw"], genis.loc[genis_yeter, "p75_kw"], atol=1e-9)


def test_siralama_korunur_ve_iclik_dislik_orani_normale_yaklasir():
    h = _cerceve()
    u = uf.uygula_df(h, AYAR, RUN, None)
    g = u["p50_kw"] > 0
    assert (u.loc[g, "p10_kw"] <= u.loc[g, "p25_kw"] + 1e-9).all()
    assert (u.loc[g, "p25_kw"] <= u.loc[g, "p50_kw"] + 1e-9).all()
    assert (u.loc[g, "p50_kw"] <= u.loc[g, "p75_kw"] + 1e-9).all()
    assert (u.loc[g, "p75_kw"] <= u.loc[g, "p90_kw"] + 1e-9).all()
    # σ bağlayıcı olduğu saatlerde iç/dış = Z25/Z10 ≈ 0,526
    bag = g & (u["p10_kw"] > 0)
    oran = ((u["p75_kw"] - u["p25_kw"]) / (u["p90_kw"] - u["p10_kw"]))[bag]
    assert np.isclose(oran.median(), uf.Z25 / uf.Z10, atol=0.02)


def test_gece_sifir_ve_nan_ic_bant_dokunulmaz():
    h = _cerceve()
    u = uf.uygula_df(h, AYAR, RUN, None)
    gece = h["p50_kw"] <= 0
    assert (u.loc[gece, "p25_kw"] == 0).all() and (u.loc[gece, "p75_kw"] == 0).all()
    # iç bant yok (Mod A/B model bandı): NaN kalır, uydurulmaz
    h2 = _cerceve()
    h2["p25_kw"] = None
    h2["p75_kw"] = None
    u2 = uf.uygula_df(h2, AYAR, RUN, None)
    assert u2["p25_kw"].isna().all() and u2["p75_kw"].isna().all()
    # p25/p75 kolonu hiç yoksa fonksiyon eski davranışıyla çalışır
    u3 = uf.uygula_df(_cerceve().drop(columns=["p25_kw", "p75_kw"]), AYAR, RUN, None)
    assert "p25_kw" not in u3.columns


def test_sigma_sifir_ve_ayar_yok_degismez():
    h = _cerceve()
    u0 = uf.uygula_df(h, {"sigma_kw": {"0": 0.0}, "kova_saat": 24}, RUN, None)
    pd.testing.assert_frame_equal(u0, h, check_dtype=False)
    pd.testing.assert_frame_equal(uf.uygula_df(h, None, RUN, None), h)


def test_tavan_ve_ac_bekcisi_ile_asim_yok():
    h = _cerceve(p50_tepe=1950.0)   # tavana yakın
    tavan = 2000.0
    u = uf.uygula_df(h, AYAR, RUN, tavan)
    g = u["p50_kw"] > 0
    # σ ile GENİŞLETİLEN değer tavanı aşmaz (p90 ile aynı sözleşme); ham bant zaten tavan üstündeyse ufuk katmanı kırpmaz,
    # onu zincirin sonundaki G2-A1 bekçisi kırpar
    genisledi = g & (u["p75_kw"] > h["p75_kw"] + 1e-9)
    assert genisledi.any() and (u.loc[genisledi, "p75_kw"] <= tavan + 1e-9).all()
    assert (u.loc[g, "p75_kw"] <= np.maximum(h.loc[g, "p75_kw"], tavan) + 1e-9).all()
    assert (u.loc[g, "p90_kw"] <= np.maximum(h.loc[g, "p90_kw"], tavan) + 1e-9).all()
    assert (u.loc[g, "p25_kw"] >= 0).all() and (u.loc[g, "p10_kw"] >= 0).all()
    # sapma çarpanı sonrası G2-A1 bekçisi (AC 1800): hiçbir kantil aşmaz, sıralama korunur
    s = u.copy()
    for k in ("p10_kw", "p25_kw", "p50_kw", "p75_kw", "p90_kw"):
        s[k] = s[k] * 1.2
    b = tavan_bekcisi(s, 1800.0)
    for k in ("p10_kw", "p25_kw", "p50_kw", "p75_kw", "p90_kw"):
        assert (b.loc[g, k] <= 1800.0 + 1e-9).all()
    assert (b.loc[g, "p25_kw"] <= b.loc[g, "p50_kw"] + 1e-9).all() and (b.loc[g, "p50_kw"] <= b.loc[g, "p75_kw"] + 1e-9).all()


@pytest.mark.parametrize("ic", [0.0, 0.01, 0.05])
def test_deterministik_ve_tekrar_uretilebilir(ic):
    h = _cerceve(ic=ic)
    a = uf.uygula_df(h, AYAR, RUN, 2500.0)
    b = uf.uygula_df(h, AYAR, RUN, 2500.0)
    pd.testing.assert_frame_equal(a, b)


# ───────────────────────── G2-C2b: ampirik asimetrik k−/k+ (çevrimiçi, Z25 geri düşüşlü) ─────────────────────────
def _artik_kumesi(n: int = 400, seed: int = 3):
    """Sentetik standardize artık: asimetrik — alt kuyruk ağır (gerçek < p50), üst hafif. σ(kova) sabit 100 → hata = p50 − gerçek."""
    rng = np.random.default_rng(seed)
    z = np.where(rng.random(n) < 0.5, -np.abs(rng.normal(0, 1.1, n)), np.abs(rng.normal(0, 0.5, n)))   # z = (gerçek − p50)/σ
    hata = pd.Series(-z * 100.0)
    kova = pd.Series(np.zeros(n, dtype=int))
    return hata, kova, z


def test_k25_hesapla_isaret_kantil_ve_kirpma():
    hata, kova, z = _artik_kumesi()
    k = uf.k25_hesapla(hata, kova, {"0": 100.0})
    assert k is not None and k["kaynak"] == "ampirik" and k["n"] == len(z)
    # işaret: alt = −Q25(z) (gerçek p50'nin altına ne kadar sapıyor), üst = Q75(z)
    assert np.isclose(k["alt"], np.clip(-np.quantile(z, 0.25), uf.K25_ALT_SINIR, uf.K25_UST_SINIR), atol=1e-4)
    assert np.isclose(k["ust"], np.clip(np.quantile(z, 0.75), uf.K25_ALT_SINIR, uf.K25_UST_SINIR), atol=1e-4)
    assert k["alt"] > k["ust"], "sentetik asimetri: alt kuyruk ağır → k− > k+"
    # kırpma: çok dar dağılım → alt sınır; çok geniş → üst sınır
    dar = uf.k25_hesapla(pd.Series(np.full(200, 1.0)), pd.Series(np.zeros(200, dtype=int)), {"0": 100.0})
    assert dar["alt"] == uf.K25_ALT_SINIR and dar["ust"] == uf.K25_ALT_SINIR
    genis = uf.k25_hesapla(pd.Series(np.concatenate([np.full(100, 500.0), np.full(100, -500.0)])), pd.Series(np.zeros(200, dtype=int)), {"0": 100.0})
    assert genis["alt"] == uf.K25_UST_SINIR and genis["ust"] == uf.K25_UST_SINIR
    assert uf.K25_UST_SINIR < uf.Z10   # sıralama garantisi


def test_k25_yetersiz_veya_sigmasiz_none_ve_oku_geri_dusus():
    hata, kova, _ = _artik_kumesi(n=uf.MIN_SAAT - 1)
    assert uf.k25_hesapla(hata, kova, {"0": 100.0}) is None
    hata, kova, _ = _artik_kumesi()
    assert uf.k25_hesapla(hata, kova, {"5": 100.0}) is None            # kovanın σ'sı yok → z sonlu değil → None
    for ayar in (None, {}, {"sigma_kw": {"0": 1}}, {"k25": None}, {"k25": {"alt": "x", "ust": 1}}, {"k25": {"alt": float("nan"), "ust": 0.5}}, {"k25": {"alt": 0.5}}):
        assert uf.k25_oku(ayar) == (uf.Z25, uf.Z25)
    assert uf.k25_oku({"k25": {"alt": 0.6, "ust": 0.4}}) == (0.6, 0.4)
    assert uf.k25_oku({"k25": {"alt": 5.0, "ust": 0.01}}) == (uf.K25_UST_SINIR, uf.K25_ALT_SINIR)   # okurken de kırpılır


def test_sigma_hesapla_df_k25_uretir_ve_sigma_degismez():
    rng = np.random.default_rng(5)
    idx = pd.date_range("2026-09-01", periods=24 * 20, freq="h", tz="UTC")
    run_at = (idx.floor("D") - pd.Timedelta(hours=2))
    p50 = 1000 * np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None)
    power = p50 * (1 + rng.normal(0, 0.15, len(idx)))
    df = pd.DataFrame({"ts_utc": idx, "run_at": run_at, "p50_kw": p50, "power_kw": power})
    a = uf.sigma_hesapla_df(df, 4000.0)
    assert a is not None and "k25" in a and uf.K25_ALT_SINIR <= a["k25"]["alt"] <= uf.K25_UST_SINIR and uf.K25_ALT_SINIR <= a["k25"]["ust"] <= uf.K25_UST_SINIR
    # σ sözlüğü k25'ten bağımsız (eski alanlar birebir)
    b = {k: v for k, v in a.items() if k not in ("k25", "hesap_zamani")}
    assert set(b) == {"sigma_kw", "n", "kova_saat", "pencere_gun"} and b["kova_saat"] == 24


def test_uygula_df_k25_asimetrik_kullanir_ve_eski_ayar_z25_ile_birebir():
    h = _cerceve()
    eski = uf.uygula_df(h, AYAR, RUN, None)                                   # k25 yok → Z25 (G2-C2 davranışı)
    z25 = uf.uygula_df(h, {**AYAR, "k25": {"alt": uf.Z25, "ust": uf.Z25}}, RUN, None)
    pd.testing.assert_frame_equal(eski, z25)                                  # ayar uyumu: k25 = Z25 ⇒ aynı
    ayar = {**AYAR, "k25": {"alt": 0.9, "ust": 0.35}}
    u = uf.uygula_df(h, ayar, RUN, None)
    g = u["p50_kw"] > 0
    sig = _sigma_kova(u.index)
    # alt taraf daha geniş (0,9σ), üst taraf daha dar (0,35σ); yalnız genişletir
    np.testing.assert_allclose(u.loc[g, "p25_kw"], np.minimum(h.loc[g, "p25_kw"], np.clip(h.loc[g, "p50_kw"] - 0.9 * sig[g.to_numpy()], 0, None)), atol=1e-9)
    np.testing.assert_allclose(u.loc[g, "p75_kw"], np.maximum(h.loc[g, "p75_kw"], h.loc[g, "p50_kw"] + 0.35 * sig[g.to_numpy()]), atol=1e-9)
    for k in ("p10_kw", "p50_kw", "p90_kw"):
        np.testing.assert_allclose(u[k].to_numpy(float), eski[k].to_numpy(float), atol=1e-9)   # dış bant ve merkez dokunulmaz
    # en geniş izinli katsayıda (1,0) bile sıralama korunur
    u1 = uf.uygula_df(h, {**AYAR, "k25": {"alt": 1.0, "ust": 1.0}}, RUN, 2500.0)
    assert (u1.loc[g, "p10_kw"] <= u1.loc[g, "p25_kw"] + 1e-9).all() and (u1.loc[g, "p75_kw"] <= u1.loc[g, "p90_kw"] + 1e-9).all()


def test_k25_sigma_sifir_kova_uyarisiz_dusurulur():
    """QA C2b İ-4 / M20: σ = 0 (ya da eksik) kovası sonsuz/NaN z üretir; bu satırlar düşer, uyarı çıkmaz, yetersizse None."""
    import warnings
    hata, kova, _ = _artik_kumesi()
    with warnings.catch_warnings():
        warnings.simplefilter("error")                      # RuntimeWarning olsaydı test düşerdi
        assert uf.k25_hesapla(hata, kova, {"0": 0.0}) is None
        karisik = pd.Series(np.concatenate([np.zeros(400, dtype=int), np.ones(400, dtype=int)]))
        k = uf.k25_hesapla(pd.concat([hata, hata], ignore_index=True), karisik, {"0": 0.0, "1": 100.0})
    assert k is not None and k["n"] == 400       # yalnız σ’lı kova sayılır
