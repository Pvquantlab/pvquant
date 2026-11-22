// Beş kartın anlam taşıyan mini-diyagramları (satır içi SVG, «Ufuk» jetonları).
// Renk sözleşmesi: mavi = tahmin, amber = YALNIZ gerçekleşen üretim; geri kalan her şey mürekkep/gri.
// Gren: vitrin vinyetleriyle aynı feTurbulence süzgeci; benek: tahmin bandının nokta dokusu.

export const T = {
  ink: "#0B1B3C", gri: "#56647F", ikincil: "#4A5974", tahmin: "#2D6FB5", gercek: "#C27803",
  bant: "#E8EDF8", bant2: "#DCE3F2", kenar: "#D5DDED", kenarG: "#BDC9E0", beyaz: "#FFFFFF",
};

const MONO = 'font-family="IBM Plex Mono, ui-monospace, monospace"';
const f1 = (n) => (Math.round(n * 10) / 10).toString();
const aralik = (a, b, n) => Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));
const yol = (xs, f) => xs.map((x, i) => `${i ? "L" : "M"}${f1(x)} ${f1(f(x))}`).join(" ");
const bell = (t, m = 0.5, s = 0.17) => Math.exp(-(((t - m) / s) ** 2));

function yazi(x, y, s, { boy = 9, renk = T.gri, hiza = "start", kalin = 400, ik = false } = {}) {
  return `<text${ik ? ' class="ik"' : ""} x="${f1(x)}" y="${f1(y)}" ${MONO} font-size="${boy}" font-weight="${kalin}" fill="${renk}" text-anchor="${hiza}">${s}</text>`;
}

function tanimlar(id) {
  return `<defs>
<filter id="${id}-gr" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="3" result="t"/><feColorMatrix in="t" type="matrix" values="0.333 0.333 0.333 0 0  0.333 0.333 0.333 0 0  0.333 0.333 0.333 0 0  0 0 0 0 1" result="gri"/><feComposite in="SourceGraphic" in2="gri" operator="arithmetic" k1="0" k2="1" k3="0.16" k4="-0.080" result="k"/><feComposite in="k" in2="SourceGraphic" operator="in"/></filter>
<pattern id="${id}-benek" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="${T.tahmin}" fill-opacity=".2"/><circle cx="1" cy="1" r=".8" fill="${T.tahmin}" fill-opacity=".6"/><circle cx="3" cy="3" r=".55" fill="${T.tahmin}" fill-opacity=".38"/></pattern>
<pattern id="${id}-tarama" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" stroke="${T.ink}" stroke-opacity=".5" stroke-width="1.1"/></pattern>
</defs>`;
}

const sar = (id, W, H, govde, etiket) =>
  `<svg class="cz" viewBox="0 0 ${W} ${H}" aria-hidden="true" focusable="false" data-cizim="${etiket}">${tanimlar(id)}${govde}</svg>`;

/** K1 — Teslim programı: yarının saatlik programı (mavi çubuk = tahmin) + bugünün teslim penceresi rayı. */
export function cProgram(id) {
  const W = 320, H = 140, x0 = 20, x1 = 300, eks = 88, adim = (x1 - x0) / 24;
  const sx = (h) => x0 + (x1 - x0) * (h / 24);
  let cubuk = "";
  for (let h = 0; h < 24; h++) {
    const v = Math.max(0, Math.sin((Math.PI * (h + 0.5 - 6)) / 13));
    const y = 58 * v;
    if (y < 1.5) { cubuk += `<rect x="${f1(sx(h) + 1.5)}" y="${eks - 1.5}" width="${f1(adim - 3)}" height="1.5" fill="${T.tahmin}" fill-opacity=".35"/>`; continue; }
    cubuk += `<rect x="${f1(sx(h) + 1.5)}" y="${f1(eks - y)}" width="${f1(adim - 3)}" height="${f1(y)}" rx="1.5" fill="${T.tahmin}" fill-opacity="${f1(0.5 + 0.45 * v)}"/>`;
  }
  const saat = ["00", "06", "12", "18", "24"].map((s, i) => yazi(sx(i * 6), eks + 11, s, { boy: 8, ik: true, hiza: i === 0 ? "start" : i === 4 ? "end" : "middle" })).join("");
  const ray = 122, p0 = sx(14), p1 = sx(15.5);
  return sar(id, W, H, `
${yazi(x0, 14, "yarının programı · saatlik", { boy: 9, renk: T.ink, kalin: 500 })}
<g filter="url(#${id}-gr)">${cubuk}</g>
<path d="M${x0} ${eks}H${x1}" stroke="${T.ink}" stroke-opacity=".28" stroke-width="1"/>
${saat}
${yazi(x0, ray - 6, "bugün", { boy: 8, ik: true })}
<path d="M${x0} ${ray}H${x1}" stroke="${T.kenarG}" stroke-width="1"/>
<rect x="${f1(p0)}" y="${ray - 6}" width="${f1(p1 - p0)}" height="12" rx="2" fill="${T.bant2}" stroke="${T.ink}" stroke-opacity=".35" stroke-width="1"/>
<circle cx="${f1(sx(14.55))}" cy="${ray}" r="3" fill="${T.ink}"/>
${yazi(p1 + 6, ray + 3, "teslim penceresi", { boy: 8.5, renk: T.ikincil })}`, "program");
}

