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
    ("bozuk_10_bant_yarim_d24.json", "D24", False),
    ("bozuk_11_matris_marjinal_d25.json", "D25", False),
]
_sayac = [0]

# v2.157: kayıt makamının sabit kehaneti — TEK yerde (mutasyon bekçisi kalır,
# aynı sayı iki yerde elle yaşamaz). Yeni denetim eklenince BURASI bilinçli güncellenir.
BEKLENEN_KODLAR = ["D%d" % i for i in range(1, 26)]   # D1..D25
BEKLENEN_GECEN_KAYIT = 36                             # kanonik koşuda geçen kayıt sayısı (D22 +3, D23 +2, D24 +3, D25 +3)


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
    assert sorted({k["kod"] for k in kayitlar}) == sorted(BEKLENEN_KODLAR)
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
    assert j["ozet"]["hata"] == 0 and j["ozet"]["gecti"] == BEKLENEN_GECEN_KAYIT
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
    assert len(j["gecenler"]) == BEKLENEN_GECEN_KAYIT
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
    """v2.132 üst-sınır: 468 günlük dönemde 9.419 saat (%84) meşrudur.
    (B3b-1: hüküm artık alandan — mutasyon da alanda.)"""
    d = _yuzey()
    d["ARSIV_BAS"], d["ARSIV_BIT"] = (2025, 4, 30), (2026, 8, 10)
    d["ARSIV_SAAT"] = 9419
    assert "D6" not in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d6_kapasite_asimi_hala_duser():
    d = _yuzey()                      # uçlar kanonik alandan (1 Şub–4 Ağu)
    d["ARSIV_SAAT"] = 4600            # 184 gün × 24 × 1,01 = 4.460 < 4.600
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
    d["ARSIV_BAS"], d["ARSIV_BIT"] = (2024, 1, 1), (2024, 2, 28)
    d["ARSIV_SAAT"] = 1416
    assert "D15" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


# ------------------------------------------------- B3b-1 (v2.169)
def test_d6_alan_oncelik_etiket_hukumsuz():
    """Alanlar sağlamken etiket çorbaysa D6 GEÇER — etiket artık hüküm
    makamı değil, sunum süsüdür."""
    d = _yuzey()
    d["ARSIV_ETIKET"] = "anlamsız çorba (bozuk etiket)"
    assert "D6" not in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d6_etiket_yedegi_alan_yoksa_yasar():
    """Eski JSON'lar alan taşımaz — üç alan da yokken etiket çözümü
    (yedek yol) hükmü verir: 4.600 saat kapasite aşımı yakalanır."""
    d = _yuzey()
    d["ARSIV_BAS"] = d["ARSIV_BIT"] = d["ARSIV_SAAT"] = None
    d["ARSIV_ETIKET"] = "1 Şubat – 4 Ağustos 2026\n    (4.600 saat)"
    assert "D6" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_b3b1_kanonik_alanlar_ve_sebeke_alandan(tmp_path):
    """Kontrat kanıtı: kanonik alanları taşır; SEBEKE tokenı ALANDAN gelir
    (display-split öldü — alan değişince display aynı kalsa da token oynar)."""
    m = taze_veri(KANONIK)
    assert m.ARSIV_BAS == (2026, 2, 1) and m.ARSIV_BIT == (2026, 8, 4)
    assert m.ARSIV_SAAT == 4440 and m.SEBEKE_AC_MWE == 10.0
    assert m.doldur("{{SEBEKE}}") == "10,0 MWe"
    J = json.loads(KANONIK.read_text(encoding="utf-8"))
    J["plant"]["sebeke_ac_mwe"] = 3.6          # display'e DOKUNULMADI
    y = tmp_path / "sebeke36.json"
    y.write_text(json.dumps(J, ensure_ascii=False), encoding="utf-8")
    assert taze_veri(y).doldur("{{SEBEKE}}") == "3,6 MWe"


