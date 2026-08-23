# -*- coding: utf-8 -*-
"""v2.183: holdout dikey dilimi — Mod B raporu uçtan uca.

Holdout, Mod C hibrit gate'inin ürünüdür; yokluğu (Mod B) EKSİKLİK DEĞİL
yapısal gerçektir (v2.141/v2.181/v2.182 ailesi). Beş bacak:
  (1) servis: calibration bloğu HER modda kurulur — katsayılar+pencere
      holdout'suz da yaşar (eski kapı Mod B'de katsayıları da düşürüyordu);
  (2) adaptör: blok opsiyonel, uçlar .get, HOLDOUT_VAR gözlenebilir bayrağı;
  (3) sayfalar: s09 "karşılaştırması yok" satırı (katsayı kartları kalır),
      s10 test-bölmesi düşer, s03 kartı "—"+nötr;
  (5) denetim: D2/D16 "iddia yok → gecti" dalları (D12 kalıbı).
GİZLİ KUSUR KAPANIŞI (sıra hatası): _anlati calibration'dan önce koşuyordu →
canlı yolda coefficients hiç yazılmamış, exec_2 hep fallback basmıştı; çağrı
taşındı, iki stub testi kapanışı kanıtlar. Kapak pill/rozetleri v2.184'tedir.
"""
import datetime as dt
import json
import sys
from pathlib import Path

from test_bantsiz_rapor import _bantsiz_ctx
from test_rapor_tutarlilik import KANONIK, taze_veri, uret_kos

MODB = Path(__file__).resolve().parent / "data" / "modb_v21.json"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.config import get_settings                       # noqa: E402
from pvquant.services.report_html_service import ctx_to_json  # noqa: E402


# ---------------------------------------------------------------- (2) adaptör
def test_kanonik_holdout_var():
    m = taze_veri(KANONIK)
    assert m.HOLDOUT_VAR is True
    assert m.KPI_HOLDOUT_DEGER == "%8,9" and m.DURUM_HOLDOUT == "ok"
    assert m.doldur("{{FIZIK}}|{{HOLDOUT}}") == "13,6|8,9"


def test_modb_taze_veri():
    m = taze_veri(MODB)
    assert m.HOLDOUT_VAR is False and m.SELALE_ADIM is None
    assert m.KPI_HOLDOUT_DEGER == "—" and m.DURUM_HOLDOUT == ""
    assert "karşılaştırması yok" in m.KPI_HOLDOUT_NOT
    assert m.doldur("{{FIZIK}}|{{HOLDOUT}}|{{IYILESME}}") == "—|—|—"
    # katsayılar holdout'suz da yaşar (Mod B gerçeği)
    assert m.KAT_ETA == "0,942" and m.KAL_PENCERE != ""


# ---------------------------------------------------------------- (3) uçtan uca
def test_modb_uret_16_sayfa_durust(tmp_path):
    p = uret_kos(MODB, tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(sorted(tmp_path.glob("*_s??_*.html"))) == 16
    j = json.loads((tmp_path / "denetim.json").read_text(encoding="utf-8"))
    assert j["ozet"]["hata"] == 0 and j["ozet"]["uyari"] == 0 and j["bulgular"] == []
    s09 = next(tmp_path.glob("*_s09_*.html")).read_text(encoding="utf-8")
    assert "kalibrasyon karşılaştırması yok" in s09      # dürüst satır
    assert "Net sonuç" not in s09 and "13,6" not in s09  # uç/şelale kalıntısı yok
    assert "0,942" in s09                                # katsayı kartı kalır
    s10 = next(tmp_path.glob("*_s10_*.html")).read_text(encoding="utf-8")
    assert "bağımsız test bölmesi yok" in s10
    assert "EĞİTİM — ilk %80" not in s10                 # split düştü
    s03 = next(tmp_path.glob("*_s03_*.html")).read_text(encoding="utf-8")
    assert "%—" not in s03                               # saçma değer yok
    assert "bu koşuda bağımsız test karşılaştırması yok" in s03
    s07 = next(tmp_path.glob("*_s07_*.html")).read_text(encoding="utf-8")
    assert "MOD B · KALİBRE" in s07                      # foot MOD_ROZET canlı


# ---------------------------------------------------------------- (1) servis
def _modb_ctx():
    ctx = _bantsiz_ctx(get_settings().forecast_horizon_days)
    ctx.mode = "B"
    del ctx.holdout_mape_pct, ctx.holdout_physics_mape_pct
    ctx.eta_bos, ctx.bifacial_pct, ctx.kal_saat = 0.94, 6.1, 1200
    ctx.kal_tarih = dt.datetime(2026, 8, 20)
    return ctx


def test_ctx_to_json_modb_gecer():
    """Eski davranış: 'calibration.holdout (gate)' eksiğiyle ValueError; eski
    kapı katsayıları da düşürüyordu. Yeni sözleşme: blok her modda, uçsuz."""
    J = ctx_to_json(_modb_ctx(), {"customer": "Stub AŞ", "capacity_kwp": 1000.0})
    C = J["calibration"]
    assert "physics_mape" not in C and "holdout_mape" not in C
    assert C["coefficients"]["eta_bos"] == 0.94 and C["window_days"] == 120
    assert "raporlanmıyor" in J["narrative"]["exec_2"]   # dürüst fallback


def test_ctx_to_json_sira_kusuru_kapandi():
    """Gizli kusur kanıtı: holdout'LU koşuda exec_2 artık gerçek uçları basar
    ve coefficients canlı JSON'a yazılır (eski sırada ikisi de imkânsızdı)."""
    ctx = _bantsiz_ctx(get_settings().forecast_horizon_days)
    ctx.eta_bos = 0.95
    J = ctx_to_json(ctx, {"customer": "Stub AŞ", "capacity_kwp": 1000.0})
    assert "13" in J["narrative"]["exec_2"]              # fizik ucu metinde
    assert J["calibration"]["coefficients"]["eta_bos"] == 0.95


# ---------------------------------------------------------------- (5) denetim
def test_d2_d16_iddia_yok_gecti():
    import denetim
    kayitlar, bulgular, _ = denetim.denetle_tam(taze_veri(MODB))
    d2 = [k for k in kayitlar if k["kod"] == "D2"]
    d16 = [k for k in kayitlar if k["kod"] == "D16"]
    assert any(k["durum"] == "gecti" and "iddiası da yok" in k["mesaj"] for k in d2)
    assert any(k["durum"] == "gecti" and "HOLDOUT" in k["mesaj"]
               and "iddiasız" in k["mesaj"] for k in d16)
    assert bulgular == []                                # uyarı bile yok
