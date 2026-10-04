import { useEffect, useRef, useState } from "react";
import { BOLUMLER } from "./bolumler";

/** Sayfa içi bölüm çubuğu (R30): uzun anlatıda yön duygusu — Solargis'in ürün alt-nav'ının
 *  bizim dilde karşılığı. Hero'dan sonra akışa girer, üst çubuğun altına yapışır; scroll-spy
 *  aktif bölümü işaretler. IO yoksa işaretleme yapılmaz ve çubuk düz bağlantı listesi gibi
 *  davranır; azaltılmış harekette spy sürer, yalnız geçişler kapalıdır. Hiçbir şey gizlenmez. */
export function BolumCubugu() {
  const [aktif, setAktif] = useState<string | null>(null);
  const kutu = useRef<HTMLElement>(null);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const hedefler = BOLUMLER
      .map(([id]) => document.getElementById(id))
      .filter((e): e is HTMLElement => e !== null);
    // Bantta olanlar kümede tutulur (IO yalnız DEĞİŞEN girdileri bildirir — "o anki görünürler"
    // listesi değildir); aktif = kümedekilerin belge sırasında SONUNCUSU. En üsttekini seçmek
    // uzun bir önceki bölümü aktif bırakıyordu; çıkış olayında küme güncellenince geri
    // kaydırma da doğru çalışır.
    const bantta = new Set<string>();
    const io = new IntersectionObserver(
      (girdiler) => {
        for (const g of girdiler) {
          if (g.isIntersecting) bantta.add(g.target.id);
          else bantta.delete(g.target.id);
        }
        const sirali = BOLUMLER.map(([bolumId]) => bolumId).filter((bolumId) => bantta.has(bolumId));
        if (sirali.length > 0) setAktif(sirali[sirali.length - 1]);
      },
      { rootMargin: "-124px 0px -55% 0px", threshold: 0 },   // 64px üst çubuk + 45px çubuk + pay
    );
    hedefler.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
  // Dar ekranda aktif bağlantı şeride getirilir — SAYFA değil yalnız şerit kaydırılır:
  // scrollIntoView(block:'nearest') + 80px odak scroll-margin birleşimi her aktif değişiminde
  // sayfayı 16px yukarı çekip kullanıcının kaydırmasıyla kavga ediyordu (inceleme C2).
  useEffect(() => {
    if (!aktif || !kutu.current) return;
    const serit = kutu.current.querySelector<HTMLElement>(".vt-bolumcubuk__ic");
    const bag = kutu.current.querySelector<HTMLAnchorElement>(`a[href="#${aktif}"]`);
    if (!serit || !bag || serit.scrollWidth <= serit.clientWidth) return;
    const s = serit.getBoundingClientRect();
    const b = bag.getBoundingClientRect();
    if (b.left < s.left) serit.scrollLeft += b.left - s.left - 20;
    else if (b.right > s.right) serit.scrollLeft += b.right - s.right + 20;
  }, [aktif]);
  return (
    <nav ref={kutu} className="vt-bolumcubuk" aria-label="Sayfa bölümleri">
      <div className="vt-kap vt-bolumcubuk__ic">
        <span className="vt-bolumcubuk__et" aria-hidden="true">Bu sayfada</span>
        <ul role="list" className="vt-bolumcubuk__liste">
          {BOLUMLER.map(([id, ad]) => (
            <li key={id}>
              <a className="vt-bolumcubuk__bag" href={`#${id}`}
                aria-current={aktif === id ? "true" : undefined}>{ad}</a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
