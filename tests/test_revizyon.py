"""v2.507 (F-10) — gün içi revize program önerisi: SAF kıyas (eşik, taban, revizyon son anı = teslimat − 30 dk), alarm kuralı dalı, API kapısı."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import alarm_service, revizyon_service as rv

IST = "Europe/Istanbul"


def _gun():
    idx = pd.date_range("2026-10-30 00:00", periods=24, freq="h", tz=IST)
    prog = pd.Series([0] * 6 + [2, 5, 8, 10, 11, 11, 10, 8, 5, 2] + [0] * 8, index=idx, dtype=float)
    return idx, prog


def test_oner_df_esik_taban_ve_son_an():
    idx, prog = _gun()
    bek = prog.copy(); bek.iloc[11] = 8.0; bek.iloc[12] = 6.5; bek.iloc[14] = 5.2     # 11 ve 12 eşik üstü, 14 altı
    r = rv.oner_df(prog, bek, pd.Timestamp("2026-10-30 09:40", tz=IST), kurulu_guc_mw=12)
    assert r["oneri_saatleri"] == [11, 12] and r["ilk_revizyon_son"].endswith("10:30:00+03:00")
    s11 = next(s for s in r["saatler"] if s["saat"] == 11)
    assert s11["revizyon_son"].endswith("10:30:00+03:00") and s11["esik_mwh"] == 1.1 and s11["fark_mwh"] == -3.0 and s11["revize_mumkun"]
    s9 = next(s for s in r["saatler"] if s["saat"] == 9)
    assert s9["revize_mumkun"] is False and s9["oneri"] is False                           # 09:00 için son an 08:30 geçti
    # taban: kurulu gücün %2'si (0,24 MWh) — sıfır/küçük programda gürültü önerilmez
    assert next(s for s in r["saatler"] if s["saat"] == 20)["esik_mwh"] == 0.24
    # saat ilerleyince 11 pencereden çıkar
    assert rv.oner_df(prog, bek, pd.Timestamp("2026-10-30 10:45", tz=IST), kurulu_guc_mw=12)["oneri_saatleri"] == [12]
    # beklenen yoksa fark None, öneri yok
    r2 = rv.oner_df(prog, prog.iloc[:12], pd.Timestamp("2026-10-30 09:40", tz=IST))
    assert all(s["fark_mwh"] is None for s in r2["saatler"] if s["saat"] >= 12) and r2["oneri_saatleri"] == []
    # eşik oranı parametre
    assert rv.oner_df(prog, bek, pd.Timestamp("2026-10-30 09:40", tz=IST), esik_oran=0.5, kurulu_guc_mw=12)["oneri_saatleri"] == []


def test_alarm_kurali_dali():
    plant = {"id": "p", "name": "A", "params_json": {"alarm_kurallari": ["kgup_revizyon_onerisi"]}}
    out = alarm_service.ek_alarmlar(plant, {"revizyon_oneri_saatleri": [11, 12], "revizyon_toplam_fark_mwh": -6.3, "revizyon_ilk_son": "2026-10-30T10:30:00+03:00"})
    assert len(out) == 1 and out[0][0] == "kgup_revizyon_onerisi" and "11:00, 12:00" in out[0][2] and "10:30" in out[0][2] and "-6.3" in out[0][2]
    assert alarm_service.ek_alarmlar(plant, {"revizyon_oneri_saatleri": []}) == []
    assert "kgup_revizyon_onerisi" in alarm_service.EK_KURALLAR and alarm_service.ESIK_VARSAYILAN["revizyon_esik"] == 0.10
    assert alarm_service.KURAL_ETIKET["kgup_revizyon_onerisi"] == "Program revizyonu önerisi"


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 12000.0, "params_json": {}} if p == "p1" else None)
    idx, prog = _gun(); bek = prog.copy(); bek.iloc[12] = 6.5
    monkeypatch.setattr(rv, "_program_bugun", lambda t, plant, gun: (prog, "bildirilen dosya (sürüm 1)"))
    monkeypatch.setattr(rv, "_beklenen", lambda t, plant, simdi: (bek, "son koşu P50"))
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_revizyon_kapisi(istemci, monkeypatch):
    monkeypatch.setattr(pd.Timestamp, "now", classmethod(lambda cls, tz=None: pd.Timestamp("2026-10-30 09:40", tz=IST).tz_convert(tz) if tz else pd.Timestamp("2026-10-30 09:40", tz=IST)))
    j = istemci.get("/v1/plants/p1/kgup/revizyon").json()
    assert j["durum"] == "ok" and j["oneri_saatleri"] == [12] and j["program_kaynagi"].startswith("bildirilen") and j["esik_oran"] == 0.10
    assert istemci.get("/v1/plants/yok/kgup/revizyon").status_code == 404
