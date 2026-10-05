# Kart tasarımı — TL bölümünün beş kartı

Görev dosyası: `05addac8-kart-tasarim-gorev.md` (karar kapılı akış, §0 sınırları bağlayıcı).

## Durum

**Şu an:** 4. AŞAMA — Tasarım turu ⛔ DUR · kullanıcının tasarım seçimi bekleniyor (`secenekler/2-tasarimlar.md`, `onizleme/tasarim-A..E.html`). İsim seçimi (3. aşama) kullanıcı kararıyla en sona ertelendi.

| Aşama | Durum | Çıktı |
|---|---|---|
| 1 · Mevcut durum analizi | ✅ bitti | `analiz.md`, `arastirma-ekran/00–04` |
| 2 · Sektör araştırması | ✅ bitti (sınırlı: bkz. not) | `arastirma.md` |
| 3 · İsim turu | ⏸ ertelendi (en sonda seçilecek) | `secenekler/1-isimler.md` |
| 4 · Tasarım turu | ⛔ seçim bekleniyor | `onizleme/tasarim-A..E.html`, `secenekler/2-tasarimlar.md` |
| 5 · Açıklama turu | — | `secenekler/3-aciklamalar.md` |
| 6 · Uygulama | — | `onizleme/final.html`, `kod/`, `kod/UYGULAMA.md` |

## Karar günlüğü

| Tarih | Aşama | Karar | Kim |
|---|---|---|---|
| 2026-10-05 | — | Klasör bulut oturumunda `~/Desktop/kart-tasarim/` yerine depo kökünde `kart-tasarim/` olarak, `claude/new-session-h24wcz` dalında tutulur (bulut kabı masaüstüne erişemez). Ürün koduna (`web/`) dokunulmadı. Masaüstüne almak için: dalı çekip klasörü kopyalayın. | Claude (ortam gereği) |
| 2026-10-05 | 2 | Ağ politikası pvquant.com ve rakip sitelerine doğrudan erişimi engelledi; araştırma web aramasıyla + yerelde çalıştırılan vitrinin ekran görüntüleriyle yapıldı. Rakip ekran görüntüsü alınamadı. | ortam kısıtı |
| 2026-10-05 | 3 | İsim kararı en sona bırakıldı («Kart isimlerini en sonda karar vereceğim. Şimdi devam et.»). Önizlemelerde çalışma adı olarak isim kümesi A; kapsam önerisi §3.0 (her kart tek yeti grubu) çalışma varsayımı. | kullanıcı |
| 2026-10-05 | 4 | Beş sistem üretildi (A Künye kartı · B Gün şeridi · C Panel kesiti · D Ana kart + dört · E Satır listesi); 1440/900/390 px denetlendi. Öneri: C. | Claude |

## Önizlemeleri yeniden üretmek

`node kart-tasarim/onizleme/_uret/uret.mjs` → `onizleme/tasarim-A..E.html` (diyagramlar `_uret/cizimler.mjs`).
Dosyalar tek başına açılır; yazı tipleri Google Fonts'tan gelir (çevrimdışıyken sistem yazı tipine düşer).

## Yeniden başlarken

1. Bu dosyadaki **Durum** satırına bakın.
2. Bekleyen seçim varsa ilgili `secenekler/*.md` dosyasının sonundaki «Seçim» bölümünü doldurun ya da sohbette yazın.
3. Yerel önizleme için: `cd web && npm ci && npx vite` → `http://localhost:5173/?vitrin#para`.
