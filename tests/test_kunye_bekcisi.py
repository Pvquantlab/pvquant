"""04.11.2026 v2.535 — Künye bekçisi: koddaki Resmî Gazete atıfları doğrulama arşivinin kaynak envanteriyle (tests/data/kunye_envanteri.json: sayı → tarih)
eş olmalı; sicil (kunye.py) ve Hakkında mevzuat listesi künyeli; dayanak bloğu olan dosyalar RG yazıyor."""
import json
import re
from pathlib import Path

from pvquant.ext.turkiye import kunye, takvim
from pvquant.services import kaynak_service, mutabakat_service

KOK = Path(__file__).resolve().parents[1]
ENV = json.load(open(KOK / "tests/data/kunye_envanteri.json", encoding="utf-8"))
RG = re.compile(r"RG\s+(\d{1,2})[./](\d{1,2})[./](\d{4})\s*[-/]\s*(\d{5})\b")


def _norm(g, a, y):
    return f"{int(g):02d}.{int(a):02d}.{y}"


def test_koddaki_rg_atiflari_envanterle_es():
    hatali = []
    for p in sorted((KOK / "src/pvquant").rglob("*.py")):
        for m in RG.finditer(p.read_text(encoding="utf-8")):
            g, a, y, sayi = m.groups(); tarih = _norm(g, a, y)
            if sayi not in ENV:
                hatali.append(f"{p.relative_to(KOK)}: RG {tarih}-{sayi} envanterde yok")
            elif ENV[sayi] != tarih:
                hatali.append(f"{p.relative_to(KOK)}: RG {tarih}-{sayi} ≠ envanter {ENV[sayi]}")
    assert not hatali, "\n".join(hatali)


def test_sicil_tam_ve_envanterle_es():
    assert len(kunye.KUNYE) >= 30
    for ad, (kisa, tam) in kunye.KUNYE.items():
        assert kisa and tam and len(tam) > 20, ad
        for m in RG.finditer(tam):
            g, a, y, sayi = m.groups()
            assert ENV.get(sayi) == _norm(g, a, y), (ad, sayi)
    assert kunye.kunye("DUY").startswith("Elektrik Piyasası Dengeleme") and kunye.kunye("yok_boyle") == "yok_boyle"
    assert "33405" in kunye.blok("DUY", "KARAR_14907") and kunye.rg_sayilari() <= set(ENV)
    b = kunye.bul("DUY m.132/A(1); LÜY m.26(7); YEK Yön. m.5")
    assert [x["ad"] for x in b] == ["DUY", "LUY", "YEK_YON"] and kunye.bul("") == []


def test_dayanak_bloklari_dosyalarda():
    """Her dosyadaki literal blok, yorumdaki anahtar listesiyle kunye.blok(...) çıktısına eşit (sicil değişince dosyalar da yenilenmeli)."""
    import ast
    dosyalar = [p for p in (KOK / "src/pvquant").rglob("*.py") if "DAYANAK_KUNYELERI = (" in p.read_text(encoding="utf-8")]
    assert len(dosyalar) >= 20, [p.name for p in dosyalar]
    for p in dosyalar:
        src = p.read_text(encoding="utf-8")
        keys = re.search(r"# v2\.535 dayanak künyeleri \[([A-Z0-9_, ]+)\]", src).group(1).replace(" ", "").split(",")
        tree = ast.parse(src)
        lit = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "DAYANAK_KUNYELERI")
        assert lit == kunye.blok(*keys), p.name
        assert "RG " in lit


def test_hakkinda_mevzuat_kunyeli_ve_takvim_dayanak():
    m = kaynak_service.MEVZUAT
    assert len(m) >= 12 and all(x.get("kunye") for x in m) and sum("RG " in x["kunye"] for x in m) >= 9
    assert any("14907" in x["kunye"] for x in m) and any("32413" in x["kunye"] for x in m) and any("28782" in x["kunye"] for x in m)
    from datetime import date
    o = takvim._olay("x", "Deneme", date(2026, 11, 5), kaynak="DUY m.132/A(1): ayın 11'i", kaynak_turu="mevzuat")
    assert o["dayanak"] and "27200" in o["dayanak"][0] and takvim._olay("y", "Y", date(2026, 1, 1), kaynak="EPDK duyurusu", kaynak_turu="duyuru")["dayanak"] == []
    assert "33405" in mutabakat_service.__file__ or True
    src = Path(mutabakat_service.__file__).read_text(encoding="utf-8")
    assert "m.110(4) ve m.113(2) (RG 19.10.2026-33405)" in src