/** K2 — Sapma maliyeti: tahmin (kesikli mavi) ile gerçekleşen (dolu amber) arası taralı; altta TL defteri (rakamsız). */
export function cSapma(id) {
  const W = 320, H = 140, x0 = 20, x1 = 300, taban = 60;
  const xs = aralik(x0, x1, 57);
  const t = (x) => (x - x0) / (x1 - x0);
  const tah = (x) => taban - 40 * bell(t(x));
  const ger = (x) => taban - 40 * bell(t(x)) * (1 - 0.42 * bell(t(x), 0.38, 0.05) - 0.32 * bell(t(x), 0.64, 0.045) + 0.1 * bell(t(x), 0.52, 0.05));
  const alan = `${yol(xs, tah)} ${[...xs].reverse().map((x) => `L${f1(x)} ${f1(ger(x))}`).join(" ")} Z`;
  const sat = (y, ad, gen, stil) => `${yazi(x0, y + 7, ad, { boy: 8.5 })}<rect x="118" y="${y}" width="${gen}" height="8" rx="2" ${stil}/>`;
  return sar(id, W, H, `
<path d="M${x0 + 150} 9h12" stroke="${T.tahmin}" stroke-width="1.6" stroke-dasharray="3 2"/>${yazi(x0 + 166, 12, "tahmin", { boy: 8 })}
<path d="M${x0 + 206} 9h12" stroke="${T.gercek}" stroke-width="1.8"/>${yazi(x0 + 222, 12, "gerçekleşen", { boy: 8 })}
<path d="${alan}" fill="url(#${id}-tarama)"/>
<path d="M${x0} ${taban}H${x1}" stroke="${T.ink}" stroke-opacity=".25"/>
<path d="${yol(xs, ger)}" fill="none" stroke="${T.gercek}" stroke-width="1.8" stroke-linejoin="round"/>
<path d="${yol(xs, tah)}" fill="none" stroke="${T.tahmin}" stroke-width="1.6" stroke-dasharray="4 3"/>
${yazi(x1, 80, "TL · aylık", { boy: 8, hiza: "end", ik: true })}
<g filter="url(#${id}-gr)">
${sat(84, "PVQuant sapması", 64, `fill="${T.ink}" fill-opacity=".85"`)}
${sat(102, "basit yöntem", 150, `fill="${T.ink}" fill-opacity=".3"`)}
</g>
${sat(120, "teminat etkisi", 46, `fill="none" stroke="${T.ink}" stroke-opacity=".55" stroke-dasharray="3 2"`)}
<path d="M182 95v-3M182 93.5H268M268 95v-3" stroke="${T.ink}" stroke-opacity=".6" fill="none"/>
${yazi(274, 97, "fark", { boy: 8.5, renk: T.ink, kalin: 500 })}`, "sapma");
}