# ------------------------------------------------- B3b-2 (v2.170)
def test_b3b2_kanonik_katsayilar_ve_turetim():
    """Kontrat kaniti: kanonik coefficients tasir, token'lar SAYIDAN turetilir
    ve donmus metinlerle birebir; statik ayna da ayni turetimden gecer."""
    m = taze_veri(KANONIK)
    assert (m.KAT_ETA_V, m.KAT_BIF_V, m.KAT_ALBEDO) == (0.942, 7.3, 0.16)
    assert m.KAT_SAAT_V == 1487 and m.KAT_TARIH_V == (2026, 7, 19)
    assert m.doldur("{{KAT_ETA}}|{{KAT_BIF}}|{{KAT_SAAT}}|{{KAT_TARIH}}") == \
        "0,942|%7,3|1.487|19 Temmuz 2026"
    J = json.loads(KANONIK.read_text(encoding="utf-8"))
    assert "kat_eta" not in J["narrative"]   # ayni bilgi iki yerde yasamaz


def test_d7_sayi_oncelik_metin_hukumsuz():
    """Sayi alani varken metin corbasi D7'yi oynatamaz; bozuk SAYI ise
    metin ne derse desin yakalanir — hukum makami sayidir."""
    d = _yuzey(); d["KAT_ETA"] = d["KAT_BIF"] = "çorba"
    assert "D7" not in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}
    d = _yuzey(); d["KAT_ETA"] = "0,942"; d["KAT_ETA_V"] = 1.50
    assert "D7" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_d7_d5_metin_yedegi_alan_yoksa_yasar():
    """Eski JSON'lar sayi tasimaz — alanlar None iken metin cozumu hukum
    verir: aralik disi eta yakalanir, D5 saati metinden okur."""
    d = _yuzey()
    d["KAT_ETA_V"] = d["KAT_BIF_V"] = d["KAT_SAAT_V"] = None
    d["KAT_ETA"] = "0,50"
    b = denetim.denetle(d)
    assert "D7" in {x.kod for x in b if x.seviye == "hata"}
    assert "D5" not in {x.kod for x in b if x.seviye == "uyari"
                        and "saat" in x.mesaj.lower() and "yok" in x.mesaj.lower()}


# ------------------------------------------------- D22 (v2.172)
def test_d22_anlati_bayat_sayi_yakalanir():
    """Alan oynadı, anlatı eski sayıyı söylüyor → D22 hata. (10 Ağu
    vakasının anlatı ayağı: taze alan + bayat cümle aynı sayfada olamaz.)"""
    d = _yuzey(); d["KAT_ETA_V"] = 0.951          # anlatı hâlâ "0,942" der
    assert "D22" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d22_anlati_kosulluluk_alansiz_iddia_duser():
    """Alan None iken anlatı o katsayıdan söz edemez — canlı bifacial'sız
    santral senaryosu: künye '—' derken anlatı '0,16' satamaz."""
    d = _yuzey(); d["KAT_ALBEDO"] = None
    b = [x for x in denetim.denetle(d) if x.kod == "D22" and x.seviye == "hata"]
    assert b and "albedo" in b[0].mesaj


def test_d22_iddiasiz_anlati_gecer():
    """Boş anlatı ve katsayıdan söz etmeyen anlatı iddia taşımaz → D22
    sesini çıkarmaz; rakam-sınır bekçisi '10,16' içindeki '0,16'yı saymaz."""
    d = _yuzey(); d["NARR_S09_PROSE"] = ""
    assert "D22" not in {b.kod for b in denetim.denetle(d)}
    d = _yuzey(); d["NARR_S09_PROSE"] = "Kalibrasyon dönemi yeterli uzunluktadır."
    assert "D22" not in {b.kod for b in denetim.denetle(d)}
    d = _yuzey()
    d["NARR_S09_PROSE"] = d["NARR_S09_PROSE"].replace("0,16", "10,16")
    assert "D22" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


