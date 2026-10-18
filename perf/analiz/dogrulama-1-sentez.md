<!-- bağımsız doğrulama iş akışı wf_53bef3a9-fe8, sentez ajanı çıktısı (değiştirilmeden) -->

**Nihai hüküm: dal bu hâliyle sahibe teslim edilemez.** Kod tarafı büyük ölçüde sağlam. Testler, tip denetimi, lint ve derleme temiz. main'e birleştirme, push ya da canlıya gönderim yapılmamış. Medya dosyaları bayt bayt aynı. Ancak REPORT.md'de bir ölçüm hatası, açıklanmamış kapsam daraltmaları ve commit'lenmemiş düzeltmeler var. Bunlar giderilmeden kabul tablosu dürüst sayılamaz.

**Teslimden önce zorunlu düzeltmeler**

- **Chromium kısıtlı hat «önce» sütunları geçersiz.** Etkilenen yerler: REPORT §2 LCP tablosundaki Chromium Slow 4G / Fast 3G hücreleri, KIYAS.md ve TABLOLAR.md (/yontem dahil).
  - Nedeni: «önce» replikasının sertifikası 18.10 20:10:14Z'de yenilenmiş, bu satırlar ise 20:34–20:50Z'de, dosyadaki eski sertifika anahtarıyla ölçülmüş.
  - Sonuç: yalnız Chromium'da sunucu yanıt süresi şişmiş: 2 911 / 858 ms. Diğer bütün ölçüm setlerinde ve Firefox/WebKit'te 1 749–1 757 / 503–519 ms.
  - Yanlışlıkla iyileşme diye sunulan değerler: 1 516→1 208, 2 224→1 588, 4 624→4 256, 4 056→2 796, 4 480→3 324, 7 096→6 088, /yontem 1 828→1 372 ve 4 212→3 020.
  - Özgün temel ölçüme göre Chromium kısıtlı FCP değişmemiş; LCP aşağı yukarı aynı ya da hafif kötü (ör. 1 128→1 208, 4 216→4 256).
  - Yapılacak: «önce» Chromium kısıtlı hat satırları canlı sertifika anahtarıyla yeniden ölçülmeli ya da özgün temel ölçüm satırları (matris-eski-vekil.jsonl) kullanılmalı. KOK-NEDENLER'deki «eski vekil ~150 ms» açıklaması ve baseline/SUMMARY.md düzeltilmeli.
- **Kabul tablosunun kapsamı ve yorumu açıkça yazılmalı.**
  - Lighthouse yalnız «/» ve «/yontem» için koşulmuş. /parola-yenile ve giriş görünümü ölçülmemiş; ya ölçülmeli ya «tüm sayfalar» ifadesi düzeltilmeli.
  - TBT ölçütü yalnız Lighthouse'tan değerlendirilmiş. Projenin kendi matrisinde Chromium'da 18 hücre 200 ms'yi aşıyor (en yüksek 1 949 ms) ve sıcak yüklemede kötüleşmiş (ör. 424→1 254). Başsız tarayıcı yapaylığı olabilir, ama yazılmalı.
  - «Firefox/Chromium LCP farkı < %20» ölçütü tek yönlü uygulanmış. Simetrik okumada 24 hücrenin 10–11'i karşılanmıyor (formüle göre). Bunların çoğu 768/1920 genişlikte, Chromium posteri LCP saydığı için 3–4 kat yavaş olduğu hücreler.