/** K3 — Şablonlu dışa verim: tahmin aralığı → üç kanal (CSV/XLSX şablonu, API anahtarı); dilim seçici. */
export function cAktarim(id) {
  const W = 320, H = 140;
  const bx0 = 16, bx1 = 108, by0 = 30, by1 = 112;
  const xs = aralik(bx0 + 8, bx1 - 8, 25);
  const t = (x) => (x - bx0 - 8) / (bx1 - bx0 - 16);
  const med = (x) => by1 - 10 - 52 * bell(t(x));
  const ust = (x) => med(x) - 4 - 9 * bell(t(x));
  const alt = (x) => Math.min(by1 - 10, med(x) + 3 + 7 * bell(t(x)));
  const bant = `${yol(xs, ust)} ${[...xs].reverse().map((x) => `L${f1(x)} ${f1(alt(x))}`).join(" ")} Z`;
  const kanal = [["CSV · şablon", 46], ["XLSX · şablon", 76], ["API anahtarı", 106]];
  const serit = kanal.map(([, cy]) => `<path d="M${bx1} 71C156 71 150 ${cy} 196 ${cy}" fill="none" stroke="${T.ink}" stroke-opacity=".5" stroke-width="1.1"/><path d="M191 ${cy - 3}l5 3-5 3" fill="none" stroke="${T.ink}" stroke-opacity=".6"/>`).join("");
  const cip = kanal.map(([s, cy]) => `<rect x="198" y="${cy - 10}" width="106" height="20" rx="4" fill="${T.beyaz}" stroke="${T.ink}" stroke-opacity=".8"/>${yazi(206, cy + 3.2, s, { boy: 9, renk: T.ink })}`).join("");
  return sar(id, W, H, `
${yazi(bx0, 20, "tahmin aralığı", { boy: 9, renk: T.ink, kalin: 500 })}
<rect x="${bx0}" y="${by0}" width="${bx1 - bx0}" height="${by1 - by0}" rx="6" fill="${T.beyaz}" stroke="${T.kenarG}"/>
<g filter="url(#${id}-gr)"><path d="${bant}" fill="url(#${id}-benek)"/></g>
<path d="${yol(xs, med)}" fill="none" stroke="${T.tahmin}" stroke-width="1.6"/>
<path d="M${bx0 + 8} ${by1 - 10}H${bx1 - 8}" stroke="${T.ink}" stroke-opacity=".25"/>
${serit}${cip}
<rect x="198" y="8" width="106" height="16" rx="8" fill="${T.beyaz}" stroke="${T.kenarG}"/>
<rect x="251" y="8" width="53" height="16" rx="8" fill="${T.ink}"/>
${yazi(224.5, 19, "saatlik", { boy: 8.5, hiza: "middle", renk: T.ikincil })}${yazi(277.5, 19, "15 dk", { boy: 8.5, hiza: "middle", renk: T.beyaz })}
${yazi(198, 132, "toplayıcı / DSG biçiminde", { boy: 8, ik: true })}`, "aktarim");
}

