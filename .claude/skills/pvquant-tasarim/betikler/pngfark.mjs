/** İki PNG'yi piksel piksel kıyaslar (bağımlılıksız; 8-bit RGB/RGBA, interlace yok).
 *  node pngfark.mjs a.png b.png → BİREBİR ya da fark sayısı/oranı + fark kutusu. Çıkış 0 = birebir.
 *  Kullanım: vitrin bozulmadı kanıtı — değişikliksiz (git stash) ve değişiklikli kareleri kıyasla. */
import fs from "node:fs";
import zlib from "node:zlib";
function png(yol) {
  const b = fs.readFileSync(yol);
  if (b.readUInt32BE(0) !== 0x89504e47) throw new Error("PNG değil: " + yol);
  let p = 8, w = 0, h = 0, bpp = 0, idat = [];
  while (p < b.length) {
    const n = b.readUInt32BE(p), tip = b.toString("ascii", p + 4, p + 8), veri = b.subarray(p + 8, p + 8 + n);
    if (tip === "IHDR") { w = veri.readUInt32BE(0); h = veri.readUInt32BE(4); bpp = { 2: 3, 6: 4, 0: 1, 4: 2 }[veri[9]]; if (veri[12] !== 0) throw new Error("interlace"); }
    else if (tip === "IDAT") idat.push(veri);
    p += 12 + n;
  }
  const ham = zlib.inflateSync(Buffer.concat(idat));
  const satir = w * bpp, out = Buffer.alloc(w * h * 4);
  let onceki = Buffer.alloc(satir);
  for (let y = 0; y < h; y++) {
    const f = ham[y * (satir + 1)], s = Buffer.from(ham.subarray(y * (satir + 1) + 1, (y + 1) * (satir + 1)));
    for (let i = 0; i < satir; i++) {
      const a = i >= bpp ? s[i - bpp] : 0, u = onceki[i], c = i >= bpp ? onceki[i - bpp] : 0;
      let v = s[i];
      if (f === 1) v += a; else if (f === 2) v += u; else if (f === 3) v += (a + u) >> 1;
      else if (f === 4) { const q = a + u - c, pa = Math.abs(q - a), pb = Math.abs(q - u), pc = Math.abs(q - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? u : c; }
      s[i] = v & 255;
    }
    for (let x = 0; x < w; x++) {
      const o = (y * w + x) * 4, i = x * bpp;
      if (bpp >= 3) { out[o] = s[i]; out[o + 1] = s[i + 1]; out[o + 2] = s[i + 2]; out[o + 3] = bpp === 4 ? s[i + 3] : 255; }
      else { out[o] = out[o + 1] = out[o + 2] = s[i]; out[o + 3] = bpp === 2 ? s[i + 1] : 255; }
    }
    onceki = s;
  }
  return { w, h, px: out };
}
const [a, b] = process.argv.slice(2);
const A = png(a), B = png(b);
if (A.w !== B.w || A.h !== B.h) { console.log(`BOYUT FARKLI: ${A.w}×${A.h} ↔ ${B.w}×${B.h}`); process.exit(1); }
let fark = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
for (let y = 0; y < A.h; y++) for (let x = 0; x < A.w; x++) {
  const o = (y * A.w + x) * 4;
  if (A.px[o] !== B.px[o] || A.px[o + 1] !== B.px[o + 1] || A.px[o + 2] !== B.px[o + 2] || A.px[o + 3] !== B.px[o + 3]) {
    fark++; if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y;
  }
}
console.log(fark === 0 ? `BİREBİR ${A.w}×${A.h}` : `fark ${fark} px (%${(100 * fark / (A.w * A.h)).toFixed(3)}) · kutu x ${x0}–${x1}, y ${y0}–${y1} · ${A.w}×${A.h}`);
process.exit(fark === 0 ? 0 : 1);
