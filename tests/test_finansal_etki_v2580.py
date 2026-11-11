"""v2.580 (Faz 2 F2-B, Stage 3A) — Finansal Etki Merkezi: üretim/program özeti ve satış geliri. Saf testler (program kuralı saatlik_hesap ile
birebir, sapma işareti, eksik saat 0 sayılmaz, bildirilen/öneri karışımı, ölçüm sınırı; tarife sabit / PTF (senaryo saat) / çok zamanlı / yok;
resmî YEK kalemi yalnız ay döneminde ve YEKDEM segmentinde; pencere günü). Test DB ile uçtan uca (tarife sabit, 10 günlük Eylül verisi)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.ext.platform import finans as fn
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe

UTC = timezone.utc
BUGUN = date(2026, 11, 11)
PLANT = {"id": "p1", "name": "Test GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul", "params_json": {}}


def _izgara(kod: str) -> tuple[dict, pd.DatetimeIndex]:
    d = fe.donem(PLANT, kod, BUGUN)
    return d, fn.saat_kumesi(d)


def _df(izgara: pd.DatetimeIndex, gercek_yok: list[int] | None = None, oneri_yok: list[int] | None = None) -> pd.DataFrame:
    """06–18 TSİ 100..600 kW, gece 0; öneri = gerçek × 1,1; naif = gerçek. gercek_yok/oneri_yok: ızgara konumları NaN."""
    ist = izgara.tz_convert("Europe/Istanbul")
    ger = np.array([float(100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0 for h in ist.hour])
    df = pd.DataFrame({"gercek_kw": ger, "kgup_kw": ger * 1.1, "naif_kw": ger, "uretim_kaynak": "scada", "cekis_kw": np.nan}, index=izgara)
    for i in (gercek_yok or []):
        df.iloc[i, df.columns.get_loc("gercek_kw")] = np.nan
    for i in (oneri_yok or []):
        df.iloc[i, df.columns.get_loc("kgup_kw")] = np.nan
    return df


def _fiyat(izgara: pd.DatetimeIndex, senaryo: list[int] | None = None) -> pd.DataFrame:
    f = pd.DataFrame({"ptf": 2000.0, "smf": 1900.0, "yon": "dengede", "kaynak": "epias"}, index=izgara)
    for i in (senaryo or []):
        f.iloc[i, f.columns.get_loc("ptf")] = 2651.81; f.iloc[i, f.columns.get_loc("kaynak")] = "senaryo"; f.iloc[i, f.columns.get_loc("yon")] = None
    return f


# ---------------- program kuralı ----------------
def test_program_serisi_saatlik_hesapla_birebir():
    _, iz = _izgara("2026-10-05")
    df = _df(iz)
    bil = pd.Series(np.nan, index=iz); bil.iloc[8:14] = 0.55   # 6 saat bildirilen KGÜP (MWh)
    prog, kaynak = fe.program_serisi(df, bil, iz)
    assert prog.iloc[8] == 0.55 and kaynak.iloc[8] == "bildirilen" and kaynak.iloc[3] == "oneri" and abs(prog.iloc[12] - 0.55) < 1e-9
    pv, _, _, _ = ds.saatlik_hesap(df.reset_index().rename(columns={"index": "ts_utc"}), _fiyat(iz), bildirilen_mwh=bil)
    assert np.allclose(pv["kgup"].values, prog.reindex(pv.index).values) and list(pv["program_kaynak"]) == list(kaynak.reindex(pv.index))
    prog2, kaynak2 = fe.program_serisi(df, None, iz)
    assert np.allclose(prog2.values, df["kgup_kw"].values / 1000.0) and (kaynak2 == "oneri").all()


def test_uretim_ozeti_toplamlar_sapma_ve_eksik_saat():
    d, iz = _izgara("2026-10-05")
    df = _df(iz, gercek_yok=[10, 11], oneri_yok=[20])   # iki ölçüm saati eksik, bir öneri saati eksik (gece)
    o = fe.uretim_ozeti_saf(d, iz, df, None, "scada", {"beklenen_saat": 24, "olculdu_saat": 22, "kapsama_pct": 91.7}, 1000.0)
    ger = df["gercek_kw"] / 1000.0; on = df["kgup_kw"] / 1000.0
    assert o["gerceklesen"]["mwh"] == round(float(ger.sum()), 3) and o["gerceklesen"]["saat"] == 22 and o["gerceklesen"]["beklenen_saat"] == 24
    assert o["planlanan"]["mwh"] == round(float(on.sum()), 3) and o["planlanan"]["saat"] == 23 and o["planlanan"]["kaynak"] == "oneri"
    ortak = ger.notna() & on.notna()
    assert o["sapma"]["ortak_saat"] == int(ortak.sum()) == 21
    assert o["sapma"]["mwh"] == round(float(ger[ortak].sum() - on[ortak].sum()), 3) and o["sapma"]["mwh"] < 0 and o["sapma"]["yon"] == "eksik"
    assert o["sapma"]["pct"] == round(100 * (ger[ortak].sum() - on[ortak].sum()) / on[ortak].sum(), 2)
    assert o["tahmin"]["mwh"] == o["planlanan"]["mwh"] and o["sapma"]["tahmine_gore_mwh"] == o["sapma"]["mwh"]
    assert o["gerceklesen"]["sinir"] == "plant_gross_ac" and o["gerceklesen"]["kaynak_saat"] == {"scada": 22} and o["gerceklesen"]["kapsama"]["kapsama_pct"] == 91.7
    assert any("2 saatte ölçüm yok" in n for n in o["notlar"]) and any("1 ölçüm saatinde program yok" in n for n in o["notlar"])
    assert o["donem"]["kod"] == "2026-10-05" and o["donem"]["tur"] == "gun" and o["kapasite_kwp"] == 1000.0


def test_uretim_ozeti_fazla_dengede_ve_karisik_program():
    d, iz = _izgara("2026-10-05")
    df = _df(iz); df["kgup_kw"] = df["gercek_kw"] * 0.9   # gerçek > program → fazla
    o = fe.uretim_ozeti_saf(d, iz, df, None, "scada", None)
    assert o["sapma"]["yon"] == "fazla" and o["sapma"]["mwh"] > 0
    df2 = _df(iz); df2["kgup_kw"] = df2["gercek_kw"] * 1.001
    assert fe.uretim_ozeti_saf(d, iz, df2, None, "scada", None)["sapma"]["yon"] == "dengede"
    bil = pd.Series(np.nan, index=iz); bil.iloc[6:18] = (df["gercek_kw"].iloc[6:18] / 1000.0).values
    o3 = fe.uretim_ozeti_saf(d, iz, df, bil, "scada", None)
    assert o3["planlanan"]["kaynak"] == "karisik" and o3["planlanan"]["bildirilen_saat"] == 12 and o3["planlanan"]["oneri_saat"] == 12
    assert any("12 saatte bildirilen KGÜP" in n for n in o3["notlar"])
    bos = fe.uretim_ozeti_saf(d, iz, pd.DataFrame(index=iz, columns=["gercek_kw", "kgup_kw"]), None, "scada", None)
    assert bos["gerceklesen"]["mwh"] is None and bos["planlanan"]["mwh"] is None and bos["sapma"]["mwh"] is None and bos["planlanan"]["kaynak"] == "yok"


def test_olcum_siniri_sayac():
    d, iz = _izgara("2026-10-05")
    df = _df(iz); df["uretim_kaynak"] = "sayac_olculmus"
    o = fe.uretim_ozeti_saf(d, iz, df, None, "sayac", None)
    assert o["gerceklesen"]["sinir"] == "pcc_net" and "sayaç" in o["gerceklesen"]["sinir_etiket"]
    df.iloc[:5, df.columns.get_loc("uretim_kaynak")] = "scada"
    o2 = fe.uretim_ozeti_saf(d, iz, df, None, "sayac", None)
    assert o2["gerceklesen"]["sinir"] == "karisik" and "19 saat" in o2["gerceklesen"]["sinir_etiket"] and "5 saat" in o2["gerceklesen"]["sinir_etiket"]
    assert fe.uretim_ozeti_saf(d, iz, _df(iz), None, "sayac", None)["gerceklesen"]["sinir"] == "plant_gross_ac"   # sayaç seçili ama sayaç saati yok


# ---------------- satış geliri ----------------
def test_gelir_sabit_tarife_ve_gun_donemi_resmi_notu():
    d, iz = _izgara("2026-10-05")
    df = _df(iz, gercek_yok=[12])
    g = fe.satis_geliri_saf(d, iz, df["gercek_kw"], {"tip": "sabit", "tl_mwh": 2000.0}, _fiyat(iz), PLANT, "lisansli_serbest", None)
    mwh = float(df["gercek_kw"].sum() / 1000.0)
    b = g["bilesenler"][0]
    assert b["kod"] == "satis_geliri" and b["tutar_tl"] == round(mwh * 2000.0, 2) and b["alacak_tl"] == b["tutar_tl"] and b["borc_tl"] == 0.0
    assert b["nitelik"] == "sozlesme_tahmini" and b["kapsam_saat"] == 23 and b["beklenen_saat"] == 24 and "sabit fiyat" in b["kaynak"]
    assert g["toplam"]["tutar_tl"] == b["tutar_tl"] and g["toplam"]["nitelik"] == "sozlesme_tahmini" and g["toplam"]["giren"] == ["satis_geliri"]
    assert g["tarife"]["ortalama_fiyat_tl_mwh"] == 2000.0 and g["uretim_mwh"] == round(mwh, 3) and g["resmi"] is None and g["fark_tl"] is None
    assert g["fiyat"] == {"epias_saat": 23, "senaryo_saat": 0} and fe.NOT_RESMI_AY in g["notlar"] and fe.NOT_GELIR in g["notlar"]


def test_gelir_ptf_tarifesi_senaryo_saat_ve_cok_zamanli():
    d, iz = _izgara("2026-10-05")
    df = _df(iz)
    f = _fiyat(iz, senaryo=[9, 10])
    g = fe.satis_geliri_saf(d, iz, df["gercek_kw"], {"tip": "ptf", "prim_oran": 0.1, "sabit_ek_tl_mwh": 50.0}, f, PLANT, "lisansli_serbest", None)
    b = g["bilesenler"][0]
    beklenen = float(((df["gercek_kw"] / 1000.0) * (f["ptf"] * 1.1 + 50.0)).sum())
    assert abs(b["tutar_tl"] - beklenen) < 0.01 and b["nitelik"] == "senaryo" and g["fiyat"]["senaryo_saat"] == 2
    assert any("2 saat EPİAŞ fiyatı olmadığından" in n for n in g["notlar"])
    g2 = fe.satis_geliri_saf(d, iz, df["gercek_kw"], {"tip": "ptf", "prim_oran": 0.0}, _fiyat(iz), PLANT, "lisansli_serbest", None)
    assert g2["bilesenler"][0]["nitelik"] == "sozlesme_tahmini" and abs(g2["bilesenler"][0]["tutar_tl"] - float(df["gercek_kw"].sum() / 1000.0 * 2000.0)) < 0.01
    g3 = fe.satis_geliri_saf(d, iz, df["gercek_kw"], {"tip": "cok_zamanli", "gunduz_tl_mwh": 1000.0, "puant_tl_mwh": 3000.0, "gece_tl_mwh": 500.0},
                             _fiyat(iz), PLANT, "lisansli_serbest", None)
    ist = iz.tz_convert("Europe/Istanbul").hour
    fiy = np.where((ist >= 6) & (ist < 17), 1000.0, np.where((ist >= 17) & (ist < 22), 3000.0, 500.0))
    assert abs(g3["bilesenler"][0]["tutar_tl"] - float(((df["gercek_kw"] / 1000.0) * fiy).sum())) < 0.01 and g3["bilesenler"][0]["nitelik"] == "sozlesme_tahmini"


def test_gelir_tarife_yok_senaryo_ve_olcum_yok_eksik():
    d, iz = _izgara("2026-10-05")
    df = _df(iz)
    g = fe.satis_geliri_saf(d, iz, df["gercek_kw"], None, _fiyat(iz), PLANT, "lisansli_serbest", None)
    b = g["bilesenler"][0]
    assert b["nitelik"] == "senaryo" and abs(b["tutar_tl"] - float(df["gercek_kw"].sum() / 1000.0 * 2000.0)) < 0.01 and fe.NOT_TARIFE_YOK in g["notlar"]
    assert g["tarife"] == {"tip": None, "etiket": "tarife yok", "ortalama_fiyat_tl_mwh": 2000.0}
    bos = fe.satis_geliri_saf(d, iz, pd.Series(np.nan, index=iz), {"tip": "sabit", "tl_mwh": 2000.0}, _fiyat(iz), PLANT, "lisansli_serbest", None)
    assert bos["bilesenler"][0]["nitelik"] == "eksik" and bos["bilesenler"][0]["tutar_tl"] is None and bos["toplam"]["tutar_tl"] is None
    assert bos["toplam"]["eksik"] == ["satis_geliri"] and bos["uretim_mwh"] is None


def test_gelir_resmi_yek_kalemi_yalniz_ay_ve_yekdem():
    d, iz = _izgara("2026-10")
    df = _df(iz)
    t = {"tip": "sabit", "tl_mwh": 2500.0}   # tarife tipi burada önemsiz; resmî eşleme segment + kaleme bakar
    bil = {"surum_etiket": "nihai bildirim", "zaman": "2026-11-16T10:00", "kalemler": [
        {"kod": "res", "kalem_ad": "YEK", "yon": "alacak", "tutar_tl": 120000.0}, {"kod": "res", "kalem_ad": "YEK düzeltme", "yon": "borc", "tutar_tl": 2000.0},
        {"kod": "imbalance", "kalem_ad": "Dengesizlik", "yon": "borc", "tutar_tl": 5000.0}]}
    g = fe.satis_geliri_saf(d, iz, df["gercek_kw"], t, _fiyat(iz), PLANT, "lisansli_yekdem", bil)
    assert g["resmi"] is not None and g["resmi"]["kod"] == "satis_geliri_resmi" and g["resmi"]["tutar_tl"] == 118000.0 and g["resmi"]["nitelik"] == "resmi"
    assert g["resmi"]["toplanir"] is False and "nihai bildirim" in g["resmi"]["kaynak"]
    assert g["toplam"]["giren"] == ["satis_geliri"] and g["fark_tl"] == round(g["bilesenler"][0]["tutar_tl"] - 118000.0, 2) and "artı = PVQuant" in g["fark_etiket"]
    g2 = fe.satis_geliri_saf(d, iz, df["gercek_kw"], t, _fiyat(iz), PLANT, "lisansli_yekdem", None)
    assert g2["resmi"] is None and fe.NOT_BILDIRIM_YOK in g2["notlar"]
    g3 = fe.satis_geliri_saf(d, iz, df["gercek_kw"], t, _fiyat(iz), PLANT, "lisansli_serbest", bil)
    assert g3["resmi"] is None and fe.NOT_RESMI_SERBEST in g3["notlar"]
    bil_res_yok = {"surum_etiket": "ön bildirim", "zaman": "", "kalemler": [{"kod": "imbalance", "kalem_ad": "Dengesizlik", "yon": "borc", "tutar_tl": 1.0}]}
    g4 = fe.satis_geliri_saf(d, iz, df["gercek_kw"], t, _fiyat(iz), PLANT, "lisansli_yekdem", bil_res_yok)
    assert g4["resmi"] is None and any("YEK kalemi bulunamadı" in n for n in g4["notlar"])
    dg, izg = _izgara("2026-10-05")
    g5 = fe.satis_geliri_saf(dg, izg, _df(izg)["gercek_kw"], t, _fiyat(izg), PLANT, "lisansli_yekdem", bil)
    assert g5["resmi"] is None and fe.NOT_RESMI_AY in g5["notlar"]


def test_pencere_gun():
    d = fe.donem(PLANT, "2026-10", BUGUN)
    simdi = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
    assert fe.pencere_gun(d, datetime(2026, 11, 9, 21, tzinfo=UTC), simdi) == 44   # 30.09 21:00 UTC → 11.11 09:00 = 41,5 gün → 42 + 2
    assert fe.pencere_gun(d, None, simdi) == 44
    assert fe.pencere_gun(d, datetime(2026, 12, 1, tzinfo=UTC), simdi) == 64   # son ölçüm bugünden ileride (saat farkı) → o referans
    assert fe.pencere_gun(fe.donem(PLANT, "2026-11-11", BUGUN), None, simdi) == 3


# ---------------------------------------------------------------- test DB
@pytest.fixture()
def santral():
    from pvquant.db import sistem_baglami
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    tz = "Europe/Istanbul"
    pj = '{"tarife": {"tip": "sabit", "tl_mwh": 2000}, "segment": "lisansli_serbest"}'
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'fe-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) VALUES(:p, :t, 'FE GES', 1000, 900, 37.0, 32.0, :tz, CAST(:pj AS jsonb))"),
                  {"p": pid, "t": tid, "tz": tz, "pj": pj})
        for g in range(1, 11):   # 1–10 Eylül 2026: 06–18 TSİ 100..600 kW; 5 Eylül 12:00 bayraklı (geçersiz)
            for h in range(0, 24):
                ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=tz).tz_convert("UTC").to_pydatetime()
                kw = float(100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0
                s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, :kw, :kw, :f, 60)"),
                          {"t": tid, "p": pid, "ts": ts, "kw": kw, "f": ("frozen_value" if (g == 5 and h == 12) else "valid")})
            gun0 = pd.Timestamp(f"2026-09-{g:02d}", tz=tz)
            # iki koşu: bir gün önce 03:00 UTC (program kuralı 15:30 kesimi öncesi) ve aynı gün 00:00 UTC (0–24 saat öncülü fizik beklentisi — F2-D kayıp ayrışımı)
            for ra in ((gun0 - pd.Timedelta(days=1)).tz_convert("UTC").normalize() + pd.Timedelta(hours=3), gun0.tz_convert("UTC")):   # ikincisi D 00:00 TSİ = D−1 21:00 UTC (15:30 kesiminden sonra; programa girmez)
                rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) "
                                     "VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"), {"t": tid, "p": pid, "ra": ra.to_pydatetime()}).scalar()
                for h in range(0, 24):
                    ts = pd.Timestamp(f"2026-09-{g:02d} {h:02d}:00", tz=tz).tz_convert("UTC").to_pydatetime()
                    kw = (float(100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0) * 1.1
                    s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw, physics_kw) VALUES(:t, :r, :p, :ts, :kw, :kw, :kw, :ph)"),
                              {"t": tid, "r": rid, "p": pid, "ts": ts, "kw": kw, "ph": kw / 1.1 * 1.2})   # fizik beklentisi 1,2 × gerçek
    yield tid, {"id": pid, "name": "FE GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": tz,
                "params_json": {"tarife": {"tip": "sabit", "tl_mwh": 2000}, "segment": "lisansli_serbest"}, "archived": False}
    with sistem_baglami() as s:
        for t in ("finansal_etki_sonuc", "forecast_values", "forecast_runs", "scada_hourly"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_db_uretim_ozeti_ve_gelir_gun_ve_ay(santral):
    tid, plant = santral
    gun_kwh = sum(float(100 + 50 * min(h - 6, 18 - h)) for h in range(6, 19))   # 4.900 kWh/gün
    o = fe.uretim_ozeti(tid, plant, "2026-09-05", bugun=date(2026, 9, 11))
    assert o["gerceklesen"]["saat"] == 23 and o["gerceklesen"]["mwh"] == round((gun_kwh - 400.0) / 1000.0, 3)   # 12:00 bayraklı saat yok (400 kW)
    assert o["planlanan"]["saat"] == 24 and o["planlanan"]["kaynak"] == "oneri" and o["planlanan"]["mwh"] == round(gun_kwh * 1.1 / 1000.0, 3)
    assert o["planlanan"]["tamamlanan_saat"] == 1 and any("1 ölçümsüz saatin programı" in n for n in o["notlar"])   # bayraklı 12:00: program arşivden
    assert o["sapma"]["ortak_saat"] == 23 and o["sapma"]["yon"] == "eksik" and o["gerceklesen"]["kapsama"]["beklenen_saat"] == 24
    assert o["gerceklesen"]["kapsama"]["olculdu_saat"] == 23 and o["gerceklesen"]["sinir"] == "plant_gross_ac"
    g = fe.satis_geliri(tid, plant, "2026-09-05", bugun=date(2026, 9, 11))
    assert g["bilesenler"][0]["tutar_tl"] == round((gun_kwh - 400.0) / 1000.0 * 2000.0, 2) and g["bilesenler"][0]["nitelik"] == "sozlesme_tahmini"
    ay = fe.ozet(tid, plant, "2026-09", bugun=date(2026, 9, 11))
    assert ay["uretim"]["donem"]["kirpildi"] is True and ay["uretim"]["gerceklesen"]["saat"] == 239 and ay["uretim"]["gerceklesen"]["beklenen_saat"] == 264
    assert ay["uretim"]["gerceklesen"]["mwh"] == round((10 * gun_kwh - 400.0) / 1000.0, 3)
    assert ay["gelir"]["bilesenler"][0]["tutar_tl"] == round((10 * gun_kwh - 400.0) / 1000.0 * 2000.0, 2) and ay["gelir"]["resmi"] is None
    assert fe.NOT_BILDIRIM_YOK not in ay["gelir"]["notlar"] and fe.NOT_RESMI_SERBEST in ay["gelir"]["notlar"]
    assert any("25 saatte ölçüm yok" in n for n in ay["uretim"]["notlar"])
