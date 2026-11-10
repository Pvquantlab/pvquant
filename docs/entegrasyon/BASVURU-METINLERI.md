# Başvuru ve talep metinleri — dış girdiler için taslaklar (10.11.2026)

Taslaklar; göndermeden önce şirket bilgileri ve tarihler doldurulur. Hiçbiri gönderilmedi. Hepsinde ortak ilke: **yalnızca okuma**, kimlik
bilgisi güvenli kanaldan, kapsam ve süre yazılı, iptal anında. Köşeli parantez içi alanlar doldurulur. Usuller araştırma notudur
(`DIS-GIRDI-TAKIBI.md`); üreticinin güncel ekranı farklıysa üreticininki geçerlidir.

## §1 FusionSolar — kurulumcuya Northbound (NBI) hesabı isteği (D2)

Konu: PVQuant için FusionSolar Northbound (NBI) kullanıcısı

Sayın [kurulumcu yetkilisi],

[Müşteri unvanı]'nın [santral adı, kurulu güç] santralinin üretim verisini uzlaştırma ve tahmin analizi için PVQuant'a aktarmak istiyoruz.
Huawei FusionSolar bu aktarım için ayrı bir **Northbound (NBI) kullanıcısı** öngörüyor; bu kullanıcıyı yalnız kayıtlı kurulumcu şirketin
yöneticisi açabiliyor. Sizden ricamız:

1. FusionSolar yönetim hesabınızla PVQuant için ayrı bir Northbound kullanıcısı açmanız.
2. Kullanıcıya yalnız şu santral(ler)in atanması: [santral adları / kodları].
3. Yalnız şu arayüzlerin yetkilendirilmesi: `login`, santral listesi (`stations` ya da `getStationList`), saatlik santral KPI'sı
   (`getKpiStationHour`). Yazma, komut ya da cihaz yapılandırma arayüzü istemiyoruz.
4. Kullanıcı adı ve systemCode'un e-posta gövdesi yerine [güvenli kanal: telefonla/ayrı mesajla] iletilmesi.
5. Hesabın hangi bölge sunucusunda açıldığının (ör. intl, eu5) belirtilmesi.

PVQuant bu kimlikle yalnız veri okur; kimlik bilgisi şifreli saklanır, yalnız düzenli saatlik çekişte kullanılır ve santral sahibi istediği anda
PVQuant'tan silebilir. Günlük çağrı sayımız santral başına 25'in altında kalır. Hesap açıldıktan sonra ilk gün yanıtlardaki birimleri
(kapasite, saatlik enerji) portal dışa aktarımıyla kıyaslayacağız; bu kıyas için aynı güne ait portal «saatlik üretim» dışa aktarımını da rica ederiz.

Saygılarımızla, [ad, unvan, telefon]

**Not (bize):** şirket başına en çok 5 NBI hesabı; oturum 30 dk; 10 dk'da ≤5 giriş. Teslim alınca D2 doğrulama protokolü uygulanır.

## §2 Pilot sahası — yazılı yetki ve kapsam beyanı (D3; G02/G03/G04/G10)

Araştırmada hazır metin yok; kapsam kalemleri B 17/09–09a'dan. Üç taraf imzalar: tesis/veri sahibi, O&M, OT/ağ sorumlusu.

**PVQuant veri okuma pilotu — yetki ve kapsam beyanı**

1. **Taraflar.** Tesis/veri sahibi: [unvan]. O&M: [unvan]. OT/ağ: [unvan/kişi]. Hizmet sağlayıcı: PVQuant [unvan].
2. **Amaç.** [Santral adı]'nın üretim verisinin uzlaştırma ve tahmin analizi için okunması. Başka amaç yoktur.
3. **Cihazlar.** Yalnız aşağıdaki cihazlar: [etiket, model, seri no, donanım/yazılım sürümü, IP, port, birim kimliği]. Listede olmayan hiçbir
   cihaza erişilmez.
4. **Okuma kapsamı.** Modbus TCP: yalnız fonksiyon 3 ve 4 (kayıt okuma), yalnız listedeki birim kimlikleri ve adres aralıkları
   [aralıklar]. IEC 104: yalnız STARTDT/STOPDT/TESTFR, S-çerçeve ve genel sorgulama (C_IC_NA_1); saat eşitleme ve komut gönderilmez.
   Yazma, komut, parametre değişikliği, şebeke profili değişikliği yapılmaz. OT bu kapsamı ağ tarafında da süzgeçle (hedef/port/birim/fonksiyon)
   uygular ve süzgecin çalıştığını [tarih]'te doğrular.
