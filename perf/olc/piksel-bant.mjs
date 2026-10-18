// piksel-bant.mjs — boyu değişmiş görüntüde farkın hangi satır aralıklarında olduğunu çıkarır (üstten ve alttan hizalı).
// node olc/piksel-bant.mjs baseline/screens/X.png after/screens/X.png [--dpr 2]
import fs from "node:fs";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";
const [fa, fb] = process.argv.slice(2, 4); const dpr = Number(process.argv[process.argv.indexOf("--dpr") + 1] || 1);
const x = PNG.sync.read(fs.readFileSync(fa)), y = PNG.sync.read(fs.readFileSync(fb)); const w = x.width, h = Math.min(x.height, y.height);
const bantlar = (ya, yb, kaydir) => { const c = new PNG({ width: w, height: h });
  pixelmatch(x.data.subarray(ya * w * 4, (ya + h) * w * 4), y.data.subarray(yb * w * 4, (yb + h) * w * 4), c.data, w, h, { threshold: 0.1, includeAA: false, diffMask: true });
  const satir = []; for (let r = 0; r < h; r++) { let n = 0; for (let i = r * w * 4 + 3; i < (r + 1) * w * 4; i += 4) if (c.data[i]) n++; satir.push(n); }
  const ar = []; let bas = -1, top = 0, bos = 0;
  for (let r = 0; r <= h; r++) { const n = r < h ? satir[r] : 0; if (n) { if (bas < 0) bas = r; top += n; bos = 0; } else if (bas >= 0 && ++bos > 30) { ar.push([bas, r - bos, top]); bas = -1; top = 0; bos = 0; } }
  return ar.map(([a, z, t]) => `CSS y ${Math.round((a + kaydir) / dpr)}–${Math.round((z + kaydir) / dpr)} (${t} px)`); };
console.log("boy", x.height, "→", y.height, "(CSS", Math.round(x.height / dpr), "→", Math.round(y.height / dpr) + ")");
console.log("üstten hizalı fark bantları (sonra koordinatı):", bantlar(0, 0, 0).join(" · ") || "yok");
console.log("alttan hizalı fark bantları (sonra koordinatı):", bantlar(x.height - h, y.height - h, y.height - h).join(" · ") || "yok");
