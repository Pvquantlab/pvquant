import { useEffect, useRef } from "react";
import { ReferansEgri } from "./ReferansEgri";
import sahne from "./varlik/hero-ufuk-sahne.svg";
import { GokyuzuCanli } from "./GokyuzuCanli";

/** Hero «Ufuk» (v2.386, cila-a): dokulu ufuk sahnesi — 21 Haziran'dan 21 Aralık'a on beş günde bir,
 *  gerçek güneş geometrisinden hesaplanmış 13 yükseklik yayı + benekli güneş + santral tarlası.
 *  Sahne salt süs (aria-hidden, <img>); dürüst künye sağ altta koyu kartuşta. Ürün penceresi
 *  (gerçek 01.10 koşusu grafiği) sahnenin önünde durur. Yükseklik clamp'i ve uç genişlik kuralları
 *  vitrin.css CİLA katmanında (QA dersi: 1081–1240 ve ≥1920 ayrıca sınanır). */
export function Hero() {
  const sahneImg = useRef<HTMLImageElement>(null);
  useEffect(() => {                                            // paralaks fısıltısı (R29)
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    let kare = 0;
    const kaydir = () => {
      if (kare) return;
      kare = requestAnimationFrame(() => {
        kare = 0;
        const el = sahneImg.current;
        if (el) el.style.transform = `translateY(${Math.min(28, window.scrollY * 0.05).toFixed(1)}px)`;
      });
    };
    const uygula = () => {                                     // tercih oturum içinde değişirse de uyulur
      window.removeEventListener("scroll", kaydir);
      if (mq.matches) { const el = sahneImg.current; if (el) el.style.transform = ""; return; }
      window.addEventListener("scroll", kaydir, { passive: true });
    };
    uygula();
    mq.addEventListener("change", uygula);
    return () => { mq.removeEventListener("change", uygula); window.removeEventListener("scroll", kaydir); if (kare) cancelAnimationFrame(kare); };
  }, []);
  return (
    <section className="vt-hero vt-hero--a" aria-labelledby="vt-hero-baslik">
      <div className="vt-hero__sahne" aria-hidden="true">
        <img ref={sahneImg} src={sahne} alt="" width="1000" height="720" />
      </div>
      <div className="vt-kap vt-hero__ic">
        <div className="vt-hero__sol">
          <h1 className="vt-h1 vt-hero__baslik" id="vt-hero-baslik"><span className="vt-h1__vurgu">Programı zamanında verin;</span> sapmanın TL&#39;sini gün&nbsp;gün görün.</h1>
          <p className="vt-giris vt-hero__giris">Türkiye&#39;deki güneş santralleri için iyimser–kötümser aralığıyla saatlik üretim tahmini. Program dosyanız teslim penceresi kapanmadan hazır; sapmanın TL karşılığı, basit yönteme göre farkıyla birlikte panelde gün gün. Tahmin <a className="vt-bag vt-bag--metin" href="#karne">her gece gerçekleşenle sınanır</a>.</p>
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
      <p className="vt-kunye vt-hero__kunye">güneş yükseklik yayları · 21{" "}Haziran’dan 21{" "}Aralık’a on beş günde bir · İç{" "}Anadolu enlemi (38°{" "}K) · manzara temsili<GokyuzuCanli /></p>
    </section>
  );
}
