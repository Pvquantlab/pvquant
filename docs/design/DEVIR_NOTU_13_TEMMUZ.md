# PVQuant Devir Notu — 13 Temmuz 2026

12 Temmuz'da büyük ingestion + UI entegrasyonu tamamlandı. Yarın 
kalibrasyon boru hattı güncellemesi + kalıcılık.

## Dün ne yapıldı (12 Temmuz)

### Sabah — Ingestion katmanı
- 8 modül `src/pvquant/io/ingestion/` altına girdi
- 6 test yeşil
- **Commit:** `df555ff feat(io): ingestion katmani`

### Öğleden sonra — Fable 5 iyileştirmesi
- `_detect_excel_format`: xlsx başlık otomatik tespit
- Self-healing: header_row × delimiter varyantları
- `MappingFailedError`: yapılandırılmış istisna
- Kümülatif enerji sayacı tespiti
- 16 markanın sözlük alias'ları + fuzzy fallback
- 5 yeni test (11 toplam)
- **Commit:** `fix(io): Excel baslik tespiti + kumulatif enerji`

### Öğleden sonra 2 — UI ingestion'a bağlandı
- `frontend/veri_yukleme.py` yeniden yazıldı
- 2 fazlı akış: preview + karne
- Santral bilgisi formu (kapasite/koordinat/tz)
- Şablon otomatik kaydediliyor
- MERKAS Türkçe sözlük eklendi
- **Commit:** `feat(ui): veri_yukleme ingestion katmanina baglandi`

### Akşam — MERKAS canlı test
- `MERKAS_GES_yillik_SCADA.xlsx` (8760 satır) uçtan uca çalıştı
- Header row 1 otomatik tespit, 4 kolon %100 eşleşti
- Kalite karnesi: 5541/8760 geçerli

### Akşam 2 — MappingFailedError UI + bug fix
- Manuel eşleme mini-ekranı (8 dropdown'lu) eklendi
- `_try_mapping_variants` bug'ı düzeltildi: MappingFailedError'da 
  artık initial_df kullanılıyor (son denenen saçma varyant değil)
- `gizli_scada.csv` ile uçtan uca test: manuel eşleme + ingest + 
  karne (28/28 geçerli) çalıştı
- **Commit:** `feat(ui,io): MappingFailedError yakalama + manuel esleme`

## Repo Durumu

- Dal: `faz2-ui`, origin ile senkron
- Son 6 commit:

- **Testler: 11/11 ingestion + 88 backend = 99 yeşil**
- `.gitignore`: `ingestion_templates/` eklendi

## Fable 5 Raporundaki 7 İş — Durum

- ✅ İş 1: UI ingestion'a bağlı
- ✅ İş 2: `to_clean_frame()` kalibrasyona hazır (session_state)
- ⬜ İş 3: `clean_scada_outliers` flag-farkındalıklı — **yarın**
- ⬜ İş 4: Kalıcılık (parquet + storage/) — **yarın veya sonra**
- ✅ İş 5: Geçici dosya try/finally + unlink
- ✅ İş 6: TemplateStore devrede
- ✅ İş 7: Eski except kalıntısı yok
- ✅ **Bonus:** MappingFailedError UI yakalama + manuel eşleme

## Yarın Yapılacaklar

### Öncelik 1 — Kalibrasyon boru hattı (İş 3)

Kalibrasyon sayfası (`frontend/kalibrasyon.py`) hâlâ eski `SCADAData` 
bekliyor olabilir. Ingestion çıktısı `to_clean_frame()` bir DataFrame.

**İlk iş:**
1. `calibrate_from_scada` imzasını doğrula
2. `st.session_state.scada_clean` (DataFrame) → `SCADAData` adaptörü
3. Kalibrasyon sayfası bu adaptörü kullansın

**Session'da hazır olanlar:**
- `st.session_state.scada_clean` — DataFrame (timestamp + power_kw + ...)
- `st.session_state.plant_context` — {capacity_kwp, latitude, longitude, timezone}

### Öncelik 2 — Kalıcılık (İş 4)
Fable 5 rehberinin 5. bölümü:
- `data/raw/{plant_id}/{upload_id}.xlsx`
- `ingestion_templates/{name}.json` (zaten var)
- `data/normalized/{plant_id}/{upload_id}.parquet`

Yeni klasör: `src/pvquant/storage/`

### Öncelik 3 — Raporlar sayfası 6b-6e
Adım 6a bitmişti. Kalanlar: format kartları, Excel/JSON, PDF, geçmiş.

## Bilinen Sorunlar

1. **Streamlit cache** — Frontend dosyaları değişince `Cmd+R` yeterli 
   değil. `pkill -f streamlit` + yeniden başlat gerekli.

2. **`_try_mapping_variants` yavaş** — xlsx için her varyant 
   `pd.read_excel` çağırıyor. İlk yükleme ~10-15 sn donmuş hissi. 
   Şablon kaydolunca ikinci yükleme anında geçiyor.
   
3. **POA vs GHI ayrımı** — Türkçe "Işıma" POA'ya eşleniyor ama gerçekte 
   GHI olabilir. UI'da manuel eşleme dropdown'ı yalnızca 
   `MappingFailedError` fırlarsa açılıyor. Otomatik eşleme başarılı 
   olduysa kullanıcı düzeltemiyor. Yarın düşük öncelik.

4. **"Kalibrasyona geç →"** butonu sayfa değiştiriyor ama veri geçişi 
   test edilmedi — Öncelik 1 zaten bu.

## Yarın Başlarken

Yeni sohbette bu notu yükle, sonra:

```bash
cd ~/Desktop/pvquant && git status && git log --oneline -6
PYTHONPATH=src pytest tests/test_ingestion.py -v --tb=no -q
```

11/11 yeşil doğrulanınca Öncelik 1'e (kalibrasyon boru hattı) başla.