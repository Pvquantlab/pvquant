// piksel.mjs — görsel regresyon: <once>/screens/*.png ↔ <sonra>/screens/*.png (pixelmatch 7).
// node olc/piksel.mjs baseline after   → after/piksel.json + after/diff/*.png (yalnız farklı olanlar; .gitignore dışı değil)
// Ölçüt: aynı boyut + farklı piksel sayısı. pixelmatch eşiği 0,1 (algısal YIQ farkı), kenar yumuşatma pikselleri ayrı sayılır
// (includeAA: false → AA farkı «fark» sayılmaz, ayrıca raporlanır). Boyut farklıysa kıyas yapılmaz, «boyut farkı» yazılır.
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";
import { KOK } from "./ortak.mjs";

const [a, b] = [process.argv[2] || "baseline", process.argv[3] || "after"].map((k) => path.join(KOK, k));
const fark = path.join(b, "diff");
fs.mkdirSync(fark, { recursive: true });
const sonuc = [];
for (const ad of fs.readdirSync(path.join(a, "screens")).filter((f) => f.endsWith(".png")).sort()) {
  const yb = path.join(b, "screens", ad);
  if (!fs.existsSync(yb)) { sonuc.push({ ad, durum: "sonra yok" }); continue; }
  const x = PNG.sync.read(fs.readFileSync(path.join(a, "screens", ad))), y = PNG.sync.read(fs.readFileSync(yb));
  if (x.width !== y.width) { sonuc.push({ ad, durum: "genişlik farkı", once: [x.width, x.height], sonra: [y.width, y.height] }); continue; }
  if (x.height !== y.height) {
    // Boy farklı (bilinçli düzen değişikliği, ör. WebKit #isler −77 px): üstten hizalı ve alttan hizalı ortak parçalar ayrı kıyaslanır.
    // Fark yalnız değişen bandın içindeyse, üst parçanın farkı o bandın ALTINDA, alt parçanınki ÜSTÜNDE sıfırlanır.
    const h = Math.min(x.height, y.height), w = x.width, parca = (img, y0) => img.data.subarray(y0 * w * 4, (y0 + h) * w * 4);
    const kiyasla = (a, b) => { const c = new PNG({ width: w, height: h }); const n = pixelmatch(a, b, c.data, w, h, { threshold: 0.1, includeAA: false, diffMask: true });
      let ilk = -1, son = -1; for (let r = 0; r < h; r++) { let v = false; for (let i = r * w * 4 + 3; i < (r + 1) * w * 4; i += 4) if (c.data[i]) { v = true; break; } if (v) { if (ilk < 0) ilk = r; son = r; } }
      return { n, ilk, son, c }; };
    const ust = kiyasla(parca(x, 0), parca(y, 0)), alt = kiyasla(parca(x, x.height - h), parca(y, y.height - h));
    if (ust.n) fs.writeFileSync(path.join(fark, ad.replace(".png", "-ust.png")), PNG.sync.write(ust.c));
    if (alt.n) fs.writeFileSync(path.join(fark, ad.replace(".png", "-alt.png")), PNG.sync.write(alt.c));
    sonuc.push({ ad, durum: "boy farkı", once: [x.width, x.height], sonra: [y.width, y.height],
      ustHizali: { farkli: ust.n, ilkSatir: ust.ilk, sonSatir: ust.son }, altHizali: { farkli: alt.n, ilkSatir: alt.ilk === -1 ? -1 : alt.ilk + (y.height - h), sonSatir: alt.son === -1 ? -1 : alt.son + (y.height - h) } });
    continue;
  }
  const cikis = new PNG({ width: x.width, height: x.height });
  const farkli = pixelmatch(x.data, y.data, cikis.data, x.width, x.height, { threshold: 0.1, includeAA: false, diffMask: true });
  const aaDahil = pixelmatch(x.data, y.data, null, x.width, x.height, { threshold: 0.1, includeAA: true });
  // farklı piksellerin dikey dağılımı (hangi bölge): 10 eşit bant
  const bant = Array(10).fill(0);
  if (farkli) for (let i = 0; i < cikis.data.length; i += 4) if (cikis.data[i + 3]) bant[Math.min(9, Math.floor((i / 4 / x.width) / x.height * 10))]++;
  if (farkli) fs.writeFileSync(path.join(fark, ad), PNG.sync.write(cikis));
  sonuc.push({ ad, durum: farkli ? "fark" : "aynı", boyut: [x.width, x.height], farkli, oran: farkli / (x.width * x.height), aaDahil, bant });
}
fs.writeFileSync(path.join(b, "piksel.json"), JSON.stringify(sonuc, null, 1));
for (const r of sonuc) console.log(r.durum.padEnd(14), r.ad, r.farkli !== undefined ? `${r.farkli} px (%${(100 * r.oran).toFixed(4)}) · AA dahil ${r.aaDahil} · bant ${r.bant.join("/")}`
  : r.ustHizali ? `${JSON.stringify(r.once)}→${JSON.stringify(r.sonra)} · üstten hizalı fark ${r.ustHizali.farkli} px (satır ${r.ustHizali.ilkSatir}–${r.ustHizali.sonSatir}) · alttan hizalı ${r.altHizali.farkli} px (sonra-satır ${r.altHizali.ilkSatir}–${r.altHizali.sonSatir})`
  : JSON.stringify(r.once ?? "") + "→" + JSON.stringify(r.sonra ?? ""));
