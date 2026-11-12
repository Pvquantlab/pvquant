# Santral kimliği (Faz 4 F4-E, v2.599)

Tarih: 12 Kasım 2026. Göç: `alembic/versions/v2599_santral_kunye.py`. Kod: `src/pvquant/services/santral_kunye_service.py`.
Testler: `tests/test_santral_kunye_v2599.py`. Zaman ve kalite sözleşmeleri: `docs/ZAMAN-SOZLESMESI.md`, `docs/VERI-KALITESI.md`.

## Neden

`plants` tek satırdı, kimlik alanları `params_json`'da 40+ şemasız anahtardı ve geçmişi yoktu: kapasite artışı, AC tavanı değişimi,
segment geçişi ya da UEVÇB kodu düzeltmesi geçmiş dönemlerin hesabını sessizce değiştiriyordu. DC/AC/EAK tanımları da tüketiciye göre
değişiyordu (yükleme kapasite kuralı DC, EPİAŞ anomali tavanı DC, EAK iki kuraldan).

## Tarihli künye (`santral_kunye`)

| Alan | Anlam | Göçte dolduruldu mu |
|---|---|---|
| `gecerli_bas` / `gecerli_bit` | yarı açık geçerlilik aralığı; `NULL` bit = süresiz | kayıt günü / NULL |
| `dc_kwp`, `ac_kw`, `eak_kw` | DC kurulu güç, inverter AC tavanı, emre amade kapasite | `capacity_kwp`, `ac_limit_kw`, `params_json.eak_kw` |
| `baglanti_turu` (`iletim`/`dagitim`), `gerilim_kv` | şebeke bağlantısı | NULL (bilinmiyor) |
| `segment`, `lisans_durumu` (`lisansli`/`lisanssiz`/`muaf`) | ticari segment ve lisans | `params_json.segment`; lisans segmentten türetildi |
| `uevcb_kod`, `eic`, `epias_santral_id` | piyasa kimlikleri | `uevcb`, `epias_santral_id`; EIC NULL |
| `sayac_kimligi`, `olcum_siniri` | sayaç ve ölçüm sınırı (`inverter_ac`/`plant_gross_ac`/`pcc_net`/`settlement`) | NULL |
| `kaynak` (`kayit`/`beyan`/`belge`/`goc`/`epias`), `dogrulama` (`beyan`/`belgeli`/`dogrulandi`), `belge_adi`, `notlar`, `olusturan` | kayıt künyesi | `goc` / `beyan` |

Kural: satır güncellenmez; değişiklik `yeni_surum` ile yeni satırdır, eski satır `gecerli_bit` ile kapanır. Verilmeyen alanlar önceki
sürümden taşınır. Geçmiş tarihli sürüm eklenebilir (yeniden hesap), ama var olan sürümün başlangıcından önce olamaz. Her yazma
`denetim_izi`'ne (`santral_kunye`) düşer: değişen alanlar, önceki değerler, kaynak, doğrulama.

## Çift yazım ve geriye uyum

`plants` «güncel görünüm»dür: `yeni_surum` bugünü kapsıyorsa `capacity_kwp`/`ac_limit_kw` ve `params_json` kimlik anahtarları
(`eak_kw`, `segment`, `uevcb`, `epias_santral_id`) güncellenir; eski okuyucular bozulmaz. `plant_service.olustur` ilk künyeyi
(`kaynak='kayit'`) açar; `plant_service.guncelle` kapasite/AC değiştiğinde yeni sürüm açar ve denetim yazar. Test fixture'ları gibi
`plants`'a doğrudan satır ekleyen yollar künye açmaz; `guncel` None döner ve güç tanımları `plants`'tan okunur (davranış değişmez).

## Güç tanımları — tek yer

`guc_tanimlari(plant, gun, kunye)` → `{dc_kwp, ac_kw, eak_kw, eak{eak_mw, kaynak, bitis?}, ihracat_siniri_kw, kaynaklar}`.
EAK kuralı v2.275 ile aynı: geçici kısıt (bitişe kadar) > EAK alanı > AC tavanı > kurulu güç; EAK AC/DC'yi aşamaz.

| Tüketici | Önce | Şimdi |
|---|---|---|
| `kgup_service.eak_etkin` | kendi if-zinciri | `guc_tanimlari(...)["eak"]` (aynı çıktı) |
| EPİAŞ gerçek zamanlı üretim anomali tavanı | DC kurulu güç | ihracat sınırı (EAK/AC; yoksa DC) |
| Yükleme `over_capacity` bayrağı | 1,05 × DC | 1,05 × AC tavanı (biliniyorsa), yoksa 1,05 × DC |
| Karne gündüz maskesi paydası | `plant["capacity_kwp"]` | `guc_tanimlari(plant)["dc_kwp"]` (aynı değer, tek kaynak) |

## Beyan → üyelik

`params_json.dsg_kodu` / `toplayici_portfoyu` beyanları tarihli portföy üyeliğiyle (F3-A) çakışır. `beyan_uyarilari(tenant, plant)`:
beyan varken açık üyelik yoksa uyarı + geçiş önerisi (DSG koduyla tanımlı portföy bulunduysa `portfoy_id`). Otomatik üyelik açılmaz.
`GET /v1/plants/{id}/kunye` bu uyarıları döndürür.

## API

- `GET /v1/plants/{id}/kunye` → `{guncel, tarihce, guc, uyarilar, sozluk}`.
- `POST /v1/plants/{id}/kunye` (yazma yetkisi) → yeni sürüm; gövde: `gecerli_bas`, künye alanları, `kaynak`, `dogrulama`, `belge_adi`, `notlar`.
- Dış API `GET /v1/dis/santraller` künye alanlarını taşır (`dc_kwp`, `ac_kw`, `eak_kw`, `baglanti_turu`, `gerilim_kv`, `segment`,
  `lisans_durumu`, `uevcb_kod`, `eic`, `epias_santral_id`, `olcum_siniri`, `kunye_gecerli_bas`, `kunye_dogrulama`); eski alanlar
  (`id`, `ad`, `kapasite_kwp`, `tz`) aynen kalır.

## Açık noktalar

- Web Santralim sayfası künyeyi henüz göstermiyor / düzenlemiyor (F4-K).
- `params_json`'daki diğer 36 anahtar (alarm, veri yolu, kirlenme, depolama…) künye değil ayar; şemaya alınmadı.
- `sayac_kimligi`, `eic`, `gerilim_kv`, `baglanti_turu` göçte boş; müşteri/belge ile dolar.
