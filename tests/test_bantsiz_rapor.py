# -*- coding: utf-8 -*-
"""v2.181: bant kapısı + bantsız savunma.

Bantsızlık EKSİKLİK DEĞİLDİR: Mod B ve eski-artefakt (v2.178) koşuları
kuantil üretmez; v2.141 ailesi gereği eksiklik reddedilmez, dürüstçe akar.
Dört bacak:
  (1) BANT_VAR gözlenebilir bayrağı (half tam + toplam uçları dolu),
  (2) doldur() bant token'ları bantsızken '—' (uydurma değer yok),
  (3) fan_chart bantsızken poligon/kenar çizmez (beklenti çizgisi kalır),
  (4) ctx_to_json bantsız ctx'i REDDETMEZ (eski 'Mod C bandı' iste'si kalktı),
      half_mwh/totals None akar, bant anlatıları (_anlati) kendiliğinden düşer.
Cümle-içi bant yüzeyleri ('948 değil, — MWh', taahhüt satırı, lejant) BİLİNÇLİ
olarak mühür-2'nin (Mod B açıklama bloğu) işidir — burada test edilmez.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

from test_rapor_tutarlilik import KANONIK, MOTOR, taze_veri, uret_kos

BANTSIZ = Path(__file__).resolve().parent / "data" / "bantsiz_v21.json"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.services.report_html_service import ctx_to_json  # noqa: E402


# ---------------------------------------------------------------- (1) + (2)
def test_kanonik_bant_var():
    """Mutasyon bekçisi: kanonik girdi BANTLIDIR — bayrak yanlışlıkla
    sönerse md5'ten önce burada yakalanır."""
    m = taze_veri(KANONIK)
    assert m.BANT_VAR is True
    assert "—" not in m.doldur("{{TOPLAM_BANT}}")


def test_bantsiz_bayrak_ve_tokenlar():
    m = taze_veri(BANTSIZ)
    assert m.BANT_VAR is False
    assert (m.doldur("{{TOPLAM_BANT}}|{{TOPLAM_P10}}|{{TOPLAM_P90}}|{{MIN_HW}}")
            == "—|—|—|—")
    # eksen bantsızken yalnız P50'den türer (None patlatmaz, uydurma genişlik yok)
    assert m.GUN_YMIN <= min(m.P50_GUN) and m.GUN_YMAX >= max(m.P50_GUN)


def test_yarim_bant_bantsiz_sayilir():
    """Tek None bile bantsızdır — yarım bant çizilmez, uydurulmaz."""
    m = taze_veri(BANTSIZ)
    assert m.BANT_VAR is False  # tümü None
    # tam liste + toplam uçları None → yine bantsız (tanımın ikinci bacağı)
    m2 = taze_veri(KANONIK)
    assert (all(h is not None for h in m2.HW_GUN)
            and m2.TOPLAM_P10_MWH is not None and m2.BANT_VAR is True)


# ---------------------------------------------------------------- (3)
def test_fan_chart_bantsiz_poligonsuz():
    sys.path.insert(0, str(MOTOR))
    import pvq
    bantli = pvq.fan_chart([50.0, 60.0], [4.0, 5.0], ["01", "02"], "x", "y",
                           ymin=40, ymax=70)
    bantsiz = pvq.fan_chart([50.0, 60.0], [None, None], ["01", "02"], "x", "y",
                            ymin=40, ymax=70)
    assert "<polygon" in bantli
    assert "<polygon" not in bantsiz
    # beklenti çizgisi her iki durumda da var
    assert bantsiz.count("<path") >= 1 and "<circle" in bantsiz


