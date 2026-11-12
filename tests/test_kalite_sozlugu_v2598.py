"""v2.598 (Faz 4 F4-C, Stage 4) — veri kalitesi sözlüğü: tek Nitelik kümesi, flag/tamlık/sayaç/uygunluk eşlemeleri, amaç başına SQL
süzgeci (eski literal'lerle denklik), kodda ham `flag='valid'` kalmadı (AST bekçi), göç kümesi = sözlük, rapor çizelgesi tam,
validate: boş saat `eksik` / gündüz sıfır `sifir_gunduz`, DST satırı düşmez (M4), ingest kaynak önceliği (DB), flag CHECK (DB),
jobs_log.sonuc_json (DB), API sözlük ucu."""
from __future__ import annotations

import ast
import importlib.util
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami, tenant_baglami
from pvquant.io.ingestion import RowFlag
from pvquant.io.ingestion import transform as tr
from pvquant.io.ingestion import validate as vd
from pvquant.services import kalite_sozlugu as ks

KOK = Path(__file__).resolve().parents[1]


# ───────────────────────────────────────────── saf ─────────────────────────────────────────────
def test_nitelik_kumesi_ve_etiketler():
    assert {n.value for n in ks.Nitelik} == {"dogrulanmis", "olculmus", "kismi", "tahmini", "doldurulmus", "elle", "supheli", "gecikmis", "eksik", "gecersiz"}
    assert set(ks.ETIKET) == set(ks.Nitelik)
    for n in ks.Nitelik:   # müşteri yüzü: iç ad sızmaz
        assert "_" not in ks.ETIKET[n][0] and "flag" not in ks.ETIKET[n][1].lower()


def test_flag_sozlugu_rowflag_ve_yazicilari_kapsar():
    for f in RowFlag:
        assert f.value in ks.FLAG_NITELIK, f.value
    for f in ("kisinti", "anomali"):   # hijyen ve EPİAŞ yazıcıları
        assert f in ks.FLAG_NITELIK
    assert ks.flag_nitelik("valid") is ks.Nitelik.OLCULMUS and ks.flag_nitelik("eksik") is ks.Nitelik.EKSIK
    assert ks.flag_nitelik("sifir_gunduz") is ks.Nitelik.SUPHELI and ks.flag_nitelik("bogus") is ks.Nitelik.GECERSIZ and ks.flag_nitelik(None) is ks.Nitelik.EKSIK


def test_sql_kosulu_eski_literallerle_birebir_ve_gecerli_mi():
    assert ks.sql_kosulu("karne") == "flag IN ('valid')" and ks.sql_kosulu("karne", "s") == "s.flag IN ('valid')"
    assert ks.sql_kosulu("kayip", "sh") == "sh.flag IN ('valid', 'kisinti')"
    for a in ("karne", "kalibrasyon", "uzlastirma", "rapor", "tazelik"):
        assert ks.gecerli_flaglar(a) == ("valid",)
    for a in ("kayip", "kullanilabilirlik", "hijyen"):
        assert ks.gecerli_flaglar(a) == ("valid", "kisinti")
    assert ks.gecerli_mi("valid", "karne") and not ks.gecerli_mi("kisinti", "karne") and ks.gecerli_mi("kisinti", "kayip")
    assert not ks.gecerli_mi("partial_hour", "kayip") and ks.gecerli_mi(ks.Nitelik.OLCULMUS, "rapor") and not ks.gecerli_mi(ks.Nitelik.SUPHELI, "rapor")
    with pytest.raises(KeyError):
        ks.sql_kosulu("bilinmeyen")
    m = ks.pandas_maskesi(pd.Series(["valid", "kisinti", "eksik"]), "kayip")
    assert m.tolist() == [True, True, False]