5. **Oturum ve mevcut sistemler.** Mevcut SCADA/PPC/O&M bağlantıları etkilenmez. IEC 104'te PVQuant için ayrı istemci yuvası
   / yedeklilik grubu tanımlanmıştır: [yuva/IP]. STARTDT gönderilmesine sahip [onay veriyor / vermiyor].
6. **Ağ.** Erişim sahanın başlattığı VPN/tünel üzerinden; Modbus 502 internete açılmaz. PVQuant IP: 178.18.206.130.
7. **Test penceresi.** [başlangıç – bitiş tarihi/saati]; okuma sıklığı en fazla [15 dk]; pencere dışında erişim yok.
8. **Referans.** Sahip aynı cihaz(lar)dan aynı dönem için sayaç/dışa aktarım verisini [tarih] itibarıyla verir; ölçüm sınırı:
   [inverter çıkışı / PCC / uzlaştırma sayacı]; saat dilimi ve zaman damgası kuralı: [UTC+3, saat başı/sonu].
9. **Tolerans ve kabul (önceden).** Saatlik enerji farkı %2 ya da 0,5 kWh içinde «uyumlu»; en az 24 ortak saat; eksik/ikame saatler
   ayrı sayılır.
10. **Saklama ve silme.** Okunan ham örnekler PVQuant'ta [süre] tutulur; sahibin yazılı talebiyle [x gün] içinde silinir.
11. **Kesinti ve geri alma.** O&M/OT bildirimsiz kesebilir; PVQuant tarafı kesildiğinde cihazda hiçbir değişiklik kalmaz (yalnız okuma).
    Sorumlu kişiler ve telefonları: [liste].
12. **Gizlilik.** Bu belgeye parola/anahtar yazılmaz; kimlik bilgileri ayrı güvenli kanaldan iletilir.

İmza ve tarih: tesis/veri sahibi · O&M · OT · PVQuant.

## §3 Sungrow — geliştirici kaydı ve ticari kullanım onayı talebi (D4)

