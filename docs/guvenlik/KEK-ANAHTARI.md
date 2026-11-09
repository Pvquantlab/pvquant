# Bulut kimlik kasası — ana anahtar (KEK) işletimi (v2.556, 09.11.2026)

**Ne.** Müşterinin inverter bulutu hesabı (FusionSolar Northbound kullanıcı adı + systemCode) veritabanında yalnız şifreli durur: kayıt başına rastgele
veri anahtarı (DEK, AES-256-GCM) gövdeyi şifreler; DEK, sunucu ortamındaki ana anahtarla (KEK) sarılır. KEK veritabanında yoktur; DB yedeği tek başına
çözülemez. Ek doğrulanmış veri «kiracı:santral:sağlayıcı» olduğundan bir kaydın şifreli gövdesi başka kayda taşınamaz. Kod: `src/pvquant/guvenlik/kasa.py`.

**Neden uygulama içi KEK.** İncelenen bulut KMS bölge listelerinde Türkiye yok; HashiCorp Vault Transit'in Türkiye'de barındırma ve fiyatı doğrulanmadı
(Opus araştırması 05 §«Kimlik bilgisi saklama», T2). Bu seçenek ücretsizdir; bedeli işletim disiplinidir (bu belge). KVKK md. 9 görüşü ayrıca alınır.

## Kurulum (bir kez, sunucuda)

```bash
python -m pvquant.guvenlik.kasa
```

Çıktı base64 32 bayttır. `/opt/pvquant/.env` dosyasına:

```
PVQ_KEK=<çıktı>
PVQ_KEK_ID=k1
```

Sonra `docker compose up -d api worker` (ortam değişkeni yeniden okunur). Anahtar depoya, günlüğe, bilet sistemine yazılmaz; yalnız .env ve
şifre kasasında (işletim) saklanır. KEK tanımlı değilse uygulama kimlik saklamayı reddeder («kasa kapalı»); sınama çalışmaya devam eder.

## Yedek

KEK'in bir kopyası DB yedeğinden AYRI bir yerde tutulmalıdır (DB yedeği + KEK birlikte düşerse kayıtlar çözülemez; ikisi aynı yerde durursa ayrımın anlamı kalmaz).

## Dönüş (rotasyon)

1. Yeni anahtar üret; `.env`: `PVQ_KEK=<yeni>`, `PVQ_KEK_ID=k2`, `PVQ_KEK_ESKI=k1=<eski>`.
2. api+worker yeniden başlat (eski anahtar yalnız çözme için okunur).
3. Yeniden sarma: `docker compose run --rm api python -c "from pvquant.services.bulut_kimlik_service import yeniden_sar_tumu as y; print(y())"`
   (gövde yeniden şifrelenmez; yalnız veri anahtarı yeni KEK ile sarılır).
4. Çıktı `zaten_aktif` dışında kayıt bırakmıyorsa `PVQ_KEK_ESKI` satırı silinir, yeniden başlatılır.

## Sızıntı şüphesi

Dönüş adımları uygulanır; müşterilere sağlayıcı tarafında (FusionSolar yönetim ekranı) Northbound şifresini değiştirmeleri söylenir; eski şifreyle kayıtlar
«kimlik_hatasi» düşer ve müşteri Santralim › Veri kaynakları'ndan yeniden kaydeder. Denetim izinde kimlik bilgisi hiç bulunmadığından iz temizliği gerekmez.
