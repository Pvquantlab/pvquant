// piksel-bagimsiz.mjs — bağımsız doğrulama: baseline/screens/X.png ↔ after/screens/X.png (izlenen dosyalara YAZMAZ).
// node dogrulama/piksel-bagimsiz.mjs [desen]   → dogrulama/piksel-bagimsiz.json
// Her çift için: ham bayt eşitliği (RGBA arabelleği), pixelmatch (eşik 0,1, includeAA false) ve includeAA true sayımı.
// Boyu farklı çiftlerde (WebKit «/» tam sayfa) yalnız üstteki hero bölgesi (görünüm yüksekliği × DPR satır) kıyaslanır;
// ayrıca üstten hizalı ilk farklı satır (aygıt ve CSS px) bulunur.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const G = { "390x844": { h: 844, dpr: 3 }, "768x1024": { h: 1024, dpr: 2 }, "1440x900": { h: 900, dpr: 2 }, "1920x1080": { h: 1080, dpr: 1 } };
const desen = new RegExp(process.argv[2] || ".");
const IKINCI = process.argv[3] || "after"; // ikinci küme (varsayılan after; gürültü tabanı için analiz/gurultu)
const adlar = fs.readdirSync(path.join(KOK, "baseline/screens")).filter((f) => f.endsWith(".png") && desen.test(f)).sort();
const sonuc = [];
for (const ad of adlar) {
  const x = PNG.sync.read(fs.readFileSync(path.join(KOK, "baseline/screens", ad)));
  const y = PNG.sync.read(fs.readFileSync(path.join(KOK, IKINCI, "screens", ad)));
  const g = G[ad.split("-")[1]];
  const kayit = { ad, once: [x.width, x.height], sonra: [y.width, y.height] };
  if (x.width !== y.width) { kayit.durum = "genişlik farkı"; sonuc.push(kayit); console.log(ad, kayit.durum); continue; }
  const w = x.width;
  if (x.height === y.height) {
    kayit.hamAyni = Buffer.compare(x.data, y.data) === 0;
    kayit.farkli = pixelmatch(x.data, y.data, null, w, x.height, { threshold: 0.1, includeAA: false });
    kayit.aaDahil = pixelmatch(x.data, y.data, null, w, x.height, { threshold: 0.1, includeAA: true });
    kayit.durum = kayit.farkli === 0 ? "aynı" : "fark";
  } else {
    // Boy farkı: hero bölgesi = ilk (görünüm yüksekliği × DPR) satır
    const hh = Math.min(g.h * g.dpr, x.height, y.height), n = w * hh * 4;
    const a = x.data.subarray(0, n), b = y.data.subarray(0, n);
    kayit.durum = "boy farkı";
    kayit.heroSatir = hh;
    kayit.heroHamAyni = Buffer.compare(Buffer.from(a.buffer, a.byteOffset, n), Buffer.from(b.buffer, b.byteOffset, n)) === 0;
    kayit.heroFarkli = pixelmatch(a, b, null, w, hh, { threshold: 0.1, includeAA: false });
    kayit.heroAaDahil = pixelmatch(a, b, null, w, hh, { threshold: 0.1, includeAA: true });
    // üstten hizalı ilk ham farklı satır
    const sat = w * 4; let ilk = -1;
    for (let r = 0; r < Math.min(x.height, y.height); r++) {
      if (Buffer.compare(x.data.subarray(r * sat, (r + 1) * sat), y.data.subarray(r * sat, (r + 1) * sat)) !== 0) { ilk = r; break; }
    }
    kayit.ilkFarkliSatir = ilk; kayit.ilkFarkliCssPx = ilk < 0 ? -1 : +(ilk / g.dpr).toFixed(1);
    kayit.boyFarkiCssPx = +((x.height - y.height) / g.dpr).toFixed(1);
  }
  sonuc.push(kayit);
  console.log(kayit.durum.padEnd(10), ad.padEnd(42), kayit.farkli !== undefined ? `farklı ${kayit.farkli} · AA dahil ${kayit.aaDahil} · ham aynı ${kayit.hamAyni}`
    : `hero ${kayit.heroSatir} satır: farklı ${kayit.heroFarkli} · AA dahil ${kayit.heroAaDahil} · ham aynı ${kayit.heroHamAyni} · ilk farklı satır ${kayit.ilkFarkliSatir} (CSS ${kayit.ilkFarkliCssPx}) · boy farkı ${kayit.boyFarkiCssPx} CSS px`);
}
fs.writeFileSync(path.join(KOK, IKINCI === "after" ? "dogrulama/piksel-bagimsiz.json" : "dogrulama/piksel-gurultu.json"), JSON.stringify(sonuc, null, 1));
