import { useEffect, useRef, useState, type ImgHTMLAttributes } from "react";
import { useHeroHazir } from "./heroHazir";

/** İllüstrasyon levhası (16.10 hız turu 3): dosya bayt bayt aynı (Storyset PNG, 2000×2000); yalnız
 *  İNDİRME ZAMANI yönetilir. Hero posteri inene dek `src` verilmez — tarayıcının tembel yükleme eşiği
 *  (mobil 3G'de 2500 px) «Dört adım» levhalarını açılışta posterle yarıştırıyordu. Kullanıcı o arada
 *  levhanın yanına kaydırırsa (120 px) beklemeden indirilir. Genişlik/yükseklik öznitelikleri yer
 *  tuttuğundan kayma olmaz. */
export function Levha({ src, ...oz }: ImgHTMLAttributes<HTMLImageElement> & { src: string }) {
  const heroHazir = useHeroHazir();
  const ref = useRef<HTMLImageElement>(null);
  const [yakin, setYakin] = useState(false);
  useEffect(() => {
    if (heroHazir || yakin) return;
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") { setYakin(true); return; }
    const io = new IntersectionObserver(([g]) => { if (g?.isIntersecting) { setYakin(true); io.disconnect(); } }, { rootMargin: "120px 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, [heroHazir, yakin]);
  return <img ref={ref} {...oz} src={heroHazir || yakin ? src : undefined} />;
}
