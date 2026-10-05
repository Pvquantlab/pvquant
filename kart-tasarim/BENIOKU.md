# Kart tasarımı — TL bölümünün beş kartı

Görev dosyası: `05addac8-kart-tasarim-gorev.md` (karar kapılı akış, §0 sınırları bağlayıcı).

## Durum

**Şu an:** 3. AŞAMA — İsim turu ⛔ DUR · kullanıcının seçimi bekleniyor (`secenekler/1-isimler.md`).

| Aşama | Durum | Çıktı |
|---|---|---|
| 1 · Mevcut durum analizi | ✅ bitti | `analiz.md`, `arastirma-ekran/00–04` |
| 2 · Sektör araştırması | ✅ bitti (sınırlı: bkz. not) | `arastirma.md` |
| 3 · İsim turu | ⛔ seçim bekleniyor | `secenekler/1-isimler.md` |
| 4 · Tasarım turu | — | `onizleme/tasarim-A..E.html`, `secenekler/2-tasarimlar.md` |
| 5 · Açıklama turu | — | `secenekler/3-aciklamalar.md` |
| 6 · Uygulama | — | `onizleme/final.html`, `kod/`, `kod/UYGULAMA.md` |

## Karar günlüğü

| Tarih | Aşama | Karar | Kim |
|---|---|---|---|
| 2026-10-05 | — | Klasör bulut oturumunda `~/Desktop/kart-tasarim/` yerine depo kökünde `kart-tasarim/` olarak, `claude/new-session-h24wcz` dalında tutulur (bulut kabı masaüstüne erişemez). Ürün koduna (`web/`) dokunulmadı. Masaüstüne almak için: dalı çekip klasörü kopyalayın. | Claude (ortam gereği) |
| 2026-10-05 | 2 | Ağ politikası pvquant.com ve rakip sitelerine doğrudan erişimi engelledi; araştırma web aramasıyla + yerelde çalıştırılan vitrinin ekran görüntüleriyle yapıldı. Rakip ekran görüntüsü alınamadı. | ortam kısıtı |

## Yeniden başlarken

1. Bu dosyadaki **Durum** satırına bakın.
2. Bekleyen seçim varsa ilgili `secenekler/*.md` dosyasının sonundaki «Seçim» bölümünü doldurun ya da sohbette yazın.
3. Yerel önizleme için: `cd web && npm ci && npx vite` → `http://localhost:5173/?vitrin#para`.
