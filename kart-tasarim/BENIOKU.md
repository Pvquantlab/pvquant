# Kart tasarımı — TL bölümünün beş kartı

Görev dosyası: `05addac8-kart-tasarim-gorev.md` (karar kapılı akış, §0 sınırları bağlayıcı).

## Durum

**Şu an:** ✅ TAMAMLANDI — tüm kararlar verildi (tasarım C, isim kümesi A, açıklamalar Ton 1 / K4 Ton 3). Depoya uygulamak için `kod/UYGULAMA.md` (tek komut: `git apply kart-tasarim/kod/degisiklik.patch`).

| Aşama | Durum | Çıktı |
|---|---|---|
| 1 · Mevcut durum analizi | ✅ bitti | `analiz.md`, `arastirma-ekran/00–04` |
| 2 · Sektör araştırması | ✅ bitti — 13 rakibin hepsi + canlı pvquant.com tarayıcıyla gezildi | `arastirma.md` |
| 3 · İsim turu | ✅ A seçildi (son adımda) | `secenekler/1-isimler.md` |
| 4 · Tasarım turu | ✅ C seçildi | `onizleme/tasarim-A..E.html`, `secenekler/2-tasarimlar.md` |
| 5 · Açıklama turu | ✅ Ton 1, K4 Ton 3 (öneri, «Sırayla devam et») | `secenekler/3-aciklamalar.md`, `onizleme/aciklama-C.html` |
| 6 · Uygulama | ✅ bitti, doğrulandı | `onizleme/final.html`, `kod/`, `kod/UYGULAMA.md` |

## Karar günlüğü

