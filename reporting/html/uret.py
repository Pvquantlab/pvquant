"""Tüm raporu tek komutla üretir: 16 sayfa + birleşik HTML/PDF.

    python3 uret.py

Çıktılar PVQ_CIKTI (varsayılan: ./cikti) altına yazılır.
Bir sayfa taşarsa uyarı basılır ve çıkış kodu 1 olur — CI adımı olarak kullanılabilir.
"""
import runpy, sys, io, contextlib, os

# ---- İç tutarlılık denetimi: HERHANGİ bir sayfa üretilmeden ÖNCE (v2.128).
# Tek bir "hata" bulgusu rapor üretimini durdurur; bozuk rapor hiç yazılmaz.
# Bulgular her koşuda cikti/denetim.json'a da yazılır (geçen/geçmeyen ayrımı).
import veri, denetim
from pvq import OUT

_kayitlar, _bulgular, _bayrak = denetim.denetle_tam(veri)
denetim.json_yaz(_kayitlar, _bayrak, os.path.join(OUT, "denetim.json"))
for _b in _bulgular:
    print("[%s] %s — %s | beklenen: %s | bulunan: %s"
          % (_b.seviye.upper(), _b.kod, _b.mesaj, _b.beklenen, _b.bulunan))
if _bayrak:
    print("[BAYRAK] ŞÜPHELİ KALİBRASYON işareti kaldırıldı (denetim.json).")
_hatalar = [_b for _b in _bulgular if _b.seviye == "hata"]
if _hatalar:
    print("\nDENETİM BAŞARISIZ: %d hata — rapor üretilmedi. Ayrıntı: %s"
          % (len(_hatalar), os.path.join(OUT, "denetim.json")))
    sys.exit(1)
print("Denetim: %d kontrol geçti (%d uyarı). Sayfa üretimi başlıyor."
      % (sum(1 for k in _kayitlar if k["durum"] == "gecti"),
         sum(1 for k in _kayitlar if k["durum"] == "uyari")))

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
# ---- Render denetimi (v2.135): birlesimden ONCE — doldurulmamis token,
# s02/s15 sayfa referanslari. Ihlal -> birlesim yok, rc=1.
_rb = denetim.render_denetle(OUT)
for _b in _rb:
    print("[%s] %s — %s | beklenen: %s | bulunan: %s"
          % (_b.seviye.upper(), _b.kod, _b.mesaj, _b.beklenen, _b.bulunan))
if _rb:
    print("\nRENDER DENETIMI BASARISIZ: %d bulgu — birlesim yapilmadi." % len(_rb))
    sys.exit(1)
runpy.run_module("merge_html", run_name="__main__")

if sorunlu:
    print("\nTAŞAN SAYFALAR:", ", ".join(sorunlu))
    sys.exit(1)
print("\nTüm sayfalar tek A4'e sığdı.")