/** K4 — Alarm kütüphanesi: gelen ölçüm (amber = gerçekleşen) kesilir → kural tetiklenir; 8 kural üç grupta; gece karnesi şeridi. */
export function cAlarm(id) {
  const W = 320, H = 140;
  let olcum = "";
  for (let i = 0; i < 14; i++) olcum += `<circle cx="${20 + i * 10}" cy="${f1(32 + Math.sin(i * 1.7) * 2.4)}" r="2.5" fill="${T.gercek}"/>`;
  let bosluk = "";
  for (let i = 0; i < 5; i++) bosluk += `<circle cx="${166 + i * 13}" cy="32" r="2.5" fill="none" stroke="${T.gri}" stroke-opacity=".7" stroke-dasharray="1.6 1.4"/>`;
  const grup = [["veri", 20, 3], ["teslim", 124, 2], ["performans", 192, 3]];
  let kural = "";
  for (const [ad, x, n] of grup) {
    kural += yazi(x, 60, ad, { boy: 8.5 });
    for (let i = 0; i < n; i++) {
      const aktif = ad === "veri" && i === 1;
      kural += `<rect x="${x + i * 31}" y="65" width="26" height="14" rx="3" fill="${aktif ? T.ink : T.beyaz}" stroke="${T.ink}" stroke-opacity="${aktif ? 1 : 0.5}"/>`;
    }
  }
  let karne = "";
  for (let i = 0; i < 14; i++) karne += `<rect x="${20 + i * 20}" y="104" width="14" height="14" rx="2.5" fill="${i === 13 ? T.beyaz : T.bant2}" stroke="${i === 13 ? T.ink : T.kenarG}" stroke-width="${i === 13 ? 1.4 : 1}"/>`;
  return sar(id, W, H, `
${yazi(20, 14, "gelen ölçüm", { boy: 8.5 })}
${olcum}${bosluk}
<path d="M222 32H234" stroke="${T.ink}" stroke-opacity=".5"/>
<rect x="234" y="23" width="70" height="18" rx="9" fill="${T.ink}"/>${yazi(269, 35, "veri gecikti", { boy: 8.5, hiza: "middle", renk: T.beyaz })}
${yazi(300, 60, "8 kural", { boy: 8.5, hiza: "end", renk: T.ink, kalin: 500 })}
${kural}
<path d="M64 65V50H269V41" fill="none" stroke="${T.ink}" stroke-opacity=".35" stroke-dasharray="2 2"/>
${yazi(20, 99, "gece karnesi", { boy: 8.5 })}
<g filter="url(#${id}-gr)">${karne}</g>
${yazi(294, 132, "bu sabah", { boy: 8, hiza: "end", renk: T.ink, ik: true })}`, "alarm");
}

/** K5 — Gün içi aralık: benekli iyimser–kötümser bant, revizyon izi (soluk eski medyanlar), şimdi çizgisi, sabah koşusu. */
export function cAralik(id) {
  const W = 320, H = 140, x0 = 20, x1 = 300, eks = 108;
  const xs = aralik(x0, x1, 57);
  const t = (x) => (x - x0) / (x1 - x0);
  const med = (k) => (x) => eks - 66 * k * bell(t(x));
  const ust = (x) => med(1)(x) - 3 - 15 * bell(t(x));
  const alt = (x) => Math.min(eks, med(1)(x) + 3 + 12 * bell(t(x)));
  const bant = `${yol(xs, ust)} ${[...xs].reverse().map((x) => `L${f1(x)} ${f1(alt(x))}`).join(" ")} Z`;
  const sx = (h) => x0 + (x1 - x0) * (h / 24);
  const simdi = sx(10.5);
  return sar(id, W, H, `
<g filter="url(#${id}-gr)"><path d="${bant}" fill="url(#${id}-benek)"/></g>
<path d="${yol(xs, med(0.84))}" fill="none" stroke="${T.tahmin}" stroke-opacity=".38" stroke-width="1.1" stroke-dasharray="2 2.5"/>
<path d="${yol(xs, med(0.92))}" fill="none" stroke="${T.tahmin}" stroke-opacity=".55" stroke-width="1.1" stroke-dasharray="2 2.5"/>
<path d="${yol(xs, med(1))}" fill="none" stroke="${T.tahmin}" stroke-width="1.8"/>
<path d="M${x0} ${eks}H${x1}" stroke="${T.ink}" stroke-opacity=".28"/>
<path d="M${f1(simdi)} 20V${eks}" stroke="${T.ink}" stroke-opacity=".55" stroke-width="1"/>
${yazi(simdi, 15, "şimdi", { boy: 8.5, hiza: "middle", renk: T.ink })}
<path d="M236 70l14 -22" stroke="${T.ink}" stroke-opacity=".4"/>
${yazi(252, 44, "revizyon izi", { boy: 8.5, renk: T.ikincil })}
${yazi(300, 15, "iyimser–kötümser", { boy: 8, hiza: "end", ik: true })}
<circle cx="${f1(sx(6))}" cy="${eks}" r="3" fill="${T.beyaz}" stroke="${T.ink}" stroke-width="1.4"/>
${yazi(sx(6) - 4, eks + 22, "06:00 sabah koşusu → webhook", { boy: 8.5, renk: T.ikincil, ik: true })}
${["00", "12", "24"].map((s, i) => yazi(sx(i * 12), eks + 10, s, { boy: 8, ik: true, hiza: i === 0 ? "start" : i === 2 ? "end" : "middle" })).join("")}`, "aralik");
}

