# PVQuant

> **Saha-kalibre PV Performans Analitiği** — SCADA verisinden modeli sahaya özel kalibre eden, canlı meteoroloji ile 7 günlük üretim tahmini yapan kaynağı-açık (source-available) Python kütüphanesi ve REST API.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Elastic 2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Ne yapar?

PVQuant iki tür kullanıcıya hizmet eder:

1. **Operasyonel saha sahibi** (SCADA verisi var) — Geçmiş üretim verisini yükle, model parametrelerini sahaya kalibre et, ardından 7 günlük canlı tahmin al.
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

## Hızlı Başlangıç

### Kurulum

```bash
git clone https://github.com/YOUR_USERNAME/pvquant.git
cd pvquant
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Python kütüphanesi olarak kullanım

```python
from pvquant.pipeline.forecast import forecast_7day
from pvquant.io.meteo import OpenMeteoClient

# 5 MWp bir santralin 7 günlük tahmini
meteo = OpenMeteoClient().get_forecast(latitude=37.87, longitude=32.49)

result = forecast_7day(
    meteo=meteo,
    p_nom_kwp=5000,
    tilt=30,
    azimuth=180,
    module_tech="mono_si",
    bifacial_factor=0.70,
    albedo=0.25,
)

print(result.daily_energy_kwh)  # 7 günlük günlük üretim
print(result.total_kwh)         # toplam
```

### SCADA verisi ile kalibrasyon

```python
from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.io.scada import load_fusionsolar_csv

scada = load_fusionsolar_csv("refplant_2025.csv")
calibration = calibrate_from_scada(
    scada=scada,
    p_nom_kwp=4514,
    latitude=38.76,
    longitude=30.54,
    tilt=25,
    azimuth=180,
)

print(calibration.bg)          # BG = 0.347 (geri hesaplanmış)
print(calibration.eta_bos)     # 0.931
print(calibration.mape_pct)    # validasyon hatası
```

### REST API olarak çalıştırma

```bash
uvicorn pvquant.api.main:app --reload
# → http://localhost:8000/docs (Swagger UI otomatik)
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
├── pipeline/        ← Modelleri birleştiren akış (forecast, calibration)
├── io/              ← Veri girişi (SCADA CSV, Open-Meteo)
├── validation/      ← MAPE, RMSE, PR metrikleri
└── api/             ← FastAPI REST endpoint'leri
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

React + Vite + TypeScript frontend için bkz. [`frontend/README.md`](frontend/README.md).

## Dokümantasyon

- [Mimari](docs/ARCHITECTURE.md) — Veri akışı, modül yapısı, kalibrasyon stratejisi
- [Matematiksel Modeller](docs/PVQuant_Matematiksel_Modeller.docx) — Tüm formüller, akademik kaynaklarla

## Lisans

Elastic License 2.0 (ELv2) — bkz. [LICENSE](LICENSE). Kaynak açıktır;
kullanım, kopyalama ve türev çalışma serbesttir. Yazılımın üçüncü taraflara
barındırılan/yönetilen servis (SaaS) olarak sunulması lisansça yasaktır.

## Atıflar

PVQuant'ı akademik bir çalışmada kullanırsanız, lütfen kullanılan matematiksel modellerin orijinal kaynaklarına atıf yapın (tam liste docs içinde).
