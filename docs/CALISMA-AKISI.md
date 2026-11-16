# PVQuant çalışma akışı standardı (16.11.2026)

Amaç: küçük düzeltmelerin her birinde tam kod taraması, tam test takımı, ayrı commit ve ayrı dağıtım döngüsüne girmeden; güvenlik, veri bütünlüğü ve kritik işlev kontrollerinden ödün vermeden **parti halinde** ilerlemek. Mühür ritüeli (CLAUDE.md) değişmedi; bu belge mührün **önündeki** çalışmayı düzenler.

## 1. Üç kademe

| Kademe | Ne zaman | Ne koşar | Süre |
|---|---|---|---|
| **Hızlı** | her düzenleme sonrası | `scripts/kontrol.sh hizli` → `tsc -b`, web testleri (node:test, ~2 sn), değişen Python dosyasının eşleşen `tests/test_<ad>*.py` dosyaları | 10–40 sn |
| **Tam** | parti kapanırken (bir ekran / bir konu bitti) | hızlı + `vite build` + `oxlint` (taban 16) + ruff HEAD kıyası (değişen Python dosyalarında yeni kural kodu yok) | 1–2 dk |
| **Mühür** | kullanıcı «commitle / gönder» dediğinde, partide bir kez | tam + Python değiştiyse tam pytest (test DB, sahip rolü) **ve** CI taklidi (`TZ=UTC`, `pvq_api` rolü) → Türkçe commit → push → CI tarayıcıdan → ssh dağıtım (yalnız değişen servisler) → healthz/readyz → defter | 20–35 dk |

Python değişmediyse mühürde tam pytest **atlanır**; CI zaten koşar. Web değişmediyse web adımları atlanır.

## 2. Parti disiplini

1. **Önce envanter, sonra düzenleme.** Aynı türden sorunları (ör. satır içi punto, ham kod gösterimi, kısa ayraç çizgisi) tek seferde grep / `denetim.mjs` ile dök; tek tek rastladıkça düzeltme.
2. **Mekanik dönüşüm betikle.** 20'den çok yerde aynı değişiklik varsa Python/regex betiği, kuru çalışma sayımı, sonra uygulama; elle dosya dosya gezme yok.
3. **Bağlam yeniden okunmaz.** Oturum içinde bir kez okunan bileşen/CSS tekrar okunmaz; `git diff -U0` ile yalnız değişen satırlara bakılır.
4. **Doğrulama hedefli.** Düzenleme sırasında yalnız hızlı kademe. Kare (`kare.mjs`) ve hesaplanmış stil taraması parti sonunda, iki temada, 1440 + 375.
5. **Örnek API yeniden başlatma** yalnız `sahte-api-panel.mjs` değiştiyse; web paketi `dist-sahte` yeniden derlenir, `vite preview` yeniden başlatılmaz (diskten okur).
6. **Tek commit, tek dağıtım.** Parti = bir `vN.NNN` commit'i (NE / NEDEN / KANIT) + bir dağıtım + bir defter kaydı. Rötuş başına mühür yok.
7. **Canlıya dokunma.** Üretim veritabanına yalnız `BEGIN READ ONLY`; dağıtım yalnız açık istekle; worker 04:00–08:30 TSİ penceresinde yeniden yaratılmaz.

## 3. Değişmeyen zorunlu kontroller

- Güvenlik: `tests/test_faz9_guvenlik_matrisi.py` (uç envanteri, kiracı izolasyonu), `test_db_rolu.py` (yetki pinleri), dil bekçisi `web/test/panel/dil.test.ts`.
- Veri bütünlüğü: `test_db_rolu` değişmez tablo pinleri; göç varsa DB sahibiyle, mühürden önce test DB'de.
- Çekirdek sınırı: `docs/CEKIRDEK-SINIRI.md` alanlarına (tahmin, uzlaştırma formülleri, kalibrasyon, şema) dokunan değişiklik parti dışı, ayrı onay.

## 4. Tipografi kuralı (16.11 partisiyle geldi)

Satır içi sayısal punto **yazılmaz**; jeton kullanılır: `--t-baslik 28 · --t-bolum 21 · --t-kart 16 · --t-govde 15 · --t-tablo 14 · --t-veri 14 (mono veri) · --t-ikincil 13,5 · --t-kod 13 · --t-tablo-dar 13 · --t-etiket 12,5 · --t-kucuk 12`. İkincil metnin tek boyu 13,5'tir (eskiden 13 / 13,5 / 14 arasında geziyordu). **Tek aile (16.11 ikinci parti):** panelde başlık/KPI/gövde/tablo/grafik ekseni Inter Variable; `body` düzeyinde `tabular-nums`; `.mono` sınıfı VERİ rolüdür ve gövde ailesindedir. Plex Mono yalnız kod, API anahtarı, kimlik ve kısayol (`.kod`, `.cip-kod`, `.kod-duz`, `.plat-anahtar`, `.girdi.mono`, `kbd`). Inter Tight yalnız vitrin. Hash/kimlik/SHA değerleri `.kimlik` sınıfı alır (`.kunye-sayi` sayı içindir). Grafik (ECharts) seçenek nesnelerindeki sayısal puntolar bu kuralın dışında (kütüphane sayı ister).

## 5. Bir partinin akışı (kontrol listesi)

- [ ] Envanter: grep / tarama → bulgu listesi, aynı türdekiler gruplanır
- [ ] Kuru çalışma: dönüşüm betiği sayım verir, beklenmeyen eşleşme yok
- [ ] Uygulama + `scripts/kontrol.sh hizli`
- [ ] Parti sonu: `scripts/kontrol.sh tam` + kare iki tema (1440, 375) + örnek kipte tıklama kontrolü
- [ ] Rapor (Türkçe): doğrulanan / reddedilen / uygulanan / dosyalar / testler / kalan
- [ ] Kullanıcı «gönder» → `scripts/kontrol.sh muhur` → mühür ritüeli