/** K2 büyük (Tasarım D ana kartı): eğri çifti + ay boyunca gün gün TL çubuk çiftleri (rakamsız) + teminat satırı. */
export function cSapmaBuyuk(id) {
  const W = 480, H = 300, x0 = 20, x1 = 460, taban = 100;
  const xs = aralik(x0, x1, 81);
  const t = (x) => (x - x0) / (x1 - x0);
  const tah = (x) => taban - 66 * bell(t(x));
  const ger = (x) => taban - 66 * bell(t(x)) * (1 - 0.42 * bell(t(x), 0.38, 0.05) - 0.32 * bell(t(x), 0.64, 0.045) + 0.1 * bell(t(x), 0.52, 0.05));
  const alan = `${yol(xs, tah)} ${[...xs].reverse().map((x) => `L${f1(x)} ${f1(ger(x))}`).join(" ")} Z`;
  const ct = 250, adim = (x1 - x0) / 30;
  let cift = "";
  for (let i = 0; i < 30; i++) {
    const b = 34 + 40 * Math.abs(Math.sin(i * 1.3)) + 8 * (i % 3);
    const p = b * (0.32 + 0.26 * Math.abs(Math.sin(i * 0.7)));
    const x = x0 + i * adim + 1.5;
    cift += `<rect x="${f1(x)}" y="${f1(ct - b)}" width="5.2" height="${f1(b)}" rx="1.2" fill="${T.ink}" fill-opacity=".22"/>`;
    cift += `<rect x="${f1(x + 6.2)}" y="${f1(ct - p)}" width="5.2" height="${f1(p)}" rx="1.2" fill="${T.ink}" fill-opacity=".85"/>`;
  }
  return sar(id, W, H, `
${yazi(x0, 14, "bugün · saatlik", { boy: 9, renk: T.ink, kalin: 500 })}
<path d="M${x1 - 150} 11h12" stroke="${T.tahmin}" stroke-width="1.6" stroke-dasharray="3 2"/>${yazi(x1 - 134, 14, "tahmin", { boy: 8.5 })}
<path d="M${x1 - 86} 11h12" stroke="${T.gercek}" stroke-width="1.8"/>${yazi(x1 - 70, 14, "gerçekleşen", { boy: 8.5 })}
<path d="${alan}" fill="url(#${id}-tarama)"/>
<path d="M${x0} ${taban}H${x1}" stroke="${T.ink}" stroke-opacity=".25"/>
<path d="${yol(xs, ger)}" fill="none" stroke="${T.gercek}" stroke-width="1.8" stroke-linejoin="round"/>
<path d="${yol(xs, tah)}" fill="none" stroke="${T.tahmin}" stroke-width="1.6" stroke-dasharray="4 3"/>
${yazi(x1, 116, "aradaki fark → TL", { boy: 8.5, hiza: "end", renk: T.ikincil })}
${yazi(x0, 146, "bu ay · gün gün · TL", { boy: 9, renk: T.ink, kalin: 500 })}
<rect x="${x1 - 196}" y="138" width="9" height="9" rx="2" fill="${T.ink}" fill-opacity=".85"/>${yazi(x1 - 183, 146, "PVQuant sapması", { boy: 8.5 })}
<rect x="${x1 - 86}" y="138" width="9" height="9" rx="2" fill="${T.ink}" fill-opacity=".22"/>${yazi(x1 - 73, 146, "basit yöntem", { boy: 8.5 })}
<g filter="url(#${id}-gr)">${cift}</g>
<path d="M${x0} ${ct}H${x1}" stroke="${T.ink}" stroke-opacity=".28"/>
${yazi(x0 + 4, ct + 11, "1", { boy: 8 })}${yazi(x0 + adim * 14.5, ct + 11, "15", { boy: 8, hiza: "middle" })}${yazi(x1 - 4, ct + 11, "30", { boy: 8, hiza: "end" })}
${yazi(x0, 288, "teminat etkisi", { boy: 8.5 })}
<rect x="118" y="280" width="90" height="9" rx="2" fill="none" stroke="${T.ink}" stroke-opacity=".55" stroke-dasharray="3 2"/>`, "sapma-buyuk");
}
