# PVQuant Dış API (v2.264)

Müşteri sistemlerinin (SCADA/EMS, ticaret masası, portföy yazılımı) PVQuant tahminini kendi tarafına
çekmesi için. Etkileşimli şema: `https://<alan>/docs` (OpenAPI, "Dış API" etiketi).

## Kimlik

- Yönetici, panelde **Portföy › Dış erişim** kartından anahtar üretir. Anahtar `pvq_<önek>_<sır>` biçimindedir ve
  **yalnız bir kez** gösterilir; sunucu yalnız sha256 özetini saklar.
- Her istekte başlık: `X-API-Key: pvq_…`
- Kapsamlar: `tahmin:oku` (santral listesi + saatlik tahmin), `kgup:oku` (KGÜP programı). Kapsam dışı → 403.
- Oran sınırı anahtar başına dakikada `rpm` (varsayılan 120) → aşımda 429. Geçersiz/iptal/süresi dolmuş → 401.

## Uçlar

| Uç | Kapsam | Ne verir |
|---|---|---|
| `GET /v1/dis/santraller` | tahmin:oku | Kiracının santralleri (id, ad, kWp, saat dilimi) |
| `GET /v1/dis/santral/{id}/tahmin` | tahmin:oku | Son koşunun saatlik P10/P50/P90 (kW, UTC) + koşu kimliği |
| `GET /v1/dis/santral/{id}/kgup?gun=YYYY-MM-DD&kantil=p50&fmt=json|csv` | kgup:oku | KGÜP saatlik program (TPYS CSV ya da JSON); gün verilmezse İstanbul yarını |
| `GET /v1/dis/santral/{id}/toplayici?gun=YYYY-MM-DD&fmt=csv|xlsx|json&adim=60|15` | kgup:oku | Toplayıcı/DSG program dosyası: P10/P50/P90 MW + EAK; `adim=15` ile çeyrek saatlik (2027 hazırlığı). Kolon adları santralın `toplayici_sablon` eşlemesiyle değiştirilebilir |

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