def test_diger_sozluk_eslemeleri_ve_tazelik():
    assert ks.tamlik_nitelik("measured_complete") is ks.Nitelik.OLCULMUS and ks.tamlik_nitelik("measured_partial") is ks.Nitelik.KISMI and ks.tamlik_nitelik(None) is ks.Nitelik.EKSIK
    from pvquant.services import sayac_service
    for n in sayac_service.NITELIKLER:
        assert n in ks.SAYAC_NITELIK
    assert ks.sayac_nitelik("yok") is ks.Nitelik.EKSIK and ks.sayac_nitelik("elle") is ks.Nitelik.ELLE
    assert ks.uygunluk_nitelik("olculdu") is ks.Nitelik.OLCULMUS and ks.uygunluk_nitelik("kismi_saat") is ks.Nitelik.KISMI
    assert ks.uygunluk_nitelik("bayrak:frozen_value") is ks.Nitelik.SUPHELI and ks.uygunluk_nitelik("sayac:tahmini") is ks.Nitelik.TAHMINI
    assert ks.uygunluk_nitelik("olay:kisit") is ks.Nitelik.SUPHELI and ks.uygunluk_nitelik(None) is ks.Nitelik.EKSIK
    simdi = pd.Timestamp("2026-11-12 00:00", tz="UTC")
    assert ks.tazelik_durumu(None)["kod"] == "eksik"
    assert ks.tazelik_durumu("2026-11-11T10:00Z", simdi) == {"kod": "taze", "nitelik": "olculmus", "etiket": "veri güncel", "yas_saat": 14.0}
    g = ks.tazelik_durumu("2026-11-09T00:00Z", simdi)
    assert g["kod"] == "gecikmis" and g["yas_saat"] == 72.0 and "3 gün" in g["etiket"]
    sz = ks.sozluk()
    assert sz["surum"] == ks.SOZLUK_SURUMU and len(sz["nitelikler"]) == 10 and sz["amaclar"]["kayip"] == ["valid", "kisinti"] and sz["bayraklar"]["frozen"]["eski"] is True


