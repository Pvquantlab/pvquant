"""v2.590 (Faz 3 F3-C, DB) — portföy sapma servisi: dönem (gün ve kırpılmış ay) için program (öneri, 15:30 kesimi) / gerçekleşen / gün öncesi tahmin / fizik;
geçersiz ölçüm saati hesap dışı; katkı toplamı; maruziyet saatleri; gelecek risk (program öneri → tahmini risk); üye yok; izolasyon."""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, bakim_baglami
from pvquant.services import portfoy_sapma_service as sp
from pvquant.services import portfoy_varlik_service as pv

TZ = "Europe/Istanbul"; BUGUN = date(2026, 9, 11); KAPS = {"A": 1000.0, "B": 600.0, "C": 800.0}


def _profil(kap, idx):
    h = idx.tz_convert(TZ).hour.values
    return 0.85 * kap * np.clip(np.sin((h - 6) / 12 * np.pi), 0, None) * ((h >= 6) & (h <= 18))


@pytest.fixture()
def portfoy():
    tid, tid2 = str(uuid.uuid4()), str(uuid.uuid4())
    pl = {ad: str(uuid.uuid4()) for ad in ("A", "B", "C")}
    rng = np.random.default_rng(5)
    idx = pd.date_range(pd.Timestamp("2026-09-01", tz=TZ), pd.Timestamp("2026-09-13", tz=TZ), freq="h", inclusive="left").tz_convert("UTC")
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'sp-test', 'active'), (:t2, 'sp-test-2', 'active')"), {"t": tid, "t2": tid2})
        for ad, pid in pl.items():
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :ad, :kap, 37.0, 32.0, :tz, '{\"segment\": \"lisansli_serbest\"}')"),
                      {"p": pid, "t": tid, "ad": f"GES {ad}", "kap": KAPS[ad], "tz": TZ})
            kap = KAPS[ad]; p50 = _profil(kap, idx); carpan = {"A": 1.10, "B": 0.90, "C": 1.0}[ad]   # A fazla, B eksik, C dengede üretir
            y = p50 * carpan + rng.normal(0, 0.02 * kap, len(idx)) * (p50 > 0)
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, :f, 60)"),
                      [{"t": tid, "p": pid, "ts": t.to_pydatetime(), "kw": float(max(v, 0)), "f": ("frozen_value" if (ad == "B" and t == pd.Timestamp("2026-09-10 12:00", tz=TZ)) else "valid")}
                       for t, v in zip(idx, y, strict=True) if t < pd.Timestamp(BUGUN, tz=TZ)])
            for g in pd.DatetimeIndex(idx.tz_convert(TZ).normalize().unique()):   # koşu D−1 10:00 UTC (13:00 TSİ, 15:30 kesiminden önce) → program ve gün öncesi kuralı
                ra = (g - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=10)
                rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"),
                                {"t": tid, "p": pid, "ra": ra.to_pydatetime()}).scalar()
                m = (idx >= g.tz_convert("UTC")) & (idx < (g + pd.Timedelta(days=1)).tz_convert("UTC"))
                s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw, physics_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90, :ph)"),
                          [{"t": tid, "r": rid, "p": pid, "ts": t.to_pydatetime(), "p50": float(a), "p10": float(a * 0.8), "p90": float(min(a * 1.2, kap)), "ph": float(a * 1.05)}
                           for t, a in zip(idx[m], p50[m], strict=True)])
    pid = pv.portfoy_ekle(tid, "Portföy S", "ozel", "2026-01-01")
    for ad in pl:
        pv.uyelik_ekle(tid, pid, pl[ad], "2026-01-01")
    yield tid, tid2, pid, pl
    with bakim_baglami() as s:
        for t in ("dogrulama_sonuc", "portfoy_sonuc", "ticari_sozlesme", "portfoy_uyelik", "dsg_grubu", "toplayici_kapsami", "portfoy", "kurulus", "denetim_izi",
                  "forecast_values", "forecast_runs", "scada_hourly", "plants"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id IN (:t, :t2)"), {"t": tid, "t2": tid2})
        s.execute(text("DELETE FROM tenants WHERE id IN (:t, :t2)"), {"t": tid, "t2": tid2})


def test_db_donem_gun_ay_ve_gelecek(portfoy):
    tid, tid2, pid, pl = portfoy
    o = sp.donem(tid, pid, "2026-09-10", bugun=BUGUN)
    assert o["durum"] == "ok" and o["santral"] == 3 and o["hesaba_giren"] == 3 and o["eksik_santral"] == [] and o["donem"]["kod"] == "2026-09-10" and o["kapasite_kwp"] == 2400.0
    oz = o["ozet"]
    assert oz["saat"] == 24 and oz["program"]["tam_saat"] == 24 and oz["gerceklesen"]["eksik_saat"] == 1 and oz["program_sapma"]["tam_saat"] == 23   # B 12:00 bayraklı → hesap dışı
    assert oz["program_sapma"]["mwh"] is not None and oz["tahmin_hata"]["mwh"] is not None and oz["fizik_sapma"]["mwh"] is not None and oz["fizik"]["saat"] == 24
    # öneri program = gün öncesi tahmin (aynı koşu) → tahmin hatası = −program sapması; fizik = 1,05 × p50 → fizik sapması = sapma − 0,05 × p50
    assert oz["tahmin_hata"]["mwh"] == pytest.approx(-oz["program_sapma"]["mwh"], abs=1e-6) and oz["fizik_sapma"]["mwh"] < oz["program_sapma"]["mwh"]
    k = o["katkilar"]
    assert "GES A" in k["fazla"] and "GES B" in k["eksik"] and "GES B" not in k["fazla"] and "GES A" not in k["eksik"]
    assert sum(r["mwh"] for r in k["satirlar"]) == pytest.approx(k["toplam_mwh"], abs=1e-6) and k["netlesen_mwh"] > 0 and "kısmen dengeliyor" in k["not"]
    assert o["kapsama"]["guvenilirlik"] == "tam" and o["kapsama"]["sapma_tam_saat"] == 23 and o["korelasyon"]["durum"] == "yetersiz_veri"   # 1 gün < 14
    assert 1 <= len(o["maruziyet_saatleri"]["saatler"]) <= 10 and o["maruziyet_saatleri"]["saatler"][0]["baskin_santral"] in ("GES A", "GES B")
    assert o["santral_bilgi"]["GES A"]["program"]["oneri_saat"] == 24 and o["santral_bilgi"]["GES A"]["program"]["bildirilen_saat"] == 0 and o["santral_bilgi"]["GES B"]["olcum_saat"] == 23
    assert len(o["saatlik"]) == 24 and sum(1 for r in o["saatlik"] if not r["tam"]) == 1 and len(o["meta"]["uyelik_anlik"]) == 3 and o["riskli_gunler"][0]["gun"] == "2026-09-10"
    # kırpılmış ay: 1–10 Eylül ölçülü, 11. gün ölçümsüz (bugün) → kirpildi
    a = sp.donem(tid, pid, "2026-09", bugun=BUGUN)
    assert a["donem"]["kirpildi"] is True and a["ozet"]["saat"] == 11 * 24 and a["ozet"]["gerceklesen"]["tam_saat"] == 10 * 24 - 1 and a["kapsama"]["guvenilirlik"] == "kismi"
    assert len(a["riskli_gunler"]) == 5 and a["korelasyon"]["durum"] == "yetersiz_veri" and a["ozet"]["program"]["saat"] == 11 * 24
    # gelecek: program öneri (bildirilen yok) → tahmini risk; bugün + yarın 48 saat
    g = sp.gelecek(tid, pid, gun=2, bugun=BUGUN)   # «son» koşu yalnız yarını kapsar (her koşu tek gün) → 24 saat; program 48 saat
    assert g["durum"] == "ok" and g["risk"]["etiket"] == "tahmini" and g["risk"]["saat"] == 24 and g["program_kaynak"] == {"bildirilen": 0, "oneri": 48, "yok": 0}
    g2 = sp.gelecek(tid, pid, gun=2, kural="gun_oncesi", bugun=BUGUN)   # gün öncesi kuralı iki günü de bulur
    assert g2["risk"]["saat"] == 48 and g2["kural_ad"] == "Gün öncesi tahmin" and g2["risk"]["beklenen_sapma_mwh"] == pytest.approx(0.0, abs=1e-6)   # program = aynı koşu
    assert g["risk"]["program_mwh"] > 0 and g["risk"]["program_bildirilen"] is False and g["santral_program"]["GES A"]["oneri_saat"] == 48 and g["belirsizlik"]["durum"] == "yetersiz_veri"
    # izolasyon / üye yok
    assert sp.donem(tid2, pid, "2026-09-10", bugun=BUGUN)["durum"] == "uye_yok" and sp.gelecek(tid2, pid, bugun=BUGUN)["durum"] == "uye_yok"
    assert sp.donem(tid, pid, "2026-09-10", bugun=BUGUN, tarih=date(2025, 1, 1))["durum"] == "uye_yok"   # üyelik 2026'da başlar
