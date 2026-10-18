import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { heroBekle, heroHazirOldu, posterYavasMi } from "./heroHazir";
import santral1440 from "./varlik/santral-1440.mp4";
import santral1080 from "./varlik/santral-1080.mp4";
import santralPoster from "./varlik/santral-poster.webp";

/** Hero (13.10 jua katmanı: tam yükseklik, dikey perde, tek sütun metin; ürün penceresi Açık karne bölümüne taşındı; vurgu sona taşındı,
 *  TL bağı ikincil hap düğme oldu — görünüm vitrin.css «Jua katmanı»nda).
 *  Hero (11.10; 13.10 «orijinal haliyle»): sahne bir santral üzerinde yavaş drone çekimi, sessiz. Geniş ekranda
 *  kaynak dosyanın KENDİSİ, kesilmeden ve yeniden kodlanmadan (2560×1440, 25,8 sn; masaüstündeki
 *  12299056-uhd_2560_1440_30fps.mp4 ile bayt bayt aynı); döngü sonunda başa döner. Üstünde hiçbir örtü yok. ≤760 px'te
 *  12 sn dikişsiz 1080p döngü. Sahne salt süs (aria-hidden); gece örtüsü metni okunur tutar. Hareket
 *  azaltma tercihinde yalnız ilk kare (poster) durur; ekran dışında ya da sekme gizliyken oynatma bekler.
 *  Ürün penceresi (gerçek 01.10 koşusu grafiği) sahnenin önünde. Künye kartuşu kullanıcı isteğiyle kaldırıldı. */
/** Döngü aralığı (14.10, ölçüldü): panel bölgesinin kenar keskinliği 7,5–19 s arasında en yüksek (Laplace ≥ 22 bin);
 *  ilk 6 s en zayıf ve şirket tabelasını içeriyor, 20 s sonrası düşüyor. Dosya olduğu gibi; yalnız bu aralık oynar.
 *  16.10 hız turu 4 (kullanıcı kararı, «melez»): İLK oynatma posterin kendi karesinden başlar — poster resmi videonun
 *  ~6,07 s karesi (tuvalde karşılaştırıldı: 6,04–6,11 s en yakın; 7,5 s belirgin uzak). Önce 7,5'ten başlıyordu: poster →
 *  video eriyişinde 1,4 s'lik kamera sıçraması ve 900 ms çift görüntü vardı, ilk kareden önce ~2 MB fazladan iniyordu.
 *  Döngü dönüşleri 9,009 s anahtar karesine (MP4 stss: 3,003 s arayla) — keskin aralığın içinde. */
const ILK_BAS = 6.0727;
const DONGU_BAS = 9.009;
const DONGU_SON = 19.0;
/** 16.10 hız turu 4 (kullanıcı kararı): posteri (474 KB) 2 sn'den uzun sürede indiren hat videoyu (mobil 6,9 MB,
 *  masaüstü 36 MB) akıcı oynatamaz — veri ve bant harcar, takılır. Bağlantı türü API'si yalnız Chrome'da var ve
 *  kısıtlı hatta bile çoğu zaman «4g» diyor (ölçüldü: 1,6 Mbps'de video yine indi); ölçü tarayıcıdan bağımsız:
 *  posterin kendi indirme süresi (Resource Timing). Poster 1 yıl önbellekte kalır; önbellekten geldiğinde (aktarım 0)
 *  süre hat hakkında bir şey söylemez — o zaman son AĞ ölçümünün kararı kullanılır (7 gün geçerli; yoksa video oynar).
 *  18.10: «ağdan mı» testi motor bağımsız (Firefox bellek önbelleğinde RT girdisi yazmıyor, WebKit 0 bayt yazıp
 *  kaydı {y:false} ile eziyordu) — ölçüm ve kayıt heroHazir.ts posterYavasMi'de. */
