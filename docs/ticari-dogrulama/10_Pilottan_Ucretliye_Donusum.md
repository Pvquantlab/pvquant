# 10 — Pilottan ücretliye dönüşüm süreci (Faz 8, F8-H — 13.11.2026)

> **Durum: pilot yok, teklif yok, dönüşüm yok.** Bu belge süreci ve kayıt alanlarını önceden tanımlar. «Teknik başarı ≠ ödeme istekliliği» (06/07); fiyat formüllü ve sayısız (09);
> canlı faturalama ayarı yok (ödeme altyapısı entegre değil; tahsilat panel dışında); abonelik durumu yönetim panelinden değiştirilir (Faz 6: pilot → aktif, gerekçe zorunlu, iz).
> Hiçbir adım müşteriyle iletişim içermez; iletişim gerektiren adımlar `14` izin listesine düşer.

## 1. Süreç (pilot başlangıcından karara)

| Adım | İçerik | Kanıt / kayıt | Kim karar verir | Kapı |
|---|---|---|---|---|
| 1. Uygunluk | 06/07 giriş şartları G1–G9 + 04 §7 nitelik matrisi (nitelikli) + sinyal ≥ 4 | 05 kaydı; nitelik sonucu | PVQuant (kullanıcı) | hepsi yoksa pilot başlamaz |
| 2. Başarı ölçütü (önceden) | 06/07 Z/B/G eşikleri **yazılı ve iki tarafça kabul**; «teknik kabul ≠ satın alma» cümlesi pilot belgesinde | pilot protokolü eki (imzalı/yazılı) | iki taraf | eşik sonradan değiştirilmez |
| 3. Karar vericiler | bütçe sahibi (09 E2), teknik sahip, veri sahibi — rol düzeyi; kişi adı dosyaya yazılmaz | 05 başlık `karar_verici_mi`; 09 `butce_sahibi_rolu` | müşteri | bütçe sahibiyle en az bir görüşme pilot bitmeden (04 §5 basamak 5) |
| 4. Gösterilen değer | pilot sonunda: 06/07 kabul raporu (teknik), 08 raporu varsa «varsayımsal fark» (nitelikli), kullanım izleri — yalnız bugün kaydedilenler: giriş (denetim izi «giris»), rapor üretimi (`report_log`), koşu sayısı (`forecast_runs`), dış API/webhook (`kullanim_sayac`), KGÜP beyan kayıtları (modül `kgup`); «rapor indirme» ayrı sayılmaz | rapor kimlikleri; kullanım özeti | PVQuant | değer «gösterilir», iddia edilmez; tasarruf dili yok |
| 5. Pilot kapanış incelemesi | kabul sınıfı (teknik kabul / şartlı / değerlendirilemedi), kullanım, açık sorunlar, müşterinin kendi kelimeleriyle değer ifadesi, sonraki adım | `pilot_kapanis` kaydı (§3) | iki taraf | 60. gün ± 7 |
| 6. Teklif | 09 §6 formüllü mektup, sayılar kullanıcı kararıyla; kapsam = pilotta kullanılan modüller + talep edilenler; süre; kurulum kalemi | teklif tarihi, sürüm | kullanıcı | **gönderim izinle** (14); 14 gün ÖNERİ |
| 7. Kapsam ve sözleşme şartları | plan (Standart/Kurumsal), dilim, modüller, veri işleme sözleşmesi, fesih, destek, veri sahipliği; «vaat edilmeyenler» maddesi | sözleşme taslağı (hukuki inceleme kullanıcıda) | iki taraf | fiyat dışı şartlar önce netleşir |
| 8. Karar | kabul / ret / erteleme; ret ve ertelemede **gerekçe sınıfı** (§2) | `teklif_sonucu`, `ret_gerekcesi_sinifi` | müşteri | — |
| 9. Devir | kabulde: abonelik pilot → aktif (yönetim paneli, gerekçe + iz), plan/modül/kota ayarı, veri hattı kalıcı, iletişim kanalları; **devir belgesi** (§4) | abonelik geçmişi (Faz 6), devir belgesi | kullanıcı | ödeme kaydı panel dışı (fatura/ödeme belgesi) → 09 basamak 5 |
| 10. Ret/erteleme sonrası | pilot verisi müşteri isterse silinir; sona_erdi durumu (salt okuma yalnız zorla kipinde — bugün uyarı kipi); öğrenim kaydı 11/12'ye | durum geçmişi | kullanıcı | — |

