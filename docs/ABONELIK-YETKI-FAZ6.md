# Abonelik, yetkilendirme ve kota — Faz 6 (v2.609)

Tarih: 13 Kasım 2026. Kapsam: Pilot / Standart / Kurumsal planlarının yönetilebilir abonelik + hak (entitlement) + kota sistemine dönüşmesi; platform
ve müşteri paneli yüzeyleri; kapılar (uyarı kipi). Tahmin çekirdeği, uzlaştırma formülleri ve kalibrasyon DEĞİŞMEDİ. Fiyat kodda YOK (yalnız belge).
Plan ve kanıtlar: `~/Desktop/PVQuant_Faz6_Ticari_Model/` (00 plan + paket blokları, 04/05/06 ticari belgeler, 07 test turları, 08 teslim raporu, kanit/).

## 1. Şema — göç `v2609_abonelik` (F6-A)

| Nesne | İçerik | Erişim |
|---|---|---|
| `planlar` + 3 sütun | `ac_mw_limit NUMERIC`, `portfoy_limit`, `aylik_isleme_saat_limit` (NULL = sınırsız) | mevcut |
| `plan_modulleri(plan_ad, modul, dahil, sinir JSONB)` | plan → modül varsayılanları; tohum Pilot 5 / Standart 11 / Kurumsal 15 | platform yazar |
| `kiraci_abonelik(tenant_id PK → tenants ON DELETE CASCADE, plan, durum, baslangic, bitis, pilot_bitis, modul_ek[], modul_cikar[], kota_ezme JSONB, sozlesme_notu, teklif_ref, guncelleme, guncelleyen)` | kiracının aboneliği; CHECK durum ∈ 7 durum; RLS + FORCE; pvq_app SELECT, pvq_api S/I/U | tek kaynak |
| `abonelik_gecmisi(id, tenant_id, zaman, aktor, eylem, eski, yeni, gerekce)` | yalnız ekleme (UPDATE/DELETE yetkisi yok); RLS | denetim |

Geri doldurma: `tenants.plan IS NULL → 'pilot'`; her kiracıya kayıt (suspended → askida; pilot bitişi = created_at + 60 gün, geçmişse sona_erdi; diğerleri aktif,
bitişsiz) + geçmişe `geri_doldurma`. `tenants.plan` ve `status` korunur ve abonelikle **eşzamanlı** yazılır (çift yazım; eski okuyucular bozulmaz).

## 2. Hak servisi — `src/pvquant/services/yetki_service.py`

- Sözlükler: `DURUMLAR` (pilot · aktif · sona_eriyor · yenileme_bekliyor · askida · sona_erdi · feshedildi) + `DURUM_ETIKET`; `MODULLER` (15 kod: ad, durum
  mevcut/sinirli/gelistirmede/is_bazli/surec); `KOTALAR` (8 alan → `planlar` sütunu, ad, birim); `KOTA_DURUM_ETIKET` (sağlıklı · dikkat ≥%80 · **dolu =%100
  «sınıra ulaşıldı»** · aşıldı >%100 · sınırsız · ölçülmüyor); `KAPI_KODLARI`; `PILOT_GUN = 60`, `SONA_ERIYOR_GUN = 30`.
- Saf kurallar: `durum_turet(plan, status, kayit, bugun)` (feshedildi status'tan ÖNCE ve terminal; suspended → askida; sona_erdi yapışkan; pilot → pilot_bitis;
  diğerleri bitis: yok → aktif, geçti → yenileme_bekliyor, ≤30 gün → sona_eriyor), `moduller_birlestir`, `kota_durumu(limit, kullanim, ezme=)`,
  `varsayilan_kayit`, `kapi_hukmu` (§5).
- DB: `haklar(tenant_id)` **60 sn süreç içi önbellek** (4 işçide en çok 60 sn eski hak — kapı tasarımı bu kabulle), `onbellek_dusur`, `musteri_gorunumu`
  (sözleşme iç notu yüzeye çıkmaz, `sozlesme_istisnasi` bayrağı), `modul_var`, `kota(alan, artis)` («bu işlem yapılırsa» öngörüsü; ezme kaynağı korunur).
