# Dış API sözleşmesi (v2.603, Faz 4 F4-I)

## Kimlik ve kapsam

- `X-API-Key: pvq_<prefix>_<secret>`; sunucu yalnız sha256 saklar. Kapsamlar (`ext/platform/api_anahtar.KAPSAMLAR`): tahmin:oku, kgup:oku,
  gerceklesen:oku, gerceklesen:yaz, alarm:oku, rapor:indir, santral:yaz ve v2.603 ile **veri_kalitesi:oku, portfoy:oku, finans:oku**.
- **Santral kapsamı** (göç v2603 `api_keys.plant_ids`): anahtar üretilirken `plant_ids` verilirse yalnız o santraller; NULL = kiracının tüm santralleri
  (eski anahtarlar değişmez). Kiracıda olmayan santral kimliği 422. `/v1/dis/santraller` süzülür; santral uçları kapsam dışında **403
  `santral_kapsam_disi`**, kiracıda olmayan santralda **404 `santral_yok`** (başka kiracının santrali de 404: varlık sızdırılmaz).
- Anahtarla yapılan yazmalar denetim izinde `dis_api` kapsamında (F4-H).

## Hata gövdesi ve şema sürümü

- `/v1/dis/*` yollarında her hata `{"detail": …, "kod": …, "schema_version": …}`; doğrulama hatası (422) ayrıca `alanlar: [{konum, mesaj}]`.
  Kodlar: anahtar_gecersiz (401), kapsam_yetersiz / santral_kapsam_disi / yetki_yok (403), santral_yok / portfoy_yok / kosu_yok / bulunamadi (404),
  kosu_yok (koşu yoksa) / hesaplanamadi (409, ör. KGÜP eksik saat), istek_gecersiz (422), oran_siniri (429). Panel yolları FastAPI varsayılanında kalır.
- Her `/v1/dis` yanıtı `X-PVQuant-Schema: <sürüm>` başlığı taşır; yeni uçların gövdesinde `schema_version`. Eski liste gövdeleri (ör. santraller)
  biçimini korur (dizi); sürüm başlıkta.

## Uçlar

| Uç | Kapsam | Not |
|---|---|---|
| `GET /v1/dis/santraller` | tahmin:oku | künye alanları (F4-E); santral kapsamıyla süzülü |
| `GET /v1/dis/santral/{id}/tahmin` | tahmin:oku | ETag = koşu |
| `GET /v1/dis/santral/{id}/tahmin-arsivi?hedef&yayin_oncesi` | tahmin:oku | **yeni**: o anda yayımlanmış koşu (F4-B); geriye bakışlı koşu dönmez |
| `GET /v1/dis/santral/{id}/kalite?bas&bit` | veri_kalitesi:oku | **yeni**: bayrak/nitelik dağılımı (bayraksız satır «bayraksiz», uzlaştırmaya girmez), uzlaştırmaya uygun saat, tazelik (santralın tamamı), künye (pencere içi kaynaklar, son geliş) |
| `GET /v1/dis/santral/{id}/kgup?fmt=json` | kgup:oku | yan etkisiz önizleme |
| `GET …/kgup?fmt=csv|eak` | kgup:oku | **eski**: arşive yazar; `Deprecation: true` + `Warning` başlığı |
| `POST /v1/dis/santral/{id}/kgup {gun, kantil, fmt}` | kgup:oku | **yeni**: dosyayı üretir ve arşivler (yan etkili işlem POST'ta) |
| `GET /v1/dis/portfoyler?tarih&n&sonraki` | portfoy:oku | **yeni**: imleçli sayfalama (`sonraki` kimlik imleci, n ≤ 200) |
| `GET /v1/dis/portfoy/{id}/finansal-etki?donem&uretim` | finans:oku | **yeni**: F3-G portföy finansal etkisi; meta: kural sicili sha/sürümü, DSG fiyat sha, hesap durumu, çıktı sürümü, girdi sha |
| gerceklesen, kaynak-saatlik, alarmlar, rapor-donem, ayarlar, uretim-dosyasi, toplayici, kgup/surumler | mevcut | santral kapsamı denetimi eklendi |

## Çekirdek sınırı

`io/bulut/solaredge_oauth.py` artık `services` içe aktarmaz: belirteç yenilemede platform uygulaması kaydı, istemciyi kuran servis
(`bulut_cekis_service`) tarafından `uygulama_getir` ile enjekte edilir; verilmemişse yenileme açık hatayla durur. Bekçi testindeki istisna düştü.

## Yapılmayan

- Eski liste uçlarına (santraller, alarmlar, kgup/surumler) imleç eklenmedi (gövde biçimi korunur); `n` ile sınırlı.
- OpenAPI şeması ayrı sürümlenmedi; `schema_version` tarih dizgisidir.
