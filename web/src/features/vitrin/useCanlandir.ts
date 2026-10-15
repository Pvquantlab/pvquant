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
    // 15.10 hız turu 2: tembel levhalar sayfa ve fontlar indikten sonra DOM sırasıyla, ikişer ikişer
    // önden indirilir — kaydırınca önbellekten anında açılırlar (kullanıcı: «kartlar hemen açılsın»).
    // Yavaş bağlantı/veri tasarrufunda tarayıcının kendi tembel eşiği yeter; önden indirme yapılmaz.
    const baglanti = (navigator as Navigator & { connection?: { effectiveType?: string; saveData?: boolean } }).connection;
    const yavas = !!baglanti && (baglanti.saveData === true || /(^|-)2g$|^3g$/.test(baglanti.effectiveType ?? ""));
    let iptal = false;
    const kur = () => {
      if (iptal || yavas) return;
      const sira = [...document.querySelectorAll<HTMLImageElement>('img[loading="lazy"]')];
      const yukle = (i: number) => {
        if (iptal || i >= sira.length) return;
        const img = sira[i];
        const sonraki = () => yukle(i + 2);
        img.loading = "eager";
        if (img.complete) sonraki();
        else { img.addEventListener("load", sonraki, { once: true }); img.addEventListener("error", sonraki, { once: true }); }
      };
      yukle(0); yukle(1); // iki paralel kuyruk: 0,2,4… ve 1,3,5…
    };
    const hazir = () => { document.fonts.ready.then(kur); };
    if (document.readyState === "complete") hazir(); else window.addEventListener("load", hazir, { once: true });
    return () => { iptal = true; window.removeEventListener("load", hazir); io.disconnect(); };
  }, [tetik]);
}
