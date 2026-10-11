import { useEffect, useRef } from "react";
import { ReferansEgri } from "./ReferansEgri";
import santral1080 from "./varlik/santral-1080.mp4";
import santral720 from "./varlik/santral-720.mp4";
import santralPoster from "./varlik/santral-poster.webp";

/** Hero (11.10): sahne bir santral üzerinde yavaş drone çekimi — 12 sn dikişsiz döngü (son 1,2 sn
 *  baştakiyle çapraz geçer), sessiz, 1080p (dar ekranda 720p). Sahne salt süs (aria-hidden); gece
 *  örtüsü metni okunur tutar. Hareket azaltma tercihinde yalnız ilk kare (poster) durur; ekran
 *  dışında ya da sekme gizliyken oynatma bekler. Ürün penceresi (gerçek 01.10 koşusu grafiği)
 *  sahnenin önünde. Künye kartuşu kullanıcı isteğiyle kaldırıldı (11.10). */
export function Hero() {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    v.muted = true;                                            // tarayıcılar otomatik oynatmayı yalnız sessiz videoya verir
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
    return () => { io?.disconnect(); mq.removeEventListener("change", uygula); document.removeEventListener("visibilitychange", uygula); };
  }, []);
  return (
    <section className="vt-hero vt-hero--a vt-hero--video" aria-labelledby="vt-hero-baslik">
      <div className="vt-hero__sahne" aria-hidden="true">
        <video ref={video} className="vt-hero__video" poster={santralPoster} muted loop playsInline disablePictureInPicture preload="metadata" width="1920" height="1080" tabIndex={-1}>
          <source src={santral720} type="video/mp4" media="(max-width: 760px)" />
          <source src={santral1080} type="video/mp4" />
        </video>
      </div>
      <div className="vt-kap vt-hero__ic">
        <div className="vt-hero__sol">
          <h1 className="vt-h1 vt-hero__baslik" id="vt-hero-baslik"><span className="vt-h1__vurgu">Güneş santraliniz için</span> saatlik üretim tahmini ve günlük doğruluk karnesi.</h1>
          <p className="vt-giris vt-hero__giris">PVQuant, güneş santralinizin saatlik üretimini 15 güne kadar tahmin eder ve her tahmine bir güven aralığı ekler. Günlük üretim programınız bildirim saatinden önce hazır olur; tahmin ile gerçekleşen üretim arasındaki farkın size maliyeti panelde günlük olarak raporlanır. Her tahmin, <a className="vt-bag vt-bag--metin" href="#karne">ertesi gün gerçekleşen üretimle karşılaştırılır</a>.</p>
          <div className="vt-eylemler vt-hero__eylem">
            <a className="vt-dugme vt-dugme--dolu vt-dugme--ok" href="#basla">Karnenizi başlatın</a>
            <p className="vt-hero__mikro">başvuru · hesabınızı biz kurarız · veri yüklemeniz gerekmez · karneniz ilk gece sınavından itibaren birikir</p>
            <a className="vt-bag" href="#para">TL karşılığı nasıl hesaplanır</a>
          </div>
        </div>
        <div className="vt-hero__pencere">
          <ReferansEgri veri={null} />
          <a className="vt-bag vt-hero__tl-alt" href="#para">TL karşılığı nasıl hesaplanır</a>
        </div>
      </div>
    </section>
  );
}
