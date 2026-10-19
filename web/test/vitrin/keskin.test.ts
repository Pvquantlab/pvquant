// 19.10 perf/cross-browser — Firefox hero keskinleştirmesi WebGL tuvalinde (keskinGL.ts): seçim, cover eşlemesi, tampon boyu,
// SVG süzgeciyle aynı çekirdek, kurulum/söküm/geri dönüş (sahte WebGL ile) ve Hero/CSS bağlantısı.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { KESKIN_CEKIRDEK, KESKIN_PARCA, keskinEslem, keskinGLGerekli, keskinGLKur, kutuOlc } from "../../src/features/vitrin/keskinGL.ts";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");
const rvfc = { requestVideoFrameCallback() {} };

test("yalnız Firefox (Gecko) ve requestVideoFrameCallback varsa", () => {
  const ff = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:158.0) Gecko/20100101 Firefox/158.0";
  assert.equal(keskinGLGerekli(ff, rvfc), true);
  assert.equal(keskinGLGerekli("Mozilla/5.0 (Android 15; Mobile; rv:158.0) Gecko/158.0 Firefox/158.0", rvfc), true);
  assert.equal(keskinGLGerekli(ff, {}), false, "Firefox < 132: CSS süzgeci kalır");
  assert.equal(keskinGLGerekli(ff, undefined), false);
  for (const ua of [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/140.0 Mobile/15E148 Safari/605.1.15",
  ]) assert.equal(keskinGLGerekli(ua, rvfc), false, ua);
});

test("cover eşlemesi: tampon pikseli ortası → doku; komşu 1 CSS pikseli; object-position yüzde ve piksel; kesirli yoğunluk", () => {
  const dok = (e: ReturnType<typeof keskinEslem>, x: number, y: number) => [x * e.m[0] + e.m[2], y * e.m[1] + e.m[3]];
  // tam oturan kutu (1440×810, 16:9 video, tampon 2880×1620)
  const a = keskinEslem(1440, 810, 2560, 1440, "50% 0%", 2);
  assert.deepEqual(dok(a, 0, 0), [0, 0]);
  assert.deepEqual(dok(a, 2880, 1620).map((x) => +x.toFixed(9)), [1, 1]);
  assert.deepEqual(a.a.map((x) => +x.toFixed(12)), [1 / 1440, 1 / 810].map((x) => +x.toFixed(12)));
  // telefon: 390×844 kutu, 1920×1080 video, tampon 1170×2532 — yükseklik dolar, yanlar kırpılır; 50% 0% → yatayda ortalı
  const b = keskinEslem(390, 844, 1920, 1080, "50% 0%", 3);
  const [ux, uy] = dok(b, 585, 1266);
  assert.ok(Math.abs(ux - 0.5) < 1e-9 && Math.abs(uy - 0.5) < 1e-9, `${ux} ${uy}`);
  const [sol] = dok(b, 0, 0), [sag] = dok(b, 1170, 0);
  assert.ok(sol > 0.36 && sag < 0.64 && Math.abs(sol + sag - 1) < 1e-9, "görünen dilim ortada");
  assert.ok(Math.abs(dok(keskinEslem(390, 844, 1920, 1080, "0% 0%", 3), 0, 0)[0]) < 1e-12, "0% → sol kenar");
  assert.ok(Math.abs(dok(keskinEslem(1000, 1000, 1000, 500, "10px 0px", 1), 10, 0)[0]) < 1e-12, "10 px kayma");
  // kesirli kutu (1351×775,6; 1366×768 ekranda ölçülen): tampon satırı aygıt pikseline birebir → 775,6 CSS px = dokunun altı;
  // tamsayı kutuyla (776) eşleme 0,05 % kayar — 1x ekranda ince panel deseni görünür biçimde kayıyordu (ölçüldü)
  const c = keskinEslem(1351, 775.6, 2560, 1440, "50% 0%", 1);
  assert.ok(Math.abs(dok(c, 0, 775.6)[1] - 1) < 1e-9, "alt kenar");
  assert.ok(Math.abs(dok(c, 1351 / 2, 0)[0] - 0.5) < 1e-9, "yatay orta");
});