def test_goc_flag_kumesi_sozlukle_ayni_ve_rapor_cizelgesi_tam():
    spec = importlib.util.spec_from_file_location("goc_v2598", KOK / "alembic" / "versions" / "v2598_kalite.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert tuple(m.FLAGLAR) == ks.FLAGLAR
    from pvquant.services.report_html_service import BAYRAK_AKSIYON
    eksik = [f for f in ks.FLAGLAR if f != "valid" and f not in BAYRAK_AKSIYON]
    assert not eksik, f"rapor çizelgesinde karşılığı olmayan bayrak: {eksik}"
    assert BAYRAK_AKSIYON["frozen_value"] == BAYRAK_AKSIYON["frozen"]


def _docstring_satirlari(agac: ast.AST) -> set[int]:
    out = set()
    for d in ast.walk(agac):
        if isinstance(d, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and d.body:
            ilk = d.body[0]
            if isinstance(ilk, ast.Expr) and isinstance(getattr(ilk, "value", None), ast.Constant) and isinstance(ilk.value.value, str):
                out.update(range(ilk.lineno, (ilk.end_lineno or ilk.lineno) + 1))
    return out


def test_kodda_ham_flag_valid_literali_kalmadi():
    """Bekçi: süzgeç yalnız kalite_sozlugu.sql_kosulu'ndan gelir. Docstring/yorumdaki anlatım serbest; kalite_sozlugu'nun kendisi muaf."""
    desen = re.compile(r"flag\s*(=\s*'valid'|IN\s*\(\s*'valid'\s*,\s*'kisinti'\s*\))")
    ihlal = []
    dosyalar = sorted((KOK / "src" / "pvquant" / "services").glob("*.py")) + [KOK / "apps" / "api" / "main.py", KOK / "apps" / "worker" / "main.py"]
    for d in dosyalar:
        if d.name == "kalite_sozlugu.py":
            continue
        metin = d.read_text(encoding="utf-8")
        doc = _docstring_satirlari(ast.parse(metin))
        for i, l in enumerate(metin.split("\n"), 1):
            if desen.search(l) and i not in doc and not l.strip().startswith("#") and "EXCLUDED.flag" not in l:   # yazım yolu (UPSERT karşılaştırması) süzgeç değil
                ihlal.append(f"{d.relative_to(KOK)}:{i}")
    assert not ihlal, "sözlük dışı flag süzgeci:\n" + "\n".join(ihlal)


def _izgara(bas="2026-06-21", n=24):
    return pd.date_range(bas, periods=n, freq="h", tz="UTC")


def test_validate_bos_saat_eksik_okunamayan_unparseable_ve_gunduz_sifir():
    ix = _izgara()
    df = pd.DataFrame({"power_kw": np.where((ix.hour >= 5) & (ix.hour <= 16), 400.0, 0.0), "poa_global": np.where((ix.hour >= 5) & (ix.hour <= 16), 700.0, 0.0),
                       "n_kaynak_satir": 4}, index=ix)
    df.loc[ix[8], "power_kw"] = np.nan; df.loc[ix[8], "n_kaynak_satir"] = 0          # boş saat
    df.loc[ix[9], "power_kw"] = np.nan                                                  # satır var, okunamadı
    df.loc[ix[10], "power_kw"] = 0.0                                                    # gündüz, ışınım var, güç 0
    out, rapor = vd.validate(df, capacity_kwp=1000.0, latitude=37.9, longitude=32.5)
    assert out.loc[ix[8], "flag"] == RowFlag.EKSIK.value and out.loc[ix[9], "flag"] == RowFlag.UNPARSEABLE.value
    assert out.loc[ix[10], "flag"] == RowFlag.SIFIR_GUNDUZ.value and "n_kaynak_satir" not in out.columns
    assert (out.loc[ix[[0, 1, 2]], "flag"] == RowFlag.VALID.value).all()   # gece sıfır: ışınım yok → şüpheli değil
    assert any("sıfır" in u for u in rapor.warnings) and rapor.flag_counts.get("eksik") == 1
    # ışınım kolonu yoksa sıfır kuralı koşmaz; ızgara sütunu yoksa eski davranış (NaN = okunamayan)
    out2, _ = vd.validate(pd.DataFrame({"power_kw": [np.nan, 0.0]}, index=ix[:2]), capacity_kwp=1000.0, latitude=37.9, longitude=32.5)
    assert out2["flag"].tolist() == [RowFlag.UNPARSEABLE.value, RowFlag.VALID.value]


def test_dst_satiri_dusmez_bayraklanir_m4():
    ham = pd.Series(["2026-03-29 01:30", "2026-03-29 02:30", "2026-03-29 03:30", "2026-10-25 02:30", "2026-10-25 02:30", "2026-10-25 03:30"])
    idx, bayrak = tr.parse_timestamps(ham, "Europe/Berlin")
    assert len(idx) == 6 and idx.notna().sum() == 5 and pd.isna(idx[1])   # yalnız yok saat (02:30 ileri alma) NaT: tek UTC karşılığı yok, rapora sayılır
    assert bayrak.tolist() == [False, True, False, True, True, False]  # yok saat + çift saat bayraklı
    assert idx[3] < idx[4] and idx[4] < idx[5]                         # çift 02:30 sırayla çözüldü, ikisi de kaldı
    idx_u, b_u = tr.parse_timestamps(pd.Series(["2026-03-29 02:30"]), "UTC")
    assert not b_u.any() and idx_u[0] == pd.Timestamp("2026-03-29 02:30", tz="UTC")
    # tam zincir: Türkiye DST'siz; Berlin'de 4 günlük saatlik seri geçişte de 96 satır verir, DST saatleri bayraklı
    saatler = pd.date_range("2026-03-28 00:00", "2026-03-31 23:00", freq="h", tz="Europe/Berlin")
    df = pd.DataFrame({"zaman": saatler.tz_localize(None).strftime("%Y-%m-%d %H:%M"), "guc": 100.0})
    utc, fl = tr.parse_timestamps(df["zaman"], "Europe/Berlin")
    assert len(utc) == len(df) and fl.sum() == 0   # tz-aware aralıktan türetilen yerel saatlerde yok saat bulunmaz


# ───────────────────────────────────────────── DB ──────────────────────────────────────────────
@pytest.fixture()
def santral():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'kalite-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Kalite GES', 1000, 900, 37.9, 32.5, 'Europe/Istanbul', '{}')"), {"p": pid, "t": tid})
    yield tid, {"id": pid, "tenant_id": tid, "name": "Kalite GES", "capacity_kwp": 1000.0, "ac_limit_kw": 900.0, "lat": 37.9, "lon": 32.5, "tz": "Europe/Istanbul", "params_json": {}}
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM jobs_log WHERE plant_id=:p OR job='kalite_test_isi'"), {"p": pid})
        for t in ("scada_hourly", "ingestion_batches"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid}); s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_db_flag_check_ve_kunye_sutunlari(santral):
    tid, plant = santral
    with tenant_baglami(tid) as s:
        s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag, kaynak, kaynak_damga_tipi) VALUES(:t, :p, '2026-06-21 10:00+00', 100, 'sifir_gunduz', 'epias', 'aralik_basi')"),
                  {"t": tid, "p": plant["id"]})
    for sql in ("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag) VALUES(:t, :p, '2026-06-21 11:00+00', 100, 'bogus')",
                "INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, kaynak) VALUES(:t, :p, '2026-06-21 12:00+00', 100, 'dosya')",
                "INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, kaynak_damga_tipi) VALUES(:t, :p, '2026-06-21 13:00+00', 100, 'orta')"):
        with pytest.raises(Exception, match="check"), tenant_baglami(tid) as s:
            s.execute(text(sql), {"t": tid, "p": plant["id"]})
    with sistem_baglami() as s:
        assert s.execute(text("SELECT convalidated FROM pg_constraint WHERE conname='scada_hourly_flag_check'")).scalar() is True


