# Yönetici paneli görsel uyum turu — 26.10.2026 (yerel, commit edilmedi)

Müşteri paneli tasarım referansı alındı; /yonetim yüzü aynı jeton ve bileşen diline oturtuldu. İş mantığı, API, veri akışı
dokunulmadı; müşteri paneli CSS kuralları değişmedi (ölçümle doğrulandı, aşağıda).

## Değişen dosyalar (7 + 1 araç)
- `web/src/index.css` — platform yüzü: vurgu jetonu ailesi `--plat-vurgu*` (`--marka*` yuvalarına bağlı; sabit hex kalktı),
  `.rozet-ok` metni `--marka-koyu` (4,2 → 7,2:1), `.zaman` gövde ailesi + tabular (mono kalktı), tabloda `.cip-kod` = `.kod` dili
  (mono 12,5 px, hafif zemin, 6 px köşe), `.plat-rozet-sari` saydamlık yerine amber jetonu (8,5:1), ≤560 px kart başlığı sağ yuvası
  sarar / sayaç çipi tek parça.
- `web/src/features/yonetim/sayfalar.tsx` — `rozet-kucuk` kalktı (tablo rozeti müşteriyle aynı 12,5 px); Denetim izi ve
  Kullanıcılar süzgeç formları kartın içine (müşteri panelinde form hep kart içinde; Sistem/İş kayıtları ile aynı kalıp).
- `web/src/features/yonetim/Sistem.tsx` — zaman/sayı hücrelerinde `mono` kalktı, iki tablo `veri sayisal` (tabular), satır içi
  13,5 px punto kalktı (ortak 14 px); hata ayrıntısı (teknik metin) mono kaldı.
- `web/src/features/yonetim/Kullanim.tsx` — künye `dd` ve gün sütunu mono kalktı (kunye zaten tabular).
- `web/src/features/yonetim/Planlar.tsx` — etiket + birim tek satır (flex sütununda birim ayrı satıra düşüyordu).
- `web/src/features/yonetim/ortak.tsx` — `LimitRozet` tam boy rozet.
- `web/test/panel/yonetim.test.ts` — iki pin güncellendi (`--plat-vurgu`, `.zaman` gövde ailesi), yeni «görsel uyum» bekçisi
  (mono yalnız kimlik/IP/kod/hata, rozet tam boy, formlar kart içinde, jetonlar, müşteri kuralları değişmedi).
- `.claude/skills/pvquant-tasarim/betikler/iki-panel-olcum.mjs` — YENİ: iki panelde hesaplanmış stil + yazı tipi histogramı +
  taşma + kare (Playwright channel chrome; sahte API 4807 + vite preview 4273).

Mono bilerek KALAN yerler: üst çubuk tarihi (müşteriyle aynı `.mono ust-tarih`), IP, kısaltılmış tenant/nesne kimliği, eylem/iş
kodu çipi, iş hatası ayrıntısı, denetim ayrıntı çipleri (müşteri Kuruluş sayfasıyla ortak bileşen), tek seferlik anahtar/bağlantı.

## Üç doğrulama aşaması — gerçek sonuçlar
Düzenek: sahte API (`PLATFORM_2FA=1`, :4807) + `VITE_API_URL` ile üretim derlemesi `vite preview` :4273; Chrome (Playwright channel);
müşteri paneli örnek kip koyu tema, platform sahte sahip jetonu. Önce/sonra aynı betikle.

**1. Görsel kontrol (1440 px, 5 müşteri + 10 platform sayfası, 30 seçici)** — önce ölçülen farklar ve sonrası:
| Öğe | Önce (platform) | Sonra | Müşteri referansı |
|---|---|---|---|
| `.zaman` | IBM Plex Mono 500 13 px | Inter Variable 14 px tabular | Ekip «Son giriş»: Inter 14 px |
| tablo `.rozet` | 11,5 px, metin #5B8DEF (4,25:1) | 12,5 px / 24 px, metin #9DBBFF (7,18:1) | 12,5 px / 24 px |
| tablo `.cip-kod` | çıplak mono 13 px, 22 px | mono 12,5 px, zemin .07, 6 px köşe | `.kod` satır içi kod |
| mono metin düğümü (Sistem / Genel bakış / Müşteriler) | 45 / 21 / 7 | 9 / 16 / 1 | Ayarlar 8 (API anahtarları) |
| h1, kart h3, kart-alt, kpi, girdi, girdi-etiket, dugme, nav, ust, yan, body, icerik | — | birebir aynı | — |
Müşteri paneli: 5 sayfa × 30 seçici hesaplanmış stil + yazı tipi histogramı önce/sonra **birebir** (fark 0).
Kontrast (koyu yüz, hesaplandı): metin 17,2 · ikincil 11,7 · soluk 7,3 (kart) / 8,2 (zemin) · rozet-ok 7,2 · rozet-uyarı 6,7 ·
rozet-nötr 9,6 · PLATFORM rozeti 7,8 · nav aktif 7,6 · amber limit rozeti 8,5 · KPI uyarı 7,0 — hepsi AA (≥4,5) üstünde;
yüzey kademeleri zemin #0B0E15 / yan #10131B / kart #181B23 (saf siyah yok; müşteri koyu yüzüyle aynı jetonlar).

**2. Responsive kontrol (375 / 768 / 1024 / 1440 / 1920)** — 15 sayfa × 5 genişlik = 75 ölçüm (platform 50): yatay taşma **0**,
kalan iskelet 0, `role=alert` 0, sayfa hatası 0 (konsoldaki 404/500'ler sahte API'nin müşteri örnek kipi uçları; platforma ait
değil). 375'te bulunan ve düzeltilen: İş kayıtları başlığındaki «5 kayıt | 1 hata» çipi sözcük sözcük dikey kırılıyordu → kart
başlığı sarar, çip tek parça (ikinci ölçümle doğrulandı). Platform giriş ekranı 375/1440: taşma 0, aynı giriş tipografisi.

**3. Son doğrulama** — tüm platform sayfaları yeniden tarandı (yukarıdaki 50 ölçüm son derlemeyle); kapılar:
`tsc -b` 0 hata · `npm run build` tamam · web testleri **99/99** (yeni bekçi dahil) · oxlint 16 uyarı / 0 hata (taban).
pytest koşulmadı: Python tarafında değişiklik yok (yalnız web/ ve betik).

## Çalıştırılamayan / kapsam dışı
- 2FA kurulum ekranı (IkiAdimKurulum) karede yok: sahte API `PLATFORM_2FA=1` ile koşuldu (panelin açılması için); ekran CSS'i
  giriş ekranıyla ortak (`.giris-*`), kodu değişmedi.
- Müşteri panelinin Kuruluş denetim tablosu zamanları hâlâ mono (`className="mono"`); müşteri paneli bu turda bilerek
  değiştirilmedi — istenirse aynı kesime (gövde tabular) alınır.
- Firefox/WebKit koşulmadı (yalnız Chrome); açık tema platformda yok (yüz koyu sabit, tasarım kararı).