## 2. Ret / erteleme gerekçesi sınıflaması (ürün itirazı ↔ engel)

| Sınıf | Alt tür | Örnek müşteri cümlesi (kayıt: aynen) | Ne öğretir | Nereye |
|---|---|---|---|---|
| **Ürün itirazı** | doğruluk yetersiz / modül eksik / kullanılabilirlik / güven (yöntem) | «kış aylarında sapma büyük», «talimat uzlaştırması yok» | ürün yol haritası; 15 §14 | Iterate |
| **Değer itirazı** | problem küçük / mevcut çözüm yeterli / toplayıcı zaten taşıyor | «dengesizliği toplayıcı üstleniyor» | segment hipotezi çürütme (02 §4) | Iterate/Stop |
| **Fiyat/yapı itirazı** | seviye / yapı (santral↔MW) / sözleşme süresi | — | 09 kalibrasyon | Iterate (fiyat) |
| **Bütçe engeli** | bütçe dönemi / yetki / grup merkezi | «bütçe Ocak'ta» | zamanlama; kuruluş süreci | Erteleme |
| **Satın alma engeli** | tedarikçi kaydı / referans isteği / hukuki inceleme / yabancı para | — | süreç; 12 risk | Erteleme |
| **Veri engeli** | veri paylaşım izni / KVKK / SCADA erişimi / EPYS dışa aktarım | — | 06 G2, 08 G1 | Erteleme / Iterate (ürün: bağlayıcı) |
| **Entegrasyon engeli** | BT güvenlik / API / mevcut platform (rakip) ile yan yana | — | ortaklık/entegrasyon (03 §4) | Iterate |
| **Zamanlama** | YEKDEM kararı / 30.11 / Aralık uzlaştırma / 2027 belirsizliği | — | takvim | Erteleme |

Kural: her ret tek **birincil** sınıfla + varsa ikincil; sınıflama iki kodlayıcıyla (04 §6 kuralı); ürün itirazı ile engel **toplanmaz** (11'de ayrı sütun).

## 3. Pilot kapanış incelemesi — kayıt alanları

`pilot_id, kurulus_kodu (AD-xx), segment, baslangic, bitis, kabul_sinifi (teknik kabul / şartlı / değerlendirilemedi), Z_karsilandi, B_karsilandi, G_notu, kullanim_giris_gun (denetim), kullanim_rapor_uretim (report_log),
kgup_beyan_sayisi, 08_raporu_var (evet/hayır; dönem sayısı), musteri_deger_ifadesi_aynen, acik_sorunlar, sinyal_basamagi, teklif_tarihi, teklif_sonucu, ret_gerekcesi_sinifi, odeme_basamagi, sonraki_adim`
(05 CSV ile aynı kuruluş kodu; kişi adı yok).

## 4. Devir belgesi (kabulde; iki sayfa)

1. Taraflar (kuruluş kodu + tüzel ad yalnız sözleşmede), plan, dilim, modüller, kotalar; abonelik başlangıç/bitiş; pilot kabul raporu kimliği.
2. Veri: kaynaklar, yetkiler, veri işleme sözleşmesi referansı; müşteri verisinin sahipliği; silme talebi süreci.
3. Hizmet: koşu takvimi (gece + gün içi), KGÜP öneri saati, raporlar, alarm kanalları (e-posta/webhook), destek kanalı ve süreleri (Kurumsal: destek_oncelik).
4. Vaat edilmeyenler: tasarruf/kazanç/garanti yok; TPYS bildirimi PVQuant tarafından yapılmaz; 15 dk uzlaştırma ve talimat/TELMT kapsam dışı; depolama modeli yok.
5. Ödeme: fatura dönemi ve kanal (panel dışı); abonelik durumu geçişleri (sona_eriyor 30 gün önce, yenileme).
6. İmza/onay alanları (rol düzeyi).

## 5. Dürüstlük kuralları

- Dönüşüm sayısı yalnız 09 basamak 3–5 ile; «sözlü evet» dönüşüm değildir.
- Ücretsiz pilot ödeme sinyali üretmez → kapanışta teklif zorunlu (09 T3).
- Her ret 11'e ürün itirazı / engel ayrımıyla, 12'ye risk olarak işlenir; başarısız pilot raporlanır («değerlendirilemedi» ≠ «başarısız»).
- Devir belgesinde ve teklifte rakip adı, kişi adı, TL vaadi yok.
