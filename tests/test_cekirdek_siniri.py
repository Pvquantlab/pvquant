"""v2.597 (Faz 4 F4-A, Stage 2) — korunan çekirdeğin sınır bekçisi (AST; DB'siz).

1. Korunan modüller (`pipeline/*`, `models/*`, `models_v2/*`, `ext/tahmin/*`, `io/meteo.py`) servis/DB/uygulama katmanını
   içe aktarmaz; `io/*` servisleri içe aktarmaz (bilinen iki istisna adıyla listelidir, kapanışları F4-B / F4-I'da).
2. Saf katman işlevleri (bant zinciri + `tahmin_uret` + `plant_spec_kur`) gövdelerinde DB/ağ/saat adı geçmez.
3. `forecast_values` yazan tek üretim yolu `forecast_service` (apps + src); betiklerdeki yazıcılar adıyla listelidir.
Belge: docs/CEKIRDEK-SINIRI.md.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
SRC = KOK / "src" / "pvquant"

KORUNAN = ["pipeline", "models", "models_v2", "ext/tahmin", "io/meteo.py"]
YASAK_ON_EK = ("pvquant.services", "pvquant.db", "pvquant.surum", "apps", "sqlalchemy", "psycopg", "alembic")
# io/ katmanı: servis içe aktarmaz; DB yalnız arşiv modülünde (hesap/erişim ayrımı F4-B)
IO_ISTISNA = {
    "io/acik_nwp.py": {"pvquant.db"},                          # meteo_arsiv okuma/yazma — F4-B'de hesap kısmı ayrılacak
}

SAF_ISLEVLER = {
    "services/ufuk_service.py": ["uygula_df", "sigma_hesapla_df"],
    "services/sapma_service.py": ["uygula_df", "oranlar_hesapla"],
    "services/konformal_service.py": ["uygula_df", "q_hat_hesapla_df", "q_dizisi"],
    "services/ensemble_service.py": ["uye_kantilleri", "uye_meteodata", "bant_hesapla"],
    "services/forecast_service.py": ["tahmin_uret", "eksik_saatleri_kirp", "kosu_cercevesi_denetle"],
    "services/plant_spec_service.py": ["plant_spec_kur", "params_json"],
}
SAF_YASAK_ADLAR = {"tenant_baglami", "sistem_baglami", "OpenMeteoClient", "get_engine", "create_engine", "requests", "httpx", "urlopen"}

# forecast_values yazan betikler (üretim yolu değil; her biri bilinir — yeni yazıcı bu listeyi büyütmeden giremez)
BETIK_YAZICILAR = {"scripts/dev_skill_backtest.py", "scripts/faz1_solentegre_simulasyon.py", "scripts/seed_sentetik.py"}


def _py_dosyalar(kok: Path):
    if kok.is_file():
        return [kok]
    return sorted(p for p in kok.rglob("*.py") if "__pycache__" not in p.parts)


def _ice_aktarimlar(dosya: Path):
    agac = ast.parse(dosya.read_text(encoding="utf-8"), filename=str(dosya))
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Import):
            for a in dugum.names:
                yield a.name, dugum.lineno
        elif isinstance(dugum, ast.ImportFrom) and dugum.level == 0 and dugum.module:
            yield dugum.module, dugum.lineno


def _ihlaller(dosya: Path, yasak: tuple[str, ...]):
    for ad, satir in _ice_aktarimlar(dosya):
        if any(ad == y or ad.startswith(y + ".") for y in yasak):
            yield f"{dosya.relative_to(KOK)}:{satir}: {ad}"


@pytest.mark.parametrize("bolum", KORUNAN)
def test_korunan_cekirdek_servis_db_uygulama_ice_aktarmaz(bolum):
    ihlal = [i for d in _py_dosyalar(SRC / bolum) for i in _ihlaller(d, YASAK_ON_EK)]
    assert not ihlal, "çekirdek sınırı ihlali:\n" + "\n".join(ihlal)


def test_io_katmani_servis_ice_aktarmaz_istisnalar_adiyla():
    ihlal = []
    for d in _py_dosyalar(SRC / "io"):
        goreli = d.relative_to(SRC).as_posix()
        izin = IO_ISTISNA.get(goreli, set())
        for ad, satir in _ice_aktarimlar(d):
            for y in ("pvquant.services", "apps"):
                if (ad == y or ad.startswith(y + ".")) and y not in izin:
                    ihlal.append(f"io/{goreli}:{satir}: {ad}")
            if (ad == "pvquant.db" or ad.startswith("pvquant.db.")) and "pvquant.db" not in izin:
                ihlal.append(f"io/{goreli}:{satir}: {ad}")
    assert not ihlal, "io katmanı sınır ihlali:\n" + "\n".join(ihlal)
    # istisnalar gerçekten var mı (kapanınca liste küçülsün, ölü istisna kalmasın)
    for goreli, izin in IO_ISTISNA.items():
        adlar = {ad for ad, _ in _ice_aktarimlar(SRC / goreli)}
        for y in izin:
            assert any(ad == y or ad.startswith(y + ".") for ad in adlar), f"ölü istisna: {goreli} artık {y} içe aktarmıyor — listeden düş"


@pytest.mark.parametrize("dosya,islevler", sorted(SAF_ISLEVLER.items()))
def test_saf_islevler_db_ag_saat_adi_gecirmez(dosya, islevler):
    agac = ast.parse((SRC / dosya).read_text(encoding="utf-8"))
    tanimlar = {d.name: d for d in agac.body if isinstance(d, ast.FunctionDef)}
    for ad in islevler:
        assert ad in tanimlar, f"{dosya}: saf işlev {ad} yok (ad değiştiyse listeyi güncelle)"
        kullanilan = set()
        for dugum in ast.walk(tanimlar[ad]):
            if isinstance(dugum, ast.Name):
                kullanilan.add(dugum.id)
            elif isinstance(dugum, ast.Attribute):
                kullanilan.add(dugum.attr)
            elif isinstance(dugum, (ast.Import, ast.ImportFrom)):
                for a in dugum.names:
                    kullanilan.add(a.name.split(".")[0]); kullanilan.add(a.asname or "")
                if isinstance(dugum, ast.ImportFrom) and dugum.module:
                    kullanilan.add(dugum.module)
        kesisim = kullanilan & SAF_YASAK_ADLAR
        assert not kesisim, f"{dosya}:{ad} saf değil — {sorted(kesisim)}"
        # saat: `*_hesapla*` ayarın hesap_zamani damgasını basar, `tahmin_uret` yalnız `simdi` varsayılanı için okur; uygulayıcılar
        # (uygula_df, q_dizisi, kantiller, kurucu) zamanı parametre alır — saat okumaz
        if ad != "tahmin_uret" and "hesapla" not in ad:
            for dugum in ast.walk(tanimlar[ad]):
                if isinstance(dugum, ast.Attribute) and dugum.attr in {"now", "utcnow", "today"}:
                    pytest.fail(f"{dosya}:{ad} saat okuyor (satır {dugum.lineno}) — zamanı parametre yap")


def test_forecast_values_yazan_tek_uretim_yolu_forecast_service():
    hedef = "INSERT INTO forecast_values"
    yazanlar = set()
    for kok in (KOK / "src", KOK / "apps", KOK / "scripts"):
        for d in _py_dosyalar(kok):
            if hedef.lower() in d.read_text(encoding="utf-8").lower():
                yazanlar.add(d.relative_to(KOK).as_posix())
    uretim = {y for y in yazanlar if not y.startswith("scripts/")}
    assert uretim == {"src/pvquant/services/forecast_service.py"}, f"forecast_values yazan üretim yolu birden fazla: {sorted(uretim)}"
    assert {y for y in yazanlar if y.startswith("scripts/")} == BETIK_YAZICILAR, "betik yazıcı listesi değişti — docs/CEKIRDEK-SINIRI.md ile birlikte güncelle"