# ---------------------------------------------------------------- (4) uçtan uca
def test_bantsiz_uret_16_sayfa_denetim_temiz(tmp_path):
    p = uret_kos(BANTSIZ, tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    sayfalar = sorted(tmp_path.glob("*_s??_*.html"))
    assert len(sayfalar) == 16, [s.name for s in sayfalar]
    j = json.loads((tmp_path / "denetim.json").read_text(encoding="utf-8"))
    assert j["ozet"]["hata"] == 0 and j["bulgular"] == []
    s04 = next(tmp_path.glob("*_s04_*.html")).read_text(encoding="utf-8")
    assert "<polygon" not in s04          # bant çizilmedi
    assert ">None<" not in s04            # sızıntı yok
    assert s04.count("—") >= 32           # P90+P10 satırları '—' hücreli durur
    # v2.182: dürüst blok + kural-4 düşürmeleri
    assert "Bu koşuda olasılık bandı üretilmedi" in s04     # blok metni
    assert "Bu koşuda bant yok" in s04                      # blok başlığı
    assert "olasılık aralığı" not in s04                    # fan lejantı düştü
    assert "948 değil" not in s04                           # kanonik bant prozu düştü
    s01 = next(tmp_path.glob("*_s01_*.html")).read_text(encoding="utf-8")
    s03 = next(tmp_path.glob("*_s03_*.html")).read_text(encoding="utf-8")
    s05 = next(tmp_path.glob("*_s05_*.html")).read_text(encoding="utf-8")
    assert "bu koşuda olasılık bandı üretilmedi" in s01     # taahhüt notu dürüst
    assert "bu koşuda olasılık bandı üretilmedi" in s03     # KPI notu dürüst
    assert "olasılıkla — MWh" not in s03                    # saçma kuyruk düştü
    for sayfa in (s01, s03, s05):
        assert "olasılık aralığı" not in sayfa              # bant anlatısı yok
    assert 'class="fan"' not in s05 or "<path" in s05       # lejant yok (CSS kuralı uyuyabilir)


# ---------------------------------------------------------------- (4) servis kapısı
def _bantsiz_ctx(ufuk):
    """Bantsız-C stub'u (v2.178 eski-artefakt popülasyonu): kuantil kolonu
    yok, holdout kapısı geçmiş. Alan listesi ctx_to_json'un GERÇEK
    tüketiminden türetildi (uydurma imza değil)."""
    from types import SimpleNamespace as NS
    gunler = pd.date_range("2026-08-20", periods=ufuk, freq="D")
    saat = pd.date_range("2026-08-20 00:00", periods=48, freq="h", tz="UTC")
    p50h = (pd.Series([0] * 6 + [50, 200, 400, 500, 520, 480, 300, 100] + [0] * 10,
                      index=saat[:24]).reindex(saat, fill_value=0.0).astype(float))
    karne = pd.DataFrame({
        "date": [gunler[0].date()] * 2, "horizon_bucket": ["0-24", "24-72"],
        "mape": [8.0, 11.0], "rmse": [1.0, 1.5],
        "skill_vs_naive": [30.0, 20.0], "naive_wmape": [12.0, 14.0]})
    return NS(
        plant_name="Stub GES", capacity_kwp=1000.0, mode="C",
        model_name="hybrid", run_at_utc=dt.datetime(2026, 8, 20, 6, 0),
        plant_tz="Europe/Istanbul", latitude=37.87, longitude=32.49,
        tilt_deg=20, azimuth_deg=180,
        daily_kwh=pd.Series([5000.0] * ufuk, index=gunler),
        # daily_p10/p90 BİLEREK YOK — testin konusu
        hourly=pd.DataFrame({"p50_kw": p50h}), karne=karne, karne_kapsama=None,
        uninterrupted_days=12,
        error_dist={"prof_mw": [], "mae24": [], "mae72": [],
                    "mu": 0.1, "sd": 1.0, "ndays": 30},
        coverage_pct=90.0, flag_dagilimi={"valid": 100},
        holdout_mape_pct=9.0, holdout_physics_mape_pct=13.0, kal_pencere_gun=120,
        ilk_scada_ts=None, son_scada_ts=None, albedo=None,
        iklim=pd.DataFrame({"yil": [2024] * 12 + [2025] * 12,
                            "ay": list(range(1, 13)) * 2, "mwh": [100.0] * 24}),
        quality_monthly={"aylar": ["Tem", "Ağu"], "gecerli": [90, 92]},
        kosu_evrim=pd.DataFrame({
            "run_at": pd.to_datetime(["2026-08-18", "2026-08-19"]),
            "p50_mwh": [70.0, 71.0], "half_mwh": [4.0, 4.1]}),
    )


def test_ctx_to_json_bantsiz_gecer():
    """Eski davranış: 'daily[].p10/p90 (Mod C bandı)' eksiğiyle ValueError.
    Yeni sözleşme: bantsız ctx GEÇER; half/totals None, bant anlatıları yok."""
    from pvquant.config import get_settings
    J = ctx_to_json(_bantsiz_ctx(get_settings().forecast_horizon_days),
                    {"customer": "Stub AŞ", "capacity_kwp": 1000.0})
    assert all(d["half_mwh"] is None for d in J["daily"])
    assert J["totals"]["p10_mwh"] is None and J["totals"]["p90_mwh"] is None
    assert "exec_1" not in J["narrative"] and "exec_4" not in J["narrative"]


# ---------------------------------------------------------------- v2.182
def test_kanonik_bant_tokenlari():
    """Bantlıda token'lar kanonik baytları üretir; blok BOŞTUR (D24 aynası)."""
    m = taze_veri(KANONIK)
    assert m.BANT_ACIKLAMA == ""
    assert m.TAAHHUT_NOT == "taahhüt için önerilen alt sınır 1.005 MWh"
    assert m.OLASILIK_KUYRUK.endswith("1.005–1.068 MWh aralığında gerçekleşecektir")
    assert m.KPI_BANT_DURUM == "ok"


def test_bantsiz_bant_tokenlari():
    """Bantsızda blok DOLU, taahhüt notu sayı iddia etmez, kuyruk düşer."""
    m = taze_veri(BANTSIZ)
    assert m.BANT_ACIKLAMA and "üretilmedi" in m.BANT_ACIKLAMA
    assert "MWh" not in m.TAAHHUT_NOT
    assert m.OLASILIK_KUYRUK == "" and m.KPI_BANT_DURUM == ""


def test_d24_karma_half_uyari(tmp_path):
    """Yarım bant girdisi: karma half → D24 'uyari' (bantsız sayıldı), hata yok."""
    import test_rapor_tutarlilik as trt
    veri_json = json.loads(Path(KANONIK).read_text(encoding="utf-8"))
    veri_json["daily"][0]["half_mwh"] = None          # tek gün boş → karma
    yol = tmp_path / "karma.json"
    yol.write_text(json.dumps(veri_json, ensure_ascii=False), encoding="utf-8")
    import denetim
    kayitlar, bulgular, _ = denetim.denetle_tam(taze_veri(yol))
    d24 = [k for k in kayitlar if k["kod"] == "D24"]
    assert any(k["durum"] == "uyari" and "yarım bant" in k["mesaj"] for k in d24)
    assert not any(k["durum"] == "hata" for k in d24)
