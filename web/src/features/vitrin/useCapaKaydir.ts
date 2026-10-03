import { useEffect } from "react";

/** Sayfalar arası çapa düzeltmesi (örn. ana sayfadan /yontem#yt-tanimlar'a, /yontem'den /#ilkeler'e):
 *  tarayıcı kaydırmayı React hedefi çizmeden dener ve sayfa başında kalır. İlk çizimden sonra hedefe
 *  kendimiz kaydırırız; `tetik` (örn. doğrulama durumu) değişince yeniden — iskeletten gerçek içeriğe
 *  geçiş bölüm yüksekliklerini değiştirir. Üst çubuk payı .vt [id] üzerindeki scroll-margin-top'tan. */
export function useCapaKaydir(tetik?: unknown) {
  useEffect(() => {
    const h = window.location.hash;
    if (!h) return;
    requestAnimationFrame(() => {
      document.getElementById(decodeURIComponent(h.slice(1)))?.scrollIntoView();
    });
  }, [tetik]);
}