def test_db_ingest_kaynak_onceligi_kisinti_korunur(santral):
    from pvquant.services import ingest_service as ing
    tid, plant = santral
    ix = pd.date_range("2026-06-21 06:00", periods=4, freq="h", tz="UTC")
    with tenant_baglami(tid) as s:   # hijyen 07:00'ı kısıntı işaretlemiş, 08:00 EPİAŞ'tan gelmiş
        s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag, kirpma, kaynak) VALUES(:t, :p, :ts, 50, 'kisinti', true, 'scada_dosya')"), {"t": tid, "p": plant["id"], "ts": ix[1]})
        s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, flag, kaynak) VALUES(:t, :p, :ts, 60, 'valid', 'epias')"), {"t": tid, "p": plant["id"], "ts": ix[2]})
    veri = pd.DataFrame({"timestamp": ix, "power_kw": [300.0, 310.0, 320.0, 330.0], "flag": ["valid", "valid", "valid", "frozen_value"]})
    res = SimpleNamespace(data=veri, file_format=None, mapping=None, transform=SimpleNamespace(source_timestep_minutes=15, to_dict=lambda: {"source_timestep_minutes": 15}), report=None)
    out = ing.yukle_ve_kaydet(tid, plant["id"], "test.csv", capacity_kwp=1000.0, latitude=37.9, longitude=32.5, source_timezone="UTC", hazir_sonuc=res)
    assert out["n_satir"] == 4
    with tenant_baglami(tid) as s:
        rows = {r.ts_utc.hour: r for r in s.execute(text("SELECT ts_utc, power_kw, flag, kirpma, kaynak, aralik_dk, alinma_zamani FROM scada_hourly WHERE plant_id=:p ORDER BY ts_utc"), {"p": plant["id"]})}
    assert rows[6].flag == "valid" and rows[6].kaynak == "scada_dosya" and rows[6].aralik_dk == 15 and rows[6].alinma_zamani is not None
    assert rows[7].flag == "kisinti" and rows[7].power_kw == 310.0                      # değer SCADA dosyasından, kısıntı bayrağı korunur
    assert rows[8].flag == "valid" and rows[8].power_kw == 320.0 and rows[8].kaynak == "scada_dosya"   # EPİAŞ satırının üstüne SCADA yazdı
    assert rows[9].flag == "frozen_value"


def test_db_jobs_log_sonuc_json_ve_veri_yolu(santral, monkeypatch):
    import apps.worker.main as w
    from pvquant.services import veri_yolu_service as vy
    tid, plant = santral
    monkeypatch.setattr(w, "_tum_santraller", lambda: [plant])
    w._logla("kalite_test_isi", lambda p: {"durum": "ok", "n_yazilan": 7, "n_cekilen": 24})()
    w._logla("kalite_test_isi", lambda p: "metin sonuç")()
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT status, detail, sonuc_json FROM jobs_log WHERE job='kalite_test_isi' AND plant_id=:p ORDER BY started"), {"p": plant["id"]}).fetchall()
    assert len(rows) == 2 and rows[0].sonuc_json == {"durum": "ok", "n_yazilan": 7, "n_cekilen": 24} and rows[1].sonuc_json is None and rows[1].detail == "metin sonuç"
    assert vy.epias_cekis_durumu("ok", rows[0].detail, rows[0].sonuc_json)["kod"] == "ok"
    assert vy.epias_cekis_durumu("ok", "{'durum': 'ok', 'n_yazilan': 0}") == {"kod": "yazilmadi", "etiket": "çekiş başarılı, yeni saat yazılmadı (SCADA verisi öncelikli)"}
    assert vy.epias_cekis_durumu("ok", None, {"durum": "veri_yok", "n_yazilan": 0})["kod"] == "kayit_yok"


def test_api_sozluk_kalite():
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()), "role": "viewer", "exp": 0}
    try:
        r = TestClient(api_main.app).get("/v1/sozluk/kalite")
        assert r.status_code == 200 and r.json()["surum"] == ks.SOZLUK_SURUMU and r.json()["bayraklar"]["valid"]["nitelik"] == "olculmus"
        assert {n["kod"] for n in r.json()["nitelikler"]} == {n.value for n in ks.Nitelik}
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)
