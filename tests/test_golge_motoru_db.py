"""Faz 1 gölge MOTORU — DB'ye bağlı uçtan uca test (izole test DB; RLS). Sözleşme (tests/test_golge_motoru.py'nin DB tamamlayıcısı):
- Gerçek `yayin_nwp_kosusu` / `golge_tekrar_var` / `golge_arsivle` / `golge_degerlendir` yolları: yayın koşusu yazılır, motor aynı NWP ile A/B
  gölgesini `etiket='golge'` arşivler, C artefaktsız → düşüş not edilir ve C yazılmaz; ikinci çağrı tekrar yazmaz (idempotans); farklı NWP → atlanır.
- Müşteri yüzeyleri (koşu geçmişi, yayımlanmış koşu, damga) gölgeyi görmez; yayın koşusu otoriter kalır.
- Değerlendirme: aynı maske, 24-48 kovasında yayin/golge_A/golge_B aynı n; PICP yalnız bant varsa.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_kosu_kunyesi_v2572 import (  # noqa: F401 — DB fixture'ı (tenant+plant+kalibrasyon, teardown siler)
    _sentetik_meteo,
    santral,
)

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import damga_service as ds
from pvquant.services import forecast_service as fs
from pvquant.services import golge_service as gs


def _ayar(plant, **k):
    taban = {"golge_etkin": "acik", "golge_santraller": plant["id"], "golge_modlar": "A,B,C", "mod_c_golge": "kapali",
             "mod_c_onayli_artefakt": "", "mod_c_musteri": "kapali"}
    taban.update(k)
    return SimpleNamespace(**taban)


def test_db_golge_motoru_uctan_uca_idempotans_ve_degerlendirme(santral):   # noqa: F811 — pytest fixture parametresi
    tid, plant, cid = santral
    simdi = pd.Timestamp.now("UTC").floor("h")
    # Gün sınırı tuzağı (CI 46189752729, 00:12 TSİ): yayın koşusu simdi−1 dk → hem UTC günü (yayin_nwp_kosusu gün başından arar) hem
    # TSİ günü (provenans gün bazında gruplar) aynı kalmalı; iki saat diliminde de saat 0 ise bir saat ileri al.
    while simdi.hour == 0 or simdi.tz_convert("Europe/Istanbul").hour == 0:
        simdi += pd.Timedelta(hours=1)
    nwp = simdi - pd.Timedelta(hours=6)
    meteo = _sentetik_meteo(simdi.strftime("%Y-%m-%d"), 3, kosu_zamani=nwp)
    girdi = fs.TahminGirdisi(mode="B", kalibrasyon_id=cid, kalibrasyon_params={"eta_bos": 0.85}, sapma_ayar={"aktif": False, "neden": "test"})
    yayin_an = simdi - pd.Timedelta(minutes=1)
    yayin_id = fs.arsive_yaz(tid, plant, meteo, fs.tahmin_uret(plant, meteo, girdi, simdi=yayin_an), kalibrasyon_id=cid, etiket=None, girdi=girdi)
    try:
        # 1) motor: gerçek DB yolları (yayın NWP, tekrar, arşiv); meteo/girdi enjekte (ağ yok)
        assert gs.yayin_nwp_kosusu(tid, plant["id"], simdi) == nwp
        r = gs.golge_motoru_calistir(plant, simdi=simdi, ayar=_ayar(plant), meteo_getir=lambda p: meteo, girdi_getir=lambda p: girdi)
        assert r["durum"] == "ok" and r["modlar"]["A"]["durum"] == "ok" and r["modlar"]["B"]["durum"] == "ok"
        assert r["modlar"]["C"]["durum"] == "atlandi" and "C→B" in r["modlar"]["C"]["neden"] and r["golge_c"] == "hibrit_artefakt_yok"
        with sistem_baglami() as s:
            sat = s.execute(text("SELECT etiket, mode, model, run_at, nwp_kosu_zamani, kalibrasyon_id, artefakt_sha16, "
                                 "(SELECT count(*) FROM forecast_values v WHERE v.run_id = r.id) AS n, satir_sayisi "
                                 "FROM forecast_runs r WHERE tenant_id = :t ORDER BY run_at, mode"), {"t": tid}).mappings().all()
        assert [x["etiket"] for x in sat] == ["yayin", "golge", "golge"] and [x["mode"] for x in sat] == ["B", "A", "B"]
        assert all(pd.Timestamp(x["nwp_kosu_zamani"]).tz_convert("UTC") == nwp for x in sat), "aynı yayımlanmış NWP"
        assert all(pd.Timestamp(x["run_at"]).tz_convert("UTC") == simdi for x in sat[1:]) and all(x["n"] == x["satir_sayisi"] > 0 for x in sat)
        assert sat[1]["kalibrasyon_id"] is None and str(sat[2]["kalibrasyon_id"]) == cid and all(x["artefakt_sha16"] is None for x in sat)
        # 2) idempotans: aynı NWP için ikinci tur hiçbir satır yazmaz
        assert gs.golge_tekrar_var(tid, plant["id"], "A", "barhdadi_bennis", nwp) and not gs.golge_tekrar_var(tid, plant["id"], "A", "barhdadi_bennis", nwp - pd.Timedelta(hours=6))
        r2 = gs.golge_motoru_calistir(plant, simdi=simdi + pd.Timedelta(minutes=5), ayar=_ayar(plant), meteo_getir=lambda p: meteo, girdi_getir=lambda p: girdi)
        assert r2["durum"] == "atlandi" and all(v["durum"] == "atlandi" for v in r2["modlar"].values())
        # 3) farklı NWP yayını → atlanır (yayın koşusuyla eşleşmiyor)
        m2 = _sentetik_meteo(simdi.strftime("%Y-%m-%d"), 3, kosu_zamani=nwp + pd.Timedelta(hours=6))
        r3 = gs.golge_motoru_calistir(plant, simdi=simdi, ayar=_ayar(plant), meteo_getir=lambda p: m2, girdi_getir=lambda p: girdi)
        assert r3["durum"] == "atlandi" and "aynı değil" in r3["neden"]
        with sistem_baglami() as s:
            assert s.execute(text("SELECT count(*) FROM forecast_runs WHERE tenant_id=:t AND etiket='golge'"), {"t": tid}).scalar() == 2
        # 4) müşteri yüzeyleri: yayın otoriter, gölge görünmez
        gecmis = fs.kosu_gecmisi(tid, plant["id"], n=10)
        assert len(gecmis) == 1 and gecmis[0].etiket == "yayin"
        hedef = pd.Timestamp(meteo.ghi.index[40])
        yk = fs.yayimlanmis_kosu(tid, plant["id"], hedef, yayin_oncesi=simdi + pd.Timedelta(minutes=10))
        assert yk is not None and yk["kosu"]["run_id"] == yayin_id
        assert pd.Timestamp(ds.hesapla(tid, plant["id"])["son_kosu"]).tz_convert("UTC") == yayin_an
        # 5) değerlendirme: sentetik gerçekleşen (gündüz 24–48 s kovası) → aynı maske, üç mod, aynı n; bant yok → PICP None
        saatler = [ts for ts in meteo.ghi.index if 24 <= (ts - simdi).total_seconds() / 3600 < 48 and meteo.ghi[ts] > 100]
        with bakim_baglami() as s:
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk) VALUES(:t, :p, :ts, 300, 300, 'valid', 60)"),
                      [{"t": tid, "p": plant["id"], "ts": ts.to_pydatetime()} for ts in saatler])
        satirlar = gs.golge_degerlendir(tid, plant, simdi - pd.Timedelta(hours=2), simdi + pd.Timedelta(hours=1))
        k = {(x["mod"], x["kova"]): x for x in satirlar}
        assert {m for m, _ in k} == {"yayin", "golge_A", "golge_B"} and all(kv == "24-48" for _, kv in k)
        n = {m: v["n"] for (m, _), v in k.items()}
        assert len(set(n.values())) == 1 and n["yayin"] == len(saatler) > 0, "aynı maske: her modda aynı saat sayısı"
        assert all(v["picp80"] is None and v["esik"]["picp80"] is None for v in k.values()) and all(v["wmape"] >= 0 for v in k.values())
        assert k[("yayin", "24-48")]["wmape"] == k[("golge_B", "24-48")]["wmape"], "yayın (B) ile gölge B aynı girdi → aynı tahmin"
        # 5b) kanıt toplayıcı betiği (salt okunur): provenans — aynı gün, aynı NWP, gölge yayından sonra
        import importlib.util
        spec = importlib.util.spec_from_file_location("golge_kanit_topla", Path(__file__).resolve().parents[1] / "scripts" / "golge_kanit_topla.py")
        kt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kt)
        prov = kt.provenans({"id": plant["id"]}, simdi - pd.Timedelta(hours=2), simdi + pd.Timedelta(hours=1))
        assert prov["gun"] == 1 and prov["ayni_nwp_gun"] == 1 and prov["golge_gun"] == 1
        g0 = prov["gunler"][0]
        assert g0["yayin_kosu"] == 1 and g0["golge_kosu"] == 2 and g0["golge_modlar"] == ["A", "B"] and g0["ayni_nwp"] and g0["golge_yayindan_sonra"] and g0["c_sha_dolu"] is None
        # 6) devre kesici girdisi: jobs_log'da art arda hata sayımı (en yeniden geriye; ilk 'ok' sayımı keser)
        with bakim_baglami() as s:
            for i, durum in enumerate(("error", "error", "error")):
                s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status, detail) VALUES('golge_tahmin', :t, :p, now() - make_interval(mins => :m), now(), :s, 'test')"),
                          {"t": tid, "p": plant["id"], "m": 30 - i, "s": durum})
        assert gs.golge_son_ardisik_hata(tid, plant["id"]) == 3
        with bakim_baglami() as s:
            s.execute(text("INSERT INTO jobs_log(job, tenant_id, plant_id, started, finished, status, detail) VALUES('golge_tahmin', :t, :p, now(), now(), 'ok', 'test')"), {"t": tid, "p": plant["id"]})
        assert gs.golge_son_ardisik_hata(tid, plant["id"]) == 0
    finally:
        with bakim_baglami() as s:
            s.execute(text("DELETE FROM scada_hourly WHERE tenant_id=:t"), {"t": tid})
            s.execute(text("DELETE FROM jobs_log WHERE tenant_id=:t"), {"t": tid})
