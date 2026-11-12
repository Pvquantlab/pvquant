# EPİAŞ entegrasyonu (v2.604, Faz 4 F4-J)

## Kamuya açık / özel ayrımı

| Yüzey | Yön | PVQuant'ta | Kimlik |
|---|---|---|---|
| **Şeffaflık Platformu** (`seffaflik.epias.com.tr/electricity-service`) | okuma | `ext/turkiye/epias.Istemci` (tek istemci) | kayıtlı kullanıcı + şifre → CAS TGT (`giris.epias.com.tr/cas/v1/tickets`); `PVQUANT_EPIAS_KULLANICI/SIFRE` |
| **EPYS / TPYS** (uzlaştırma, KGÜP bildirimi) | yazma | **YOK** — dosya üretilir (TPYS CSV, EAK CSV), gönderim ve kabul müşterinin sisteminden; uzlaştırma bildirimi müşteri yükler (Mutabakat) | — |
| **DGP/GİP teklif** | yazma | YOK (PVQuant piyasaya teklif vermez) | — |

Şeffaflık verisi kamuya açıktır ama erişim kayıtlı kimlik ister; kimlik yoksa fiyatlar **senaryo** (kaynak `senaryo`), gerçekleşen üretim EPİAŞ'tan
çekilmez (atlanır). Hiçbir uç uydurma veri üretmez; boş yanıt boş seri döner.

## İstemci davranışı

- TGT 100 dk önbellekli (doküman 2 sa, CAS 8 sa; kısa olan esas); CAS TGT limiti 100/dk; veri servisi limiti doğrulanamadı (429'da 30 sn bekleme).
- Tarihler piyasa günü (`Europe/Istanbul`; `piyasa_service.piyasa_gunu`): gece işi (03:15 TSİ) dünü ve 3 günü, gün öncesi PTF (14:35 TSİ) bugün+yarın,
  gerçekleşen üretim (03:18 TSİ) dünü ve 7 günü piyasa gününe göre alır. v2.604 öncesi `date.today()` sunucu UTC günüydü: 21:00 UTC sonrası
  «dün» bir gün geri kayıyordu.
- Gün önbelleği (`PVQUANT_EPIAS_ONBELLEK_DIZIN`, varsayılan `var/epias`, api ve worker ortak `./var` hacmi): yalnız bitişi **7+ gün** geride kalan
  pencereler, saat sayısı tam ise CSV'ye yazılır (kısmi yanıt kalıcı olmaz). Gece işinin son 3 günü hep ağdan gelir; EPİAŞ düzeltmeleri `piyasa_fiyat_surum` tarihçesine düşer (F4-G). Geri doldurma
  pencereleri ikinci kez ağa gitmez. `""` → kapalı.
- Sistem yönü METİN döner, `kurallar.yon_normalize` ile acik|fazla|dengede; bilinmeyen → None (o saat hesaplanmaz).

## Uç sözleşmeleri

Şeffaflık 2.0 teknik belgesi bu oturumlardan okunamadı (erişim); satırlar koddaki şema notları, Wayback v1.15.x şeması ve **31.10.2026 canlı sınaması**
(kayıtlı kimlik, sunucudan) üzerinden. «Dış doğrulama gerekli» = belgeyle teyit bekliyor.

| Uç | Yol | Gövde / alan | Durum |
|---|---|---|---|
| ptf | `POST /v1/markets/dam/data/mcp` | startDate, endDate → `price` | canlı sınandı (29.10.2026) |
| smf | `POST /v1/markets/bpm/data/system-marginal-price` | → `systemMarginalPrice` | canlı sınandı |
| sistem_yonu | `POST /v1/markets/bpm/data/system-direction` | → `systemDirection` (metin) | canlı sınandı; metin→kod eşlemesi `yon_normalize` |
| kgup / kgup_ilk | `POST /v1/generation/data/dpp[-first-version]` | + `region: TR1` zorunlu → `toplam` | canlı sınandı (region 400 dersi) |
| gercek_zamanli_uretim | `POST /v1/generation/data/realtime-generation` | + `powerPlantId` → `total` | canlı sınandı |
| santral_listesi | `GET /v1/generation/data/powerplant-list` | — | canlı sınandı (1832 santral) |
| organizasyon_listesi | `POST /v1/generation/data/organization-list` | startDate, endDate | canlı sınandı (692 kuruluş) |
| uevcb_listesi | `POST /v1/generation/data/uevcb-list` | organizationId, startDate (endDate şemada yok) | canlı sınandı |
| uevcb_santraldan | `POST /v1/markets/data/uevcb-list-by-power-plant-id` | powerPlantId, startDate | canlı sınandı |
| dengesizlik_miktar / tutar | `POST /v1/markets/imbalance/data/imbalance-*` | → `positiveImbalance` | **dış doğrulama gerekli** (üretim yolunda kullanılmıyor) |
| gip_aof | `POST /v1/markets/idm/data/weighted-average-price` | → `wap` | **dış doğrulama gerekli** |
| yek_dengesizlik | `POST /v1/renewables/data/imbalance-cost` | → `imbalanceCost` | ESKİ dönem ucu: yalnız ≤30.04.2016 (31.10.2026 sınaması, SEF1181) |

Karar 14968 (RG 20.10.2026-33406): Şeffaflık veri listesi 1.1.2027'den değişir; SMF yalnız saatlik listelenir (15 dk DGP belirsizliği,
`docs/ZAMAN-SOZLESMESI.md`). Belgeye erişilince bu tablo satır satır teyit edilir; `swagger.json info.version` değişimi izlenir.

## Yapılan / yapılmayan (F4-J)

- Yapılan: ölü ikinci istemci `ext/kaynak/epias.SeffaflikIstemci` kaldırıldı (eski formül fonksiyonu guard'lı kaldı); gün önbelleği üretimde açık ve
  düzeltme penceresiyle; tarih aralıkları piyasa günü; bu belge.
- Yapılmayan: yeni uç eklenmedi; Şeffaflık belgesi doğrulaması (erişim); `eptr2` değerlendirmesi; EPYS/TPYS yazma (ilke gereği yok).
