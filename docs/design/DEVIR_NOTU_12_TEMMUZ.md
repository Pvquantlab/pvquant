# PVQuant Devir Notu — 12 Temmuz 2026

Bu not, 11 Temmuz akşamı biten çalışmadan sonra durumu ve yarın ne yapacağımı
özetler. Bir önceki devir notu (11 Temmuz sabahı) artık geçersiz — o notta
"backend'e dokunma" kuralı vardı, aynı gün Fable 5 ile yaptığım mimari
kararlarla değişti.

## Büyük resim: PVQuant mimarisi yeniden yazıldı

11 Temmuz'da Fable 5 ile PVQuant'ın eksik yönlerini araştırdım. Sonuç:
mevcut fizik + kalibrasyon (Faz 1) modeli tek başına yeterli değil.
Endüstri standardı olan hibrit rezidüel öğrenme (fizik + LightGBM) doğru yol.

Referans: `docs/design/PVQuant_Anlasilir_Anlatim.docx` (Temmuz 2026, Fable 5
ile yazılan manifest). Bölüm 9 "Karar tablosu"nda seçenekler karşılaştırılıyor,
Seçenek 5 (Hibrit rezidüel) seçildi.

Yeni mimari 5 katman:
1. Fizik zinciri (mevcut, çalışıyor)
2. Kalibrasyon (mevcut, çalışıyor)
3. Hibrit YZ katmanı (Fable 5 ile yazıldı, henüz uygulanmadı)
4. Olasılık katmanı (P10/P50/P90 — henüz yok)
5. Fizik kilitleri (var, hibrit üzerine bindirilecek)

## Üç açık cephe (öncelik sırasıyla)

### Cephe 1 — Ingestion katmanı (yarın odak)

Kullanıcı herhangi bir formatta SCADA verisi yüklesin, sistem otomatik
temizlesin/doğrulasın. FusionSolar/Huawei/SMA gibi vendor'lardan gelen
cp1254 kodlu, ";" ayraçlı, ondalık virgüllü, 4 satır meta başlıklı
dosyaları da algılasın.

**Durum:** Kod hazır ama repo'da değil.
`~/Desktop/pvquant_fable5_hazirlanan/ingestion/` altında 8 dosya:
- `__init__.py`, `contracts.py`, `detection.py`, `mapping.py`,
  `transform.py`, `validate.py`, `templates.py`, `pipeline.py`
- + `test_ingestion.py` (6 test senaryosu)

**Rehber:** `~/Desktop/pvquant_fable5_hazirlanan/docs/INGESTION_ENTEGRASYON.md`

**Yarın yapılacaklar:**
1. `src/pvquant/io/ingestion/` altına dosyaları koy
2. `tests/test_ingestion.py` çalıştır — 6/6 yeşil olmalı
3. Kendi M10 CSV'mizle CLI'dan dene, kalite karnesini gör
4. Frontend'e (Veri Yükleme sayfası) 4-ekran sihirbaz olarak bağla
   (rehberin 4. bölümü)

**Önemli:** `models_v2`'ye referans veriyor (`HistoricalData`,
`HybridResidualModel`). Bu bağımlılık `models_v2` gelene kadar
mock'lanmalı ya da adaptör yazılmalı.

### Cephe 2 — Hibrit model (Ingestion'dan sonra)

`models_v2/hybrid_residual.py` — fizik + LightGBM rezidüel öğrenme.
MERKAS GES üzerinde sentetik test: MAPE %6.8 → %3.15.

**Durum:** Kod hazır ama repo'da değil.
`~/Desktop/pvquant_fable5_hazirlanan/models_v2/hybrid_merkas_demo.py`
Bağımlılık: `pip install lightgbm joblib`

**Yarın yapılacaklar (Cephe 1 bitince):**
1. `models_v2/` paketini oluştur, `contracts.py` + `hybrid_residual.py` koy
2. `lightgbm` + `joblib` kur
3. MERKAS SCADA verisiyle demo koştur
   (`data/MERKAS_SCADA_FULL.csv` durumu belirsiz — kontrol et)
4. Sonucu doğrula: Fizik MAPE, Hibrit MAPE, iyileşme puanı
5. Faz 2 UI'nin `calibrate_from_scada`'sını bunun üzerine yönlendir

### Cephe 3 — Faz 2 UI: Raporlar (Ingestion + Hibrit bitince)

**Adım 6a bitti ve commit + push edildi** (`faz2-ui` dalı, commit mesajı
"feat(ui): Faz 2 Adim 6a - Raporlar iskelet (KPI seridi + guard'lar)").

`raporlar.py` 208 satır. İçinde: kalibrasyon guard, forecast guard,
KPI şeridi (4 kart), Adım 6b placeholder'ı.

**Kalan:**
- Adım 6b: 3 format kartı (görsel)
- Adım 6c: Excel/JSON gerçek işleyiş
- Adım 6d: PDF yönetici özeti (fpdf2 ile)
- Adım 6e: Rapor geçmişi (dekoratif)

**Kütüphane hazır:** fpdf2 2.8.7 kurulu, `requirements.txt`'te.

## Kural değişikliği

Eski devir notundaki "backend'e dokunma, sadece 4 fonksiyonu çağır"
kuralı **artık geçersiz**. Yeni mimari yeni backend gerektiriyor.

Yeni kural: Faz 2 UI'nin çağırdığı fonksiyonların **isimleri** değişmeyecek
(`load_csv`, `calibrate_from_scada`, `OpenMeteoClient`, `forecast_7day`),
ama **arkalarındaki implementasyon** evrilecek — sırayla ingestion, sonra
hibrit katmanı. Bu sayede UI kırılmayacak.

## Önceki sohbet durumu (11 Temmuz akşamı)

Tamamlananlar:
- Faz 2 UI Adım 5d: Export butonları (CSV/Excel/JSON) + API URL kutusu.
  Excel için timezone-unaware düzeltmesi. Commit + push edildi.
- Faz 2 UI Adım 6a: Raporlar sayfası iskeleti, KPI şeridi, iki guard.
  Commit + push edildi.
- `fpdf2` kütüphanesi kuruldu, `requirements.txt` güncellendi.
- Fable 5'ten gelen ingestion + hibrit çalışmaları incelendi. Sonuç:
  kaliteli iş, ama repo'ya konmadan önce bu devir notu yazıldı.

Karşılaşılan tuzaklar (yarın için hatırlatma):
- `raporlar.py` oluştururken `sayfalar.py`'deki router bloğunu yanlışlıkla
  içine kopyalamıştım — sonsuz recursion oldu. Yeni dosya oluştururken
  kopya-yapıştır kaynağına dikkat.
- Streamlit runOnSave yeni dosyayı algılamayabiliyor, tarayıcıda Cmd+R.
- openpyxl timezone-aware datetime kabul etmiyor, önce `tz_localize(None)`.
- GitHub Desktop diff'te satır sayısı yanıltıcı olabiliyor
  (208 satır → 1,209 gösterdi). Gerçek satır sayısı için `wc -l`.

## Yarın başlarken

Yeni sohbet açtığında bu notu paylaş. Sonra ilk komut olarak:

```bash
cd ~/Desktop/pvquant && git status && git log --oneline -5
```

Bu, hangi dalda olduğumu ve son commit'leri gösterir. Ardından:

```bash
ls ~/Desktop/pvquant_fable5_hazirlanan/
```

Bu, Ingestion + Hibrit dosyalarının hazır beklediğini teyit eder.

**Odak:** Ingestion katmanını repo'ya entegre etme, testleri koşturma,
CLI ile deneme. UI'ye bağlama daha sonra.