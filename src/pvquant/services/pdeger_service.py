"""04.11.2026 v2.534 (P8b-1; IH-098, IH-099) — yıl yıl P-değeri serisi ve gerçekleşen kıyası.

Seri: bankable P50 (yıllık kWh, bankable_service) ve 1 yıllık toplam belirsizlik σ₁'den n. yıl için P50_n = P50 × (1 − d)^(n−1) (d = bozunma
oranı: saglik_service YoY ölçümü varsa o, yoksa %0,5/yıl VARSAYILAN, etiketli); P75/P90/P95/P99_n = P50_n × (1 − z·σ₁). Ömür ortalaması (N yıl)
için yıllar arası σ √N ile küçülür (bankable n_yil ile aynı kural); ömür toplamı = Σ P50_n. Biçim etiketi her satırda: «yıl n» / «ömür ortalaması» /
«ömür toplamı» (IH-098: biçim karışmasın). Yıl 1 = işletmeye giriş yılı (Santral tarihleri), yoksa ilk ölçüm yılı; ilk yıl kısmi olabilir.
Kıyas (IH-099): kapsaması ≥ %90 olan tamamlanmış takvim yılları için gerçekleşen kWh ↔ P50_n / P90_n → oran ve konum (P50 üstü / P50–P90 arası /
P90 altı); cari yıl için yıl başından bugüne gerçekleşen ↔ P50_n × iklim ışınım payı (iklim_beklenti aylık GHI P50 paylarıyla; bulunduğumuz ay
gün oranıyla) — HAVA DÜZELTMESİZ (ölçülen ışınım sensörü akışı yok; sapmanın bir kısmı o yılın havasıdır). İsteğe bağlı yıllık bütçe
(params_json.butce_kwh_yil, finansal model) girildiyse bütçe oranı da verilir. Tutar yok; TL kıyası bankable gelir kartında.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from pvquant.ext.standart.belirsizlik_butcesi import Z

BOZUNMA_VARSAYILAN = 0.5          # %/yıl (sektör tipik değeri; ölçüm yoksa)
KAPSAMA_ESIK = 0.90
KONUM = {"ustu": "P50 üstü", "arasi": "P50–P90 arası", "alti": "P90 altı"}


def yil_yil_seri(p50_kwh: float, sigma1: float, bozunma_yuzde_yil: float, n_yil: int, ilk_yil: int | None, sigma_yillar_arasi: float = 0.0) -> dict:
    """SAF. n. yıl P-değerleri + ömür ortalaması ve toplamı."""
    d = max(float(bozunma_yuzde_yil), 0.0) / 100.0
    satirlar = []
    for n in range(1, int(n_yil) + 1):
        p50 = float(p50_kwh) * (1 - d) ** (n - 1)
        satirlar.append({"n": n, "takvim_yili": (int(ilk_yil) + n - 1) if ilk_yil else None, "bicim": "yıl n",
                         **{f"p{q}": round(p50 * (1 - z * sigma1), 0) for q, z in Z.items()}})
    # ömür ortalaması: yıllar arası bileşen √N ile küçülür; diğer bileşenler sabit → σ_N = √(σ₁² − σ_ya² + σ_ya²/N)
    s_n = float(np.sqrt(max(sigma1 ** 2 - sigma_yillar_arasi ** 2, 0.0) + (sigma_yillar_arasi ** 2) / max(n_yil, 1)))
    ort_p50 = float(np.mean([s["p50"] for s in satirlar]))
    omur_ort = {"bicim": "ömür ortalaması", "n_yil": int(n_yil), **{f"p{q}": round(ort_p50 * (1 - z * s_n), 0) for q, z in Z.items()}}
    omur_top = {"bicim": "ömür toplamı", "n_yil": int(n_yil), **{f"p{q}": round(ort_p50 * (1 - z * s_n) * n_yil, 0) for q, z in Z.items()}}
    return {"satirlar": satirlar, "omur_ortalamasi": omur_ort, "omur_toplami": omur_top, "sigma_1yil": round(float(sigma1), 4), "sigma_nyil": round(s_n, 4),
            "bozunma_yuzde_yil": round(float(bozunma_yuzde_yil), 2)}


def _konum(oran_p50: float, oran_p90: float) -> str:
    return "ustu" if oran_p50 >= 1.0 else ("arasi" if oran_p90 >= 1.0 else "alti")


def gerceklesen_kiyas(yillik: pd.DataFrame, seri: dict, bugun: date, aylik_pay: list[float] | None = None, butce_kwh_yil: float | None = None) -> list[dict]:
    """SAF. yillik: yil, kwh, saat. Tamamlanmış yıl kapsaması ≥ %90 ise P50_n/P90_n ile kıyas; cari yıl iklim payıyla yıl başından bugüne."""
    p_by_year = {s["takvim_yili"]: s for s in seri["satirlar"] if s.get("takvim_yili")}
    out = []
    if yillik is None or yillik.empty:
        return out
    for _, r in yillik.sort_values("yil").iterrows():
        yil = int(r["yil"]); kwh = float(r["kwh"]); saat = int(r["saat"]); s = p_by_year.get(yil)
        if s is None:
            continue
        if yil < bugun.year:
            kapsam = saat / (8784 if pd.Timestamp(year=yil, month=12, day=31).is_leap_year else 8760)
            if kapsam < KAPSAMA_ESIK:
                out.append({"yil": yil, "n": s["n"], "durum": "kapsam_yetersiz", "kapsam_pct": round(kapsam * 100, 1), "gerceklesen_kwh": round(kwh, 0),
                            "p50_kwh": s["p50"], "p90_kwh": s["p90"], "oran_p50": None, "oran_p90": None, "konum": None, "butce_orani": None})
                continue
            p50, p90 = s["p50"], s["p90"]
            out.append({"yil": yil, "n": s["n"], "durum": "tam_yil", "kapsam_pct": round(kapsam * 100, 1), "gerceklesen_kwh": round(kwh, 0), "p50_kwh": p50, "p90_kwh": p90,
                        "oran_p50": round(kwh / p50, 3), "oran_p90": round(kwh / p90, 3), "konum": _konum(kwh / p50, kwh / p90),
                        "butce_orani": (round(kwh / float(butce_kwh_yil), 3) if butce_kwh_yil else None)})
        elif yil == bugun.year:
            if not aylik_pay or len(aylik_pay) != 12 or sum(aylik_pay) <= 0:
                out.append({"yil": yil, "n": s["n"], "durum": "cari_pay_yok", "gerceklesen_kwh": round(kwh, 0), "p50_kwh": s["p50"], "p90_kwh": s["p90"],
                            "oran_p50": None, "oran_p90": None, "konum": None, "butce_orani": None, "ytd_pay": None})
                continue
            pay = [p / sum(aylik_pay) for p in aylik_pay]
            ay_gun = pd.Period(f"{yil}-{bugun.month:02d}").days_in_month
            ytd = sum(pay[: bugun.month - 1]) + pay[bugun.month - 1] * (bugun.day / ay_gun)
            p50_ytd, p90_ytd = s["p50"] * ytd, s["p90"] * ytd
            out.append({"yil": yil, "n": s["n"], "durum": "cari_yil", "ytd_pay": round(ytd, 4), "gerceklesen_kwh": round(kwh, 0), "p50_kwh": round(p50_ytd, 0), "p90_kwh": round(p90_ytd, 0),
                        "oran_p50": round(kwh / p50_ytd, 3) if p50_ytd else None, "oran_p90": round(kwh / p90_ytd, 3) if p90_ytd else None,
                        "konum": _konum(kwh / p50_ytd, kwh / p90_ytd) if p50_ytd else None,
                        "butce_orani": (round(kwh / (float(butce_kwh_yil) * ytd), 3) if butce_kwh_yil else None)})
    return out


def _yillik_uretim(tenant_id, plant_id) -> pd.DataFrame:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        tz = s.execute(text("SELECT tz FROM plants WHERE id=:p"), {"p": plant_id}).scalar() or "UTC"
        return pd.read_sql(text(
            "SELECT CAST(date_part('year', ts_utc AT TIME ZONE :tz) AS int) AS yil, sum(COALESCE(energy_kwh, power_kw)) AS kwh, count(*) AS saat "
            "FROM scada_hourly WHERE plant_id=:p AND flag='valid' GROUP BY 1 ORDER BY 1"), s.connection(), params={"p": plant_id, "tz": tz})


def _aylik_pay(tenant_id, plant_id) -> list[float] | None:
    try:
        from pvquant.services import iklim_service
        b = iklim_service.iklim_oku(tenant_id, plant_id)
    except Exception:   # noqa: BLE001
        return None
    if b is None or b.empty or len(b) != 12:
        return None
    v = b.sort_values("ay")["ghi_p50_kwh_m2"].astype(float).tolist()
    return v if all(x == x and x > 0 for x in v) else None


def hesapla(tenant_id, plant: dict, bugun: date | None = None) -> dict:
    import json
    from pvquant.services import bankable_service, saglik_service
    bugun = bugun or datetime.now(timezone.utc).date()
    bk = bankable_service.getir(plant)
    if not bk or bk.get("durum") != "ok":
        return {"durum": "bankable_yok", "not": "Yıllık beklenti (P50/P90) henüz hesaplanmadı; Aylık beklenti sayfasından «Hesapla»."}
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    try:
        sg = saglik_service.saglik(tenant_id, plant); boz = sg.get("bozunma_yuzde_yil"); boz_ga = sg.get("bozunma_ga")
    except Exception:   # noqa: BLE001
        boz = None; boz_ga = None
    if boz is not None and boz < 0:
        bozunma, boz_kaynak = abs(float(boz)), "ölçüm (yıldan yıla verim kaybı" + (f", ±{abs(boz_ga[1] - boz_ga[0]) / 2:.2f}".replace(".", ",") if boz_ga else "") + ")"
    else:
        bozunma, boz_kaynak = BOZUNMA_VARSAYILAN, "varsayılan (sektör tipik %0,5/yıl; ölçülen bozunma yok)"
    giris = pj.get("isletmeye_giris")
    yillik = _yillik_uretim(tenant_id, plant["id"])
    ilk_yil = int(str(giris)[:4]) if giris else (int(yillik["yil"].min()) if not yillik.empty else None)
    n_yil = int(bk.get("N_yil") or 10)
    if ilk_yil and bugun.year - ilk_yil + 1 > n_yil:
        n_yil = bugun.year - ilk_yil + 1
    seri = yil_yil_seri(float(bk["p50_kwh"]), float(bk.get("sigma_toplam") or 0.0), bozunma, n_yil, ilk_yil, float((bk.get("bilesenler") or {}).get("yillar_arasi") or 0.0))
    butce = pj.get("butce_kwh_yil")
    butce = float(butce) if butce not in (None, "") else None
    kiyas = gerceklesen_kiyas(yillik, seri, bugun, _aylik_pay(tenant_id, plant["id"]), butce)
    return {"durum": "ok", "bugun": bugun.isoformat(), "p50_kwh": float(bk["p50_kwh"]), "bankable_hesap_zamani": bk.get("hesap_zamani"), "bankable_donem": bk.get("donem"),
            "ilk_yil": ilk_yil, "ilk_yil_kaynak": "işletmeye giriş tarihi" if giris else ("ilk ölçüm yılı" if ilk_yil else None), "n_yil": n_yil,
            "bozunma_kaynak": boz_kaynak, "butce_kwh_yil": butce, **seri, "kiyas": kiyas,
            "not": ("P-değerleri bankable yıllık beklentinin (uydu türevli ışınım arşivi, fizik modeli) 1 yıllık belirsizliğiyle; n. yıl bozunmayla düşer. Gerçekleşen kıyası "
                    "hava düzeltmesizdir: o yılın ışınımı uzun dönem ortalamasından sapmışsa oran bunu da içerir; cari yıl iklim ışınım payıyla yıl başından bugüne. "
                    "Finans raporu için bağımsız doğrulama gerekir.")}