- **«Sıfır konsol hatası» ölçütü a1fb5b8'de her ortamda geçerli değil.** <head>'deki `document.fonts.load` çağrılarının reddi yakalanmıyor (`web/vite.config.ts:398`). Arial, Liberation Sans ya da Arimo olmayan sistemlerde (Android) her sayfada 3 «Uncaught (in promise)» hatası çıkıyor. Bu, benzetimle kanıtlandı; gerçek Android cihazda sınanmadı.
- **Çalışma ağacında commit'lenmemiş, ölçülmemiş değişiklikler var.** 6 web/ dosyası ve 3 perf/olc dosyası 19.10 01:25–01:29'da başka bir oturum tarafından değiştirilmiş: `.catch` eki, çapalı açılışta beklememe, levha dinleyicisinin bırakılması ve canlı sertifika anahtarı okuma. Bu değişikliklerle `npm test` 57/57 geçiyor (bu incelemede koşuldu). Teslimden önce bunlar ya kök neden başına ayrı commit'lenmeli ve etkilediği ölçümler yeniden alınmalı, ya geri alınmalı. Rapordaki «sonra = a1fb5b8» ifadesi buna göre güncellenmeli.
- **Firefox kaydırma (§2) yeniden yazılmalı.**
  - ara4'teki «önce» değerleri (29,0 ms / 2,32 çekirdek) medyan değil: iki geçerli koşunun büyük değerleri seçilmiş. Gerçek medyan 27,6 ms / 2,30 çekirdek; geçerli koşu sayısı (n=2) da belirtilmemiş.
  - Son derlemenin kendi A/B ölçümü (after/ab) çok daha kötü: p95 165 ms (koşular 165 / 34,5 / 182,6), %11 kaçan kare, 3,12 çekirdek. Rapor bunu hiç anmıyor.
  - «Değişmedi» yerine «kararsız, belirsiz» yazılmalı.
- **/yontem mobil FCP 1,50→1,65 sn yanlış commit'e bağlanmış.** Bu artış K5'e bağlanmış, ama K5'i (fa0c598) içeren ara derlemelerde (araa, arac) değer hâlâ 1,50 sn. Ben de yeniden okudum. Neden bilinmiyor; 13e9f12'den sonra ortaya çıkıyor (7c8c46d olası, kanıtlanmadı). «/» mobil LCP'deki 1 729→1 878 ms artışı da açıklanmamış.
- **Açıklanmamış davranış değişiklikleri ve olası gerilemeler §8'e eklenmeli:**
  - Yavaş hatlarda kart görsellerinin önden indirmesi 8/8'den Firefox'ta 0/8'e, WebKit'te 1–3/8'e, Chromium 390'da 4/8'e inmiş.
  - Chromium 1440, 20 Mbps sıcak ziyarette indirilen bayt 9,0→23,0 MB (medyan, yüksek oynaklık). Önbellek iki tarafta da çalışıyor; bu fark önbellek hatası değil, video baytı.
  - Firefox 390/768 Fast 3G FCP +0,16–0,21 sn.
  - WebKit 1440 Slow 4G LCP iki ayrı oturumda +160–230 ms; WebKit /yontem Slow 4G +114 / +137 ms.
  - WebKit 1440 kısıtsız FCP 116→224 ms. Bu, raporun «ilk boyama anı değişmiyor» cümlesiyle çelişiyor.
  - Firefox 1440 Slow 4G iyileşmesi abartılı: rapor −257 ms diyor, bağımsız ölçüm −76 ms.
