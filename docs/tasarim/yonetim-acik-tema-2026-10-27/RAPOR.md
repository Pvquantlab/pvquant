# Yönetici paneli (/yonetim) açık tema adayları — 27.10.2026 (KARAR BEKLİYOR; commit edilmedi)

Üç aday yalnız **önizleme anahtarıyla** görünür; anahtar yoksa platform bugünkü gibi koyu. Müşteri paneli ve koyu yüz dokunulmadı.
- Denemek (yerel dev sunucu, gerçek veri): `http://localhost:5173/yonetim?onizleme=warm` · `…=slate` · `…=pearl` · `…=kapali` (siler).
- Kod: `web/src/index.css` sonundaki «PLATFORM AÇIK TEMA ÖNİZLEMESİ» bloğu (yalnız jeton değerleri) + `Yonetim.tsx` `onizlemePaleti()`.
- Kareler (sahte API, Chrome): `warm/ slate/ pearl/ koyu/` altında Genel bakış · Sistem · Denetim izi × 1440/375; yan yana `karsilastirma-*.png`.

## Ortak ilkeler (üç palette aynı)
Saf beyaz yok (kart en açık #FBFAF7); müşteri açık yüzü kalıbı **zemin < yan < kart**, kart/zemin ≥ 1,15; metin üçlüsü (metin / ikincil /
soluk) hepsi AA üstü; platform laciverti açık yüzde mürekkep tonuna iner (tint üstü metin ≥ 6:1); uyarı/amber tonları müşteri açık
temasıyla aynı (#B8421F / #9A5C07); tipografi, rozet (Inter Tight 500 12,5 px / 26 px hap), kart (12 px köşe, 22×24 px dolgu), tablo
(14 px, 10 px satır) ve boşluklar koyu yüzle birebir — yalnız renk jetonları değişir.

## HEX paletler
| Jeton | Soft Warm | Cool Slate | Neutral Pearl |
|---|---|---|---|
| `--zemin` (ana arka plan) | #ECE8DF | #E6EAF0 | #E9E9EC |
| `--yan` (yan menü, üst çubuk) | #F3F0EA | #EEF1F5 | #F1F1F3 |
| `--kart` | #FBFAF7 | #F8F9FB | #FAFAFB |
| `--yuzey` / `--yuzey2` (iç yüzey, hover) | rgba(46,38,26,.05/.09) | rgba(20,30,48,.05/.09) | rgba(18,18,22,.05/.09) |
| `--kenar` | #DCD6CA | #D2D8E1 | #D7D7DC |
| `--izgara` (tablo çizgisi) | rgba(46,38,26,.11) | rgba(20,30,48,.11) | rgba(18,18,22,.11) |
| `--metin` / `--ikincil` / `--soluk` | #1E1A14 / #4A443B / #675F54 | #141B29 / #3B4556 / #5B6679 | #161619 / #404248 / #60636B |
| `--plat-vurgu` (odak, mürekkep) | #3D6BCB | #3366CC | #3C63C2 |
| `--plat-vurgu-acik` (tint üstü metin: nav aktif, rozet-ok, PLATFORM rozeti, avatar) | #2A52A8 | #244FA6 | #2B4C9E |
| `--marka-zemin` / `--yan-aktif` | rgba(61,107,203,.12/.13) | rgba(51,102,204,.12/.13) | rgba(60,99,194,.12/.13) |
| `.dugme-ana` | zemin #1E1A14, yazı #FBFAF7 | #141B29 / #F8F9FB | #161619 / #FAFAFB |
| rozet-uyarı / amber / nötr | #B8421F on #FBEEEA · #9A5C07 on #FDF1DE · ikincil on yuzey | aynı | aynı |

## WCAG kontrast (hesaplandı; metin ≥4,5, UI ≥3)
| Çift | Warm | Slate | Pearl |
|---|---|---|---|
| metin / kart | 16,6 | 16,4 | 17,3 |
| ikincil / kart | 9,2 | 9,2 | 9,6 |
| soluk / kart | 6,0 | 5,5 | 5,8 |
| soluk / zemin | 5,1 | 4,8 | 5,0 |
| soluk / yan | 5,5 | 5,1 | 5,3 |
| vurgu metni / tint (rozet-ok, avatar) | 6,0 | 6,2 | 6,5 |
| nav aktif metni / yan-aktif | 5,1 | 5,3 | 5,6 |
| PLATFORM rozeti / tint-yan | 5,2 | 5,4 | 5,6 |
| vurgu mürekkebi / kart (odak halkası, UI) | 4,8 | 5,1 | 5,4 |
| uyarı metni / uyarı zemini · / kart | 4,8 · 5,2 | 4,8 · 5,2 | 4,8 · 5,3 |
| amber metni / amber zemini | 4,8 | 4,8 | 4,8 |
| nötr rozet ikincil / yuzey | 8,4 | 8,3 | 8,7 |
| dugme-ana yazı / zemin | 16,6 | 16,4 | 17,3 |
| kart / zemin (yüzey ayrımı, hedef ≥1,15) | 1,17 | 1,15 | 1,16 |
| kenar / kart | 1,39 | 1,36 | 1,37 |
Hepsi geçer; en düşük metin oranı Slate soluk/zemin 4,8 (AA üstü).

## Ölçüm
3 palet × 3 sayfa × 1440/375: yatay taşma 0, `role=alert` 0, sayfa hatası 0; `data-tema=acik` + `data-palet` doğru uygulandı
(`rapor.json`). Kapılar: `tsc -b` 0, web testleri 100/100, oxlint 16/0 (taban). Önizleme anahtarı olmadan koyu yüz birebir
(`koyu/` kareleri). pytest koşulmadı (Python değişmedi).

## Karşılaştırma
| Ölçüt | Soft Warm | Cool Slate | Neutral Pearl |
|---|---|---|---|
| Okunabilirlik | en yüksek soluk-metin oranı (6,0) | iyi (5,5) | iyi (5,8) |
| Göz konforu (uzun kullanım) | en yumuşak; bej-gri kâğıt hissi | serin; parlaklık dengeli | nötr; en «sessiz» |
| Kurumsal SaaS kalitesi | sıcak, editoryal; enerji sektöründe az görülen bir ton | B2B SaaS standardı; lacivert vurguyla aynı aile | temiz ama müşteri açık temasına en yakın |
| Koyu yüzle akrabalık | zayıf (koyu yüz serin lacivert) | güçlü (aynı mavi aile) | orta |
| Müşteri panelinden ayırt edilme (yanlış pencere riski) | güçlü (sıcak ton hemen fark edilir) | güçlü (mavi-gri) | zayıf (#E9E9EC ≈ müşterinin #E8EAEE) |
| Uyarı/amber tonlarıyla uyum | kırmızı/amber bej üstünde biraz sıcak yığılır | iyi, kırmızı net ayrışır | iyi |

## Öneri: **Cool Slate**
Gerekçe: (1) platform kimliği zaten lacivert vurgu — Slate'in gri-mavi yüzeyi aynı aileden, koyu yüzle geçiş doğal; (2) müşteri açık
temasından (nötr gri) açıkça ayrışır, yanlış pencerede işlem riski için ilk bakışta fark edilir (Pearl bunu sağlamaz); (3) uyarı
kırmızısı ve amber serin zemin üstünde en temiz ayrışır (Warm'da sıcaklar yığılır); (4) tüm oranlar AA üstü, kart/zemin 1,15 eşikte —
istenirse zemin bir ton koyulaştırılarak (#E2E7EE) 1,18'e çekilir. İkinci seçenek: Soft Warm — en konforlu ve en okunur; koyu yüzle
akrabalığı zayıf olduğu için tek başına «platform = açık, sıcak» kararıyla anlamlı.

## Seçimden sonra
Seçilen blok `:root[data-yuz="platform"]` açık yüz jetonlarına taşınır, diğer iki blok ve önizleme anahtarı silinir, tema üçlüsü (oto/açık/koyu)
platform üst çubuğuna eklenir (müşteri Kabuk kalıbı), `jetonlar.md`'ye platform açık yüz satırı, bekçi testleri, 5 genişlik taraması, mühür.

## Ek (27.10 akşam) — 4. aday: Claude Ivory (kullanıcı isteği)
claude.ai açık yüzünün fildişi zemini birebir: `--zemin #F0EEE6` (ivory medium) · `--yan #F5F4EE` · `--kart #FAF9F5` (ivory light) ·
`--kenar #DDD9CE` · metin #1F1E1D / #45443F / #66645E · yuzey rgba(31,30,29,.05). Vurgu platform laciverti (#3D6BCB / #2A52A8) kalır:
Claude'un terakotası (#C96442) kart üstünde 3,7:1 (metin AA altı) ve uyarı kırmızısı ailesine yakın — amber/uyarı sözleşmesiyle çatışır,
kullanılmadı. Önizleme: `?onizleme=claude`; kareler `claude/`, dörtlü montaj `karsilastirma4-*.png`.

Kontrast (hesaplandı): metin/kart 15,8 · ikincil 9,3 · soluk/kart 5,6 · soluk/zemin 5,1 · soluk/yan 5,4 · vurgu metni/tint 6,0 ·
nav aktif 5,6 · vurgu/kart UI 4,8 · uyarı 4,8 · amber 4,8 · nötr rozet 8,4 — hepsi AA üstü. **Yüzey ayrımı: kart/zemin 1,10, yan/zemin 1,05**
— hedefin (≥1,15) altında; Claude'un kendi arayüzü de ayrımı kenarlıkla taşır (kenar/kart 1,34). Ölçüm: 3 sayfa × 1440/375 taşma 0, alert 0;
tsc 0, web 100/100, oxlint 16/0.

Değerlendirme: Soft Warm'a çok yakın (Warm zemini #ECE8DF biraz daha koyu ve daha gri; Claude Ivory daha açık ve daha sarı). Göz konforu
Warm ile eş; kart/zemin ayrımı daha zayıf (1,10 ↔ 1,17), lacivert vurguyla sıcaklık gerilimi aynı. Seçilirse öneri: zemini #ECEAE1'e
çekip ayrımı 1,15'e getirmek (Claude hissi korunur). Genel öneri değişmedi: Cool Slate; sıcak yön isteniyorsa Soft Warm ≈ Claude Ivory.

## Ek 2 (27.10 akşam) — 5. aday: Claude White (Mac masaüstü uygulamasının beyazı; kullanıcı düzeltmesi)
Kaynak: kullanıcının masaüstü uygulaması ekran görüntüsü piksel piksel örneklendi — sohbet/panel zemini **#FFFFFF**, kullanıcı balonu
#F3F3F3 (= beyaz üstünde %5 mürekkep), kenar çizgisi #DDDDDD, ana metin #0A0A0A, ikincil metin #5F5F5F. Palet (`?onizleme=beyaz`):
`--zemin #FFFFFF` · `--yan #F7F7F8` · `--kart #FFFFFF` · `--yuzey rgba(10,10,10,.05)` (= #F3F3F3) · `--kenar #D9D9DE` (örneklenenden bir tık
koyu: beyaz-üstü-beyaz kartı yalnız kenarlık ayırır) · metin #0A0A0A / #3F3F42 / #66666B · vurgu platform laciverti.

Kontrast: metin/kart 19,8 · ikincil 10,5 · soluk 5,7 · soluk/yan 5,3 · vurgu metni/tint 6,2 · nav aktif 5,8 · vurgu/kart 5,0 · nötr rozet 9,5
— hepsi AA üstü. **Kart/zemin 1,00** (beyaz üstünde beyaz; ayrım yalnız kenarlıktan: kenar/kart 1,41), yan/zemin 1,07.
Ölçüm: 3 sayfa × 1440/375 taşma 0, alert 0; tsc 0, web 100/100, oxlint 16/0. Kareler `beyaz/`, üçlü montaj `karsilastirma5-*.png`
(Slate · Claude Ivory · Claude White).

Değerlendirme: en parlak ve en yüksek kontrastlı aday (metin 19,8:1) — masaüstü uygulamasının hissi birebir. Bedeli: brief'in «saf beyazın
yoğun kullanımından kaçın» ve kart/zemin ≥1,15 ilkelerinden sapar; uzun kullanımda en çok göz yoran palet bu olur, kartlar zeminden
ayrışmaz (yalnız çerçeve). Beyaz his isteniyorsa ara yol: zemin #F7F7F8 (yan ile aynı), kart #FFFFFF → kart/zemin 1,07; ya da Neutral
Pearl (zemin #E9E9EC, kart #FAFAFB) zaten «beyaz ama yorulmayan» cevaptır.

## KARAR (27.10 akşam): Claude Ivory — kalıcı uygulama = v2.499 CANLI (610072f, CI #606 5 dk 38 sn; yalnız web imajı)
**Canlı kanıt:** index.html birebir (ilk boyama betiği platform jetonunu okuyor), 22/22 JS/CSS sha256 referans derlemeyle aynı, `/yonetim` 200, canlı CSS'te `data-tema=acik]{--zemin:#f0eee6;--yan:#f5f4ee;--kart:#faf9f5`, canlı Yonetim parçasında `pvq_platform_tema` var ve `onizleme` kalıntısı 0. Sunucuda `git pull` + `docker compose build web` + `up -d --force-recreate web`; api/worker/alembic dokunulmadı.
Kullanıcı gerçek veride üst çubuk seçicisiyle 5 adayı gezip **Claude Ivory**'yi seçti. Uygulama:
- `web/src/index.css`: aday blokları, `data-palet` ve önizleme notu kalktı; tek kalıcı blok `:root[data-yuz="platform"][data-tema="acik"]`
  (zemin #F0EEE6 / yan #F5F4EE / kart #FAF9F5 / kenar #DDD9CE / mürekkep #1F1E1D-#45443F-#66645E / vurgu #3D6BCB-#2A52A8) + açık yüz
  `.dugme-ana` kuralı. Koyu yüz blokları ve müşteri `:root` jetonları değişmedi (bekçi pinleri).
- `Yonetim.tsx`: koyu sabitleme kalktı → `pvq_platform_tema` (açık varsayılan | koyu), atomik geçiş (`tema-gecisi`, müşteri kalıbı);
  önizleme anahtarı, `paletler.ts` ve seçici silindi.
- `PlatformKabugu.tsx`: üst çubukta `.seg` **Açık / Koyu** (müşteri Kabuk kalıbı; «Oto» yok — platformda sayfa yüzü ayrımı yok).
- `web/index.html`: ilk boyama betiği `/yonetim` + platform jetonu için yüzü boyamadan önce uygular (açık↔koyu yanıp sönmesi yok).
- `test/panel/yonetim.test.ts`: «koyu sabit» pini güncellendi; yeni bekçi (jetonlar, seçici, betik, önizleme kalıntısı yok, müşteri/koyu aynen).
- `pvquant-tasarim/referans/jetonlar.md` platform açık yüzü satırı (bilinçli sapma: kart/zemin 1,10); `emsaller.md` «önce önizlenebilir aday» kalıbı.

Doğrulama (sahte API, Chrome): 10 platform sayfası × 375/768/1024/1440/1920 = **50 ölçüm**, taşma 0, alert 0, iskelet 0, hepsi
`acik/platform`, mono 0; müşteri paneli 25 ölçüm değişmedi (örnek kip koyu). Geçiş: jetonsuz giriş ekranı açık · ilk açılış açık (ilk boyama
betiği `data-tema="acik"`) · Koyu tık → #0B0E15, yenilemede kalıcı · Açık tık geri · çıkış sonrası giriş ekranı açık · müşteri paneli
`data-yuz` yok. Kapılar: `tsc -b` 0, web **101/101**, oxlint 16/0, `npm run build` tamam. pytest koşulmadı (Python değişmedi).
Kareler: `kalici-acik-denetim-1440.png`, `kalici-koyu-genel-1440.png`, `kalici-acik-giris-1440.png`, `platform-sistem-1440.png`, `platform-genel_bakış-375.png`.
