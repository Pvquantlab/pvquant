# PVQuant Mimarisi

Bu doküman PVQuant'ın mimari kararlarını ve veri akışını açıklar. Matematiksel model
detayları için bkz. `PVQuant_Matematiksel_Modeller.docx`.

> **Güncellik notu (v2.194):** Bu belge Faz-1 çekirdeğini (fizik zinciri, kalibrasyon
> stratejisi, eski `/forecast` · `/calibration` uçları) anlatır ve o katmanda doğrudur.
> Bugünkü üretim yüzeyi `/v1/*` uçlarıyla `apps/api/main.py`'dedir; servis katmanı
> (`src/pvquant/services/`), worker (`apps/worker/`), hibrit model (`models_v2/`),
> çok kiracılılık/RLS (`alembic/`, `db.py`) ve 16 sayfalık denetimli rapor motoru
> (`reporting/html/`) bu belgede yoktur. Güncel gerçeğin adresleri: dağıtım için
> `KONUSLANDIRMA.md`, rapor sözleşmesi için `reporting/html/docs/`, zorunlu sözleşme
> için `.github/workflows/ci.yml`.

## Temel Tasarım Prensibi

PVQuant, **iki ayrı kullanıcı senaryosu** için **tek bir matematiksel model katmanı**
kullanır:

```
┌─────────────────────┐      ┌──────────────────────┐
│ Santral verisi      │      │ Meteorolojik veri    │
│ olan kullanıcı      │      │ olan kullanıcı       │
│ (SCADA tarihçesi)   │      │ (yeni proje)         │
└──────────┬──────────┘      └──────────┬───────────┘
           │                            │
           ▼                            │
   ┌───────────────┐                    │
   │ Kalibrasyon   │                    │
   │ (BG, η_BoS)   │                    │
   └───────┬───────┘                    │
           │                            │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────┐
           │ Matematiksel Modeller  │
           │ Erbs → Perez →         │
           │ Bifacial → Faiman →    │
           │ Barhdadi-Bennis → AC   │
           └────────────┬───────────┘
                        ▼
           ┌────────────────────────┐
           │ 7 Günlük Tahmin        │
           │ (saatlik + günlük)     │
           └────────────────────────┘
```

## Modül Yapısı

```
src/pvquant/
├── config.py              # Pydantic Settings, env vars
├── models/                # Matematiksel modeller (saf fonksiyonlar)
│   ├── irradiance.py     # Erbs, Perez, solar position
│   ├── temperature.py    # NOCT, Faiman, SAPM
│   ├── power.py          # PVWatts, Skoplaki-Palyvos, Barhdadi-Bennis
│   └── bifacial.py       # Basit + pvlib infinite_sheds
├── io/                    # Veri girişi/çıkışı
│   ├── meteo.py          # Open-Meteo client
│   └── scada.py          # CSV loader (FusionSolar uyumlu)
├── validation/            # Metrikler
│   └── metrics.py        # MAPE, RMSE, NMBE, PR (IEC 61724-1)
├── pipeline/              # İş akışı orkestrasyonu
│   ├── forecast.py       # 7-günlük tahmin pipeline'ı
│   └── calibration.py    # SCADA'dan parametre kalibrasyonu
└── api/                   # FastAPI HTTP katmanı
    ├── main.py           # App factory
    ├── routes/           # Endpoint'ler
    └── schemas/          # Pydantic request/response
```

## Kullanıcı Akışları

### Akış 1: Meteorolojik veri ile tahmin (yeni proje)

```
POST /forecast/
  → Open-Meteo'dan 7 günlük forecast çek (GHI, T_air, WS, vb.)
  → Erbs ile GHI → DHI/DNI ayrıştır
  → Perez ile POA hesapla
  → Bifacial katkı ekle (geometrik faktör)
  → Faiman ile hücre sıcaklığı
  → Barhdadi-Bennis ile DC güç
  → η_BoS · η_INV · clip ile AC güç
  → Saatlik + günlük tahmin döndür
```

**Parametreler:** Tipik literatür değerleri (γ, NOCT, BG, η_BoS varsayılanları).

### Akış 2: SCADA verisi ile kalibre tahmin (mevcut santral)

