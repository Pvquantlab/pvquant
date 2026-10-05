/** Determinizm dondurucusu — her görsel test sayfayı AYNI dünyada açar:
 *  saat sabit (15 Haz 2026 12:00 TRT — canlı gök hesabı gün ortası, degrade
 *  kararlı), /v1/dogrulama yanıtı sabit «kapalı» (canlı karne sayıları
 *  baseline'a sızmaz), yazı tipleri yüklenmeden kare alınmaz. */
import type { Page } from "@playwright/test";

export const SABIT_AN = Date.UTC(2026, 5, 15, 9, 0, 0); // 12:00 TRT

export async function dondur(page: Page): Promise<void> {
  await page.clock.install({ time: SABIT_AN });
  // açık karne şeridi: canlı sayı yerine deterministik «kapalı» durumu
  await page.route("**/v1/dogrulama", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ durum: "kapali" }) }));
  // vitrin formu asla gerçek gönderilmez — test dünyasında uç tamamen kapalı
  await page.route("**/v1/vitrin/**", (route) => route.abort());
}

export async function fontlariBekle(page: Page): Promise<void> {
  await page.evaluate(() => (document as Document & { fonts: FontFaceSet }).fonts.ready.then(() => undefined));
}
