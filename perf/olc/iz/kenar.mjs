// kenar.mjs — PNG'lerde kenar enerjisi (ortalama |∇L|, Sobel) ve yüksek frekans payı: keskinlik düzeyini kıyaslamak için.
import fs from "node:fs";
import { PNG } from "pngjs";
for (const f of process.argv.slice(2)) {
  const p = PNG.sync.read(fs.readFileSync(f)); const { width: w, height: h, data: d } = p;
  const L = new Float32Array(w * h); for (let i = 0; i < w * h; i++) L[i] = 0.2126 * d[4 * i] + 0.7152 * d[4 * i + 1] + 0.0722 * d[4 * i + 2];
  let top = 0, n = 0, yuksek = 0;
  for (let y = 6; y < h - 6; y++) for (let x = 6; x < w - 6; x++) {
    const a = (yy, xx) => L[yy * w + xx];
    const gx = -a(y - 1, x - 1) - 2 * a(y, x - 1) - a(y + 1, x - 1) + a(y - 1, x + 1) + 2 * a(y, x + 1) + a(y + 1, x + 1);
    const gy = -a(y - 1, x - 1) - 2 * a(y - 1, x) - a(y - 1, x + 1) + a(y + 1, x - 1) + 2 * a(y + 1, x) + a(y + 1, x + 1);
    const lap = Math.abs(4 * a(y, x) - a(y - 1, x) - a(y + 1, x) - a(y, x - 1) - a(y, x + 1));
    top += Math.hypot(gx, gy) / 8; yuksek += lap; n++;
  }
  console.log(f.split("/").pop().padEnd(44), "kenar", (top / n).toFixed(3), "laplace", (yuksek / n).toFixed(3));
}