- Zorlama kipi: `Settings.abonelik_zorlama: "uyari" | "zorla"` (varsayılan **uyari**; env `PVQUANT_ABONELIK_ZORLAMA`). «zorla» yalnız açık onayla.

## 3. Yaşam döngüsü — `abonelik_service.py` (F6-C)

`varsayilan_olustur` (idempotent), `senkron` (tenants.plan/status → abonelik; platform `kiraci_olustur/guncelle` kancaları), `GECISLER` (elle hedef yalnız
aktif / askida / feshedildi; aktif→aktif = yenileme; feshedildi terminal), `guncelle(…, gerekce zorunlu)` (plan / bitiş / pilot bitişi / modül ek-çıkar /
kota ezme / sözleşme notu / teklif ref / durum; askı ve fesih `tenants.status=suspended` + `users.oturum_surumu` artar → oturumlar düşer; tarih
verilince durum yeniden türer; dizi sırası normalize), `gecmis`, `gece_turet` (worker `gece_abonelik` 03:12 TSİ; yapışkan durumlara dokunmaz).

## 4. Kullanım ve kota — `kullanim_service.py` (F6-B)

Anlık sayımlar tek SQL (`ANLIK_ALT_SORGU`): etkin santral, AC MW (AC sınırı yoksa DC «yaklaşık»), etkin kullanıcı, etkin portföy; aylık: dış API
(`kullanim_sayac`), rapor (`report_log`), işlenen üretim verisi (`scada_hourly` tazelik koşulu). Hüküm ve sözcük uçtan; arayüz oran hesaplamaz
(`KotaRozet` yalnız çizer). Bilgi amaçlı kotalar (rapor, işleme saati) kapı taşımaz.

## 5. Kapılar — `apps/api/deps.py` (F6-E)

`kapi_hukmu(tenant_id, modul=, alan=, artis=1, yazma=)` → None | {kod, http, mesaj, ayrinti}: (1) yazma + abonelik sona_erdi/askida/feshedildi → 403
(okuma serbest); (2) modül dâhil değil → 403 `modul_kapali`; (3) kota öngörüsü aşıldı → 409 `kota_asildi` {limit, kullanim, kaynak} (dolu + 1 = aşım).
`modul_gerekli(modul, yazma=)`, `kota_kontrol(alan, artis=)`, `abonelik_kapisi_uygula`: **uyarı kipi** → iş yapılır; başlık `X-PVQuant-Abonelik: uyari`
+ `X-PVQuant-Abonelik-Kod` (bağımlılık yanıtı + main.py middleware `request.state.abonelik_uyari`, dosya/304 dönen uçlarda da); denetim izi
`abonelik_uyari` kiracı × kod × nesne başına saatte bir (süreç başına). **Zorla kipi** → HTTP 403/409, detail {kod, mesaj, …}; dış API gövdesi
`{detail, kod, schema_version}`. UUID olmayan kiracı kimliği / kayıt yoksa kapı sessiz geçer.

| Uç | Kapı |
|---|---|
| `POST /v1/plants`, `POST /v1/plants/{id}/geri-al` | kota `santral` |
| `POST /v1/takim` | kota `kullanici` |
| `POST /v1/api-anahtarlari`, `POST /v1/webhooklar` | modül `dis_api` (yazma) |
| `POST /v1/paylasimlar` | modül `paylasim` (yazma) |
| `GET/POST /v1/plants/{id}/mutabakat` | modül `mutabakat` (POST yazma) |
| `PUT /v1/plants/{id}/rapor-gonderim` | modül `rapor_gelismis` (yazma) |
| `GET …/finansal-etki` (santral, kuruluş, portföy) | modül `finansal_etki` |
| `POST /v1/portfoyler`, `POST /v1/portfoyler/{id}/uyeler` | modül `portfoy_dsg` (yazma) + kota `portfoy` (oluşturma) |
| `/v1/dis/*` (anahtar kapısı) | modül `dis_api` + kota `aylik_dis_api`; iz kapsamı `dis_api` |

