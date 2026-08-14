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
    ("bozuk_8_naif_celisik_d4.json", "D4", False),
    ("bozuk_9_olculdu_sayili_d18.json", "D18", False),
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
        "D1", "D10", "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18",
        "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
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
    assert j["ozet"]["hata"] == 0 and j["ozet"]["gecti"] == 22
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


def test_d4_turetilmis_naif_totoloji_uyarisi():
    """v2.137: naif alandan gelmiyorsa ozdeslik denetimi anlamsizdir — uyari."""
    d = _yuzey(); d["KARNE_NAIF_KAYNAK"] = "turetilmis"
    b = denetim.denetle(d)
    assert "D4" not in {x.kod for x in b if x.seviye == "hata"}
    assert "D4" in {x.kod for x in b if x.seviye == "uyari"}


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
    assert len(j["gecenler"]) == 22
    assert all({"kod", "mesaj", "beklenen", "bulunan"} <= set(g) for g in j["gecenler"])


# ------------------------------------------------- v2.132 anlam testleri
def test_d2_adimsiz_girdi_engellemez_ama_selale_basilmaz(tmp_path):
    """B4 tersine çevrildi: steps yoksa rapor çıkar (uyarı), s09'da şelale
    yerine 'veri eksik' satırı vardır — görev reçetesinin kendisi."""
    J = json.loads(KANONIK.read_text(encoding="utf-8"))
    del J["calibration"]["steps"]
    yol = tmp_path / "adimsiz.json"
    yol.write_text(json.dumps(J, ensure_ascii=False), encoding="utf-8")
    kayitlar, bulgular, _b = denetim.denetle_tam(taze_veri(yol))
    assert "D2" not in {b.kod for b in bulgular if b.seviye == "hata"}
    d2u = [b for b in bulgular if b.kod == "D2" and b.seviye == "uyari"]
    assert d2u and "basılmaz" in d2u[0].mesaj  # dogru dal: 'selale basilmaz' 
    p = uret_kos(yol, tmp_path / "cikti")
    assert p.returncode == 0, p.stdout + p.stderr
    s09 = next((tmp_path / "cikti").glob("*_s09_*.html")).read_text(encoding="utf-8")
    assert "veri eksik (gerekli: kalibrasyon adımları)" in s09
    assert "Kalibrasyon iyilesme selalesi" not in s09


def test_d5_pencere_iddiasi_yoksa_uyari():
    """Pencere kartta iddia edilmiyorsa uydurma 120'ye karşı denetlenmez."""
    d = _yuzey(); d["KAL_PENCERE"] = ""; d["KAT_SAAT"] = "4.272"
    b = denetim.denetle(d)
    assert "D5" not in {x.kod for x in b if x.seviye == "hata"}
    assert "D5" in {x.kod for x in b if x.seviye == "uyari"}


def test_d6_bosluklu_durust_arsiv_gecer():
    """v2.132 üst-sınır: 468 günlük dönemde 9.419 saat (%84) meşrudur."""
    d = _yuzey()
    d["ARSIV_ETIKET"] = "30 Nisan 2025 – 10 Ağustos 2026\n    (9.419 saat)"
    assert "D6" not in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d6_kapasite_asimi_hala_duser():
    d = _yuzey()
    d["ARSIV_ETIKET"] = "1 Şubat – 4 Ağustos 2026\n    (4.600 saat)"
    assert "D6" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


