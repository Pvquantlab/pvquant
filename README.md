# PVQuant

> **Saha-kalibre PV Performans Analitiği** — SCADA verisinden modeli sahaya özel kalibre eden, canlı meteoroloji ile 15 günlük üretim tahmini yapan kaynağı-açık (source-available) Python kütüphanesi ve REST API.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Elastic 2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Ne yapar?

PVQuant iki tür kullanıcıya hizmet eder:

1. **Operasyonel saha sahibi** (SCADA verisi var) — Geçmiş üretim verisini yükle, model parametrelerini sahaya kalibre et, ardından 15 günlük canlı tahmin al.
2. **Yeni proje geliştirici** (sadece koordinat ve sistem bilgisi) — Datasheet parametreleriyle ön fizibilite tahmini al.

Her iki durumda da arka planda aynı fiziksel model zinciri çalışır:

```
GHI → DHI/DNI (Erbs)
    → POA (Perez transposition)
    → T_cell (Faiman, rüzgar dahil)
    → η_rel (Barhdadi-Bennis bifacial revize)
    → P_DC → P_AC
```

Tüm matematiksel modeller orijinal akademik kaynaklarına karşı doğrulanmıştır — bkz. [`docs/PVQuant_Matematiksel_Modeller.docx`](docs/PVQuant_Matematiksel_Modeller.docx).

**Bugünkü bütün (v2.19x):** bu çekirdeğin çevresinde çok kiracılı bir servis yaşar —
FastAPI uygulaması (`apps/api`, JWT + satır düzeyi güvenlik/RLS), zamanlanmış worker
(`apps/worker`: gece skill, rapor istatistikleri, aylık kalibrasyon), React SPA (`web/`),
LightGBM hibrit artık modeli (`models_v2/`, Mod A/B/C + holdout kapısı) ve 26 tutarlılık
denetimli, bayt-pinli 16 sayfalık rapor motoru (`reporting/html/`). Dağıtım gerçeği için
`KONUSLANDIRMA.md`, rapor sözleşmesi için `reporting/html/docs/` başvuru noktasıdır.

## Hızlı Başlangıç

### Kurulum

```bash
git clone https://github.com/Pvquantlab/pvquant.git
cd pvquant
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Python kütüphanesi olarak kullanım

```python
from pvquant.pipeline.forecast import PlantSpec, forecast_7day
from pvquant.io.meteo import OpenMeteoClient

# 5 MWp bir santralin 15 günlük tahmini
# (fonksiyon adı tarihîdir; ufuk config'ten gelir, bugün 15 gün)
meteo = OpenMeteoClient().get_forecast(latitude=37.87, longitude=32.49, days=15)

plant = PlantSpec(
    p_nom_kwp=5000,
    latitude=37.87,
    longitude=32.49,
    tilt=30,
    azimuth=180,
    module_tech="mono_si",
    bifacial_factor=0.70,
    albedo=0.25,
)
result = forecast_7day(meteo=meteo, plant=plant)

print(result.daily_energy_kwh)  # günlük üretim dizisi
print(result.total_kwh)         # toplam
```

### SCADA verisi ile kalibrasyon

```python
from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.pipeline.forecast import PlantSpec
from pvquant.io.scada import load_fusionsolar_csv
from pvquant.io.meteo import OpenMeteoClient

scada = load_fusionsolar_csv("refplant_2025.csv")
historical_meteo = OpenMeteoClient().get_historical(
    latitude=38.76, longitude=30.54,
    start_date="2025-06-01", end_date="2025-06-30",
)
plant = PlantSpec(p_nom_kwp=4514, latitude=38.76, longitude=30.54,
                  tilt=25, azimuth=180)
calibration = calibrate_from_scada(
    scada=scada,
    historical_meteo=historical_meteo,
    plant=plant,
)

