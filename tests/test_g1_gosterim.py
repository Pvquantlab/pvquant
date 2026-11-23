"""Faz 1 G1 (22.11.2026) — gösterim dürüstlüğü: beceri formülü, kova açıklaması, ölçüm sınırı etiketi (EPİAŞ), atlanan iş statüsü,
santral türü (kamu_referans). Hesap/tahmin/finans formülleri DEĞİŞMEZ; yalnız etiket, sözlük ve statü. DB'siz, saf."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pvquant.services import durum_sozlugu as ds
from pvquant.services import karne_kurali as kk
from pvquant.services import olcum_uygunluk_service as ou


def test_kova_aciklamasi_tum_kovalari_kapsar_ve_secimi_degistirmez():
    assert set(kk.KOVA_ACIKLAMA) == set(kk.ANA_KOVALAR) | {kk.KOVA_PROGRAM, kk.KOVA_GUN_ICI}
    assert "05:00" in kk.KOVA_ACIKLAMA["0-24"]["ad"] and "8 saat" in kk.KOVA_ACIKLAMA["0-24"]["ufuk"]
    assert "15:30" in kk.KOVA_ACIKLAMA["program"]["ufuk"]
    assert "günlük" in kk.WMAPE_TANIM["karne"] and "havuz" in kk.WMAPE_TANIM["havuz"]
    assert kk.KOVA_SINIRLARI == [0, 24, 72, 168, 999] and kk.GUNDUZ_ORAN == 0.02   # seçim kuralı sabit


def test_sinir_sozlugu_epias_ve_veri_kaynagi_turetme():
    assert ou.SINIR["epias"][0] == "settlement_gross" and "SCADA değil" in ou.SINIR["epias"][1]
    ix = pd.date_range("2026-11-01", periods=3, freq="1h", tz="UTC", name="ts_utc")   # saat_izgarasi gibi adlı indeks
    epias = pd.DataFrame({"power_kw": [1.0, 2.0, 3.0], "kaynak": ["epias"] * 3}, index=ix)
    karisik = pd.DataFrame({"power_kw": [1.0, 2.0, 3.0], "kaynak": ["epias", None, "scada"]}, index=ix)
    eski = pd.DataFrame({"power_kw": [1.0, 2.0, 3.0]}, index=ix)
    assert ou.veri_kaynagi(epias) == "epias"
    assert ou.veri_kaynagi(karisik) == "scada"          # karışık → seçilen kaynak (etiket uydurulmaz)
    assert ou.veri_kaynagi(eski) == "scada"             # kaynak kolonu yok (eski satırlar)
    assert ou.veri_kaynagi(epias, "sayac") == "sayac"   # sayaç seçimi EPİAŞ'tan etkilenmez
    df = ou.siniflandir(ix, epias)
    d = ou.dokum(df, "scada", ou.veri_kaynagi(epias))
    assert d["sinir"] == "settlement_gross" and d["veri_kaynagi"] == "epias" and d["kaynak"] == "scada"
    assert ou.dokum(df, "scada")["sinir"] == "plant_gross_ac"   # geriye uyum: veri kaynağı verilmezse eski davranış


def test_atlanan_is_durumu_kurali():
    from apps.worker.main import _is_durumu
    assert _is_durumu({"durum": "atlandi", "neden": "piyasa şeffaflık kimliği tanımlı değil"}, "") == "atlandi"
    assert _is_durumu({"durum": "ok", "yazilan": 24}, "") == "ok"
    assert _is_durumu("kimlik_yok; yazılan 0", "kimlik_yok; yazılan 0") == "atlandi"
    assert _is_durumu("program: yetersiz veri (0 saat), atlandı; gun_oncesi: n=205 wmape=26.4", "") == "ok"   # kısmen hesaplandı → ok
    assert _is_durumi_ok("program: n=205 wmape=28.0; gun_oncesi: n=205 wmape=26.4")
    assert _is_durumu(None, "") == "ok" and _is_durumu("", "") == "ok"
    assert _is_durumu("kimlik_yok; yazılan 24", "") == "ok"            # QA İ-4: sayı yazılmış → veri üretmiş, atlanmış değil
    assert _is_durumu("3 santral atlandı, n=12 satır yazıldı", "") == "ok"


def _is_durumi_ok(metin: str) -> bool:
    from apps.worker.main import _is_durumu
    return _is_durumu(metin, metin) == "ok"


def test_alarm_durumu_atlanan_is_dikkat_ve_geriye_uyum():
    simdi = dt.datetime(2026, 11, 22, 12, tzinfo=dt.timezone.utc)
    eski = ds.alarm_durumu(0, 0, 0, None, simdi)   # eski imza aynen çalışır
    assert eski["durum"] == ds.Durum.SAGLIKLI.value and eski["son_is_atlanan"] is None
    atl = ds.alarm_durumu(0, 0, 0, None, simdi, son_is_atlanan=simdi - dt.timedelta(hours=5))
    assert atl["durum"] == ds.Durum.DIKKAT.value and "atlanan iş" in atl["neden"] and "başarısız" not in atl["neden"]
    hata = ds.alarm_durumu(0, 0, 0, simdi - dt.timedelta(hours=5), simdi)
    assert hata["durum"] == ds.Durum.DIKKAT.value and "başarısız iş" in hata["neden"]


def test_santral_turu_kamu_referans_rozet_ve_tazelik():
    assert "kamu_referans" in ds.SANTRAL_TURLERI and "müşteri santrali değil" in ds.SANTRAL_TURLERI["kamu_referans"]
    kr = ds.santral_sinifi({"santral_turu": "kamu_referans"})
    assert kr["rozet"] == "KAMU REFERANS" and kr["tazelik_izlenir"] is True
    st = ds.santral_sinifi({"santral_turu": "sanal_test"})
    assert st["rozet"] == "SANAL TEST" and st["tazelik_izlenir"] is False
    op = ds.santral_sinifi({})
    assert op["santral_turu"] == "operasyonel" and op["rozet"] is None and op["tazelik_izlenir"] is True
