# 11 — Doğrulama puan kartı (Faz 8, F8-H — 13.11.2026)

> 13 ölçü × hedef / gerçek / kanıt; aday başına 9 alan; Go / Iterate / Stop ölçütleri **kanıta bağlı** ve **ÖNERİ** (kullanıcı onaylar). Makine okunur kopya `puan_karti.csv`.
> **13.11.2026 itibarıyla bütün «gerçek» değerler 0**: görüşme, pilot, finansal doğrulama, teklif ve ödeme yapılmadı. Hedefler brief'ten; «başlangıç hedefi, sonuç değil».

## 1. Ölçüler (13)

| # | Ölçü | Hedef (brief / plan) | Gerçek (13.11.2026) | Kanıt kaynağı | Durum |
|---|---|---|---|---|---|
| Ö1 | Görüşülen kuruluş | 12–15 | **0** | 05 başlık kayıtları | Henüz yapılmadı — hazır: 03 kısa liste 15, 04/05 |
| Ö2 | Segment kapsaması (A/B/C/D + GTŞ ≥ 1) | A ≥ 3, B ≥ 2, C ≥ 2 (TP) + DSG ≥ 2, D ≥ 3, GTŞ ≥ 1 (E §5) | 0/0/0/0/0 | 05 | Henüz yapılmadı |
| Ö3 | Problem gösterildi (sinyal ≥ 2: tarihli örnek ya da belge) | ≥ %50 görüşme (ÖNERİ) | 0 | 05 `sinyal_basamagi` | Henüz yapılmadı |
| Ö4 | Şiddet puanı ≥ 12 olan kuruluş | ≥ 5 (ÖNERİ; pilot havuzu) | 0 | 05 şiddet sütunları | Henüz yapılmadı |
| Ö5 | Mevcut harcama kalemi olan (sinyal 3) | ≥ 4 (ÖNERİ) | 0 | 09 E1 | Henüz yapılmadı |
| Ö6 | Pilot taahhüdü (sinyal ≥ 4: veri + gizlilik + tarih) | ≥ 3 | 0 | 05; veri işleme sözleşmesi | Henüz yapılmadı |
| Ö7 | Lisanslı GES pilotu başlatılan | 1–2 | 0 | 06 G1–G9 kaydı | Henüz yapılmadı — hazır: 06 |
| Ö8 | Toplayıcı/DSG pilotu başlatılan | 1 | 0 | 07 | Henüz yapılmadı — hazır: 07 |
| Ö9 | Pilot teknik kabul (Z + B) | başlatılanların ≥ %50 (ÖNERİ) | 0 | 06/07 kabul kontrol listesi | Henüz yapılmadı |
| Ö10 | Finansal doğrulama dönemi (resmî bildirimle mutabık + karşı-olgu) | ≥ 2 dönem, ≥ 1 kuruluş | 0 | 08 raporu + CSV | Henüz yapılmadı — hazır: 08; en erken Ocak 2027 |
| Ö11 | Teklif istenen / gönderilen (09 basamak 2–3) | ≥ 3 istek (ÖNERİ) | 0 | 09 `teklif_istendi` | Henüz yapılmadı |
| Ö12 | Kabul edilen teklif / imza (09 basamak 3–4) | ≥ 1 | 0 | sözleşme | Henüz yapılmadı |
| Ö13 | Fiili ödeme (09 basamak 5) | ≥ 1 | 0 | fatura/ödeme kaydı (panel dışı) | Henüz yapılmadı |

Ek sayımlar (ölçü değil, bağlam): ret gerekçesi dağılımı (ürün itirazı / engel — 10 §2); ürün boşluğu listesi (15 §14); dış eylem izin sayısı (14).

## 2. Aday başına 9 alan (puan_karti.csv ikinci bölüm; her AD-xx için bir satır — bugün hepsi boş)

`aday_id, segment, sinyal_basamagi (1–6), siddet_puani (1–27 | gösterge), nitelik_sonucu (nitelikli/izle/değil), pilot_durumu (yok/başladı/kabul/şartlı/değerlendirilemedi), finansal_dogrulama_donem (0–n),
teklif_durumu (yok/istendi/gönderildi/kabul/ret/erteleme), odeme_basamagi (0–5)` — ret varsa `ret_gerekcesi_sinifi` (10 §2) ek sütun.

## 3. Go / Iterate / Stop ölçütleri (ÖNERİ; her biri kanıta bağlı; karar kullanıcıda)

| Karar | Koşul (hepsi birden) | Kanıt | Anlamı |
|---|---|---|---|
| **GO** (ticari doğrulama var; satış/ölçek kararı) | Ö1 ≥ 12 **ve** Ö3 ≥ %50 **ve** Ö9 ≥ 1 teknik kabul **ve** Ö12 ≥ 1 **ve** Ö13 ≥ 1 | 05, 06/07, sözleşme, ödeme | problem gösterildi, ürün teknik olarak kabul edildi, en az bir kuruluş ödedi |
| **ITERATE** (talep var, dönüşüm yok) | (Ö3 ≥ %50 **ya da** Ö4 ≥ 5) **ve** Ö12 = 0; ret gerekçeleri ağırlıkla **ürün itirazı** ya da **fiyat/yapı** | 10 §2 dağılımı | problem gerçek, ürün ya da fiyat uymuyor → 15 §14 yol haritası, 09 kalibrasyon, ikinci tur |
| **ITERATE (engel)** | Ö3 ≥ %50, Ö6 ≥ 1 ama ret/erteleme ağırlıkla **bütçe/satın alma/veri/entegrasyon engeli** | 10 §2 | ürün değil süreç; satış kanalı/ortaklık (03 §4) ve veri bağlayıcıları |
| **STOP (bu segmentte)** | Ö1 ≥ 8 **ve** Ö3 < %30 **ve** Ö5 = 0 **ve** Ö6 = 0 | 05 | problem gösterilmiyor, kimse ödemiyor, kimse veri vermiyor → segment hipotezi çürütüldü (E §4 ÇÜRÜTME) |
| **BELİRSİZ** | Ö1 < 8 ya da persona başına < 3 | — | sonuç «gösterge»; karar verilmez, program uzatılır |

Eşikler görüşmelerden önce yazıldı (seçim yanlılığına karşı); değiştirilirse gerekçe ve tarih 00'a.

## 4. Okuma kuralları

- «Hazır» ≠ «yapıldı»: her satırda hazır olan belge ayrı yazılır.
- Gerçek değerler yalnız 05/06/07/08/09 kayıtlarından; sözlü beyan sayılmaz.
- Rapor (15) bu tabloyu olduğu gibi taşır; yuvarlama ve yorum yok.