print(calibration.bg)                # BG (geri hesaplanmış)
print(calibration.eta_bos)           # BoS verimi
print(calibration.validation_after)  # kalibrasyon sonrası doğrulama raporu
```

### REST API olarak çalıştırma

```bash
# Üretim yüzeyi (compose'un koştuğu uygulama — /v1/* uçları):
uvicorn apps.api.main:app --reload
# → http://localhost:8000/docs (Swagger UI otomatik)
# Not: `pvquant.api.main:app` eski Faz-1 uygulamasıdır (/forecast, /calibration);
# üretim yığını apps.api.main'i koşar (bkz. docker-compose.yml).
```

## Matematiksel Modeller

| Model | Katman | Kaynak |
|---|---|---|
| Erbs (1982) | GHI → DHI/DNI ayrıştırma | Solar Energy 28(4) |
| Perez (1990) | POA transposition | Solar Energy 44(5) |
| Faiman (2008) | Hücre sıcaklığı (rüzgar dahil) | Prog. Photovolt. 16(4) |
| Barhdadi-Bennis (2012) | Bağıl verim 3-parametreli | Afr. Rev. Phys. 7 |
| PVWatts v5 (Dobos 2014) | Hızlı tahmin | NREL/TP-6A20-62641 |
| SAPM (King 2004) | 5-nokta I-V (ileri) | SAND2004-3535 |
| De Soto (2006) | Tek diyot 5 parametre | Solar Energy 80(1) |

Tam denklemler, parametre tabloları ve uygulama kılavuzu için [matematiksel modeller dokümanına](docs/PVQuant_Matematiksel_Modeller.docx) bakın.

## Proje Yapısı

```
src/pvquant/
├── models/          ← Matematiksel modeller (saf fonksiyonlar)
├── models_v2/       ← Model protokolü + hibrit LightGBM artık modeli
├── pipeline/        ← Modelleri birleştiren akış (forecast, calibration, hybrid_ui)
├── io/              ← Veri girişi (SCADA CSV + ingestion hattı, meteoroloji istemcisi)
├── services/        ← Uygulama katmanı (13 modül: forecast, calib, report, auth, …)
├── validation/      ← MAPE, RMSE, PR metrikleri
├── reporting/       ← Hızlı PDF/Excel/JSON motoru (operasyonel çıktılar)
├── db.py            ← Tenant bağlamı (RLS) + oturum yönetimi
└── api/             ← Eski Faz-1 REST uçları (üretim yüzeyi apps/api'dir)

Kökte: apps/ (api + worker) · alembic/ (şema, RLS) · reporting/ (16 sayfalık
denetimli rapor motoru) · web/ (React SPA) · docker-compose.yml + Caddyfile
```

## Geliştirme

```bash
pip install -e ".[dev]"
pytest                           # Testleri çalıştır
ruff check src/                  # Lint
black src/ tests/                # Format
mypy src/                        # Type check
```

## Frontend

React + Vite + TypeScript frontend için bkz. [`web/README.md`](web/README.md).

## Dokümantasyon

- [Mimari](docs/ARCHITECTURE.md) — Veri akışı, modül yapısı, kalibrasyon stratejisi
- [Matematiksel Modeller](docs/PVQuant_Matematiksel_Modeller.docx) — Tüm formüller, akademik kaynaklarla

## Lisans

Elastic License 2.0 (ELv2) — bkz. [LICENSE](LICENSE). Kaynak açıktır;
kullanım, kopyalama ve türev çalışma serbesttir. Yazılımın üçüncü taraflara
barındırılan/yönetilen servis (SaaS) olarak sunulması lisansça yasaktır.

## Veri kaynakları

- **ECMWF Open Data (IFS / AIFS)** — ECMWF · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [veri](https://www.ecmwf.int/en/forecasts/datasets/open-data) · 0.25°, 15 gün; ssrd/2t/10u/10v/tcc; ENS 50+1 üye; yalnız son ~2–3 gün koşu tutulur
- **ICON-EU (DWD Open Data)** — Deutscher Wetterdienst · [CC BY 4.0](https://www.dwd.de/EN/service/legal_notice/legal_notice.html) · [veri](https://opendata.dwd.de/weather/nwp/) · 0.0625° (~7 km), +120 s, 8 koşu/gün; aswdir_s/aswdifd_s; alan 23,5°B–45°D, Türkiye içinde
- **CAMS Solar Radiation Time-Series** — Copernicus / ECMWF · [CC BY 4.0](https://ads.atmosphere.copernicus.eu/) · [veri](https://ads.atmosphere.copernicus.eu/datasets/cams-solar-radiation-timeseries) · 2004→, 1 dk–1 saat; GHI/BHI/DHI/BNI + açık gök; Meteosat alanı (Türkiye dâhil); ~2 gün gecikme
- **PVGIS v5.3 (SARAH-3, ERA5)** — Avrupa Komisyonu JRC · [CC BY 4.0](https://commission.europa.eu/legal-notice_en) · [veri](https://re.jrc.ec.europa.eu/pvg_tools/en/) · SARAH-3 2005–2023 saatlik; TMY; 30 çağrı/sn/IP
- **EPİAŞ Şeffaflık Platformu** — EPİAŞ · [Kullanım şartları (kayıtlı erişim)](https://seffaflik.epias.com.tr/) · [veri](https://seffaflik.epias.com.tr/electricity-service/technical/tr/index.html) · PTF/SMF/KGÜP/gerçek zamanlı üretim/dengesizlik; TGT kimlik; CAS limitleri

Veriler PVQuant tarafından işlenmiştir; kaynak kurumlar bu ürünü desteklemez.

Meteoroloji girdisi varsayılan olarak açık verilerden gelir (`PVQUANT_METEO_KAYNAK=acik`); Open-Meteo ücretsiz katmanı ticari kullanıma kapalı olduğu için v2.270 ile devre dışıdır. Kalibrasyon geçmişi için CAMS e-postası: `PVQUANT_CAMS_EMAIL`.

## Atıflar

PVQuant'ı akademik bir çalışmada kullanırsanız, lütfen kullanılan matematiksel modellerin orijinal kaynaklarına atıf yapın (tam liste docs içinde).
