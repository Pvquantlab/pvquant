/** Tema kancasi (v2.73-A yeniden yazim — kayip lib/ dosyasi).
 *  oku: :root'tan CSS degiskeni okur (grafikler CSS temasiyla ayni dili konussun).
 *  n: tema degisim sayaci — <html> nitelikleri degisince artar;
 *  useMemo bagimliligi olarak grafigi yeni renklerle tazeler. */
import { useEffect, useState } from "react";

export function useTema() {
  const [n, setN] = useState(0);

  useEffect(() => {
    // 24.10 açık tema geçiş turu: YALNIZ data-tema izlenir. Kabuk tema geçişinde <html>'e önce .tema-gecisi sınıfını
    // koyup 120 ms sonra kaldırır; filtresiz gözlemci her tema değişiminde ÜÇ kez tetikleniyor, sayfadaki her grafik
    // seçeneklerini üç kez kurup setOption(notMerge) ile üç kez yeniden çiziyordu (Doğruluk: 6 grafik × 3). Renkler
    // data-tema ile birlikte değiştiğinden tek tetik yeterlidir; çıktı birebir aynı.
    const gozlemci = new MutationObserver(() => setN((x) => x + 1));
    gozlemci.observe(document.documentElement, { attributes: true, attributeFilter: ["data-tema"] });
    return () => gozlemci.disconnect();
  }, []);

  const oku = (ad: string): string =>
    getComputedStyle(document.documentElement).getPropertyValue(ad).trim();

  return { n, oku };
}
