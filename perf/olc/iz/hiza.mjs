// hiza.mjs — iki PNG arasında en iyi tam piksel kayması (±R) ve o kaymada ortalama fark; eşleme mi örnekleme mi ayırmak için.
import fs from "node:fs";
import { PNG } from "pngjs";
const [fa, fb, R = "4"] = process.argv.slice(2);
const A = PNG.sync.read(fs.readFileSync(fa)), B = PNG.sync.read(fs.readFileSync(fb)), r = +R;
const L = (p, x, y) => { const i = (y * p.width + x) * 4; return 0.2126 * p.data[i] + 0.7152 * p.data[i + 1] + 0.0722 * p.data[i + 2]; };
let enIyi = null; const m = 40;
for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
  let t = 0, n = 0;
  for (let y = m; y < A.height - m; y += 2) for (let x = m; x < A.width - m; x += 2) { t += Math.abs(L(A, x, y) - L(B, x + dx, y + dy)); n++; }
  const o = t / n; if (!enIyi || o < enIyi.o) enIyi = { dx, dy, o };
  if (dx === 0 && dy === 0) console.log(`kaymasız ortalama |ΔL| ${o.toFixed(2)}`);
}
console.log(`en iyi kayma dx=${enIyi.dx} dy=${enIyi.dy} → ortalama |ΔL| ${enIyi.o.toFixed(2)}`);
