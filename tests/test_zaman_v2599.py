"""v2.599 (Faz 4 F4-D, Stage 5) — zaman sözleşmesi: tek PIYASA_TZ (bekçi), gün/kesim yardımcıları, dönem çözümleyici devri, hour-ending
1–24 dosyası, «24:00» damgası, aralık sonu damgalı 15 dk dosya (enerji korunur), Europe/Berlin DST satırları düşmez, 15 dk dağıtımda
eksik saat NaN + yöntem etiketi."""
from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pvquant import zaman as z
from pvquant.ext.platform import finans as fn
from pvquant.ext.tahmin import alt_saatlik as alt
from pvquant.io.ingestion import RowFlag
from pvquant.io.ingestion import transform as tr
from pvquant.io.ingestion.pipeline import ingest_file
from pvquant.services import aylik_rapor_service as ar
from pvquant.services import karne_kurali as kk

KOK = Path(__file__).resolve().parents[1]


def _docstring_satirlari(agac):
    out = set()
    for d in ast.walk(agac):
        if isinstance(d, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and d.body:
            ilk = d.body[0]
            if isinstance(ilk, ast.Expr) and isinstance(getattr(ilk, "value", None), ast.Constant) and isinstance(ilk.value.value, str):
                out.update(range(ilk.lineno, (ilk.end_lineno or ilk.lineno) + 1))
    return out


def test_piyasa_tz_tek_tanim_bekcisi():
    """Kodda (docstring/yorum dışı) çift tırnaklı "Europe/Istanbul" yalnız zaman.py'de; ölü api/routes ve ingestion örneği muaf."""
    desen = re.compile(r'"Europe/Istanbul"')
    ihlal = []
    for d in sorted(list((KOK / "src" / "pvquant").rglob("*.py")) + list((KOK / "apps").rglob("*.py"))):
        g = d.relative_to(KOK).as_posix()
        if g.endswith("pvquant/zaman.py") or "/api/routes/" in g or "__pycache__" in g:
            continue
        metin = d.read_text(encoding="utf-8"); doc = _docstring_satirlari(ast.parse(metin))
        for i, l in enumerate(metin.split("\n"), 1):
            if desen.search(l.split("#")[0]) and i not in doc and not l.strip().startswith((">>>", "...")):
                ihlal.append(f"{g}:{i}")
    assert not ihlal, "PIYASA_TZ dışında saat dilimi literal'i:\n" + "\n".join(ihlal)
    assert kk.PIYASA_TZ is z.PIYASA_TZ and fn.IST_AD == z.PIYASA_TZ and ar.IST_AD == z.PIYASA_TZ


def test_gun_kesim_ve_donem_yardimcilari():
    assert z.gun_basi_utc("2026-06-10") == pd.Timestamp("2026-06-09 21:00", tz="UTC") and z.gun_sonu_utc(date(2026, 6, 10)) == pd.Timestamp("2026-06-10 21:00", tz="UTC")
    assert z.gun_basi_utc("2026-03-29", "Europe/Berlin") == pd.Timestamp("2026-03-28 23:00", tz="UTC")
    assert (z.gun_sonu_utc("2026-03-29", "Europe/Berlin") - z.gun_basi_utc("2026-03-29", "Europe/Berlin")) == pd.Timedelta(hours=23)   # 23 saatlik gün
    assert z.piyasa_gunu("2026-06-09T21:30Z") == date(2026, 6, 10) and z.santral_gunu("2026-06-09T21:30Z", "UTC") == date(2026, 6, 9)
    assert z.program_kesimi("2026-06-10") == pd.Timestamp("2026-06-09 15:30", tz="Europe/Istanbul") and z.program_kesimi(date(2024, 12, 31)) == pd.Timestamp("2024-12-30 16:00", tz="Europe/Istanbul")
    assert kk.program_kesimi(date(2026, 6, 10)) == z.program_kesimi("2026-06-10")
    assert z.santral_tz({"tz": "Europe/Berlin"}) == "Europe/Berlin" and z.santral_tz({}) == z.PIYASA_TZ and z.utc("2026-01-01 10:00") == pd.Timestamp("2026-01-01 10:00", tz="UTC")
    d = z.donem_cozumle("2026-10", date(2026, 11, 12)); assert d["tur"] == "ay" and d["saat"] == 744 and d == fn.donem_cozumle("2026-10", date(2026, 11, 12))
    assert ar.donem_cozumle("2026-Q3", date(2026, 11, 12)) == fn.donem_cozumle("2026-Q3", date(2026, 11, 12))
    with pytest.raises(ValueError, match="YYYY-MM"):
        ar.donem_cozumle("2026-10-05", date(2026, 11, 12))            # rapor gün kodu kabul etmez
    with pytest.raises(ValueError, match="rapor üretilmez"):
        ar.donem_cozumle("2027-01", date(2026, 11, 12))
    assert fn.donem_cozumle("2026-10-05", date(2026, 11, 12))["tur"] == "gun"
    with pytest.raises(ValueError):
        z.saat_damgasi_araliga(pd.DatetimeIndex([]), "yok", 60)


def _csv(yol: Path, satirlar: list[str]) -> Path:
    yol.write_text("\n".join(satirlar), encoding="utf-8"); return yol


def test_hour_ending_1_24_dosyasi_aralik_basina_cevrilir(tmp_path):
    satirlar = ["date,hour,production"] + [f"2023-06-{g:02d},{h},{5.0 + h * 0.1}" for g in (1, 2) for h in range(1, 25)]
    r = ingest_file(_csv(tmp_path / "he.csv", satirlar), capacity_kwp=35000.0, latitude=36.8, longitude=34.6, source_timezone="Europe/Istanbul")
    d = r.data.reset_index()
    assert len(d) == 48 and d["timestamp"].dt.tz_convert("Europe/Istanbul").dt.hour.tolist()[:24] == list(range(24))
    assert d["timestamp"].min() == pd.Timestamp("2023-06-01 00:00", tz="Europe/Istanbul")       # saat 1 → 00:00–01:00 aralığı
    assert d["timestamp"].max() == pd.Timestamp("2023-06-02 23:00", tz="Europe/Istanbul")       # saat 24 → 23:00–24:00, ertesi güne taşmaz
    assert r.transform.kaynak_damga_tipi == "aralik_sonu" and r.transform.damga_duzeltme == "saat-1"
    # 0–23 dosyası eskisi gibi aralık başı
    r2 = ingest_file(_csv(tmp_path / "hb.csv", ["date,hour,production"] + [f"2023-06-01,{h},{5.0}" for h in range(24)]), capacity_kwp=35000.0, latitude=36.8, longitude=34.6, source_timezone="Europe/Istanbul")
    assert r2.transform.kaynak_damga_tipi == "aralik_basi" and r2.transform.damga_duzeltme is None
    # v2.607 (mühür sonrası inceleme): hour-ending dosya + 'aralik_sonu' seçimi TEK kaydırma (çift düzeltme yok)
    r3 = ingest_file(_csv(tmp_path / "he2.csv", satirlar), capacity_kwp=35000.0, latitude=36.8, longitude=34.6, source_timezone="Europe/Istanbul", damga_tipi="aralik_sonu")
    d3 = r3.data.reset_index()
    assert d3["timestamp"].min() == pd.Timestamp("2023-06-01 00:00", tz="Europe/Istanbul") and d3["timestamp"].max() == pd.Timestamp("2023-06-02 23:00", tz="Europe/Istanbul")
    # v2.607: 1–23 (24 satırı yok) belirsiz — kaydırılmaz, raporda uyarı
    r4 = ingest_file(_csv(tmp_path / "he3.csv", ["date,hour,production"] + [f"2023-06-01,{h},{5.0}" for h in range(1, 24)]), capacity_kwp=35000.0, latitude=36.8, longitude=34.6, source_timezone="Europe/Istanbul")
    assert r4.transform.damga_duzeltme is None and any("saat tabanı belirsiz" in w for w in r4.report.warnings)


def test_24_00_damgasi_ertesi_gun_00_00():
    s = pd.Series(["2026-10-01 23:00", "2026-10-01 24:00", "01.10.2026 24:00:00", "2026-10-02 01:00"])
    out = tr._yirmi_dort_sifirla(s)
    assert out.tolist() == ["2026-10-01 23:00", "2026-10-02 00:00", "2026-10-02 00:00", "2026-10-02 01:00"]
    idx, _ = tr.parse_timestamps(s, "Europe/Istanbul")
    assert idx[1] == pd.Timestamp("2026-10-02 00:00", tz="Europe/Istanbul") and idx.notna().all()
    from pvquant.services import sayac_service as ss
    assert ss._zaman("01.10.2026", "24:00") == idx[2].to_pydatetime()   # sayaç kuralıyla aynı an


def test_aralik_sonu_damgali_15dk_dosya_enerji_korunur(tmp_path):
    # kaynak: 15 dk GÜÇ, damga aralık SONU (00:15 = 00:00–00:15 ortalaması); 2 gün; saatlik indirgemede güç ortalanır, enerji = ortalama × 1 sa
    ix = pd.date_range("2026-06-01 00:15", periods=2 * 96, freq="15min")
    guc = np.where((ix.hour >= 6) & (ix.hour < 18), (40.0 + 80.0 * np.sin(np.pi * (ix.hour + ix.minute / 60.0 - 6) / 12.0)).round(3), 0.0)
    satirlar = ["timestamp,power_kw"] + [f"{t:%Y-%m-%d %H:%M},{g}" for t, g in zip(ix, guc, strict=True)]
    yol = _csv(tmp_path / "son.csv", satirlar)
    r_son = ingest_file(yol, capacity_kwp=200.0, latitude=37.9, longitude=32.5, source_timezone="UTC", damga_tipi="aralik_sonu")
    r_bas = ingest_file(yol, capacity_kwp=200.0, latitude=37.9, longitude=32.5, source_timezone="UTC")
    assert r_son.transform.kaynak_damga_tipi == "aralik_sonu" and r_son.transform.damga_duzeltme == "adim_geri" and r_son.transform.source_timestep_minutes == 15
    ds, db = r_son.data, r_bas.data
    assert ds.index.min() == pd.Timestamp("2026-06-01 00:00", tz="UTC") and ds.index.max() == pd.Timestamp("2026-06-02 23:00", tz="UTC") and len(ds) == 48
    assert db.index.max() == pd.Timestamp("2026-06-03 00:00", tz="UTC") and len(db) == 49                 # aralık başı okunursa gece yarısına taşar
    # enerji korunur: saatlik ortalama × 1 sa = dört dilimin ortalaması; 06:00 saati ilk dört gündüz dilimini içerir
    beklenen_06 = float(guc[24:28].mean())
    assert abs(float(ds.loc[pd.Timestamp("2026-06-01 06:00", tz="UTC"), "power_kw"]) - beklenen_06) < 1e-6 and (ds["kapsama_dk"].dropna() == 60).all()
    assert abs(float(ds["power_kw"].sum()) - float(guc.reshape(-1, 4).mean(axis=1).sum())) < 1e-6
    assert abs(float(db.loc[pd.Timestamp("2026-06-01 06:00", tz="UTC"), "power_kw"]) - float(guc[23:27].mean())) < 1e-6   # kaydırılmadan okunursa 06:00 saati 06:00–06:45 damgalarını alır: bir dilim kayar
    assert abs(float(ds.loc[pd.Timestamp("2026-06-01 05:00", tz="UTC"), "power_kw"]) - float(guc[23]) / 4.0) < 1e-6              # aralık sonu: 06:00 damgası 05:45–06:00 dilimi → 05:00 saatine
    with pytest.raises(ValueError, match="damga_tipi"):
        ingest_file(yol, capacity_kwp=200.0, latitude=37.9, longitude=32.5, source_timezone="UTC", damga_tipi="orta")

def test_berlin_dst_gecisi_satirlar_dusmez_bayraklanir(tmp_path):
    gunler = pd.date_range("2026-03-28", "2026-03-31", freq="D")
    satirlar = ["timestamp,power_kw"] + [f"{g:%Y-%m-%d} {h:02d}:00,{100.0 if 7 <= h <= 17 else 0.0}" for g in gunler for h in range(24)]
    r = ingest_file(_csv(tmp_path / "berlin.csv", satirlar), capacity_kwp=500.0, latitude=52.5, longitude=13.4, source_timezone="Europe/Berlin")
    # ileri alma: 29.03 02:00 yerel saat yok — tek UTC karşılığı olmadığından seriye girmez; sessiz değil, karne uyarısı sayar
    assert r.report.n_rows_read == 95 and len(r.data) == 95 and r.transform.dst_yok_saat_satiri == 1
    assert any("var olmayan yerel saate" in u for u in r.report.warnings) and r.report.flag_counts.get("duplicate_time", 0) == 0
    satirlar2 = ["timestamp,power_kw"] + [f"2026-10-25 {h:02d}:00,{100.0 if 7 <= h <= 17 else 0.0}" for h in list(range(3)) + [2] + list(range(3, 24))]   # 02:00 iki kez (geri alma)
    r2 = ingest_file(_csv(tmp_path / "berlin2.csv", satirlar2), capacity_kwp=500.0, latitude=52.5, longitude=13.4, source_timezone="Europe/Berlin")
    assert len(r2.data) == 25 and r2.report.flag_counts.get(RowFlag.DST_AMBIGUOUS.value) == 2   # 25 saatlik gün; iki 02:00 sırayla ayrı UTC saatine, bayraklı
    assert r2.data.index.is_unique and r2.transform.dst_yok_saat_satiri == 0


def test_15dk_dagitim_eksik_saat_nan_ve_yontem_etiketi():
    ix = pd.date_range("2026-06-21 03:00", periods=18, freq="h", tz="UTC")
    s = pd.Series(np.clip(800 * np.sin(np.pi * (ix.hour - 3) / 13), 0, None), index=ix).drop(ix[8])
    q = alt.saatlikten_15dk(s, 37.9, 32.5)
    assert q.attrs["yontem"] == alt.YONTEM_ETIKETI and "tahmin değildir" in q.attrs["yontem"]
    assert int(q.isna().sum()) == 4 and q[q.index.floor("h") == ix[8]].isna().all()     # eksik saatin 4 dilimi NaN, 0 değil
    assert (q[q.index.floor("h") == ix[0]] == 0).all()                                   # gece sıfır (ölçüm var) 0 kalır
    sa = q.resample("h").mean().reindex(s.index)
    assert np.allclose(sa, s, rtol=1e-6, atol=1e-6)                                      # enerji korunur
    from pvquant.services import toplayici_service as ts
    gun = pd.date_range("2026-06-20 21:00", periods=24, freq="h", tz="UTC")   # 21.06 İstanbul günü
    tam = pd.Series(np.clip(800 * np.sin(np.pi * (gun.tz_convert("Europe/Istanbul").hour - 4) / 14), 0, None), index=gun).drop(gun[12])   # 09:00 saati eksik
    tbl = ts.tablo_uret(pd.DataFrame({"p50_kw": tam * 1000.0}), date(2026, 6, 21), "UEVCB-1", 900.0, 37.9, 32.5, adim=15)
    assert tbl.attrs.get("dagitim_yontemi") == alt.YONTEM_ETIKETI and int(tbl["P50_MW"].isna().sum()) == 4 and len(tbl) == 96   # eksik saatin 4 dilimi satır olarak kalır, değeri NaN
