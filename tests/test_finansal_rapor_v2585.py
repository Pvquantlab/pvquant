"""v2.585 (Faz 2 F2-G, Stage 7) — Finansal etki raporu: durum etiketi (saf), şablon bölümleri (HTML/Markdown), JSON 1.4.0 financial_impact bloğu
(var/yok; arayüz hesabıyla birebir), Excel «Financial-Impact» sayfası, dönem raporu özeti, API (fmt, dönem kodu, üretim girdisi 422)."""
from __future__ import annotations

import json
from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from test_reporting import _sentetik_calibration, _sentetik_forecast

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.reporting import build_excel, build_json, from_results
from pvquant.services import aylik_rapor_service as ar
from pvquant.services import finansal_etki_service as fe
from pvquant.services import sablon_rapor_service as srs
from tests.test_finansal_etki_v2580 import santral as _santral

santral = _santral   # pytest fixture'ı bu modülde ad olarak tanıtır (noqa'sız; ruff --fix içe aktarmayı silmesin)

BUGUN = date(2026, 9, 11)


def test_finansal_durum_etiketi():
    bos = {"toplam": {"tutar_tl": None}, "meta": {}, "uzlastirma": {"resmi": {"bilesenler": []}}}
    assert srs.finansal_durum(bos)[0] == "EKSİK HESAP"
    tah = {"toplam": {"tutar_tl": 1.0, "nitelik": "sozlesme_tahmini"}, "meta": {"senaryo": None}, "uzlastirma": {"resmi": {"bilesenler": []}}}
    assert srs.finansal_durum(tah)[0] == "TAHMİNİ HESAP" and "resmî uzlaştırma belgesi değildir" in srs.finansal_durum(tah)[1]
    sen = {"toplam": {"tutar_tl": 1.0, "nitelik": "senaryo"}, "meta": {"senaryo": None}, "uzlastirma": {"resmi": {"bilesenler": [{"kod": "dengesizlik_resmi"}]}}}
    assert srs.finansal_durum(sen)[0] == "SENARYO HESABI"   # senaryo, resmîden önce gelir
    poz = {"toplam": {"tutar_tl": 1.0, "nitelik": "hesaplanan"}, "meta": {"senaryo": {"pozisyon": {}}}, "uzlastirma": {"resmi": {"bilesenler": []}}}
    assert srs.finansal_durum(poz)[0] == "SENARYO HESABI"
    res = {"toplam": {"tutar_tl": 1.0, "nitelik": "hesaplanan"}, "meta": {"senaryo": None}, "uzlastirma": {"resmi": {"bilesenler": [{"kod": "dengesizlik_resmi"}]}}}
    assert srs.finansal_durum(res)[0] == "RESMÎ KARŞILAŞTIRMALI"


