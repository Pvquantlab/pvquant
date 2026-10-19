// keskin-webgl.js — DENEY: hero videosundaki SVG feConvolveMatrix keskinleştirmesinin (o = 2,8c − 0,45·(sol+sağ+üst+alt), sRGB,
// alfa korunur) tek geçişli WebGL eşdeğeri. Sayfaya enjekte edilir; window.__keskinKur(video, { adim }) → söküm işlevi | null.
// adim: komşu pikselin uzaklığı CSS pikseli cinsinden (Gecko feConvolveMatrix'i CSS pikselinde uygular → 1; Chromium aygıt
// pikselinde → 1/dpr). Tuval videonun hemen üstüne konur (poster <img> ve örtü yine üstte kalır), aynı kutu, aynı aynalama;
// object-fit: cover + object-position videodan okunur. İlk kare çizilene dek tuval gizli ve video CSS süzgecini korur.
window.__keskinKur = function (v, ayar) {
  ayar = ayar || {};
  var c = document.createElement("canvas");
  c.setAttribute("aria-hidden", "true");
  c.className = "vt-hero__keskin";
  c.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none;transform:scaleX(-1);visibility:hidden";
  var gl = c.getContext("webgl", { alpha: false, antialias: false, depth: false, stencil: false, premultipliedAlpha: false,
    preserveDrawingBuffer: false, failIfMajorPerformanceCaveat: true });
  if (!gl) return null;
  var derle = function (tur, kod) { var s = gl.createShader(tur); gl.shaderSource(s, kod); gl.compileShader(s); return s; };
  var p = gl.createProgram();
  gl.attachShader(p, derle(gl.VERTEX_SHADER, "attribute vec2 k;void main(){gl_Position=vec4(k,0.,1.);}"));
  gl.attachShader(p, derle(gl.FRAGMENT_SHADER,
    "precision highp float;uniform sampler2D t;uniform vec4 m;uniform vec2 a;uniform float h;uniform vec2 w;" +
    "void main(){vec2 u=vec2(gl_FragCoord.x,h-gl_FragCoord.y)*m.xy+m.zw;" +
    "vec3 o=w.x*texture2D(t,u).rgb-w.y*(texture2D(t,u+vec2(a.x,0.)).rgb+texture2D(t,u-vec2(a.x,0.)).rgb" +
    "+texture2D(t,u+vec2(0.,a.y)).rgb+texture2D(t,u-vec2(0.,a.y)).rgb);gl_FragColor=vec4(clamp(o,0.,1.),1.);}"));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) return null;
  gl.useProgram(p);
  var b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  var kl = gl.getAttribLocation(p, "k"); gl.enableVertexAttribArray(kl); gl.vertexAttribPointer(kl, 2, gl.FLOAT, false, 0, 0);
  var dok = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, dok);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  var uM = gl.getUniformLocation(p, "m"), uA = gl.getUniformLocation(p, "a"), uH = gl.getUniformLocation(p, "h"), uW = gl.getUniformLocation(p, "w");
  gl.uniform2f(uW, ayar.kimlik ? 1 : 2.8, ayar.kimlik ? 0 : 0.45);   // kimlik: süzgeçsiz (ardışık düzen denetimi)
  var kutu = null, bitti = false, gorundu = false, dokBoy = "";
  var olc = function () { var s = getComputedStyle(v).objectPosition.split(" "); kutu = { W: v.clientWidth, H: v.clientHeight,
    px: parseFloat(s[0]) / 100, py: parseFloat(s[1] || "50%") / 100, dpr: ayar.olcek || window.devicePixelRatio || 1 }; };   // olcek: tuval çözünürlüğü (CSS pikseli başına)
  var ciz = function () {
    if (bitti || !v.videoWidth || v.readyState < 2) return;
    if (!kutu) olc();
    var W = kutu.W, H = kutu.H, dpr = kutu.dpr, w = v.videoWidth, hh = v.videoHeight, s = Math.max(W / w, H / hh);
    var gw = Math.max(1, Math.round(W * dpr)), gh = Math.max(1, Math.round(H * dpr));
    if (c.width !== gw || c.height !== gh) { c.width = gw; c.height = gh; gl.viewport(0, 0, gw, gh); }
    var ox = (W - w * s) * kutu.px, oy = (H - hh * s) * kutu.py, adim = ayar.adim || 1;
    gl.uniform4f(uM, 1 / (dpr * w * s), 1 / (dpr * hh * s), -ox / (w * s), -oy / (hh * s));
    gl.uniform2f(uA, adim / (w * s), adim / (hh * s));
    gl.uniform1f(uH, gh);
    if (ayar.alt && dokBoy === w + "x" + hh) gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, v);
    else { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, v); dokBoy = w + "x" + hh; }
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (!gorundu) { gorundu = true; c.style.visibility = "visible"; v.style.setProperty("filter", "none"); }
  };
  var kare = function () { if (bitti) return; ciz(); v.requestVideoFrameCallback(kare); };
  var ro = new ResizeObserver(function () { kutu = null; ciz(); });
  var kayip = function (e) { e.preventDefault(); sok(); };
  var sok = function () {
    if (bitti) return; bitti = true; ro.disconnect(); c.removeEventListener("webglcontextlost", kayip);
    v.style.removeProperty("filter"); c.remove();
    var x = gl.getExtension("WEBGL_lose_context"); if (x) x.loseContext();
  };
  c.addEventListener("webglcontextlost", kayip);
  v.after(c);
  ro.observe(v);
  v.requestVideoFrameCallback(kare);
  if (v.readyState >= 2) ciz();                                    // duraklatılmış videoda ilk kareyi hemen çiz
  window.__keskinSok = sok;
  return sok;
};