test("tampon boyu: kesirli CSS kutusu × devicePixelRatio (device-pixel-content-box fiziksel ekranı bildiriyor — kullanılmaz)", () => {
  const kutu = (w: number, h: number) => [{ inlineSize: w, blockSize: h }];
  assert.deepEqual(kutuOlc({ contentBoxSize: kutu(1425.5, 801.5) }, { W: 1, H: 1 }, 2), { W: 1425.5, H: 801.5, gw: 2851, gh: 1603, dpr: 2 });
  assert.deepEqual(kutuOlc({ contentBoxSize: kutu(1351, 775.6) }, { W: 1, H: 1 }, 1), { W: 1351, H: 775.6, gw: 1351, gh: 776, dpr: 1 });
  assert.deepEqual(kutuOlc({ contentBoxSize: kutu(1440, 810) }, { W: 1, H: 1 }, 1.5), { W: 1440, H: 810, gw: 2160, gh: 1215, dpr: 1.5 });
  assert.deepEqual(kutuOlc(undefined, { W: 390, H: 844 }, 3), { W: 390, H: 844, gw: 1170, gh: 2532, dpr: 3 });
});

test("WebGL çekirdeği Hero'daki SVG süzgeciyle aynı; eşleme satırı sabit", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  const m = /<feConvolveMatrix order="3" kernelMatrix="([^"]+)" divisor="1" preserveAlpha="true" edgeMode="duplicate" \/>/.exec(hero);
  assert.ok(m, "feConvolveMatrix bulunamadı");
  const k = m[1].split(/\s+/).map(Number);
  assert.deepEqual(k, [0, -KESKIN_CEKIRDEK.komsu, 0, -KESKIN_CEKIRDEK.komsu, KESKIN_CEKIRDEK.merkez, -KESKIN_CEKIRDEK.komsu, 0, -KESKIN_CEKIRDEK.komsu, 0]);
  assert.match(hero, /<filter id="vt-keskin" colorInterpolationFilters="sRGB">/, "sRGB: gölgelendirici de doğrusallaştırmadan çalışır");
  assert.ok(KESKIN_PARCA.includes("vec2 u=vec2(gl_FragCoord.x,h-gl_FragCoord.y)*m.xy+m.zw;"), "üstten piksel ortası → doku (UNPACK_FLIP_Y yok)");
  assert.ok(KESKIN_PARCA.includes("vec3 o=2.80*texture2D(t,u).rgb-0.45*(texture2D(t,u+vec2(a.x,0.)).rgb+texture2D(t,u-vec2(a.x,0.)).rgb+texture2D(t,u+vec2(0.,a.y)).rgb+texture2D(t,u-vec2(0.,a.y)).rgb);"), KESKIN_PARCA);
  assert.ok(KESKIN_PARCA.includes("gl_FragColor=vec4(clamp(o,0.,1.),1.)"), "kırpılır, alfa 1 (video opak)");
});

