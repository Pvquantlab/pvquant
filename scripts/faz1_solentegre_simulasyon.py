"""v2.577 (11.11.2026, Faz 1 F1-F2) — SOLENTEGRE GES 2025 GERİYE DÖNÜK SİMÜLASYON (test DB; canlıya dokunmaz).

Gerçek üretim: EPİAŞ UEVM 2025 (uzlaştırma sayacı, şebekeye veriş; Faz 0 08 belgesi). Yayımlandığı anda saklanmış tahmin YOK; bu betik
fiziksel modeli (Mod A, kalibrasyonsuz) sonradan elde olan analiz hava verisiyle (Open-Meteo ERA5 arşivi) koşturur ve koşuları
`model='backtest'`, `meteo_source='open-meteo-arsiv'` etiketiyle yazar (karne ve gece doğrulaması bunları ZATEN dışlar). Sonuç motorda
`simulasyon=True` ile ölçülür, rapor «GERİYE DÖNÜK SİMÜLASYON» etiketi taşır ve dogrulama_sonuc'a KAYDEDİLMEZ. Sonuç «modelin analiz
meteosuyla gerçek üretime uyumu»dur; tarihsel tahmin başarısı DEĞİLDİR (NWP yaşı 0, bulut hatası yok, geriye bakış sızıntısı var).

Kullanım (yalnız test DB — betik localhost:55432 dışını reddeder):
  PVQUANT_METEO_KAYNAK=open_meteo PYTHONPATH=src PVQ_DB_URL=... python scripts/faz1_solentegre_simulasyon.py --kanit <klasör> [--yil 2025]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
from sqlalchemy import text  # noqa: E402

SANTRAL_AD = "SOLENTEGRE GES (EPİAŞ 2108, UEVM 2025)"
UFUK_SAAT = 48


def _guvenlik():
    url = os.environ.get("PVQ_DB_URL", "")
    if "localhost:55432" not in url and "127.0.0.1:55432" not in url:
        raise SystemExit("yalnız test DB (localhost:55432); canlıda koşulmaz")
    if os.environ.get("PVQUANT_METEO_KAYNAK") != "open_meteo":
        raise SystemExit("PVQUANT_METEO_KAYNAK=open_meteo gerekir (arşiv hava verisi Open-Meteo ERA5'ten; analiz verisi, tahmin değil)")


def santral_bul():
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT p.id, p.tenant_id, p.name, p.capacity_kwp, p.ac_limit_kw, p.lat, p.lon, p.tz, p.params_json FROM plants p WHERE p.name=:n"), {"n": SANTRAL_AD}).mappings().first()
    if r is None:
        raise SystemExit("Solentegre santralı test DB'de yok (Faz 0 kanit/08_ice_al.py)")
    d = dict(r); d["id"] = str(d["id"]); d["tenant_id"] = str(d["tenant_id"]); return d


def meteo_cek(plant: dict, yil: int, kanit: Path):
    """Open-Meteo ERA5 arşivi, aylık parçalar; CSV önbelleği kanıt klasöründe (yeniden üretim)."""
    from pvquant.io.meteo import OpenMeteoClient, MeteoData
    yol = kanit / f"F1-F2_meteo_arsiv_{yil}.csv"
    if yol.exists():
        df = pd.read_csv(yol, index_col=0, parse_dates=True)
        df.index = pd.DatetimeIndex(df.index, tz="UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    else:
        parcalar = []
        c = OpenMeteoClient()
        for ay in range(1, 13):
            bas = date(yil, ay, 1); bit = date(yil + (ay == 12), ay % 12 + 1, 1) - pd.Timedelta(days=1)
            md = c.get_historical(float(plant["lat"]), float(plant["lon"]), bas.isoformat(), bit.isoformat())
            parcalar.append(md.to_dataframe()); print(f"meteo {yil}-{ay:02d}: {len(parcalar[-1])} saat")
        df = pd.concat(parcalar).sort_index(); df = df[~df.index.duplicated()]
        df.to_csv(yol)
    return MeteoData(ghi=df["ghi"], temp_air=df["temp_air"], wind_speed_10m=df["wind_speed_10m"], relative_humidity=df.get("relative_humidity"),
                     cloud_cover=df.get("cloud_cover"), latitude=float(plant["lat"]), longitude=float(plant["lon"]), timezone="UTC",
                     precipitation=df.get("precipitation"), kaynak="open-meteo-arsiv", nwp_model="ERA5 (analiz; tahmin değil)")


def fizik_kos(plant: dict, meteo):
    from pvquant.pipeline.forecast import forecast_7day
    from pvquant.services.calib_service import _plant_spec
    fr = forecast_7day(meteo, _plant_spec(plant))
    h = fr.hourly.rename(columns={"p_ac_kw": "p50_kw"})
    h.index = pd.DatetimeIndex(h.index).tz_localize("UTC") if pd.DatetimeIndex(h.index).tz is None else pd.DatetimeIndex(h.index).tz_convert("UTC")
    return h[["p50_kw"]].dropna()


def kosulari_yaz(plant: dict, h: pd.DataFrame, yil: int) -> int:
    """Her yerel gün D için D-1 03:00 UTC sanal yayın; D ve D+1 saatleri (48 s). Arşiv tabloları uygulama rolünde silinemez (doğru kısıt):
    bu yıl için simülasyon koşusu zaten varsa yeniden yazılmaz, mevcutlar kullanılır (yeniden üretim aynı girdiyle aynı sonucu verir)."""
    from pvquant.db import tenant_baglami
    tz = plant.get("tz") or "Europe/Istanbul"
    from pvquant.surum import yazilim_surumu
    n = 0
    with tenant_baglami(plant["tenant_id"]) as s:
        var = s.execute(text("SELECT count(*) FROM forecast_runs WHERE plant_id=CAST(:p AS uuid) AND model='backtest' AND run_at >= :a AND run_at < :b"),
                        {"p": plant["id"], "a": datetime(yil - 1, 12, 30, tzinfo=timezone.utc), "b": datetime(yil + 1, 1, 1, tzinfo=timezone.utc)}).scalar()
        if var:
            print(f"bu yıl için {var} simülasyon koşusu zaten var; yeniden yazılmadı (silme yetkisi bilerek yok)"); return int(var)
        for gun in pd.date_range(f"{yil}-01-01", f"{yil}-12-31", freq="D"):
            d0 = pd.Timestamp(gun, tz=tz).tz_convert("UTC"); d1 = d0 + pd.Timedelta(hours=UFUK_SAAT)
            ra = (d0 - pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=3)
            win = h[(h.index >= d0) & (h.index < d1)]
            if len(win) < 24:
                continue
            rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json, ufuk_saat, kapasite_kwp, yazilim_surumu, etiket) "
                                 "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), :ra, 'A', 'backtest', 'open-meteo-arsiv', CAST(:oz AS jsonb), :u, :k, :ys, NULL) RETURNING id"),
                            {"t": plant["tenant_id"], "p": plant["id"], "ra": ra.to_pydatetime(), "u": int(len(win)), "k": float(plant["capacity_kwp"]), "ys": yazilim_surumu(),
                             "oz": json.dumps({"kaynak": "open-meteo-arsiv", "nwp_model": "ERA5 analiz", "simulasyon": True, "not": "Faz 1 F1-F2 geriye dönük simülasyon; sanal yayın D-1 03:00 UTC"})}).scalar()
            s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, physics_kw) VALUES(:t, :r, :p, :ts, :v, :v)"),
                      [{"t": plant["tenant_id"], "r": rid, "p": plant["id"], "ts": ts.to_pydatetime(), "v": float(v)} for ts, v in win["p50_kw"].items()])
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--kanit", required=True); ap.add_argument("--yil", type=int, default=2025); a = ap.parse_args()
    _guvenlik(); kanit = Path(a.kanit); kanit.mkdir(parents=True, exist_ok=True)
    from pvquant.services import bagimsiz_dogrulama_service as bd, sablon_rapor_service as srs
    plant = santral_bul(); print("santral:", plant["name"], plant["capacity_kwp"], "kWp", plant["lat"], plant["lon"])
    meteo = meteo_cek(plant, a.yil, kanit); print("meteo saat:", len(meteo.ghi))
    h = fizik_kos(plant, meteo); print("fizik saat:", len(h), "toplam MWh:", round(h["p50_kw"].sum() / 1000, 1))
    n = kosulari_yaz(plant, h, a.yil); print("yazılan sanal koşu:", n)
    sonuclar = {}
    for kural in ("gun_oncesi", "ufuk"):
        s = bd.hesapla(plant["tenant_id"], plant, gun=365, kural=kural, bugun=date(a.yil + 1, 1, 1), simulasyon=True)
        sonuclar[kural] = s
        (kanit / f"F1-F2_sonuc_{kural}.json").write_text(json.dumps(s, default=str, ensure_ascii=False, indent=1), encoding="utf-8")
        m = s["metrik"]; print(f"{kural}: n={m['n_saat']} gün={m['n_gun']} WMAPE={m['wmape']} nMBE={m['nmbe']} MAE={m['mae_kw']} kapsama={s['butunluk']['olcum']['kapsama_pct']}")
        print("   referans:", {k: (v.get("wmape"), v.get("beceri_pct"), v.get("sonuc")) for k, v in s["referans"].items()})
        print("   aylar:", [(x["kesit"], x["wmape"]) for x in s["kesit"].get("ay", [])])
    r = srs.bagimsiz_dogrulama(plant["tenant_id"], plant, sonuc=sonuclar["gun_oncesi"], simulasyon=True)
    (kanit / "F1-F2_Solentegre_2025_simulasyon_raporu.html").write_text(srs.html_sar(r), encoding="utf-8")
    (kanit / "F1-F2_Solentegre_2025_simulasyon_raporu.md").write_text(r.markdown(), encoding="utf-8")
    try:
        bd.kaydet(plant["tenant_id"], sonuclar["gun_oncesi"], plant["id"])
        print("HATA: simülasyon kaydedildi!"); return 2
    except ValueError as e:
        print("kaydet reddetti (doğru):", e)
    print("kanıt:", kanit); return 0


if __name__ == "__main__":
    raise SystemExit(main())
