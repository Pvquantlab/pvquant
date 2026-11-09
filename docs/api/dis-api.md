# PVQuant Dış API (v2.264)

Müşteri sistemlerinin (SCADA/EMS, ticaret masası, portföy yazılımı) PVQuant tahminini kendi tarafına
çekmesi için. Etkileşimli şema: `https://<alan>/docs` (OpenAPI, "Dış API" etiketi).

## Kimlik

- Yönetici, panelde **Kuruluş › Dış erişim** kartından anahtar üretir. Anahtar `pvq_<önek>_<sır>` biçimindedir ve
  **yalnız bir kez** gösterilir; sunucu yalnız sha256 özetini saklar.
- Her istekte başlık: `X-API-Key: pvq_…`
- Kapsamlar: `tahmin:oku` (santral listesi + saatlik tahmin), `kgup:oku` (KGÜP programı, sürüm geçmişi, toplayıcı dosyası), `gerceklesen:oku` (gerçekleşen üretim), `alarm:oku` (alarm listesi), `rapor:indir` (dönem raporu), `santral:yaz` (sayaç ayarı alanları), `gerceklesen:yaz` (üretim dosyası itme, v2.553). Kapsam dışı → 403. (v2.528: dört kapsam canlıya alındı.)
- Oran sınırı anahtar başına dakikada `rpm` (varsayılan 120) → aşımda 429. Geçersiz/iptal/süresi dolmuş → 401.

## Uçlar

| Uç | Kapsam | Ne verir |
|---|---|---|
| `GET /v1/dis/santraller` | tahmin:oku | Kiracının santralleri (id, ad, kWp, saat dilimi) |
| `GET /v1/dis/santral/{id}/tahmin` | tahmin:oku | Son koşunun saatlik P10/P50/P90 (kW, UTC) + koşu kimliği |
| `GET /v1/dis/santral/{id}/kgup?gun=YYYY-MM-DD&kantil=p50&fmt=json|csv` | kgup:oku | KGÜP saatlik program (CSV ya da JSON; `kantil` p10/p25/p50/p75/p90); gün verilmezse İstanbul yarını. Tahmini eksik saat varsa **422** (0 yazılmaz). JSON `sha256`, `kosu`, `sablon.durum` taşır; dosya biçimi resmî TPYS şablonuyla karşılaştırılmadı, gönderim müşterinin TPYS'sinden |
| `GET /v1/dis/santral/{id}/toplayici?gun=YYYY-MM-DD&fmt=csv|xlsx|json&adim=60|15` | kgup:oku | Toplayıcı/DSG program dosyası: P10/P50/P90 MW + EAK; `adim=15` ile çeyrek saatlik veri (15 dk DGP uzlaştırması en erken 1.1.2027, DUY Geçici 40; fiilî tarih EPİAŞ/TEİAŞ duyurusuna bağlı). Kolon adları santralın `toplayici_sablon` eşlemesiyle değiştirilebilir |
| `GET /v1/dis/santral/{id}/kgup/surumler?gun=&n=` | kgup:oku | KGÜP sürüm geçmişi (indirilen dosyalar: sürüm, kaynak koşu, kesim, SHA-256) |
| `GET /v1/dis/santral/{id}/gerceklesen?bas=YYYY-MM-DD&bit=YYYY-MM-DD&kaynak=scada|sayac` | gerceklesen:oku | Saatlik gerçekleşen üretim, kWh, UTC saat başı. `scada`: geçerli SCADA ölçümü (brüt; kaynak scada_dosya / epias_seffaflik). `sayac`: yüklü sayaç verisi (net veriş; kaynak epys/osos/mass/elle, nitelik ölçülmüş/tahmini). En çok 92 gün; verilmezse son 7 Türkiye günü. Uzlaştırmaya esas UEVM değildir. |
| `GET /v1/dis/santral/{id}/alarmlar?n=20` | alarm:oku | Alarm listesi (yeni → eski, en çok 200): kural kodu + Türkçe adı, şiddet, mesaj, zaman, okunma/atama |
| `GET /v1/dis/santral/{id}/rapor-donem?donem=YYYY-MM|YYYY-QN|YYYY&fmt=json|html` | rapor:indir | Dönem raporu (panelin Raporlar › Dönem raporu ile aynı hesap): üretim, gün başı beklentisi, olay kaydı, kullanılabilirlik, temel PR, ay döneminde uzlaştırma kalemleri; `html` indirilebilir dosya. Denetim izine düşer. |
| `POST /v1/dis/santral/{id}/uretim-dosyasi` (çok parçalı `dosya`) | gerceklesen:yaz | v2.553: SCADA / kayıt cihazı dışa aktarımını (CSV, XLSX; ≤50 MB) PVQuant'a iter. Dosya panelden yükleme ile aynı alım hattından geçer (biçim/eşleme algılama, kayıtlı şablon, doğrulama karnesi) ve geçerli saatler üretim serisine yazılır. Cihaz bazlı dosyada tekrar politikası santral ayarından (`itme.tekrar`: sum/mean) gelir; yoksa 422. Yanıt: parti kimliği, satır sayısı, karne. Aynı hat SFTP ile itilen dosyalar için `PVQ_ITME_DIZIN/<santral>/gelen/` klasörünü 10 dakikada bir tarar (hesap açma işletim tarafında). |
| `GET /v1/dis/santral/{id}/kaynak-saatlik?bas&bit&sinir` | gerceklesen:oku | v2.559 (V4): her saatin kaynağı, ölçüm sınırı, niteliği (tam / kısmi / tahmini) ve revizyonu ile gölge görünüm; üretim serisindeki saatle yan yana. En çok 31 gün. Tahmin ve doğruluk bu görünümü kullanmaz; uzlaştırmaya esas UEVM değildir. |
| `PUT /v1/dis/santral/{id}/ayarlar` (JSON gövde) | santral:yaz | Sayaç ayarı alanları: `sayac_turu` (15dk_endeks|diger), `scada_durum` (bagli|kopuk|yok), `scada_kopukluk_baslangic` (YYYY-MM-DD), `uzaktan_acma_var` (bool), `sistem_kullanim_bedeli_tl_ay`, `uzlastirma_girdi` (scada|sayac). Yalnız gönderilen alanlar değişir, null temizler; boş gövde 422. Künye/segment/tarife bu kapsamda değildir. |

