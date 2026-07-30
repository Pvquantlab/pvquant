/** Tema kancasi (v2.73-A yeniden yazim — kayip lib/ dosyasi).
 *  oku: :root'tan CSS degiskeni okur (grafikler CSS temasiyla ayni dili konussun).
 *  n: tema degisim sayaci — <html> nitelikleri degisince artar;
 *  useMemo bagimliligi olarak grafigi yeni renklerle tazeler. */
import { useEffect, useState } from "react";

export function useTema() {
  const [n, setN] = useState(0);

  useEffect(() => {
    const gozlemci = new MutationObserver(() => setN((x) => x + 1));
    gozlemci.observe(document.documentElement, { attributes: true });
    return () => gozlemci.disconnect();
  }, []);

  const oku = (ad: string): string =>
    getComputedStyle(document.documentElement).getPropertyValue(ad).trim();

  return { n, oku };
}