/** 18.10 (perf/cross-browser): Gecko feConvolveMatrix'i WebRender'da çalıştırmıyor (gfx.webrender.svg-filter-effects
 *  .feconvolvematrix = false) — filtreli video ve poster her değişimde CPU'da süzülüyor (stok Firefox 158, 1440@2,
 *  kaydırırken 1,6 çekirdek, %7 kaçan kare; filtresiz 0,36 çekirdek). Aynı çekirdek, o = 2,8c − 0,45·(l+r+u+d), WebRender'ın
 *  GPU'da çalıştırdığı ilkellerle kurulur (4 feOffset + 4 aritmetik feComposite; Gecko ≥ 132'de varsayılan açık; ESR 128/115
 *  ve öncesinde bu ilkeller de CPU'da → özgün filtre kalır). Ofset 1 AYGIT pikseli: Chromium çekirdeği aygıt pikselinde
 *  uygular (referans görünüm; ayrışık kurulum Chromium'un özgün çıktısıyla ≤2/255 aynı), Gecko'nun feConvolveMatrix'i CSS
 *  pikselinde uyguluyordu — Retina'da iki kat kaba, belirgin fazla keskin (kenar enerjisi 12,9 ↔ Chrome 9,4; yeni 9,5).
 *  Ölçümler: perf/analiz (filtre-esdeger, ab-boya). 1,001: Gecko ofseti tamsayıya keserse 1 aygıt pikselinin altına düşmesin. */
function geckoWebRenderFiltresi(): boolean {
  if (typeof navigator === "undefined") return false;
  const m = /\bFirefox\/(\d+)/.exec(navigator.userAgent);
  return !!m && Number(m[1]) >= 132;
}
const OYNATMA_HIZI = 0.7;   // 14.10 kullanıcı: arka plan göze batmasın — %70 hız (11,5 s'lik aralık ~16 s sürer)

/** Açılış sırası (16.10 hız turu 3 — film ölçümü: hero ilk boyamada siyah zeminle açılıyor, poster
 *  levhalar/videoyla yarışıp mobil 3G'de 11 sn'de iniyor, video poster gelmeden ve farklı kareden başlıyordu):
 *  1) zemin: posterin kendi renklerinden gradyan (vitrin.css «Hız turu 3»; fotoğrafa dokunulmaz);
 *  2) poster: aynı dosya, yüksek öncelikli <img> + videonun kendi posteri; üstteki örtü poster tamamen
 *     çözülünce 450 ms'de solar (yarım çizim görünmez). Hız turu 4: istek index.html'deki betikten, CSS iner
 *     inmez başlar (vite.config «pvq-vitrin-kabugu»); <img> o yanıtı kullanır;
 *  3) video: YALNIZ poster + sayfa yüklendikten sonra ve hero ekrandayken iner; oynamaya başlayınca üstteki poster resmi 900 ms'de
 *     solar (poster 6,07 sn karesi, ilk oynatma da oradan — aynı kare üzerinde erime). Veri tasarrufu, 2G/3G, posteri
 *     2 sn'den uzun sürede indiren hat ve hareket azaltma tercihinde video hiç indirilmez, poster kalır.
 *  LCP (canlı ölçüm v2.451): saydamdan görünüre geçen video ilk karesinde yeni LCP adayı oluyordu (masaüstü 4G
 *  6,0 sn). Video baştan görünür ve posterli olunca yalnız poster anında bir kez sayılır; örtü ve zemin düşük
 *  bilgili SVG olduğundan aday değildir.
 *  Önceki kusur: görünürlük gözlemcisi ilk çağrısında play() diyordu; preload="none" videoda play() indirmeyi
 *  başlatır — «load sonrası» kuralı hiç işlemiyordu (mobil 4G'de video 0,98 sn'de inmeye başlıyordu). */