**Kayıt (siz):** geliştirici portalı (`developer-api.isolarcloud.com`; B'de `.com.hk`) → hesap → uygulama başvurusu: ad «PVQuant»,
simge, **redirect URL** `https://pvquant.com/v1/bulut/oauth/sungrow/geri-donus` (uç v2.564'te yazıldı). Onay sonrası AppKey, Secret Key, applicationId → `.env` (OAUTH-UYGULAMA-KAYDI.md).

**Ticari onay e-postası (İngilizce; alıcı: portal destek adresi ve/veya data-protection@sungrowpower.com):**

Subject: Request for commercial-use approval under the Developer Service Agreement (clause VIII(c)) — PVQuant

Dear Sungrow iSolarCloud developer team,

PVQuant ([legal name, Türkiye]) provides settlement and forecasting analytics to owners of solar plants in Türkiye. Plant owners who use
iSolarCloud ask us to read their own plant data through the OpenAPI so that we can reconcile their hourly production with the Turkish
market operator's settlement. We request your written approval for this commercial use, as required by clause VIII(c) of the Developer
Service Agreement.

Scope: read-only access authorised by each plant owner through the OAuth consent flow; endpoints `queryPowerStationList` and
`getPowerStationPointMinuteDataList` only; no device control, no configuration; data is stored only for the owner's own account and is
not resold or redistributed to third parties (clause III(c)). Expected volume: fewer than [N] plants and fewer than 2,000 calls per hour.
Developer account: [e-mail]. Application: PVQuant. Region: plants are located in Türkiye; please confirm which regional gateway
(International or Europe) serves Turkish accounts.

Please let us know whether additional company information is required (clause II(a)). Kind regards, [name, title, phone]

## §4 SolarEdge — kurulumcuya filo erişimi / ilişkili hesap isteği (D5)

**Kayıt (siz):** `developer.solaredge.com` → geliştirici hesabı (Free) → uygulama; site sahibi onayı için Allowed Redirect URI `https://pvquant.com/v1/bulut/oauth/solaredge_oauth/geri-donus`, kapsam SITE_DATA; Client ID/Secret → `.env` (OAUTH-UYGULAMA-KAYDI.md). Filo yolu kurulumcunun tercihine göre.

Sayın [kurulumcu yetkilisi],

[Müşteri unvanı]'nın SolarEdge sistemlerinin saatlik üretim verisini PVQuant'a aktarmak için SolarEdge'in V2 API'sinde iki yol var; size uyanı
seçmenizi rica ederiz:

- **Filo erişimi (External Fleet):** PVQuant uygulaması için size bir onay bağlantısı gelir (14 gün geçerli). SolarEdge hesabınızla
  girip süreyi seçersiniz (3/6/12 ay ya da en çok 24 ay). Sonra anahtarı biz üretiriz; anahtar yalnız sitelerinizi okur.
- **İlişkili hesap (Associated Accounts):** Monitoring › Account Details › Associated Accounts › Add → [PVQuant yönetici e-postası],
  «Read only», «Per site»: [site adları].

Her iki yolda da erişim yalnızca okumadır; kontrol ya da yapılandırma istemiyoruz. API kredilerini PVQuant öder. Saygılarımızla, [ad]

## §5 Growatt — kurulumcuya API belirteci isteği (D6)

Sayın [kurulumcu yetkilisi],

[Müşteri unvanı]'nın Growatt santralinin üretim verisini PVQuant'a aktarmak için Growatt OpenAPI belirteci gerekiyor; belgeye göre belirteç
OSS hesabınızdan şu yolla istenir: OSS › System Settings › System Management › **Add API**. Onay sonrası belirteç e-postayla gelir. Ricamız:

1. Başvuruyu [santral adı] için yapmanız; mümkünse «yalnızca okuma» notu düşmeniz.
2. Belirteç gelince e-posta gövdesi yerine [güvenli kanal] ile iletmeniz.
3. IP beyaz listesi istenirse PVQuant sabit adresi: **178.18.206.130**.

PVQuant yalnız santral listesi ve günlük güç serisini okur (günde santral başına en fazla birkaç çağrı); kimlik şifreli saklanır, sahip istediği
anda siler. Türkiye temsilciliği (Ankara) ile görüşmek gerekirse: +90 312 394 71 00, servis@growatt-tr.com. Saygılarımızla, [ad]

## §6 Solis — santral sahibine adımlar ve kapsam beyanı (D7)

**Sahibin yapacakları (SolisCloud):** Service Centre › yeni bilet, tür «API Access Request», SolisCloud e-postası → Solis onay e-postası →
çıkış/giriş → Service › API Management › «activate now» → doğrulama (CAPTCHA + e-posta kodu) → **Key ID + Key Secret** → PVQuant'a
[güvenli kanal] ile iletme. Anahtar hesabın yazma uçlarını da açar; PVQuant yazma uçlarını kod düzeyinde kullanmaz.

**Kapsam beyanı (sahip ile PVQuant arasında, hizmet sözleşmesi eki):**
«[Sahip], SolisCloud hesabına ait API anahtarını PVQuant'a yalnızca kendi santral(ler)inin üretim verisinin okunması ve kendisi adına
uzlaştırma/tahmin analizi yapılması için verir. PVQuant veriyi üçüncü taraflara satmaz, yeniden dağıtmaz, SolisCloud kullanım şartlarının
yasakladığı hiçbir amaçla kullanmaz; anahtarı şifreli saklar, yalnız düzenli çekişte çözer; sahip anahtarı her an silebilir ve SolisCloud'da
yenileyebilir.»

## §7 İlk müşteri görüşmesi — envanter soruları (P-ENV / B U01)

Amaç: hangi yolun (bulut, Modbus, IEC 104, dosya) açılabileceğini ilk görüşmede anlamak. Yanıtlar `pilot` parametre formuna işlenir.

1. Santral(ler): ad, kurulu güç (MWac/MWdc), lisanslı/lisanssız, UEVÇB/ölçüm noktası.
2. Inverter markası ve tam modeli; adet; yazılım sürümü biliniyor mu.
3. Logger/SCADA/PPC: marka (SmartLogger, Logger1000, EzLogger, Inavitas, LOGGMA/Solarify, Mikrodev, diğer); kim işletiyor (O&M).
4. Bulut portalı kullanılıyor mu (FusionSolar, iSolarCloud, SolisCloud, SEMS, Growatt, SolarEdge); hesap kimin adına (sahip/kurulumcu).
5. Mevcut dış bağlantılar: EDAŞ/TEİAŞ RTU hattı, O&M uzaktan erişimi, başka analiz hizmeti.
6. Ağ: sahada internet türü (fiber/4G), outbound VPN kurabilecek router/gateway var mı, OT sorumlusu kim.
7. Sayaç verisi: OSOS/MASS erişimi, sayaç çözünürlüğü, CT/PT; uzlaştırma sayacıyla inverter çıkışı arasındaki fark biliniyor mu.
8. Mevcut dışa aktarım: portal/SCADA'dan saatlik CSV alınabiliyor mu (referans için en az 1 ay).
9. Yetki: veri sahibi, O&M ve OT'nin yazılı izin verme süreci; imza yetkilisi.
10. Beklenti ve zaman: hangi ay için ilk mutabakat; pilot penceresi.