```
POST /calibration/  (multipart: PlantSpec + SCADA CSV)
  → SCADA CSV'yi yükle, saatlik resample
  → Aynı dönem için Open-Meteo'dan tarihsel veri çek
  → Pipeline'ı baseline parametrelerle çalıştır
  → η_BoS'u toplam üretim oranına fit et
  → BG'yi scipy.optimize ile fit et (bifacial katkı)
  → Kalibre PlantSpec ile 7-günlük tahmin döndür
  → Validation raporu (MAPE, RMSE, NMBE, PR) ekle
```

## Teknoloji Kararları

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Backend dili | Python 3.10+ | pvlib, pandas, scipy ekosistemi |
| Web framework | FastAPI | Async, otomatik OpenAPI, Pydantic native |
| Frontend | React + Vite + TypeScript | Profesyonel, ölçeklenebilir |
| Meteo kaynağı | Open-Meteo | Ücretsiz, anahtarsız, 7-gün forecast + arşiv |
| SCADA formatı | CSV | FusionSolar Excel export uyumlu |
| Paketleme | pyproject.toml (PEP 621) | Modern Python standardı |
| Test | pytest + coverage | Standart |
| Lint/Format | ruff + black | Hızlı, opinionated |
| CI | GitHub Actions | Repo ile entegre |

## Veri Akışı Detayı (Saatlik Adım)

Her saat için pipeline:

1. **Open-Meteo input:** `shortwave_radiation` (GHI), `temperature_2m`, `wind_speed_10m`
2. **Solar position:** `pvlib.solarposition.get_solarposition()` ile zenit/azimut
3. **Decomposition:** Erbs (1982) → DHI, DNI
4. **Transposition:** Perez (1990) → POA (front)
5. **Bifacial:** BG · BF · A faktörü → POA (effective)
6. **Wind log profile:** 10m → modül yüksekliği (z_ref=10, z=h_module)
7. **Cell temp:** Faiman (2008) → T_cell
8. **DC power:** Barhdadi-Bennis (2012) → P_dc
9. **AC power:** P_ac = min(P_dc · η_BoS · η_INV, P_clip)
10. **Energy:** E_h = P_ac · 1h (saatlik kW → kWh)

## Kalibrasyon Stratejisi (Bölüm 3.3.7, Tez)

Tez yaklaşımı: kapasite faktörü (CF) ile bifacial gain'i ters-çöz.

```
1. Kapasite faktörü ölç: CF_actual = E_total / (P_nom · 8760)
2. Modeli BG=0 ile çalıştır, CF_mono al
3. Net bifacial katkı = CF_actual / CF_mono - 1
4. Bu net katkıyı verecek BG'yi scipy.optimize.minimize_scalar ile bul
   (BF, A sabit; bounds: BG ∈ [0.05, 0.60])
```

η_BoS ayrıca toplam üretim ölçeğinden fit edilir (basit oran).

## Yan Etkiler ve Sınırlamalar

- **Open-Meteo gecikmesi:** Forecast endpoint güncel saat için bazen gecikmeli olabilir.
- **Saatlik adım:** Alt-saatlik dalgalanmalar (bulut geçişleri) ortalamada yok olur.
- **Bifacial basit model:** Geometrik faktör tek skaler; ileri kullanım için
  `pvlib.bifacial.infinite_sheds` modülü hazır ama varsayılan değil.
- **Termal model:** Faiman varsayılan; SAPM ve NOCT alternatif olarak mevcut.

## Genişleme Noktaları

- **Yeni meteo kaynağı:** `io/` altına yeni client ekle, aynı `MeteoData` dataclass'ını döndür.
- **Yeni termal model:** `models/temperature.py`'ye fonksiyon ekle, `cell_temperature()` dispatcher'a kaydet.
- **Yeni güç modeli:** `models/power.py`'ye fonksiyon ekle, `calculate_dc_power()` dispatcher'a kaydet.
- **Frontend:** `web/` dizini React + Vite ile ayrı bir paket olarak gelir; üretimde Caddy aynı kökenden servis eder (`/v1/*` → api), geliştirmede CORS üzerinden konuşur.
