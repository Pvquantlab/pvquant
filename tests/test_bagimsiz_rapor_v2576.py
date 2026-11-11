"""v2.576 (Faz 1 F1-E, Stage 8) — bağımsız doğrulama raporu: şablon (HTML/Markdown), JSON bloğu, Excel sayfası, durum etiketi, API."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import text

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.db import sistem_baglami
from pvquant.reporting import build_excel, build_json, from_results
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import olcum_uygunluk_service as ou
from pvquant.services import sablon_rapor_service as srs
from test_reporting import _sentetik_calibration, _sentetik_forecast

UTC = timezone.utc
PLANT = {"id": "p1", "name": "Rapor GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul"}


def _sentetik_sonuc(gun: int = 30, kural: str = "program") -> dict:
    rng = np.random.default_rng(2)
    bas_g = date(2026, 9, 1); bit_g = date(2026, 9, 1 + gun) if gun < 30 else date(2026, 10, 1)
    iz = ou.saat_izgarasi(pd.Timestamp(bas_g, tz="Europe/Istanbul").tz_convert("UTC"), pd.Timestamp(bit_g, tz="Europe/Istanbul").tz_convert("UTC"))
    saat = iz.tz_convert("Europe/Istanbul").hour
    y = pd.Series(np.clip(np.sin(np.pi * (saat - 5) / 14), 0, None) * 800 * rng.uniform(0.5, 1.0, size=len(iz)), index=iz)
    olcum = pd.DataFrame({"power_kw": y.values, "energy_kwh": y.values, "flag": "valid", "kirpma": False, "kapsama_dk": 60}, index=iz).iloc[:-6]
    saatler = ou.siniflandir(iz, olcum, {iz[4 * 24 + 12]: "ariza"})   # 5 Eylül 12:00 TSİ (gündüz)
    rows = []
    for g in pd.date_range(bas_g - pd.Timedelta(days=1), bit_g, freq="D"):
        ra = pd.Timestamp(g, tz="UTC") + pd.Timedelta(hours=3)
        for t in pd.date_range(ra.floor("h") + pd.Timedelta(hours=1), ra.floor("h") + pd.Timedelta(hours=48), freq="h"):
            yt = float(y.get(t, 0.0)); p50 = max(0.0, yt * (1.04 + rng.normal(0, 0.08)))
            rows.append({"ts_utc": t, "run_at": ra, "run_id": f"r{g.date()}", "p50_kw": p50, "p10_kw": p50 * 0.8, "p90_kw": p50 * 1.25, "physics_kw": max(0.0, yt * 1.15),
                         "model": "hybrid_residual", "meteo_source": "acik-nwp", "etiket": None})
    tahmin = pd.DataFrame(rows)
    kosular = tahmin.drop_duplicates("run_id")[["run_id", "run_at", "model", "meteo_source", "etiket"]].assign(mode="C", kalibrasyon_id="c1", yazilim_surumu="v-test", nwp_kosu_zamani=pd.NaT)
    return bd.hesapla_saf(tahmin, saatler, ou.dokum(saatler), PLANT, bas_g, bit_g, kural, "scada", y[y.index < iz[0]], kosular)


def test_sablon_rapor_bolumleri_ve_durum():
    s = _sentetik_sonuc()
    r = srs.bagimsiz_dogrulama("t", PLANT, sonuc=s)
    adlar = [a for a, _ in r.bolumler]
    for b in ("Durum", "Kimlik ve dönem", "Ölçüm kaynağı ve kalitesi", "Tahmin bilgileri (yayımlandığı andaki kayıt)", "Doğruluk ölçütleri",
              "Tahmin aralığı (P10–P90) kapsaması", "Referans modellerle karşılaştırma (aynı saatler, aynı ölçüm)", "Eksik ve dışlanan gündüz saatleri",
              "Gece davranışı", "En zayıf günler", "Güçlü yanlar", "Zayıf yanlar", "Yöntem ve sınırlar", "Yeniden üretim kimliği"):
        assert b in adlar, b
    assert "DOĞRULANMIŞ ÖLÇÜM" in r.bolumler[0][1]
    h = srs.html_sar(r); md = r.markdown()
    assert "Bağımsız tahmin doğrulama raporu" in h and s["meta"]["kosu_kumesi_sha"] in h and s["meta"]["kosu_kumesi_sha"] in md
    assert "Fiziksel model (öğrenilmiş düzeltme olmadan)" in h and "olay kaydı: arıza" in h and "EPİAŞ uzlaştırmasıyla aynı veri değildir" in h
    assert "fiziksel model ve öğrenilmiş düzeltme" in h and "c1" in h   # tahmin bilgileri: mod ve kalibrasyon kimliği
    g, z = srs.guclu_zayif(s)
    assert any("Fiziksel model" in x for x in g + z) and all(x.endswith(".") or x.endswith(")") for x in g + z)


def test_durum_etiketi_simulasyon_ve_eksik():
    s = _sentetik_sonuc()
    assert srs.dogrulama_durumu(s, simulasyon=True)[0] == "GERİYE DÖNÜK SİMÜLASYON"
    kisa = _sentetik_sonuc(gun=8)
    assert srs.dogrulama_durumu(kisa)[0] == "EKSİK DEĞERLENDİRME"
    s2 = json.loads(json.dumps(s, default=str)); s2["butunluk"]["olcum"]["kapsama_pct"] = 50.0
    assert srs.dogrulama_durumu(s2)[0] == "EKSİK DEĞERLENDİRME"
    r = srs.bagimsiz_dogrulama("t", PLANT, sonuc=kisa, simulasyon=True)
    assert "GERİYE DÖNÜK SİMÜLASYON" in r.bolumler[0][1] and "OKUNMAZ" in r.bolumler[0][1]


def test_json_blogu_var_yok_ve_excel_sayfasi():
    fr = _sentetik_forecast(); ctx = from_results(fr, _sentetik_calibration(), plant_name="Test")
    d = json.loads(build_json(ctx))
    assert d["schema_version"] == "1.4.0" and "independent_validation" not in d           # yok = YOK
    wb = load_workbook(BytesIO(build_excel(ctx))); assert "Validation-Independent" not in wb.sheetnames
    ctx.bagimsiz = _sentetik_sonuc()
    d = json.loads(build_json(ctx)); iv = d["independent_validation"]
    assert iv["status"] == "DOĞRULANMIŞ ÖLÇÜM" and iv["rule"] == "program" and iv["dictionary_version"] == bd.SOZLUK_SURUMU
    assert iv["wmape_pct"] == ctx.bagimsiz["metrik"]["wmape"] and iv["hours_evaluated"] == ctx.bagimsiz["metrik"]["n_saat"]
    assert set(iv["references"]) >= {"fizik", "persistans"} and iv["references"]["fizik"]["skill_pct"] is not None
    assert iv["run_set_sha"] == ctx.bagimsiz["meta"]["kosu_kumesi_sha"] and "olay:ariza" in iv["excluded_daytime_hours"]
    assert len(iv["worst_days"]) == 5 and iv["mbe_kw"] is not None
    wb = load_workbook(BytesIO(build_excel(ctx))); assert "Validation-Independent" in wb.sheetnames
    ws = wb["Validation-Independent"]; hucreler = {ws.cell(i, 1).value: ws.cell(i, 2).value for i in range(1, 40)}
    assert hucreler["durum"] == "DOĞRULANMIŞ ÖLÇÜM" and abs(hucreler["wmape"] - ctx.bagimsiz["metrik"]["wmape"]) < 1e-6 and hucreler["kural"] == "program"


@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4()); tz = "Europe/Istanbul"
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'bd-rapor-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) VALUES(:p, :t, 'Rapor BD GES', 1000, 900, 37.0, 32.0, :tz, '{}')"), {"p": pid, "t": tid, "tz": tz})
        for g in range(1, 11):
            for h in range(6, 19):
                ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=tz).tz_convert("UTC").to_pydatetime(); kw = 100 + 50 * min(h - 6, 18 - h)
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, 'valid', 60)"), {"t": tid, "p": pid, "ts": ts, "kw": kw})
            ra = (pd.Timestamp(f"2026-09-{g:02d}", tz=tz) - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=3)
            rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"),
                            {"t": tid, "p": pid, "ra": ra.to_pydatetime()}).scalar()
            for h in range(0, 24):
                ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=tz).tz_convert("UTC").to_pydatetime(); kw = (100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0
                s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw, physics_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90, :ph)"),
                          {"t": tid, "r": rid, "p": pid, "ts": ts, "p50": kw * 1.1, "p10": kw * 0.9, "p90": kw * 1.3, "ph": kw * 1.2})
    yield tid, {"id": pid, "name": "Rapor BD GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": tz, "params_json": {}, "archived": False}
    with sistem_baglami() as s:
        for t in ("dogrulama_sonuc", "forecast_values", "forecast_runs", "scada_hourly"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_db_sablon_uret_ve_api(santral, monkeypatch):
    tid, plant = santral
    icerik, ad = srs.uret(tid, plant, "bagimsiz-dogrulama", gun=10, kural="gun_oncesi", bugun=date(2026, 9, 11))
    h = icerik.decode("utf-8")
    assert ad.startswith("bagimsiz-dogrulama_Rapor_BD_GES_") and ad.endswith(".html")
    assert "EKSİK DEĞERLENDİRME" in h and "en az 14 gün" in h   # 10 gün < 14
    assert "%10,0" in h and "fazla tahmin" in h                     # p50 = 1,1×gerçek → WMAPE %10, nMBE pozitif (zayıf yanlar cümlesi)
    md, ad2 = srs.uret(tid, plant, "bagimsiz-dogrulama", fmt="md", gun=10, kural="gun_oncesi", bugun=date(2026, 9, 11))
    assert ad2.endswith(".md") and md.decode("utf-8").startswith("# Bağımsız tahmin doğrulama raporu")
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        monkeypatch.setattr(bd, "hesapla", lambda t, p, gun=30, kural="program", kaynak="scada", bugun=None: bd.hesapla.__wrapped__(t, p, gun, kural, kaynak, date(2026, 9, 11)) if False else _db_hesap(t, p, gun, kural))
        r = c.get(f"/v1/plants/{plant['id']}/rapor-sablon/bagimsiz-dogrulama?gun=10&kural=gun_oncesi&fmt=md")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown") and "Bağımsız tahmin doğrulama raporu" in r.text
        assert c.get(f"/v1/plants/{plant['id']}/rapor-sablon/bagimsiz-dogrulama?kural=yok").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/rapor-sablon/bagimsiz-dogrulama?fmt=pdf").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/rapor-sablon/bagimsiz-dogrulama?gun=3").status_code == 422
    finally:
        api_main.app.dependency_overrides.clear()


_GERCEK_HESAPLA = bd.hesapla


def _db_hesap(t, p, gun, kural):
    return _GERCEK_HESAPLA(t, p, gun=gun, kural=kural, bugun=date(2026, 9, 11))
