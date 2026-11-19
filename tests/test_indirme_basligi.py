"""19.11 canlı özellik testi — indirme başlığı: Türkçe santral adı 500/502 vermez (ASCII `filename=` + RFC 5987 `filename*=`)."""
import re
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import dengesizlik_service, plant_service

PLANT = "33333333-3333-3333-3333-333333333333"


def test_indirme_basligi_ascii_ve_utf8():
    b = api_main._indirme_basligi("pvquant_uzlastirma_saatlik_Karapınar RT-2579_90g.csv")
    assert b == 'attachment; filename="pvquant_uzlastirma_saatlik_Karapinar_RT-2579_90g.csv"; filename*=UTF-8\'\'pvquant_uzlastirma_saatlik_Karap%C4%B1nar%20RT-2579_90g.csv'
    b.encode("latin-1")   # başlık kodlanabilir (uvicorn/h11 latin-1 ister)
    assert api_main._indirme_basligi('Kıvanç "2" GES.xlsx').startswith('attachment; filename="Kivanc_2_GES.xlsx"')
    assert api_main._indirme_basligi("şğı") == 'attachment; filename="sgi"; filename*=UTF-8\'\'%C5%9F%C4%9F%C4%B1'
    assert api_main._indirme_basligi("") == 'attachment; filename="pvquant"; filename*=UTF-8\'\''


def test_turkce_adli_santralda_csv_indirme_200(monkeypatch):
    """Canlıda Karapınar RT-2579 için dengesizlik/saatlik?fmt=csv 500 veriyordu (UnicodeEncodeError başlıkta)."""
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": PLANT, "name": "Karapınar RT-2579", "params_json": {}})
    monkeypatch.setattr(dengesizlik_service, "dokum", lambda *a, **k: (pd.DataFrame({"saat": [1]}), {"aylar": []}))
    monkeypatch.setattr(dengesizlik_service, "dokum_csv", lambda df: "saat\n1\n")
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"tenant_id": "t", "sub": "u", "role": "viewer"}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/plants/{PLANT}/dengesizlik/saatlik?gun=90&fmt=csv")
        assert r.status_code == 200, r.text
        cd = r.headers["content-disposition"]
        assert 'filename="pvquant_uzlastirma_saatlik_Karapinar_RT-2579_90g.csv"' in cd
        assert "filename*=UTF-8''pvquant_uzlastirma_saatlik_Karap%C4%B1nar_RT-2579_90g.csv" in cd
        assert r.text == "saat\n1\n"
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)


def test_ham_baslik_kalmadi():
    k = Path(api_main.__file__).read_text(encoding="utf-8")
    assert len(re.findall(r"attachment; filename=", k)) == 1, "yalnız _indirme_basligi içinde"
    assert k.count("_indirme_basligi(") == 16, "15 indirme ucu + tanım"
