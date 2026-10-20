# Bağımlılık envanteri (web/package.json) — 20.10

`npm audit --omit=dev`: 0 zafiyet. `npm outdated` (20.10): react/react-dom 19.2.8 → 19.3.1, vite 8.2.0 → 8.3.4, oxlint 1.76 → 1.89,
typescript 6.0.3 (7.0.2 var), @vitejs/plugin-react 6.0.5 → 6.1.2, @tanstack/react-query, zustand, @types/*. Güncelleme YAPILMADI:
bu turun hedefi ölçülebilir performans; derleme zincirini (vite/react) değiştirmek piksel/kabuk doğrulamasını baştan gerektirir ve
ölçülmüş bir kazancı yok. Rapora «öneri» olarak yazıldı.

**Hiç içe aktarılmayan paketler (src, index.html, scripts, vite.config.ts taraması — 0 geçiş):**

| Paket | Boyut (node_modules) | Karar |
|---|---|---|
| `@fontsource-variable/bricolage-grotesque` | font dosyaları | kaldırıldı |
| `@fontsource/ibm-plex-sans` | font dosyaları | kaldırıldı |
| `@tanstack/react-query` | JS | kaldırıldı |
| `zustand` | JS | kaldırıldı |

Derleme çıktısına etkisi YOK (zaten demete girmiyorlardı; dist bayt bayt aynı kalmalı — «sonra» derlemesinde doğrulanır). Kazanç:
`npm ci` daha az paket (5 paket), CI/Docker derleme süresi ve denetim yüzeyi.
