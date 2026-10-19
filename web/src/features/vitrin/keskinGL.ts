/** 19.10 perf/cross-browser — Firefox: hero videosundaki keskinleştirmenin tek geçişli WebGL eşdeğeri.
 *
 *  Hero.tsx'teki SVG süzgeci (#vt-keskin: feConvolveMatrix, o = 2,8·c − 0,45·(sol+sağ+üst+alt), sRGB, alfa korunur) Firefox'ta
 *  WebRender'da yok (gfx.webrender.svg-filter-effects.feconvolvematrix=false): her video karesi işlemcide süzülüyor, kaydırırken tarayıcı
 *  1,6–2,7 çekirdek harcıyor, video karesi geri kalıyordu. Aynı çekirdek burada bir parça gölgelendiricisinde, ekran kartında çalışır:
 *  tuval videonun hemen üstünde, aynı kutuda ve aynı aynalamayla durur; her sunulan video karesinde (requestVideoFrameCallback) kare
 *  dokuya yüklenir ve çizilir. İlk kare hatasız çizilene dek tuval gizli, video CSS süzgecini korur; çizilince videonun süzgeci kalkar (.is-gl).
 *
 *  Ölçek: Gecko feConvolveMatrix'i aygıt çözünürlüğünde ama komşuları 1 CSS pikseli uzaktan alarak uyguluyor (ölçüldü: perf/analiz/webgl);
 *  burada da öyle — Firefox'taki görünüm değişmez. Tuval tamponu = video kutusu (CSS, ResizeObserver) × devicePixelRatio; yoğunluk
 *  değişimi (pencere başka ekrana taşınınca) matchMedia(resolution) ile izlenir. device-pixel-content-box KULLANILMAZ: Firefox 158 orada
 *  sayfanın çizildiği yoğunluğu değil fiziksel ekranınkini bildiriyor (yoğunluk geçersiz kılınınca 1x'te 2x tampon → tuval küçültülüp
 *  yumuşuyordu) ve yoğunluk değişince gözlemciyi tetiklemiyor (ölçüldü: perf/olc/iz/ro-sina.mjs, perf/analiz/webgl-son). Chromium ve WebKit'te kullanılmaz:
 *  onlar süzgeci zaten ekran kartında uyguluyor.
 *  Geri dönüş (CSS süzgeci olduğu gibi kalır): WebGL yok, yalnız yazılımla çalışıyor (failIfMajorPerformanceCaveat), bağlam kayıp,
 *  gölgelendirici/program kurulamadı, ilk karede GL hatası ya da istisna, sonradan bağlam kaybı, requestVideoFrameCallback yok (Firefox < 132),
 *  birleştirici yazılımla çalışıyor (aşağıda: ilk saniyenin kare aralığı sınaması). */

/** Yazılımla birleştirme sınaması: Firefox'ta birleştirici yazılımla çalışırken (software WebRender — engellenmiş sürücü, sanal makine,
 *  uzak masaüstü, başsız) WebGL bağlamı «performans engeli»ni geçebiliyor ama tuval her karede işlemciye geri okunuyor: ölçüldü (Playwright
 *  Firefox 157 başsız, 1440×900) boşta kare aralığı ortancası CSS süzgeciyle 16,7 ms, tuvalle 99,8 ms. Tuval ilk karesinden sonra ~1 sn
 *  (en çok 30 kare) kare aralığına bakar; ortanca 25 ms'yi aşarsa söker (CSS süzgeci geri gelir) ve kararı 7 gün hatırlar (K1 yavaş hat
 *  kaydıyla aynı kalıp). Donanımla birleştirmede ortanca ~16,7 ms (stok Firefox 158). Gizli sekmede karar verilmez. */
const YAZILIM_KAYIT = "pvq_keskin_yazilim";
const YAZILIM_OMUR_MS = 7 * 24 * 3600 * 1000;
const YAVAS_KARE_MS = 25;
export function keskinYazilimKayitli(simdi: number, depo?: Pick<Storage, "getItem">): boolean {
  try {
    const k = JSON.parse((depo ?? globalThis.localStorage).getItem(YAZILIM_KAYIT) ?? "null") as { t?: number } | null;
    return !!k && typeof k.t === "number" && simdi - k.t >= 0 && simdi - k.t < YAZILIM_OMUR_MS;
  } catch { return false; }
}
export function karelerYavasMi(araliklar: readonly number[]): boolean {
  if (araliklar.length < 5) return false;
  const s = [...araliklar].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)] > YAVAS_KARE_MS;
}

/** #vt-keskin kernelMatrix="0 -0.45 0 -0.45 2.8 -0.45 0 -0.45 0" (Hero.tsx) — test ikisinin aynı kaldığını denetler. */
export const KESKIN_CEKIRDEK = { merkez: 2.8, komsu: 0.45 } as const;

