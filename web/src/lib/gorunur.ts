import { useCallback, useEffect, useRef, useState } from "react";

/** 17.11 Santralim hız turu — görünürlük kapısı: bir bölgenin verisi, bölge görüş alanına (payda kadar) yaklaşınca istenir.
 *  Bir kez açılınca açık kalır (kaydırınca kapanmaz); IntersectionObserver yoksa hemen açık sayılır (eski motor, SSR).
 *  Amaç: ilk ekranın istekleriyle sayfa altının 10+ isteği aynı anda sunucu kuyruğuna girmesin.
 *  Geri çağrı ref: öğe sonradan bağlansa da (iskelet → gerçek sayfa) gözlemci o anda kurulur; bağımlılıksız efekt gerekmez. */
export function useGorunur<T extends Element>(payda = "480px"): [(el: T | null) => void, boolean] {
  const [gorunur, setGorunur] = useState(false);
  const acik = useRef(false);
  const io = useRef<IntersectionObserver | null>(null);
  const ref = useCallback((el: T | null) => {
    io.current?.disconnect(); io.current = null;
    if (!el || acik.current) return;
    if (typeof IntersectionObserver === "undefined") { acik.current = true; setGorunur(true); return; }
    const o = new IntersectionObserver((kayitlar) => {
      if (kayitlar.some((k) => k.isIntersecting)) { acik.current = true; setGorunur(true); o.disconnect(); io.current = null; }
    }, { rootMargin: `${payda} 0px` });
    o.observe(el); io.current = o;
  }, [payda]);
  useEffect(() => () => { io.current?.disconnect(); }, []);
  return [ref, gorunur];
}
