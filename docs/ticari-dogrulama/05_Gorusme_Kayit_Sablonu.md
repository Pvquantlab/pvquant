# 05 — Görüşme kayıt şablonu (Faz 8, F8-D — 13.11.2026)

> `faz2/E_Gorusme_Rehberi.md` §8 şablonunu (başlık, soru bazlı CSV, 24 saat sentezi, veri koruma) **genişletir**; E'deki alanlar aynen kalır. Makine okunur kopya:
> `gorusme_kayit_sablonu.csv` (yalnız başlık + biçim örneği satırı; **içerik boş — hiç görüşme yapılmadı**). Kişi adı, telefon, e-posta, UEVÇB kodu, santral adı yazılmaz
> (E §8.4); kuruluş adı ↔ `kurulus_kodu` eşlemesi erişimi sınırlı ayrı dosyada (`03`'teki AD-xx kimliği kullanılabilir).

## 1. Görüşme başlığı (görüşme başına bir kayıt)

```
gorusme_id: G-<persona>-<sıra>      (ör. G-LS-01)          | kurulus_kodu: AD-xx (03) ya da K-<sıra>
tarih: GG.AA.YYYY | süre_dk: | kanal: yüz yüze / video / telefon | görüşmeci: (kısaltma) | ikinci_kodlayıcı:
segment: A / B / C / D            | persona_kodu: LS / TC / DSG / TP / GTŞ / İŞ / EPC / LL
rol: (unvan düzeyi; kişi adı yazılmaz) | karar_verici_mi: evet / hayır / kısmen
portfoy: MW aralığı (<5 / 5–20 / 20–100 / >100) | santral sayısı aralığı | YEKDEM (evet/hayır/karışık; son yıl) | DSG/toplayıcı (üye / grup tarafı / yok)
pvquant_temasi: var / yok | pvquant_duymus: evet / hayır | rakip_platform: var (ad yazılmaz) / yok / bilinmiyor
kvkk_acik_riza: alındı (tarih) | ses_kaydi: evet / hayır
sinyal_basamagi: 1–6 (04 §5)      | siddet_puani: sıklık × maliyet × yetersizlik = (04 §6) ya da «gösterge (K1)»
nitelik_sonucu: nitelikli / izle / değil (04 §7) + gerekçe
```

## 2. Soru bazında kayıt (CSV; her soru için bir satır)

| Sütun | İçerik | Kural |
|---|---|---|
| gorusme_id, kurulus_kodu, segment, persona | başlıktan | — |
| soru_no | S1–S20 (E), D1–D7, Y1–Y8 (04), YDK (yedek), AÇ (açılış/kapanış) | — |
| hipotez | H1–H20 (E) ya da Y1–Y8 (04 §3; Y numarası hipotez kimliğidir) ya da «—» | — |
| yanit_ozeti | 1–3 cümle, görüşmecinin özeti | yorum katmaz |
| musteri_kelimesi_aynen | müşterinin terimi/cümlesi (ürün dili sözlüğü için) | «ceza» derse aynen |
| kanit_duzeyi | K1 söz / K2 tarihli somut örnek / K3 belge-ekran | destek/çürütme yalnız K2/K3 |
| kanit_turu | ekran / dosya / sözleşme özeti / yazı / yok | — |
| destek_mi | DESTEK / ÇÜRÜTME / NÖTR | — |
| curutme_kaniti | **zorunlu alan**: hipotezi zayıflatan ne söylendi (boşsa «yok» yazılır) | E §7 #12 |
| sayi_varsa, saat_varsa | müşterinin söylediği sayı (birimiyle) / saat (TSİ) | görüşmecinin sayısı değil |
| arac_dosya_bicim | Excel / portal / API / e-posta / SCADA … | — |
| siddet_siklik, siddet_maliyet, siddet_yetersizlik | 1–3 (yalnız D1–D4 ve S2/S3/S9/S10 satırlarında; K1 ise boş) | 04 §6 |
| sinyal_basamagi | o yanıtın gösterdiği en yüksek basamak (1–6) | 04 §5 |
| not | — | — |

## 3. Görüşme sonrası sentez (24 saat; E §8.3 + ekler)

| Alan | İçerik |
|---|---|
| Saat saat akış | müşterinin anlattığı günlük akış; `E_Musteri_Sesi` §3 ile fark |
| D1–D7 özeti | son problem · fark etme · çözüm · maliyet (kendi ölçüsü) · bugünkü harcama (kalem adı) · onaylayan · yeterli kanıt |
| Hipotez durumu | H1–H20, Y1–Y8: DESTEK / ÇÜRÜTME / NÖTR / SORULMADI (kanıt düzeyiyle) |
| Şiddet puanı | 3 boyut + çarpım + tek satır gerekçe; iki kodlayıcı farkı |
| Sinyal basamağı | 1–6 + kanıt |
| Nitelik | nitelikli / izle / değil + hangi ölçüt eksik (04 §7) |
| Kelime sözlüğü | müşterinin terimleri (ürün dili için; 15 §13) |
| Yeni hipotez / açık soru | listede olmayan konu; E §9 bağlantısı |
| Sonraki adım | ikinci görüşme / veri paylaşımı / yok — **izin gereken dış eylem 14'e** |

## 4. Program özeti tablosu (15 ve 11 için; görüşmeler bittiğinde doldurulur)

| Segment | Hedef | Yapılan | Sinyal ≥2 | Sinyal ≥4 | Puan ≥12 | Nitelikli | Veri paylaşan | Not |
|---|---|---|---|---|---|---|---|---|
| A | 5 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| B | 2–3 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| C | 6 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| D | 2–3 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| LL (teyit) | 2 | 0 | — | — | — | — | — | H15 / D' |
| **Toplam** | 12–15 kuruluş | **0** | 0 | 0 | 0 | 0 | 0 | 13.11.2026: hiç görüşme yok |

## 5. Veri koruma (E §8.4 + ekler)

Kişi adı/telefon/e-posta/UEVÇB/santral adı dosyalara yazılmaz; ekran görüntülerinde maskelenir; ses kaydı yalnız açık rızayla ve 90 gün sonra silinir (öneri);
müşteri uzlaştırma/üretim verisi yalnız ayrı veri işleme sözleşmesiyle, PVQuant üretim ortamına değil ayrı analiz klasörüne; sözleşme metinleri istenmez, kalıp türü yeterli.