def test_db_sablon_json_excel_donem_raporu_api(santral):
    tid, plant = santral
    o = fe.ozet(tid, plant, "2026-09", bugun=BUGUN)
    # --- şablon (aynı sonuçtan)
    r = srs.finansal_etki(tid, plant, sonuc=o)
    adlar = [a for a, _ in r.bolumler]
    for b in ("Durum", "Kimlik ve dönem", "Üretim ve program", "Finansal sonuç bileşenleri", "Toplam", "Resmî bildirimle karşılaştırma", "Fiyat kaynakları", "Sözleşme varsayımları",
              "Kural sürümleri ve dayanak", "Üretim düşüklüğü", "Üretim düşüklüğü notu", "İleriye dönük maruziyet (senaryo)", "Ne yapmalı", "Veri kalitesi sınırları", "Formüller", "Yeniden üretim kimliği"):
        assert b in adlar, b
    h = srs.html_sar(r); md = r.markdown()
    assert "Finansal etki raporu" in h and "EPİAŞ bildirimi esastır" in h and "resmî uzlaştırma belgesi değildir" in h and "Enerji satışı" in h and "Eylül 2026" in h
    assert srs.finansal_durum(o)[0] in h and "EDTA/EDTB" in h and md.startswith("# Finansal etki raporu") and "Enerji dengesizlik tutarı" in md
    assert "Bu dönem için EPİAŞ bildirimi yüklenmedi" in h   # ay dönemi, bildirim yok
    # --- JSON: blok yok → anahtar yok; var → arayüz hesabıyla birebir
    fr = _sentetik_forecast(); ctx = from_results(fr, _sentetik_calibration(), plant_name="Test")
    d = json.loads(build_json(ctx))
    assert d["schema_version"] == "1.4.0" and "financial_impact" not in d
    wb = load_workbook(BytesIO(build_excel(ctx))); assert "Financial-Impact" not in wb.sheetnames
    ctx.finansal = o
    d = json.loads(build_json(ctx)); fi = d["financial_impact"]
    assert fi["status"] == srs.finansal_durum(o)[0] and fi["period_code"] == "2026-09" and fi["period_type"] == "ay" and fi["dictionary_version"] == o["meta"]["sozluk_surumu"]
    assert fi["total_net_tl"] == o["toplam"]["tutar_tl"] and fi["total_quality"] == o["toplam"]["nitelik"] and fi["total_included"] == o["toplam"]["giren"]
    assert [c["code"] for c in fi["components"]] == [b["kod"] for b in o["bilesenler"]] and fi["components"][0]["net_tl"] == o["bilesenler"][0]["tutar_tl"]
    assert fi["planned_mwh"] == o["uretim"]["planlanan"]["mwh"] and fi["actual_mwh"] == o["uretim"]["gerceklesen"]["mwh"] and fi["deviation_pct"] == o["uretim"]["sapma"]["pct"]
    assert fi["official_available"] is False and fi["is_scenario"] is False and fi["program_source"] == "oneri" and fi["price_epias_hours"] + fi["price_scenario_hours"] >= 239
    assert [x["code"] for x in fi["recommendations"]] == [x["kod"] for x in o["oneriler"]] and "artı" in fi["sign_convention"] and fi["tariff_type"] == "sabit"
    wb = load_workbook(BytesIO(build_excel(ctx))); assert "Financial-Impact" in wb.sheetnames
    ws = wb["Financial-Impact"]; hucreler = {ws.cell(i, 1).value: ws.cell(i, 2).value for i in range(1, 80)}
    assert hucreler["durum"] == fi["status"] and abs(float(hucreler["toplam_net"]) - o["toplam"]["tutar_tl"]) < 1e-6 and hucreler["planlanan"] == o["uretim"]["planlanan"]["mwh"]
    satirlar = [ws.cell(i, 2).value for i in range(1, 80) if ws.cell(i, 1).value in (b["ad"] for b in o["bilesenler"])]
    assert satirlar and satirlar[0] == "satis_geliri"
    # --- dönem raporu (ay): özet bölümü, arayüzle aynı toplam
    v = ar.veri(tid, plant, "2026-09", bugun=BUGUN)
    fi2 = v["finansal"]
    assert fi2 and not fi2.get("hata") and fi2["toplam_tl"] == o["toplam"]["tutar_tl"] and fi2["durum"] == srs.finansal_durum(o)[0] and fi2["satirlar"][0]["kod"] == "satis_geliri"
    rp, _ = ar.rapor(tid, plant, "2026-09", bugun=BUGUN)
    assert any(a == "Finansal etki özeti (Finansal Etki Merkezi)" for a, _ in rp.bolumler) and any("Resmî uzlaştırma belgesi değildir" in str(g) for a, g in rp.bolumler if a == "Finansal etki notu")
    # --- uret + API
    icerik, ad = srs.uret(tid, plant, "finansal-etki", donem="2026-09", bugun=BUGUN)
    assert ad.startswith("finansal-etki_FE_GES_") and ad.endswith(".html") and "Finansal etki raporu" in icerik.decode("utf-8")
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        r1 = c.get(f"/v1/plants/{plant['id']}/rapor-sablon/finansal-etki?donem=2026-09&fmt=md")
        assert r1.status_code == 200 and r1.headers["content-type"].startswith("text/markdown") and r1.text.startswith("# Finansal etki raporu")
        assert c.get(f"/v1/plants/{plant['id']}/rapor-sablon/finansal-etki?donem=2026-13").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/rapor-sablon/finansal-etki?donem=2026-09&uretim=x").status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/rapor-sablon/finansal-etki?donem=2026-09&fmt=pdf").status_code == 422
    finally:
        api_main.app.dependency_overrides.clear()
