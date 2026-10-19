/** 19.10 perf/cross-browser — Firefox: hero videosundaki keskinleştirmenin tek geçişli WebGL eşdeğeri.
 *
 *  Hero.tsx'teki SVG süzgeci (#vt-keskin: feConvolveMatrix, o = 2,8·c − 0,45·(sol+sağ+üst+alt), sRGB, alfa korunur) Firefox'ta
 *  WebRender'da yok (gfx.webrender.svg-filter-effects.feconvolvematrix=false): her video karesi işlemcide süzülüyor, kaydırırken tarayıcı
 *  1,6–2,7 çekirdek harcıyor, video karesi geri kalıyordu. Aynı çekirdek burada bir parça gölgelendiricisinde, ekran kartında çalışır:
 *  tuval videonun hemen üstünde, aynı kutuda ve aynı aynalamayla durur; her sunulan video karesinde (requestVideoFrameCallback) kare
 *  dokuya yüklenir ve çizilir. İlk kare çizilene dek tuval gizli, video CSS süzgecini korur; çizilince videonun süzgeci kalkar (.is-gl).
 *
 *  Ölçek: Gecko feConvolveMatrix'i aygıt çözünürlüğünde ama komşuları 1 CSS pikseli uzaktan alarak uyguluyor (ölçüldü: perf/analiz/webgl);
 *  burada da öyle — Firefox'taki görünüm değişmez (kenar enerjisi 18,20 ↔ 18,13; piksel başına ortalama fark 2,5/255, video ölçekleme
 *  süzgecinin farkı). Chromium ve WebKit'te kullanılmaz: onlar süzgeci zaten ekran kartında uyguluyor.
 *  Geri dönüş: WebGL yok, yalnız yazılımla çalışıyor (failIfMajorPerformanceCaveat), bağlam kaybı, requestVideoFrameCallback yok
 *  (Firefox < 132) → tuval kaldırılır, CSS süzgeci olduğu gibi kalır. */

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

export type KeskinEslem = { m: [number, number, number, number]; a: [number, number]; gw: number; gh: number };

/** object-fit: cover eşlemesi. W×H: video kutusu (CSS pikseli); w×h: video karesi; objectPosition: hesaplanmış değer ("50% 0%");
 *  dpr: tuval çözünürlüğü. Dönen m: aygıt pikseli (sol üstten, piksel ortası) → doku koordinatı u = p·m.xy + m.zw;
 *  a: 1 CSS pikseli komşu uzaklığı doku biriminde; gw×gh: tuval tampon boyu. */
export function keskinEslem(W: number, H: number, w: number, h: number, objectPosition: string, dpr: number): KeskinEslem {
  const s = Math.max(W / w, H / h);
  const [px, py] = objectPosition.trim().split(/\s+/);
  const ox = konum(px, W - w * s), oy = konum(py ?? "50%", H - h * s);
  return {
    m: [1 / (dpr * w * s), 1 / (dpr * h * s), -ox / (w * s), -oy / (h * s)],
    a: [1 / (w * s), 1 / (h * s)],
    gw: Math.max(1, Math.round(W * dpr)), gh: Math.max(1, Math.round(H * dpr)),
  };
}

/** Tuvali videoya bağlar. Dönen işlev söker (tuvali gizler, videonun CSS süzgecini geri verir, bağlamı bırakır); kurulamazsa null. */
export function keskinGLKur(v: HTMLVideoElement, c: HTMLCanvasElement): (() => void) | null {
  const gl = c.getContext("webgl", { alpha: false, antialias: false, depth: false, stencil: false, premultipliedAlpha: false,
    preserveDrawingBuffer: false, failIfMajorPerformanceCaveat: true });
  if (!gl) return null;
  const golge = (tur: number, kod: string) => { const s = gl.createShader(tur)!; gl.shaderSource(s, kod); gl.compileShader(s); return s; };
  const p = gl.createProgram()!;
  gl.attachShader(p, golge(gl.VERTEX_SHADER, KESKIN_KOSE));
  gl.attachShader(p, golge(gl.FRAGMENT_SHADER, KESKIN_PARCA));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { gl.getExtension("WEBGL_lose_context")?.loseContext(); return null; }
  gl.useProgram(p);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const k = gl.getAttribLocation(p, "k"); gl.enableVertexAttribArray(k); gl.vertexAttribPointer(k, 2, gl.FLOAT, false, 0, 0);
  gl.bindTexture(gl.TEXTURE_2D, gl.createTexture());
  for (const [ad, deger] of [[gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE], [gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR]]) gl.texParameteri(gl.TEXTURE_2D, ad, deger);
  const uM = gl.getUniformLocation(p, "m"), uA = gl.getUniformLocation(p, "a"), uH = gl.getUniformLocation(p, "h");
  let eslem: KeskinEslem | null = null, bitti = false, hazir = false, istek = 0;
  const ciz = () => {
    if (bitti || !v.videoWidth || v.readyState < 2) return;
    if (!eslem) {
      eslem = keskinEslem(v.clientWidth, v.clientHeight, v.videoWidth, v.videoHeight, getComputedStyle(v).objectPosition, window.devicePixelRatio || 1);
      if (c.width !== eslem.gw || c.height !== eslem.gh) { c.width = eslem.gw; c.height = eslem.gh; }
      gl.viewport(0, 0, eslem.gw, eslem.gh);
      gl.uniform4f(uM, ...eslem.m); gl.uniform2f(uA, ...eslem.a); gl.uniform1f(uH, eslem.gh);
    }
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, v);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (!hazir) { hazir = true; c.classList.add("is-hazir"); v.classList.add("is-gl"); }
  };
  const kare = () => { if (bitti) return; ciz(); istek = v.requestVideoFrameCallback(kare); };
  const ro = new ResizeObserver(() => { eslem = null; ciz(); });   // kutu, kırılım (object-position) ya da dpr değişince
  const kayip = (e: Event) => { e.preventDefault(); sok(); };
  const sok = () => {
    if (bitti) return;
    bitti = true; ro.disconnect(); v.cancelVideoFrameCallback(istek); c.removeEventListener("webglcontextlost", kayip);
    c.classList.remove("is-hazir"); v.classList.remove("is-gl");
    gl.getExtension("WEBGL_lose_context")?.loseContext();
  };
  c.addEventListener("webglcontextlost", kayip);
  ro.observe(v);
  istek = v.requestVideoFrameCallback(kare);
  return sok;
}
