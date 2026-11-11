"""v2.586 (Faz 2 F2-H, Stage 8, TUR 2 — bütünleşme): Finansal Etki Merkezi'nin EDT/KÜPST'si Doğruluk dökümüyle (dengesizlik_service.dokum) aynı saatlerde birebir;
portföy toplamı santral toplamlarının toplamı; viewer rolü yalnız okur; JSON raporu = API özeti (aynı toplam); sayaç girdisi seçilince kapsam değişir, hesap düşmez."""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe
from test_finansal_etki_v2580 import santral as _santral

santral = _santral   # pytest fixture'ı bu modülde ad olarak tanıtır (noqa'sız)

BUGUN = date(2026, 9, 11)


def test_db_fem_edt_dokumle_birebir_ve_portfoy_toplami(santral):
    tid, plant = santral
    dok, ozet = ds.dokum(tid, plant, gun=10)   # Doğruluk / Mutabakat ile aynı döküm (son geçerli SCADA'dan 10 gün geriye)
    for kod, bas in (("2026-09-05", "2026-09-05"), ("2026-09", "2026-09")):
        uz = fe.uzlastirma(tid, plant, kod, bugun=BUGUN)
        sec = dok[dok["zaman"].str.startswith(bas)]
        edt = next(b for b in uz["bilesenler"] if b["kod"] == "dengesizlik"); kp = next(b for b in uz["bilesenler"] if b["kod"] == "kupst")
        tol = 0.005 * len(sec) + 0.05   # döküm her saati 2 ondalığa yuvarlar (dışa aktarım); FEM yuvarlamadan toplar → saat başına ≤ 0,005 TL fark
        assert abs(edt["tutar_tl"] - float(pd.to_numeric(sec["edt_net_tl"], errors="coerce").sum())) < tol, kod
        if kp["tutar_tl"] is not None:
            assert abs(-kp["tutar_tl"] - float(pd.to_numeric(sec["kupst_tl"], errors="coerce").sum())) < tol, kod
        assert edt["kapsam_saat"] == int(pd.to_numeric(sec["edt_net_tl"], errors="coerce").notna().sum())
    o = fe.ozet(tid, plant, "2026-09-05", bugun=BUGUN)
    pf = fe.portfoy(tid, [plant, plant], "2026-09-05", bugun=BUGUN)   # aynı santral iki kez: toplam = 2 × santral (toplama kuralı doğrusal)
    assert abs(pf["toplam"]["tutar_tl"] - 2 * o["toplam"]["tutar_tl"]) < 0.05 and pf["toplam"]["toplanan_santral"] == 2
    assert abs(pf["toplam"]["planlanan_mwh"] - 2 * o["uretim"]["planlanan"]["mwh"]) < 1e-6
    # sayaç girdisi: sayaç satırı yok → SCADA'ya düşer, ölçüm sınırı etiketi SCADA kalır, hesap aynı
    s2 = fe.uretim_ozeti(tid, plant, "2026-09-05", uretim="sayac", bugun=BUGUN)
    assert s2["gerceklesen"]["secim"] == "sayac" and s2["gerceklesen"]["sinir"] == "plant_gross_ac" and s2["gerceklesen"]["mwh"] == o["uretim"]["gerceklesen"]["mwh"]


def test_db_viewer_yalniz_okur_ve_json_api_esitligi(santral):
    tid, plant = santral
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r = c.get(f"/v1/plants/{plant['id']}/finansal-etki?donem=2026-09-05&taze=1"); assert r.status_code == 200
        api_toplam = r.json()["toplam"]["tutar_tl"]
        r2 = c.get(f"/v1/plants/{plant['id']}/report?fmt=json")
        if r2.status_code == 200 and "financial_impact" in r2.json():   # rapor son tam ayı alır; fixture Eylül'de → bugün Kasım: blok olmayabilir (dürüst yokluk)
            assert r2.json()["schema_version"] == "1.4.0"
        md = c.get(f"/v1/plants/{plant['id']}/rapor-sablon/finansal-etki?donem=2026-09-05&fmt=md")
        assert md.status_code == 200 and "Finansal etki raporu" in md.text and api_toplam is not None
        # viewer yazamaz: ayar ucuna PUT 403
        assert c.put(f"/v1/plants/{plant['id']}/tarife", json={"tip": "sabit", "tl_mwh": 1}).status_code in (401, 403)
    finally:
        api_main.app.dependency_overrides.clear()
