"""Tüm raporu tek komutla üretir: 16 sayfa + birleşik HTML/PDF.

    python3 uret.py

Çıktılar PVQ_CIKTI (varsayılan: ./cikti) altına yazılır.
Bir sayfa taşarsa uyarı basılır ve çıkış kodu 1 olur — CI adımı olarak kullanılabilir.
"""
import runpy, sys, io, contextlib

SAYFALAR = ["build_s%02d" % i for i in range(1, 17)]
sorunlu = []

for mod in SAYFALAR:
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        runpy.run_module(mod, run_name="__main__")
    cikti = tampon.getvalue().strip()
    print(cikti)
    if "TAŞMA" in cikti or ": 1 sayfa" not in cikti and "sayfa: 1" not in cikti:
        sorunlu.append(mod)

print("-" * 60)
runpy.run_module("merge_html", run_name="__main__")

if sorunlu:
    print("\nTAŞAN SAYFALAR:", ", ".join(sorunlu))
    sys.exit(1)
print("\nTüm sayfalar tek A4'e sığdı.")
