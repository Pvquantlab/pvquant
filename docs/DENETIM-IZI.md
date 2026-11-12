# Denetim izi (v2.602, Faz 4 F4-H)

## İlke

İz, kapı değildir: yazım kendi kısa işleminde (sistem bağlamı) yapılır, ana işi düşürmez. Sır yazılmaz (parola, jeton, anahtar, kurtarma kodu,
webhook sırrı, dosya içeriği). Üç kapsam: `platform` (personel), `musteri` (kiracı kullanıcısı), `dis_api` (API anahtarıyla yazma; aktör = anahtar
kimliği). Bilinmeyen kapsam `kaydet` tarafından açıkça reddedilir (`False` + günlük) — M1 dersi: CHECK'e takılan iz sessizce kaybolmuştu.

## Şema (göç v2602)

- `kapsam` CHECK: platform | musteri | dis_api (**M1** kapandı: dış API itme izi artık yazılır).
- Downgrade eski CHECK'i NOT VALID ekler (dis_api izleri silinmez).
- `pvq_app` ve `pvq_api` UPDATE/DELETE yapamaz. Saklama temizliği (`denetim_service.temizle`; yalnız `giris`, `giris_basarisiz`, `kiraci_goruntule`,
  `PVQUANT_DENETIM_SAKLAMA_AY` > 0) DB sahibi bağlamında worker'da koşar ve **kendi izini** bırakır (`denetim_temizlik`: silinen, saklama ayı, eylemler).
- `ix_denetim_nesne (nesne_tur, nesne_id, zaman)`: bir santralın değişiklik geçmişi.
- Kiracı okuması için RLS politikası AYRI KARAR; okuma API'de `tenant_id` ile süzülür (`/v1/kurulus/denetim`).

## Ayrıntı standardı (ayar değişiklikleri)

`denetim_service.ayar_degisikligi_kaydet` → `{"degisen": {alan: {"eski", "yeni"}}, "ayar_sha": {"eski", "yeni"}, …ek}`. Damga
`services/ayar_damgasi.ayar_sha16(params_json)`: hesabı etkileyen santral ayarlarının (tarife, EAK/kısıt, KÜPST geçersiz kılma, pozisyon,
segment/UEVÇB/DSG/toplayıcı, LÜY, uzlaştırma girdisi/sayaç türü, EPİAŞ santral kimliği, lisans yıllık üretimi, depolama) kanonik sha'sı.
Fizik terimleri ve alarm kuralları damga dışıdır (tahmin/alarm katmanı); izleri `degisen` taşır.

Standarda geçen uçlar: tarife, EAK/pozisyon (`eak_ayar`), segment (`santral_segment`), EPİAŞ santral kimliği, sayaç ayarı (dış API: kapsam
`dis_api`). Yeni izler: `santral_ekle`, `alarm_kural_ayar` (alıcı adresleri yazılmaz, yalnız sayı), `fizik_terim_ayar`, `paylasim_ekle/iptal`,
`elle_kosu`, `scada_yukle` (dosya adı, damga tipi, parti kimliği, satır sayısı), `iki_adim_ac/kapat/kurtarma_yenile`, `webhook_dene` (HTTP durumu),
platform `parola_degistir`. `webhook_ekle` URL'si maskelenir (`maskele_url`: sorgu dizgisi ve kullanıcı bilgisi düşer).

## Etkilenen hesaplar

FEM sonucu `meta.ayar_sha` taşır (çıktı sürümü 1.1). `GET /v1/kurulus/denetim/{iz_id}/etkilenen` → izin `ayar_sha.yeni` damgasından farklı
damgayla, izden ÖNCE hesaplanmış `finansal_etki_sonuc` satırları (dönem, hesap zamanı, eski damga, hesap durumu). Yeniden hesaplamaz; gece işi
girdi damgası değiştiği için yeni sonucu yazar (F4-G `ayni_girdili_kayit`), ya da `taze=1` ile anında hesap istenir. Damgasız iz (v2.602 öncesi
ya da damga dışı alan) `durum: damgasiz` döner. v2.601 öncesi sonuç kayıtlarının damgası yoktur; listede kalır ve `damgasiz_kayit` sayısıyla ayrılır.

## Yapılmayan

- Portföy sonuçları için etkilenen sorgusu (santral damgası üye bazında; portföy meta `girdi.santraller` zaten üye sha'larını taşır).
- Kiracı RLS politikası; izlerin dışa aktarımı; eski izlerin geriye dönük damgalanması.

**Saklama temizliği (v2.606 düzeltmesi):** uygulama rolleri `denetim_izi`'nde UPDATE/DELETE yapamaz; `denetim_service.temizle` yalnız `SECURITY DEFINER denetim_izi_temizle(eylemler, ay)` işlevini çağırır (platform kapsamı, `TEMIZLENEN_EYLEMLER`, `ay` aydan eski). Bu, pvq_api için tek izinli silme yoludur.