`tahmin` yanıtı `ETag: W/"<koşu id>"` taşır. `If-None-Match` ile aynı değeri gönderirseniz koşu değişmediyse
**304** döner (gövde yok) — 60 saniyede bir yoklamak ucuzdur. Bant yoksa `p10_kw`/`p90_kw` `null` gelir.

```bash
curl -H "X-API-Key: pvq_ab12cd34_…" https://<alan>/v1/dis/santral/<id>/tahmin
```

## Webhook (tahmin.yeni)

Sabah koşusu kaydedilince PVQuant, kayıtlı alıcılara `POST` atar. Gövde: santral, koşu kimliği, yerel gün
toplamları (P50 her zaman; P10/P90 yalnız günün tüm saatleri doluysa) ve saatlik ucun adresi.

Başlıklar: `X-PVQ-Event`, `X-PVQ-Timestamp` (Unix saniye), `X-PVQ-Signature: v1=<hex>`.
İmza = HMAC-SHA256(secret, `"<timestamp>." + gövde baytları`). 5 dakikadan eski damgayı reddedin.

```python
import hmac, hashlib, time
def dogrula(secret: str, govde: bytes, basliklar: dict) -> bool:
    t = basliklar["X-PVQ-Timestamp"]; imza = basliklar["X-PVQ-Signature"].split("=", 1)[1]
    if abs(time.time() - int(t)) > 300: return False
    beklenen = hmac.new(secret.encode(), f"{t}.".encode() + govde, hashlib.sha256).hexdigest()
    return hmac.compare_digest(beklenen, imza)
```

Alıcı 2xx dışında yanıt verirse `hata_sayisi` artar; PVQuant koşuyu asla bu yüzden düşürmez. Panelden "Dene"
ile `deneme` olayı gönderilir. URL `https://` olmalıdır (geliştirmede `http://localhost` serbest).
