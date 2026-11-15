"""Faz 9 (14.11.2026) — A/B/C alanları: tahmin doğrulama motorunun BAĞIMSIZ sınaması (DB'siz, saf fonksiyonlar).

Çekirdeğe dokunmaz; yalnız `pvquant.services.bagimsiz_dogrulama_service` ve `karne_kurali` saf fonksiyonlarını çağırır ve sonuçlarını
bu dosyadaki İKİNCİ (bağımsız, numpy) uygulamayla karşılaştırır. Bütün veriler SENTETİKTİR (saha kanıtı değildir).

Ölçüt bağları (02_Basari_Kriterleri_Matrisi.md):
  A-Z1 yayın damgası / geriye bakış 0      → test_program_* , test_gun_oncesi_*, test_geriye_bakisli_*, test_ozellik_rastgele_*
  A-B1..B4 metrik tanımları (WMAPE, MAE…)  → test_metrik_bagimsiz_yeniden_hesap, test_payda_kurali_*
  B-Z1 pay/payda (eksik veri şişiremez)    → test_butunluk_payda_* (Faz 9 bulgusu F9-B01 — beklenen davranışı belgeler)
  C-B1 PICP80 kalibrasyonu (sentetik)      → test_picp_*
Koşu: PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider tests/test_faz9_tahmin_dogrulama.py
(`faz9_*` adı varsayılan `test_*.py` toplama kalıbına uymaz: tam takıma/CI'ye girmez, yalnız açıkça verilince koşar.)
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import karne_kurali as kk

TZ = "Europe/Istanbul"
KAP = 1000.0


def _ist(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz=TZ).tz_convert("UTC")


def _gun_saatleri(gun: str) -> pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(gun, tz=TZ), periods=24, freq="1h").tz_convert("UTC")


def _kosu(gun: str, run_at: pd.Timestamp, p50: float, run_id: str, **ek) -> pd.DataFrame:
    ts = _gun_saatleri(gun)
    d = pd.DataFrame({"ts_utc": ts, "run_at": run_at, "run_id": run_id, "p50_kw": p50, "p10_kw": p50 * 0.8, "p90_kw": p50 * 1.2,
                      "physics_kw": p50, "model": ek.get("model", "hibrit"), "meteo_source": ek.get("meteo_source", "open-meteo"),
                      "etiket": ek.get("etiket", "yayin")})
    return d


# ------------------------------------------------------------------------------------------------ A-Z1 yayın damgası
def test_program_kesim_sonrasi_kosu_secilmez():
    """A-Z1: teslim günü D=2026-06-10 için kesim D-1 15:30 İstanbul. 15:00 koşusu (p50=100) seçilmeli; 15:31 koşusu (p50=999,
    kesimden SONRA — gerçekte KGÜP'e giremezdi) seçilmemeli. Aksi = gelecekteki bilgiyle «program doğruluğu» (sızıntı)."""
    once = _kosu("2026-06-10", _ist("2026-06-09 15:00"), 100.0, "r_once")
    sonra = _kosu("2026-06-10", _ist("2026-06-09 15:31"), 999.0, "r_sonra")
    s = bd.kosu_sec(pd.concat([once, sonra]), "program", TZ)
    assert len(s) == 24
    assert set(s["run_id"]) == {"r_once"}
    assert (s["run_at"] <= _ist("2026-06-09 15:30")).all()


def test_program_kesim_ani_dahil_ve_belgelenir():
    """A-Z1 sınır: run_at == kesim (15:30:00) dâhil (`<=`). Koşu run_at'i başlangıç damgasıysa yayın kesimden sonra bitebilir —
    Faz 9 bulgusu F9-A02 (K3): forecast_runs.run_at'in anlamı (başlangıç/bitiş) bu testle değil şemayla doğrulanmalı."""
    tam = _kosu("2026-06-10", _ist("2026-06-09 15:30"), 100.0, "r_tam")
    s = bd.kosu_sec(tam, "program", TZ)
    assert set(s["run_id"]) == {"r_tam"}


def test_program_2025_oncesi_kesim_1600():
    """A-Z1 + D (kural dönemi): 1.1.2025 öncesi kesim 16:00. Teslim günü 2024-12-15 için 15:45 koşusu dâhil, 16:01 hariç."""
    a = _kosu("2024-12-15", _ist("2024-12-14 15:45"), 100.0, "r_1545")
    b = _kosu("2024-12-15", _ist("2024-12-14 16:01"), 999.0, "r_1601")
    s = bd.kosu_sec(pd.concat([a, b]), "program", TZ)
    assert set(s["run_id"]) == {"r_1545"}
    assert kk.program_kesimi(date(2024, 12, 15)) == pd.Timestamp("2024-12-14 16:00", tz=TZ)
    assert kk.program_kesimi(date(2025, 1, 1)) == pd.Timestamp("2024-12-31 15:30", tz=TZ)


@pytest.mark.parametrize("ek", [{"model": "backtest"}, {"meteo_source": "open-meteo-arsiv"}, {"meteo_source": "sentetik_tohum"},
                                {"etiket": "backtest"}, {"etiket": "simulasyon"}, {"etiket": "sentetik"}, {"etiket": "demo"},
                                {"etiket": "yeniden_kurma"}])
@pytest.mark.parametrize("kural", ["program", "gun_oncesi", "gun_ici", "ufuk"])
def test_geriye_bakisli_kosu_hicbir_kurala_girmez(ek, kural):
    """A-Z1: geriye bakışlı koşu (backtest / arşiv-analiz meteo / sentetik tohum / etiket sözlüğü) yayımlanmış koşudan DAHA YENİ ve daha
    iyi olsa bile seçilmez. Yayımlanmış koşu: D-1 12:00. Geriye bakışlı: D-1 15:00 (program ve gün öncesi kurallarında kazanırdı)."""
    df = _geri_senaryo(ek, kural)
    s = bd.kosu_sec(df, kural, TZ)
    assert "r_geri" not in set(s["run_id"])


def _geri_senaryo(ek, kural):
    """Tur 3 (13 #3.2): gün içi kuralı yalnız etiket='gun_ici' koşularını seçtiği için senaryo o kurala göre kurulur — ikisi de gün içi revizyon
    (D 06:30 ve D 09:30 UTC), geriye bakışlı olan daha yeni. Etiket varyantları gün içi kuralında ayırt edici değildir (etiket 'gun_ici' değilse zaten
    seçilmez) → açıkça atlanır."""
    if kural == "gun_ici":
        if "etiket" in ek:
            pytest.skip("etiket varyantı gun_ici kuralında ayırt edici değil (etiket gun_ici değilse kova dışı)")
        yayin = _kosu("2026-06-10", pd.Timestamp("2026-06-10 06:30", tz="UTC"), 100.0, "r_yayin", etiket="gun_ici")
        geri = _kosu("2026-06-10", pd.Timestamp("2026-06-10 09:30", tz="UTC"), 999.0, "r_geri", etiket="gun_ici", **ek)
    else:
        yayin = _kosu("2026-06-10", _ist("2026-06-09 12:00"), 100.0, "r_yayin")
        geri = _kosu("2026-06-10", _ist("2026-06-09 15:00"), 999.0, "r_geri", **ek)
    return pd.concat([yayin, geri])


@pytest.mark.parametrize("ek", [{"model": "backtest"}, {"meteo_source": "open-meteo-arsiv"}, {"meteo_source": "sentetik_tohum"},
                                {"etiket": "backtest"}, {"etiket": "simulasyon"}, {"etiket": "sentetik"}, {"etiket": "demo"},
                                {"etiket": "yeniden_kurma"}])
@pytest.mark.parametrize("kural", ["program", "gun_oncesi", "gun_ici", "ufuk"])
def test_geriye_bakisli_testi_ayirt_edici_mutasyon(ek, kural, monkeypatch):
    """Tur 3 mutasyon sınaması: süzgeç (karne_kurali.geriye_bakisli) devre dışıyken aynı senaryoda geriye bakışlı koşu SEÇİLMELİ — yani yukarıdaki
    test süzgeç olmasa kırmızı olurdu (ayırt edici). Bağımsız doğrulayıcının bulgusu: ilk sürümde gun_ici için 8 parametre süzgeçsiz de geçiyordu."""
    from pvquant.services import karne_kurali as _kk
    df = _geri_senaryo(ek, kural)
    monkeypatch.setattr(_kk, "geriye_bakisli", lambda d: pd.Series(False, index=d.index))
    s = bd.kosu_sec(df, kural, TZ)
    assert "r_geri" in set(s["run_id"])


def test_simulasyon_kipi_geriye_bakisliyi_acikca_alir_ve_kaydedilmez():
    """A-Z1: simulasyon=True yalnız «geriye dönük simülasyon» etiketli çalışma içindir; sonuç meta.simulasyon=True taşır."""
    geri = _kosu("2026-06-10", _ist("2026-06-09 15:00"), 500.0, "r_geri", model="backtest", meteo_source="open-meteo-arsiv")
    s = bd.kosu_sec(geri, "program", TZ, simulasyon=True)
    assert set(s["run_id"]) == {"r_geri"}


def test_simulasyon_kipi_etiketli_backtesti_acikca_alir():
    """F9-A03 (düşük) — DÜZELTİLDİ: simulasyon=True artık `etiket` sütununu da «simulasyon» yapar; etiket='backtest' koşusu simülasyon
    kipinde dâhil (normal kipte yine dışlanır)."""
    geri = _kosu("2026-06-10", _ist("2026-06-09 15:00"), 500.0, "r_geri", etiket="backtest")
    assert set(bd.kosu_sec(geri, "program", TZ, simulasyon=True)["run_id"]) == {"r_geri"}
    assert bd.kosu_sec(geri, "program", TZ).empty


def test_gun_oncesi_gun_basi_ani_haric():
    """A-Z1: gün öncesi kuralı yerel D 00:00'dan ÖNCE yayımlanmış son koşuyu alır; tam 00:00 koşusu (kesin <) dışarıda."""
    a = _kosu("2026-06-10", _ist("2026-06-09 23:59"), 100.0, "r_2359")
    b = _kosu("2026-06-10", _ist("2026-06-10 00:00"), 999.0, "r_0000")
    s = bd.kosu_sec(pd.concat([a, b]), "gun_oncesi", TZ)
    assert set(s["run_id"]) == {"r_2359"}


def test_ozellik_rastgele_kosu_kumelerinde_geriye_bakis_sifir():
    """A-Z1 (özellik testi, 200 rastgele senaryo, tohum sabit): her teslim günü için seçilen koşu (i) kesimden önce, (ii) kesim
    öncesi koşuların EN SONUNCUSU, (iii) geriye bakışlı değil; saat başına tek satır. İkinci (bağımsız) uygulama ile kıyas."""
    rng = np.random.default_rng(20261114)
    gunler = ["2026-03-01", "2026-03-02", "2026-03-03"]
    for _ in range(200):
        parcalar = []
        for gun in gunler:
            kesim = pd.Timestamp(gun, tz=TZ) - pd.Timedelta(days=1) + pd.Timedelta(hours=15, minutes=30)
            for j in range(int(rng.integers(0, 5))):
                kayma = pd.Timedelta(minutes=int(rng.integers(-60 * 40, 60 * 20)))
                geri = rng.random() < 0.25
                parcalar.append(_kosu(gun, (kesim + kayma).tz_convert("UTC"), float(rng.integers(1, 900)), f"{gun}-{j}",
                                      **({"model": "backtest"} if geri else {})))
        if not parcalar:
            continue
        df = pd.concat(parcalar, ignore_index=True)
        s = bd.kosu_sec(df, "program", TZ)
        # bağımsız beklenti
        for gun in gunler:
            kesim = (pd.Timestamp(gun, tz=TZ) - pd.Timedelta(days=1) + pd.Timedelta(hours=15, minutes=30)).tz_convert("UTC")
            g = df[(df["ts_utc"].dt.tz_convert(TZ).dt.date == date.fromisoformat(gun)) & (df["model"] != "backtest") & (df["run_at"] <= kesim)]
            sg = s.iloc[0:0] if s.empty else s[pd.to_datetime(s["ts_utc"], utc=True).dt.tz_convert(TZ).dt.date == date.fromisoformat(gun)]
            if g.empty:
                assert sg.empty
                continue
            beklenen = g["run_at"].max()
            assert (sg["run_at"] == beklenen).all() and len(sg) == 24
            assert sg["ts_utc"].is_unique


# ------------------------------------------------------------------------------------------------ A-B metrikler
def _e(y, f, p10=None, p90=None, gunler=None):
    n = len(y)
    ts = pd.date_range("2026-06-10 03:00", periods=n, freq="1h", tz="UTC")
    d = pd.DataFrame({"ts_utc": ts, "y": np.asarray(y, float), "p50_kw": np.asarray(f, float),
                      "p10_kw": np.asarray(p10 if p10 is not None else np.full(n, np.nan), float),
                      "p90_kw": np.asarray(p90 if p90 is not None else np.full(n, np.nan), float)})
    d["gun"] = gunler if gunler is not None else ts.tz_convert(TZ).date
    return d


def test_metrik_bagimsiz_yeniden_hesap():
    """A-B1..B4, C-B1: metrikler() ile bağımsız numpy hesabı aynı sayıları verir (sentetik 300 saat, tohum sabit)."""
    rng = np.random.default_rng(7)
    n = 300
    y = rng.uniform(50, 900, n)
    f = y * rng.normal(1.03, 0.15, n)
    lo, hi = f * 0.85, f * 1.15
    e = _e(y, f, lo, hi)
    m = bd.metrikler(e, KAP)
    err = f - y
    assert m["n_saat"] == n
    assert m["wmape"] == pytest.approx(np.abs(err).sum() / y.sum() * 100, abs=0.006)
    assert m["mae_kw"] == pytest.approx(np.abs(err).mean(), abs=0.006)
    assert m["rmse_kw"] == pytest.approx(np.sqrt((err ** 2).mean()), abs=0.006)
    assert m["nmae"] == pytest.approx(np.abs(err).mean() / KAP * 100, abs=0.006)
    assert m["nrmse"] == pytest.approx(np.sqrt((err ** 2).mean()) / KAP * 100, abs=0.006)
    assert m["nmbe"] == pytest.approx(err.mean() / KAP * 100, abs=0.006)
    assert m["nmbe"] > 0          # işaret sözleşmesi: tahmin − gerçek; fazla tahmin pozitif
    icinde = (y >= lo) & (y <= hi)
    assert m["picp80"] == pytest.approx(icinde.mean() * 100, abs=0.06)
    assert m["p10_alti"] == pytest.approx((y < lo).mean() * 100, abs=0.06)
    assert m["p90_ustu"] == pytest.approx((y > hi).mean() * 100, abs=0.06)
    assert m["picp80"] + m["p10_alti"] + m["p90_ustu"] == pytest.approx(100, abs=0.15)
    w = (hi - lo) + (2 / 0.2) * (lo - y) * (y < lo) + (2 / 0.2) * (y - hi) * (y > hi)
    assert m["winkler_kw"] == pytest.approx(w.mean(), abs=0.06)
    assert m["bant_genisligi_oran"] == pytest.approx((hi - lo).mean() / KAP * 100, abs=0.06)


def test_payda_kurali_kucuk_gerceklesende_wmape_uydurulmaz():
    """A-B1 payda kuralı: Σy < PAYDA_ASGARI_ORAN·kapasite·n ise WMAPE None (kesinti/kar günü %1000'lük sayı üretmez)."""
    n = 10
    y = np.full(n, 0.5)                 # 0,5 kW × 10 saat = 5 < 0,01 × 1000 × 10 = 100
    e = _e(y, np.full(n, 30.0))
    m = bd.metrikler(e, KAP)
    assert m["wmape"] is None and "payda" in m["not"]
    assert m["mae_kw"] == pytest.approx(29.5)


def test_asgari_saat_alti_hicbir_metrik_yok():
    """A-Z: ASGARI_SAAT (3) altındaki kesitte metrik üretilmez — «yeterli veri yok»."""
    m = bd.metrikler(_e([100, 200], [110, 190]), KAP)
    assert m["wmape"] is None and m["mae_kw"] is None and m["picp80"] is None


def test_beceri_formulu():
    """A-B5: beceri = 1 − WMAPE_model/WMAPE_ref; referanslar() aynı saat kümesinde (adil kıyas) hesaplar."""
    y = np.array([100, 400, 800, 600, 300, 100], float)
    f = y * 1.10                         # model WMAPE %10
    fiz = y * 1.20                       # fizik WMAPE %20
    e = _e(y, f)
    e["physics_kw"] = fiz
    r = bd.referanslar(e, KAP, None, pd.Timestamp("2026-06-10", tz="UTC"), 37.0, 32.0, None)
    assert r["fizik"]["wmape"] == pytest.approx(20.0, abs=0.01)
    assert r["fizik"]["model_wmape_ayni_saatler"] == pytest.approx(10.0, abs=0.01)
    assert r["fizik"]["beceri_pct"] == pytest.approx(50.0, abs=0.1)
    assert r["persistans"]["wmape"] is None and "hesaplanamadı" in r["persistans"]["tanim"]   # geçmiş yok → uydurulmaz


def test_persistans_bilgi_kumesi_tutarli():
    """A-B5 referans: persistans değeri yayın anından ÖNCE ölçülmüş saatten gelir (t − 24k < r). Yayın 15:00 D-1, hedef D 12:00 UTC
    → k=1 ise kaynak D-1 12:00 (< 15:00) uygun; yayın 11:00 D-1 olsaydı kaynak D-2 12:00 olmalı."""
    ts = pd.Timestamp("2026-06-10 09:00", tz="UTC")
    gecmis = pd.Series({pd.Timestamp("2026-06-09 09:00", tz="UTC"): 500.0, pd.Timestamp("2026-06-08 09:00", tz="UTC"): 300.0})
    for run_at, kaynak in ((pd.Timestamp("2026-06-09 12:00", tz="UTC"), 500.0), (pd.Timestamp("2026-06-09 08:00", tz="UTC"), 300.0)):
        e = pd.DataFrame({"ts_utc": [ts], "run_at": [run_at]})
        p = bd.persistans(e, gecmis, 37.0, 32.0)
        assert p.iloc[0] == pytest.approx(kaynak, rel=2e-3)   # aynı saat; açık gök oranı günden güne ≈1 (±%0,1)


# ------------------------------------------------------------------------------------------------ B pay/payda
def _saatler(gun: str, kwh: np.ndarray, durum: list[str]) -> pd.DataFrame:
    ts = _gun_saatleri(gun)
    return pd.DataFrame({"ts_utc": ts, "kwh": kwh, "durum": durum, "neden": [None if d == "olculdu" else "eksik" for d in durum], "kirpma": False})


def _gunluk_profil() -> np.ndarray:
    h = np.arange(24)
    return np.clip(900 * np.sin(np.pi * (h - 6) / 13), 0, None)   # yerel 06–19 arası üretim


def test_butunluk_payda_tahmin_ve_olcum_yoksa_saat_paydadan_duser():
    """B-Z1 (Faz 9 bulgusu F9-B01, K1 → v2.610 düzeltmesi): hem tahminin hem ölçümün eksik olduğu gündüz saati gözlenen maskede görünmez.
    Senaryo: 12 gerçek gündüz saati; 4'ünde hem ölçüm hem tahmin yok (worker + SCADA kesintisi). Doğru oran 8/12 = %66,7.
    Konum verilince (hesapla_saf yolu) payda astronomik gündüzü sayar → %66,7. Konum yoksa eski davranış (%100) sürer ve payda_kurali bunu söyler."""
    gun = "2026-06-10"
    prof = _gunluk_profil()
    gunduz_idx = np.where(prof > 0.02 * KAP)[0]
    kayip = gunduz_idx[3:7]                        # 4 gündüz saati
    durum = ["olculdu"] * 24
    for i in kayip:
        durum[i] = "eksik"
    saatler = _saatler(gun, np.where(np.isin(np.arange(24), kayip), np.nan, prof), durum)
    tahmin = _kosu(gun, _ist("2026-06-09 12:00"), 0.0, "r1")
    tahmin["p50_kw"] = prof * 1.05
    tahmin = tahmin[~np.isin(np.arange(24), kayip)]   # o saatlerde tahmin satırı da yok
    s = bd.kosu_sec(tahmin, "program", TZ)
    d = bd.eslestir(s, saatler, TZ)
    e = bd.degerlendirilebilir(d, KAP)
    gercek_gunduz = len(gunduz_idx)
    dogru_oran = round((gercek_gunduz - len(kayip)) / gercek_gunduz * 100, 1)
    assert dogru_oran == pytest.approx(66.7)
    b = bd.butunluk(d, e, {}, KAP, konum=(37.0, 32.0))
    assert b["degerlendirilen_saat"] == gercek_gunduz - len(kayip)
    assert b["gunduz_saat"] == gercek_gunduz and b["gunduz_saat_veri_yok_eklenen"] == len(kayip)
    assert b["degerlendirilen_pct"] == pytest.approx(dogru_oran, abs=0.06)
    assert b["gunduz_dislanan"].get("eksik") == len(kayip)
    eski = bd.butunluk(d, e, {}, KAP)              # konum yok: eski davranış açıkça etiketli
    assert eski["degerlendirilen_pct"] == 100.0 and "konum yok" in eski["payda_kurali"]


def test_butunluk_payda_yalniz_olcum_eksikse_dogru_sayilir():
    """B-Z1 kontrol: tahmin VAR ama ölçüm eksikse saat gündüz sayılır ve dışlanan nedeniyle raporlanır (şişme yok)."""
    gun = "2026-06-10"
    prof = _gunluk_profil()
    gunduz_idx = np.where(prof > 0.02 * KAP)[0]
    kayip = gunduz_idx[3:7]
    durum = ["olculdu"] * 24
    for i in kayip:
        durum[i] = "eksik"
    saatler = _saatler(gun, np.where(np.isin(np.arange(24), kayip), np.nan, prof), durum)
    tahmin = _kosu(gun, _ist("2026-06-09 12:00"), 0.0, "r1")
    tahmin["p50_kw"] = prof * 1.05
    s = bd.kosu_sec(tahmin, "program", TZ)
    d = bd.eslestir(s, saatler, TZ)
    e = bd.degerlendirilebilir(d, KAP)
    b = bd.butunluk(d, e, {}, KAP)
    assert b["gunduz_saat"] == len(gunduz_idx)
    assert b["degerlendirilen_pct"] == pytest.approx((len(gunduz_idx) - 4) / len(gunduz_idx) * 100, abs=0.06)
    assert b["gunduz_dislanan"].get("eksik") == 4


def test_eksik_saat_hata_olarak_sifir_sayilmaz():
    """A-Z: ölçümü eksik saat metrik paydasına 0 kWh olarak girmez (WMAPE'yi ne iyileştirir ne kötüleştirir)."""
    gun = "2026-06-10"
    prof = _gunluk_profil()
    durum = ["olculdu"] * 24
    durum[12] = "eksik"
    saatler = _saatler(gun, np.where(np.arange(24) == 12, np.nan, prof), durum)
    tahmin = _kosu(gun, _ist("2026-06-09 12:00"), 0.0, "r1")
    tahmin["p50_kw"] = prof * 1.10
    r = bd.hesapla_saf(tahmin, saatler, {}, {"capacity_kwp": KAP, "tz": TZ, "lat": 37.0, "lon": 32.0},
                       pd.Timestamp(gun, tz=TZ), pd.Timestamp(gun, tz=TZ) + pd.Timedelta(days=1))
    assert r["metrik"]["wmape"] == pytest.approx(10.0, abs=0.01)
    assert r["metrik"]["n_saat"] == int((prof > 0.02 * KAP).sum()) - 1


# ------------------------------------------------------------------------------------------------ C bant kalibrasyonu
@pytest.mark.parametrize("olcek,beklenen_aralik", [(1.0, (76.0, 84.0)), (0.5, (35.0, 55.0)), (2.0, (95.0, 100.0))])
def test_picp_sentetik_kalibre_bantta_nominali_bulur(olcek, beklenen_aralik):
    """C-B1 (sentetik): gerçekleşen ~ N(μ, σ); P10/P90 = μ ∓ 1,2816·σ·ölçek. Ölçek 1 → PICP80 ≈ %80 (± örnekleme), dar bant (0,5)
    → ≈ %47, geniş bant (2) → ≈ %99. Motor bu üç durumu ayırır; Faz 3 kuralı [70, 90] yalnız kalibre olanı kabul eder."""
    rng = np.random.default_rng(42)
    n = 4000
    mu = rng.uniform(200, 800, n)
    sig = 0.1 * mu
    y = rng.normal(mu, sig)
    z = 1.2815515655446004 * olcek
    e = _e(y, mu, mu - z * sig, mu + z * sig)
    m = bd.metrikler(e, KAP)
    assert beklenen_aralik[0] <= m["picp80"] <= beklenen_aralik[1]
    if olcek == 1.0:
        assert 5.0 <= m["p10_alti"] <= 15.0 and 5.0 <= m["p90_ustu"] <= 15.0
    if olcek == 2.0:
        # geniş bant kapsamayı «iyi» gösterir ama Winkler/keskinlik ayrı raporlanır: genişlik ölçek 1'in iki katı
        m1 = bd.metrikler(_e(y, mu, mu - 1.2815515655446004 * sig, mu + 1.2815515655446004 * sig), KAP)
        assert m["bant_genisligi_oran"] == pytest.approx(2 * m1["bant_genisligi_oran"], rel=0.01)


def test_picp_kayik_bant_kuyruk_asimetrisini_gosterir():
    """C-B2: bant doğru genişlikte ama sistematik yukarı kayık (fazla tahmin) → PICP düşer, p90_ustu ≈ 0, p10_alti büyür."""
    rng = np.random.default_rng(3)
    n = 3000
    mu = rng.uniform(200, 800, n)
    sig = 0.1 * mu
    y = rng.normal(mu, sig)
    f = mu * 1.15
    e = _e(y, f, f - 1.2816 * sig, f + 1.2816 * sig)
    m = bd.metrikler(e, KAP)
    assert m["p10_alti"] > 30 and m["p90_ustu"] < 3 and m["picp80"] < 70


# ------------------------------------------------------------------------------------------------ A — şişirme riskleri (K3 → K1)
def test_portfoy_havuzu_normalize_metrikleri_n_kat_kucultur():
    """R2 → F9-A04 (K1, Yüksek): `bd.portfoy` santral-saat satırlarını ALT ALTA ekler (saat bazında toplamaz) ve `metrikler`'e TOPLAM kWp verir.
    İki özdeş santral (aynı hata) havuzunda nMAE / nRMSE / nMBE / bant genişliği yarıya iner; WMAPE değişmez. Doğru portföy nMAE'si
    (saatlik toplam üretim ve toplam kapasite) tek santralinkiyle aynı olmalıdır. Bu test `bd.portfoy`'un kullandığı bileşimi aynen kurar."""
    rng = np.random.default_rng(11)
    n = 200
    y = rng.uniform(100, 800, n)
    f = y * rng.normal(1.05, 0.12, n)
    tek = _e(y, f, f * 0.9, f * 1.1)
    m1 = bd.metrikler(tek, KAP)
    havuz = pd.concat([tek.assign(_plant="a"), tek.assign(_plant="b")], ignore_index=True)   # bd.portfoy:452-457
    m2 = bd.metrikler(havuz, 2 * KAP)
    assert m2["wmape"] == pytest.approx(m1["wmape"], abs=0.01)
    for k in ("nmae", "nrmse"):
        assert m2[k] == pytest.approx(m1[k] / 2, abs=0.01)
    assert m2["bant_genisligi_oran"] == pytest.approx(m1["bant_genisligi_oran"] / 2, abs=0.06)
    # doğru portföy toplaması (saatlik Σ): nMAE tek santralinkine eşit
    dogru = _e(2 * y, 2 * f)
    assert bd.metrikler(dogru, 2 * KAP)["nmae"] == pytest.approx(m1["nmae"], abs=0.01)


def test_kisinti_bayragi_fizik_tahminine_bagli():
    """R1 → F9-A05 (K1, Yüksek): `hijyen_service.bayrakla_df` gerçek üretim fizik tahmininin (beklenen_kw = son koşunun physics_kw'si) belirgin
    altında ve düz ise saati `kisinti` işaretler; bu saatler `valid` olmadığı için karneden ve bağımsız doğrulamadan DÜŞER. Fiziğin bulutlu bir
    öğleden sonrayı büyük fazla tahmin ettiği durumda «tahmin hatası» olan saatler sınavdan çıkabilir. Senaryo: 6 saat düz 300 kW gerçek,
    fizik 800 kW (kapasite 1000)."""
    from pvquant.services import hijyen_service as hs
    ts = pd.date_range("2026-06-10 08:00", periods=6, freq="1h", tz="UTC")
    df = pd.DataFrame({"ts_utc": ts, "power_kw": [300.0] * 6, "beklenen_kw": [800.0] * 6})
    b = hs.bayrakla_df(df, None, 1000.0)
    isaretli = int(b["kisinti"].sum())
    print(f"\nkısıntı işaretlenen saat: {isaretli}/6")
    assert isaretli >= 1     # tahmine bağlı dışlama gerçekleşiyor (bulgunun kanıtı); 0 ise bulgu düşer