# ------------------------------------------------- D23 (v2.173)
def test_d23_v2169_senaryosu_bayat_display_yakalanir():
    """v2.169 kanıt testinin kapattığı deliğin bekçisi: alan oynar, display
    bayat kalır → {{SEBEKE}} ile SAHA aynı raporda çelişirdi. Artık D23 düşer."""
    d = _yuzey(); d["SEBEKE_AC_MWE"] = 3.6     # display hâlâ "…/ 10,0 MWe"
    assert "D23" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}
    d = _yuzey(); d["KAPASITE_MWP"] = 13.0     # MWp bacağı da aynı bekçide
    assert "D23" in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


def test_d23_alansiz_mwe_iddiasi_duser():
    """Koşulluluk aynası: SEBEKE_AC_MWE None iken künye '—' basar — SAHA
    display'i sayı satamaz."""
    d = _yuzey(); d["SEBEKE_AC_MWE"] = None
    b = [x for x in denetim.denetle(d) if x.kod == "D23" and x.seviye == "hata"]
    assert b and "MWe" in b[0].mesaj


def test_d23_durust_sessizlik_ve_tolerans_gecer():
    """Alan yok + display iddia etmiyor → geçer; ±0,05 değer toleransı
    biçim kaymasını hata saymaz (bayat sayı avlanır, ondalık değil)."""
    d = _yuzey(); d["SEBEKE_AC_MWE"] = None
    d["SAHA"] = [("Kurulu güç", "12,4 MWp")] + [s for s in d["SAHA"]
                                               if s[0] != "Kurulu güç"]
    assert "D23" not in {b.kod for b in denetim.denetle(d)}
    d = _yuzey()
    d["SAHA"] = [("Kurulu güç", "12,42 MWp / 10,03 MWe")] + \
        [s for s in d["SAHA"] if s[0] != "Kurulu güç"]
    assert "D23" not in {b.kod for b in denetim.denetle(d) if b.seviye == "hata"}


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
    r["wmape_0_24"] = r["skill"] = r["naif_wmape"] = r["wmape_24_72"] = None
    # v2.185: karne aynası (D25) — gün ölçülmemişse matris kolonu da boş
    # olmalı; fikstür senaryosu artık matrisi de kapsar (D25'in ilk avı
    # bu testti: eski fikstür kolonu dolu bırakıyordu, bekçi haklıydı).
    for _satir in J["error_dist"]["matrix"]["mae_mw"]:
        _satir[27] = None
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


def test_d18_olculmemis_gune_24_72_basilamaz():
    d = _yuzey()
    olc = [True] * 30; olc[27] = False
    wm = list(d["KARNE_WM"]); sk = list(d["KARNE_SK"]); nf = list(d["KARNE_NAIF"])
    wm[27] = sk[27] = nf[27] = None
    d["KARNE_OLCULDU"], d["KARNE_WM"], d["KARNE_SK"], d["KARNE_NAIF"] = olc, wm, sk, nf
    d["KESINTISIZ_GUN"] = 2
    # kuyruk 5. satir (indeks 27-23=4) DOLU birakildi -> ihlal
    assert "D18" in {x.kod for x in denetim.denetle(d) if x.seviye == "hata"}


def test_s07_uydurma_carpan_kaynakta_yok():
    """v2.143 gerileme bekçisi: 'hiçbir sayı elle yazılmaz' — s07'de çarpım
    formulü olarak 1.36 kalmadı (24-72 artık KARNE_H72 ölçümünden)."""
    kaynak = (MOTOR / "build_s07.py").read_text(encoding="utf-8")
    assert "* 1.36" not in kaynak and "*1.36" not in kaynak
    assert "KARNE_H72" in kaynak