Kapısız (her planda dâhil): tahmin, doğruluk, veri yükleme, alarm, KGÜP.

## 6. Uçlar

| Uç | Rol | Not |
|---|---|---|
| `GET /v1/abonelik` | her rol | `musteri_gorunumu`; uyarılar, kotalar, modüller, sözlük |
| `POST /v1/abonelik/talep` | yazma yetkisi | teklif / yükseltme talebi → `vitrin_basvurulari` (kaynak yukseltme \| sanayi_ges); hedef plan `planlar`'dan, modül sözlükten; 10/saat; denetim `abonelik_talep`; posta yok |
| `GET/PUT /v1/yonetim/kiracilar/{tid}/abonelik` | platform / gerekçe zorunlu; fesih sahip | `model_fields_set`; denetim `abonelik_guncelle` |
| `PUT /v1/yonetim/planlar/{ad}/moduller` | sahip | `plan_modul_guncelle`; denetim `plan_modul_guncelle` |
| `GET /v1/yonetim/kullanim`, `/planlar` | platform | kota hükümleri, modüller adıyla |

## 7. Arayüz

- Platform: Müşteri detayı «Abonelik» kartı (`features/yonetim/Abonelik.tsx`; düzenleme formu, askı/etkinleştir/fesih, yalnız-ekleme geçmişi; ödeme
  «entegre değil»), Planlar 8 limit + modül onay kutuları, Kullanım kota rozetleri, Başvurular «Kaynak» sütunu.
- Müşteri: Ayarlar › «Aboneliğiniz» (`features/sayfalar/Abonelik.tsx`; plan ve süre / sınırlar ve kullanım / dâhil özellikler / uyarılar / «panelden
  doğrudan satın alma yoktur» / talep formu yalnız yazma yetkisi), `ModulNotu` altı yerde (dâhilse çizilmez; uyarı kipinde sayfa çalışır),
  `lib/abonelik.ts` (tek istek; hata önbelleklenmez; jetona bağlı), `KotaRozet` paylaşılan parça, `KotaDurum` tek tip, `client.ts detayMesaji`.
- Sahte API fixture'ları: `sahte-api.mjs` (platform), `sahte-api-panel.mjs` (müşteri).

## 8. Dürüstlük kuralları (testle zorlanır)

Fiyat/ödeme/satın alma düğmesi yok; «tasarruf / kazanç / garanti / ceza» yok (dil bekçisi `dil.test.ts` Abonelik.tsx'i tarar); hüküm ve sözcük uçtan;
sayı uydurulmaz (ölçülmüyor → «—»); yeni yetenek vaadi yok (15 dk / 7 gün gibi seçenekler belgede de yok); zorlama kipi varsayılan uyarı.

## 9. Testler

`test_abonelik_v2609` (8: saf kurallar, göç tohumu, DB, kanca, kota kenarları «dolu»), `test_kullanim_v2609` (2), `test_abonelik_yasam_v2609` (5),
`test_abonelik_talep_v2609` (2), `test_abonelik_kapilari_v2609` (9: altı senaryo × iki kip, gerçek iz, Response başlığı); web `yonetim.test.ts`,
`abonelik.test.ts`, `dil.test.ts`. Ayrıntı ve tam takım sonuçları: `07_Test_Turlari.md`.

## 10. Açık kararlar (08 §15)

Zorla kipini açma (ve kiracı başına muafiyet); pilot ücretli mi; kota ezme / modül istisnası sahip-only mu; vitrin SSS metni (04 §6); Sanayi GES;
fiyat sayıları (görüşme + 05 ölçümü); ikinci işçi eşiği (05 §2.2); `test_kosu_kunyesi_v2572` duvar saati testi (Faz 1, ayrı iş).
