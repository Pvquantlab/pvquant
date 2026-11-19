"""19.11 canli ozellik testi (Bulgu 4 + 5): is geregi «kayit yok» uclari 200 + {yok: true}; isitici yer tutuculari onceki ay / gecen ceyrek."""
import inspect

from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import calib_service, yanit_isitici

PLANT = "33333333-3333-3333-3333-333333333333"


def test_kalibrasyon_kayit_yoksa_200_yok(monkeypatch):
    """Canlida Karapinar/Golden 33 icin /kalibrasyon 404 → tarayici konsolunda «Failed to load resource» (sayfa dogru bos durumu gosteriyordu)."""
    monkeypatch.setattr(calib_service, "kalibrasyon_ozeti", lambda t, p: None)
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"tenant_id": "t", "sub": "u", "role": "viewer"}
    try:
        r = TestClient(api_main.app).get(f"/v1/plants/{PLANT}/kalibrasyon")
        assert r.status_code == 200, r.text
        assert r.json() == {"yok": True, "mesaj": "aktif kalibrasyon yok"}
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)
    assert "HTTPException(404" not in inspect.getsource(api_main._kalibrasyon_uret)
    assert "HTTPException(404, \"henüz" not in inspect.getsource(api_main.kayip_agaci_uc)


def test_isitici_yer_tutuculari_onceki_ay_gecen_ceyrek():
    g = yanit_isitici.gunler()
    assert len(g["onceki_ay"]) == 7 and g["onceki_ay"] < g["gecen_ay"] < g["bugun"][:7]
    assert g["gecen_ceyrek"][4:6] == "-Q" and g["gecen_ceyrek"][6] in "1234"
    sabit = {"bugun": "2026-11-19", "yarin": "2026-11-20", "gecen_ay": "2026-10", "onceki_ay": "2026-09", "gecen_ceyrek": "2026-Q3"}
    assert yanit_isitici.anahtar_coz("finansal-etki?donem={onceki_ay}&uretim=None&itibariyle=None", sabit) == "finansal-etki?donem=2026-09&uretim=None&itibariyle=None"
    assert yanit_isitici.anahtar_coz("finansal-etki?donem={gecen_ceyrek}&uretim=None&itibariyle=None", sabit) == "finansal-etki?donem=2026-Q3&uretim=None&itibariyle=None"
    assert yanit_isitici.anahtar_coz("kgup?gun={yarin}", sabit) == "kgup?gun=2026-11-20"   # eski yer tutucular ayni


def test_gecen_ceyrek_yil_basi(monkeypatch):
    """Ocak-Mart: son tam ceyrek onceki yilin Q4'u."""
    import datetime as dt

    class _Sabit(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2027, 2, 10, 12, 0, tzinfo=tz)
    monkeypatch.setattr(dt, "datetime", _Sabit)
    g = yanit_isitici.gunler()
    assert g["gecen_ceyrek"] == "2026-Q4" and g["gecen_ay"] == "2027-01" and g["onceki_ay"] == "2026-12"


def test_isitici_kayitlari_bulgu5():
    k = inspect.getsource(api_main._yanit_isiticisini_baslat)
    for anahtar in ("finansal-etki?donem={onceki_ay}&uretim=None&itibariyle=None", "finansal-etki?donem={gecen_ceyrek}&uretim=None&itibariyle=None",
                    "finansal-etki?donem={gecen_ay}&uretim=scada&itibariyle=None", 'f"skill?bucket={b}&gun=90"', "dogrulama/bagimsiz?gun=90&kural=program&taze=0"):
        assert anahtar in k, anahtar
    assert "def _finans_isit(tenant_id: str, plant_id: str, donem: str | None = None, uretim: str | None = None)" in inspect.getsource(api_main._finans_isit)
