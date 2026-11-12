"""v2.604 (Faz 4 F4-J, Stage 12) — EPİAŞ entegrasyonu: ölü ikinci istemci kaldırıldı; gün önbelleği yalnız kesinleşmiş (7+ gün eski) pencereleri yazar;
tarih aralıkları piyasa gününe (İstanbul) göre; üretim istemcisi önbellek dizinini ayardan alır."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from pvquant.ext.turkiye.epias import ONBELLEK_KESINLESME_GUN, Istemci, sahte_tasiyici
from pvquant.services import piyasa_service as ps


def _items(bas: str, n: int = 24):
    return [{"date": f"{bas}T{h:02d}:00:00+03:00", "price": 1000.0 + h} for h in range(n)]


def test_olu_istemci_kaldirildi():
    import pvquant.ext.kaynak.epias as eski
    assert not hasattr(eski, "SeffaflikIstemci") and not hasattr(eski, "UC") and eski.ESKI_FORMUL_SON == "2025-12-31"   # eski formül guard'lı kalır
    s = pd.Series([1.0] * 24, index=pd.date_range("2026-01-01", periods=24, freq="h", tz="Europe/Istanbul"))
    with pytest.raises(ValueError, match="eski formül"):
        eski.dengesizlik_maliyeti(s, s, s, s)


def test_onbellek_yalniz_kesinlesmis_pencere(tmp_path):
    sayac = {"n": 0}
    import httpx
    ic = sahte_tasiyici({"/v1/markets/dam/data/mcp": _items("2026-01-05")})
    def handler(req):
        if req.url.path.endswith("/mcp"):
            sayac["n"] += 1
        return ic.handler(req)
    c = Istemci("u", "p", transport=httpx.MockTransport(handler), onbellek_dizin=tmp_path)
    eski_bit = (pd.Timestamp.now(tz="Europe/Istanbul").normalize() - pd.Timedelta(days=ONBELLEK_KESINLESME_GUN + 2)).date()
    a = c.ptf(eski_bit.isoformat(), eski_bit.isoformat()); b = c.ptf(eski_bit.isoformat(), eski_bit.isoformat())   # tek günlük pencere: 24 saat tam
    assert sayac["n"] == 1 and len(a) == 24 and a.equals(b) and list(tmp_path.glob("ptf_*.csv"))   # kesinleşmiş pencere: ikinci çağrı önbellekten
    yeni_bit = (pd.Timestamp.now(tz="Europe/Istanbul").normalize() - pd.Timedelta(days=1)).date()
    c.ptf(yeni_bit.isoformat(), yeni_bit.isoformat()); c.ptf(yeni_bit.isoformat(), yeni_bit.isoformat())
    assert sayac["n"] == 3   # düzeltme penceresi: her çağrı ağdan (önbelleğe yazılmaz)
    assert Istemci("u", "p", transport=httpx.MockTransport(handler)).onbellek_dizin is None   # dizin verilmezse önbellek kapalı
    # tam 7 gün geride biten pencere yazılır (7+ gün); 6 gün geride biten yazılmaz
    sinir = (pd.Timestamp.now(tz="Europe/Istanbul").normalize() - pd.Timedelta(days=ONBELLEK_KESINLESME_GUN)).date()
    n0 = sayac["n"]; c.ptf(sinir.isoformat(), sinir.isoformat()); c.ptf(sinir.isoformat(), sinir.isoformat()); assert sayac["n"] == n0 + 1
    alti = sinir + timedelta(days=1); n0 = sayac["n"]; c.ptf(alti.isoformat(), alti.isoformat()); c.ptf(alti.isoformat(), alti.isoformat()); assert sayac["n"] == n0 + 2
    # kısmi yanıt (24 yerine 20 saat) önbelleğe yazılmaz
    kismi = sahte_tasiyici({"/v1/markets/dam/data/mcp": _items("2026-01-05", 20)})
    def handler2(req):
        if req.url.path.endswith("/mcp"):
            sayac["n"] += 1
        return kismi.handler(req)
    c2 = Istemci("u", "p", transport=httpx.MockTransport(handler2), onbellek_dizin=tmp_path / "kismi")
    n0 = sayac["n"]; c2.ptf(eski_bit.isoformat(), eski_bit.isoformat()); c2.ptf(eski_bit.isoformat(), eski_bit.isoformat())
    assert sayac["n"] == n0 + 2 and not list((tmp_path / "kismi").glob("*.csv"))


def test_piyasa_gunu_istanbul_ve_gece_isi_dilimi(monkeypatch):
    # 12.11.2026 22:30 UTC = 13.11.2026 01:30 TSİ → piyasa günü 13.11; UTC günü 12.11
    simdi = pd.Timestamp("2026-11-12T22:30:00Z")
    assert ps.piyasa_gunu(simdi) == date(2026, 11, 13) and ps.piyasa_gunu(pd.Timestamp("2026-11-12T20:30:00Z")) == date(2026, 11, 12)
    monkeypatch.setattr(ps, "piyasa_gunu", lambda simdi=None: date(2026, 11, 13))
    monkeypatch.setattr(ps, "kimlik_var", lambda: True)
    yakalanan = {}
    monkeypatch.setattr(ps, "fiyat_cek", lambda bas, bitis, istemci=None: yakalanan.update(bas=bas, bitis=bitis) or None)
    monkeypatch.setattr(ps, "kaydet", lambda df: 0)
    assert ps.gece_piyasa(gun=3)["durum"] == "ok" and yakalanan == {"bas": "2026-11-09", "bitis": "2026-11-12"}   # dün = piyasa günü − 1
    r = ps.geri_doldur("2026-11-01", "2026-12-31", istemci=object())
    assert r["bitis"] == "2026-11-12"   # geri doldurma bitişi piyasa dününe kırpılır


def test_istemci_onbellek_ayardan(monkeypatch, tmp_path):
    from pvquant import config
    s = config.get_settings()
    monkeypatch.setattr(s, "epias_kullanici", "u"); monkeypatch.setattr(s, "epias_sifre", "p"); monkeypatch.setattr(s, "epias_onbellek_dizin", str(tmp_path))
    assert str(ps._istemci().onbellek_dizin) == str(tmp_path)
    monkeypatch.setattr(s, "epias_onbellek_dizin", "")
    assert ps._istemci().onbellek_dizin is None