// ── sahte WebGL/DOM ile kurulum, çizim, yeniden boyut, söküm ve geri dönüşler
type Sec = { glVar?: boolean; kayip?: boolean; golgeYok?: boolean; hata?: number };
function sahne(sec: Sec = {}) {
  const kayit: string[] = [];
  const sinif = () => { const s = new Set<string>(); return { add: (x: string) => s.add(x), remove: (x: string) => s.delete(x), has: (x: string) => s.has(x) }; };
  let kare: (() => void) | null = null, roGeri: ((g: unknown[]) => void) | null = null, roKutu = "";
  const mqDinle = new Set<() => void>();
  const pencere = { devicePixelRatio: 2, matchMedia: (q: string) => ({ media: q, addEventListener: (_: string, f: () => void) => mqDinle.add(f), removeEventListener: (_: string, f: () => void) => mqDinle.delete(f) }) };
  const v = { videoWidth: 2560, videoHeight: 1440, readyState: 4, getBoundingClientRect: () => ({ width: 1440, height: 810 }), classList: sinif(),
    requestVideoFrameCallback: (f: () => void) => { kare = f; return 7; }, cancelVideoFrameCallback: (n: number) => kayit.push(`iptal ${n}`) };
  const dinle: Record<string, (e: Event) => void> = {};
  const gl = new Proxy({} as Record<string, unknown>, { get: (_, ad: string) => {
    if (ad === "isContextLost") return () => !!sec.kayip;
    if (ad === "getProgramParameter") return () => true;
    if (ad === "getError") return () => sec.hata ?? 0;
    if (ad === "NO_ERROR") return 0;
    if (ad === "getExtension") return () => ({ loseContext: () => kayit.push("bağlam bırakıldı") });
    if (ad === "getAttribLocation") return () => 0;
    if (ad === "createShader" && sec.golgeYok) return () => null;
    if (/^[A-Z_]+$/.test(ad)) return ad;
    return (...a: unknown[]) => { if (/^(uniform|viewport|texImage2D|drawArrays)/.test(ad)) kayit.push(`${ad} ${a.slice(ad.startsWith("uniform") ? 1 : 0).map((x) => (typeof x === "number" ? +x.toPrecision(6) : String(x))).join(",")}`); return {}; };
  } });
  const c = { width: 300, height: 150, classList: sinif(), getContext: () => (sec.glVar === false ? null : gl),
    addEventListener: (t: string, f: (e: Event) => void) => { dinle[t] = f; }, removeEventListener: (t: string) => { delete dinle[t]; } };
  Object.assign(globalThis, { window: pencere, getComputedStyle: () => ({ objectPosition: "50% 0%" }),
    ResizeObserver: class { constructor(f: (g: unknown[]) => void) { roGeri = f; } observe(_: unknown, o?: { box?: string }) { roKutu = o?.box ?? ""; } disconnect() { kayit.push("ro bitti"); } } });
  const yogunluk = (d: number) => { pencere.devicePixelRatio = d; for (const f of [...mqDinle]) f(); };
  return { v, c, kayit, dinle, kare: () => kare?.(), ro: (g: unknown) => roGeri?.([g]), roKutu: () => roKutu, yogunluk, mqSay: () => mqDinle.size };
}
const kur = (s: ReturnType<typeof sahne>) => keskinGLKur(s.v as unknown as HTMLVideoElement, s.c as unknown as HTMLCanvasElement);

test("kurulum ve çizim: ilk hatasız karede tuval görünür, video süzgecini bırakır; uniform'lar eşlemle aynı", () => {
  const s = sahne();
  const sok = kur(s);
  assert.ok(sok);
  assert.equal(s.roKutu(), "", "içerik kutusu (device-pixel-content-box değil)");
  assert.equal(s.c.classList.has("is-hazir"), false, "ilk kare çizilmeden görünmez");
  s.kare();
  assert.equal(s.c.classList.has("is-hazir"), true);
  assert.equal(s.v.classList.has("is-gl"), true, "video süzgeci kalkar");
  assert.deepEqual([s.c.width, s.c.height], [2880, 1620]);
  const e = keskinEslem(1440, 810, 2560, 1440, "50% 0%", 2);
  assert.ok(s.kayit.includes(`uniform4f ${e.m.map((x) => +x.toPrecision(6)).join(",")}`), s.kayit.join(" | "));
  assert.ok(s.kayit.includes(`uniform2f ${e.a.map((x) => +x.toPrecision(6)).join(",")}`));
  assert.ok(s.kayit.includes("uniform1f 1620"));
  assert.ok(s.kayit.some((x) => x.startsWith("texImage2D")) && s.kayit.some((x) => x.startsWith("drawArrays")));
  // kutu değişti (kırılım / pencere): tampon ve eşlem yenilenir
  s.ro({ contentBoxSize: [{ inlineSize: 720, blockSize: 405 }] });
  assert.deepEqual([s.c.width, s.c.height], [1440, 810]);
  assert.ok(s.kayit.includes("uniform1f 810"));
  s.ro({ contentBoxSize: [{ inlineSize: 1440, blockSize: 810 }] });
  // yoğunluk değişimi ResizeObserver'sız (Firefox 158 bildirmiyor): matchMedia(resolution) olayıyla tampon yenilenir
  s.yogunluk(1);
  assert.deepEqual([s.c.width, s.c.height], [1440, 810], "pencere 1x ekrana taşındı");
  s.yogunluk(3);
  assert.deepEqual([s.c.width, s.c.height], [4320, 2430]);
  assert.equal(s.mqSay(), 1, "eski sorgu bırakılır, yenisi dinlenir");
  sok!();
  assert.equal(s.mqSay(), 0, "sökümde dinleyici kalkar");
  assert.equal(s.c.classList.has("is-hazir"), false);
  assert.equal(s.v.classList.has("is-gl"), false, "CSS süzgeci geri gelir");
  assert.ok(s.kayit.includes("iptal 7") && s.kayit.includes("bağlam bırakıldı") && s.kayit.includes("ro bitti"));
});

