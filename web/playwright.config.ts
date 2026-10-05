/** Görsel regresyon yapılandırması (tasarım zekâsı Mühür D, v2.398).
 *  Kapsam: YALNIZ tests/visual — birim testleri node:test'te kalır (npm test).
 *  Koşum: npm run gorsel (baseline güncelleme: npm run gorsel -- --update-snapshots
 *  + diff'i GÖZLE onayla + commit; eşik gevşetme yasak — kaynağı sabitle).
 *  Baseline'lar işletim sistemine göre adlanır (-darwin yerel iç döngü);
 *  CI Linux baseline üretimi AÇIK İŞ (defter: 2026-10-05-tasarim-zekasi). */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual",
  fullyParallel: true,
  retries: 0,                      // görsel testte retry maskeleme yapar
  reporter: [["list"]],
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100,          // gevşetmek yasak: fark büyüyorsa kaynağı sabitle
      animations: "disabled",
      caret: "hide",
    },
  },
  use: {
    baseURL: "http://localhost:5173",
    deviceScaleFactor: 1,          // küçük, kararlı PNG; dpr farkı baseline'ı bozar
  },
  webServer: {
    command: "npm run dev -- --port 5173",
    url: "http://localhost:5173",
    reuseExistingServer: true,     // pvquant-web-dev zaten ayaktaysa onu kullanır
    timeout: 60000,
  },
  projects: [
    { name: "masaustu", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 } },
    { name: "mobil", use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 812 }, deviceScaleFactor: 1, isMobile: false } },
  ],
});
