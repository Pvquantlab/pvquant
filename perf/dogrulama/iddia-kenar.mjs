// Bağımsız denetim: «kenar enerjisi» (komşu aygıt pikseli farkı) — birkaç tanımla yeniden hesap
import fs from "node:fs";
import { PNG } from "pngjs";
for (const f of process.argv.slice(2)) {
  const p = PNG.sync.read(fs.readFileSync(f)); const { width: w, height: h, data: d } = p;
  let sRGB = 0, sY = 0, sRGB2 = 0, n = 0, n2 = 0;
  const Y = (i) => 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  for (let y = 0; y < h - 1; y++) for (let x = 0; x < w - 1; x++) {
    const i = (y * w + x) * 4, r = i + 4, b = i + w * 4;
    sRGB += (Math.abs(d[i] - d[r]) + Math.abs(d[i + 1] - d[r + 1]) + Math.abs(d[i + 2] - d[r + 2])) / 3; n++;
    sRGB2 += (Math.abs(d[i] - d[r]) + Math.abs(d[i + 1] - d[r + 1]) + Math.abs(d[i + 2] - d[r + 2]) + Math.abs(d[i] - d[b]) + Math.abs(d[i + 1] - d[b + 1]) + Math.abs(d[i + 2] - d[b + 2])) / 6;
    sY += (Math.abs(Y(i) - Y(r)) + Math.abs(Y(i) - Y(b))) / 2;
  }
  console.log(f.split("/").pop().padEnd(46), `${w}x${h}`, "yatayRGB", (sRGB / n).toFixed(2), "yatay+dikeyRGB", (sRGB2 / n).toFixed(2), "Y(y+d)", (sY / n).toFixed(2));
}
