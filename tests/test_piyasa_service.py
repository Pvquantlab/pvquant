"""v2.258 — piyasa_service: senaryo fiyatı, EPİAŞ çekimi (sahte taşıyıcı), kapılar."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.ext.turkiye.epias import Istemci, sahte_tasiyici
from pvquant.services import piyasa_service as ps


def test_senaryo_ve_cekim():
    idx = pd.date_range("2025-07-01", periods=48, freq="h", tz="UTC")
    s = ps.senaryo_fiyat(idx); assert (s.kaynak == "senaryo").all() and s.ptf.iloc[0] == ps.SENARYO_PTF
    items = [{"date": "2025-07-01T00:00:00+03:00", "price": 2600.0}, {"date": "2025-07-01T01:00:00+03:00", "price": 2700.0}]
    smf = [{"date": "2025-07-01T00:00:00+03:00", "systemMarginalPrice": 2500.0}]
    yon = [{"date": "2025-07-01T00:00:00+03:00", "systemDirection": "Enerji Açığı"}]
    c = Istemci("u", "p", transport=sahte_tasiyici({"/v1/markets/dam/data/mcp": items, "/v1/markets/bpm/data/system-marginal-price": smf, "/v1/markets/bpm/data/system-direction": yon}))
    f = ps.fiyat_cek("2025-07-01", "2025-07-01", istemci=c)
    assert len(f) == 2 and (f.kaynak == "epias").all() and str(f.index.tz) == "UTC" and f.ptf.iloc[1] == 2700.0


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    monkeypatch.setattr(ps, "durum", lambda: {"kimlik": False, "son_fiyat": None, "saat": 0, "senaryo": {"ptf": ps.SENARYO_PTF, "smf": ps.SENARYO_SMF, "ad": ps.SENARYO_AD}})
    monkeypatch.setattr(ps, "fiyatlar", lambda idx: ps.senaryo_fiyat(idx))
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    d = istemci.get("/v1/piyasa/durum").json(); assert d["kimlik"] is False and d["senaryo"]["ptf"] == ps.SENARYO_PTF
    f = istemci.get("/v1/piyasa/fiyat?bas=2025-07-01&bitis=2025-07-02").json()
    assert f["senaryo_saat"] == 48 and f["epias_saat"] == 0 and f["satirlar"][0]["ts"].endswith("21:00:00+00:00")
    assert istemci.get("/v1/piyasa/fiyat?bas=2020-01-01&bitis=2025-07-02").status_code == 422


class _SahteIstemci:
    """geri_doldur/gun_oncesi_ptf için: fiyat_paketi parça parça çağrılır; `patlayan` aralıkla başlayan parça hata fırlatır."""
    def __init__(self, patlayan: str | None = None):
        self.cagrilar: list[tuple[str, str]] = []; self.patlayan = patlayan
    def fiyat_paketi(self, b, e):
        self.cagrilar.append((b, e))
        if self.patlayan and b == self.patlayan:
            raise RuntimeError("EPİAŞ 400 Bad Request (sahte)")
        idx = pd.date_range(f"{b} 00:00", f"{e} 23:00", freq="h", tz="Europe/Istanbul").tz_convert("UTC")
        return pd.DataFrame({"ptf": 2000.0, "smf": 2100.0, "yon": "acik"}, index=idx)
    def ptf(self, b, e):
        idx = pd.date_range(f"{b} 00:00", f"{e} 23:00", freq="h", tz="Europe/Istanbul").tz_convert("UTC")
        return pd.Series(2500.0, index=idx, name="ptf")


def test_geri_doldur_bitisi_dune_kirpar_ve_parca_hatasi_durdurmaz(monkeypatch):
    """29.10 (v2.505, canlı ders): bitiş bugün verilince SMF/yön ucu 400 dönüyordu → bitiş düne kırpılır; hatalı parça atlanır, diğerleri yazılır."""
    from datetime import date
    yazilan = []
    monkeypatch.setattr(ps, "kaydet", lambda df: yazilan.append(len(df)) or len(df))
    c = _SahteIstemci(patlayan="2026-10-08")
    r = ps.geri_doldur("2026-10-01", "2026-10-29", parca_gun=7, istemci=c, bugun=date(2026, 10, 29))
    assert r["bitis"] == "2026-10-28" and c.cagrilar[-1] == ("2026-10-22", "2026-10-28")          # bugün (29.10) hiç istenmez
    assert r["durum"] == "kismi" and r["parca"] == 4 and len(r["hatali"]) == 1 and r["hatali"][0]["bas"] == "2026-10-08"
    assert r["yazilan"] == sum(yazilan) == 3 * 7 * 24                                                # 3 başarılı parça × 168 saat
    r2 = ps.geri_doldur("2026-10-20", "2026-10-21", istemci=_SahteIstemci(), bugun=date(2026, 10, 29))
    assert r2["durum"] == "ok" and r2["hatali"] == [] and r2["yazilan"] == 48


def test_gun_oncesi_ptf_yalniz_ptf_ve_kaynak_gop(monkeypatch):
    """29.10 (v2.505): GÖP sonrası bugün+yarın PTF; smf/yön boş, kaynak 'epias_gop'; EPİAŞ hatası 'henuz_yok' (hata değil)."""
    from datetime import date
    tutulan = {}
    monkeypatch.setattr(ps, "kaydet", lambda df: tutulan.update(df=df) or len(df))
    r = ps.gun_oncesi_ptf(istemci=_SahteIstemci(), bugun=date(2026, 10, 29))
    df = tutulan["df"]
    assert r["durum"] == "ok" and r["yazilan"] == 48 and r["yarin_saat"] == 24
    assert (df["kaynak"] == "epias_gop").all() and df["smf"].isna().all() and df["yon"].isna().all() and df["ptf"].iloc[0] == 2500.0

    class _Patlayan(_SahteIstemci):
        def ptf(self, b, e): raise RuntimeError("400 henüz yayımlanmadı")
    r2 = ps.gun_oncesi_ptf(istemci=_Patlayan(), bugun=date(2026, 10, 29))
    assert r2["durum"] == "henuz_yok" and r2["yazilan"] == 0


def test_santral_listesi_get_ve_kgup_region():
    """29.10 (v2.505, canlı sınama): santral listesi GET (POST 404 veriyordu); KGÜP ucu region ister → varsayılan TR1."""
    import httpx
    gorulen = []
    def tasiyici(req: httpx.Request):
        gorulen.append((req.method, req.url.path, (req.read() or b"").decode()))
        if req.url.path.endswith("/cas/v1/tickets"):
            return httpx.Response(201, text="TGT-sahte")
        if req.url.path.endswith("/powerplant-list"):
            return httpx.Response(200, json={"items": [{"id": 1, "name": "A", "eic": "40W", "shortName": "A"}]})
        if req.url.path.endswith("/dpp"):
            return httpx.Response(200, json={"items": [{"date": "2026-10-27T00:00:00+03:00", "toplam": 5.0}]})
        return httpx.Response(404)
    c = Istemci("u", "p", transport=httpx.MockTransport(tasiyici))
    assert c.santral_listesi()[0]["eic"] == "40W"
    assert c.kgup("2026-10-27", "2026-10-27").iloc[0] == 5.0
    liste = [g for g in gorulen if g[1].endswith("/powerplant-list")][0]; kg = [g for g in gorulen if g[1].endswith("/dpp")][0]
    import json as _j
    assert liste[0] == "GET" and kg[0] == "POST" and _j.loads(kg[2])["region"] == "TR1"
