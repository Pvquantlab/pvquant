# Örnek: ilk tam rubrik turunun gerçek bulguları (Mühür E, v2.399)

Tur kapsamı: Portföy/Veri/Tahminler/Raporlar (1440, koyu) + Doğruluk/Kalibrasyon/Santralım/
Aylık (önceki mühür kareleri) + vitrin mobil. Yargıç çıktısı biçimi: madde → kanıt → fix.

## KALDI → düzeltildi (aynı mühürde)

1. **Kırpılan metin (madde 15 ailesi):** Portföy «Bugün beklenen · yarın» KPI'ı 1440'ta bile
   «24,5 MWh · 27,0 M» diye kesiliyordu (kpi-dg nowrap + çift birimli uzun değer).
   **Fix:** iki değer aynı ölçekteyse birim TEK kez sonda — «24,5 · 27,0 MWh» (Portfoy.tsx).
   Ders: nowrap kesilmeyi gizlemez, sadece taşırır; çift değerli KPI'da birim tekrarı yasak.
2. **Çelişkili boş durum (madde 16):** aynı sayfada WMAPE «—» iken altı «0,00 MWp karneli»
   yazıyordu — tire «yok» derken alt metin ölçüm iddia ediyordu.
   **Fix:** değer yokken alt da dürüst: «karne birikmedi — eşleşmiş gün yok».
3. **Dokunma hedefi (madde 12/a11y):** `.vt-disiplin__bag { min-height:0 }` tabanın 44 px
   dokunma hedefini eziyordu. **Fix:** ezme kaldırıldı (vitrin.css).
   Tarama betiği de iki YANLIŞ POZİTİF sınıfı öğrendi: (a) WCAG 2.5.8 satır içi istisnası
   (p/li/td/dd içindeki bağ), (b) `::before{position:absolute;inset:0}` «kartın tamamı
   tıklanabilir» hilesi — gerçek hedef karttır, eleman kutusu ölçülmez.

## En zayıf 3 (geçti ama aday — rubrik «hepsi geçti» yasağı)

- **Raporlar sayfasında hiç primary eylem yok** (5 eş outline «Hazırla») — hiyerarşi düz;
  16 sayfalık müşteri raporu primary adayı. Ürün kararı ister; dalga-3.
- **Vitrin mobilde çift dolu CTA** (nav + hero «Karnenizi başlatın») — bilinçli pazarlama
  kalıbı (sticky nav CTA); madde 4'ün kayıtlı istisnası, değiştirilmedi.
- **Portföy tablosunda karışık enerji birimi** (Konya MWh satırının altında Kosusuz Lab
  «3.501 kWh») — enerjiTr ölçekle yazıyor (dürüst) ama sütun başlığı birimsiz; aday:
  başlığa «(ölçekli)» ibaresi ya da satır içi birim vurgusu. Dalga-3.

Kanıt kareleri: scratchpad mE/ (portfoy-ust = öncesi, portfoy-duzeltilmis = sonrası).
