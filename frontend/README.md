# PVQuant Frontend

React + Vite + TypeScript frontend.

## Kurulum

```bash
npm create vite@latest . -- --template react-ts
npm install
npm install axios recharts @tanstack/react-query
```

## Çalıştırma

```bash
npm run dev
```

Backend `http://localhost:8000` üzerinde, frontend `http://localhost:5173` üzerinde çalışır.

## Yapı (önerilen)

```
frontend/
├── src/
│   ├── App.tsx
│   ├── api/              # FastAPI client (axios)
│   ├── components/
│   │   ├── PlantForm.tsx       # PlantSpec girişi
│   │   ├── ScadaUpload.tsx     # CSV upload
│   │   ├── ForecastChart.tsx   # Recharts ile 7-gün grafiği
│   │   └── ValidationCard.tsx  # MAPE/RMSE gösterimi
│   └── pages/
│       ├── ForecastOnly.tsx    # Meteo-only akışı
│       └── Calibrated.tsx      # SCADA + kalibrasyon akışı
```

## Backend ile İletişim

```typescript
// src/api/client.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Meteo-only forecast
export const getForecast = (plant: PlantSpec) =>
  api.post('/forecast/', { plant });

// SCADA + kalibrasyon
export const calibrateAndForecast = (plant: PlantSpec, csv: File) => {
  const fd = new FormData();
  fd.append('plant_json', JSON.stringify(plant));
  fd.append('scada_csv', csv);
  return api.post('/calibration/', fd);
};
```

CORS backend tarafında zaten açık (`api/main.py`).
