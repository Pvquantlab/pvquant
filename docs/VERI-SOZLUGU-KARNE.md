# Veri sözlüğü — doğruluk karnesi (v2.568, 10.11.2026)

Tek kaynak: `src/pvquant/services/karne_kurali.py`. Yöntem metni (`web/src/features/vitrin/yontem-metni.ts`) bu sözlüğe eşlenir.

## Hangi tahmin sınava girer

| Kural | Tanım | Dayanak |
|---|---|---|
| Geriye bakışlı dışlama | `forecast_runs.model='backtest'` ya da `meteo_source='open-meteo-arsiv'` koşuları karneye girmez | Faz 0 TK-09: analiz meteosuyla geçmiş tarihli koşu sınav değildir |
| Gün içi revizyon | `meteo_ozet_json.etiket='gun_ici'` (09:30 ve 15:30 UTC) koşuları ana kovalara girmez; `horizon_bucket='gun_ici'` satırında, saat başına en son revizyon | Faz 0 TK-05 |
| Ana kovalarda tek koşu | 0-24 / 24-72 / 72-168 / 168+ kovalarında her (saat, kova) için en erken yayımlanan koşu (en uzun ufuk) | «sonradan düzeltme yapılmaz» |
| Program kovası | `horizon_bucket='program'`: teslim günü D (İstanbul) için D-1 KGÜP kesimi (1.1.2025'ten 15:30, öncesinde 16:00) öncesi son koşunun D saatleri; kesim öncesi koşu yoksa satır yok | DUY m.69(1); `kgup_service.kaynak_kosu_df` ile aynı |
| Gündüz | gerçekleşen > %2 kurulu güç (`GUNDUZ_ORAN`) | tek sabit: worker, accuracy_service, konformal_service, backtest_service |
| Geçerli saat | `scada_hourly.flag='valid'` | değişmedi |

Faz 0 öncesi (v2.567 ve öncesi): koşu süzgeci ve tekilleştirme yoktu; aynı saat birden çok koşuyla sayılıyor, gün içi revizyonlar 0-24 kovasına karışıyordu (saf yeniden üretim: WMAPE %20 → %11). Rapor hata dağılımı en kısa ufku tutuyor, Doğruluk sayfası saat başına ortalama alıyordu. 10.11.2026'da üçü tek kurala bağlandı ve karne arşivden yeniden hesaplandı (`scripts/karne_yeniden_hesapla.py`; eski değerler `skill_daily_eski_<tarih>` yedeğinde).

## Sütunlar (`skill_daily`)

| Sütun | İçerik | Not |
|---|---|---|
| `date` | gerçekleşen saatin UTC günü | |
| `horizon_bucket` | `0-24`, `24-72`, `72-168`, `168+`, `gun_ici`, `program` | metin |
| `mape` | **WMAPE** (%) = Σ\|p50 − gerçek\| / Σ gerçek × 100, gündüz saatleri, gün içinde | ad tarihsel; içerik WMAPE. API alanı `wmape` / `wmape_ort` |
| `naive_wmape`, `skill_vs_naive` | akıllı persistans referansı ve beceri | |
| `cliper_wmape`, `skill_vs_cliper` | iklim + persistans optimal birleşimi referansı | |
| `nmae`, `nrmse`, `nmbe` | kapasiteye normalize yüzde (Solar Forecast Arbiter sözlüğü) | |
| `picp80`, `kapsama_p10/p90`, `pinball_*`, `crps`, `bant_n` | olasılıksal bant ölçümü | |

Pencere değeri (`/v1/plants/{id}/skill`, vitrin karnesi, rapor): günlük WMAPE'lerin ortalaması (oranların ortalaması), yöntem metninde yazılı. Havuzlanmış WMAPE değildir.

## Değişmeyenler

Kalibrasyon eşikleri (1 kW, POA ≥ 5 W/m², kısıntı sezgiseli) ve `ext/tahmin/dogrulama.gunduz_maskesi` (%1, tahmin veya gerçek) farklı amaçlıdır; bu sözlükle birleştirilmedi (Faz 0 TK-12, ayrı paket).
