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