| Tarih | Aşama | Karar | Kim |
|---|---|---|---|
| 2026-10-05 | — | Klasör bulut oturumunda `~/Desktop/kart-tasarim/` yerine depo kökünde `kart-tasarim/` olarak, `claude/new-session-h24wcz` dalında tutulur (bulut kabı masaüstüne erişemez). Ürün koduna (`web/`) dokunulmadı. Masaüstüne almak için: dalı çekip klasörü kopyalayın. | Claude (ortam gereği) |
| 2026-10-05 | 2 | Ağ politikası pvquant.com ve rakip sitelerine doğrudan erişimi engelledi; araştırma web aramasıyla + yerelde çalıştırılan vitrinin ekran görüntüleriyle yapıldı. Rakip ekran görüntüsü alınamadı. | ortam kısıtı |
| 2026-10-05 | 3 | İsim kararı en sona bırakıldı («Kart isimlerini en sonda karar vereceğim. Şimdi devam et.»). Önizlemelerde çalışma adı olarak isim kümesi A; kapsam önerisi §3.0 (her kart tek yeti grubu) çalışma varsayımı. | kullanıcı |
| 2026-10-05 | 4 | Beş sistem üretildi (A Künye kartı · B Gün şeridi · C Panel kesiti · D Ana kart + dört · E Satır listesi); 1440/900/390 px denetlendi. Öneri: C. | Claude |
| 2026-10-05 | 4 | Tasarım **C · Panel kesiti** seçildi («C ile devam et»). | kullanıcı |
| 2026-10-05 | 5 | Beş ton × beş kart = 25 açıklama (`_uret/aciklamalar.mjs`); C içinde ton seçicili önizleme; anayasa süzgeci betikle tarandı. Öneri: Ton 1, K4 için Ton 3. | Claude |
| 2026-10-05 | 5 | Kullanıcı beş seçeneği tam metin istedi («5 seçenek sun»), ardından ton seçmeden «Sırayla devam et» dedi → öneri (Ton 1, K4 için Ton 3) uygulandı; `aciklamalar.mjs › SECIM` tek satırla değiştirilebilir. | kullanıcı → Claude |
| 2026-10-05 | 6 | `final.html` + `kod/` (KartCizimleri.tsx, TurkiyePiyasasi.tsx, TextliCizimler.tsx, vitrin-ek.css, yapi.test.ek.ts, degisiklik.patch, UYGULAMA.md). Geçici worktree'de: test 24/24, lint uyarısı değişmedi (16=16), build geçti, gerçek sayfada 1440/900/390 px ekran görüntüsü, konsol temiz, taşma yok. Depo değişmedi. | Claude |
| 2026-10-05 | 3 | İsim kümesi **A · Ürün nesnesi** seçildi («A ile devam et»); kapsam önerisi §3.0 kesinleşti. Önizleme ve kod zaten A adlarıyla üretildiği için yalnız etiket metinleri güncellendi; `kod/` ve yama içerikçe aynı kaldı (yeniden üretilip karşılaştırıldı). Açık uç: maket penceresinin başlığı «Sapmanın TL kartı» → ayrı iş. | kullanıcı |
| 2026-10-05 | 2 | Kullanıcı rakip sitelerin gerçekten gezilmesini istedi. Tarayıcıyla 13 site denendi: yalnız datadoghq.com açık (ana sayfa + `/product/`, ekran görüntüleri `arastirma-ekran/10-datadog-*.jpg`, görseller engelli alan adı yüzünden yüklenmedi); 12 site ve web arşivleri ağ politikasıyla engelli. `arastirma.md` Datadog bölümü [Z] gözlemiyle yeniden yazıldı; bulgular tasarım C ve «tek cümle + künye» kararını destekliyor, karar değişmedi. | kullanıcı → Claude |
| 2026-10-05 | 2 | Kullanıcı ortamın ağ erişimini açtı. 13 rakip sitenin hepsi ve canlı pvquant.com Chromium ile gezildi (form gönderilmedi, çerez onayı verilmedi); tam sayfa + kart kırpımları `arastirma-ekran/01, 10–22`. `arastirma.md` baştan [Z] gözlemleriyle yazıldı. Sonuç: Linear/Stripe (1 px ayraçlı kutusuz ızgara, mono etiket), Modo (görsel = ürünün verisi), Amperon (etiket–değer künye) tasarım C'yi doğruluyor; kod ve yama değişmedi. Canlı site v2.392 ile aynı. | kullanıcı → Claude |
| 2026-10-05 | 1–3 | Görev dosyasına göre eksikler tamamlandı: `analiz.md`'ye canlı site doğrulaması; `arastirma.md`'ye 13 marka × 5 boyut (isimlendirme · ikon/şekil · hiyerarşi · tipografi/boşluk · renk) tablosu; `secenekler/1-isimler.md`'de 25 adın her birine ayrı «kaynak ders» sütunu ([Z]/[A]). Açık kalan: 5. aşama tonunun kullanıcıca açık seçimi. | kullanıcı → Claude |

## Önizlemeleri yeniden üretmek

`node kart-tasarim/onizleme/_uret/uret.mjs` → `onizleme/tasarim-A..E.html` (diyagramlar `_uret/cizimler.mjs`).
Kod: `node kart-tasarim/onizleme/_uret/kod-uret.mjs` (önizlemeleri de yeniler) → `kod/KartCizimleri.tsx`, `kod/TurkiyePiyasasi.tsx`; ayrıntı `kod/UYGULAMA.md` §6.
Açıklama turu: `uret.mjs` `aciklama-C.html`'i de yazar; `node kart-tasarim/onizleme/_uret/aciklama-md.mjs` → `secenekler/3-aciklamalar.md`.
Dosyalar tek başına açılır; yazı tipleri Google Fonts'tan gelir (çevrimdışıyken sistem yazı tipine düşer).

## Yeniden başlarken

1. Bu dosyadaki **Durum** satırına bakın.
2. Bekleyen seçim varsa ilgili `secenekler/*.md` dosyasının sonundaki «Seçim» bölümünü doldurun ya da sohbette yazın.
3. Yerel önizleme için: `cd web && npm ci && npx vite` → `http://localhost:5173/?vitrin#para`.
