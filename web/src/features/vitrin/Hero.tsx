import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { heroBekle, heroHazirOldu } from "./heroHazir";
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
 *  ilk 6 s en zayıf ve şirket tabelasını içeriyor, 20 s sonrası düşüyor. Dosya olduğu gibi; yalnız bu aralık oynar. */
const DONGU_BAS = 7.5;
const DONGU_SON = 19.0;
const OYNATMA_HIZI = 0.7;   // 14.10 kullanıcı: arka plan göze batmasın — %70 hız (11,5 s'lik aralık ~16 s sürer)

/** Açılış sırası (16.10 hız turu 3 — film ölçümü: hero ilk boyamada siyah zeminle açılıyor, poster
 *  levhalar/videoyla yarışıp mobil 3G'de 11 sn'de iniyor, video poster gelmeden ve farklı kareden başlıyordu):
 *  1) zemin: posterin kendi renklerinden gradyan (vitrin.css «Hız turu 3»; fotoğrafa dokunulmaz);
 *  2) poster: aynı dosya, yüksek öncelikli <img>; tamamen çözülünce 450 ms'de belirir (yarım çizim görünmez);
 *  3) video: YALNIZ poster + sayfa yüklendikten sonra iner; ilk karesi oynayınca 900 ms'lik geçişle görünür
 *     (poster 6,07 sn karesi, döngü 7,5'ten başlar — sıçrama yerine erime). Veri tasarrufu, 2G/3G ve
 *     hareket azaltma tercihinde video hiç indirilmez, poster kalır.
 *  Önceki kusur: görünürlük gözlemcisi ilk çağrısında play() diyordu; preload="none" videoda play() indirmeyi
 *  başlatır — «load sonrası» kuralı hiç işlemiyordu (mobil 4G'de video 0,98 sn'de inmeye başlıyordu). */
export function Hero({ kabuk = false }: { kabuk?: boolean } = {}) {
  heroBekle();
  const video = useRef<HTMLVideoElement>(null);
  const [posterHazir, setPosterHazir] = useState(false);
  const [videoGorunur, setVideoGorunur] = useState(false);
  const posterYuklendi = (e: SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    (typeof img.decode === "function" ? img.decode() : Promise.resolve()).catch(() => {}).then(() => { setPosterHazir(true); heroHazirOldu(); });
  };
  const posterHata = () => { setPosterHazir(true); heroHazirOldu(); };
  // poster çok gecikirse (çok yavaş hat) levhalar en geç 5 sn sonra serbest
  useEffect(() => { const t = window.setTimeout(heroHazirOldu, 5000); return () => window.clearTimeout(t); }, []);
  useEffect(() => {
    const v = video.current;
    if (!v || !posterHazir) return;
    const baglanti = (navigator as Navigator & { connection?: { effectiveType?: string; saveData?: boolean } }).connection;
    const kisit = !!baglanti && (baglanti.saveData === true || /(^|-)2g$|^3g$/.test(baglanti.effectiveType ?? ""));
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (kisit || mq.matches) return;                           // video hiç inmez; poster sahnede kalır
    v.muted = true;                                            // tarayıcılar otomatik oynatmayı yalnız sessiz videoya verir
    // aralık yalnız 25,8 s'lik orijinal için; ≤760 px'teki 12 s'lik 1080p döngü zaten iyi bölümden kesilmiş — olduğu gibi döner
    const araliksiz = () => !(v.duration > DONGU_SON + 1);
    const basaSar = () => { if (!araliksiz()) v.currentTime = DONGU_BAS; };
    const aralik = () => { if (araliksiz()) return; if (v.currentTime >= DONGU_SON || v.currentTime < DONGU_BAS - 0.25) basaSar(); };
    v.addEventListener("loadedmetadata", basaSar);
    v.addEventListener("timeupdate", aralik);
    const oynuyor = () => setVideoGorunur(true);
    v.addEventListener("playing", oynuyor);
    let izin = false;                                          // yükleme başlamadan play() ÇAĞRILMAZ (indirmeyi tetikler)
    let gorunur = true;
    const uygula = () => {
      if (!izin) return;
      if (gorunur && document.visibilityState === "visible") v.play().catch(() => {});
      else v.pause();
    };
    const io = typeof IntersectionObserver === "undefined" ? null
      : new IntersectionObserver(([g]) => { gorunur = !!g?.isIntersecting; uygula(); });
    io?.observe(v);
    document.addEventListener("visibilitychange", uygula);
    const basla = () => { izin = true; v.preload = "auto"; v.load(); v.playbackRate = OYNATMA_HIZI; uygula(); };
    if (document.readyState === "complete") basla(); else window.addEventListener("load", basla, { once: true });
    return () => {
      window.removeEventListener("load", basla); io?.disconnect(); document.removeEventListener("visibilitychange", uygula);
      v.removeEventListener("loadedmetadata", basaSar); v.removeEventListener("timeupdate", aralik); v.removeEventListener("playing", oynuyor);
    };
  }, [posterHazir]);
  return (
    <section className="vt-hero vt-hero--a vt-hero--video" aria-labelledby="vt-hero-baslik">
      {/* 14.10: videoya hafif keskinleştirme (SVG unsharp çekirdeği) — uzak panel sıraları 1440p'de yumuşak kalıyordu */}
      <svg className="vt-hero__filtre" width="0" height="0" aria-hidden="true" focusable="false">
        <filter id="vt-keskin" colorInterpolationFilters="sRGB">
          <feConvolveMatrix order="3" kernelMatrix="0 -0.45 0 -0.45 2.8 -0.45 0 -0.45 0" divisor="1" preserveAlpha="true" edgeMode="duplicate" />
        </filter>
      </svg>
      <div className="vt-hero__sahne" aria-hidden="true">
        {/* kabuk (derlemede HTML'e dökülen ilk ekran) poster ve videoyu içermez: ilk boyamayı geciktirmesinler */}
        {!kabuk && <img className={posterHazir ? "vt-hero__poster is-hazir" : "vt-hero__poster"} src={santralPoster} alt="" width="2560" height="1440"
          fetchPriority="high" decoding="async" onLoad={posterYuklendi} onError={posterHata} />}
        {!kabuk && (
        <video ref={video} className={videoGorunur ? "vt-hero__video is-oynuyor" : "vt-hero__video"} muted loop playsInline disablePictureInPicture preload="none" width="2560" height="1440" tabIndex={-1}>
          <source src={santral1080} type="video/mp4" media="(max-width: 760px)" />
          <source src={santral1440} type="video/mp4" />
        </video>
        )}
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
