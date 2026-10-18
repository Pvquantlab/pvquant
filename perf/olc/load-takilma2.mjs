// load-takilma2.mjs — takılmayı yakalayınca teşhis: tembel görsellerin durumu; aşağı kaydırınca load geliyor mu?
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once"), motor = arg("motor", "firefox"), en = Number(arg("tekrar", "40"));
const yama = arg("yama", "yok");
// Teşhis yamaları (çalışma anında; derleme değişmez): poster = <video> poster özniteliği yazılmaz · kaynak = <video> içine <source> eklenmez
const YAMA = {
  poster: `(() => { const s = Element.prototype.setAttribute; Element.prototype.setAttribute = function (a, v) { if (this.tagName === "VIDEO" && a === "poster") return; return s.call(this, a, v); }; })();`,
  kaynak: `(() => { const a = Node.prototype.appendChild, i = Node.prototype.insertBefore; const engel = (p, c) => p && p.tagName === "VIDEO" && c && c.tagName === "SOURCE";
    Node.prototype.appendChild = function (c) { return engel(this, c) ? c : a.call(this, c); }; Node.prototype.insertBefore = function (c, r) { return engel(this, c) ? c : i.call(this, c, r); }; })();`,
};
const t = await motorAc(motor, hedef);
let yakalandi = 0, gezinme = 0;
for (let k = 1; k <= en && yakalandi < Number(arg("dur", "2")); k++) {
  const b = await t.newContext(baglamAyar(motor, GORUNUMLER["1440x900"])); if (YAMA[yama]) await b.addInitScript(YAMA[yama]); const s = await b.newPage();
  await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load", timeout: 45000 }).catch(() => {}); gezinme++;
  gezinme++;
  const ok = await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load", timeout: 15000 }).then(() => true).catch(() => false);
  if (!ok) {
    yakalandi++;
    const d = await s.evaluate(() => ({ hazir: document.readyState, loadStart: performance.getEntriesByType("navigation")[0]?.loadEventStart,
      levha: [...document.querySelectorAll("img[loading]")].map((i) => ({ ad: (i.currentSrc || i.getAttribute("src") || "").split("/").pop().slice(0, 18), lazy: i.loading, tamam: i.complete, ust: Math.round(i.getBoundingClientRect().top) })) }));
    console.log(`#${k} TAKILDI`, JSON.stringify(d).slice(0, 200));
    const e = await s.evaluate(async () => ({
      font: document.fonts.status, fontYukleniyor: [...document.fonts].filter((f) => f.status === "loading").map((f) => f.family + " " + f.weight),
      onyukleme: [...document.querySelectorAll("link[rel=preload]")].map((l) => l.as + ":" + l.href.split("/").pop().slice(0, 30)),
      kaynakBitmemis: performance.getEntriesByType("resource").filter((r) => !(r.responseEnd > 0)).map((r) => r.name.split("/").pop()),
      kaynakSayisi: performance.getEntriesByType("resource").length,
      poster: (() => { const p = document.querySelector("img.vt-hero__poster"); return p ? { tamam: p.complete, w: p.naturalWidth } : null; })(),
      video: (() => { const v = document.querySelector("video"); return v ? { ag: v.networkState, hazir: v.readyState, src: v.currentSrc.split("/").pop(), preload: v.preload } : null; })(),
      iframe: document.querySelectorAll("iframe").length, betik: [...document.scripts].map((x) => (x.src || "satır-içi").split("/").pop()).join(","),
    }));
    console.log("   teşhis:", JSON.stringify(e));
    for (const y of [1500, 3000, 4500, 6000]) {
      await s.evaluate((y) => scrollTo(0, y), y); await s.waitForTimeout(1500);
      const h = await s.evaluate(() => [document.readyState, [...document.querySelectorAll("img[loading]")].filter((i) => !i.complete).length]);
      console.log(`   kaydır ${y}: belge ${h[0]}, tamamlanmamış tembel görsel ${h[1]}`);
      if (h[0] === "complete") break;
    }
  }
  await b.close();
}
console.log(`yama ${yama} · yakalanan ${yakalandi} · gezinme ${gezinme}`);
await t.close();
