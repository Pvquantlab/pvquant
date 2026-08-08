# PVQuant Rapor Motoru — Depo Entegrasyonu (Dalga E.1)

Doğrulama durumu (7 Ağu 2026, konteyner provası):
- `python3 uret.py` → 16/16 sayfa tek A4, taşma yok.
- Birleşik HTML **bayt-birebir** (md5 `8764…3001`), PDF görsel-birebir
  (piksel farkı yok; md5 farkı yalnız WeasyPrint zaman damgası).
- `denetim_uygulama.py` 12/12 ✓ (tek taban `taban_d.json` ile çapraz).

## Depoya yerleşim (github.com/Pvquantlab/pvquant)
    reporting/
      html/            ← motor (pvq.py, build_s01..s16.py, merge_html.py, uret.py)
        fontlar/       ← 6 TTF (OFL lisansları eklenecek)
        docs/          ← README, veri_haritasi, üretim kılavuzu
      denetim/         ← denetim_uygulama.py + taban_d.json

## Yapılacaklar (Mac'te)
1. Zip'i depo köküne aç, `reporting/` ağacını commit et.
2. `gereksinimler.txt` içeriğini (weasyprint>=62, pypdf>=4) ana
   requirements dosyasına ekle. wkhtmltopdf KULLANILMAZ (kılavuz §9).
3. Prova: `cd reporting/html && python3 uret.py` → "Tüm sayfalar tek
   A4'e sığdı" beklenir; ardından
   `python3 ../denetim/denetim_uygulama.py cikti/*.pdf ../denetim/taban_d.json`.
4. CI adımı (öneri): üret + "1 sayfa" satır sayısı 16 mı + denetim
   12/12 mi — üçü de yeşilse mühür.

## Dalga E.2 (sıradaki, ayrı mühür)
- `veri.py` konsolidasyonu: 16 build dosyasına dağılmış sabit verinin
  tek modüle toplanması (motor README'sinin önerdiği ilk adım).
- JSON v2.0 → `veri.py` adaptörü (`veri_haritasi.md` alan eşlemesiyle);
  şema v2.1 ihtiyaçları: `report.customer`, `sources.weather.model/
  version`, `accuracy.skill_basis`, `hourly[].band_method`.
- Rapor üretimini `report_service.py`'ye bağlama (run sonrası otomatik).

## Bilinen küçük pürüzler (kozmetik, E.2'de)
- PDF'e DejaVu Serif/Sans-Bold sızıyor: "Σ", "✓" gibi kalın glifler
  Plex/Source Serif alt-kümesinde yok; ya glif kapsamı genişletilir
  ya karakterler değiştirilir.
- S7 grafiği "ortalama %39" etiketi; hesap %38,5 → "%38,5" basılması
  veya yuvarlama kuralının sabitlenmesi önerilir (S3 metni %38 diyor,
  pencereler farklı: 120 gün vs son 30 gün — kasıt notu eklenebilir).

## Dondurulan hat
Word/docx şablonu (Rev D.1) tasarım referansı olarak arşivde kalır;
ürün çıktısı bu HTML/WeasyPrint hattıdır. (Onay bekliyor.)


## Dalga E.2 Adım 3a — köprü (v2.101 adayı)
- `reporting/kopru.py`: uygulama→motor tek kapı. `json_ile_uret(json)` üretir,
  iki bekçi koşar (16 sayfa + denetim çıkış 0), yolları döner. Konteyner ispatı:
  kanonik JSON → md5 `8764…c001`; bozuk günlükle çıkış 1 (denetim 2 fark).
- `reporting/report_html_service_taslak.py`: ctx→JSON v2.1 eşlemesi; **DB'ye karşı
  test edilmedi**. Yerleşim: `src/pvquant/services/report_html_service.py`.
  Boşluk defteri başlıkta (B1–B7); eksikler sessizce Konya'ya düşmez, ValueError.
- CI adımı (3b): `python3 reporting/kopru.py reporting/html/ornek_girdi_v21.json` —
  "RAPOR HAZIR" + çıkış 0 mühür koşuludur.
