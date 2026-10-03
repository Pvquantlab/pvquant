import { useEffect } from "react";

/** Kaydırma canlılığı (R25): [data-canlan] taşıyan bölümler görünür olunca `is-acildi` alır;
 *  CSS yalnız opacity+translateY geçirir (vitrin.css CİLA-ek 4). Kurallar: hero reveal almaz
 *  (sayfa açılışta tam durur), %5 görünürlükte tetiklenir (hızlı kaydırmada boş kare penceresi daralsın) ve bir kez çalışır (unobserve),
 *  azaltılmış harekette CSS zaten kapalı olduğundan sınıf eklemek zararsızdır. IO yoksa
 *  (çok eski motor) hiçbir şey gizlenmez: gizleme sınıfı da burada eklenir, böylece JS'siz
 *  ya da IO'suz ortamda içerik baştan görünür kalır. */
export function useCanlandir(tetik?: unknown) {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const hedefler = Array.from(document.querySelectorAll<HTMLElement>("[data-canlan]:not(.is-acildi)"));
    if (hedefler.length === 0) return;
    const io = new IntersectionObserver((girdiler) => {
      for (const g of girdiler) {
        if (!g.isIntersecting) continue;
        g.target.classList.remove("is-bekliyor");
        g.target.classList.add("is-acildi");
        io.unobserve(g.target);
      }
    }, { threshold: 0.05, rootMargin: "0px 0px -24px 0px" });
    for (const e of hedefler) {
      // gizleme sınıfı IO kurulduktan sonra eklenir: IO yoksa içerik hiç gizlenmez
      if (e.getBoundingClientRect().top > window.innerHeight) e.classList.add("is-bekliyor");
      else { e.classList.remove("is-bekliyor"); e.classList.add("is-acildi"); continue; }
      io.observe(e);
    }
    return () => io.disconnect();
  }, [tetik]);
}
