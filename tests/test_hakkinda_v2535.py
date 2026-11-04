"""v2.535 — Hakkında doğrulama turu (04.11.2026): kural satırı doğrulama durumu, KÜPST geçersiz kılma işareti,
iş günlüğü tazeliği ve lisans doğrulama kayıtları. Uydurma veri yok: kayıt yoksa alanlar None."""
import json
import pathlib

import numpy as np
import pandas as pd
from pvquant.ext.kaynak import atif
from pvquant.ext.turkiye import dengesizlik as d
from pvquant.ext.turkiye import kurallar as kr
from pvquant.services import dengesizlik_service as ds
from pvquant.services import kaynak_service as ks
from pvquant.services import piyasa_service as ps

KOK = pathlib.Path(__file__).resolve().parents[1]


def test_dogrulama_durumu_metinden_turetilir():
    assert kr.dogrulama_durumu("DUY m.110 (RG 2.2.2020-31027)", "Karar 14029 (RG 29.12.2025-33122)")[0] == "dogrulandi"
    assert kr.dogrulama_durumu("DUY m.110", "Karar 14907 Md.7 «takip eden fatura dönemi» → 1.11.2026 çıkarım")[0] == "cikarim"
    durum, notu = kr.dogrulama_durumu("DUY m.110; k = l = 0,03 — karar taslağı (asıl karar no bulunamadı)", "Karar 9422 (RG 3.7.2020-31174)")
    assert durum == "dogrulama_gerekli" and notu.startswith("EDT:") and "bulunamadı" in notu
    assert kr.dogrulama_durumu("DUY m.110", None, belirsiz_2027=True)[0] == "belirsiz"


def test_kural_tablosu_her_satirda_durum():
    rows = kr.tablo()
    assert rows and all(r["dogrulama"] in kr.DOGRULAMA_DURUMLARI and r["dogrulama_notu"] for r in rows)
    for r in rows:
        if r["belirsiz_2027"]:
            assert r["dogrulama"] == "belirsiz"
        elif any(i in (r["edt_dayanak"] or "") + (r["kupst"]["dayanak"] or "") for i in ("bulunamadı", "doğrulanmadı", "taslağı")):
            assert r["dogrulama"] == "dogrulama_gerekli"      # 2023–2025 k/l dayanağı taslaktan: gizlenmez
    assert {r["dogrulama"] for r in rows} >= {"dogrulandi", "dogrulama_gerekli", "belirsiz"}


def test_sahte_kural_tablosu_motorla_es():
    """Tasarım kipi JSON'u motordan üretilir; elle satır eklenmez — sürüklenirse test düşer."""
    sahte = json.loads((KOK / ".claude/skills/pvquant-tasarim/betikler/sahte-kurallar.json").read_text())
    assert sahte["satirlar"] == kr.tablo()


def _df():
    ix = pd.date_range("2026-11-05 06:00", periods=6, freq="h", tz="UTC")
    return pd.DataFrame({"ts_utc": ix, "gercek_kw": 1000.0, "kgup_kw": 1200.0, "naif_kw": np.nan})


def test_kupst_gecersiz_kilma_isareti():
    f = ps.senaryo_fiyat(pd.DatetimeIndex(_df()["ts_utc"]))
    k0 = ds.hesapla_df(_df(), f, segment="lisansli_serbest")["katsayilar"]
    k1 = ds.hesapla_df(_df(), f, d.Katsayilar(kupst_n=0.02, kupst_tolerans=0.05), segment="lisansli_serbest")["katsayilar"]
    assert k0["kupst_gecersiz_kilma"] is False and k0["kupst_kaynak"] == "kural tablosu" and k0["kupst_n"] == 0.05 and k0["kupst_tolerans"] == 0.08
    assert k1["kupst_gecersiz_kilma"] is True and "santral ayarı" in k1["kupst_kaynak"] and k1["kupst_n"] == 0.02 and k1["kupst_tolerans"] == 0.05
    # k/l geçersiz kılınamaz: iki hesapta da kural tablosundan
    assert k0["k"] == k1["k"] == 0.03 and k0["k_yon"] == k1["k_yon"]


def test_lisans_dogrulama_kayitlari():
    assert set(atif.LISANS_DOGRULAMA) <= set(atif.KAYNAKLAR)
    for k, (tarih, notu) in atif.LISANS_DOGRULAMA.items():
        pd.Timestamp(tarih)   # ISO tarih
        assert notu and atif.KAYNAKLAR[k].lisans.split(" ")[0] in notu or k == "gfs"
    assert "ecmwf" in atif.LISANS_DOGRULAMA and "Terms of Use" in atif.LISANS_DOGRULAMA["ecmwf"][1]


def test_is_tazeligi_bos_gunlukte_none():
    """Test veritabanında jobs_log boş: hiçbir alan uydurulmaz (PVQ_DB_URL ile koşar)."""
    t = ks.is_tazeligi({"gece_meteo": "x"})
    assert set(t) == {"gece_meteo"} and set(t["gece_meteo"]) == {"ad", "son_basarili", "son_deneme", "son_durum", "son_ayrinti"}
    assert all(v is None for k, v in t["gece_meteo"].items() if k != "ad")   # kayıt yok → uydurulmaz
