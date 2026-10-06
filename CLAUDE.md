# PVQuant — Claude çalışma kuralları

## Tasarım yığını (Mühür A, 05.10.2026)

Her UI/grafik işinde ÖNCE `pvquant-tasarim` skill'i yüklenir (`.claude/skills/pvquant-tasarim/`)
— jetonlar, mavi=tahmin/amber=gerçekleşen sözleşmesi, grafik karar tablosu, emsaller, QA
betikleri oradadır ve genel skill'lerin stil önerilerini EZER.

Rol ayrımı (çakışma kuralı): palet/font/grafik-türü VERİSİ `ui-ux-pro-max`'ten aranır;
nihai seçim `frontend-design` ilkeleriyle gerekçelendirilir ve `pvquant-tasarim`
jetonlarına bağlanır; üretim sonrası `web-design-guidelines` denetiminden geçer.
İki skill'e birden «stili sen seç» dedirtilmez.

Eklenti rolleri (07.10.2026 kurulumu): **Data** = SQL/veri keşfi/istatistik/doğrulama
(EPİAŞ CSV'leri, SCADA arşivleri) — görselleştirme/dashboard tarafı ÜRÜN yüzeyine girerse
pvquant-tasarim veto eder; **Test Coverage Intelligence** = kapsama boşluğu analizi (çıktısı
test yazımında kullanılır, ritüeli değiştirmez); **finecomb** = dönemsel salt-okunur derin
güvenlik denetimi (hızlı diff incelemesi security-review'da kalır). dataink/review-council
tarzı çakışan eklentiler BİLİNÇLİ kurulmadı.

## Dürüstlük anayasası (testle zorlanır)

Sayı uydurulmaz; logo duvarı/müşteri alıntısı/yıldız yok; görünür yüzeyde yöntem/kaynak adı
yok; amber YALNIZ gerçekleşen üretim; eylem rengi yalnız düğme/bağlantı/odak; vitrin formu
gerçek gönderilmez. Ayrıntı: `.claude/skills/pvquant-tasarim/referans/anti-slop.md`.

## Mühür ritüeli (özet)

Uygulama → python `.venv/bin/python3 -m pytest` (RLS için `docker compose up -d db`;
DİKKAT: `pytest | tail` pipe'ı çıkış kodunu YUTAR — ya ayrı komutla `$?` oku ya
`set -o pipefail`; v2.400'de 3 ERROR'lu koşu böyle sessiz geçti) →
web `npm test` / `npm run build` (tip kapısı BUDUR — kök tsconfig dosyasız olduğundan
çıplak `tsc --noEmit` hiçbir şeyi denetlemez, Mühür B dersi) / `npx oxlint src/...`
(AYRI çıkış kodları; `grep -c` zincir kırar) → görsel regresyon `npm run gorsel`
(vitrin dokunulduysa; baseline diff'i gözle onaylanır) → CDP doğrulama (`tarama.mjs`; panel için
dev JWT yerel konteynerde basılır — CANLIDA müşteri kiracısında gezinilmez) → önizleme →
AÇIK kullanıcı onayı → Türkçe NE/NEDEN/KANIT commit (`git add -A` YASAK) → push → CI
TARAYICIDAN izlenir (anonim API kota yakar) → sunucu
`ssh root@178.18.206.130 "cd /opt/pvquant && git pull && docker compose build web && docker compose up -d"`
→ canlı CDP doğrulama → defter + bellek. Workflow YAML düzenlenirse `yaml.safe_load` kapısı.
