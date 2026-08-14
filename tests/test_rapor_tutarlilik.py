# -*- coding: utf-8 -*-
"""v2.129 — Rapor tutarlılık denetimi regresyon testleri.

10 Ağustos 2026 tarihli gerçek koşuda müşteri raporuna basılan yedi
aritmetik-imkânsız değerin her biri için bir bozuk fikstür vardır
(tests/data/bozuk_*.json); ilgili kontrol her birini YAKALAMALIDIR.
Kanonik girdi (ornek_girdi_v21.json) tüm kontrollerden geçmelidir.

Ek olarak uret.py sözleşmesi sınanır: kanonikte çıkış 0 + 16 sayfa,
her bozuk fikstürde çıkış 1 + hiç sayfa yok + denetim.json'da ilgili kod.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
MOTOR = KOK / "reporting" / "html"
KANONIK = MOTOR / "ornek_girdi_v21.json"
VERI_DATA = Path(__file__).resolve().parent / "data"

sys.path.insert(0, str(MOTOR))
import denetim  # noqa: E402

# (fikstür, yakalaması gereken kontrol, bayrak beklentisi)
BOZUKLAR = [
    ("bozuk_1_selale_d2.json", "D2", False),
    ("bozuk_2_kalibrasyon_saat_d5.json", "D5", False),
    ("bozuk_3_arsiv_saat_d6.json", "D6", False),
    ("bozuk_4_bifacial_d7.json", "D7", True),
    ("bozuk_5_kf_mwe_d10.json", "D10", False),
    ("bozuk_6_ogle_cukuru_d8.json", "D8", False),
    ("bozuk_7_mwe_bos_d10.json", "D10", False),
]
_sayac = [0]


def taze_veri(json_yolu=None):
    """veri.py'yi verilen JSON'la TAZE bir modül olarak yükler.
    (veri, PVQ_VERI_JSON'u import anında okur; sys.modules önbelleğine
    takılmamak için her çağrıda ayrı modül adı kullanılır.)"""
    if json_yolu is None:
        os.environ.pop("PVQ_VERI_JSON", None)
    else:
        os.environ["PVQ_VERI_JSON"] = str(json_yolu)
    _sayac[0] += 1
    spec = importlib.util.spec_from_file_location(
        "veri_taze_%d" % _sayac[0], MOTOR / "veri.py")
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.pop("PVQ_VERI_JSON", None)
    return m


def uret_kos(json_yolu, cikti_dizin):
    env = dict(os.environ, PVQ_CIKTI=str(cikti_dizin))
    if json_yolu is None:
        env.pop("PVQ_VERI_JSON", None)
    else:
        env["PVQ_VERI_JSON"] = str(json_yolu)
    return subprocess.run(
        [sys.executable, "uret.py"], cwd=MOTOR, env=env,
        capture_output=True, text=True, timeout=600)


# ---------------------------------------------------------------- kanonik
def test_kanonik_tum_kontrollerden_gecer():
    kayitlar, bulgular, bayrak = denetim.denetle_tam(taze_veri(KANONIK))
    assert bulgular == [], "kanonik girdi bulgu üretmemeli: %r" % bulgular
    assert bayrak is False
    assert sorted({k["kod"] for k in kayitlar}) == [
        "D1", "D10", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
    assert all(k["durum"] == "gecti" for k in kayitlar)


def test_statik_yol_da_gecer():
    """JSON verilmeyen (statik) kanonik yol da temiz olmalı."""
    assert denetim.denetle(taze_veri(None)) == []


def test_kanonik_uret_cikis_0_ve_16_sayfa(tmp_path):
    p = uret_kos(KANONIK, tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    sayfalar = sorted(tmp_path.glob("*_s??_*.html"))
    assert len(sayfalar) == 16, [s.name for s in sayfalar]
    j = json.loads((tmp_path / "denetim.json").read_text(encoding="utf-8"))
    assert j["ozet"]["hata"] == 0 and j["ozet"]["gecti"] == 11
    assert j["bulgular"] == [] and j["suphe_bayragi"] is False


# ---------------------------------------------------------------- bozuklar
@pytest.mark.parametrize("dosya,kod,bayrak_bekle", BOZUKLAR,
                         ids=[b[0].replace("bozuk_", "").replace(".json", "")
                              for b in BOZUKLAR])
def test_bozuk_fikstur_yakalanir(dosya, kod, bayrak_bekle):
    kayitlar, bulgular, bayrak = denetim.denetle_tam(taze_veri(VERI_DATA / dosya))
    hatalar = {b.kod for b in bulgular if b.seviye == "hata"}
    assert kod in hatalar, "%s fikstürünü %s yakalamalıydı; hatalar: %r" % (
        dosya, kod, hatalar)
    assert bayrak is bayrak_bekle
    ilgili = [b for b in bulgular if b.kod == kod and b.seviye == "hata"]
    assert ilgili and ilgili[0].beklenen and ilgili[0].bulunan


@pytest.mark.parametrize("dosya,kod,_b", BOZUKLAR,
                         ids=[b[0].replace("bozuk_", "").replace(".json", "")
                              for b in BOZUKLAR])
def test_bozuk_fikstur_uret_cikis_1_sayfa_yok(dosya, kod, _b, tmp_path):
    p = uret_kos(VERI_DATA / dosya, tmp_path)
    assert p.returncode == 1, p.stdout + p.stderr
    assert kod in p.stdout, "stdout ilgili kontrol kodunu anmalı:\n" + p.stdout
    assert not list(tmp_path.glob("*.html")), "bozuk girdiyle hiç sayfa yazılmamalı"
    assert not list(tmp_path.glob("*.pdf"))
    j = json.loads((tmp_path / "denetim.json").read_text(encoding="utf-8"))
    assert kod in {b["kod"] for b in j["bulgular"] if b["seviye"] == "hata"}


def test_selale_fiksturu_gercek_kosu_degerlerini_tasir():
    """Görev şartı: şelale fikstürü fizik=38,7 · holdout=30,1, adımlar aynen."""
    J = json.loads((VERI_DATA / "bozuk_1_selale_d2.json").read_text(encoding="utf-8"))
    K = json.loads(KANONIK.read_text(encoding="utf-8"))
    assert J["calibration"]["physics_mape"] == 38.7
    assert J["calibration"]["holdout_mape"] == 30.1
    assert J["calibration"]["steps"] == K["calibration"]["steps"]


# ------------------------------------------------- tabloda fikstürü olmayan
# kontroller (D1 · D3 · D4 · D9) sözlük-yüzeyle sınanır: denetle() hem modül
# hem sözlük kabul eder.
def _yuzey():
    m = taze_veri(KANONIK)
    return {ad: getattr(m, ad) for ad in dir(m) if ad.isupper()}


def test_d1_gunluk_toplam_donemi_tutmali():
    d = _yuzey(); d["TOPLAM_P50_MWH"] = 1100.0
    assert "D1" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d3_bayat_olcek_yakalanir():
    """v2.131: ölçek Σbase'den türediği için sabit-bölen kusuru kurulumla
    yok edildi; kalan sınıf, taban değişmişken yüzeyde BAYAT ölçeğin
    sürülmesidir — D3 bunu yakalar."""
    d = _yuzey()
    d["BASE_KW"] = [v * 1.1 for v in d["BASE_KW"]]
    d["MATRIS_OLCEK_MWH"] = 65.8          # taban değişti, ölçek eski
    assert "D3" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d3_turetilen_olcekle_tutarli():
    """Aynı yüzeyde ölçek de yeniden türetilirse tutarlılık kurulur."""
    d = _yuzey()
    d["BASE_KW"] = [v * 1.1 for v in d["BASE_KW"]]
    d["MATRIS_OLCEK_MWH"] = sum(d["BASE_KW"]) / 1000.0
    assert "D3" not in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d4_karne_skill_ozdesligi():
    d = _yuzey(); d["KARNE_SK"] = [1.4] + list(d["KARNE_SK"][1:])
    assert "D4" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d9_ay_siniri_asan_donem_yakalanir():
    """v2.131: panel/hedef tarihleri veri-güdümlü; kalan kusur sınıfı,
    ay sınırını aşan dönemde etiketin '01'e dönüp ay adının ilk ayda
    kalmasıdır — D9 bunu yakalar."""
    d = _yuzey()
    d["GUN_ETIKET"] = ["%02d" % g for g in list(range(25, 32)) + list(range(1, 10))]
    d["AY_YIL"] = "Ağustos 2026"
    d["GUN_SAYISI"] = 16
    assert "D9" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d9_farkli_ayda_donem_artik_gecer():
    """v2.131 öncesi 'Ağustos' gömülüydü ve Eylül dönemi düşerdi; artık
    ay veriden basıldığı için aynı-ay-içi her dönem geçer."""
    d = _yuzey()
    d["AY_YIL"] = "Eylül 2026"
    assert "D9" not in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_hata_yoksa_bile_denetim_json_yazilir(tmp_path):
    kayitlar, _bulgular, bayrak = denetim.denetle_tam(taze_veri(KANONIK))
    yol = tmp_path / "denetim.json"
    denetim.json_yaz(kayitlar, bayrak, yol)
    j = json.loads(yol.read_text(encoding="utf-8"))
    assert {"zaman", "suphe_bayragi", "ozet", "gecenler", "bulgular"} <= set(j)
    assert len(j["gecenler"]) == 11
    assert all({"kod", "mesaj", "beklenen", "bulunan"} <= set(g) for g in j["gecenler"])
