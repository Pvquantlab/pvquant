import { useEffect, useRef } from "react";

/** Kullanıcının sayfayı kendisi oynattığını gösteren girdiler. `scroll` olayı yetmez: kendi scrollIntoView'umuz ve
 *  tarayıcının kaydırma çapalaması (scroll anchoring, içerik yüksekliği değişince) da scrollY'yi oynatır. */
const GIRDILER = ["wheel", "touchstart", "pointerdown", "keydown"] as const;

/** Sayfalar arası çapa düzeltmesi (örn. ana sayfadan /yontem#yt-tanimlar'a, /yontem'den /#ilkeler'e):
 *  tarayıcı kaydırmayı React hedefi çizmeden dener ve sayfa başında kalır. İlk çizimden sonra hedefe
 *  kendimiz kaydırırız; `tetik` (örn. doğrulama durumu) değişince yeniden — iskeletten gerçek içeriğe
 *  geçiş bölüm yüksekliklerini değiştirir. Üst çubuk payı .vt [id] üzerindeki scroll-margin-top'tan.
 *  17.10 denetimi: geç gelen yanıt, kullanıcı çoktan kaydırmışken onu çapaya geri çekiyordu (/yontem çekmece →
 *  «Açık karne» → /#karne, hemen kaydır). Son çapa sıçramasından beri kullanıcı kaydırdı, dokundu ya da tuşa
 *  bastıysa yeniden kaydırılmaz. Sayfa içi çapa tıkı (hashchange) yeni sıçramadır: izleme orada sıfırlanır. */
export function useCapaKaydir(tetik?: unknown) {
  const oynadi = useRef(false);
  useEffect(() => {
    const isaretle = () => { oynadi.current = true; };
    const yeniCapa = () => { oynadi.current = false; };
    for (const o of GIRDILER) window.addEventListener(o, isaretle, { capture: true, passive: true });
    window.addEventListener("hashchange", yeniCapa);
    return () => {
      for (const o of GIRDILER) window.removeEventListener(o, isaretle, { capture: true });
      window.removeEventListener("hashchange", yeniCapa);
    };
  }, []);
  useEffect(() => {
    const h = window.location.hash;
    if (!h || oynadi.current) return;
    const kare = requestAnimationFrame(() => {
      if (!oynadi.current) document.getElementById(decodeURIComponent(h.slice(1)))?.scrollIntoView();
    });
    return () => cancelAnimationFrame(kare);
  }, [tetik]);
}