export function Hero({ kabuk = false }: { kabuk?: boolean } = {}) {
  heroBekle();
  const video = useRef<HTMLVideoElement>(null);
  const [posterHazir, setPosterHazir] = useState(false);
  const [videoGorunur, setVideoGorunur] = useState(false);
  const yavasHat = useRef(false);
  const [wr] = useState(geckoWebRenderFiltresi);
  const [kayma, setKayma] = useState(() => (typeof window === "undefined" ? 1.001 : 1.001 / (window.devicePixelRatio || 1)));
  useEffect(() => {                                            // yakınlaştırma / ekran değişimi aygıt piksel oranını değiştirir
    if (!wr) return;
    let mq: MediaQueryList | null = null;
    const izle = () => {
      const dpr = window.devicePixelRatio || 1;
      setKayma(1.001 / dpr);
      mq?.removeEventListener("change", izle);
      mq = window.matchMedia(`(resolution: ${dpr}dppx)`);
      mq.addEventListener("change", izle);
    };
    izle();
    return () => mq?.removeEventListener("change", izle);
  }, [wr]);
  const posterYuklendi = (e: SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    yavasHat.current = posterYavasMi(new URL(santralPoster, window.location.href).href);
    (typeof img.decode === "function" ? img.decode() : Promise.resolve()).catch(() => {}).then(() => { setPosterHazir(true); heroHazirOldu(); });
  };
  const posterHata = () => { yavasHat.current = true; setPosterHazir(true); heroHazirOldu(); };   // poster yoksa video da denenmez
  // poster çok gecikirse (çok yavaş hat) levhalar en geç 5 sn sonra serbest
  useEffect(() => { const t = window.setTimeout(heroHazirOldu, 5000); return () => window.clearTimeout(t); }, []);
  useEffect(() => {
    const v = video.current;
    if (!v || !posterHazir) return;
    const baglanti = (navigator as Navigator & { connection?: { effectiveType?: string; saveData?: boolean } }).connection;
    const kisit = !!baglanti && (baglanti.saveData === true || /(^|-)2g$|^3g$/.test(baglanti.effectiveType ?? ""));
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (kisit || yavasHat.current || mq.matches) return;       // video hiç inmez; poster sahnede kalır
    v.muted = true;                                            // tarayıcılar otomatik oynatmayı yalnız sessiz videoya verir
    // aralık yalnız 25,8 s'lik orijinal için; ≤760 px'teki 12 s'lik 1080p döngü zaten iyi bölümden kesilmiş — olduğu gibi döner
    const araliksiz = () => !(v.duration > DONGU_SON + 1);
    let ilkTur = true;                                         // ilk tur poster karesinden, sonrakiler DONGU_BAS'tan
    const basaSar = () => { if (!araliksiz()) v.currentTime = ILK_BAS; };
    const aralik = () => {
      if (araliksiz()) return;
      const t = v.currentTime;
      if (t >= DONGU_SON) { ilkTur = false; v.currentTime = DONGU_BAS; return; }
      const alt = ilkTur ? ILK_BAS : DONGU_BAS;
      if (t < alt - 0.25) v.currentTime = alt;                 // dosya sonundan «loop» ile başa dönerse de aralığa
    };
    v.addEventListener("loadedmetadata", basaSar);
    v.addEventListener("timeupdate", aralik);
    const oynuyor = () => { requestAnimationFrame(() => setVideoGorunur(true)); };
    v.addEventListener("playing", oynuyor);
    // 16.10 hız turu 4: indirme YALNIZ hero ilk kez ekranda (ve sekme görünür) olunca başlar. Önce load() sayfa
    // yüklenir yüklenmez çağrılıyordu: /#karne, /#sss gibi çapalı açılışta hero ekran dışındayken duraklatılmış
    // video tamponu dolduruyordu (ölçüldü: masaüstü 4G'de 15 sn'de ~12 MB). play() de yüklemeden önce çağrılmaz.
    let izin = false;                                          // sayfa yüklendi (window load)
    let yuklendi = false;                                      // load() bir kez çağrıldı
    let gorunur = typeof IntersectionObserver === "undefined"; // IO yoksa görünür say; varsa ilk geri çağrı söyler
    const uygula = () => {
      if (!izin) return;
      const ekranda = gorunur && document.visibilityState === "visible";
      if (ekranda && !yuklendi) { yuklendi = true; v.preload = "auto"; v.load(); v.playbackRate = OYNATMA_HIZI; } // load() hızı sıfırlar
      if (!yuklendi) return;
      if (ekranda) v.play().catch(() => {}); else v.pause();
    };
    const io = typeof IntersectionObserver === "undefined" ? null
      : new IntersectionObserver(([g]) => { gorunur = !!g?.isIntersecting; uygula(); });
    io?.observe(v);
    document.addEventListener("visibilitychange", uygula);
    const basla = () => { izin = true; uygula(); };
    if (document.readyState === "complete") basla(); else window.addEventListener("load", basla, { once: true });
    return () => {
      window.removeEventListener("load", basla); io?.disconnect(); document.removeEventListener("visibilitychange", uygula);
      v.removeEventListener("loadedmetadata", basaSar); v.removeEventListener("timeupdate", aralik); v.removeEventListener("playing", oynuyor);
      // gerçek ayrılışta (vitrin → giriş/panel) süren video indirmesi durur; yoksa masaüstündeki 36 MB'lık dosya panel parçalarıyla
      // bant paylaşmaya devam ediyordu. StrictMode'un deneme sökümünde öğe DOM'da kalır — dokunulmaz.
      if (!v.isConnected) { v.pause(); for (const s of [...v.querySelectorAll("source")]) s.remove(); v.removeAttribute("src"); v.load(); }
    };
  }, [posterHazir]);
  return (
    <section className={wr ? "vt-hero vt-hero--a vt-hero--video vt-hero--wr" : "vt-hero vt-hero--a vt-hero--video"} aria-labelledby="vt-hero-baslik">
      {/* 14.10: videoya hafif keskinleştirme (SVG unsharp çekirdeği) — uzak panel sıraları 1440p'de yumuşak kalıyordu */}
      <svg className="vt-hero__filtre" width="0" height="0" aria-hidden="true" focusable="false">
        <filter id="vt-keskin" colorInterpolationFilters="sRGB">
          <feConvolveMatrix order="3" kernelMatrix="0 -0.45 0 -0.45 2.8 -0.45 0 -0.45 0" divisor="1" preserveAlpha="true" edgeMode="duplicate" />
        </filter>
        {wr && (
          <filter id="vt-keskin-wr" colorInterpolationFilters="sRGB" x="0" y="0" width="1" height="1">
            <feOffset in="SourceGraphic" dx={kayma.toFixed(4)} dy="0" result="l" />
            <feOffset in="SourceGraphic" dx={(-kayma).toFixed(4)} dy="0" result="r" />
            <feOffset in="SourceGraphic" dx="0" dy={kayma.toFixed(4)} result="u" />
            <feOffset in="SourceGraphic" dx="0" dy={(-kayma).toFixed(4)} result="a" />
            <feComposite in="l" in2="r" operator="arithmetic" k2="0.5" k3="0.5" result="lr" />
            <feComposite in="u" in2="a" operator="arithmetic" k2="0.5" k3="0.5" result="ua" />
            <feComposite in="lr" in2="ua" operator="arithmetic" k2="0.5" k3="0.5" result="m" />
            <feComposite in="SourceGraphic" in2="m" operator="arithmetic" k2="2.8" k3="-1.8" />
          </filter>
        )}
      </svg>
      <div className="vt-hero__sahne" aria-hidden="true">
        {/* Katmanlar (alttan üste): video (posterini kendi çizer, baştan görünür) → poster resmi (aynı dosya; video
            oynayınca solar — sıçrama yerine erime) → örtü (zeminle aynı gradyan; poster tamamen çözülünce solar —
            yarım çizim görünmez). Kabuk (derlemede HTML'e dökülen ilk ekran) video ve posteri içermez. */}
        {!kabuk && (
        <video ref={video} className="vt-hero__video" poster={santralPoster} muted loop playsInline disablePictureInPicture preload="none" width="2560" height="1440" tabIndex={-1}>
          <source src={santral1080} type="video/mp4" media="(max-width: 760px)" />
          <source src={santral1440} type="video/mp4" />
        </video>
        )}
        {!kabuk && <img className={videoGorunur ? "vt-hero__poster is-gecti" : "vt-hero__poster"} src={santralPoster} alt="" width="2560" height="1440"
          fetchPriority="high" decoding="async" onLoad={posterYuklendi} onError={posterHata} />}
        <div className={posterHazir ? "vt-hero__ortu is-acik" : "vt-hero__ortu"} />
      </div>
      <div className="vt-kap vt-hero__ic">
        <div className="vt-hero__sol">
          <h1 className="vt-h1 vt-hero__baslik" id="vt-hero-baslik"><span className="vt-h1__vurgu">Güneş santraliniz için</span> saatlik üretim tahmini ve günlük doğruluk karnesi.</h1>
          <p className="vt-giris vt-hero__giris">PVQuant, güneş santralinizin saatlik üretimini 15 güne kadar tahmin eder ve her tahmine bir güven aralığı ekler. Günlük üretim programınız bildirim saatinden önce hazır olur; tahmin ile gerçekleşen üretim arasındaki farkın size maliyeti panelde günlük olarak raporlanır. Her tahmin, <a className="vt-bag vt-bag--metin" href="#karne">ertesi gün gerçekleşen üretimle karşılaştırılır</a>.</p>
          <div className="vt-eylemler vt-hero__eylem">
            <a className="vt-dugme vt-dugme--dolu vt-dugme--ok vt-dugme--buyuk" href="#basla">Karnenizi başlatın</a>
            <a className="vt-dugme vt-dugme--gece-cizgi vt-dugme--buyuk" href="/yontem#para">TL karşılığı nasıl hesaplanır</a>
            <p className="vt-hero__mikro">başvuru · hesabınızı biz kurarız · veri yüklemeniz gerekmez · karneniz ilk gece sınavından itibaren birikir</p>
          </div>
        </div>
      </div>
    </section>
  );
}