export const KESKIN_KOSE = "attribute vec2 k;void main(){gl_Position=vec4(k,0.,1.);}";
export const KESKIN_PARCA =
  "precision highp float;uniform sampler2D t;uniform vec4 m;uniform vec2 a;uniform float h;" +
  "void main(){vec2 u=vec2(gl_FragCoord.x,h-gl_FragCoord.y)*m.xy+m.zw;" +
  `vec3 o=${KESKIN_CEKIRDEK.merkez.toFixed(2)}*texture2D(t,u).rgb-${KESKIN_CEKIRDEK.komsu.toFixed(2)}*(texture2D(t,u+vec2(a.x,0.)).rgb` +
  "+texture2D(t,u-vec2(a.x,0.)).rgb+texture2D(t,u+vec2(0.,a.y)).rgb+texture2D(t,u-vec2(0.,a.y)).rgb);" +
  "gl_FragColor=vec4(clamp(o,0.,1.),1.);}";

/** Yalnız Firefox (Gecko; iOS'taki FxiOS WebKit'tir, «Firefox/» içermez) ve requestVideoFrameCallback varsa. */
export function keskinGLGerekli(ua: string, videoProto: object | undefined): boolean {
  return /\bFirefox\/\d/.test(ua) && !!videoProto && "requestVideoFrameCallback" in videoProto;
}

/** object-position bileşeni → kutu içi kayma (CSS pikseli): yüzde ya da piksel. */
function konum(deger: string | undefined, bos: number): number {
  const v = parseFloat(deger ?? "");
  if (!Number.isFinite(v)) return 0.5 * bos;
  return deger!.trim().endsWith("%") ? (v / 100) * bos : v;
}

export type KeskinEslem = { m: [number, number, number, number]; a: [number, number] };

/** object-fit: cover eşlemesi. W×H: video kutusu (CSS pikseli, KESİRLİ — tamsayıya yuvarlanırsa 1x ekranda ince desen kayıyor, ölçüldü);
 *  w×h: video karesi; objectPosition: hesaplanmış değer ("50% 0%"); dpr: aygıt pikseli / CSS pikseli. Tampon satırları aygıt
 *  pikseline birebir oturur (Firefox tuvali germiyor): tampon pikseli (sol üstten, piksel ortası) p → CSS p/dpr → doku
 *  u = p·m.xy + m.zw; a: 1 CSS pikseli komşu uzaklığı doku biriminde. */
export function keskinEslem(W: number, H: number, w: number, h: number, objectPosition: string, dpr: number): KeskinEslem {
  const s = Math.max(W / w, H / h);
  const [px, py] = objectPosition.trim().split(/\s+/);
  const ox = konum(px, W - w * s), oy = konum(py ?? "50%", H - h * s);
  return { m: [1 / (dpr * w * s), 1 / (dpr * h * s), -ox / (w * s), -oy / (h * s)], a: [1 / (w * s), 1 / (h * s)] };
}

type Kutu = { W: number; H: number; gw: number; gh: number; dpr: number };

/** ResizeObserver girdisinden kutu (CSS pikseli, kesirli) ve tampon (× dpr, yuvarlanmış) boyu; girdi yoksa yedek (getBoundingClientRect). */
export function kutuOlc(g: { contentBoxSize?: ReadonlyArray<{ inlineSize: number; blockSize: number }> } | undefined, yedek: { W: number; H: number }, dpr: number): Kutu {
  const c = g?.contentBoxSize?.[0];
  const W = Math.max(1, c && c.inlineSize > 0 ? c.inlineSize : yedek.W), H = Math.max(1, c && c.blockSize > 0 ? c.blockSize : yedek.H);
  return { W, H, gw: Math.max(1, Math.round(W * dpr)), gh: Math.max(1, Math.round(H * dpr)), dpr };
}

