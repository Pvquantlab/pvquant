"""16.11.2026 gezinme hızı — yanıt önbelleği: isabet/ıska, damga ile geçersizleşme, kiracı yalıtımı, varsayılan kapalı, uç sarmalı."""
import re
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import damga_service, plant_service, saglik_service, yanit_onbellegi

PLANT = "33333333-3333-3333-3333-333333333333"


@pytest.fixture()
def etkin(monkeypatch):
    monkeypatch.setenv("PVQ_YANIT_ONBELLEK", "1"); yanit_onbellegi.temizle()
    damga = {"son_scada": "2026-11-16T00:00:00"}
    monkeypatch.setattr(damga_service, "hesapla", lambda t, p: dict(damga))
    yield damga
    yanit_onbellegi.temizle()


def test_isabet_iska_kiraci_ve_damga(etkin):
    say = {"n": 0}
    def uret():
        say["n"] += 1; return {"n": say["n"]}
    assert yanit_onbellegi.getir("t", PLANT, "x", uret) == {"n": 1}
    assert yanit_onbellegi.getir("t", PLANT, "x", uret) == {"n": 1}            # isabet: üretici koşmadı
    assert yanit_onbellegi.getir("t", PLANT, "x?gun=30", uret) == {"n": 2}     # başka parametre → ayrı kayıt
    assert yanit_onbellegi.getir("t2", PLANT, "x", uret) == {"n": 3}           # başka kiracı, aynı santral kimliği → paylaşılmaz
    etkin["son_scada"] = "2026-11-17T00:00:00"; yanit_onbellegi._DAMGA.clear()  # veri değişti (damga)
    assert yanit_onbellegi.getir("t", PLANT, "x", uret) == {"n": 4}
    assert yanit_onbellegi.SAYAC["isabet"] == 1 and yanit_onbellegi.SAYAC["iska"] == 4


def test_varsayilan_kapali_ve_damgasiz_onbelleksiz(monkeypatch):
    monkeypatch.delenv("PVQ_YANIT_ONBELLEK", raising=False); yanit_onbellegi.temizle()
    say = {"n": 0}
    def uret():
        say["n"] += 1; return say["n"]
    assert [yanit_onbellegi.getir("t", PLANT, "x", uret) for _ in range(2)] == [1, 2]
    monkeypatch.setenv("PVQ_YANIT_ONBELLEK", "1")
    def patlar(t, p): raise RuntimeError("DB yok")
    monkeypatch.setattr(damga_service, "hesapla", patlar)
    assert [yanit_onbellegi.getir("t", PLANT, "x", uret) for _ in range(2)] == [3, 4]   # damga okunamadı → her çağrı üretir
    def hata(): raise ValueError("üretici düştü")
    with pytest.raises(ValueError):
        yanit_onbellegi.getir("t", PLANT, "y", hata)


def test_saglik_ucu_tek_hesap_ve_sure_basligi(etkin, monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": PLANT, "capacity_kwp": 1000.0})
    say = {"n": 0}
    def sahte(t, st, gun=800):
        say["n"] += 1; return {"gun": gun, "hesap": say["n"]}
    monkeypatch.setattr(saglik_service, "saglik", sahte)
    try:
        c = TestClient(api_main.app)
        r1 = c.get(f"/v1/plants/{PLANT}/saglik"); r2 = c.get(f"/v1/plants/{PLANT}/saglik"); r3 = c.get(f"/v1/plants/{PLANT}/saglik?gun=400")
        assert r1.status_code == 200 and r1.json() == r2.json() == {"gun": 800, "hesap": 1}
        assert r3.json() == {"gun": 400, "hesap": 2}
        assert re.fullmatch(r"\d+", r1.headers["x-sure-ms"])
    finally:
        api_main.app.dependency_overrides.clear()


def test_sarilan_uclar_kaynakta():
    from pathlib import Path
    kaynak = Path(api_main.__file__).read_text(encoding="utf-8")
    for uc in ["summary", "genel-bakis", "saglik", "dengesizlik", "backtest", "hijyen", "guvenilirlik", "hata-dagilimi", "saat-profili", "skill", "monthly",
               "p-degerleri", "kullanilabilirlik", "dogrulama/bagimsiz", "performans", "saat-ay-matrisi", "gunes-yolu", "kayip-ayrisimi"]:   # canlı ölçüm (16.11, Karapınar): 0,3–2,8 s
        assert (f'plant_id, f"{uc}' in kaynak or f'plant_id, "{uc}"' in kaynak) and f'@app.get("/v1/plants/{{plant_id}}/{uc}")' in kaynak, uc
    assert kaynak.count("yanit_onbellegi.getir(") == 18
    assert "if taze:" in kaynak   # bağımsız doğrulama taze=1 önbelleğe girmez
    assert 'yanit.headers["X-Sure-ms"]' in kaynak