test("geri dönüşler: WebGL yok, bağlam kayıp, gölgelendirici yok → null; ilk karede GL hatası ve sonradan bağlam kaybı → CSS süzgeci", () => {
  assert.equal(kur(sahne({ glVar: false })), null);
  assert.equal(kur(sahne({ kayip: true })), null);
  const g = sahne({ golgeYok: true }); assert.equal(kur(g), null); assert.ok(g.kayit.includes("bağlam bırakıldı"));
  const h = sahne({ hata: 1282 }); assert.ok(kur(h)); h.kare();
  assert.equal(h.c.classList.has("is-hazir"), false, "hatalı ilk kare gösterilmez");
  assert.equal(h.v.classList.has("is-gl"), false);
  assert.ok(h.kayit.includes("bağlam bırakıldı"));
  const k = sahne(); kur(k); k.kare();
  let onlendi = false; k.dinle.webglcontextlost({ preventDefault: () => { onlendi = true; } } as unknown as Event);
  assert.equal(onlendi, true);
  assert.equal(k.v.classList.has("is-gl"), false);
});

test("Hero: tuval yalnız keskinGL'de ve videonun hemen ardında; erime GL'den bağımsız, tek deneme, istisna yutulur; CSS aynı kutu", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  assert.match(hero, /<\/video>\n\s*\)\}\n\s*\{keskinGL && <canvas ref=\{tuval\} className="vt-hero__keskin" aria-hidden="true" \/>\}\n\s*\{!kabuk && <img className=\{videoGorunur/);
  assert.match(hero, /const \[keskinGL\] = useState\(\(\) => !kabuk && typeof navigator !== "undefined"/);
  assert.match(hero, /requestAnimationFrame\(\(\) => setVideoGorunur\(true\)\);[^\n]*\n\s*if \(!glDenendi && tuval\.current\) \{ glDenendi = true; try \{ gl = keskinGLKur\(v, tuval\.current\); \} catch \{ gl = null; \} \}/);
  assert.match(hero, /v\.removeEventListener\("playing", oynuyor\);\n\s*gl\?\.\(\);/);
  const css = oku("../../src/features/vitrin/vitrin.css");
  assert.match(css, /\.vt-hero--video \.vt-hero__video \{ object-position: 50% 0%; filter: url\(#vt-keskin\); transform: scaleX\(-1\); \}/);
  assert.match(css, /\.vt-hero--video \.vt-hero__keskin \{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; pointer-events: none; transform: scaleX\(-1\); visibility: hidden; \}/);
  assert.match(css, /\.vt-hero--video \.vt-hero__keskin\.is-hazir \{ visibility: visible; \}/);
  assert.match(css, /\.vt-hero--video \.vt-hero__video\.is-gl \{ filter: none; \}/);
});
