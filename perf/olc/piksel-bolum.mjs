// piksel-bolum.mjs — boyu değişen sayfada bölüm bazında görsel kıyas: her <section>/<footer> önce ve sonra ekran görüntüsünden
// kendi DOM konumuyla kırpılır, aynı boydaysa pixelmatch ile kıyaslanır. node olc/piksel-bolum.mjs --motor webkit --gorunum 390x844
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";
import { KOK, HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "webkit"), gAd = arg("gorunum", "390x844"), g = GORUNUMLER[gAd];
const SON = arg("sonra", "after"), SON_HEDEF = arg("hedef", "sonra");   // 19.10: son derleme için --sonra son --hedef final
const kutular = {};
for (const [hedef, klasor] of [["once", "baseline"], [SON_HEDEF, SON]]) {
  const t = await motorAc(motor, hedef); const b = await t.newContext(baglamAyar(motor, g, { reducedMotion: "reduce" })); const s = await b.newPage();
  await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" }); await s.waitForTimeout(1500);
  kutular[klasor] = await s.evaluate(() => [...document.querySelectorAll("main > section, footer")].map((e, i) => { const r = e.getBoundingClientRect(); return { ad: i + ":" + (e.id || e.className.toString().split(" ")[0]), y: r.top + scrollY, h: r.height }; }));
  await t.close();
}
const oku = (k) => PNG.sync.read(fs.readFileSync(path.join(KOK, k, "screens", `${motor}-${gAd}-ana.png`)));
const A = oku("baseline"), B = oku(SON), w = A.width, d = g.dpr;
const kayit = [];
for (let i = 0; i < kutular.baseline.length; i++) {
  const a = kutular.baseline[i], z = kutular[SON][i];
  const ha = Math.round(a.h * d), hz = Math.round(z.h * d);
  if (ha !== hz) { kayit.push({ bolum: a.ad, onceBoy: a.h, sonraBoy: z.h, durum: "boy değişti" }); console.log(`${a.ad.padEnd(22)} boy ${a.h.toFixed(1)} → ${z.h.toFixed(1)} CSS px (değişti)`); continue; }
  const ya = Math.round(a.y * d), yz = Math.round(z.y * d), h = Math.min(ha, A.height - ya, B.height - yz);
  const n = pixelmatch(A.data.subarray(ya * w * 4, (ya + h) * w * 4), B.data.subarray(yz * w * 4, (yz + h) * w * 4), null, w, h, { threshold: 0.1, includeAA: false });
  kayit.push({ bolum: a.ad, onceY: a.y, sonraY: z.y, boy: a.h, farkli: n, oran: n / (w * h) });
  console.log(`${a.ad.padEnd(22)} y ${a.y.toFixed(0)} → ${z.y.toFixed(0)} · boy ${a.h.toFixed(0)} · farklı piksel ${n}${n ? ` (%${(100 * n / (w * h)).toFixed(3)})` : ""}`);
}
const dosya = path.join(KOK, SON, "piksel-bolum.json");
const tum = fs.existsSync(dosya) ? JSON.parse(fs.readFileSync(dosya, "utf8")) : {};
tum[`${motor}-${gAd}`] = kayit; fs.writeFileSync(dosya, JSON.stringify(tum, null, 1));
