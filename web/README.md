# PVQuant Web — React + TypeScript + Vite + ECharts

Streamlit'in yerini alacak SPA'nin iskeleti. `src/pvquant/` ve `apps/worker/`
degismedi; bu katman yalnizca sunum.

## Calistirmak

    cd web
    npm install
    npm run dev        # http://localhost:5173

API kapilari acilana kadar ornek veriyle calisir (`src/api/ornek.ts`).
Gercek API'ye baglamak icin `.env` dosyasi:

    VITE_API_URL=http://localhost:8000

## Yapi

    src/theme/tokens.ts        design_tokens.py'nin TS karsiligi + sayiTr
    src/lib/EChart.tsx         ECharts sarmali (ResizeObserver + dispose)
    src/api/types.ts           API SOZLESMESI — apps/api bunu donmeli
    src/api/client.ts          fetch + ornek-veri yedegi
    src/features/santralim/    Santralim ekrani + fan chart

## Sozlesme notu

`src/api/types.ts` bu isin cekirdegi. Mevcut Streamlit ekranlarindan cikarildi
ve v2.71 A-E'nin durustluk kurallarini tasiyor:

- `hafta_mwh` ILK 7 gunun toplami (v2.71-A)
- `gunler` tam 7 kayit (v2.71-A)
- `p10_kwh`/`p90_kwh` bu sirada (v2.71-B)
- `egim_azimut` gercekte kullanilani soyleyen METIN (v2.71-C)
- `ufuk_saat` secili ufku tasir (v2.71-D)
- `Karne.gun_sayisi` + `ilk_tarih`/`son_tarih` (v2.71-E)

## Henuz yok

Login/oturum, TanStack Query, router, MapLibre (iki santralla erken),
diger bes ekran. Once `apps/api` kapilari.
