import { useEffect, useRef } from "react";
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

export function Hero() {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    v.muted = true;                                            // tarayıcılar otomatik oynatmayı yalnız sessiz videoya verir
    v.playbackRate = OYNATMA_HIZI;
    // aralık yalnız 25,8 s'lik orijinal için; ≤760 px'teki 12 s'lik 1080p döngü zaten iyi bölümden kesilmiş — olduğu gibi döner
    const araliksiz = () => !(v.duration > DONGU_SON + 1);
    const basaSar = () => { if (!araliksiz()) v.currentTime = DONGU_BAS; };
    const aralik = () => { if (araliksiz()) return; if (v.currentTime >= DONGU_SON || v.currentTime < DONGU_BAS - 0.25) basaSar(); };
    if (v.readyState >= 1) basaSar(); else v.addEventListener("loadedmetadata", basaSar, { once: true });
    v.addEventListener("timeupdate", aralik);
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    let gorunur = true;
    const uygula = () => {                                     // tercih oturum içinde değişirse de uyulur
      if (!mq.matches && gorunur && document.visibilityState === "visible") v.play().catch(() => {});
      else v.pause();
    };
    const io = typeof IntersectionObserver === "undefined" ? null
      : new IntersectionObserver(([g]) => { gorunur = g.isIntersecting; uygula(); });
    io?.observe(v);
    mq.addEventListener("change", uygula);
    document.addEventListener("visibilitychange", uygula);
    uygula();
    return () => { io?.disconnect(); mq.removeEventListener("change", uygula); document.removeEventListener("visibilitychange", uygula); v.removeEventListener("timeupdate", aralik); };
  }, []);
  return (
    <section className="vt-hero vt-hero--a vt-hero--video" aria-labelledby="vt-hero-baslik">
      {/* 14.10: videoya hafif keskinleştirme (SVG unsharp çekirdeği) — uzak panel sıraları 1440p'de yumuşak kalıyordu */}
      <svg className="vt-hero__filtre" width="0" height="0" aria-hidden="true" focusable="false">
        <filter id="vt-keskin" colorInterpolationFilters="sRGB">
          <feConvolveMatrix order="3" kernelMatrix="0 -0.45 0 -0.45 2.8 -0.45 0 -0.45 0" divisor="1" preserveAlpha="true" edgeMode="duplicate" />
        </filter>
      </svg>
      <div className="vt-hero__sahne" aria-hidden="true">
        <video ref={video} className="vt-hero__video" poster={santralPoster} muted loop playsInline disablePictureInPicture preload="metadata" width="2560" height="1440" tabIndex={-1}>
          <source src={santral1080} type="video/mp4" media="(max-width: 760px)" />
          <source src={santral1440} type="video/mp4" />
        </video>
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