# ------------------------------------------------- v2.135 Faz A testleri
def test_d11_bayat_lta_yakalanir():
    d = _yuzey(); d["LTA_AY"] = list(d["LTA_AY"]); d["LTA_AY"][5] += 50
    assert "D11" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d12_bayat_iyilesme_yakalanir():
    d = _yuzey(); d["IYILESME_PCT"] = 99.9
    assert "D12" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d13_tepe_dc_ustunde_duser():
    d = _yuzey(); d["BASE_KW"] = list(d["BASE_KW"]); d["BASE_KW"][7] = 13000  # > 12,4 MWp
    assert "D13" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d14_sicrama_yakalanir():
    d = _yuzey(); b = list(d["BASE_KW"]); b[6] = b[5] + 0.5 * max(b); d["BASE_KW"] = b
    assert "D14" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d14_kirpilmis_tepede_rampa_gecer():
    """v2.136 tanim duzeltmesi: AC-kirpmali santralde sicrama kirpilmis
    tepenin %30'unu asabilir ama DC'nin %30'u altindaysa fizikseldir
    (canli 3,6 MW AC / 4,5 MWp vakasi)."""
    d = _yuzey()
    d["SAHA"] = [("Kurulu güç", "4,5 MWp / 3,6 MWe")]
    tepe = 3560.0
    d["BASE_KW"] = [200, 700, 1500, 2613, 3200, 3480, tepe, tepe, 3400,
                    3000, 2400, 1700, 1000, 500, 180]   # azami adim 1113 = DC'nin %24,7'si
    assert "D14" not in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d15_ayrik_arsiv_duser():
    d = _yuzey()
    d["ARSIV_ETIKET"] = "1 Ocak – 28 Şubat 2024\n    (1.416 saat)"
    assert "D15" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d16_celisen_durum_duser():
    d = _yuzey(); d["DURUM_KAPSAMA"] = "ok"      # 71 < 80 iken 'ok' basilamaz
    assert "D16" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d16_kesintisiz_alansiz_basilamaz():
    d = _yuzey(); d["KESINTISIZ_GUN"] = None
    assert "D16" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_render_dolmamis_token_yakalanir(tmp_path):
    for i in range(1, 17):
        (tmp_path / ("x_s%02d_a.html" % i)).write_text("<html>ok</html>", encoding="utf-8")
    (tmp_path / "x_s07_a.html").write_text("<html>{{KAYIP}}</html>", encoding="utf-8")
    b = denetim.render_denetle(str(tmp_path))
    assert any(x.kod == "R1" for x in b)


def test_render_sayfa_referansi_araliginda(tmp_path):
    for i in range(1, 17):
        (tmp_path / ("x_s%02d_a.html" % i)).write_text("<html>ok</html>", encoding="utf-8")
    (tmp_path / "x_s15_a.html").write_text("<html>bkz. sayfa 19</html>", encoding="utf-8")
    b = denetim.render_denetle(str(tmp_path))
    assert any(x.kod == "R2" for x in b)


def test_render_kanonik_temiz(tmp_path):
    p = uret_kos(KANONIK, tmp_path)
    assert p.returncode == 0
    assert denetim.render_denetle(str(tmp_path)) == []


def test_d17_bayat_pxx_yakalanir():
    d = _yuzey(); px = dict(d["PXX_YIL"]); px[90] = px[90] - 150; d["PXX_YIL"] = px
    assert "D17" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d17_populasyon_sd_kaymasi_yakalanir():
    """Formul kaymasi: n-1 orneklem boleni populasyona (n) donerse SD kuculur."""
    import math
    d = _yuzey()
    yil = [sum(d["IKLIM"][y]) for y in d["TAM_YILLAR"]]
    ort = sum(yil) / len(yil)
    d["YIL_SD"] = math.sqrt(sum((v - ort) ** 2 for v in yil) / len(yil))  # n boleni
    assert "D17" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d18_olculmemis_gun_durust_gecer(tmp_path):
    """Karar (a): olculmemis gun karnede olculdu=false + null ile KALIR;
    rapor uretilir, s07 son-7 tablosunda '—' satiri vardir, D4 o satiri
    atlar, D18 KESINTISIZ'la capraz tutarliligi dogrular."""
    J = json.loads(KANONIK.read_text(encoding="utf-8"))
    r = J["accuracy"]["report_card"][27]          # son 7 icinde
    r["olculdu"] = False
    r["wmape_0_24"] = r["skill"] = r["naif_wmape"] = None
    J["accuracy"]["uninterrupted_days"] = 2       # kuyruk: 28,29 olculu -> t=2
    yol = tmp_path / "olculmemis.json"
    yol.write_text(json.dumps(J, ensure_ascii=False), encoding="utf-8")
    kayitlar, bulgular, _b = denetim.denetle_tam(taze_veri(yol))
    assert not [b for b in bulgular if b.seviye == "hata"], bulgular
    p = uret_kos(yol, tmp_path / "c")
    assert p.returncode == 0, p.stdout + p.stderr
    s07 = next((tmp_path / "c").glob("*_s07_*.html")).read_text(encoding="utf-8")
    assert "—</td>" in s07                      # tabloda '—' satiri


def test_d18_kesintisiz_celiskisi_yakalanir():
    d = _yuzey()
    olc = [True] * 30; olc[27] = False
    d["KARNE_OLCULDU"] = olc
    wm = list(d["KARNE_WM"]); sk = list(d["KARNE_SK"]); nf = list(d["KARNE_NAIF"])
    wm[27] = sk[27] = nf[27] = None
    d["KARNE_WM"], d["KARNE_SK"], d["KARNE_NAIF"] = wm, sk, nf
    d["KESINTISIZ_GUN"] = 87                      # kuyruk t=2 iken 87 iddiasi
    assert "D18" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}