/** Tuvali videoya bağlar. Dönen işlev söker (tuvali gizler, videonun CSS süzgecini geri verir, bağlamı bırakır); kurulamazsa null. */
export function keskinGLKur(v: HTMLVideoElement, c: HTMLCanvasElement): (() => void) | null {
  const gl = c.getContext("webgl", { alpha: false, antialias: false, depth: false, stencil: false, premultipliedAlpha: false,
    preserveDrawingBuffer: false, failIfMajorPerformanceCaveat: true });
  if (!gl || gl.isContextLost()) return null;
  const birak = () => { gl.getExtension("WEBGL_lose_context")?.loseContext(); };
  const golge = (tur: number, kod: string) => { const s = gl.createShader(tur); if (!s) return null; gl.shaderSource(s, kod); gl.compileShader(s); return s; };
  const p = gl.createProgram(), ks = golge(gl.VERTEX_SHADER, KESKIN_KOSE), ps = golge(gl.FRAGMENT_SHADER, KESKIN_PARCA);
  const tampon = gl.createBuffer(), doku = gl.createTexture();
  if (!p || !ks || !ps || !tampon || !doku) { birak(); return null; }
  gl.attachShader(p, ks); gl.attachShader(p, ps); gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { birak(); return null; }
  gl.useProgram(p);
  gl.bindBuffer(gl.ARRAY_BUFFER, tampon);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const k = gl.getAttribLocation(p, "k"); gl.enableVertexAttribArray(k); gl.vertexAttribPointer(k, 2, gl.FLOAT, false, 0, 0);
  gl.bindTexture(gl.TEXTURE_2D, doku);
  for (const [ad, deger] of [[gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE], [gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR]]) gl.texParameteri(gl.TEXTURE_2D, ad, deger);
  const uM = gl.getUniformLocation(p, "m"), uA = gl.getUniformLocation(p, "a"), uH = gl.getUniformLocation(p, "h");
  let kutu: Kutu | null = null, eslemli = false, bitti = false, hazir = false, istek = 0;
  const yedekKutu = () => { const r = v.getBoundingClientRect(); return { W: r.width, H: r.height }; };   // aynalama genişliği değiştirmez
  // ilk saniyenin kare aralığı: yazılımla birleştirmede tuval ana iş parçacığını kilitliyor → CSS süzgecine dön, 7 gün hatırla
  const sina = () => {
    const d: number[] = []; let onceki = -1, bas = -1;
    const f = (t: number) => {
      if (bitti || document.visibilityState !== "visible") return;
      if (bas < 0) bas = t;
      if (onceki >= 0) d.push(t - onceki);
      onceki = t;
      if (d.length < 30 && t - bas < 1000) { requestAnimationFrame(f); return; }
      if (karelerYavasMi(d)) {
        sok();
        try { localStorage.setItem(YAZILIM_KAYIT, JSON.stringify({ t: Date.now() })); } catch { /* depo yok */ }
      }
    };
    requestAnimationFrame(() => requestAnimationFrame(f));   // ilk çizimin kurulum maliyeti sayılmaz
  };
  const ciz = () => {
    if (bitti || !v.videoWidth || v.readyState < 2) return;
    if (!eslemli) {
      kutu ??= kutuOlc(undefined, yedekKutu(), window.devicePixelRatio || 1);
      if (c.width !== kutu.gw || c.height !== kutu.gh) { c.width = kutu.gw; c.height = kutu.gh; }
      const e = keskinEslem(kutu.W, kutu.H, v.videoWidth, v.videoHeight, getComputedStyle(v).objectPosition, kutu.dpr);
      gl.viewport(0, 0, kutu.gw, kutu.gh);
      gl.uniform4f(uM, ...e.m); gl.uniform2f(uA, ...e.a); gl.uniform1f(uH, kutu.gh);
      eslemli = true;
    }
    try {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, v);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    } catch { sok(); return; }
    if (!hazir) {
      if (gl.getError() !== gl.NO_ERROR) { sok(); return; }   // ilk karede yükleme/çizim hatası: tuval hiç görünmez, CSS süzgeci kalır
      hazir = true; c.classList.add("is-hazir"); v.classList.add("is-gl");
      sina();
    }
  };
  const kare = () => { if (bitti) return; ciz(); if (!bitti) istek = v.requestVideoFrameCallback(kare); };
  // kutu ya da kırılım (object-position) değişince tampon ve eşlem yenilenir
  const ro = new ResizeObserver((girdiler) => {
    kutu = kutuOlc(girdiler[girdiler.length - 1], yedekKutu(), window.devicePixelRatio || 1);
    eslemli = false; ciz();
  });
  // yoğunluk değişimi (ResizeObserver Firefox'ta bunu bildirmiyor): CSS boyu aynı, tampon yeni dpr ile
  let mq: MediaQueryList | null = null;
  const yogunluk = () => {
    mq?.removeEventListener("change", yogunluk);
    if (bitti || typeof window.matchMedia !== "function") return;
    const dpr = window.devicePixelRatio || 1;
    mq = window.matchMedia(`(resolution: ${dpr}dppx)`);
    mq.addEventListener("change", yogunluk);
    if (kutu && (Math.round(kutu.W * dpr) !== kutu.gw || Math.round(kutu.H * dpr) !== kutu.gh)) { kutu = kutuOlc(undefined, { W: kutu.W, H: kutu.H }, dpr); eslemli = false; ciz(); }
  };
  const kayip = (e: Event) => { e.preventDefault(); sok(); };
  function sok() {
    if (bitti) return;
    bitti = true; ro.disconnect(); mq?.removeEventListener("change", yogunluk); v.cancelVideoFrameCallback(istek); c.removeEventListener("webglcontextlost", kayip);
    c.classList.remove("is-hazir"); v.classList.remove("is-gl");
    birak();
  }
  c.addEventListener("webglcontextlost", kayip);
  ro.observe(v);
  yogunluk();
  istek = v.requestVideoFrameCallback(kare);
  return sok;
}
