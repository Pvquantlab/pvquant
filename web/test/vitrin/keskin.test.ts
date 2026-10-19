// 19.10 perf/cross-browser — Firefox hero keskinleştirmesi WebGL tuvalinde (keskinGL.ts): seçim, cover eşlemesi, SVG süzgeciyle aynı
// çekirdek, kurulum/söküm (sahte WebGL ile) ve Hero/CSS bağlantısı.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { KESKIN_CEKIRDEK, KESKIN_PARCA, keskinEslem, keskinGLGerekli, keskinGLKur } from "../../src/features/vitrin/keskinGL.ts";

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

test("cover eşlemesi: piksel ortası → doku; komşu 1 CSS pikseli; object-position yüzde ve piksel", () => {
  const dok = (e: ReturnType<typeof keskinEslem>, x: number, y: number) => [x * e.m[0] + e.m[2], y * e.m[1] + e.m[3]];
  // tam oturan kutu (1440×810, 16:9 video, dpr 2)
  const a = keskinEslem(1440, 810, 2560, 1440, "50% 0%", 2);
  assert.deepEqual([a.gw, a.gh], [2880, 1620]);
  assert.deepEqual(dok(a, 0, 0), [0, 0]);
  assert.deepEqual(dok(a, 2880, 1620).map((x) => +x.toFixed(9)), [1, 1]);
  assert.deepEqual(a.a.map((x) => +x.toFixed(12)), [1 / 1440, 1 / 810].map((x) => +x.toFixed(12)));
  // telefon: 390×844 kutu, 1920×1080 video, dpr 3 — yükseklik dolar, yanlar kırpılır; 50% 0% → yatayda ortalı
  const b = keskinEslem(390, 844, 1920, 1080, "50% 0%", 3);
  const [ux, uy] = dok(b, b.gw / 2, b.gh / 2);
  assert.ok(Math.abs(ux - 0.5) < 1e-9 && Math.abs(uy - 0.5) < 1e-9, `${ux} ${uy}`);
  const [sol] = dok(b, 0, 0), [sag] = dok(b, b.gw, 0);
  assert.ok(sol > 0.36 && sag < 0.64 && Math.abs(sol + sag - 1) < 1e-9, "görünen dilim ortada");
  // 50% 100% → yükseklik zaten dolu, fark yok; 0% 0% → sol kenar dokunun solu
  assert.ok(Math.abs(dok(keskinEslem(390, 844, 1920, 1080, "0% 0%", 3), 0, 0)[0]) < 1e-12);
  // piksel cinsinden konum
  const c = keskinEslem(1000, 1000, 1000, 500, "10px 0px", 1);
  assert.ok(Math.abs(dok(c, 10, 0)[0]) < 1e-12, "10 px kayma");
});

test("WebGL çekirdeği Hero'daki SVG süzgeciyle aynı", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  const m = /<feConvolveMatrix order="3" kernelMatrix="([^"]+)" divisor="1" preserveAlpha="true" edgeMode="duplicate" \/>/.exec(hero);
  assert.ok(m, "feConvolveMatrix bulunamadı");
  const k = m[1].split(/\s+/).map(Number);
  assert.deepEqual(k, [0, -KESKIN_CEKIRDEK.komsu, 0, -KESKIN_CEKIRDEK.komsu, KESKIN_CEKIRDEK.merkez, -KESKIN_CEKIRDEK.komsu, 0, -KESKIN_CEKIRDEK.komsu, 0]);
  assert.match(hero, /<filter id="vt-keskin" colorInterpolationFilters="sRGB">/, "sRGB: gölgelendirici de doğrusallaştırmadan çalışır");
  assert.ok(KESKIN_PARCA.includes("vec3 o=2.80*texture2D(t,u).rgb-0.45*("), KESKIN_PARCA);
  assert.ok(KESKIN_PARCA.includes("gl_FragColor=vec4(clamp(o,0.,1.),1.)"), "kırpılır, alfa 1 (video opak)");
});

