"""v2.591 (Faz 3 F3-D, DB) — DSG üç perspektif zamanlı üyelik ve sözleşmeyle: üyelik değişimi (C 6 Eylül'de katılır), sözleşme değişimi (6 Eylül'den sabit pay,
öncesi varsayımsal sapma), Σ üye payı = grup, KÜPST dağılım dışı, DSG olmayan portföy, üye yok, izolasyon, kural künyesi (2026 eşiği %5)."""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, bakim_baglami
from pvquant.services import portfoy_dsg_service as sd
from pvquant.services import portfoy_varlik_service as pv

TZ = "Europe/Istanbul"; BUGUN = date(2026, 9, 11); KAPS = {"A": 1000.0, "B": 600.0, "C": 800.0}


def _profil(kap, idx):
    h = idx.tz_convert(TZ).hour.values
    return 0.85 * kap * np.clip(np.sin((h - 6) / 12 * np.pi), 0, None) * ((h >= 6) & (h <= 18))


@pytest.fixture()
def dsg():
    tid, tid2 = str(uuid.uuid4()), str(uuid.uuid4())
    pl = {ad: str(uuid.uuid4()) for ad in ("A", "B", "C")}
    rng = np.random.default_rng(9)
    idx = pd.date_range(pd.Timestamp("2026-09-01", tz=TZ), pd.Timestamp("2026-09-12", tz=TZ), freq="h", inclusive="left").tz_convert("UTC")
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'sd-test', 'active'), (:t2, 'sd-test-2', 'active')"), {"t": tid, "t2": tid2})
        for ad, pid in pl.items():
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :ad, :kap, 37.0, 32.0, :tz, '{\"segment\": \"lisansli_serbest\"}')"),
                      {"p": pid, "t": tid, "ad": f"GES {ad}", "kap": KAPS[ad], "tz": TZ})
            kap = KAPS[ad]; p50 = _profil(kap, idx); carpan = {"A": 1.08, "B": 0.92, "C": 1.0}[ad]
            y = np.clip(p50 * carpan + rng.normal(0, 0.03 * kap, len(idx)) * (p50 > 0), 0, None)
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, 'valid', 60)"),
                      [{"t": tid, "p": pid, "ts": t.to_pydatetime(), "kw": float(v)} for t, v in zip(idx, y, strict=True) if t < pd.Timestamp(BUGUN, tz=TZ)])
            for g in pd.DatetimeIndex(idx.tz_convert(TZ).normalize().unique()):
                ra = (g - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=10)
                rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"),
                                {"t": tid, "p": pid, "ra": ra.to_pydatetime()}).scalar()
                m = (idx >= g.tz_convert("UTC")) & (idx < (g + pd.Timedelta(days=1)).tz_convert("UTC"))
                s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90)"),
                          [{"t": tid, "r": rid, "p": pid, "ts": t.to_pydatetime(), "p50": float(a), "p10": float(a * 0.8), "p90": float(min(a * 1.2, kap))} for t, a in zip(idx[m], p50[m], strict=True)])
    k = pv.kurulus_ekle(tid, "DSG Yöneticisi", "dsg_yoneticisi")
    pid = pv.portfoy_ekle(tid, "DSG-X", "dsg", "2026-01-01", dsg={"dsg_kodu": "DSG-X", "yonetici_kurulus_id": k})
    tp = pv.portfoy_ekle(tid, "Toplayıcı", "toplayici", "2026-01-01")
    pv.uyelik_ekle(tid, pid, pl["A"], "2026-01-01", dogrulama="dogrulandi", belge_adi="a.pdf"); pv.uyelik_ekle(tid, pid, pl["B"], "2026-01-01")
    pv.uyelik_ekle(tid, pid, pl["C"], "2026-09-06")
    pv.sozlesme_ekle(tid, "dsg_uyelik", "2026-09-06", portfoy_id=pid, taraf_a_kurulus_id=k, dagitim_yontemi="sabit_pay",
                     parametreler={"paylar": {"GES A": 0.5, "GES B": 0.3, "GES C": 0.2}, "yonetim_ucreti_tl": 300.0}, dogrulama="dogrulandi", belge_adi="dsg-sozlesme.pdf")
    yield tid, tid2, pid, tp, pl
    with bakim_baglami() as s:
        for t in ("dogrulama_sonuc", "finansal_etki_sonuc", "portfoy_sonuc", "ticari_sozlesme", "portfoy_uyelik", "dsg_grubu", "toplayici_kapsami", "portfoy", "kurulus", "denetim_izi",
                  "forecast_values", "forecast_runs", "scada_hourly", "plants"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id IN (:t, :t2)"), {"t": tid, "t2": tid2})
        s.execute(text("DELETE FROM tenants WHERE id IN (:t, :t2)"), {"t": tid, "t2": tid2})


def test_db_uc_perspektif_uyelik_ve_sozlesme_degisimi(dsg):
    tid, tid2, pid, tp, pl = dsg
    o = sd.donem(tid, pid, "2026-09-10", bugun=BUGUN)
    assert o["durum"] == "ok" and o["santral"] == 3 and o["hesaba_giren"] == 3 and o["dsg"]["n_saat"] == 24 and o["portfoy"]["dsg_kodu"] == "DSG-X"
    per = o["perspektifler"]; dag = per["sozlesmesel"]
    assert o["yontem"] == "sabit_pay" and dag["etiket"] == "Sözleşmeye dayalı dağılım" and dag["kontrol"] is True and {s["santral"]: s["pay_pct"] for s in dag["satirlar"]} == {"GES A": 50.0, "GES B": 30.0, "GES C": 20.0}
    assert sum(s["grup_payi_tl"] for s in dag["satirlar"]) == pytest.approx(o["dsg"]["edt_grup_tl"], abs=0.05) and dag["toplam"]["ucret_tl"] == -300.0
    assert per["dsg_ici"]["nitelik"] == "senaryo" and per["ozet"]["nitelik"] == "senaryo"   # B ve C beyan, fiyat senaryo → en zayıf kazanır
    assert per["bagimsiz"]["toplam_edt_tl"] == o["dsg"]["edt_tek_tl"] and per["dsg_ici"]["netlesme_farki_tl"] == pytest.approx(o["dsg"]["edt_dsg_tl"] - o["dsg"]["edt_tek_tl"], abs=0.01)
    assert all(s["kupst_dahil_degil"] for s in dag["satirlar"]) and per["bagimsiz"]["satirlar"][0]["uyelik_dogrulama"] == "dogrulandi"
    assert o["kural"]["esik"] == 0.05 and "13869" in (o["kural"]["esik_kaynak"] or "") and o["kural"]["belirsiz_2027"] is False and o["fiyat"]["senaryo_saat"] == 24
    assert o["sozlesme"]["belge_adi"] == "dsg-sozlesme.pdf" and len(o["meta"]["uyelik_anlik"]) == 3 and len(o["meta"]["sozlesme_anlik"]) == 1 and o["meta"]["uyelik_pencerede_degisti"] is False
    # 3 Eylül: C üye değil, sözleşme yok → iki üye, varsayımsal sapma anahtarı
    e = sd.donem(tid, pid, "2026-09-03", bugun=BUGUN)
    assert e["santral"] == 2 and e["sozlesme"] is None and e["yontem"] == "sapma" and e["perspektifler"]["sozlesmesel"]["etiket"] == "Varsayımsal maliyet dağılımı"
    assert sum(s["grup_payi_tl"] for s in e["perspektifler"]["sozlesmesel"]["satirlar"]) == pytest.approx(e["dsg"]["edt_grup_tl"], abs=0.05)
    assert sd.NOT_B9 not in e["notlar"] and any("Varsayımsal" in n or "doğrulanmış bir sözleşme" in n for n in e["notlar"])
    # kırpılmış ay: üyelik dönem içinde değişti
    a = sd.donem(tid, pid, "2026-09", bugun=BUGUN)
    assert a["santral"] == 3 and a["meta"]["uyelik_pencerede_degisti"] is True and any("üyelik değişti" in n for n in a["notlar"]) and a["dsg"]["n_saat"] >= 10 * 24
    # DSG olmayan portföy, üye yok, izolasyon
    assert sd.donem(tid, tp, "2026-09-10", bugun=BUGUN)["durum"] == "dsg_degil"
    assert sd.donem(tid, pid, "2026-09-10", bugun=BUGUN, tarih=date(2025, 6, 1))["durum"] == "uye_yok"
    assert sd.donem(tid2, pid, "2026-09-10", bugun=BUGUN)["durum"] == "portfoy_yok"
