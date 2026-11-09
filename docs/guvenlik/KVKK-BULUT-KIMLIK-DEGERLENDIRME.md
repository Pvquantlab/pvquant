# KVKK değerlendirme TASLAĞI — bulut kimlik bilgisi saklama (v2.563, 09.11.2026)

**Bu belge hukuki görüş değildir.** Hukuk danışmanına gidecek olgu ve soru listesidir; karar (K1) teknik tarafta alındı (uygulama içi KEK, zarf şifreleme —
docs/guvenlik/KEK-ANAHTARI.md). Danışman görüşü gelene kadar yol haritasında «dış girdi» olarak kalır.

## 1. Ne saklanıyor, nerede

| Veri | Nitelik | Nerede | Nasıl |
|---|---|---|---|
| FusionSolar Northbound kullanıcı adı + systemCode; SolarEdge filo API anahtarı; SolisCloud Key ID/Secret; Sungrow AppKey/access key/erişim ve yenileme belirteçleri; Growatt OSS belirteci | Müşterinin (tüzel kişi) üçüncü taraf hesabına erişim kimlik bilgisi | PVQuant sunucusu (Türkiye'de barındırılan VPS), PostgreSQL `bulut_kimlik` | Zarf şifreli (kayıt başına veri anahtarı, ana anahtar veritabanı dışında `.env`); düz metin hiçbir günlük/denetim izinde yok |
| Maskeli hesap etiketi (ör. «nbi…li»), sağlayıcı, bölge, sağlayıcı santral kodu | Tanımlayıcı değil (maskeli) | Aynı tablo, düz | Ekranda ve denetim izinde görünür |
| Sağlayıcıdan çekilen saatlik üretim verisi | Tesis verisi (kişisel veri değil; tüzel kişiye ait) | `bulut_saatlik_ham`, `kaynak_saatlik` | Düz; RLS ile kiracıya kapalı |
| Onay kaydı (iki onay metni, zaman, onaylayan kullanıcı kimliği) | İşlem kaydı; kullanıcı kimliği kişisel veri olabilir | `bulut_kimlik.onay_json`, denetim izi | Düz |

## 2. Veri akışı

Müşteri kullanıcısı (tüzel kişi adına) kimliği girer → PVQuant sağlayıcıya giriş ve santral listesi sorgusu yapar (sınama) → kimlik şifrelenerek saklanır →
worker saatte bir sağlayıcıdan veri çeker (kimlik yalnız bu anda çözülür) → veri PVQuant'ta kalır. Veri Türkiye dışına PVQuant tarafından aktarılmaz;
sağlayıcı sunucuları (Huawei intl/eu5, SolarEdge, Solis, Sungrow eu/intl, Growatt intl) yurt dışındadır ve veri zaten müşterinin kendi sağlayıcısındadır —
PVQuant bu aktarımı yapmaz, mevcut hesaba yalnızca okur.

## 3. Danışmana sorular

1. Tüzel kişi müşterinin üçüncü taraf hesabına ait API kimlik bilgisi KVKK anlamında kişisel veri midir? (Hesap bir gerçek kişi adına açılmışsa — ör. kurulumcu
   çalışanının e-postası — kişisel veri niteliği doğabilir.) Bu durumda veri sorumlusu/işleyen rolleri nasıl dağılır?
2. PVQuant'ın sağlayıcıya yaptığı okuma çağrıları «yurt dışına aktarım» (md. 9) sayılır mı, yoksa müşterinin kendi aktarımının devamı mıdır? Sağlayıcı
   sözleşmeleri (Sungrow: ÇHC hukuku; SolarEdge/Huawei: kendi şartları) bu değerlendirmeyi etkiler mi?
3. Onay metinleri («yalnızca veri okunmasını onaylıyorum», «kimlik bilgisinin PVQuant'ta şifreli saklanmasını ve yalnızca düzenli veri çekişinde kullanılmasını
   onaylıyorum») açık rıza/aydınlatma bakımından yeterli mi; sözleşmeye (hizmet sözleşmesi, veri işleme eki) hangi hükümler eklenmeli?
4. Saklama süresi ve imha: müşteri kimliği sildiğinde (uygulamada anında siliniyor) ve sözleşme bitince ham sağlayıcı verisi ne kadar tutulmalı?
5. Olay bildirimi: kimlik sızıntısı şüphesinde (docs/guvenlik/KEK-ANAHTARI.md «Sızıntı şüphesi») Kurul/ilgili kişi bildirim yükümlülüğü doğar mı?
6. Sungrow Developer Service Agreement VIII(c) ticari kullanım onayı ve Solis «yalnız son kullanıcı» erişimi — sözleşmesel uyum, KVKK'dan ayrı dış girdi.

## 4. Teknik tedbirler (mevcut)

Zarf şifreleme ve ana anahtar ayrımı; RLS; denetim izinde gizli yok; kimlik yalnız worker'da çözülür; iptal/silme anında; KEK dönüşü prosedürü; TLS;
yazma uçları bağlayıcılarda yasak (Solis), komut yolu yok. Eksik: mTLS zorunluluğu (edge), HSM/Vault (karar: uygulama içi KEK), bağımsız sızma testi.
