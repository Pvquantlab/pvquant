"""C-3b (v2.152): s08 bütünlük kurallarının makine karşılığı — üretim tarafı.

Kural 2 mekanizması iki parçadır ve ikisi de burada GERÇEK üreticiyle test
edilir (v2.149 dersi: fikstür elle yazılmaz): worker'ın saf kapsama
hesaplayıcısı (karne_kapsama_hesapla) ve servisin karne dışlaması
(_karne_satirlari). Eşikler config'ten okunur — beklenenler de oradan kurulur.
"""
import sys
import datetime as dt
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from apps.worker.main import karne_kapsama_hesapla        # noqa: E402
from pvquant.config import get_settings                   # noqa: E402
from pvquant.services.report_html_service import _karne_satirlari  # noqa: E402

AYAR = get_settings()
ESIK = AYAR.karne_kapsama_esik_pct
PAYDA = AYAR.karne_gunduz_son - AYAR.karne_gunduz_bas + 1
BUGUN = dt.date(2026, 8, 17)


def _saatler(gun, n, tz="Europe/Istanbul"):
    """Verilen günde gün içi penceresinin İLK n saati için UTC ts listesi."""
    out = []
    for h in range(AYAR.karne_gunduz_bas, AYAR.karne_gunduz_bas + n):
        yerel = pd.Timestamp(gun) + pd.Timedelta(hours=h)
        out.append(yerel.tz_localize(tz).tz_convert("UTC"))
    return out


# ------------------------------------------------- karne_kapsama_hesapla
def test_kapsama_tam_gun_100():
    g = BUGUN - dt.timedelta(days=1)
    k = karne_kapsama_hesapla(_saatler(g, PAYDA), "Europe/Istanbul", bugun=BUGUN)
    assert k[str(g)] == 100


def test_kapsama_yarim_gun_orani():
    g = BUGUN - dt.timedelta(days=2)
    n = PAYDA // 2
    k = karne_kapsama_hesapla(_saatler(g, n), "Europe/Istanbul", bugun=BUGUN)
    assert k[str(g)] == int(round(n / PAYDA * 100))


def test_kapsama_verisiz_gun_sifir_ve_pencere_30():
    k = karne_kapsama_hesapla([], "Europe/Istanbul", bugun=BUGUN)
    assert len(k) == 30
    assert set(k.values()) == {0}                    # yokluk gizlenmez
    assert str(BUGUN) not in k                       # çapa DÜN'dür (v2.140)
    assert str(BUGUN - dt.timedelta(days=1)) in k
    assert str(BUGUN - dt.timedelta(days=30)) in k


def test_kapsama_gun_disi_saat_sayilmaz():
    g = BUGUN - dt.timedelta(days=1)
    gece = pd.Timestamp(g).tz_localize("Europe/Istanbul") \
        + pd.Timedelta(hours=2)                      # yerel 02:00
    k = karne_kapsama_hesapla([gece.tz_convert("UTC")], "Europe/Istanbul",
                              bugun=BUGUN)
    assert k[str(g)] == 0


def test_kapsama_yinelenen_saat_tek_sayilir():
    g = BUGUN - dt.timedelta(days=1)
    ts = _saatler(g, 1) * 3
    k = karne_kapsama_hesapla(ts, "Europe/Istanbul", bugun=BUGUN)
    assert k[str(g)] == int(round(1 / PAYDA * 100))


# ------------------------------------------------- _karne_satirlari dışlama
def _karne_df(gunler):
    b = dt.datetime.now(dt.timezone.utc).date()
    rows = []
    for g in gunler:
        t = str(b - dt.timedelta(days=g))
        rows.append(dict(date=t, horizon_bucket="0-24", mape=9.0,
                         skill_vs_naive=40.0, naive_wmape=15.0))
        rows.append(dict(date=t, horizon_bucket="24-72", mape=12.0,
                         skill_vs_naive=None, naive_wmape=None))
    return pd.DataFrame(rows), b


def test_dislama_esik_alti_gun_karne_disi():
    k, b = _karne_df([3, 2, 1])
    kap = {str(b - dt.timedelta(days=3)): ESIK - 1}
    s = _karne_satirlari(k, kap)
    r = s[-3]
    assert r["olculdu"] is False and r["kapsama_pct"] == ESIK - 1
    assert all(r[a] is None for a in                  # D18 sözleşmesi: null
               ("wmape_0_24", "skill", "naif_wmape", "wmape_24_72"))


def test_dislama_tam_esik_karne_ici():
    """'< %60' kuralın kendisi — sınır dahil değil (v2.151 D19 ile aynı)."""
    k, b = _karne_df([1])
    s = _karne_satirlari(k, {str(b - dt.timedelta(days=1)): ESIK})
    assert s[-1]["olculdu"] is True and s[-1]["wmape_0_24"] == 9.0


def test_dislama_bilinmeyen_kapsama_dokunmaz():
    k, _ = _karne_df([1])
    s = _karne_satirlari(k, None)
    assert s[-1]["olculdu"] is True and s[-1]["kapsama_pct"] is None


def test_kapsama_pct_her_satirda_yayilir():
    k, b = _karne_df([1])
    s = _karne_satirlari(k, {str(b - dt.timedelta(days=1)): 90})
    assert all("kapsama_pct" in r for r in s)
    assert s[-1]["kapsama_pct"] == 90 and s[0]["kapsama_pct"] is None
