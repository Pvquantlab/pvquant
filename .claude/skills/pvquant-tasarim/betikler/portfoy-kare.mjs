/** Portföy durum kareleri (yeni derleme, sahte API): soğuk açılışta yer tutucular (~330 ms), yerleşmiş (tahmin «sunucu hatası»),
 *  bellek dolmuş dönüşte «güncelleniyor» çipi; koyu+açık 1440, koyu 375. */
import { createRequire } from "node:module";
const pw = createRequire(process.env.PW_DIR + "/")("playwright");
const base = process.argv[2]; const dizin = process.argv[3];
const JETON = "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y";
const b = await pw.chromium.launch({ headless: true });
for (const [tema, gen] of [["koyu", 1440], ["acik", 1440], ["koyu", 375]]) {
  const ctx = await b.newContext({ viewport: { width: gen, height: gen < 768 ? 812 : 900 }, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  await ctx.addInitScript(() => { window.__kayma = 0; const G = Date; class S extends G { constructor(...a) { a.length === 0 ? super(G.now() + window.__kayma) : super(...a); } static now() { return G.now() + window.__kayma; } } window.Date = S; });
  await ctx.addInitScript(([j, t]) => { localStorage.setItem("pvq_token", j); localStorage.setItem("pvq_tema", t); localStorage.setItem("pvq_plant", "a1"); }, [JETON, tema]);
  const p = await ctx.newPage(); await p.goto(base + "/", { waitUntil: "load" }); await p.waitForSelector(".nav-btn"); await p.waitForTimeout(1500);
  const tik = (h) => p.evaluate((h) => [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === h).click(), h);
  await tik("Portföy"); await p.waitForTimeout(330); await p.screenshot({ path: `${dizin}/portfoy-${tema}-${gen}-soguk-330ms.png`, fullPage: false });
  await p.waitForTimeout(1400); await p.screenshot({ path: `${dizin}/portfoy-${tema}-${gen}-yerlesmis.png`, fullPage: gen === 1440 && tema === "koyu" });
  await tik("Tahminler"); await p.waitForTimeout(400); await p.evaluate(() => { window.__kayma += 61_000; }); await tik("Portföy"); await p.waitForTimeout(120);
  await p.screenshot({ path: `${dizin}/portfoy-${tema}-${gen}-bayat-guncelleniyor.png`, fullPage: false });
  const cip = await p.evaluate(() => document.querySelector(".icerik .cip")?.textContent);
  console.log(tema, gen, "bayat çip:", cip);
  await ctx.close();
}
await b.close();
