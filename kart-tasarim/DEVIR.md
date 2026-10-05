# Devir notu — TL bölümü kartları (sonraki oturum / başka bir asistan için)

Bu klasör, pvquant.com ana sayfasındaki TL bölümünün («Tahmin hatasının maliyetini TL olarak görün.»)
beş kartını yeniden tasarlama işinin **tamamlanmış** çıktısıdır. Kararların hepsi verildi; geriye
yalnız depoya uygulama ve canlıya çıkarma kaldı.

## Kısa özet

- **Depo:** `Pvquantlab/pvquant` · vitrin kodu `web/src/features/vitrin/`
- **Seçilen tasarım:** C · Panel kesiti (beş kart tek beyaz yüzeyin 1 px çizgiyle bölünmüş hücreleri)
- **Kart adları (küme A):** Teslim programı · Sapma maliyeti · Şablonlu dışa verim · Alarm kütüphanesi · Gün içi aralık
- **Açıklamalar:** Ton 1 («fayda önce»), Alarm kütüphanesi için Ton 3
- **Kapsam:** her kart tek bir ürün yetisini anlatır, tekrar yok; yalnız bu beş kart değişir
- **Kurallar:** mavi = tahmin, amber = yalnız gerçekleşen üretim; uydurma sayı, müşteri iması,
  yöntem/kaynak adı yok (vitrin testleri bunu zorlar)

## Depoya hazır değişiklik

`kod/degisiklik.patch` — depo kökünde tek komutla uygulanır:

```bash
git apply kart-tasarim/kod/degisiklik.patch
cd web && npm test && npx oxlint && npm run build
```

Ayrıntı ve dosya dosya liste: `kod/UYGULAMA.md`. Yama `main` (v2.392) üzerinde temiz uygulanıyor;
ayrı bir kopyada doğrulandı: test 24/24, lint'te yeni uyarı yok, build geçti, gerçek sayfada
1440/900/390 px ekran görüntüsü alındı (`onizleme/ekran/final-vitrin-*.jpg`).

## Sırada ne var (öneri)

1. Yamayı uygula, testleri çalıştır, deponun sürüm düzeniyle commit et
   (ör. «v2.393 — TL bölümü kartları: panel kesiti») ve `main`'e gönder; CI test/build/lint çalıştırır.
2. Canlıya çıkış otomatik değil: `KONUSLANDIRMA.md`'ye göre `web` imajı yeniden kurulup başlatılmalı.
3. **Açık uç:** kartların üstündeki maket penceresi hâlâ «Sapmanın TL kartı» diyor; kart adı artık
   «Sapma maliyeti». Pencere başlığı (ve `aria-label`'ı) ayrı bir küçük işte «Sapma maliyeti» yapılmalı.
4. İsteğe bağlı temizlik: `vitrin.css`'te artık kullanılmayan eski kart stilleri
   (`.vt-vin-kart`, `.vt-masalar`, `.vt-v-genis`, `.vt-v-dar`, `.vt-sss-yer .vt-vin`).

## Bilinen sınırlar

- Rakip araştırması, ortamın ağ politikası siteleri engellediği için web aramasıyla yapıldı;
  rakiplerin ekran görüntüsü yok (`arastirma.md` başındaki not).
- Açıklama tonu kullanıcı tarafından açıkça seçilmedi («Sırayla devam et» dendi); öneri uygulandı.
  Değiştirmek için `onizleme/_uret/aciklamalar.mjs › SECIM`, ardından
  `node kart-tasarim/onizleme/_uret/kod-uret.mjs`.

## Klasör haritası

| Yol | İçerik |
|---|---|
| `BENIOKU.md` | durum + tarihli karar günlüğü |
| `analiz.md` · `arastirma.md` · `arastirma-ekran/` | 1–2. aşama: mevcut durum teşhisi, sektör dersleri |
| `secenekler/1-isimler.md` · `2-tasarimlar.md` · `3-aciklamalar.md` | 25 ad, 5 tasarım, 25 açıklama ve seçimler |
| `onizleme/tasarim-A..E.html` · `aciklama-C.html` · `final.html` | tarayıcıda açılan önizlemeler |
| `onizleme/ekran/` | önizleme ve gerçek sayfa ekran görüntüleri |
| `onizleme/_uret/` | önizlemeleri ve kodu üreten betikler (tek kaynak) |
| `kod/` | depoya hazır dosyalar, `degisiklik.patch`, `UYGULAMA.md` |