- **Tasarım esnetmeleri §9'da ayrıca onaya sunulmalı.**
  - Safari'de kart görselleri 280→261 px (b6daa3e).
  - Font gelene dek ve web fontu hiç yüklenemeyen ziyaretçide yedek font, SF yerine ölçeklenmiş Arial.
  - Video hareketi en geç 4 sn ötelenebiliyor (20 Mbps'te ölçülen gecikme 0,4–0,9 sn).
  - «Sıfır istenmeyen görsel fark» ifadesi şöyle düzeltilmeli: «Chromium/Firefox 40/40 aynı; WebKit'te onay bekleyen bilinçli fark; video oynarken görsel doğrulama yapılmadı.»
- **Sayı ve atıf düzeltmeleri:**
  - §3 K4: 17/36 → 19/36 (§2 ile tutarlı olsun).
  - §3 K5: Firefox 19/36 ve Chromium 5/36 → 17/36 ve 3/36 (güncel temel ölçüm).
  - §3 K2'deki «önce 64/85/75» aslında araa (6dfbb35) derlemesi.
  - KOK-NEDENLER'deki 0,98 → 0,94.
  - K3: 18/18, 23/23, 21/23 → 24/24, 24/24, 24/24.
  - Filtre eşdeğerliği «≤ 2/255», Chromium 1440@2'de geçerli değil (en büyük fark 11/255).
  - «LCP = video karesi» (KOK-NEDENLER, 49d8f2b) ve «poster LCP sayılmıyor» (13e9f12) yanlış: LCP öğesi poster.
  - «390'da 25→0–2 (üç ağ)» yalnız kısıtlı hatlarda doğru; Firefox'ta her ağda.
  - Etkileşimdeki 539 ms iki koşunun ortalaması (n=2).
  - KIYAS'taki «önce 0 hata» bir süzgeçle sıfırlanmış; gerçekte 1 adet NS_ERROR_PARSED_DATA_CACHED var.
  - Ham verisi olmayan sayılar «yeniden üretilemez» diye işaretlenmeli ya da ham dosyaları eklenmeli: kenar enerjisi değerleri, 563→539, will-change duman testi, 172/448.
- **Commit düzeyindeki sorunlar.** Dal push edilmediği için ya yeniden düzenlenebilir (commit kimlikleri değişir ve raporlar güncellenmeli) ya da §4'te açıkça yazılabilir; karar sahibin.
  - 0686656 mesajı «53/53» diyor, o commit'te gerçek 52/52.
  - 89e910f iki kök nedeni tek commit'te birleştiriyor; bu, «kök neden başına tek commit» kuralının çiğnenmesi.
  - a1fb5b8 var olmayan bir dosyaya atıf yapıyor (perf/after/ab/video-zaman.jsonl; veri analiz/ara-sonra2'de).
  - «K1» adı 0686656'da başka, raporda başka anlamda kullanılıyor.
- **Diğer eksikler:** REPORT §6 boş bir yer tutucu (`⟨doğrulama iş akışı bekleniyor⟩`); bu doğrulamanın sonucuyla doldurulmalı. Commit'lenmemiş kanıtlar (analiz/webkit-tekrar/ekran.json, webkit-tekrar2/, gurultu/diff/) ya eklenmeli ya «yeniden üretilemez» denmeli; arad ve arae derlemeleri de yalnız reflog'da duruyor.

**Doğrulananlar**

Dört doğrulama birbirini büyük ölçüde tutuyor.

- **Kod:** `npm test` 57/57, `tsc`, `oxlint` (0 hata; 16 uyarının hepsi d6ab50a'da da var) ve derleme çıkış 0.
- **Commit davranışları:**
  - a1fb5b8, 6dfbb35'in birebir tersi; iz kalmamış.
  - K3 yavaş hat kapısı üç motorda doğru çalışıyor: yenilemede video isteği 0; WebKit'teki 73 KB video değil.
  - fa0c598 doğru rota karesini veriyor.
  - Font aralık daraltması fontTools ile doğrulandı; font yüklendikten sonraki son çizim değişmiyor.
  - 02c875d'de askıda kalma yok.
- **Lighthouse:** ham dosyalardan ve bağımsız yeniden ölçümle doğrulandı. «/» mobil 47/75/85→99/99/99 (bağımsız koşu 98), masaüstü 93→100, LCP 7,51→1,88 sn; /yontem 99/100. Erişilebilirlik / en iyi uygulama / SEO 100/100/91, değişmedi. TBT ≤ 200 sağlanıyor ama pay dar: makine yükü altında bağımsız tek koşuda 141 ms ölçüldü.
- **Kayma ve LCP:** 390'daki 25 px zıplama kısıtlı hatta üç motorda 0–2 px'e inmiş. Slow 4G 390'da LCP ≤ 2,5 sn üç motorda bağımsız olarak doğrulandı (1 316 / 1 259 / 1 915 ms).
- **Hatalar:** 432 yüklemede ve bağımsız 88 yüklemede konsol, istek ve gezinme hatası 0 (Mac'teki üç motorda).
- **Bant ve font:** yavaş hatta yenilemede video baytı 0; Firefox latin-ext 0/36; 20 Mbps kart süreleri ve boya A/B çekirdek değerleri tutuyor.
- **Piksel:** aynı boyutlu 56 çiftin 56'sı ham bayt olarak aynı. WebKit farkının «katmanlar» bandı, sonra↔sonra çekiminde de aynı 253 845 px ile çıkıyor; yani çekim gürültüsü.
- **Süreç:** temel ölçüm (49d8f2b) kod değişikliklerinden önce. main = origin/main = d6ab50a; dal uzakta yok. Canlıdaki index.html, d6ab50a derlemesiyle bayt bayt aynı. Medyanın 22'si de bayt bayt aynı.

**Doğrulanmayan ya da yanlış olanlar**

En ağır bulgu Chromium kısıtlı hat «önce» sütunu. İki doğrulayıcı bunu birbirinden bağımsız buldu; ben de zaman çizelgesini ve yanıt sürelerini yeniden okuyarak teyit ettim. Ölçüm doğrulayıcısı sertifika anahtarını bilerek uyuşmaz yapınca yanıt süresinin +350 ms arttığını deneyle gösterdi.

Bu hata geçti/kaldı kararlarını değiştirmiyor, çünkü kararlar «sonra» değerleriyle veriliyor. Ama raporun Chromium'daki iyileşme anlatısını büyük ölçüde geçersiz kılıyor. «Chromium 768: 4 624→4 256» satırı gerçekte iyileşme değil, yatay ya da hafif gerileme.

Ayrıca:
- Firefox kaydırmada rapor yalnız işine gelen ara ölçümü kullanmış.
- /yontem FCP artışının açıklaması veriyle çelişiyor.
- WebKit gerilemeleri «gürültü» eşiğinin üstünde, ama yazılmamış.
- Chromium 1440 Slow 4G LCP iki tepeli dağılıyor. Üç koşu yetmiyor: ölçüm doğrulayıcısında iki koşuyla oran 1,24 çıkıp ölçüt kaldı, beş koşuyla 0,93 çıkıp geçti. En az beş koşu gerekiyor.

**Kabul tablosu dürüst mü?**

Kendi yorumları içinde 56/59 sayımı aritmetik olarak doğru. Uydurma bir sayı bulunmadı. Ama tablo şu hâliyle dürüst değil:
- «Tüm sayfalar» iki sayfaya daraltılmış.
- TBT yalnız Lighthouse'tan okunmuş; matrisin karşıt verisi saklanmış.
- Firefox/Chromium oranı açıklanmadan tek yönlü uygulanmış.
- Konsol ölçütü Android'de bozuluyor.
- WebKit'teki tasarım değişikliği «istenmeyen değil» diye kendiliğinden onaylanmış.

Dürüst bir tabloda Lighthouse ölçütü «ölçülen iki sayfada» geçer. Firefox/Chromium ölçütü simetrik okumada «/» sayfasında büyük ölçüde kalır. Konsol ölçütü Android için «düzeltme commit'lenmedi, ölçülmedi» notu taşır. Görsel ölçüt «sahip onayı bekliyor» olur.

**Kurallara uyum**

Uyulanlar: önce ölçüm, tasarım dosyaları ve medyanın korunması, main'e birleştirmeme ve canlıya göndermeme.

Çiğnenenler ya da zayıflar:
- «Her kök neden için tek commit»: 89e910f.
- «Uydurma ya da koşulmamış sayı yok»: 0686656'nın test sayısı ve ham verisi olmayan sayılar.

Çalışma ağacı şu an temiz değil. Yeniden ölçümler, commit'lenmemiş bir ölçüm aracıyla yapılırsa yeniden üretilemez: sertifika anahtarı dosyaları 01:45 ve 01:47'de yeniden yazıldı, yani başka bir oturum şu anda ölçüm yapıyor.

Bu doğrulama için yalnız okuma komutları ve `npm test` çalıştırıldı; izlenen hiçbir dosya değiştirilmedi.

Dosyalar:
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/REPORT.md
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/after/KIYAS.md
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/analiz/KOK-NEDENLER.md
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/baseline/matris.jsonl (şişmiş Chromium satırları)
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/baseline/matris-eski-vekil.jsonl (özgün temel)
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/baseline/SUMMARY.md
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/web/vite.config.ts
- /Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/dogrulama/ (doğrulayıcıların betikleri ve çıktıları; surec-denetimi.py, spki-ttfb.mjs, iddia-*.mjs, kod-inceleme/)