def test_s05_figcap_anlatisiz_cumle_duser(tmp_path):
    """v2.144: sabit '11-12 Agustos cephe gecisi' cumlesi token'landi.
    Anlati alani yoksa cumle DUSER (kural 4) — '{{' kalintisi da olmaz (R1)."""
    J = json.loads(KANONIK.read_text(encoding="utf-8"))
    del J["narrative"]["s05_figcap"]
    yol = tmp_path / "figcapsiz.json"
    yol.write_text(json.dumps(J, ensure_ascii=False), encoding="utf-8")
    m = taze_veri(yol)
    assert m.NARR_S05_FIGCAP == ""
    p = uret_kos(yol, tmp_path / "c")
    assert p.returncode == 0, p.stdout + p.stderr
    s05 = next((tmp_path / "c").glob("*_s05_*.html")).read_text(encoding="utf-8")
    assert "cephe geçişinin" not in s05 and "{{" not in s05


def test_s05_figcap_uretici_gercek_semadan():
    """v2.145: uretici v2.1 semasindan (daily[].half_mwh) okur; en genis
    bandi ILK SEKIZ gun icinde secer; bant yoksa None (cumle dusulur)."""
    import sys as _s
    _s.path.insert(0, str(KOK / "src"))
    from pvquant.services.report_html_service import _s05_figcap_uret
    daily = [{"date": "2026-08-%02d" % (16 + i), "half_mwh": hw}
             for i, hw in enumerate([4.3, 4.2, 9.7, 4.4, 4.5, 4.4, 7.6, 7.4,
                                     99.0, 99.0])]   # 9-10. gunler pencere DISI
    c = _s05_figcap_uret(daily)
    assert c == "İlk sekiz gün içinde en geniş belirsizlik bandı 18 Ağustos günündedir (±9,7 MWh)."
    assert _s05_figcap_uret([{"date": "2026-08-16", "half_mwh": None}]) is None
    assert _s05_figcap_uret([]) is None


# ------------------------------------------------- Adim 4 (v2.147)
def test_bulgu_ayikla_json_dali(tmp_path):
    """v2.149: fikstur GERCEK ureticiden (denetim.json_yaz) gelir — v2.147'nin
    testi anahtari elle ('kalanlar') yazdigi icin ayiklayicidaki ayni yanlis
    varsayimi goremedi (canli 500 vakasi). Sozlesme artik uretici-bagli."""
    import sys as _s; _s.path.insert(0, str(KOK / "src"))
    from pvquant.services.report_html_service import _bulgu_ayikla
    kayitlar = [
        {"kod": "D1", "durum": "gecti", "mesaj": "m", "beklenen": "b", "bulunan": "v"},
        {"kod": "D18", "durum": "hata", "mesaj": "kart celisiyor",
         "beklenen": "=0", "bulunan": "46 gün"},
    ]
    denetim.json_yaz(kayitlar, False, str(tmp_path / "denetim.json"))
    b = _bulgu_ayikla(str(tmp_path), "")
    assert b and b[0]["kod"] == "D18" and b[0]["seviye"] == "hata"


def test_bulgu_ayikla_regex_yedegi(tmp_path):
    import sys as _s; _s.path.insert(0, str(KOK / "src"))
    from pvquant.services.report_html_service import _bulgu_ayikla
    metin = ("[UYARI] D2 — selale adimsiz — basilmaz | beklenen: calibration.steps | bulunan: yok\n"
             "[HATA] D18 — kart celisiyor | beklenen: = 0 | bulunan: 46 gün")
    b = _bulgu_ayikla(str(tmp_path), metin)      # denetim.json YOK -> regex
    assert [(x["kod"], x["seviye"]) for x in b] == [("D2", "uyari"), ("D18", "hata")]


def test_rapor_denetim_hatasi_bulgu_tasir():
    import sys as _s; _s.path.insert(0, str(KOK / "src"))
    from pvquant.services.report_html_service import RaporDenetimHatasi
    e = RaporDenetimHatasi("gecemedi", [{"kod": "D4", "seviye": "hata"}])
    assert e.bulgular[0]["kod"] == "D4" and isinstance(e, RuntimeError)
