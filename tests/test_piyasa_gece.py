"""v2.378 (bulgu 29) — gece_piyasa'nın tarih aralığı DÜNLE biter.

EPİAŞ SEF1124: günün MCP'si öğleden önce sorgulanamaz; bitis=bugün olunca
gece 02:00 koşusu 400 yiyip hiç fiyat yazamıyordu (ilk gerçek-kimlikli
koşuda yakalandı — kimlik yokken bu yol hiç çalışmamıştı)."""
from datetime import date, timedelta

from pvquant.services import piyasa_service


def test_gece_piyasa_bitisi_dun(monkeypatch):
    yakalanan = {}
    monkeypatch.setattr(piyasa_service, "kimlik_var", lambda: True)
    monkeypatch.setattr(piyasa_service, "fiyat_cek",
                        lambda bas, bitis: yakalanan.update(bas=bas, bitis=bitis) or None)
    monkeypatch.setattr(piyasa_service, "kaydet", lambda df: 0)
    r = piyasa_service.gece_piyasa(gun=3)
    assert r["durum"] == "ok"
    dun = date.today() - timedelta(days=1)
    assert yakalanan["bitis"] == dun.isoformat()
    assert yakalanan["bas"] == (dun - timedelta(days=3)).isoformat()


def test_kaydet_eksik_alan_mevcudu_silmez():
    """29.10 (v2.505): gün öncesi PTF (smf/yön yok) ya da boş yön parçası, dolu satırı boşaltmaz (COALESCE); dolu değer gelince güncellenir."""
    import pandas as pd
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    idx = pd.date_range("2099-01-01 00:00", periods=2, freq="h", tz="UTC")
    try:
        assert piyasa_service.kaydet(pd.DataFrame({"ptf": [1000.0, 1100.0], "smf": [900.0, 950.0], "yon": ["acik", "fazla"], "kaynak": "epias"}, index=idx)) == 2
        piyasa_service.kaydet(pd.DataFrame({"ptf": [1200.0, 1300.0], "smf": [float("nan")] * 2, "yon": [None, None], "kaynak": "epias_gop"}, index=idx))
        with sistem_baglami() as s:
            rows = s.execute(text("SELECT ptf, smf, yon, kaynak FROM piyasa_fiyat WHERE ts_utc >= '2099-01-01' ORDER BY ts_utc")).fetchall()
        assert [tuple(r) for r in rows] == [(1200.0, 900.0, "acik", "epias_gop"), (1300.0, 950.0, "fazla", "epias_gop")]   # ptf güncel, smf/yön korundu
        piyasa_service.kaydet(pd.DataFrame({"ptf": [1250.0, 1350.0], "smf": [910.0, 960.0], "yon": ["dengede", "acik"], "kaynak": "epias"}, index=idx))
        with sistem_baglami() as s:
            rows = s.execute(text("SELECT smf, yon, kaynak FROM piyasa_fiyat WHERE ts_utc >= '2099-01-01' ORDER BY ts_utc")).fetchall()
        assert [tuple(r) for r in rows] == [(910.0, "dengede", "epias"), (960.0, "acik", "epias")]                       # tam satır üzerine yazar
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM piyasa_fiyat WHERE ts_utc >= '2099-01-01'"))
