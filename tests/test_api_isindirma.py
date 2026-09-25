"""v2.364 — ithalat ısındırması: ağır pipeline zinciri API açılışında yüklenir.

25 Eyl canlı: taze işçide iki eşzamanlı istek pvquant.pipeline'ı aynı anda ilk
kez import edince "partially initialized module" yarışı /forecast'ı aralıklı
500'e düşürüyordu. Bekçi: main.py yüklendiğinde zincir sys.modules'ta olmalı.
"""
import sys


def test_pipeline_zinciri_acilista_yuklu():
    import apps.api.main  # noqa: F401 — yükleme yan etkisi sınanıyor
    for modul in ("pvquant.pipeline", "pvquant.pipeline.calibration",
                  "pvquant.pipeline.forecast"):
        assert modul in sys.modules, f"{modul} açılışta yüklenmemiş"
