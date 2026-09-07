"""v2.294 — S4: müşteriye açık doğrulama yayını (rakip araştırması bulgusu: sektörde kimse
güç tahmini karnesini kamuya açmıyor — açan için tasarım değil GÜVEN ürünü).

Yayın kapısı operatör elindedir: params_json.dogrulama_yayini == "acik" olan santral(lar)
"referans santral" olarak yayınlanır. Kamuya YALNIZ toplulaştırılmış karne çıkar:
ad/konum/koordinat/kimlik yayınlanmaz; etiket kurulu güç sınıfı + bölge genelidir.
Sayı politikası vitrinle aynı: ölçüm varsa sayı, yoksa dürüst "kapalı" — uydurma yok.
"""
from __future__ import annotations

import pandas as pd

PENCERE_GUN = 90
EN_AZ_GUN = 30          # yayına çıkmak için asgari sınav günü — cılız örneklem yayınlanmaz


def _yuvarla(x, n=1):
    return None if x is None else round(float(x), n)


def ozet() -> dict:
    """Kimliksiz uç için toplulaştırılmış karne. Sistem bağlamı; yalnız yayın bayraklı santral."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        st = s.execute(text(
            "SELECT id, capacity_kwp FROM plants "
            "WHERE params_json->>'dogrulama_yayini' = 'acik' AND NOT archived "
            "ORDER BY capacity_kwp DESC LIMIT 1")).first()
        if st is None:
            return {"durum": "kapali"}
        k = s.execute(text(
            "SELECT count(*) AS gun, max(date) AS son,"
            " avg(mape) AS wmape, avg(naive_wmape) AS naif, avg(cliper_wmape) AS siki,"
            " avg(nmae) AS nmae, avg(picp80) AS picp "
            "FROM skill_daily WHERE plant_id=:p AND horizon_bucket='0-24' "
            "AND date >= current_date - :g"), {"p": st.id, "g": PENCERE_GUN}).mappings().first()
        aylar = s.execute(text(
            "SELECT to_char(date_trunc('month', date), 'YYYY-MM') AS ay, count(*) AS gun,"
            " avg(mape) AS wmape, avg(naive_wmape) AS naif, avg(picp80) AS picp "
            "FROM skill_daily WHERE plant_id=:p AND horizon_bucket='0-24' "
            "AND date >= current_date - 120 GROUP BY 1 ORDER BY 1 DESC LIMIT 3"),
            {"p": st.id}).mappings().all()
    if not k or (k["gun"] or 0) < EN_AZ_GUN or k["wmape"] is None:
        return {"durum": "kapali"}   # örneklem cılızsa da dürüstçe kapalı
    kwp = float(st.capacity_kwp)
    sinif = "10 MW üzeri" if kwp >= 10000 else "1–10 MW" if kwp >= 1000 else "1 MW altı"
    beceri = (lambda ref: None if not ref else _yuvarla((1 - float(k["wmape"]) / float(ref)) * 100, 0))
    return {
        "durum": "acik",
        "santral_etiketi": f"Referans santral · {sinif} · İç Anadolu",
        "pencere_gun": int(k["gun"]), "son_gun": k["son"].isoformat(),
        "wmape_pct": _yuvarla(k["wmape"]), "naif_wmape_pct": _yuvarla(k["naif"]),
        "siki_referans_wmape_pct": _yuvarla(k["siki"]), "nmae_pct": _yuvarla(k["nmae"]),
        "beceri_naif_pct": beceri(k["naif"]), "beceri_siki_pct": beceri(k["siki"]),
        "bant_kapsama_pct": _yuvarla(float(k["picp"]) * 100) if k["picp"] is not None else None,
        "bant_hedef_pct": 80.0,
        "aylar": [{"ay": a["ay"], "gun": int(a["gun"]), "wmape_pct": _yuvarla(a["wmape"]),
                   "naif_wmape_pct": _yuvarla(a["naif"]),
                   "bant_kapsama_pct": _yuvarla(float(a["picp"]) * 100) if a["picp"] is not None else None}
                  for a in aylar],
        "not": "0–24 saat ufku, saatlik karşılaştırma; her gece otomatik hesaplanır, geçmiş değiştirilmez.",
    }
