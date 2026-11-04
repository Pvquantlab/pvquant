"""04.11.2026 v2.534 (P8b-1): yıl yıl P-değeri serisi ve gerçekleşen kıyası (SAF)."""
from datetime import date

import pandas as pd

from pvquant.services import pdeger_service as pdg


def test_yil_yil_seri_bozunma_ve_omur():
    s = pdg.yil_yil_seri(10_000_000, 0.06, 0.5, 10, 2024, sigma_yillar_arasi=0.04)
    r = s["satirlar"]
    assert len(r) == 10 and r[0]["takvim_yili"] == 2024 and r[9]["takvim_yili"] == 2033 and r[0]["bicim"] == "yıl n"
    assert r[0]["p50"] == 10_000_000 and r[1]["p50"] == round(10_000_000 * 0.995, 0) and r[9]["p50"] == round(10_000_000 * 0.995 ** 9, 0)
    assert r[0]["p90"] == round(10_000_000 * (1 - 1.2816 * 0.06), 0) and r[0]["p99"] < r[0]["p90"] < r[0]["p75"] < r[0]["p50"]
    assert s["sigma_nyil"] < s["sigma_1yil"] and s["omur_ortalamasi"]["bicim"] == "ömür ortalaması" and abs(s["omur_toplami"]["p50"] - s["omur_ortalamasi"]["p50"] * 10) < 10
    assert s["omur_ortalamasi"]["p90"] > sum(x["p90"] for x in r) / 10          # ömür ortalamasında yıllar arası oynaklık √N ile küçülür
    assert pdg.yil_yil_seri(1e6, 0.05, 0.0, 3, None)["satirlar"][2]["takvim_yili"] is None


def test_gerceklesen_kiyas_tam_yil_ve_cari():
    seri = pdg.yil_yil_seri(10_000_000, 0.06, 0.5, 5, 2023)
    yillik = pd.DataFrame({"yil": [2023, 2024, 2025, 2026], "kwh": [4_000_000, 10_200_000, 9_300_000, 2_000_000], "saat": [3000, 8700, 8600, 2000]})
    pay = [40, 55, 80, 100, 120, 130, 135, 125, 100, 75, 45, 35]                  # iklim GHI aylık P50 (kWh/m²)
    k = pdg.gerceklesen_kiyas(yillik, seri, date(2026, 3, 16), pay, butce_kwh_yil=9_500_000)
    r = {x["yil"]: x for x in k}
    assert r[2023]["durum"] == "kapsam_yetersiz" and r[2023]["oran_p50"] is None
    assert r[2024]["durum"] == "tam_yil" and r[2024]["konum"] == "ustu" and abs(r[2024]["oran_p50"] - 10_200_000 / seri["satirlar"][1]["p50"]) < 1e-3
    assert r[2025]["konum"] == "arasi" and r[2025]["oran_p90"] > 1 > r[2025]["oran_p50"] and r[2025]["butce_orani"] == round(9_300_000 / 9_500_000, 3)
    c = r[2026]; ytd = (40 + 55 + 80 * 16 / 31) / sum(pay)
    assert c["durum"] == "cari_yil" and abs(c["ytd_pay"] - ytd) < 1e-3 and c["p50_kwh"] == round(seri["satirlar"][3]["p50"] * ytd, 0) and c["konum"] in ("ustu", "arasi", "alti")
    # pay yoksa cari yıl kıyaslanmaz; seri dışı yıl atlanır; boş
    k2 = pdg.gerceklesen_kiyas(yillik, seri, date(2026, 3, 16), None)
    assert {x["yil"]: x["durum"] for x in k2}[2026] == "cari_pay_yok"
    assert pdg.gerceklesen_kiyas(pd.DataFrame({"yil": [2030], "kwh": [1.0], "saat": [1]}), seri, date(2026, 3, 16)) == []
    assert pdg.gerceklesen_kiyas(pd.DataFrame(), seri, date(2026, 3, 16)) == []


def test_hesapla_bankable_yoksa(monkeypatch):
    from pvquant.services import bankable_service
    monkeypatch.setattr(bankable_service, "getir", lambda plant: None)
    assert pdg.hesapla("t", {"id": "x", "params_json": {}})["durum"] == "bankable_yok"