// ── sahte WebGL/DOM ile kurulum ve söküm
function sahne(glVar = true) {
  const kayit: string[] = [];
  const sinif = () => { const s = new Set<string>(); return { add: (x: string) => s.add(x), remove: (x: string) => s.delete(x), has: (x: string) => s.has(x) }; };
  let kare: (() => void) | null = null;
  const v = { videoWidth: 2560, videoHeight: 1440, readyState: 4, clientWidth: 1440, clientHeight: 810, classList: sinif(),
    requestVideoFrameCallback: (f: () => void) => { kare = f; return 7; }, cancelVideoFrameCallback: (n: number) => kayit.push(`iptal ${n}`) };
  const dinle: Record<string, (e: Event) => void> = {};
  const gl = new Proxy({} as Record<string, unknown>, { get: (_, ad: string) => {
    if (ad === "getProgramParameter") return () => true;
    if (ad === "getExtension") return () => ({ loseContext: () => kayit.push("bağlam bırakıldı") });
    if (ad === "getAttribLocation") return () => 0;
    if (/^[A-Z_]+$/.test(ad)) return ad;
    return (...a: unknown[]) => { if (/^(uniform|viewport|texImage2D|drawArrays)/.test(ad)) kayit.push(`${ad} ${a.slice(1).map(String).join(",")}`); return {}; };
  } });
  const c = { width: 300, height: 150, classList: sinif(), getContext: () => (glVar ? gl : null),
    addEventListener: (t: string, f: (e: Event) => void) => { dinle[t] = f; }, removeEventListener: (t: string) => { delete dinle[t]; } };
  Object.assign(globalThis, { window: { devicePixelRatio: 2 }, getComputedStyle: () => ({ objectPosition: "50% 0%" }),
    ResizeObserver: class { observe() {} disconnect() { kayit.push("ro bitti"); } } });
  return { v, c, kayit, dinle, kare: () => kare?.() };
}

test("kurulum: ilk karede tuval görünür, video süzgecini bırakır; söküm ve bağlam kaybı CSS süzgecine döner", () => {
  assert.equal(keskinGLKur(sahne(false).v as unknown as HTMLVideoElement, sahne(false).c as unknown as HTMLCanvasElement), null, "WebGL yoksa null");
  const s = sahne();
  const sok = keskinGLKur(s.v as unknown as HTMLVideoElement, s.c as unknown as HTMLCanvasElement);
  assert.ok(sok);
  assert.equal(s.c.classList.has("is-hazir"), false, "ilk kare çizilmeden görünmez");
  s.kare();
  assert.equal(s.c.classList.has("is-hazir"), true);
  assert.equal(s.v.classList.has("is-gl"), true, "video süzgeci kalkar");
  assert.deepEqual([s.c.width, s.c.height], [2880, 1620]);
  assert.ok(s.kayit.some((x) => x.startsWith("drawArrays")));
  assert.ok(s.kayit.some((x) => x.startsWith("texImage2D")));
  sok!();
  assert.equal(s.c.classList.has("is-hazir"), false);
  assert.equal(s.v.classList.has("is-gl"), false, "CSS süzgeci geri gelir");
  assert.ok(s.kayit.includes("iptal 7") && s.kayit.includes("bağlam bırakıldı") && s.kayit.includes("ro bitti"));
  // bağlam kaybı
  const k = sahne(); keskinGLKur(k.v as unknown as HTMLVideoElement, k.c as unknown as HTMLCanvasElement); k.kare();
  let onlendi = false; k.dinle.webglcontextlost({ preventDefault: () => { onlendi = true; } } as unknown as Event);
  assert.equal(onlendi, true);
  assert.equal(k.v.classList.has("is-gl"), false);
});

test("Hero: tuval yalnız keskinGL'de ve videonun hemen ardında; ilk 'playing'de tek deneme; sökümde bırakılır. CSS aynı kutu/aynalama", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  assert.match(hero, /<\/video>\n\s*\)\}\n\s*\{keskinGL && <canvas ref=\{tuval\} className="vt-hero__keskin" aria-hidden="true" \/>\}\n\s*\{!kabuk && <img className=\{videoGorunur/);
  assert.match(hero, /const \[keskinGL\] = useState\(\(\) => !kabuk && typeof navigator !== "undefined"/);
  assert.match(hero, /if \(!glDenendi && tuval\.current\) \{ glDenendi = true; gl = keskinGLKur\(v, tuval\.current\); \}/);
  assert.match(hero, /v\.removeEventListener\("playing", oynuyor\);\n\s*gl\?\.\(\);/);
  const css = oku("../../src/features/vitrin/vitrin.css");
  assert.match(css, /\.vt-hero--video \.vt-hero__video \{ object-position: 50% 0%; filter: url\(#vt-keskin\); transform: scaleX\(-1\); \}/);
  assert.match(css, /\.vt-hero--video \.vt-hero__keskin \{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; pointer-events: none; transform: scaleX\(-1\); visibility: hidden; \}/);
  assert.match(css, /\.vt-hero--video \.vt-hero__keskin\.is-hazir \{ visibility: visible; \}/);
  assert.match(css, /\.vt-hero--video \.vt-hero__video\.is-gl \{ filter: none; \}/);
});
